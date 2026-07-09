import React from 'react';
import { ArrowRight, BatteryCharging, Factory, RadioTower, Zap } from 'lucide-react';
import { useApp } from '../context/AppContext';

function FlowCard({ icon: Icon, label, value, tone = 'blue' }) {
  const tones = {
    green: 'border-emerald-500/30 bg-emerald-500/5 text-emerald-400',
    blue: 'border-blue-500/30 bg-blue-500/5 text-blue-400',
    amber: 'border-amber-500/30 bg-amber-500/5 text-amber-400',
    red: 'border-red-500/30 bg-red-500/5 text-red-400',
  };

  return (
    <div className={`flex min-h-[112px] min-w-0 items-center gap-4 rounded-xl border p-4 ${tones[tone]}`}>
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-current/20 bg-black/20">
        <Icon className="h-5 w-5" />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500">{label}</p>
        <p className="mt-1 break-words text-lg font-extrabold text-current">{value}</p>
      </div>
    </div>
  );
}

export default function EnergyFlow() {
  const { activeData } = useApp();
  if (!activeData?.nodes) return null;

  const nodes = activeData.nodes ?? [];
  const totalGen = nodes
    .filter(node => ['Solar Farm', 'Wind Farm'].includes(node.type))
    .reduce((sum, node) => sum + (node.generation_output ?? 0), 0);
  const totalDemand = nodes
    .filter(node => ['Hospital', 'Water Plant', 'Telecom Tower'].includes(node.type))
    .reduce((sum, node) => sum + (node.current_demand ?? 0), 0);
  const charging = activeData.metrics?.battery_charging_power ?? Math.max(0, totalGen - totalDemand);
  const discharging = activeData.metrics?.battery_discharging_power ?? 0;
  const batteryMode = discharging > 0 ? 'Discharging' : charging > 0 ? 'Charging' : 'Standby';
  const batteryPower = Math.max(charging, discharging);

  return (
    <div className="glass-panel h-full rounded-xl border border-gray-800 p-5">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-gray-800 pb-4">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-gray-300">Physics-Aware Energy Flow</h3>
          <p className="mt-1 text-[10px] font-mono text-gray-600">Live generation, storage and demand routing</p>
        </div>
        <span className="rounded-full border border-brand-green/30 bg-brand-green/10 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-brand-green">
          {batteryMode}
        </span>
      </div>

      <div className="grid grid-cols-1 items-center gap-3 sm:grid-cols-2 xl:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr]">
        <FlowCard icon={Factory} label="Generators" value={`${totalGen.toFixed(0)} kW`} tone="green" />
        <ArrowRight className="hidden h-5 w-5 text-gray-700 xl:block" />
        <FlowCard icon={Zap} label="Renewable Pool" value={`${Math.min(totalGen, totalDemand + charging).toFixed(0)} kW`} tone="blue" />
        <ArrowRight className="hidden h-5 w-5 text-gray-700 xl:block" />
        <FlowCard icon={BatteryCharging} label="Battery Stations" value={`${batteryMode} · ${batteryPower.toFixed(0)} kW`} tone="amber" />
        <ArrowRight className="hidden h-5 w-5 text-gray-700 xl:block" />
        <FlowCard icon={RadioTower} label="Consumers" value={`${totalDemand.toFixed(0)} kW`} tone="red" />
      </div>
    </div>
  );
}
