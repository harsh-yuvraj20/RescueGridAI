import React from 'react';
import { useApp } from '../context/AppContext';
import { Activity, Server, Database, Brain, Cpu, Wind, Truck } from 'lucide-react';

export default function SystemHealthPanel() {
  const { activeData } = useApp();

  if (!activeData) return null;

  const m = activeData.metrics;
  
  const systems = [
    { name: 'Physics Engine', status: 'ONLINE', icon: Cpu },
    { name: 'AI Decision Engine', status: 'ONLINE', icon: Brain },
    { name: 'Renewable Manager', status: 'ONLINE', icon: Wind },
    { name: 'Battery Authority', status: 'ONLINE', icon: Database },
    { name: 'Mission Queue', status: activeData.ambulances.length > 0 ? 'ACTIVE' : 'IDLE', icon: Truck },
    { name: 'Simulation Loop', status: `TICK ${activeData?.recent_logs?.[0]?.step ?? '...'}`, icon: Activity },
  ];

  return (
    <div className="glass-panel rounded-xl border border-gray-800 p-4">
      <div className="flex items-center gap-2 mb-4 border-b border-gray-800 pb-2">
        <Server className="w-4 h-4 text-gray-400" />
        <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">System Health</h3>
      </div>
      
      <div className="grid grid-cols-2 gap-3">
        {systems.map((sys, idx) => (
          <div key={idx} className="flex items-center justify-between bg-gray-900/50 p-2 rounded border border-gray-800">
            <div className="flex items-center gap-2">
              <sys.icon className="w-3.5 h-3.5 text-gray-500" />
              <span className="text-[10px] text-gray-400 font-mono">{sys.name}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className={`w-1.5 h-1.5 rounded-full ${sys.status !== 'IDLE' ? 'bg-brand-green led-green' : 'bg-gray-500'}`}></div>
              <span className={`text-[9px] font-bold ${sys.status !== 'IDLE' ? 'text-brand-green' : 'text-gray-500'}`}>
                {sys.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
