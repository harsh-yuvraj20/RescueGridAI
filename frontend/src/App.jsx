import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { useApp } from './context/AppContext';
import { 
  LayoutDashboard, 
  Flame, 
  BrainCircuit, 
  Truck, 
  BarChart3, 
  Sliders, 
  Volume2, 
  VolumeX, 
  FileSpreadsheet, 
  AlertTriangle, 
  Activity
} from 'lucide-react';

// Import Pages
import Dashboard from './pages/Dashboard';
import Simulator from './pages/Simulator';
import DecisionCenter from './pages/DecisionCenter';
import AmbulancePage from './pages/AmbulancePage';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';

// Navigation links configuration
const navLinks = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/simulator', label: 'Disaster Sim', icon: Flame },
  { path: '/decision-center', label: 'AI Decision Center', icon: BrainCircuit },
  { path: '/ambulances', label: 'Energy Ambulance', icon: Truck },
  { path: '/analytics', label: 'Analytics', icon: BarChart3 },
  { path: '/settings', label: 'Control Room', icon: Sliders },
];

function Navigation() {
  const location = useLocation();
  const { triggerSound } = useApp();

  return (
    <nav className="flex flex-col gap-2 w-64 p-4 border-r border-gray-800 bg-brand-panel min-h-screen">
      <div className="flex items-center gap-3 px-2 py-4 mb-6 border-b border-gray-800">
        <div className="p-2 bg-brand-green/10 border border-brand-green/30 rounded-lg">
          <Activity className="w-6 h-6 text-brand-green animate-pulse" />
        </div>
        <div>
          <span className="font-extrabold text-lg tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-brand-green via-brand-blue to-white">
            RESCUEGRID AI
          </span>
          <span className="block text-[10px] uppercase font-mono tracking-widest text-gray-500">
            Resilience Portal
          </span>
        </div>
      </div>

      <div className="flex-1 flex flex-col gap-1.5">
        {navLinks.map(link => {
          const Icon = link.icon;
          const isActive = location.pathname === link.path;
          return (
            <Link
              key={link.path}
              to={link.path}
              onClick={() => triggerSound('click')}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-150 ${
                isActive 
                  ? 'bg-gradient-to-r from-brand-green/20 to-brand-blue/5 border border-brand-green/30 text-white shadow-glow-green/10'
                  : 'text-gray-400 border border-transparent hover:bg-gray-800 hover:text-white'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-brand-green' : 'text-gray-400'}`} />
              {link.label}
            </Link>
          );
        })}
      </div>

      <div className="p-3 bg-gray-950/40 border border-gray-800 rounded-lg text-[10px] font-mono text-gray-500">
        <p>SYSTEM CORE: v1.2.8-AI</p>
        <p>COGNITIVE LAYER: ONLINE</p>
        <div className="flex items-center gap-1.5 mt-2">
          <div className="w-2 h-2 rounded-full bg-brand-green led-green"></div>
          <span className="text-gray-400 text-[9px] uppercase">Node link synchronized</span>
        </div>
      </div>
    </nav>
  );
}

function Header() {
  const { activeData, soundEnabled, setSoundEnabled, triggerSound, exportPDFReport } = useApp();
  
  if (!activeData) return null;

  const isGridDown = activeData.metrics.grid_status === 'OFFLINE';
  const disasterActive = activeData.disaster.active;

  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800 bg-brand-panel/90 backdrop-blur-md">
      <div className="flex items-center gap-6">
        {/* Disaster warning banner */}
        {disasterActive ? (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-brand-red/10 border border-brand-red/30 rounded-lg animate-pulse">
            <AlertTriangle className="w-4 h-4 text-brand-red led-red" />
            <span className="text-xs font-bold text-brand-red font-mono uppercase tracking-wide">
              {activeData.disaster.type} ALERT IN PROGRESS
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-brand-green/10 border border-brand-green/30 rounded-lg">
            <div className="w-2 h-2 rounded-full bg-brand-green led-green"></div>
            <span className="text-xs font-bold text-brand-green font-mono uppercase tracking-wide">
              GRID HEALTH: STABLE
            </span>
          </div>
        )}

        {/* Grid connection status */}
        <div className="flex items-center gap-1.5 text-xs text-gray-400 font-mono">
          <span className="uppercase">Microgrid status:</span>
          <span className={`font-bold ${isGridDown ? 'text-brand-red' : 'text-brand-green'}`}>
            {isGridDown ? 'ISLANDED OPERATION' : 'INTEGRATED WITH MAIN GRID'}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Export Report shortcut */}
        <button
          onClick={exportPDFReport}
          className="flex items-center gap-2 px-3 py-1.5 border border-brand-blue/30 bg-brand-blue/10 hover:bg-brand-blue/20 rounded-lg text-xs font-bold text-brand-blue font-mono transition"
        >
          <FileSpreadsheet className="w-3.5 h-3.5" />
          <span>AUDIT PDF</span>
        </button>

        {/* Audio feedback button */}
        <button
          onClick={() => {
            setSoundEnabled(!soundEnabled);
            if (!soundEnabled) {
              setTimeout(() => triggerSound('beep', 600), 50);
            }
          }}
          className={`p-2 rounded-lg border transition ${
            soundEnabled 
              ? 'border-brand-green/30 bg-brand-green/5 text-brand-green' 
              : 'border-gray-800 text-gray-500 hover:text-gray-300'
          }`}
          title="Toggle UI Audio Alerts"
        >
          {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
        </button>

        {/* Current status summary details */}
        <div className="flex flex-col items-end text-xs font-mono text-gray-500 border-l border-gray-800 pl-4">
          <span>CO₂ REDUCTION</span>
          <span className="text-sm font-bold text-brand-green">
            {activeData.metrics.carbon_saved.toLocaleString()} kg
          </span>
        </div>
      </div>
    </header>
  );
}

