import React from 'react';
import { useApp } from '../context/AppContext';
import { 
  Flame, 
  Wind, 
  Droplet, 
  Activity, 
  Thermometer, 
  ShieldAlert, 
  CheckCircle,
  AlertTriangle,
  Sliders,
  Cpu,
  Navigation
} from 'lucide-react';

const disasterConfigs = [
  {
    type: 'Normal',
    label: 'Normal Grid Mode',
    icon: CheckCircle,
    color: 'border-brand-green bg-green-950/10 text-brand-green shadow-glow-green/10',
    description: 'System running under standard parameters. Renewables routing automatically. Battery stations storing surplus power.',
    impacts: { solar: '100%', wind: 'Dynamic', demand: 'Baseline', roads: '100% Accessible', grid: 'Stable' }
  },
  {
    type: 'Cyclone',
    label: 'Category 4 Cyclone',
    icon: Wind,
    color: 'border-brand-red bg-red-950/10 text-brand-red shadow-glow-red/10',
    description: 'High winds (up to 95 km/h) and heavy rainfall. Capping solar farms for protection. Wind turbines close down if wind exceeds safety threshold.',
    impacts: { solar: '5% (Tilt-profile)', wind: '0% or Capped', demand: 'Baseline', roads: 'Deteriorated (15 km/h)', grid: 'Severed / Islanded' }
  },
  {
    type: 'Flood',
    label: 'Regional Flooding',
    icon: Droplet,
    color: 'border-brand-blue bg-blue-950/10 text-brand-blue shadow-glow-blue/10',
    description: 'Major rivers breaching levels. Key substations and road bridges underwater. Power lines downed.',
    impacts: { solar: '20% (Heavy cloud)', wind: '80% Output', demand: 'Baseline', roads: 'Blocked (12 km/h)', grid: 'Severed / Islanded' }
  },
  {
    type: 'Earthquake',
    label: 'Magnitude 7.2 Earthquake',
    icon: Activity,
    color: 'border-brand-red bg-red-950/10 text-brand-red shadow-glow-red/10',
    description: 'Severe ground displacement. Collapsed towers, physical structural damage to solar arrays, and high risk of grid fires.',
    impacts: { solar: '60% (Damaged arrays)', wind: '90% Output', demand: 'Baseline', roads: 'Debris closed (10 km/h)', grid: 'Severed / Islanded' }
  },
  {
    type: 'Heatwave',
    label: 'Extreme Heat Dome',
    icon: Thermometer,
    color: 'border-brand-amber bg-amber-950/10 text-brand-amber shadow-glow-amber/10',
    description: 'Ambient temperatures climbing to 43°C. Massive AC load spike. Panel efficiency degradation. Zero wind speed.',
    impacts: { solar: '85% (Heat loss)', wind: '10% (Calm air)', demand: '+35% Peak load', roads: '100% Accessible', grid: 'Rolling Blackouts' }
  },
  {
    type: 'Cyber Attack',
    label: 'SCADA Ransomware',
    icon: ShieldAlert,
    color: 'border-brand-cyber bg-cyan-950/10 text-brand-cyber shadow-glow-cyber/10',
    description: 'Malicious payload targets grid automation controllers. Battery telemetry reading erratic, solar/wind outputs locked.',
    impacts: { solar: '30% (Locked down)', wind: '30% (Locked down)', demand: 'Baseline', roads: '100% Accessible', grid: 'Telemetry Lost' }
  }
];

