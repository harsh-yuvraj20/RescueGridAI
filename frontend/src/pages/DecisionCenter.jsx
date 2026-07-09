import React from 'react';
import { useApp } from '../context/AppContext';
import { 
  BrainCircuit, 
  Clock, 
  Zap, 
  ShieldCheck, 
  Hourglass,
  ArrowRight,
  Target,
  Leaf,
  Banknote,
  AlertTriangle,
  Activity
} from 'lucide-react';

export default function DecisionCenter() {
  const { activeData, completeDecision } = useApp();

  if (!activeData) return null;

  const criticalNodes = (activeData?.nodes ?? []).filter(n => ['Hospital', 'Water Plant', 'Telecom Tower'].includes(n.type));

  const scoredNodes = criticalNodes.map(node => {
    const soc = (node.max_capacity ?? 0) > 0 ? ((node.current_storage ?? 0) / node.max_capacity) : 0;
    const weight = node.criticality === 'High' ? 100 : (node.criticality === 'Medium' ? 50 : 20);
    const survFactor = Math.max(0, 72 - (node.survival_hours ?? 0)) * 2.5;
    const score = (1.0 - soc) * weight + survFactor;
    return { ...node, score };
  });

  scoredNodes.sort((a, b) => b.score - a.score);

  const pendingDecisions = (activeData?.recent_decisions ?? []).filter(d => d.status === 'Pending');
  const actionHistory = (activeData?.recent_decisions ?? []).filter(d => d.status !== 'Pending');
  const latestDecision = pendingDecisions[0] || actionHistory[0];

  let parsedStrategies = [];
  if (latestDecision?.optimization_strategies) {
    try {
      parsedStrategies = JSON.parse(latestDecision.optimization_strategies);
    } catch (e) { }
  }

  const renderStrategyScores = (dec) => {
    if (!dec.cost_score || dec.cost_score === 0) return null;
    return (
      <div className="flex items-center gap-4 mt-2 pt-2 border-t border-gray-800/50">
        <div className="flex items-center gap-1 text-[9px] text-gray-400 font-mono">
          <Banknote className="w-3 h-3 text-brand-amber" />
          <span>COST: {(dec.cost_score ?? 0).toFixed(1)}</span>
        </div>
        <div className="flex items-center gap-1 text-[9px] text-gray-400 font-mono">
          <Target className="w-3 h-3 text-brand-blue" />
          <span>RELIABILITY: {(dec.reliability_score ?? 0).toFixed(1)}</span>
        </div>
        <div className="flex items-center gap-1 text-[9px] text-gray-400 font-mono">
          <Leaf className="w-3 h-3 text-brand-green" />
          <span>SUSTAINABILITY: {(dec.sustainability_score ?? 0).toFixed(1)}</span>
        </div>
      </div>
    );
  };

  const riskStages = ['Observation', 'Warning', 'Critical', 'Emergency', 'Collapse'];
  
  const getRiskStage = (node) => {
    if (node.status === 'Offline') return 4; // Collapse
    if (node.status === 'Emergency' || node.status === 'Critical' || (node.survival_hours ?? 999) < 2) return 3; // Emergency
    if ((node.survival_hours ?? 999) < 12) return 2; // Critical
    if (node.status === 'Warning' || (node.survival_hours ?? 999) < 48) return 1; // Warning
    return 0; // Observation
  };

  return (
    <div className="flex flex-col gap-6 h-full">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-800 pb-4 shrink-0">
        <div>
          <h1 className="text-xl font-extrabold tracking-wider text-white font-mono uppercase flex items-center gap-2">
            <BrainCircuit className="w-5 h-5 text-brand-green" />
            AI Decision Operations
          </h1>
          <p className="text-xs text-gray-500 font-mono">
            MULTI-STRATEGY OPTIMIZATION, EXPLAINABLE LOGISTICS, PREDICTIVE RISK
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-0">
        
        {/* Left Column: Predictive Risk & Priority Queue */}
        <div className="lg:col-span-7 flex flex-col gap-4 h-full overflow-hidden">
          
          {/* Predictive Risk Panel */}
          <div className="p-4 rounded-xl border border-gray-800 bg-brand-panel glass-panel shrink-0">
            <h3 className="text-xs uppercase font-mono tracking-widest text-brand-amber font-bold mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" /> Predictive Risk Tracking
            </h3>
            <div className="grid grid-cols-5 gap-2 text-center border-b border-gray-800 pb-2 mb-2">
              {riskStages.map((stage, idx) => (
                <span key={idx} className={`text-[9px] uppercase font-bold ${idx === 4 ? 'text-brand-red' : idx === 3 ? 'text-orange-500' : idx === 2 ? 'text-brand-amber' : idx === 1 ? 'text-yellow-400' : 'text-brand-green'}`}>
                  {stage}
                </span>
              ))}
            </div>
            <div className="flex flex-col gap-2 max-h-[120px] overflow-y-auto custom-scrollbar">
              {scoredNodes.slice(0, 5).map(node => {
                const stageIdx = getRiskStage(node);
                return (
                  <div key={node.id} className="grid grid-cols-5 gap-2 items-center">
                    <span className="col-span-1 text-[10px] text-white font-mono truncate px-1">{node.name}</span>
                    <div className="col-span-4 relative flex items-center h-4">
                      {/* Track line */}
                      <div className="absolute left-0 right-0 h-px bg-gray-800"></div>
                      {/* Active point */}
                      <div 
                        className={`absolute w-3 h-3 rounded-full top-1/2 -translate-y-1/2 -ml-1.5 transition-all duration-1000 ${stageIdx === 4 ? 'bg-brand-red led-red' : stageIdx === 3 ? 'bg-orange-500 shadow-glow-red' : stageIdx === 2 ? 'bg-brand-amber led-amber' : stageIdx === 1 ? 'bg-yellow-400' : 'bg-brand-green led-green'}`}
                        style={{ left: `${(stageIdx / 4) * 100}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="p-4 rounded-xl border border-gray-800 bg-brand-panel glass-panel flex-1 flex flex-col min-h-0">
            <h3 className="text-xs uppercase font-mono tracking-widest text-gray-400 mb-2 flex items-center justify-between shrink-0">
              <span>Consumer Priority Queue</span>
              <span className="text-[10px] text-brand-green font-bold">UPDATED REAL-TIME</span>
            </h3>

            <div className="overflow-y-auto custom-scrollbar flex-1">
              <table className="w-full text-left font-mono text-[11px] border-collapse">
                <thead className="sticky top-0 bg-brand-panel z-10">
                  <tr className="border-b border-gray-800 text-gray-500 pb-2">
                    <th className="py-2 font-semibold">RANK</th>
                    <th className="py-2 font-semibold">NODE</th>
                    <th className="py-2 font-semibold text-right">SOC %</th>
                    <th className="py-2 font-semibold text-right">EXPECTED FAILURE</th>
                    <th className="py-2 font-semibold text-right">AI SCORE</th>
                  </tr>
                </thead>
                <tbody>
                  {scoredNodes.map((node, index) => {
                    const soc = node.max_capacity > 0 ? ((node.current_storage / node.max_capacity) * 100) : 0;
                    
                    let statusColor = 'text-brand-green';
                    if (node.status === 'Warning') statusColor = 'text-brand-amber';
                    if (node.status === 'Critical') statusColor = 'text-brand-red';
                    if (node.status === 'Emergency') statusColor = 'text-orange-500';
                    if (node.status === 'Offline') statusColor = 'text-gray-500';

                    const failureTime = node.status === 'Offline' 
                      ? 'COLLAPSED' 
                      : ((node.survival_hours ?? 0) >= 336.0 ? '>14 DAYS' : 
                         (node.survival_hours ?? 0) >= 48.0 ? `${((node.survival_hours ?? 0) / 24).toFixed(1)} DAYS` :
                         `${(node.survival_hours ?? 0).toFixed(1)} HOURS`);

                    return (
                      <tr key={node.id} className="border-b border-gray-800/40 hover:bg-gray-900/30 transition">
                        <td className="py-2">
                          <span className={`flex items-center justify-center w-5 h-5 rounded text-[10px] font-bold ${
                            index === 0 ? 'bg-brand-red/20 text-brand-red' : 
                            (index === 1 ? 'bg-brand-amber/20 text-brand-amber' : 'bg-gray-800 text-gray-400')
                          }`}>
                            #{index + 1}
                          </span>
                        </td>
                        <td className="py-2 pr-2">
                          <div className="flex flex-col">
                            <span className="font-bold text-white truncate w-32">{node.name}</span>
                            <span className="text-[9px] text-gray-500">{node.type}</span>
                          </div>
                        </td>
                        <td className="py-2 text-right">
                          <span className={`font-bold ${statusColor}`}>{soc.toFixed(0)}%</span>
                        </td>
                        <td className="py-2 text-right">
                          <span className={`font-bold ${(node.survival_hours ?? 999) < 12.0 ? 'text-brand-red animate-pulse' : 'text-gray-300'}`}>
                            {failureTime}
                          </span>
                        </td>
                        <td className="py-2 text-right font-bold text-brand-blue">
                          {node.score.toFixed(0)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column: AI Insights & Optimization */}
        <div className="lg:col-span-5 flex flex-col gap-4 h-full overflow-hidden">
          
          {/* Renewable Optimization Panel */}
          {latestDecision && (
            <div className="p-4 rounded-xl border border-brand-green/30 bg-brand-green/5 glass-panel shrink-0">
              <h3 className="text-xs uppercase font-mono tracking-widest text-brand-green font-bold flex items-center gap-1.5 mb-2">
                <Activity className="w-4 h-4" />
                Selected Optimization Strategy
              </h3>
              <div className="flex flex-col gap-2">
                <div className="flex justify-between items-center text-xs text-white">
                  <span className="font-mono text-gray-400">Strategy</span>
                  <span className="font-bold tracking-wide uppercase text-brand-green">{latestDecision.selected_strategy || latestDecision.type}</span>
                </div>
                {parsedStrategies.length > 0 && (
                  <div className="grid grid-cols-3 gap-2 mt-2">
                    {parsedStrategies.map((s, idx) => (
                      <div key={idx} className={`p-2 border rounded flex flex-col items-center justify-center text-center ${s.strategy === latestDecision.selected_strategy ? 'border-brand-green bg-brand-green/20' : 'border-gray-800 bg-gray-900/50'}`}>
                        <span className="text-[9px] text-gray-400 uppercase font-mono mb-1">{s.strategy}</span>
                        <span className="text-[10px] font-bold text-white whitespace-nowrap">C: {(s.cost_score ?? 0).toFixed(0)}</span>
                        <span className="text-[10px] font-bold text-brand-blue whitespace-nowrap">R: {(s.reliability_score ?? 0).toFixed(0)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* AI Thinking Panel */}
          <div className="p-4 rounded-xl border border-brand-blue/30 bg-brand-blue/5 glass-panel flex-1 flex flex-col min-h-0">
            <h3 className="text-xs uppercase font-mono tracking-widest text-brand-blue font-bold flex items-center gap-1.5 border-b border-brand-blue/20 pb-2 mb-3 shrink-0">
              <Zap className="w-4 h-4" />
              Explainable AI Timeline
            </h3>

            <div className="flex flex-col gap-3 overflow-y-auto custom-scrollbar flex-1 pr-1">
              {pendingDecisions.length === 0 && actionHistory.length === 0 ? (
                <div className="text-center py-6 text-gray-500 font-mono text-[10px]">
                  ALL SYSTEMS NOMINAL. NO DECISIONS LOGGED.
                </div>
              ) : (
                [...pendingDecisions, ...actionHistory].map(dec => (
                  <div key={dec.id} className="p-3 bg-gray-900/70 border border-gray-800 rounded-lg flex flex-col gap-2 font-mono text-xs">
                    <div className="flex justify-between items-center text-[9px] text-gray-500">
                      <span className={`uppercase font-bold ${dec.status === 'Pending' ? 'text-brand-amber' : 'text-brand-blue'}`}>
                        {dec.status === 'Pending' ? '[PENDING APPROVAL]' : '[EXECUTED]'} {dec.type}
                      </span>
                      <div className="flex gap-2">
                        {dec.confidence_score != null && (
                          <span className={`px-1.5 rounded ${(dec.confidence_score ?? 0) > 90 ? 'bg-brand-green/20 text-brand-green' : 'bg-brand-amber/20 text-brand-amber'}`}>
                            CONF: {(dec.confidence_score ?? 0).toFixed(1)}%
                          </span>
                        )}
                      </div>
                    </div>
                    
                    <div className="text-[11px] text-gray-300 leading-normal border-l-2 border-brand-blue/50 pl-3 space-y-2 py-1">
                      {dec.explanation ? (
                        dec.explanation.split(/\[OBSERVATION\]|\[EVALUATION\]|\[ACTION\]/).filter(Boolean).map((part, i) => {
                          const labels = ["OBSERVATION", "EVALUATION", "ACTION"];
                          return (
                            <div key={i} className="flex flex-col gap-0.5 relative">
                              <span className="text-[9px] text-brand-blue font-bold tracking-widest uppercase">
                                {labels[i]}
                                {/* Timeline dot */}
                                <div className="absolute -left-[17px] top-1 w-2 h-2 rounded-full bg-brand-blue"></div>
                              </span>
                              <span className="text-gray-400">{part.trim()}</span>
                            </div>
                          )
                        })
                      ) : (
                        <p>{dec.description}</p>
                      )}
                    </div>
                    {renderStrategyScores(dec)}
                    {dec.status === 'Pending' && (
                      <button
                        onClick={() => completeDecision(dec.id)}
                        className="mt-2 flex items-center justify-center gap-1.5 py-1.5 px-3 bg-brand-green/10 hover:bg-brand-green/20 border border-brand-green/30 text-brand-green hover:text-white rounded text-[10px] font-extrabold transition uppercase"
                      >
                        <span>AUTHORIZE EXECUTION</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
