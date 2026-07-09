import React from 'react';
import { useApp } from '../context/AppContext';
import { Cloud, Wind, Thermometer, Droplets, Sun, AlertTriangle } from 'lucide-react';

export default function WeatherTwin() {
  const { activeData } = useApp();

  if (!activeData) return null;

  const w = activeData.weather;
  const d = activeData.disaster;

  return (
    <div className="glass-panel rounded-xl border border-gray-800 flex flex-col overflow-hidden h-full">
      <div className="bg-gray-900/50 p-3 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Cloud className="w-5 h-5 text-brand-blue" />
          <h2 className="font-bold text-white tracking-widest text-sm uppercase">Weather Digital Twin</h2>
        </div>
        {d?.active && (
          <span className="text-[10px] bg-brand-red/20 text-brand-red border border-brand-red/30 px-2 py-0.5 rounded font-bold animate-pulse">
            SEVERITY: {((d?.severity ?? 0) * 100).toFixed(0)}%
          </span>
        )}
      </div>

      <div className="p-4 flex-1 flex flex-col justify-between">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-gray-800 text-brand-blue">
              <Cloud className="w-4 h-4" />
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-gray-500 font-mono uppercase">Cloud Cover</span>
              <span className="font-bold text-white text-sm">{(w?.cloud_cover ?? 0).toFixed(0)}%</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-gray-800 text-amber-500">
              <Sun className="w-4 h-4" />
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-gray-500 font-mono uppercase">Irradiance</span>
              <span className="font-bold text-white text-sm">{((w?.solar_irradiance ?? 0) * 1000).toFixed(0)} W/m²</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-gray-800 text-brand-blue">
              <Wind className="w-4 h-4" />
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-gray-500 font-mono uppercase">Wind Speed</span>
              <span className="font-bold text-white text-sm">{(w?.wind_speed ?? 0).toFixed(1)} km/h</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-gray-800 text-red-400">
              <Thermometer className="w-4 h-4" />
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-gray-500 font-mono uppercase">Temperature</span>
              <span className="font-bold text-white text-sm">{(w?.temperature ?? 0).toFixed(1)} °C</span>
            </div>
          </div>
        </div>

        <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-400 font-mono">FORECAST ENGINE</span>
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${d?.active ? 'bg-brand-red led-red' : 'bg-brand-green led-green'}`}></div>
              <span className="text-[9px] uppercase text-gray-500">{d?.active ? 'WARNING' : 'NOMINAL'}</span>
            </div>
          </div>
          <p className="text-sm font-medium text-white">{d?.description ?? 'Nominal weather conditions.'}</p>
        </div>
      </div>
    </div>
  );
}
