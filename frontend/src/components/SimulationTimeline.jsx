import React from 'react';
import { useApp } from '../context/AppContext';
import { Play, Pause, FastForward, Rewind, Clock, AlertTriangle } from 'lucide-react';

export default function SimulationTimeline() {
  const { 
    activeData, 
    data, // live data
    simSpeed, 
    controlSimulation, 
    history, 
    replayIndex, 
    setReplayIndex 
  } = useApp();

  if (!activeData || !data) return null;

  const isReplaying = replayIndex !== -1;
  
  const handleSliderChange = (e) => {
    const val = parseInt(e.target.value, 10);
    // If at the end of history, return to live mode
    if (val >= history.length - 1) {
      setReplayIndex(-1);
    } else {
      setReplayIndex(val);
    }
  };

  const jumpToLive = () => {
    setReplayIndex(-1);
  };

  const maxIndex = Math.max(0, history.length - 1);
  const currentIndex = isReplaying ? replayIndex : maxIndex;
  
  // Convert virtual hour to HH:MM format
  const formatTime = (hourNum) => {
    const h = Math.floor(hourNum);
    const m = Math.floor((hourNum - h) * 60);
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
  };

  return (
    <div className="glass-panel rounded-xl p-4 flex flex-col gap-3 border border-gray-800">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Clock className="w-5 h-5 text-brand-blue" />
          <h3 className="font-bold text-white uppercase tracking-wider text-sm">
            Simulation Timeline
            {isReplaying && <span className="ml-3 px-2 py-0.5 bg-brand-amber/20 text-brand-amber border border-brand-amber/30 rounded text-xs animate-pulse">REPLAY MODE</span>}
          </h3>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex flex-col items-end text-xs font-mono">
            <span className="text-gray-500">TICK</span>
            <span className="text-white font-bold">{activeData?.recent_logs?.[0]?.step ?? '...'}</span>
          </div>
          <div className="flex flex-col items-end text-xs font-mono">
            <span className="text-gray-500">VIRTUAL TIME</span>
            <span className="text-brand-blue font-bold">Day {Math.floor((activeData?.metrics?.simulation_hour ?? 0) / 24) + 1}, {formatTime((activeData?.metrics?.simulation_hour ?? 0) % 24)}</span>
          </div>
          <div className="flex flex-col items-end text-xs font-mono">
            <span className="text-gray-500">DISASTER STATE</span>
            <span className={`font-bold ${activeData?.disaster?.active ? 'text-brand-red led-red px-2 rounded-md' : 'text-brand-green'}`}>
              {activeData?.disaster?.active ? activeData.disaster.type : 'NONE'}
            </span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4 mt-2">
        <div className="flex items-center gap-2 bg-gray-900/50 p-1 rounded-lg border border-gray-800">
          <button 
            onClick={() => controlSimulation('pause')}
            className={`p-2 rounded hover:bg-gray-800 transition ${simSpeed === 0 ? 'text-brand-amber' : 'text-gray-400'}`}
            title="Pause Simulation"
          >
            <Pause className="w-4 h-4" />
          </button>
          <button 
            onClick={() => controlSimulation('speed', 1.0)}
            className={`p-2 rounded hover:bg-gray-800 transition ${simSpeed === 1.0 ? 'text-brand-green' : 'text-gray-400'}`}
            title="Normal Speed (1x)"
          >
            <Play className="w-4 h-4" />
          </button>
          <button 
            onClick={() => controlSimulation('speed', 2.0)}
            className={`p-2 rounded hover:bg-gray-800 transition ${simSpeed > 1.0 ? 'text-brand-blue' : 'text-gray-400'}`}
            title="Fast Forward (2x+)"
          >
            <FastForward className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 flex flex-col gap-1">
          <div className="flex justify-between text-[10px] text-gray-500 font-mono">
            <span>T-{history.length}</span>
            <span>LIVE</span>
          </div>
          <input 
            type="range" 
            min="0" 
            max={maxIndex} 
            value={currentIndex}
            onChange={handleSliderChange}
            className="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer"
            style={{ accentColor: '#3B82F6' }}
          />
        </div>

        {isReplaying && (
          <button 
            onClick={jumpToLive}
            className="px-3 py-1.5 text-xs font-bold text-brand-blue border border-brand-blue/30 bg-brand-blue/10 rounded hover:bg-brand-blue/20 transition"
          >
            JUMP TO LIVE
          </button>
        )}
      </div>
    </div>
  );
}
