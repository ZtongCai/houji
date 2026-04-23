export type PlantType = 'lettuce' | 'tomato' | 'basil' | 'generic';

export interface PlantStatus {
  type: PlantType;
  height: number;
  leafCount: number;
  health: number; // 0-100
  lastUpdated: string;
}

export interface SensorData {
  timestamp: string;
  temp: number;
  humidity: number;
  waterTemp: number;
  co2: number;
  ec: number;
}

export interface ActuatorStatus {
  light: boolean;
  intakeFan: boolean;
  exhaustFan: boolean;
  oxygenPump: boolean;
  nutrientPump: boolean;
  intensity: number; // 0-100
}

export interface AIThought {
  id: string;
  timestamp: string;
  type: 'observation' | 'reasoning' | 'action' | 'alert';
  content: string;
}
