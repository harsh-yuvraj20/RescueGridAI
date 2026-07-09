import React, { useEffect, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { Terminal, Cpu } from 'lucide-react';

export default function OperationsTerminal() {
  const { activeData } = useApp();
  const logContainerRef = useRef(null);

  useEffect(() => {
    const container = logContainerRef.current;
    if (!container) return;
    container.scrollTop = container.scrollHeight;
  }, [activeData?.recent_logs]);

  if (!activeData) return null;

  return (
    <div className="glass-panel rounded-xl border border-gray-800 flex flex-col h-full overflow-hidden">
      <div className="bg-gray-900/50 p-3 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Terminal className="w-5 h-5 text-gray-400" />
          <h2 className="font-bold text-white tracking-widest text-sm uppercase">Live Operations Terminal</h2>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-brand-green led-green animate-pulse"></div>
          <span className="text-[10px] text-gray-500 font-mono uppercase">Streaming</span>
        </div>
      </div>

      <div
        ref={logContainerRef}
        className="p-3 flex-1 overflow-y-auto bg-gray-950 font-mono text-[11px] leading-relaxed flex flex-col gap-1.5 custom-scrollbar"
      >
        {(activeData.recent_logs ?? []).map((log, idx) => {
          const msg = log.message ?? '';
          const isAI = msg.includes('AI') || msg.includes('Optimization');
          const isCritical = msg.includes('CRITICAL') || log.grid_status === 'Unstable';
          
          let colorClass = 'text-gray-400';
          if (isAI) colorClass = 'text-brand-blue';
          if (isCritical) colorClass = 'text-brand-red';

          return (
            <div key={idx} className="flex gap-3 pb-1 border-b border-gray-900/50">
              <span className="text-gray-600 w-12 shrink-0">T-{log.step}</span>
              <div className="flex flex-col">
                <span className={colorClass}>
                  {isAI && <Cpu className="inline w-3 h-3 mr-1" />}
                  {msg}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
