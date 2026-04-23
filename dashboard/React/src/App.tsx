import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  Thermometer, 
  Droplets, 
  Sun, 
  Wind, 
  Zap, 
  Brain, 
  Settings,
  Waves,
  Scan,
  Cloud
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { cn } from './lib/utils';
import { SensorData, ActuatorStatus, AIThought, PlantStatus, PlantType } from './types';
import { ParticleBackground } from './components/Particles';
import { PlantParticleScanner } from './components/PlantParticleScanner';

// --- API 数据获取逻辑（对接 bridge.py）---

/** 将 thought.log 中解析出的条目转换为 AIThought 格式 */
function parseThoughtsToDisplayItems(raw: any[]): AIThought[] {
  const items: AIThought[] = [];
  raw.forEach((entry) => {
    const ts = entry.timestamp.substring(11); // 只取时间部分
    // AI 推理过程
    items.push({
      id: `${entry.id}-r`,
      timestamp: ts,
      type: 'reasoning',
      content: entry.thought,
    });
    // 动作列表
    if (entry.actions?.length) {
      const relayNames: Record<number, string> = {
        1: '营养液泵', 2: '进气扇', 3: '排气扇', 7: '打氧泵', 8: '补光灯',
      };
      const acted = entry.actions
        .map((a: any) => `${relayNames[a.relay_id] ?? `继电器${a.relay_id}`} ${a.state ? 'ON' : 'OFF'}`)
        .join(' | ');
      items.push({
        id: `${entry.id}-a`,
        timestamp: ts,
        type: 'action',
        content: `执行指令：${acted}`,
      });
    }
  });
  return items;
}

// --- Components ---

const StatItem = ({ icon: Icon, label, value, unit, colorClass }: any) => (
  <div className="flex items-center gap-3 p-2 stardew-card bg-white/40 group hover:bg-white/60 transition-colors">
    <div className={cn("p-2 border-2 border-stardew-brown-dark bg-stardew-brown-light text-stardew-parchment group-hover:scale-110 transition-transform", colorClass)}>
      <Icon size={16} />
    </div>
    <div>
      <div className="text-[10px] text-stardew-brown-dark font-bold pixel-font">{label}</div>
      <div className="text-lg pixel-font font-bold">
        {value}<span className="text-xs ml-0.5 text-stardew-brown-dark/70">{unit}</span>
      </div>
    </div>
  </div>
);

const ActuatorStatusBadge = ({ icon: Icon, label, active, colorClass, compact }: any) => (
  <div className={cn(
    "flex items-center justify-between border-2 border-stardew-brown-dark transition-all",
    compact ? "px-2 py-0.5 gap-2" : "p-2",
    active ? "bg-stardew-gold/30 shadow-[inset_0_0_10px_rgba(255,204,51,0.2)]" : "bg-stardew-brown-dark/10 opacity-60"
  )}>
    <div className="flex items-center gap-2">
      <div className={cn(compact ? "p-0.5" : "p-1 border border-stardew-brown-dark bg-stardew-parchment", active ? colorClass : "text-stardew-brown-dark/40")}>
        <Icon size={compact ? 10 : 14} />
      </div>
      <span className={cn("pixel-font font-bold", compact ? "text-[10px]" : "text-xs")}>{label}</span>
    </div>
    <div className={cn("status-dot", active ? cn("bg-stardew-gold shadow-[0_0_4px_currentColor]") : "bg-stardew-brown-dark/30")} />
  </div>
);

