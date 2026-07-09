import React, { useLayoutEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import GridMap from '../components/GridMap';

import SimulationTimeline from '../components/SimulationTimeline';
import RenewablePanel from '../components/RenewablePanel';
import ResilienceScore from '../components/ResilienceScore';
import WeatherTwin from '../components/WeatherTwin';
import SystemHealthPanel from '../components/SystemHealthPanel';
import PhysicsValidationPanel from '../components/PhysicsValidationPanel';
import EnergyFlow from '../components/EnergyFlow';
import OperationsTerminal from '../components/OperationsTerminal';

export default function Dashboard() {
  const { activeData, toggleNodeStatus } = useApp();
  const [mapCenter] = useState([13.0827, 80.2707]);
  const [mapZoom] = useState(12);

  useLayoutEffect(() => {
    if ('scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual';
    }

    const resetScroll = () => {
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
      const scrollContainer = document.querySelector('main');
      if (scrollContainer) {
        scrollContainer.scrollTop = 0;
      }
    };

    resetScroll();
    const frame = window.requestAnimationFrame(resetScroll);
    const timer = window.setTimeout(resetScroll, 150);

    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(timer);
    };
  }, []);

  if (!activeData) return null;

  const isGridDown = activeData.metrics.grid_status === 'OFFLINE';

  return (
    <div className="flex min-w-0 flex-col gap-5 pb-8">
      <section className="grid grid-cols-1 gap-5 lg:grid-cols-2 2xl:grid-cols-12">
        <div className="min-h-[220px] 2xl:col-span-3">
          <ResilienceScore />
        </div>
        <div className="flex min-h-[220px] flex-col gap-4 2xl:col-span-4">
          <SimulationTimeline />
          <SystemHealthPanel />
        </div>
        <div className="min-h-[220px] 2xl:col-span-3">
          <WeatherTwin />
        </div>
        <div className="min-h-[220px] 2xl:col-span-2">
          <PhysicsValidationPanel />
        </div>
      </section>

      <section className="grid grid-cols-1 gap-5 2xl:grid-cols-12">
        <div className="relative min-h-[560px] overflow-hidden rounded-xl border border-gray-800 glass-panel shadow-glass 2xl:col-span-8">
          <div className="absolute left-4 top-4 z-[400] rounded-lg border border-gray-800 bg-gray-900/90 px-3 py-1.5 shadow-xl backdrop-blur-md">
            <h2 className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-white">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-green led-green" />
              Live Grid Twin
            </h2>
          </div>
          <GridMap
            mapCenter={mapCenter}
            mapZoom={mapZoom}
            nodes={activeData.nodes}
            ambulances={activeData.ambulances}
            isGridDown={isGridDown}
            toggleNodeStatus={toggleNodeStatus}
          />
        </div>

        <div className="grid min-w-0 grid-cols-1 gap-5 lg:grid-cols-2 2xl:col-span-4 2xl:grid-cols-1">
          <div className="min-h-[300px]">
            <RenewablePanel />
          </div>
          <div className="min-h-[300px]">
            <OperationsTerminal />
          </div>
        </div>
      </section>

      <section className="min-h-[190px] rounded-xl">
        <EnergyFlow />
      </section>
    </div>
  );
}