export default function Simulator() {
  const { data, changeDisaster } = useApp();

  if (!data) return null;

  const currentDisaster = data.disaster.type;
  const currentSeverity = data.disaster.severity;

  const handleDisasterSelect = (type) => {
    changeDisaster(type, type === 'Normal' ? 0.0 : 0.85);
  };

  const handleSeverityChange = (e) => {
    const val = parseFloat(e.target.value);
    changeDisaster(currentDisaster, val);
  };

  return (
    <div className="flex flex-col gap-6">
      
      {/* Page Header */}
      <div className="flex items-center justify-between border-b border-gray-800 pb-4">
        <div>
          <h1 className="text-xl font-extrabold tracking-wider text-white font-mono uppercase">
            Disaster Simulation Cockpit
          </h1>
          <p className="text-xs text-gray-500 font-mono">
            TRIGGER GRID EMERGENCIES AND RUN DYNAMIC RIGID-STRESS TESTS
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-900 border border-gray-800 rounded text-xs font-mono">
          <span>ACTIVE SIMULATOR STATUS:</span>
          <span className="text-brand-green font-bold uppercase animate-pulse">INTELLIGENT REACTION LIVE</span>
        </div>
      </div>

      {/* Main Grid: Selectors + Severity */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Side: Buttons Panel (Col span 8) */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {disasterConfigs.map((cfg) => {
              const Icon = cfg.icon;
              const isActive = currentDisaster === cfg.type;
              return (
                <button
                  key={cfg.type}
                  onClick={() => handleDisasterSelect(cfg.type)}
                  className={`p-5 rounded-xl border text-left flex gap-4 transition-all duration-200 ${
                    isActive 
                      ? `${cfg.color} border-2 ring-1 ring-white/10 scale-[1.01]` 
                      : 'border-gray-800 bg-brand-panel hover:bg-gray-800 hover:border-gray-700'
                  }`}
                >
                  <div className={`p-2.5 rounded-lg border ${
                    isActive 
                      ? 'bg-white/10 border-white/20' 
                      : 'bg-gray-950/40 border-gray-800 text-gray-400'
                  }`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 flex flex-col gap-1">
                    <span className={`font-extrabold text-sm uppercase tracking-wide ${isActive ? 'text-white' : 'text-gray-300'}`}>
                      {cfg.label}
                    </span>
                    <p className="text-[11px] text-gray-400 leading-relaxed font-mono">
                      {cfg.description}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Side: Severity Controls + AI Matrix (Col span 4) */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          
          {/* Dynamic Severity Adjustment Card */}
          {currentDisaster !== 'Normal' && (
            <div className="p-5 rounded-xl border border-brand-red bg-red-950/5 glass-panel flex flex-col gap-4">
              <h3 className="text-xs uppercase font-mono tracking-widest text-brand-red font-bold flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 led-red" />
                Disaster Severity Control
              </h3>
              
              <div className="flex flex-col gap-3 font-mono">
                <div className="flex justify-between items-center text-xs text-gray-400">
                  <span>SCALE FACTOR</span>
                  <span className="text-brand-red font-bold">{(currentSeverity * 100).toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.05"
                  value={currentSeverity}
                  onChange={handleSeverityChange}
                  className="w-full h-1.5 bg-gray-900 rounded-lg appearance-none cursor-pointer accent-brand-red"
                />
                <div className="flex justify-between text-[9px] text-gray-500">
                  <span>LIGHT (0.1)</span>
                  <span>MED (0.5)</span>
                  <span>CATASTROPHIC (1.0)</span>
                </div>
              </div>
            </div>
          )}

          {/* AI Decision Rules Matrix */}
          <div className="p-5 rounded-xl border border-gray-800 bg-brand-panel glass-panel flex flex-col gap-4">
            <h3 className="text-xs uppercase font-mono tracking-widest text-gray-400 border-b border-gray-800 pb-2 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-brand-green" />
              AI Reaction Matrix
            </h3>

            {(() => {
              const activeCfg = disasterConfigs.find(c => c.type === currentDisaster) || disasterConfigs[0];
              return (
                <div className="flex flex-col gap-3 font-mono text-xs">
                  <div className="flex justify-between border-b border-gray-900 pb-1.5">
                    <span className="text-gray-500">SOLAR MOD:</span>
                    <span className="font-semibold text-brand-green">{activeCfg.impacts.solar}</span>
                  </div>
                  <div className="flex justify-between border-b border-gray-900 pb-1.5">
                    <span className="text-gray-500">WIND MOD:</span>
                    <span className="font-semibold text-brand-green">{activeCfg.impacts.wind}</span>
                  </div>
                  <div className="flex justify-between border-b border-gray-900 pb-1.5">
                    <span className="text-gray-500">CITY DEMAND:</span>
                    <span className="font-semibold text-brand-blue">{activeCfg.impacts.demand}</span>
                  </div>
                  <div className="flex justify-between border-b border-gray-900 pb-1.5">
                    <span className="text-gray-500">ROAD ACCESS:</span>
                    <span className="font-semibold text-brand-amber">{activeCfg.impacts.roads}</span>
                  </div>
                  <div className="flex justify-between pb-0.5">
                    <span className="text-gray-500">GRID PROFILE:</span>
                    <span className="font-semibold text-brand-red">{activeCfg.impacts.grid}</span>
                  </div>
                </div>
              );
            })()}
          </div>

          {/* Mobile Ambulance Dispatch Details */}
          <div className="p-5 rounded-xl border border-gray-800 bg-brand-panel glass-panel flex flex-col gap-3">
            <h3 className="text-xs uppercase font-mono tracking-widest text-gray-400 flex items-center gap-2">
              <Navigation className="w-4 h-4 text-brand-blue" />
              Ambulance Deployment Physics
            </h3>
            <p className="text-[11px] text-gray-400 font-mono leading-relaxed">
              When disaster strikes and critical nodes exhaust battery storage, the AI dispatches Energy Ambulances. 
              Ambulance travel times are dynamically constrained by road conditions, calculated via haversine distance.
            </p>
          </div>

        </div>

      </div>
    </div>
  );
}
