import math
import random
import datetime
import json
from sqlalchemy.orm import Session
from .models import InfrastructureNode, EnergyAmbulance, AIDecision, DisasterStatus, SimulationState
from . import physics_engine as pe

# ─── Configurable Dispatch & Evaluation Thresholds ───
DISPATCH_SOC_THRESHOLD = 20.0       # Dispatch when SOC < 20%
DISPATCH_RUNTIME_HOURS = 4.0        # Combined with SOC for dispatch trigger
FORECAST_WINDOW_HOURS = 6.0         # Predict if node will reach Emergency within this window
EMERGENCY_SOC_PCT = 20.0            # SOC at which consumer enters Emergency status
MISSION_COMPLETE_SOC = 60.0         # Hysteresis: stop charging when target SOC > 60%
AMBULANCE_RECHARGE_RATE = 50.0      # kW recharge rate at base station

# AI Trend Memory (Persistent across ticks)
NODE_HISTORY = {}
PREVIOUS_SCORES = {}

# Great-circle distance between two points on Earth (in km)
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def find_nearest_station(ambulance, battery_stations):
    closest_station = None
    min_dist = float('inf')
    for station in battery_stations:
        dist = haversine_distance(ambulance.latitude, ambulance.longitude, station.latitude, station.longitude)
        if dist < min_dist:
            min_dist = dist
            closest_station = station
    return closest_station, min_dist


