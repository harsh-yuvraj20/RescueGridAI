const IDLE_MISSION = 'Idle - Ready for deployment';
const activeStates = new Set(['Dispatched', 'Charging Node', 'Returning', 'Recharging']);
const memory = new Map();
let previousStep = null;

const number = (value, fallback = 0) => Number.isFinite(Number(value)) ? Number(value) : fallback;
const distanceKm = (a, b) => {
  const rad = value => value * Math.PI / 180;
  const lat1 = rad(number(a?.latitude));
  const lat2 = rad(number(b?.latitude));
  const dLat = lat2 - lat1;
  const dLon = rad(number(b?.longitude) - number(a?.longitude));
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 12742 * Math.atan2(Math.sqrt(h), Math.sqrt(Math.max(0, 1 - h)));
};

const escalationStage = node => {
  if (['Solar Farm', 'Wind Farm'].includes(node.type)) return 'Normal';
  const soc = number(node.max_capacity) > 0 ? number(node.current_storage) / number(node.max_capacity) * 100 : 100;
  const risk = number(node.risk_score);
  if (soc <= 5 || risk >= 90 || node.status === 'Offline') return 'Offline';
  if (soc <= 15 || risk >= 75 || node.status === 'Critical' || node.status === 'Emergency') return 'Critical';
  if (soc <= 30 || risk >= 50 || node.status === 'Warning') return 'Warning';
  return 'Normal';
};

const nearestStation = (origin, stations, requireEnergy = false) => stations
  .filter(station => station.status !== 'Offline' && (!requireEnergy || number(station.current_storage) > 0.5))
  .map(station => ({ station, distance: distanceKm(origin, station) }))
  .sort((a, b) => a.distance - b.distance)[0];

export const stabilizeDashboard = dashboard => {
  if (!dashboard) return dashboard;
  const step = Math.max(0, ...(dashboard.recent_logs ?? []).map(log => number(log.step)));
  const elapsedTicks = previousStep === null ? 0 : Math.max(0, step - previousStep);
  previousStep = step;
  const rawNodes = dashboard.nodes ?? [];
  const stations = rawNodes.filter(node => node.type === 'Battery Station');
  const gridAvailable = dashboard.metrics?.grid_status === 'ONLINE';
  const demand = rawNodes.filter(node => ['Hospital', 'Water Plant', 'Telecom Tower'].includes(node.type))
    .reduce((sum, node) => sum + number(node.current_demand), 0);
  const generation = rawNodes.filter(node => ['Solar Farm', 'Wind Farm'].includes(node.type))
    .reduce((sum, node) => sum + number(node.generation_output), 0);
  const renewableSurplus = Math.max(0, generation - demand);

  const nodes = rawNodes.map(node => ({
    ...node,
    escalation_stage: escalationStage(node),
    ...(node.type === 'Battery Station' ? {
      recovery_source: gridAvailable ? 'Grid' : renewableSurplus > 0 ? 'Renewable surplus' : 'Awaiting generation',
      recovery_active: number(node.current_storage) < number(node.max_capacity) && (gridAvailable || renewableSurplus > 0),
      charging_available: number(node.current_storage) > 0.5,
    } : {}),
  }));

  const ambulances = (dashboard.ambulances ?? []).map(ambulance => {
    if (ambulance.status === 'Idle') {
      memory.delete(ambulance.id);
      return { ...ambulance, mission_id: '', target_node_id: null, source_name: '', destination_name: '', eta_minutes: 0, progress: 0, current_mission: IDLE_MISSION, stalled_ticks: 0, recovery_action: null };
    }
    const progress = number(ambulance.progress);
    const prior = memory.get(ambulance.id);
    const unchanged = prior && prior.progress === progress && prior.status === ambulance.status;
    const stalledTicks = unchanged ? prior.stalledTicks + elapsedTicks : 0;
    memory.set(ambulance.id, { progress, status: ambulance.status, stalledTicks });
    let recoveryAction = null;
    if (activeStates.has(ambulance.status) && stalledTicks >= 100) {
      const alternate = nearestStation(ambulance, stations, true);
      recoveryAction = alternate
        ? { type: 'Retry route', station_id: alternate.station.id, station_name: alternate.station.name }
        : { type: 'Recovery impossible', reset_allowed: true };
    }
    const station = stations.find(item => item.id === ambulance.target_node_id);
    return { ...ambulance, stalled_ticks: stalledTicks, recovery_action: recoveryAction, charging_can_resume: ambulance.status === 'Recharging' && number(station?.current_storage) > 0.5 };
  });

  const idle = ambulances.filter(ambulance => ambulance.status === 'Idle');
  const pending = (dashboard.recent_decisions ?? []).filter(decision => decision.type === 'Dispatch' && decision.status === 'Pending');
  const dispatchCandidates = pending.flatMap(decision => {
    const target = nodes.find(node => node.id === decision.node_id);
    if (!target) return [];
    return idle.flatMap(ambulance => {
      const home = nearestStation(target, stations);
      if (!home) return [];
      const payload = Math.min(50, Math.max(10, number(target.max_capacity) - number(target.current_storage)));
      const required = Number((((distanceKm(ambulance, target) + home.distance) * 1.2 * 0.45) + payload).toFixed(1));
      return number(ambulance.current_energy) >= required ? [{ decision_id: decision.id, ambulance_id: ambulance.id, target_node_id: target.id, return_station_id: home.station.id, required_energy: required, available_energy: number(ambulance.current_energy) }] : [];
    });
  }).sort((a, b) => a.required_energy - b.required_energy || a.ambulance_id - b.ambulance_id);

  const stationEnergy = stations.reduce((sum, station) => sum + number(station.current_storage), 0);
  const stationCapacity = stations.reduce((sum, station) => sum + number(station.max_capacity), 0);
  return {
    ...dashboard,
    nodes,
    ambulances,
    dispatch_candidates: dispatchCandidates,
    metrics: {
      ...dashboard.metrics,
      renewable_output: Number(generation.toFixed(1)),
      station_battery_soc: stationCapacity ? Number((stationEnergy / stationCapacity * 100).toFixed(1)) : 0,
      active_ambulances: ambulances.filter(ambulance => ambulance.status !== 'Idle').length,
    },
  };
};