export default function App() {
  const [sensors, setSensors] = useState<SensorData | null>(null);
  const [thoughts, setThoughts] = useState<AIThought[]>([]);
  const [actuators, setActuators] = useState<ActuatorStatus>({
    light: false,
    intakeFan: false,
    exhaustFan: false,
    oxygenPump: false,
    nutrientPump: false,
    intensity: 85,
  });

  const [plantStatus, setPlantStatus] = useState<PlantStatus>({
    type: 'lettuce',
    height: 12.4,
    leafCount: 6,
    health: 95,
    lastUpdated: new Date().toISOString(),
  });

  const [currentTime, setCurrentTime] = useState(new Date());
  const [startTime] = useState(new Date(Date.now() - 1000 * 60 * 60 * 24 * 3.5));

  const terminalRef = useRef<HTMLDivElement>(null);

  // 轮询传感器数据（每 30 秒）
  useEffect(() => {
    const fetchSensors = () => {
      fetch('/api/sensors')
        .then(r => r.json())
        .then((data) => {
          setSensors({
            timestamp: new Date(data.timestamp * 1000).toISOString(),
            temp: data.temp ?? 0,
            humidity: data.humidity ?? 0,
            waterTemp: 0,
            co2: data.co2 ?? 0,
            ec: data.ec ?? 0,
          });
          // 由最新动作推断执行器状态
          setActuators(prev => ({
            ...prev,
            light: false,
            intakeFan: false,
            exhaustFan: false,
            oxygenPump: false,
            nutrientPump: false,
          }));
        })
        .catch(() => {});
    };
    fetchSensors();
    const si = setInterval(fetchSensors, 30000);
    return () => clearInterval(si);
  }, []);

  // 轮询 AI 思考日志（每 60 秒）
  useEffect(() => {
    const fetchThoughts = () => {
      fetch('/api/thoughts')
        .then(r => r.json())
        .then((raw: any[]) => {
          setThoughts(parseThoughtsToDisplayItems(raw));
          // 根据最新一条动作推断继电器状态
          if (raw.length > 0) {
            const latest = raw[0];
            const on = new Set((latest.actions ?? []).filter((a: any) => a.state === 1).map((a: any) => a.relay_id));
            setActuators({
              light: on.has(8),
              intakeFan: on.has(2),
              exhaustFan: on.has(3),
              oxygenPump: on.has(7),
              nutrientPump: on.has(1),
              intensity: 85,
            });
          }
        })
        .catch(() => {});
    };
    fetchThoughts();
    const ti = setInterval(fetchThoughts, 60000);
    return () => clearInterval(ti);
  }, []);

  // 更新时钟
  useEffect(() => {
    const ci = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(ci);
  }, []);

  const getBeijingTime = () => {
    return new Intl.DateTimeFormat('zh-CN', {
      timeZone: 'Asia/Shanghai',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }).format(currentTime);
  };

  const getRunningDuration = () => {
    const diff = currentTime.getTime() - startTime.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    return `${days}天 ${hours}小时 ${mins}分`;
  };

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [thoughts]);

  return (
    <div className="h-screen w-full flex flex-col p-4 gap-4 bg-[#2c1e14] text-stardew-brown-dark overflow-hidden relative">
      {/* Particle Background */}
      <ParticleBackground />

      <div className="relative z-10 flex flex-col h-full gap-4">
        {/* Top Header Bar */}
        <header className="flex items-center justify-between px-4 py-2 stardew-header-card shrink-0">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-stardew-parchment border-2 border-stardew-brown-dark flex items-center justify-center shadow-[2px_2px_0_0_rgba(0,0,0,0.2)]">
                <Sun className="text-stardew-gold" size={24} />
              </div>
              <div className="flex flex-col">
                <h1 className="text-2xl pixel-font font-bold text-stardew-parchment drop-shadow-[2px_2px_0_rgba(0,0,0,0.5)] leading-none">后稷农场 <span className="text-stardew-gold/80 text-sm ml-1">HOUJI FARM</span></h1>
                <p className="text-[10px] pixel-font text-stardew-parchment/60 mt-1">LLM驱动的智慧农场项目</p>
              </div>
            </div>
            <div className="h-6 w-1 bg-stardew-brown-dark/30 mx-2" />
            
            <div className="flex items-center gap-8 pixel-font text-stardew-parchment">
               <div className="flex flex-col">
                 <span className="text-[10px] opacity-70 leading-none mb-1">北京时间</span>
                 <span className="text-xl leading-none">{getBeijingTime()}</span>
               </div>
               <div className="flex flex-col">
                 <span className="text-[10px] opacity-70 leading-none mb-1">持续运行时间</span>
                 <span className="text-xl leading-none">{getRunningDuration()}</span>
               </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1 bg-stardew-green/20 border-2 border-stardew-green/40">
              <div className="status-dot bg-stardew-green animate-pulse" />
              <span className="text-xs pixel-font font-bold text-stardew-parchment">AI 正在照看</span>
            </div>
            <Settings size={20} className="text-stardew-parchment hover:text-stardew-gold cursor-pointer transition-colors" />
          </div>
        </header>

        {/* Main Content Area - Bento Grid */}
        <main className="flex-1 grid grid-cols-12 grid-rows-6 gap-4 min-h-0">
          
          {/* Camera Feed - Top Left */}
          <div className="col-span-6 row-span-4 stardew-card overflow-hidden">
            <div className="absolute top-2 left-2 z-20">
              <div className="bg-stardew-brown-dark text-stardew-parchment px-2 py-0.5 pixel-font text-sm border-2 border-stardew-parchment/30">
                实时监控: 农场摄像头
              </div>
            </div>
            <img 
              src="https://images.unsplash.com/photo-1558449028-b53a39d100fc?auto=format&fit=crop&q=80&w=1200" 
              alt="Hydroponics"
              className="w-full h-full object-cover opacity-90"
              referrerPolicy="no-referrer"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-stardew-brown-dark/40 to-transparent pointer-events-none" />
            
            {/* CV Overlay */}
            <div className="absolute inset-0 p-4 flex flex-col justify-end pointer-events-none">
              <div className="flex gap-4">
                <div className="bg-black/40 backdrop-blur-sm border-2 border-stardew-green p-1 px-2">
                  <span className="text-[10px] text-white pixel-font block">当前作物</span>
                  <span className="text-sm font-bold text-stardew-gold pixel-font">健康 [98%]</span>
                </div>
              </div>
            </div>
          </div>

          {/* AI Reasoning Log - Top Right */}
          <div className="col-span-6 row-span-4 stardew-card flex flex-col">
            <div className="p-2 border-b-4 border-stardew-brown-dark bg-stardew-brown-light text-stardew-parchment flex items-center gap-2">
              <Brain size={16} />
              <h2 className="pixel-font text-lg font-bold">农场日志</h2>
            </div>
            <div 
              ref={terminalRef}
              className="flex-1 p-3 pixel-font text-lg overflow-y-auto space-y-2 custom-scrollbar bg-[#fcf5e5]"
            >
              <AnimatePresence initial={false}>
                {thoughts.map((thought) => (
                  <motion.div 
                    key={thought.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex flex-col gap-0.5 border-b border-stardew-brown-dark/10 pb-1"
                  >
                    <div className="flex items-center justify-between text-xs opacity-70">
                      <span className={cn(
                        "font-bold",
                        thought.type === 'observation' && "text-blue-700",
                        thought.type === 'reasoning' && "text-purple-700",
                        thought.type === 'action' && "text-stardew-green",
                      )}>
                        [{thought.type === 'observation' ? '观察' : thought.type === 'reasoning' ? '分析' : '行动'}]
                      </span>
                      <span>{thought.timestamp}</span>
                    </div>
                    <p className="text-stardew-brown-dark leading-tight">{thought.content}</p>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>

          {/* Sensors - Bottom Left (1/3 height, 1/3 width) */}
          <div className="col-span-4 row-span-2 stardew-card p-4 flex flex-col">
            <div className="flex items-center gap-2 mb-3">
              <Activity size={16} className="text-stardew-brown-dark" />
              <h2 className="pixel-font text-lg font-bold">环境参数</h2>
            </div>
            <div className="grid grid-cols-2 gap-3 flex-1">
              <StatItem icon={Thermometer} label="空气温度" value={sensors ? sensors.temp.toFixed(1) : '--'} unit="°C" colorClass="text-orange-600" />
              <StatItem icon={Droplets} label="空气湿度" value={sensors ? sensors.humidity.toFixed(1) : '--'} unit="%" colorClass="text-blue-600" />
              <StatItem icon={Cloud} label="二氧化碳" value={sensors ? sensors.co2.toFixed(0) : '--'} unit="ppm" colorClass="text-stardew-green" />
              <StatItem icon={Zap} label="电导率" value={sensors && sensors.ec ? sensors.ec.toFixed(2) : 'N/A'} unit="mS" colorClass="text-stardew-gold" />
            </div>
          </div>

          {/* Actuators - Bottom Middle (1/3 height, 5/12 width) */}
          <div className="col-span-5 row-span-2 stardew-card p-4 flex flex-col">
            <div className="flex items-center gap-2 mb-3">
              <Settings size={16} className="text-stardew-brown-dark" />
              <h2 className="pixel-font text-lg font-bold">元器件控制</h2>
            </div>
            <div className="grid grid-cols-2 gap-2 flex-1">
              <ActuatorStatusBadge icon={Sun} label="补光灯" active={actuators.light} colorClass="text-stardew-gold" />
              <ActuatorStatusBadge icon={Waves} label="增氧泵" active={actuators.oxygenPump} colorClass="text-blue-500" />
              <ActuatorStatusBadge icon={Wind} label="进气扇" active={actuators.intakeFan} colorClass="text-blue-400" />
              <ActuatorStatusBadge icon={Wind} label="排气扇" active={actuators.exhaustFan} colorClass="text-orange-400" />
              <div className="col-span-2">
                <ActuatorStatusBadge icon={Droplets} label="营养液蠕动泵" active={actuators.nutrientPump} colorClass="text-emerald-500" />
              </div>
            </div>
          </div>

          {/* Plant Particle Scanner - Bottom Right (1/3 height, 3/12 width) */}
          <div className="col-span-3 row-span-2 stardew-card flex flex-col overflow-hidden">
            <div className="p-2 border-b-4 border-stardew-brown-dark bg-stardew-brown-light text-stardew-parchment flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Scan size={16} />
                <h2 className="pixel-font text-lg font-bold">作物扫描</h2>
              </div>
            </div>
            <div className="flex-1 min-h-0 bg-[#1a1a1a] relative">
              <PlantParticleScanner 
                status={plantStatus}
                onUpdate={setPlantStatus}
              />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}


