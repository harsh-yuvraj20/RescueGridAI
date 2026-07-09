import React from 'react';
import { useApp } from '../context/AppContext';
import { CheckCircle2, AlertTriangle, Calculator } from 'lucide-react';

export default function PhysicsValidationPanel() {
  const { validationMetrics } = useApp();

  if (!validationMetrics) return null;

  const sysEff = validationMetrics.system_efficiency_pct ?? 0;
  const avgCf = validationMetrics.avg_capacity_factor ?? 0;
  const critLoad = validationMetrics.critical_load_served_pct ?? 0;
  const capFactors = validationMetrics.capacity_factors ?? {};

  return (
    <div className="glass-panel rounded-xl border border-gray-800 flex flex-col h-full">
      <div className="bg-gray-900/50 p-3 border-b border-gray-800 flex items-center gap-3">
        <Calculator className="w-5 h-5 text-brand-blue" />
        <h2 className="font-bold text-white tracking-widest text-sm uppercase">Physics Engine Validation</h2>
      </div>

      <div className="p-4 flex flex-col gap-3 flex-1 overflow-y-auto">
        <div className="flex items-center justify-between p-2 rounded bg-gray-900/50 border border-gray-800">
          <span className="text-xs text-gray-400 font-mono">System Efficiency (Losses)</span>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-white">{sysEff.toFixed(1)}%</span>
            {sysEff > 95 ? 
              <CheckCircle2 className="w-4 h-4 text-brand-green" /> : 
              <AlertTriangle className="w-4 h-4 text-brand-amber" />}
          </div>
        </div>

        <div className="flex items-center justify-between p-2 rounded bg-gray-900/50 border border-gray-800">
          <span className="text-xs text-gray-400 font-mono">Avg Capacity Factor</span>
          <span className="text-sm font-bold text-brand-blue">{(avgCf * 100).toFixed(1)}%</span>
        </div>

        <div className="flex items-center justify-between p-2 rounded bg-gray-900/50 border border-gray-800">
          <span className="text-xs text-gray-400 font-mono">Critical Load Served</span>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-white">{critLoad.toFixed(1)}%</span>
            {critLoad === 100 ? 
              <CheckCircle2 className="w-4 h-4 text-brand-green" /> : 
              <AlertTriangle className="w-4 h-4 text-brand-red led-red" />}
          </div>
        </div>

        <div className="flex flex-col gap-1 mt-2">
          <span className="text-[10px] text-gray-500 font-mono uppercase border-b border-gray-800 pb-1">Generator CF Breakdown</span>
          {Object.entries(capFactors).map(([name, cf]) => (
            <div key={name} className="flex justify-between items-center py-1">
              <span className="text-xs text-gray-400">{name}</span>
              <span className="text-xs font-mono text-white">{((cf ?? 0) * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
