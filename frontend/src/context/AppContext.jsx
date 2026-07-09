import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import apiClient from '../api';
import { stabilizeDashboard } from '../utils/dashboardStabilizer';

const AppContext = createContext();

// Dynamic sound generator using Web Audio API so we don't need asset files
const createSoundSynth = () => {
  let audioCtx = null;

  const initCtx = () => {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
  };

  return {
    playBeep: (freq = 800, duration = 0.08, type = 'sine') => {
      try {
        initCtx();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
        osc.type = type;
        gain.gain.setValueAtTime(0.04, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + duration);
        osc.start();
        osc.stop(audioCtx.currentTime + duration);
      } catch (e) {
        // Audio Context blocked by browser policy until user interaction
      }
    },
    playAlarm: () => {
      try {
        initCtx();
        const now = audioCtx.currentTime;
        const osc1 = audioCtx.createOscillator();
        const osc2 = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc1.connect(gain);
        osc2.connect(gain);
        gain.connect(audioCtx.destination);
        
        osc1.type = 'sawtooth';
        osc1.frequency.setValueAtTime(120, now);
        osc1.frequency.linearRampToValueAtTime(300, now + 0.3);
        
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(150, now);
        osc2.frequency.linearRampToValueAtTime(380, now + 0.3);
 
        gain.gain.setValueAtTime(0.08, now);
        gain.gain.linearRampToValueAtTime(0.0001, now + 0.4);
 
        osc1.start();
        osc1.stop(now + 0.4);
        osc2.start();
        osc2.stop(now + 0.4);
      } catch (e) {
        // Alarm synthesis failed
      }
    }
  };
};

