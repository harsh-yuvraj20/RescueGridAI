import React, { useEffect, useState, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';

// Forces Leaflet to recalculate its container size after render/resize
function MapResizer() {
  const map = useMap();
  useEffect(() => {
    const timer = setTimeout(() => map.invalidateSize(), 200);
    const handleResize = () => map.invalidateSize();
    window.addEventListener('resize', handleResize);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', handleResize);
    };
  }, [map]);
  return null;
}

const statusColors = {
  Healthy: '#10B981',
  Warning: '#F59E0B',
  Critical: '#EF4444',
  Emergency: '#F97316',
  Offline: '#6B7280',
};

const getCustomIcon = (type, status, isAmbulance = false, ambulanceStatus = 'Idle') => {
  let color = statusColors[status] || '#10B981';
  let pulseClass = '';

  if (status === 'Critical' || status === 'Offline' || status === 'Emergency') {
    pulseClass = 'animate-ping opacity-60';
  } else if (status === 'Warning') {
    pulseClass = 'animate-pulse';
  }

  let svgContent = '';
  if (isAmbulance) {
    color = ambulanceStatus === 'Dispatched' ? '#3B82F6' : (ambulanceStatus === 'Charging Node' ? '#10B981' : '#F59E0B');
    svgContent = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-3 h-3">
        <rect x="1" y="3" width="15" height="13" rx="2" ry="2"/>
        <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/>
        <circle cx="5.5" cy="18.5" r="2.5"/>
        <circle cx="18.5" cy="18.5" r="2.5"/>
      </svg>
    `;
  } else {
    switch (type) {
      case 'Hospital':
        svgContent = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="w-3.5 h-3.5"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>`;
        break;
      case 'Water Plant':
        svgContent = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="w-3.5 h-3.5"><path d="M12 22a7 7 0 0 0 7-7c0-4.3-7-11-7-11S5 10.7 5 15a7 7 0 0 0 7 7z"/></svg>`;
        break;
      case 'Telecom Tower':
        svgContent = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="w-3.5 h-3.5"><rect x="5" y="16" width="14" height="5" rx="1"/><path d="M12 16v-5"/><path d="M8 8a5 5 0 0 1 8 0"/><path d="M12 3a9 9 0 0 1 0 13"/></svg>`;
        break;
      case 'Solar Farm':
        svgContent = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="w-3.5 h-3.5"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>`;
        break;
      case 'Wind Farm':
        svgContent = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="w-3.5 h-3.5"><path d="M12.8 19.6A2 2 0 1 0 14 16H2"/><path d="M17.5 8.6A3.5 3.5 0 1 1 14 12H4"/><path d="M9.8 4.4A2.4 2.4 0 1 0 8 8h12"/></svg>`;
        break;
      case 'Battery Station':
        svgContent = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="w-3.5 h-3.5"><rect x="2" y="7" width="16" height="12" rx="2" ry="2"/><line x1="22" y1="11" x2="22" y2="15"/><line x1="6" y1="11" x2="10" y2="11"/><line x1="8" y1="9" x2="8" y2="13"/></svg>`;
        break;
      default:
        svgContent = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" class="w-3 h-3"><circle cx="12" cy="12" r="10"/></svg>`;
    }
  }

  const html = `
    <div class="relative flex items-center justify-center w-8 h-8">
      <div class="absolute w-8 h-8 rounded-full ${pulseClass}" style="background-color: ${color}40"></div>
      <div class="relative z-10 w-6 h-6 flex items-center justify-center rounded-full border border-white/20 shadow-lg" style="background-color: ${color}">
        ${svgContent}
      </div>
    </div>
  `;

  return L.divIcon({
    html,
    className: 'custom-div-icon',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
};

export default function GridMap({
  nodes,
  ambulances,
  isGridDown,
  mapCenter,
  mapZoom,
  toggleNodeStatus,
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const safeNodes = nodes ?? [];
  const safeAmbulances = ambulances ?? [];

  const energySources = safeNodes.filter(n => n.type === 'Solar Farm' || n.type === 'Wind Farm');
  const substations = safeNodes.filter(n => n.type === 'Battery Station');
  const consumers = safeNodes.filter(n => ['Hospital', 'Water Plant', 'Telecom Tower'].includes(n.type));

  const sourceToSubstationLines = [];
  energySources.forEach(src => {
    let closestSub = null;
    let minDist = Infinity;
    substations.forEach(sub => {
      const dist = Math.hypot(src.latitude - sub.latitude, src.longitude - sub.longitude);
      if (dist < minDist) {
        minDist = dist;
        closestSub = sub;
      }
    });
    if (closestSub) {
      sourceToSubstationLines.push([
        [src.latitude, src.longitude],
        [closestSub.latitude, closestSub.longitude],
      ]);
    }
  });

  const substationToConsumerLines = [];
  substations.forEach(sub => {
    consumers.forEach(cons => {
      const dist = Math.hypot(sub.latitude - cons.latitude, sub.longitude - cons.longitude);
      if (dist < 0.04) {
        substationToConsumerLines.push([
          [sub.latitude, sub.longitude],
          [cons.latitude, cons.longitude],
        ]);
      }
    });
  });

  if (!mounted) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-brand-panel text-gray-500 font-mono text-xs">
        Initializing grid map...
      </div>
    );
  }

  return (
    <MapContainer
      center={mapCenter}
      zoom={mapZoom}
      className="w-full h-full z-10"
      zoomControl={false}
      style={{ height: '100%', width: '100%' }}
    >
      <MapResizer />
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://carto.com/">CARTO</a>'
      />

      {sourceToSubstationLines.map((line, idx) => (
        <Polyline
          key={`src-${idx}`}
          positions={line}
          pathOptions={{
            color: isGridDown ? '#3B82F6' : '#10B981',
            weight: 2,
            opacity: 0.6,
            dashArray: '5, 8',
            className: 'animate-power-flow',
          }}
        />
      ))}

      {substationToConsumerLines.map((line, idx) => (
        <Polyline
          key={`cons-${idx}`}
          positions={line}
          pathOptions={{
            color: isGridDown ? '#EF4444' : '#10B981',
            weight: 1.8,
            opacity: 0.5,
            dashArray: '4, 10',
            className: isGridDown ? '' : 'animate-power-flow',
          }}
        />
      ))}

      {nodes.map(node => (
        <Marker
          key={node.id}
          position={[node.latitude, node.longitude]}
          icon={getCustomIcon(node.type, node.status)}
        >
          <Popup className="digital-twin-popup">
            <div className="text-xs flex flex-col gap-2 p-1 font-mono text-gray-200 min-w-[240px]">
              <div className="border-b border-gray-700 pb-2 flex justify-between items-start">
                <div className="flex flex-col">
                  <span className="font-extrabold text-[14px] tracking-tight">{node.name}</span>
                  <span className="text-[9px] text-gray-500">ID: {String(node.id).split('-')[0]}</span>
                </div>
                <span className="px-1.5 py-0.5 text-[9px] uppercase border border-gray-700 rounded bg-gray-900/80 text-gray-400">
                  {node.type}
                </span>
              </div>

              {node.type === 'Solar Farm' || node.type === 'Wind Farm' ? (
                <div className="bg-gray-900/50 p-2 rounded border border-gray-800">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-[10px] text-gray-400">Output Power</span>
                    <span className="font-bold text-brand-green">{node.generation_output?.toFixed(1) || 0} kW</span>
                  </div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-[10px] text-gray-400">Max Capacity</span>
                    <span className="font-bold text-gray-300">{node.max_capacity?.toFixed(1) || 0} kW</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] text-gray-400">Efficiency / CF</span>
                    <span className="font-bold text-brand-blue">
                      {node.capacity_factor ? (node.capacity_factor * 100).toFixed(1) : 0}%
                    </span>
                  </div>
                </div>
              ) : (
                <div className="bg-gray-900/50 p-2 rounded border border-gray-800 flex flex-col gap-1.5">
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] text-gray-400">Battery Status</span>
                    <span className="font-bold text-brand-blue">
                      {(node.current_storage ?? 0).toFixed(1)} / {node.max_capacity ?? 0} kWh
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-green" style={{ width: `${node.max_capacity > 0 ? ((node.current_storage ?? 0) / node.max_capacity) * 100 : 0}%` }}></div>
                  </div>
                  <div className="flex justify-between items-center mt-1">
                    <span className="text-[10px] text-gray-400">State of Charge</span>
                    <span className="font-bold text-brand-green">
                      {node.max_capacity > 0 ? (((node.current_storage ?? 0) / node.max_capacity) * 100).toFixed(1) : 0}%
                    </span>
                  </div>
                  
                  {node.type !== 'Battery Station' && (
                    <div className="flex justify-between items-center mt-1 pt-1 border-t border-gray-800">
                      <span className="text-[10px] text-gray-400">Power Demand</span>
                      <span className="font-bold text-brand-red">{node.current_demand?.toFixed(1) || 0} kW</span>
                    </div>
                  )}

                  <div className="flex justify-between items-center border-t border-gray-800 pt-1 mt-1">
                    <span className="text-[10px] text-gray-400">Survival Horizon</span>
                    <span className="font-bold text-brand-amber text-[11px]">
                      {(node.survival_hours ?? 0) >= 336.0 ? 'Charging / Stable' : 
                       (node.survival_hours ?? 0) >= 48.0 ? `${((node.survival_hours ?? 0) / 24).toFixed(1)} Days` :
                       (node.survival_hours ?? 0) >= 2.0 ? `${(node.survival_hours ?? 0).toFixed(1)} Hours` :
                       `${Math.round((node.survival_hours ?? 0) * 60)} Mins`}
                    </span>
                  </div>
                </div>
              )}

              {/* AI Insight Section */}
              <div className="bg-brand-blue/5 border border-brand-blue/20 rounded p-2 flex items-center justify-between">
                <span className="text-[9px] text-brand-blue font-bold uppercase tracking-wider">Priority Level</span>
                <div className="flex gap-1">
                  {[...Array(5)].map((_, i) => {
                    const critMap = { 'High': 5, 'Medium': 3, 'Low': 1 };
                    const critLevel = critMap[node.criticality] ?? 1;
                    return (
                      <div key={i} className={`w-3 h-1 rounded-sm ${i < critLevel ? 'bg-brand-blue shadow-glow-blue' : 'bg-gray-800'}`}></div>
                    );
                  })}
                </div>
              </div>

              <div className="flex justify-between items-center mt-2 border-t border-gray-800 pt-2">
                <div className="flex items-center gap-1.5">
                  <div className={`w-2 h-2 rounded-full`} style={{ backgroundColor: statusColors[node.status] }}></div>
                  <span className="text-[9px] uppercase font-bold" style={{ color: statusColors[node.status] }}>
                    {node.status}
                  </span>
                </div>
                <button
                  onClick={() => toggleNodeStatus(node.id)}
                  className="px-2 py-1 bg-gray-800 border border-gray-700 rounded text-[9px] font-bold hover:bg-gray-700 transition"
                >
                  MANUAL BYPASS
                </button>
              </div>
            </div>
          </Popup>
        </Marker>
      ))}

      {safeAmbulances.map(amb => (
        <Marker
          key={`amb-${amb.id}`}
          position={[amb.latitude, amb.longitude]}
          icon={getCustomIcon(null, null, true, amb.status)}
        >
          <Popup className="digital-twin-popup">
            <div className="text-xs flex flex-col gap-2 p-1 font-mono text-gray-200 min-w-[200px]">
              <div className="border-b border-gray-700 pb-2 flex justify-between items-center">
                <div className="flex flex-col">
                  <span className="font-extrabold text-[14px] tracking-tight">{amb.name}</span>
                </div>
                <span className="px-1.5 py-0.5 text-[9px] uppercase border border-blue-900 rounded bg-blue-950/60 text-brand-blue font-bold">
                  {amb.status}
                </span>
              </div>

              <div className="bg-gray-900/50 p-2 rounded border border-gray-800 flex flex-col gap-1.5">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-gray-400">Payload Energy</span>
                  <span className="font-bold text-brand-green">{(amb.current_energy ?? 0).toFixed(1)} kWh</span>
                </div>
                <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-brand-green" style={{ width: `${(amb.battery_capacity ?? 0) > 0 ? ((amb.current_energy ?? 0) / amb.battery_capacity) * 100 : 0}%` }}></div>
                </div>
                <div className="flex justify-between items-center mt-1">
                  <span className="text-[10px] text-gray-400">Total Delivered</span>
                  <span className="font-bold text-brand-blue">{(amb.energy_delivered ?? 0).toFixed(1)} kWh</span>
                </div>
              </div>

              {amb.status === 'Dispatched' && (
                <div className="bg-brand-amber/5 border border-brand-amber/20 p-2 rounded flex flex-col gap-1">
                  <span className="text-[9px] text-brand-amber font-bold uppercase">Mission Active</span>
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] text-gray-400">ETA</span>
                    <span className="font-bold text-white">{(amb.eta_minutes ?? 0).toFixed(0)} mins</span>
                  </div>
                  <div className="w-full h-1 bg-gray-800 rounded-full overflow-hidden mt-1">
                    <div className="h-full bg-brand-amber animate-pulse" style={{ width: `${amb.progress ?? 50}%` }}></div>
                  </div>
                </div>
              )}
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
