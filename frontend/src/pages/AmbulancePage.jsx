import React from 'react';
import { useApp } from '../context/AppContext';
import { 
  Truck, 
  Battery, 
  MapPin, 
  Clock, 
  Gauge, 
  Activity,
  Zap,
  CheckCircle2,
  TrendingUp
} from 'lucide-react';

export default function AmbulancePage() {
  const { activeData } = useApp();

  if (!activeData) return null;

  const ambulances = activeData.ambulances ?? [];
  const totalFleetCapacity = ambulances.reduce((acc, a) => acc + (a.battery_capacity ?? 0), 0);
  const totalFleetEnergy = ambulances.reduce((acc, a) => acc + (a.current_energy ?? 0), 0);
  const dispatchedCount = ambulances.filter(a => a.status === 'Dispatched' || a.status === 'Charging Node').length;

  return (
    <div className="flex flex-col gap-6 h-full">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-800 pb-4 shrink-0">
        <div>
          <h1 className="text-xl font-extrabold tracking-wider text-white font-mono uppercase flex items-center gap-2">
            <Truck className="w-5 h-5 text-brand-blue animate-pulse" />
            Ambulance Command Center
          </h1>
          <p className="text-xs text-gray-500 font-mono">
            MOBILE BATTERY ENERGY STORAGE SYSTEMS (BESS) DISPATCH CONTROL
          </p>
        </div>
      </div>

      {/* Fleet Stats Overview */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4 shrink-0">
        <div className="p-4 rounded-xl border border-gray-800 bg-brand-panel glass-panel flex items-center justify-between font-mono">
          <div>
            <span className="text-[10px] text-gray-500 uppercase tracking-wider block">Total Fleet Capacity</span>
            <span className="text-lg font-bold text-white mt-1 block">{totalFleetCapacity} kWh</span>
          </div>
          <Gauge className="w-8 h-8 text-brand-blue" />
        </div>
        
        <div className="p-4 rounded-xl border border-gray-800 bg-brand-panel glass-panel flex items-center justify-between font-mono">
          <div>
            <span className="text-[10px] text-gray-500 uppercase tracking-wider block">Available Mobile Storage</span>
            <span className="text-lg font-bold text-brand-green mt-1 block">
              {totalFleetEnergy.toFixed(1)} kWh ({totalFleetCapacity > 0 ? (totalFleetEnergy/totalFleetCapacity * 100).toFixed(0) : 0}%)
            </span>
          </div>
          <Battery className="w-8 h-8 text-brand-green" />
        </div>

        <div className="p-4 rounded-xl border border-gray-800 bg-brand-panel glass-panel flex items-center justify-between font-mono">
          <div>
            <span className="text-[10px] text-gray-500 uppercase tracking-wider block">Mobilized Vehicles</span>
            <span className="text-lg font-bold text-brand-amber mt-1 block">
              {dispatchedCount} / {ambulances.length} Active
            </span>
          </div>
          <Truck className="w-8 h-8 text-brand-amber" />
        </div>
      </section>

      {/* Grid of Ambulances */}
      <div className="grid grid-cols-1 gap-6 pb-6 lg:grid-cols-2">
        {ambulances.map(amb => {
          const capacity = amb.battery_capacity || 1;
          const soc = ((amb.current_energy ?? 0) / capacity) * 100;
          
          let statusBadge = 'bg-gray-900 border-gray-800 text-gray-400';
          let ledColor = 'bg-gray-500';
          let activeStage = 0;

          if (amb.status === 'Dispatched') {
            statusBadge = 'bg-brand-blue/10 border-brand-blue/30 text-brand-blue led-blue';
            ledColor = 'bg-brand-blue';
            activeStage = 1; // Travelling
          } else if (amb.status === 'Charging Node') {
            statusBadge = 'bg-brand-green/10 border-brand-green/30 text-brand-green led-green';
            ledColor = 'bg-brand-green';
            activeStage = 2; // Charging Node
          } else if (amb.status === 'Returning') {
            statusBadge = 'bg-brand-amber/10 border-brand-amber/30 text-brand-amber led-amber';
            ledColor = 'bg-brand-amber';
            activeStage = 3; // Returning
          } else if (amb.status === 'Recharging') {
            statusBadge = 'bg-cyan-900/20 border-brand-cyan/30 text-brand-cyan';
            ledColor = 'bg-brand-cyan';
            activeStage = 5; // Recharging
          } else if (amb.status === 'Idle') {
            statusBadge = 'bg-gray-800 border-gray-700 text-gray-300';
            ledColor = 'bg-gray-400';
            activeStage = 6; // Available
          }

          const targetNode = amb.target_node_id 
            ? activeData.nodes.find(n => n.id === amb.target_node_id)?.name 
            : null;

          const stages = ['Assigned', 'Travelling', 'Charging Node', 'Returning', 'Docking', 'Recharging', 'Available'];

          return (
            <div key={amb.id} className="p-5 rounded-xl border border-gray-800 bg-brand-panel glass-panel flex flex-col gap-4 font-mono relative overflow-hidden">
              
              {/* Animated Background effect if active */}
              {activeStage > 0 && activeStage < 5 && (
                <div className="absolute inset-0 bg-brand-blue/5 animate-pulse pointer-events-none"></div>
              )}

              <div className="flex justify-between items-center border-b border-gray-800 pb-3 relative z-10">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${ledColor} animate-pulse`}></div>
                  <div>
                    <h2 className="text-sm font-bold text-white tracking-wide">{amb.name}</h2>
                    <span className="text-[10px] text-gray-500 uppercase">{amb.id}</span>
                  </div>
                </div>
                <div className={`px-2 py-1 border rounded text-[10px] font-bold uppercase ${statusBadge}`}>
                  {amb.status}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 relative z-10">
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] text-gray-500 flex items-center gap-1"><Battery className="w-3 h-3"/> SOC / Payload</span>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-brand-green">{(amb.current_energy ?? 0).toFixed(1)} kWh</span>
                    <span className="text-xs text-brand-green">{soc.toFixed(0)}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-green" style={{ width: `${soc}%` }}></div>
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <span className="text-[10px] text-gray-500 flex items-center gap-1"><Zap className="w-3 h-3"/> Delivered Energy</span>
                  <span className="text-sm font-bold text-brand-blue">{(amb.energy_delivered ?? 0).toFixed(1)} kWh</span>
                </div>
              </div>

              {/* Active Mission Details */}
              <div className="bg-gray-900/50 p-3 rounded-lg border border-gray-800 relative z-10">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-[10px] text-gray-400">CURRENT MISSION</span>
                  {amb.eta_minutes > 0 && (
                    <span className="text-[10px] text-brand-amber font-bold flex items-center gap-1">
                      <Clock className="w-3 h-3" /> ETA {(amb.eta_minutes ?? 0).toFixed(0)} MIN
                    </span>
                  )}
                </div>
                <p className="text-xs text-white h-8 overflow-hidden">
                  {amb.current_mission || 'Standby at Base Station'}
                </p>
                {targetNode && (
                  <div className="flex items-center gap-1 mt-2 text-[10px] text-brand-blue font-bold bg-brand-blue/10 w-fit px-2 py-1 rounded">
                    <MapPin className="w-3 h-3" /> TARGET: {targetNode.toUpperCase()}
                  </div>
                )}
                
                {/* Travel Progress Bar if Dispatched */}
                {amb.status === 'Dispatched' && (
                  <div className="mt-3 relative">
                    <div className="flex justify-between text-[9px] text-gray-500 mb-1">
                      <span>BASE</span>
                      <Truck className="w-3 h-3 text-brand-blue animate-pulse absolute -top-4" style={{ left: `${amb.progress || 10}%` }} />
                      <span>TARGET</span>
                    </div>
                    <div className="w-full h-1 bg-gray-800 rounded-full overflow-hidden">
                      <div className="h-full bg-brand-blue animate-power-flow" style={{ width: `${amb.progress || 10}%` }}></div>
                    </div>
                  </div>
                )}

                {/* Charging Animation if Charging Node */}
                {amb.status === 'Charging Node' && (
                  <div className="mt-3 flex items-center justify-center gap-2 text-brand-green text-[10px] font-bold">
                    <Zap className="w-4 h-4 animate-pulse" /> DISCHARGING TO GRID...
                  </div>
                )}
              </div>

              {/* Mission Timeline */}
              <div className="mt-2 relative z-10">
                <span className="text-[9px] text-gray-500 mb-2 block">MISSION PLAYBACK TIMELINE</span>
                <div className="flex items-center justify-between text-[8px] uppercase text-gray-600">
                  {stages.map((stage, idx) => (
                    <div key={idx} className="flex flex-col items-center gap-1 w-12 text-center">
                      <div className={`w-2 h-2 rounded-full ${idx <= activeStage ? 'bg-brand-blue shadow-glow-blue' : 'bg-gray-800'}`}></div>
                      <span className={idx === activeStage ? 'text-white font-bold' : ''}>{stage}</span>
                    </div>
                  ))}
                </div>
                {/* Connecting Line */}
                <div className="absolute top-5 left-6 right-6 h-px bg-gray-800 -z-10"></div>
                <div className="absolute top-5 left-6 h-px bg-brand-blue transition-all duration-500 -z-10" style={{ width: `${(activeStage / (stages.length - 1)) * 100}%` }}></div>
              </div>

            </div>
          );
        })}
      </div>
    </div>
  );
}

