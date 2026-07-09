import React from 'react';
import { useApp } from '../context/AppContext';
import { 
  Play, 
  Pause, 
  RotateCcw, 
  Volume2, 
  VolumeX, 
  FileDown, 
  Terminal,
  ChevronRight,
  ShieldCheck,
  AlertTriangle,
  Zap
} from 'lucide-react';

export default function Settings() {
  const { 
    data, 
    soundEnabled, 
    setSoundEnabled, 
    simSpeed, 
    controlSimulation, 
    exportPDFReport,
    startCycloneDemo
  } = useApp();

  if (!data) return null;

  const logs = data.recent_logs;

  return (
    <div className="flex flex-col gap-6">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-800 pb-4">
        <div>
          <h1 className="text-xl font-extrabold tracking-wider text-white font-mono uppercase flex items-center gap-2">
            <Terminal className="w-5 h-5 text-brand-green" />
            Grid Control Room
          </h1>
          <p className="text-xs text-gray-500 font-mono">
            ADMINISTRATIVE SCHEDULING, SIMULATION SPEED, AUDIO AND AUDITING SYSTEM
          </p>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Admin Controls Panel (Col 5) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <div className="p-5 rounded-xl border border-gray-800 bg-brand-panel glass-panel flex flex-col gap-5">
            <h3 className="text-xs uppercase font-mono tracking-widest text-gray-400 border-b border-gray-800 pb-2">
              Simulation Loop Controls
            </h3>

            {/* Loop state buttons */}
            <div className="flex gap-3">
              <button
                onClick={() => controlSimulation('start')}
                className="flex-1 flex items-center justify-center gap-2 py-3 bg-brand-green/10 hover:bg-brand-green/20 border border-brand-green/40 text-brand-green font-bold rounded-lg font-mono text-xs transition"
              >
                <Play className="w-4 h-4 fill-brand-green" />
                <span>RESUME TICK</span>
              </button>
              
              <button
                onClick={() => controlSimulation('pause')}
                className="flex-1 flex items-center justify-center gap-2 py-3 bg-brand-amber/10 hover:bg-brand-amber/20 border border-brand-amber/40 text-brand-amber font-bold rounded-lg font-mono text-xs transition"
              >
                <Pause className="w-4 h-4 fill-brand-amber" />
                <span>PAUSE TICK</span>
              </button>
            </div>

            {/* Speed selection */}
            <div className="flex flex-col gap-2 font-mono text-xs">
              <span className="text-gray-500 uppercase">Simulation Speed Multiplier</span>
              <div className="grid grid-cols-4 gap-2">
                {[1.0, 2.0, 5.0, 10.0].map(speed => (
                  <button
                    key={speed}
                    onClick={() => controlSimulation('speed', speed)}
                    className={`py-2 border rounded font-bold text-center transition ${
                      simSpeed === speed
                        ? 'border-brand-blue bg-brand-blue/15 text-white'
                        : 'border-gray-800 text-gray-400 hover:bg-gray-800'
                    }`}
                  >
                    {speed}x
                  </button>
                ))}
              </div>
            </div>

            {/* DEMO MODE OVERRIDE */}
            <div className="border-t border-gray-800 pt-4 flex flex-col gap-3 font-mono text-xs">
              <span className="text-gray-500 uppercase font-bold text-brand-cyan flex items-center gap-2">
                <Zap className="w-3 h-3" />
                Demonstration Sequence
              </span>
              <button
                onClick={() => startCycloneDemo()}
                className="flex items-center justify-center gap-2 py-3 bg-brand-cyan/10 hover:bg-brand-cyan/20 border border-brand-cyan/40 text-brand-cyan font-bold rounded-lg transition btn-glow-cyan"
              >
                <Play className="w-4 h-4" />
                <span>AUTO-RUN JUDGE DEMO MODE</span>
              </button>
            </div>

            {/* Reset / Hard Restart */}
            <div className="border-t border-gray-800 pt-4 flex flex-col gap-3 font-mono text-xs">
              <span className="text-gray-500 uppercase">Emergency Safety Protocols</span>
              <button
                onClick={() => controlSimulation('reset')}
                className="flex items-center justify-center gap-2 py-2.5 bg-brand-red/10 hover:bg-brand-red/20 border border-brand-red/40 text-brand-red font-bold rounded-lg transition"
              >
                <RotateCcw className="w-4 h-4" />
                <span>RESET ALL SYSTEMS & SEEDS</span>
              </button>
            </div>
          </div>

          {/* System Settings Card */}
          <div className="p-5 rounded-xl border border-gray-800 bg-brand-panel glass-panel flex flex-col gap-4 font-mono text-xs">
            <h3 className="text-xs uppercase tracking-widest text-gray-400 border-b border-gray-800 pb-2">
              System Operations
            </h3>

            {/* Sound FX Toggle */}
            <div className="flex justify-between items-center py-1">
              <div>
                <span className="font-bold text-white block">Cognitive Synthesizer</span>
                <span className="text-[10px] text-gray-500">Enable synthesized alarm acoustics</span>
              </div>
              <button
                onClick={() => setSoundEnabled(!soundEnabled)}
                className={`flex items-center gap-1.5 py-1.5 px-3 border rounded transition ${
                  soundEnabled 
                    ? 'border-brand-green/30 bg-brand-green/5 text-brand-green' 
                    : 'border-gray-800 text-gray-500 hover:text-gray-300'
                }`}
              >
                {soundEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
                <span>{soundEnabled ? 'ON' : 'OFF'}</span>
              </button>
            </div>

            {/* Export Audit Report */}
            <div className="flex justify-between items-center border-t border-gray-900 pt-3">
              <div>
                <span className="font-bold text-white block">Engineering Evaluation Document</span>
                <span className="text-[10px] text-gray-500">Compile and export PDF status logs</span>
              </div>
              <button
                onClick={exportPDFReport}
                className="flex items-center gap-1.5 py-1.5 px-3 border border-brand-blue/30 bg-brand-blue/10 hover:bg-brand-blue/20 text-brand-blue rounded font-bold transition"
              >
                <FileDown className="w-3.5 h-3.5" />
                <span>PDF REPORT</span>
              </button>
            </div>
          </div>
        </div>

        {/* Live Grid Logging Shell Console (Col 7) */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <div className="p-5 rounded-xl border border-gray-800 bg-black/80 font-mono text-xs flex flex-col gap-4 h-full min-h-[500px]">
            <div className="flex items-center justify-between border-b border-gray-900 pb-2 text-[10px] text-gray-500">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-brand-green led-green"></span>
                CORE TELEMETRY LOG SHELL
              </span>
              <span>STEP OFFSET: #{logs[0]?.step || 0}</span>
            </div>

            <div className="flex-1 overflow-y-auto flex flex-col gap-2.5 pr-2 font-mono">
              {logs.map((log, idx) => {
                let statusColor = 'text-brand-green';
                let Icon = ShieldCheck;
                if (log.grid_status === 'Down') {
                  statusColor = 'text-brand-red';
                  Icon = AlertTriangle;
                } else if (log.grid_status === 'Unstable') {
                  statusColor = 'text-brand-amber';
                  Icon = AlertTriangle;
                }

                return (
                  <div key={idx} className="flex gap-2 items-start text-[11px] leading-relaxed">
                    <ChevronRight className="w-3.5 h-3.5 text-gray-600 flex-shrink-0 mt-0.5" />
                    <div className="flex-1 flex flex-col gap-0.5">
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500">[{log.timestamp.split('T')[1].split('.')[0]}]</span>
                        <span className={`px-1 text-[8px] uppercase border rounded ${
                          log.grid_status === 'Down' ? 'border-brand-red/30 text-brand-red bg-brand-red/5' : 'border-brand-green/30 text-brand-green bg-brand-green/5'
                        }`}>
                          GRID {log.grid_status}
                        </span>
                        {log.disaster_type !== 'Normal' && (
                          <span className="px-1 text-[8px] uppercase border border-brand-red/30 text-brand-red bg-red-950/20">
                            {log.disaster_type} ACTIVE
                          </span>
                        )}
                      </div>
                      <p className="text-gray-300 font-mono">
                        {log.message}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