def run_ai_decision_engine(db: Session, sim_state: SimulationState, disaster: DisasterStatus):
    """
    Evaluates the current state of the grid, calculates survival times,
    prioritizes infrastructure nodes, dispatches ambulances, and issues recommendations with full explainability.
    """
    # 1. Gather all nodes
    nodes = db.query(InfrastructureNode).all()
    ambulances = db.query(EnergyAmbulance).all()

    hospitals = [n for n in nodes if n.type == "Hospital"]
    water_plants = [n for n in nodes if n.type == "Water Plant"]
    telecom_towers = [n for n in nodes if n.type == "Telecom Tower"]
    solar_farms = [n for n in nodes if n.type == "Solar Farm"]
    wind_farms = [n for n in nodes if n.type == "Wind Farm"]
    battery_stations = [n for n in nodes if n.type == "Battery Station"]

    # 2. Calculate current total renewable generation
    total_solar_gen = sum(n.generation_output for n in solar_farms if n.status != "Offline")
    total_wind_gen = sum(n.generation_output for n in wind_farms if n.status != "Offline")
    total_renewables = total_solar_gen + total_wind_gen

    # Grid supply available?
    grid_available = not disaster.affected_grid and sim_state.grid_status == "Stable"

    # --- Decision Queue Maintenance (every tick) ---
    existing_decisions = db.query(AIDecision).filter(
        AIDecision.status.in_(["Pending", "Executing"])
    ).all()
    for dec in existing_decisions:
        if dec.node_id:
            target_n = next((n for n in nodes if n.id == dec.node_id), None)
            if target_n:
                soc_val = (target_n.current_storage / max(target_n.max_capacity, 1.0)) * 100.0
                dec.battery_level = round(soc_val, 1)
                dec.remaining_backup_time = round(min(target_n.survival_hours, 336.0), 1)
                dec.disaster_severity = disaster.severity
                dec.renewable_availability = round(total_renewables, 1)
                # Auto-resolve non-dispatch decisions for recovered nodes
                if soc_val > MISSION_COMPLETE_SOC and dec.type in ["Load Shedding", "Optimization"]:
                    dec.status = "Completed"
                elif dec.status == "Pending":
                    dec.priority_score = min(100.0, dec.priority_score + 1.0)
            else:
                dec.status = "Completed"

    # 3. Dynamic Energy Allocation and Node Status Update
    # (Energy allocation is handled in simulation.py via physics engine, 
    # but we will evaluate node survival times here for decision making)
    critical_consumers = hospitals + water_plants + telecom_towers
    
    decisions_to_add = []

    # Calculate ambulance speed and route penalties depending on disaster
    base_ambulance_speed = 50.0  # base km/h
    route_distance_penalty = 1.0  # multiplier for detours
    
    if disaster.active:
        if disaster.type == "Cyclone":
            base_ambulance_speed = 18.0
            route_distance_penalty = 1.4  # debris detours
        elif disaster.type == "Flood":
            base_ambulance_speed = 12.0
            route_distance_penalty = 1.8  # flooded road detours
        elif disaster.type == "Earthquake":
            base_ambulance_speed = 10.0
            route_distance_penalty = 1.5  # cracked road detours
        elif disaster.type == "Heatwave":
            base_ambulance_speed = 45.0
            route_distance_penalty = 1.0
        elif disaster.type == "Cyber Attack":
            base_ambulance_speed = 50.0
            route_distance_penalty = 1.0

    # 4. Continuous Priority Scoring for ALL Critical Infrastructure
    prioritized_nodes = []
    
    # ─── Escalation Stage Helper ───
    def get_escalation_stage(soc_pct, risk_score):
        if soc_pct <= 5.0 or risk_score > 90.0: return "Collapse"
        if soc_pct <= 20.0 or risk_score > 75.0: return "Emergency"
        if soc_pct <= 40.0 or risk_score > 50.0: return "Critical"
        if soc_pct <= 60.0 or risk_score > 25.0: return "Warning"
        return "Observation"

    for node in critical_consumers:
        # 1. Update Short-Term Trend Memory
        if node.id not in NODE_HISTORY:
            NODE_HISTORY[node.id] = {"soc": [], "demand": []}
        NODE_HISTORY[node.id]["soc"].append(node.current_storage / max(node.max_capacity, 1.0))
        NODE_HISTORY[node.id]["demand"].append(node.current_demand)
        
        # Keep last 15 ticks for trend memory
        if len(NODE_HISTORY[node.id]["soc"]) > 15:
            NODE_HISTORY[node.id]["soc"].pop(0)
            NODE_HISTORY[node.id]["demand"].pop(0)

        soc = NODE_HISTORY[node.id]["soc"][-1]
        soc_pct = soc * 100.0

        # Calculate Demand Trend
        demand_hist = NODE_HISTORY[node.id]["demand"]
        if len(demand_hist) >= 5:
            demand_trend = (demand_hist[-1] - demand_hist[0]) / max(0.1, demand_hist[0])
        else:
            demand_trend = 0.0

        # Base Criticality
        criticality_base = 100.0 if node.criticality == "High" else 50.0
        if node.type == "Hospital":
            criticality_base = min(100.0, criticality_base + 20.0)
        elif node.type == "Water Plant":
            criticality_base = min(100.0, criticality_base + 10.0)

        # Dynamic Attributes
        pop_served = 10000 if node.type == "Hospital" else (50000 if node.type == "Water Plant" else 100000)
        pop_factor = min(1.0, pop_served / 100000.0) * 100.0

        recovery_diff = 0.9 if node.type == "Hospital" else (0.6 if node.type == "Water Plant" else 0.3)
        recovery_factor = recovery_diff * 100.0

        # --- Multi-Horizon Predictive Failure Model ---
        # Instead of just current status, calculate failure probability at 2h, 8h, 24h
        # Adjust demand by trend and weather modifier
        weather_modifier = 1.0 + (disaster.severity if disaster.active else 0.0)
        forecast_demand = node.current_demand * (1.0 + demand_trend) * weather_modifier
        
        # Forecast Renewable Availability (assuming average generation vs current weather)
        forecast_renewable_factor = max(0.1, total_renewables / 5000.0) 
        effective_deficit = forecast_demand - (forecast_renewable_factor * forecast_demand * 0.3)
        
        predicted_runtime = node.current_storage / max(effective_deficit, 0.1)
        
        fail_prob_2h = min(100.0, max(0.0, (2.0 - predicted_runtime) / 2.0 * 100.0))
        fail_prob_8h = min(100.0, max(0.0, (8.0 - predicted_runtime) / 8.0 * 100.0))
        fail_prob_24h = min(100.0, max(0.0, (24.0 - predicted_runtime) / 24.0 * 100.0))
        
        # Weighted horizon score
        horizon_score = (fail_prob_2h * 0.6) + (fail_prob_8h * 0.3) + (fail_prob_24h * 0.1)

        # Escalation Stage
        escalation = get_escalation_stage(soc_pct, horizon_score)
        node.status = escalation # Sync status purely based on predictive stage

        # State Indicators
        soc_factor = (1.0 - soc) * 100.0
        demand_factor = min(1.0, max(0.0, demand_trend)) * 100.0
        damage_factor = node.infrastructure_damage or 0.0
        health_factor = (1.0 - (node.health_score / 100.0)) * 100.0 if node.health_score else 0.0
        
        # Logistics
        closest_amb_dist = 100.0
        for a in ambulances:
            d = haversine_distance(node.latitude, node.longitude, a.latitude, a.longitude)
            if d < closest_amb_dist: closest_amb_dist = d
        distance_factor = min(1.0, closest_amb_dist / 50.0) * 100.0

        # Determine if mission already assigned
        is_assigned = any(
            amb.target_node_id == node.id and amb.status in ["Dispatched", "Charging Node"]
            for amb in ambulances
        )

        # Weighted Sum (Normalize to 0-100)
        raw_score = (
            criticality_base * 0.10 + 
            horizon_score * 0.35 + 
            soc_factor * 0.10 + 
            damage_factor * 0.10 + 
            health_factor * 0.10 + 
            distance_factor * 0.10 + 
            pop_factor * 0.05 + 
            recovery_factor * 0.05 +
            demand_factor * 0.05
        )
        
        # Priority Decay (if assigned, smoothly lower priority to let others rise)
        if is_assigned:
            raw_score -= 30.0

        urgency_score = min(100.0, max(0.0, raw_score))

        # Priority Hysteresis (Exponential Smoothing)
        prev_score = PREVIOUS_SCORES.get(node.id, urgency_score)
        smoothed_score = (prev_score * 0.6) + (urgency_score * 0.4)
        PREVIOUS_SCORES[node.id] = smoothed_score
        
        final_score = smoothed_score

        # Ensure we always evaluate, no status gating
        dispatch_needed = True if not is_assigned else False
        
        # If there is no deficit, dispatch is strictly NOT needed.
        current_deficit = getattr(node, 'current_deficit', 0.0)
        if current_deficit <= 0.5:
            dispatch_needed = False

        prioritized_nodes.append((node, final_score, dispatch_needed))

    # Sort nodes by priority score descending
    prioritized_nodes.sort(key=lambda x: x[1], reverse=True)

    # 5. Priority-Based Mission Queue & Smart Dispatch
    # Because `prioritized_nodes` is sorted by highest urgency, evaluating it in order
    # inherently acts as a priority dequeue. The most critical nodes get the first
    # chance to pull an ambulance from `idle_ambulances`.
    idle_ambulances = [a for a in ambulances if a.status == "Idle"]
    
    for target_node, score, dispatch_eligible in prioritized_nodes:
        # Skip full strategy evaluation for healthy low-urgency nodes
        if score < 5.0 and not dispatch_eligible:
            continue

        # Generate multi-strategy evaluation
        strategies = pe.evaluate_optimization_strategies(
            target_node, idle_ambulances, battery_stations, sim_state, disaster, total_renewables
        )
        
        if not strategies:
            continue
            
        best_strategy = strategies[0]
        
        # Dispatch only when eligibility conditions are met
        if dispatch_eligible and best_strategy["strategy"] == "Dispatch Energy Ambulance":
            closest_amb = None
            min_dist = float('inf')
            best_selection_score = float('inf')
            
            if idle_ambulances:
                # --- Strategic Reserve Logic ---
                # Keep at least 1 ambulance available unless severity is high (>0.7) or score is critical (>90)
                reserve_needed = len(idle_ambulances) == 1 and (not disaster.active or disaster.severity < 0.7) and score < 90.0
                
                if not reserve_needed:
                    for amb in idle_ambulances:
                        # Calculate cost-weighted distance
                        raw_dist = haversine_distance(amb.latitude, amb.longitude, target_node.latitude, target_node.longitude)
                        effective_dist = raw_dist * route_distance_penalty
                        
                        # Assume ambulance consumes 0.5 kWh per effective km
                        consumption_to_target = effective_dist * 0.5
                        
                        # Find nearest charging station from target for the return trip
                        nearest_station_dist = float('inf')
                        for st in battery_stations:
                            d = haversine_distance(target_node.latitude, target_node.longitude, st.latitude, st.longitude)
                            if d < nearest_station_dist: nearest_station_dist = d
                        
                        return_dist_est = nearest_station_dist * route_distance_penalty
                        consumption_return = return_dist_est * 0.5
                        
                        # Payload: want to deliver at least enough to cover deficit, minimum 10kWh
                        payload_required = max(10.0, min(50.0, getattr(target_node, 'current_deficit', 10.0)))
                        
                        required_energy = consumption_to_target + consumption_return + payload_required
                        
                        # Only dispatch if it has enough charge to make the full round trip safely
                        if amb.current_energy >= required_energy:
                            # Weighted ambulance selection: ETA + distance + energy (lower = better)
                            eta_hours = effective_dist / max(base_ambulance_speed, 1.0)
                            energy_ratio = amb.current_energy / max(amb.battery_capacity, 1.0)
                            selection_score = (
                                eta_hours * 60.0 * 0.5
                                + effective_dist * 0.3
                                + (1.0 - energy_ratio) * 20.0
                            )
                            if selection_score < best_selection_score:
                                best_selection_score = selection_score
                                min_dist = effective_dist
                                closest_amb = amb

            existing_pending = next((d for d in existing_decisions if d.node_id == target_node.id and d.type == "Dispatch" and d.status == "Pending"), None)

            if closest_amb:
                soc_percent = (target_node.current_storage / max(target_node.max_capacity, 1.0) * 100.0)
                confidence = best_strategy.get("confidence", round(94.0 + random.uniform(0.5, 5.8), 1))
                eta = (min_dist / base_ambulance_speed) * 60.0  # minutes
                recovery_est = round((target_node.max_capacity - target_node.current_storage) / 100.0, 1) # transfer hours
                
                # Append ETA to the Chain-of-Thought action string
                explanation_str = best_strategy["reasoning"] + f" Routing {closest_amb.name} via optimal safe-path (ETA: {eta:.1f}m)."

                # Setup ambulance mission
                closest_amb.status = "Dispatched"
                closest_amb.target_node_id = target_node.id
                closest_amb.current_mission = f"Delivering backup power pack to {target_node.name}"
                closest_amb.eta_minutes = round(eta, 1)
                closest_amb.mission_id = f"MS-{sim_state.current_step}-{closest_amb.id}"
                closest_amb.source_name = "Battery Substation Base"
                closest_amb.destination_name = target_node.name
                closest_amb.progress = 0.0

                print(f"[AMB_VALIDATION] {closest_amb.name} transition: Idle -> Dispatched. Target: {target_node.name}, ETA: {eta:.1f}m, Mission: {closest_amb.mission_id}")

                idle_ambulances.remove(closest_amb)
                
                if existing_pending:
                    # Deduplication: Update the existing pending decision to executing instead of creating a new one
                    existing_pending.status = "Executing"
                    existing_pending.description = f"AI dispatched {closest_amb.name} to {target_node.name} (ETA: {eta:.1f}m)."
                    existing_pending.explanation = explanation_str
                    existing_pending.ambulance_distance = round(min_dist, 2)
                    existing_pending.recovery_time = recovery_est
                    existing_pending.priority_score = score
                    existing_pending.confidence_score = confidence
                else:
                    decisions_to_add.append(
                        AIDecision(
                            node_id=target_node.id,
                            type="Dispatch",
                            status="Executing",
                            priority_score=score,
                            description=f"AI dispatched {closest_amb.name} to {target_node.name} (ETA: {eta:.1f}m).",
                            battery_level=round(soc_percent, 1),
                            remaining_backup_time=round(target_node.survival_hours, 1),
                            disaster_severity=disaster.severity,
                            ambulance_distance=round(min_dist, 2),
                            recovery_time=recovery_est,
                            explanation=explanation_str,
                            optimization_strategies=json.dumps(strategies),
                            selected_strategy=best_strategy["strategy"],
                            cost_score=best_strategy["cost_score"],
                            reliability_score=best_strategy["reliability_score"],
                            sustainability_score=best_strategy["sustainability_score"],
                            confidence_score=confidence
                        )
                    )
            elif dispatch_eligible:
                # Deduplication: Only create Pending if one doesn't already exist
                if existing_pending:
                    existing_pending.priority_score = score
                    existing_pending.explanation = best_strategy["reasoning"] + " Awaiting available ambulance (Mission Queued)."
                    existing_pending.confidence_score = best_strategy.get("confidence", 90.0)
                else:
                    soc_percent = (target_node.current_storage / max(target_node.max_capacity, 1.0) * 100.0)
                    decisions_to_add.append(
                        AIDecision(
                            node_id=target_node.id,
                            type="Dispatch",
                            status="Pending",
                            priority_score=score,
                            description=f"AI queued {target_node.name} for emergency power (No ambulances available).",
                            battery_level=round(soc_percent, 1),
                            remaining_backup_time=round(target_node.survival_hours, 1),
                            disaster_severity=disaster.severity,
                            ambulance_distance=0.0,
                            recovery_time=0.0,
                            explanation=best_strategy["reasoning"] + " Awaiting available ambulance (Mission Queued).",
                            optimization_strategies=json.dumps(strategies),
                            selected_strategy="Pending Queue",
                            cost_score=best_strategy["cost_score"],
                            reliability_score=best_strategy["reliability_score"],
                            sustainability_score=best_strategy["sustainability_score"],
                            confidence_score=best_strategy.get("confidence", 90.0)
                        )
                    )
        else:
            # For non-dispatch strategies, still record the decision log with the Chain of Thought string
            soc_percent = (target_node.current_storage / max(target_node.max_capacity, 1.0) * 100.0)
            confidence = best_strategy.get("confidence", round(94.0 + random.uniform(0.5, 5.8), 1))
            explanation_str = best_strategy["reasoning"]
            
            # Deduplication for non-dispatch
            existing = db.query(AIDecision).filter(
                AIDecision.node_id == target_node.id, 
                AIDecision.status.in_(["Pending", "Executing"]),
                AIDecision.type == best_strategy["strategy"]
            ).first()
            
            if existing:
                existing.priority_score = score
                existing.explanation = explanation_str
                existing.confidence_score = confidence
            else:
                decisions_to_add.append(
                    AIDecision(
                        node_id=target_node.id,
                        type=best_strategy["strategy"],
                        description=f"AI initiated {best_strategy['strategy']} for {target_node.name}.",
                        priority_score=score,
                        status="Executing",
                        confidence_score=confidence,
                        battery_level=round(soc_percent, 1),
                        remaining_backup_time=round(target_node.survival_hours, 1),
                        criticality_level=target_node.criticality,
                        renewable_availability=round(total_renewables, 1),
                        disaster_severity=disaster.severity,
                        ambulance_distance=0.0,
                        recovery_time=0.0,
                        explanation=explanation_str,
                        optimization_strategies=json.dumps(strategies),
                        selected_strategy=best_strategy["strategy"],
                        cost_score=best_strategy["cost_score"],
                        reliability_score=best_strategy["reliability_score"],
                        sustainability_score=best_strategy["sustainability_score"]
                    )
                )

    # 6. Manage Dispatched/Charging Ambulances
    for amb in ambulances:
        if amb.status == "Dispatched" and amb.target_node_id:
            target = db.query(InfrastructureNode).filter(InfrastructureNode.id == amb.target_node_id).first()
            if target:
                dist = haversine_distance(amb.latitude, amb.longitude, target.latitude, target.longitude)
                step_dist = (amb.speed * pe.SIM_HOURS_PER_TICK)
                
                # Update progress percentage
                amb.progress = min(99.0, amb.progress + (step_dist / max(0.1, dist + step_dist)) * 100.0)

                if dist <= step_dist:
                    amb.latitude = target.latitude
                    amb.longitude = target.longitude
                    amb.status = "Charging Node"
                    amb.eta_minutes = 0.0
                    amb.progress = 100.0
                    amb.current_mission = f"Supplying power directly to {target.name}"
                    
                    print(f"[AMB_VALIDATION] {amb.name} transition: Dispatched -> Charging Node at {target.name}. Energy: {amb.current_energy:.1f} kWh")

                    soc_pct = (target.current_storage / max(target.max_capacity, 1.0)) * 100.0
                    explanation_arrival = (
                        f"{amb.name} has arrived at {target.name} and established an emergency coupling. "
                        f"Commenced high-speed energy transfer at 100 kW. Expected to fully balance "
                        f"backups in {((target.max_capacity - target.current_storage)/100.0):.2f} hours."
                    )

                    decisions_to_add.append(
                        AIDecision(
                            node_id=target.id,
                            type="Recharge",
                            description=f"{amb.name} arrived at {target.name}. Initiated rapid battery transfer.",
                            priority_score=95.0,
                            status="Executing",
                            confidence_score=99.9,
                            battery_level=round(soc_pct, 1),
                            remaining_backup_time=round(target.survival_hours, 1),
                            criticality_level=target.criticality,
                            renewable_availability=round(total_renewables, 1),
                            disaster_severity=disaster.severity,
                            ambulance_distance=0.0,
                            recovery_time=0.0,
                            explanation=explanation_arrival,
                            optimization_strategies="[]",
                            selected_strategy="Arrival Execution",
                            cost_score=100.0,
                            reliability_score=100.0,
                            sustainability_score=100.0
                        )
                    )
                else:
                    ratio = step_dist / max(0.1, dist)
                    amb.latitude += (target.latitude - amb.latitude) * ratio
                    amb.longitude += (target.longitude - amb.longitude) * ratio
                    new_dist = dist - step_dist
                    amb.eta_minutes = max(0.1, round((new_dist / base_ambulance_speed) * 60.0, 1))
                    
        elif amb.status == "Charging Node" and amb.target_node_id:
            target = db.query(InfrastructureNode).filter(InfrastructureNode.id == amb.target_node_id).first()
            if target:
                transfer_rate_kw = 100.0  # kW
                energy_to_transfer_kwh = transfer_rate_kw * pe.SIM_HOURS_PER_TICK  # kWh per tick
                actual_transfer_kwh = min(energy_to_transfer_kwh, amb.current_energy, target.max_capacity - target.current_storage)
                
                if actual_transfer_kwh > 0:
                    amb.current_energy -= actual_transfer_kwh
                    # Single Authority: Use update_battery for the target node
                    pe.update_battery(target, actual_transfer_kwh / pe.SIM_HOURS_PER_TICK, sim_state)
                    amb.energy_delivered += actual_transfer_kwh
                    if getattr(target, 'current_demand', 0) > 0:
                        target.survival_hours = target.current_storage / target.current_demand
                
                # Hysteresis: charge until target SOC > MISSION_COMPLETE_SOC (60%)
                target_soc_pct = (target.current_storage / max(target.max_capacity, 1.0)) * 100.0
                if amb.current_energy <= 5.0 or target_soc_pct >= MISSION_COMPLETE_SOC:
                    amb.status = "Returning"
                    amb.current_mission = "Returning to nearest Battery Station for recharge"
                    amb.progress = 0.0
                    
                    print(f"[AMB_VALIDATION] {amb.name} transition: Charging Node -> Returning. Target SOC reached or energy low ({amb.current_energy:.1f} kWh).")

                    closest_station = None
                    min_dist = float('inf')
                    for station in battery_stations:
                        d = haversine_distance(amb.latitude, amb.longitude, station.latitude, station.longitude) * route_distance_penalty
                        if d < min_dist:
                            min_dist = d
                            closest_station = station
                    
                    if closest_station:
                        amb.target_node_id = closest_station.id
                        amb.source_name = target.name
                        amb.destination_name = closest_station.name
                        eta = (min_dist / base_ambulance_speed) * 60.0
                        amb.eta_minutes = round(eta, 1)
                    else:
                        amb.target_node_id = None
                        amb.status = "Idle"
                        amb.current_mission = "Idle - Out of fuel, stationary"

        elif amb.status == "Returning" and amb.target_node_id:
            station = db.query(InfrastructureNode).filter(InfrastructureNode.id == amb.target_node_id).first()
            if station:
                dist = haversine_distance(amb.latitude, amb.longitude, station.latitude, station.longitude)
                step_dist = (amb.speed * pe.SIM_HOURS_PER_TICK)
                amb.progress = min(99.0, amb.progress + (step_dist / max(0.1, dist + step_dist)) * 100.0)

                if dist <= step_dist:
                    amb.latitude = station.latitude
                    amb.longitude = station.longitude
                    amb.status = "Recharging"
                    amb.current_mission = f"Recharging battery pack at {station.name}"
                    amb.eta_minutes = 0.0
                    amb.progress = round((amb.current_energy / max(amb.battery_capacity, 1.0)) * 100.0, 1)

                    print(f"[AMB_VALIDATION] {amb.name} transition: Returning -> Recharging at {station.name}. Start Energy: {amb.current_energy:.1f} kWh")
                else:
                    ratio = step_dist / max(0.1, dist)
                    amb.latitude += (station.latitude - amb.latitude) * ratio
                    amb.longitude += (station.longitude - amb.longitude) * ratio
                    new_dist = dist - step_dist
                    amb.eta_minutes = max(0.1, round((new_dist / base_ambulance_speed) * 60.0, 1))

        elif amb.status == "Recharging" and amb.target_node_id:
            station = db.query(InfrastructureNode).filter(InfrastructureNode.id == amb.target_node_id).first()
            if station:
                # Recharge only from ONLINE stations with available energy
                station_online = station.status != "Offline"
                if not station_online or station.current_storage <= 0.5:
                    # Station is dead/offline. Find another one if available, otherwise just wait.
                    closest_station = None
                    min_dist = float('inf')
                    for st in battery_stations:
                        if st.id != station.id and st.status != "Offline" and st.current_storage > 5.0:
                            d = haversine_distance(amb.latitude, amb.longitude, st.latitude, st.longitude)
                            if d < min_dist:
                                min_dist = d
                                closest_station = st
                    if closest_station:
                        amb.target_node_id = closest_station.id
                        amb.status = "Returning"
                        amb.source_name = station.name
                        amb.destination_name = closest_station.name
                        amb.eta_minutes = round((min_dist / base_ambulance_speed) * 60.0, 1)
                        amb.current_mission = f"Rerouting to {closest_station.name} for recharge"
                        print(f"[AMB_VALIDATION] {amb.name} transition: Recharging -> Returning (Station Empty). Rerouting to {closest_station.name}.")
                    else:
                        amb.current_mission = f"Waiting for {station.name} to generate energy"
                else:
                    charge_kw = AMBULANCE_RECHARGE_RATE
                    charge_this_tick_kwh = charge_kw * pe.SIM_HOURS_PER_TICK
                    charge_needed_kwh = amb.battery_capacity - amb.current_energy
                    actual_charge_kwh = min(charge_this_tick_kwh, charge_needed_kwh, max(0.0, station.current_storage))
                    
                    if actual_charge_kwh > 0:
                        amb.current_energy += actual_charge_kwh
                        # Single Authority: Use update_battery to discharge the station
                        pe.update_battery(station, -actual_charge_kwh / pe.SIM_HOURS_PER_TICK, sim_state)
                    
                    amb.progress = round((amb.current_energy / max(amb.battery_capacity, 1.0)) * 100.0, 1)
                    amb.current_mission = f"Recharging at {station.name} ({amb.progress:.0f}%)"
                    
                    print(f"[AMB_VALIDATION] {amb.name} is Recharging. Current Energy: {amb.current_energy:.1f} kWh (+{actual_charge_kwh:.1f} kWh)")

                    # Recharge complete: become idle when hitting threshold (e.g., 95%)
                    if amb.current_energy >= amb.battery_capacity * 0.95:
                        amb.status = "Idle"
                        amb.current_mission = "Idle - Ready for deployment"
                        
                        print(f"[AMB_VALIDATION] {amb.name} transition: Recharging -> Idle. Energy fully restored ({amb.current_energy:.1f} kWh). Mission data cleared.")
                        
                        # Mission Reuse: Wipe temporary data completely
                        amb.target_node_id = None
                        amb.mission_id = ""
                        amb.source_name = ""
                        amb.destination_name = ""
                        amb.eta_minutes = 0.0
                        amb.progress = 100.0

        elif amb.status == "Idle" and amb.current_energy < amb.battery_capacity:
            station, station_dist = find_nearest_station(amb, battery_stations)
            if station and station_dist <= 1.0 and station.status != "Offline" and station.current_storage > 0.5:
                charge_kw = AMBULANCE_RECHARGE_RATE
                charge_this_tick_kwh = charge_kw * pe.SIM_HOURS_PER_TICK
                charge_needed_kwh = amb.battery_capacity - amb.current_energy
                actual_charge_kwh = min(charge_this_tick_kwh, charge_needed_kwh, max(0.0, station.current_storage))
                if actual_charge_kwh > 0:
                    amb.current_energy += actual_charge_kwh
                    pe.update_battery(station, -actual_charge_kwh / pe.SIM_HOURS_PER_TICK, sim_state)
                    amb.progress = round((amb.current_energy / max(amb.battery_capacity, 1.0)) * 100.0, 1)
                    print(f"[AMB_VALIDATION] {amb.name} idle top-up at {station.name}. Current Energy: {amb.current_energy:.1f} kWh (+{actual_charge_kwh:.1f} kWh)")

    # 7. Load-Shedding / Energy Balancing (runs regardless of grid state)
    critical_infra_low_soc = [n for n in critical_consumers if (n.current_storage / max(n.max_capacity, 1)) < 0.25]
    for node in critical_infra_low_soc:
        potential_saving = node.base_demand * 0.20
        extended_hours = node.current_storage / max(0.1, (node.current_demand - potential_saving)) - node.survival_hours
        
        exists = db.query(AIDecision).filter(
            AIDecision.node_id == node.id,
            AIDecision.type == "Load Shedding",
            AIDecision.status == "Pending"
        ).first()
        
        if not exists and extended_hours > 0.5:
            # Calculate strategies for load shedding
            strategies = pe.evaluate_optimization_strategies(
                node, ambulances, battery_stations, sim_state, disaster, total_renewables
            )
            ls_strat = next((s for s in strategies if "Load Shedding" in s["strategy"]), None)
            if not ls_strat:
                continue

            soc_val = (node.current_storage / max(node.max_capacity, 1)) * 100.0
            explain_load = (
                f"Selected {ls_strat['strategy']} (Score: {ls_strat['overall_score']:.1f}). "
                f"Reasoning: {ls_strat['reasoning']}. "
                f"By shedding 20% of non-essential loads (saving {potential_saving:.1f} kW of electricity), "
                f"we extend the remaining survival duration by {extended_hours:.1f} hours."
            )

            decisions_to_add.append(
                AIDecision(
                    node_id=node.id,
                    type="Load Shedding",
                    description=f"Reduce non-critical operations at {node.name} by 20% (Saves {potential_saving:.1f}kW, extending runtime by {extended_hours:.1f}h).",
                    priority_score=75.0,
                    status="Pending",
                    confidence_score=91.5,
                    battery_level=round(soc_val, 1),
                    remaining_backup_time=round(node.survival_hours, 1),
                    criticality_level=node.criticality,
                    renewable_availability=round(total_renewables, 1),
                    disaster_severity=disaster.severity,
                    ambulance_distance=0.0,
                    recovery_time=extended_hours,
                    explanation=explain_load,
                    optimization_strategies=json.dumps(strategies),
                    selected_strategy=ls_strat["strategy"],
                    cost_score=ls_strat["cost_score"],
                    reliability_score=ls_strat["reliability_score"],
                    sustainability_score=ls_strat["sustainability_score"]
                )
            )

    if disaster.active and disaster.type == "Heatwave":
        exists = db.query(AIDecision).filter(
            AIDecision.type == "Grid Adjust",
            AIDecision.status == "Pending"
        ).first()
        if not exists:
            explain_heat = (
                "Initiating grid demand-response algorithms due to extreme heatdome temperatures. "
                "By capping non-critical residential AC systems and calling local energy reserves, "
                "we shave 15% off peak loading to protect substation transformers from thermal overload."
            )
            decisions_to_add.append(
                AIDecision(
                    type="Grid Adjust",
                    description="Heatwave Peak Demand: Initiate commercial demand-response, shedding 15% city-wide non-critical residential load.",
                    priority_score=80.0,
                    status="Pending",
                    confidence_score=94.2,
                    battery_level=0.0,
                    remaining_backup_time=0.0,
                    criticality_level="Low",
                    renewable_availability=round(total_renewables, 1),
                    disaster_severity=disaster.severity,
                    ambulance_distance=0.0,
                    recovery_time=0.0,
                    explanation=explain_heat,
                    optimization_strategies="[]",
                    selected_strategy="Demand Response",
                    cost_score=90.0,
                    reliability_score=85.0,
                    sustainability_score=100.0
                )
            )

    if decisions_to_add:
        db.add_all(decisions_to_add)

    db.commit()