function ToastPortal() {
  const { alerts } = useApp();
  
  return (
    <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-2 max-w-md w-full">
      {alerts.map(alert => {
        let alertColor = 'border-brand-blue bg-blue-950/80 text-blue-200';
        if (alert.type === 'critical') alertColor = 'border-brand-red bg-red-950/90 text-red-200 shadow-glow-red/20 led-red';
        if (alert.type === 'error') alertColor = 'border-brand-red bg-red-950/80 text-red-200';
        if (alert.type === 'success') alertColor = 'border-brand-green bg-green-950/80 text-green-200';

        return (
          <div
            key={alert.id}
            className={`flex items-start gap-3 p-4 rounded-xl border backdrop-blur-md shadow-xl transition-all duration-300 transform translate-y-0 ${alertColor}`}
          >
            <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div className="flex-1 text-sm font-medium leading-relaxed font-sans">
              {alert.message}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function App() {
  const { loading, error } = useApp();

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-brand-dark text-gray-400 font-mono gap-4">
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 border-4 border-brand-green/20 rounded-full"></div>
          <div className="absolute inset-0 border-4 border-t-brand-green border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin"></div>
        </div>
        <div className="text-sm uppercase tracking-widest text-brand-green animate-pulse">
          Connecting to RescueGrid Core...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-brand-dark text-gray-300 font-mono gap-6 p-4 text-center">
        <AlertTriangle className="w-16 h-16 text-brand-red led-red" />
        <div className="max-w-md">
          <h2 className="text-xl font-bold text-white mb-2 uppercase tracking-wide">Connection Failure</h2>
          <p className="text-sm text-gray-500 mb-6">{error}</p>
          <div className="flex flex-col gap-2 bg-gray-900 border border-gray-800 p-4 rounded-lg text-left text-xs">
            <p>1. Start the backend from the project root: <code>python -m uvicorn backend.main:app --reload --port 8000</code></p>
            <p>2. Start the frontend: <code>npm run dev</code> in the frontend folder (open http://localhost:3000).</p>
            <p>3. Do not open port 8000 directly — the UI runs on port 3000 and proxies API calls.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <Router>
      <div className="flex bg-brand-dark min-h-screen">
        {/* Left panel navigation */}
        <Navigation />

        {/* Right side page container */}
        <div className="flex min-w-0 flex-1 flex-col min-h-screen">
          <Header />
          <main className="min-w-0 flex-1 bg-brand-dark/20 p-4 sm:p-6 scan-line">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/simulator" element={<Simulator />} />
              <Route path="/decision-center" element={<DecisionCenter />} />
              <Route path="/ambulances" element={<AmbulancePage />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>

        {/* Alerts Overlay */}
        <ToastPortal />
      </div>
    </Router>
  );
}


