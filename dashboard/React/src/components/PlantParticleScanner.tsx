import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Camera, Loader2 } from 'lucide-react';
import { PlantType, PlantStatus } from '../types';
import { analyzePlantImage } from '../services/geminiService';

interface PlantParticleScannerProps {
  status: PlantStatus;
  onUpdate: (newStatus: PlantStatus) => void;
}

export const PlantParticleScanner: React.FC<PlantParticleScannerProps> = ({
  status,
  onUpdate,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsAnalyzing(true);
    const reader = new FileReader();
    reader.onloadend = async () => {
      const base64 = reader.result as string;
      try {
        const newStatus = await analyzePlantImage(base64);
        onUpdate(newStatus);
      } catch (error) {
        console.error("Analysis failed:", error);
      } finally {
        setIsAnalyzing(false);
      }
    };
    reader.readAsDataURL(file);
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let particles: Particle[] = [];

    class Particle {
      x: number;
      y: number;
      originX: number;
      originY: number;
      size: number;
      color: string;
      angle: number;
      type: 'stem' | 'leaf' | 'ghost' | 'oxygen' | 'sunlight' | 'fruit';
      life: number;
      maxLife: number;

      constructor(x: number, y: number, color: string, type: 'stem' | 'leaf' | 'ghost' | 'oxygen' | 'sunlight' | 'fruit') {
        this.x = x;
        this.y = y;
        this.originX = x;
        this.originY = y;
        this.type = type;
        this.size = type === 'oxygen' || type === 'sunlight' ? Math.random() * 1 + 0.5 : Math.random() * 1.5 + 0.5;
        this.color = color;
        this.angle = Math.random() * Math.PI * 2;
        this.maxLife = type === 'oxygen' || type === 'sunlight' ? 100 : 100;
        this.life = this.maxLife;
      }

      update() {
        const time = Date.now() * 0.001;
        if (this.type === 'oxygen') {
          this.y -= 0.3;
          this.x += Math.sin(this.y * 0.1) * 0.2;
          this.life--;
        } else if (this.type === 'sunlight') {
          this.x += 0.2;
          this.y += 0.2;
          this.life--;
        } else {
          this.x = this.originX + Math.sin(time + this.angle) * 1.2;
          this.y = this.originY + Math.cos(time + this.angle) * 0.4;
        }
      }

      draw(ctx: CanvasRenderingContext2D) {
        if ((this.type === 'oxygen' || this.type === 'sunlight') && this.life <= 0) return;
        ctx.globalAlpha = this.type === 'ghost' ? 0.1 : (this.type === 'oxygen' || this.type === 'sunlight' ? this.life / this.maxLife : 1);
        ctx.fillStyle = this.color;
        const s = Math.ceil(this.size);
        ctx.fillRect(Math.floor(this.x), Math.floor(this.y), s, s);
        ctx.globalAlpha = 1;
      }
    }

    const init = () => {
      const width = canvas.width;
      const height = canvas.height;
      particles = [];

      const createPlantParticles = (
        centerX: number,
        plantHeight: number,
        leafCount: number,
        type: 'real' | 'ghost'
      ) => {
        const stemHeight = (plantHeight / 20) * height * 0.7;
        const startY = height - 20;
        const isGhost = type === 'ghost';
        const stemColor = isGhost ? '#ffffff' : '#348e3e';
        const leafColor = isGhost ? '#ffffff' : '#4ade80';

        if (status.type === 'lettuce') {
          // Lettuce: Bushy ball shape
          for (let i = 0; i < leafCount * 15; i++) {
            const angle = Math.random() * Math.PI * 2;
            const radius = Math.random() * (stemHeight * 0.6);
            const x = centerX + Math.cos(angle) * radius;
            const y = startY - (Math.random() * stemHeight * 0.8);
            particles.push(new Particle(x, y, leafColor, isGhost ? 'ghost' : 'leaf'));
          }
        } else if (status.type === 'tomato') {
          // Tomato: Tall stem with fruit
          for (let i = 0; i < stemHeight; i += 4) {
            const y = startY - i;
            const x = centerX + Math.sin(i * 0.05) * 2;
            particles.push(new Particle(x, y, stemColor, isGhost ? 'ghost' : 'stem'));
          }
          for (let i = 0; i < leafCount; i++) {
            const ly = startY - (i / leafCount) * stemHeight;
            const lx = centerX + (i % 2 === 0 ? 12 : -12);
            particles.push(new Particle(lx, ly, leafColor, isGhost ? 'ghost' : 'leaf'));
            if (!isGhost && i > 3 && i % 3 === 0) {
              particles.push(new Particle(lx + 4, ly + 4, '#ef4444', 'fruit'));
            }
          }
        } else {
          // Generic/Basil: Standard plant
          for (let i = 0; i < stemHeight; i += 4) {
            const y = startY - i;
            const x = centerX + Math.sin(i * 0.05) * 2;
            particles.push(new Particle(x, y, stemColor, isGhost ? 'ghost' : 'stem'));
          }
          for (let i = 0; i < leafCount; i++) {
            const ly = startY - (i / leafCount) * stemHeight;
            const side = i % 2 === 0 ? 1 : -1;
            const lx = centerX + side * 12;
            for (let j = 0; j < 6; j++) {
              const px = lx + Math.cos(j) * 6 * side;
              const py = ly + Math.sin(j) * 4;
              particles.push(new Particle(px, py, leafColor, isGhost ? 'ghost' : 'leaf'));
            }
          }
        }
      };

      createPlantParticles(width * 0.5, 20, 10, 'ghost');
      createPlantParticles(width * 0.5, status.height, status.leafCount, 'real');
    };

    const handleResize = () => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (rect) {
        canvas.width = rect.width;
        canvas.height = rect.height;
        init();
      }
    };

    let lastOxygen = 0;
    let lastSunlight = 0;
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const centerX = canvas.width * 0.5;
      const startY = canvas.height - 20;
      const stemHeight = (status.height / 20) * canvas.height * 0.7;

      if (Date.now() - lastOxygen > 1500) {
        const ox = centerX + (Math.random() - 0.5) * 20;
        const oy = startY - Math.random() * stemHeight;
        particles.push(new Particle(ox, oy, '#ffffff', 'oxygen'));
        lastOxygen = Date.now();
      }

      if (Date.now() - lastSunlight > 100) {
        const sx = Math.random() * canvas.width - 50;
        const sy = -10;
        particles.push(new Particle(sx, sy, '#fffce0', 'sunlight'));
        lastSunlight = Date.now();
      }

      particles = particles.filter(p => (p.type !== 'oxygen' && p.type !== 'sunlight') || p.life > 0);
      particles.forEach(p => {
        p.update();
        p.draw(ctx);
      });
      animationFrameId = requestAnimationFrame(animate);
    };

    window.addEventListener('resize', handleResize);
    handleResize();
    animate();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, [status]);

  return (
    <div className="w-full h-full relative overflow-hidden group">
      <canvas ref={canvasRef} className="w-full h-full" />
      
      <div className="absolute top-2 left-2 flex flex-col gap-1 pointer-events-none pixel-font">
        <div className="flex items-center gap-2 text-[12px] text-stardew-gold">
          <div className="w-2 h-2 bg-stardew-gold animate-pulse" />
          正在扫描: {status.type.toUpperCase()}
        </div>
      </div>

      <AnimatePresence>
        {isAnalyzing && (
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="absolute inset-0 bg-stardew-brown-dark/60 flex flex-col items-center justify-center gap-4 z-20"
          >
            <Loader2 className="w-8 h-8 text-stardew-gold animate-spin" />
            <span className="pixel-font text-stardew-parchment text-sm">AI 视觉分析中...</span>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10">
        <button 
          onClick={() => fileInputRef.current?.click()}
          className="stardew-card px-4 py-2 flex items-center gap-2 hover:scale-105 transition-transform active:scale-95"
        >
          <Camera className="w-4 h-4 text-stardew-brown-dark" />
          <span className="pixel-font text-stardew-brown-dark text-sm">上传照片</span>
        </button>
      </div>

      <input 
        type="file" ref={fileInputRef} accept="image/*" className="hidden"
        onChange={handleFileUpload}
      />
      
      <div className="absolute bottom-2 left-2 right-2 flex justify-between items-end pointer-events-none pixel-font">
        <div className="text-[10px] text-stardew-parchment/50 uppercase tracking-tighter">
          生物特征分析_v4.2
        </div>
        <div className="flex gap-2">
           <div className="h-2 w-16 bg-stardew-brown-dark rounded-none overflow-hidden border border-stardew-parchment/20">
             <motion.div 
               className="h-full bg-stardew-gold"
               animate={{ width: `${(status.height / 20) * 100}%` }}
             />
           </div>
        </div>
      </div>
    </div>
  );
};