export const AppProvider = ({ children }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [simSpeed, setSimSpeed] = useState(1.0);
  const [alerts, setAlerts] = useState([]);
  const [predictions, setPredictions] = useState(null);
  const [validationMetrics, setValidationMetrics] = useState(null);
  const [history, setHistory] = useState([]);
  const [replayIndex, setReplayIndex] = useState(-1);
  
  const synthRef = useRef(null);

  useEffect(() => {
    synthRef.current = createSoundSynth();
  }, []);

  const triggerSound = (type, freq = 800) => {
    if (!soundEnabled || !synthRef.current) return;
    if (type === 'beep') synthRef.current.playBeep(freq);
    if (type === 'click') synthRef.current.playBeep(450, 0.05, 'triangle');
    if (type === 'alarm') synthRef.current.playAlarm();
    if (type === 'success') synthRef.current.playBeep(1200, 0.15, 'sine');
  };

  const addToastAlert = (message, type = 'info') => {
    const id = Date.now() + Math.random().toString(36).substr(2, 5);
    setAlerts(prev => [...prev, { id, message, type }]);
    
    if (type === 'critical' || type === 'error') {
      triggerSound('alarm');
    } else {
      triggerSound('beep', 700);
    }

    setTimeout(() => {
      setAlerts(prev => prev.filter(a => a.id !== id));
    }, 5000);
  };

  const fetchDashboardData = async () => {
    try {
      const response = await apiClient.get('/api/dashboard');
      const nextData = stabilizeDashboard(response.data);

      setData(prev => {
        if (prev && nextData) {
          if (nextData.disaster.active && !prev.disaster.active) {
            queueMicrotask(() => addToastAlert(`CRITICAL ALERT: ${nextData.disaster.type} has begun! Main power grid is DOWN.`, 'critical'));
          }
          if (!nextData.disaster.active && prev.disaster.active) {
            queueMicrotask(() => addToastAlert("Disaster threat neutralized. Main grid restored to normal operations.", "success"));
          }
          if (nextData.recent_decisions.length > prev.recent_decisions.length) {
            const latest = nextData.recent_decisions[0];
            if (latest && latest.type === 'Dispatch') {
              queueMicrotask(() => addToastAlert(`AI ACTION: ${latest.description}`, 'info'));
            }
          }
          const prevOffline = prev.nodes.filter(n => n.status === 'Offline').map(n => n.id);
          const currOffline = nextData.nodes.filter(n => n.status === 'Offline');
          currOffline.forEach(node => {
            if (!prevOffline.includes(node.id) && node.type !== 'Solar Farm' && node.type !== 'Wind Farm') {
              queueMicrotask(() => addToastAlert(`SYSTEM DOWN: ${node.name} is depleted and OFFLINE!`, 'error'));
            }
          });
        }
        
        // Add to history (keep max 100 snapshots)
        setHistory(h => {
          const newHistory = [...h, nextData];
          if (newHistory.length > 100) newHistory.shift();
          return newHistory;
        });

        return nextData;
      });
      setLoading(false);
      setError(null);
    } catch (err) {
      setError("Failed to connect to RescueGrid AI backend server.");
      setLoading(false);
    }
  };

  const fetchPredictions = async () => {
    try {
      const res = await apiClient.get('/api/predictions');
      setPredictions(res.data);
    } catch (err) {
      // API may be temporarily unavailable
    }
  };

  const fetchValidation = async () => {
    try {
      const res = await apiClient.get('/api/validation');
      setValidationMetrics(res.data);
    } catch (err) {
      // API may be temporarily unavailable
    }
  };

  // Periodic polling
  useEffect(() => {
    fetchDashboardData();
    fetchPredictions();
    fetchValidation();
    const interval = setInterval(() => {
      // Only poll if not in replay mode
      setReplayIndex(idx => {
        if (idx === -1) {
          fetchDashboardData();
          fetchPredictions();
          fetchValidation();
        }
        return idx;
      });
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const changeDisaster = async (type, severity = 0.8) => {
    try {
      triggerSound('click');
      await apiClient.post('/api/simulator/disaster', {
        type,
        severity,
        active: type !== 'Normal',
        affected_grid: type !== 'Normal',
        description: ''
      });
      await fetchDashboardData();
    } catch (err) {
      addToastAlert("Failed to update disaster state.", "error");
    }
  };

  const controlSimulation = async (action, speedVal = 1.0) => {
    try {
      triggerSound('click');
      if (action === 'speed') setSimSpeed(speedVal);
      await apiClient.post(`/api/simulator/control?action=${action}&speed=${speedVal}`);
      if (action === 'reset') {
        addToastAlert("Simulation reset successful. Restoring battery levels.", "success");
      } else if (action === 'start') {
        addToastAlert("Simulation engine started.", "success");
      } else if (action === 'pause') {
        addToastAlert("Simulation engine paused.", "info");
      }
      await fetchDashboardData();
      await fetchPredictions();
    } catch (err) {
      addToastAlert("Failed to update simulation controls.", "error");
    }
  };

  const toggleNodeStatus = async (nodeId) => {
    try {
      triggerSound('click');
      await apiClient.post(`/api/infrastructure/${nodeId}/toggle`);
      addToastAlert("Manual infrastructure bypass triggered.", "info");
      await fetchDashboardData();
    } catch (err) {
      addToastAlert("Failed to toggle node status.", "error");
    }
  };

  const completeDecision = async (decisionId) => {
    try {
      triggerSound('success');
      await apiClient.post(`/api/decision/${decisionId}/action`);
      addToastAlert("AI Recommendation accepted and executed.", "success");
      await fetchDashboardData();
    } catch (err) {
      addToastAlert("Failed to execute decision.", "error");
    }
  };

  const askCommander = async (queryText) => {
    try {
      triggerSound('click');
      const res = await apiClient.post('/api/incident-commander/ask', { query: queryText });
      return res.data.response;
    } catch (err) {
      return "Telemetry system busy. Please try asking again shortly.";
    }
  };

  const startCycloneDemo = async () => {
    try {
      triggerSound('alarm');
      setSimSpeed(2.0); // fast forward during demo
      await apiClient.post('/api/demo/cyclone');
      addToastAlert("JUDGE DEMO MODE ACTIVATED: Category 4 Cyclone scenario initiated.", "critical");
      await fetchDashboardData();
      await fetchPredictions();
    } catch (err) {
      addToastAlert("Failed to start cyclone demo.", "error");
    }
  };

  const exportPDFReport = () => {
  triggerSound('success');
  addToastAlert("Preparing PDF Resilience Audit Report...", "info");
  window.open(`${apiClient.defaults.baseURL}/api/report/export`, "_blank");
};

  return (
    <AppContext.Provider value={{
      data,
      loading,
      error,
      soundEnabled,
      setSoundEnabled,
      simSpeed,
      alerts,
      predictions,
      validationMetrics,
      history,
      replayIndex,
      setReplayIndex,
      activeData: replayIndex >= 0 && history[replayIndex] ? history[replayIndex] : data,
      addToastAlert,
      triggerSound,
      changeDisaster,
      controlSimulation,
      toggleNodeStatus,
      completeDecision,
      askCommander,
      startCycloneDemo,
      exportPDFReport,
      refetch: fetchDashboardData
    }}>
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => useContext(AppContext);

