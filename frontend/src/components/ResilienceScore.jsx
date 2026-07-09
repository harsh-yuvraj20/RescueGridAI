import React from 'react';
import { useApp } from '../context/AppContext';
import { Shield, TrendingUp, TrendingDown } from 'lucide-react';

export default function ResilienceScore() {
  const { activeData, validationMetrics } = useApp();

  if (!activeData) return null;

  // Use validationMetrics for a more accurate resilience if available, else derive from activeData
  const reliability = validationMetrics?.grid_reliability_pct ?? (
    (activeData.nodes.filter(n => ['Hospital', 'Water Plant', 'Telecom Tower'].includes(n.type) && n.status !== 'Offline').length / 
    Math.max(1, activeData.nodes.filter(n => ['Hospital', 'Water Plant', 'Telecom Tower'].includes(n.type)).length)) * 100
  );
  
  const batteryHealth = validationMetrics?.battery_health_avg_pct ?? activeData?.metrics?.battery_soh ?? 100;
  const renewablePenetration = validationMetrics?.renewable_penetration_pct ?? activeData?.metrics?.renewable_penetration ?? 0;
  
  // Weights for resilience
  const wRel = 0.5;
  const wBat = 0.25;
  const wRen = 0.25;
  
  const score = (reliability * wRel) + (batteryHealth * wBat) + (Math.min(renewablePenetration, 100) * wRen);

  let statusColor = 'text-brand-green';
  let glowClass = 'led-green';
  let label = 'OPTIMAL';
  if (score < 80) { statusColor = 'text-brand-blue'; glowClass = 'led-blue'; label = 'STABLE'; }
  if (score < 60) { statusColor = 'text-brand-amber'; glowClass = 'led-amber'; label = 'WARNING'; }
  if (score < 40) { statusColor = 'text-brand-red'; glowClass = 'led-red'; label = 'CRITICAL'; }

  // Draw circular SVG gauge
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="glass-panel rounded-xl border border-gray-800 p-4 flex flex-col items-center relative overflow-hidden">
      <Shield className={`absolute top-4 right-4 w-6 h-6 opacity-20 ${statusColor}`} />
      <h2 className="font-bold text-gray-400 tracking-widest text-xs uppercase mb-4 self-start">Grid Resilience Index</h2>
      
      <div className="relative flex items-center justify-center mb-4">
        <svg width="120" height="120" className="transform -rotate-90">
          {/* Background circle */}
          <circle
            cx="60"
            cy="60"
            r={radius}
            stroke="rgba(255,255,255,0.05)"
            strokeWidth="10"
            fill="none"
          />
          {/* Progress circle */}
          <circle
            cx="60"
            cy="60"
            r={radius}
            stroke="currentColor"
            strokeWidth="10"
            fill="none"
            className={`${statusColor} transition-all duration-1000 ease-out`}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
          />
        </svg>
        <div className={`absolute inset-0 flex flex-col items-center justify-center rounded-full ${glowClass} m-4 opacity-10 blur-xl`}></div>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-3xl font-bold font-mono ${statusColor}`}>{Math.round(score)}</span>
        </div>
      </div>
      
      <div className="w-full grid grid-cols-3 gap-2 text-center border-t border-gray-800 pt-3">
        <div className="flex flex-col">
          <span className="text-[9px] text-gray-500 font-mono uppercase">Reliability</span>
          <span className="text-xs font-bold text-white">{reliability.toFixed(1)}%</span>
        </div>
        <div className="flex flex-col border-x border-gray-800">
          <span className="text-[9px] text-gray-500 font-mono uppercase">Renewables</span>
          <span className="text-xs font-bold text-white">{renewablePenetration.toFixed(1)}%</span>
        </div>
        <div className="flex flex-col">
          <span className="text-[9px] text-gray-500 font-mono uppercase">Battery</span>
          <span className="text-xs font-bold text-white">{batteryHealth.toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
}
