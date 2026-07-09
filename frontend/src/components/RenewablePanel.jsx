import React from 'react';
import { useApp } from '../context/AppContext';
import { Sun, Wind, Battery, Zap, ArrowDown, Activity } from 'lucide-react';

export default function RenewablePanel() {
  const { activeData, validationMetrics } = useApp();

  if (!activeData) return null;

  const nodes = activeData.nodes;
  
  const solarGen = nodes.filter(n => n.type === 'Solar Farm').reduce((acc, n) => acc + (n.generation_output ?? 0), 0);
  const windGen = nodes.filter(n => n.type === 'Wind Farm').reduce((acc, n) => acc + (n.generation_output ?? 0), 0);
  
  const batteries = nodes.filter(n => n.type === 'Battery Station');
  const batteryOutput = activeData.metrics.battery_discharging_power ?? 0;
  
  const totalBatteryStorage = batteries.reduce((acc, n) => acc + (n.current_storage ?? 0), 0);
  const totalBatteryCapacity = batteries.reduce((acc, n) => acc + (n.max_capacity ?? 0), 0);
  const batterySoc = totalBatteryCapacity > 0 ? (totalBatteryStorage / totalBatteryCapacity) * 100 : 0;

  const totalGen = solarGen + windGen;
  
  const consumers = nodes.filter(n => ['Hospital', 'Water Plant', 'Telecom Tower'].includes(n.type));
  const totalDemand = consumers.reduce((acc, n) => acc + (n.current_demand ?? 0), 0);

  const curtailment = activeData.metrics.curtailed_energy ?? Math.max(0, totalGen - totalDemand - batteries.reduce((acc,n)=>acc+((n.max_capacity ?? 0) - (n.current_storage ?? 0)), 0));
  const deficit = activeData.metrics.renewable_deficit ?? Math.max(0, totalDemand - totalGen - batteryOutput);

  return (
    <div className="glass-panel rounded-xl border border-gray-800 flex flex-col overflow-hidden h-full">
      <div className="bg-gray-900/50 p-3 border-b border-gray-800 flex items-center gap-3">
        <Zap className="w-5 h-5 text-brand-green" />
        <h2 className="font-bold text-white tracking-widest text-sm uppercase">Live Renewable Operations</h2>
      </div>

      <div className="p-4 grid grid-cols-2 gap-4">
        {/* Solar */}
        <div className="bg-gray-900/30 border border-gray-800 rounded-lg p-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${solarGen > 0 ? 'bg-amber-500/20 text-amber-400 led-amber' : 'bg-gray-800 text-gray-500'}`}>
              <Sun className={`w-5 h-5 ${solarGen > 0 ? 'animate-[spin_10s_linear_infinite]' : ''}`} />
            </div>
            <div className="flex flex-col">
              <span className="text-xs text-gray-400 font-mono">SOLAR GEN</span>
              <span className="font-bold text-white text-lg">{solarGen.toFixed(1)} kW</span>
            </div>
          </div>
        </div>

        {/* Wind */}
        <div className="bg-gray-900/30 border border-gray-800 rounded-lg p-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${windGen > 0 ? 'bg-brand-blue/20 text-brand-blue led-blue' : 'bg-gray-800 text-gray-500'}`}>
              <Wind className={`w-5 h-5 ${windGen > 0 ? 'animate-[spin_2s_linear_infinite]' : ''}`} />
            </div>
            <div className="flex flex-col">
              <span className="text-xs text-gray-400 font-mono">WIND GEN</span>
              <span className="font-bold text-white text-lg">{windGen.toFixed(1)} kW</span>
            </div>
          </div>
        </div>

        {/* Battery */}
        <div className="bg-gray-900/30 border border-gray-800 rounded-lg p-3 flex items-center justify-between col-span-2">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-brand-green/20 text-brand-green led-green">
              <Battery className="w-5 h-5" />
            </div>
            <div className="flex flex-col">
              <span className="text-xs text-gray-400 font-mono">BATTERY OUTPUT / SOC</span>
              <div className="flex items-baseline gap-2">
                <span className="font-bold text-white text-lg">{batteryOutput.toFixed(1)} kW</span>
                <span className="text-sm font-bold text-brand-green">({batterySoc.toFixed(1)}%)</span>
              </div>
            </div>
          </div>
          <div className="w-24 h-2 bg-gray-800 rounded-full overflow-hidden">
            <div className="h-full bg-brand-green" style={{ width: `${batterySoc}%` }}></div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 border-t border-gray-800 bg-gray-900/20 divide-x divide-gray-800">
        <div className="p-3 flex flex-col items-center justify-center text-center">
          <span className="text-[10px] text-gray-500 font-mono uppercase">Coverage</span>
          <span className="font-bold text-brand-green">{validationMetrics?.renewable_penetration_pct ?? activeData.metrics.renewable_penetration ?? 0}%</span>
        </div>
        <div className="p-3 flex flex-col items-center justify-center text-center">
          <span className="text-[10px] text-gray-500 font-mono uppercase">Utilization</span>
          <span className="font-bold text-brand-blue">{validationMetrics?.renewable_utilization_pct ?? activeData.metrics.renewable_utilization ?? 0}%</span>
        </div>
        <div className="p-3 flex flex-col items-center justify-center text-center">
          <span className="text-[10px] text-gray-500 font-mono uppercase">Curtailment</span>
          <span className="font-bold text-brand-amber">{curtailment.toFixed(1)} kW</span>
        </div>
        <div className="p-3 flex flex-col items-center justify-center text-center">
          <span className="text-[10px] text-gray-500 font-mono uppercase">Deficit</span>
          <span className={`font-bold ${deficit > 0 ? 'text-brand-red' : 'text-gray-400'}`}>{deficit.toFixed(1)} kW</span>
        </div>
      </div>
    </div>
  );
}
