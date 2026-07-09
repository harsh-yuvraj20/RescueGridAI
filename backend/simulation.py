"""
RescueGrid AI — Simulation Orchestrator
=========================================
Runs one tick of the grid simulation, delegating physics calculations
to physics_engine.py while preserving demo mode and all existing behavior.
"""

import random
import math
import json
import datetime
from sqlalchemy.orm import Session
from .models import InfrastructureNode, EnergyAmbulance, DisasterStatus, SimulationState, SimulationLog, BatteryHistory
from .decision_engine import run_ai_decision_engine
from . import physics_engine as pe
from . import energy_manager

# ─── Configurable SOC Thresholds for Consumer Node Status ───
CONSUMER_SOC_HEALTHY = 60.0      # SOC > 60% → Healthy
CONSUMER_SOC_WARNING = 40.0      # 60% >= SOC > 40% → Warning
CONSUMER_SOC_CRITICAL = 20.0     # 40% >= SOC > 20% → Critical
CONSUMER_SOC_EMERGENCY = 5.0     # 20% >= SOC > 5% → Emergency
                                 # SOC <= 5% → Offline
MAX_SURVIVAL_HOURS = 336.0       # 14-day cap for effectively unlimited runtime display
CONSUMER_RECHARGE_RATE = 10.0    # kW recharge rate when grid is online


def run_simulation_step(db: Session):
    """
    Executes one step of the physical grid simulation.
    Each tick represents SIM_HOURS_PER_TICK hours of simulated time.
    Updates weather, demand, renewable generation, batteries, node health, risk, and logs,
    and runs the AI Decision Engine.
    """
    # 1. Load active state
    sim_state = db.query(SimulationState).first()
    disaster = db.query(DisasterStatus).first()
    
    if not sim_state or not disaster:
        return

    sim_state.current_step += 1
    step = sim_state.current_step

    # --- ADVANCED DEMO MODE SCRIPT (PRESERVED) ---
    if sim_state.demo_mode:
        sim_state.demo_timer += 1
        timer = sim_state.demo_timer
        
        # 1-click script spanning 60-90 seconds (assuming ~30-45 steps if 2s ticks)
        # Phase 1 (steps 1-5): Cyclone warning, sky darkens.
        # Phase 2 (steps 6-12): Grid fails, solar flatlines, backups start draining.
        # Phase 3 (steps 13-20): AI computes priority, ambulance dispatches, moves on map.
        # Phase 4 (steps 21-30): Ambulance arrives at Rajiv Gandhi Government General Hospital, starts charging, restores it.
        # Phase 5 (steps 31-35): Validation metrics computed, scenario comparison generated.
        # Phase 6 (steps 36-40): Grid restored, cyclone passes, simulation returns to stable.
        
        if timer <= 5:
            sim_state.demo_phase = 1
            disaster.type = "Cyclone"
            disaster.active = True
            disaster.severity = 0.3
            disaster.affected_grid = False  # warning phase
            disaster.description = "DEMO PHASE 1: Cyclone warning broadcasted. Wind speeds rising, grid fluctuating. AI monitoring activated."
            sim_state.grid_status = "Unstable"
        elif timer <= 12:
            sim_state.demo_phase = 2
            disaster.severity = 0.85
            disaster.affected_grid = True
            disaster.description = "DEMO PHASE 2: Cyclone landing. Downed power poles detected. Main utility grid is OFFLINE. AI Decision Engine engaged."
            sim_state.grid_status = "Down"
            # Deplete Rajiv Gandhi Government General Hospital backup to force AI dispatch
            demo_hospital = db.query(InfrastructureNode).filter(InfrastructureNode.name.like("%Rajiv Gandhi%")).first()
            if demo_hospital:
                demo_hospital.current_storage = max(5.0, demo_hospital.current_storage - 40.0)
                demo_hospital.status = "Critical"
        elif timer <= 20:
            sim_state.demo_phase = 3
            disaster.description = "DEMO PHASE 3: AI Prioritization engaged. Multi-strategy optimization evaluating dispatch, load-shedding, and battery redistribution."
            # The decision engine will automatically dispatch an ambulance because the demo hospital is Critical.
        elif timer <= 30:
            sim_state.demo_phase = 4
            disaster.description = "DEMO PHASE 4: Mobile BESS coupling established. Rapid battery transfer in progress. Validation metrics updating in real-time."
        elif timer <= 35:
            sim_state.demo_phase = 5
            disaster.description = "DEMO PHASE 5: Engineering validation complete. Scenario comparison generated. Carbon and cost analysis finalized."
        elif timer <= 40:
            sim_state.demo_phase = 6
            disaster.type = "Normal"
            disaster.active = False
            disaster.severity = 0.0
            disaster.affected_grid = False
            disaster.description = "DEMO PHASE 6: Cyclone dissipated. Utility grid restored. All critical systems fully charged. Engineering report ready."
            sim_state.grid_status = "Stable"
            sim_state.demo_mode = False
            sim_state.demo_phase = 0
            sim_state.demo_timer = 0
            
            # Reset nodes to healthy
            nodes = db.query(InfrastructureNode).all()
            for node in nodes:
                node.status = "Healthy"
                node.infrastructure_damage = 0.0
                node.health_score = 100.0
                if node.max_capacity > 0:
                    node.current_storage = node.max_capacity * 0.85

    # 2. Simulate Weather (using physics engine)
    pe.simulate_weather(sim_state, disaster)

    # 3. Simulate Infrastructure Generation and Demand
    nodes = db.query(InfrastructureNode).all()
    
    total_renewables = 0.0
    total_demand = 0.0
    critical_infra_online = 0
    total_critical_infra = 0
    
    # Pre-classify nodes
    solar_farms = [n for n in nodes if n.type == "Solar Farm"]
    wind_farms = [n for n in nodes if n.type == "Wind Farm"]
    battery_stations = [n for n in nodes if n.type == "Battery Station"]
    consumers = [n for n in nodes if n.type in ["Hospital", "Water Plant", "Telecom Tower"]]
    generators = solar_farms + wind_farms

    # --- Calculate generation using physics engine ---
    for node in solar_farms:
        output = pe.calculate_solar_output(node, sim_state, disaster)
        total_renewables += output
        # Track cumulative energy
        if node.total_energy_generated is None:
            node.total_energy_generated = 0.0
        node.total_energy_generated += output * pe.SIM_HOURS_PER_TICK
    
    for node in wind_farms:
        output = pe.calculate_wind_output(node, sim_state, disaster)
        total_renewables += output
        if node.total_energy_generated is None:
            node.total_energy_generated = 0.0
        node.total_energy_generated += output * pe.SIM_HOURS_PER_TICK

    # Battery stations — no active generation
    for node in battery_stations:
        node.generation_output = 0.0
        node.current_demand = node.base_demand

    # --- Calculate demand using physics engine ---
    for node in consumers:
        demand = pe.calculate_demand(node, sim_state, disaster)
        total_demand += demand
        
        # Track cumulative consumption
        if getattr(node, 'total_energy_consumed', None) is None:
            node.total_energy_consumed = 0.0
        node.total_energy_consumed += demand * pe.SIM_HOURS_PER_TICK

    # 4. HRES: Renewable Energy Management & Smart Battery Strategy
    # This MUST run before consumer batteries drain, so renewables can cover the load first.
    energy_manager.optimize_energy_distribution(db, sim_state, disaster, nodes)

    # 5. Consumer backup battery management (Single Authority)
    for node in consumers:
        grid_online = not disaster.affected_grid and sim_state.grid_status == "Stable"
        if not grid_online:
            # Grid is down: consumer drains backup battery for the remaining deficit left by HRES
            deficit_kw = getattr(node, 'current_deficit', 0.0)
            if deficit_kw > 0.0:
                pe.update_battery(node, -deficit_kw, sim_state)
        else:
            # Grid is online: slowly recharge backup battery
            pe.update_battery(node, CONSUMER_RECHARGE_RATE, sim_state)

    # 6. DIGITAL TWIN HEALTH & DAMAGE CALCULATIONS
    for node in nodes:
        if node.health_score is None: node.health_score = 100.0
        if node.risk_score is None: node.risk_score = 0.0
        if node.infrastructure_damage is None: node.infrastructure_damage = 0.0

        # --- Progressive Disaster Effects ---
        if disaster.active:
            severity = disaster.severity
            duration_factor = min(2.0, (sim_state.current_step % 100) / 50.0) # Escalates over time
            
            # Use node ID and step for staggering (so they don't fail simultaneously)
            stagger = ((sim_state.current_step + node.id) % 3 == 0)
            
            if stagger:
                if disaster.type == "Cyclone":
                    if node.type == "Telecom Tower":
                        node.infrastructure_damage += 0.8 * severity * duration_factor
                    elif node.type in ["Solar Farm", "Wind Farm"]:
                        node.infrastructure_damage += 0.5 * severity
                    elif node.type == "Hospital":
                        node.infrastructure_damage += 0.1 * severity # Hardened
                        
                elif disaster.type == "Flood":
                    if node.type == "Water Plant":
                        node.infrastructure_damage += 0.2 * severity * (duration_factor ** 2)
                    elif node.type == "Battery Station":
                        node.infrastructure_damage += 0.4 * severity * duration_factor
                        
                elif disaster.type == "Earthquake":
                    if node.type == "Hospital":
                        node.infrastructure_damage += 0.2 * severity
                    else:
                        node.infrastructure_damage += 0.5 * severity
                        
                elif disaster.type == "Heatwave":
                    if node.type == "Battery Station":
                        node.infrastructure_damage += 0.3 * severity * duration_factor
                    elif node.type == "Solar Farm":
                        node.infrastructure_damage += 0.2 * severity
                        
            node.infrastructure_damage = min(100.0, node.infrastructure_damage)
        else:
            # repair slowly in normal grid conditions
            node.infrastructure_damage = max(0.0, node.infrastructure_damage - 0.8)

    # 7. Finalize Status and Runtime for Consumers
    for node in consumers:
        grid_online = not disaster.affected_grid and sim_state.grid_status == "Stable"
        # Health caps based on damage
        max_health = 100.0 - node.infrastructure_damage
        if getattr(node, 'status', "Healthy") == "Offline":
            node.health_score = max(0.0, node.health_score - 1.8)
        elif getattr(node, 'status', "Healthy") == "Critical":
            node.health_score = max(0.0, node.health_score - 0.5)
        elif getattr(node, 'status', "Healthy") == "Warning":
            node.health_score = max(0.0, node.health_score - 0.1)
        else:
            node.health_score = min(max_health, node.health_score + 1.0)
        node.health_score = min(max_health, node.health_score)
        
        # Recalculate survival_hours based on post-battery-update state
        if not grid_online and node.current_demand > 0.1:
            node.survival_hours = round(node.current_storage / node.current_demand, 3)
        else:
            node.survival_hours = MAX_SURVIVAL_HOURS

        # Dynamic consumer status based on SOC thresholds
        soc_pct = (node.current_storage / max(node.max_capacity, 1.0)) * 100.0
        if soc_pct <= CONSUMER_SOC_EMERGENCY:
            node.status = "Offline"
        elif soc_pct <= CONSUMER_SOC_CRITICAL:
            node.status = "Emergency"
        elif soc_pct <= CONSUMER_SOC_WARNING:
            node.status = "Critical"
        elif soc_pct <= CONSUMER_SOC_HEALTHY:
            node.status = "Warning"
        else:
            node.status = "Healthy"
            
        if node.status != "Offline":
            total_critical_infra += 1
            critical_infra_online += 1

        # Risk score formula
        disaster_risk = 45.0 * disaster.severity if disaster.active else 0.0
        soc_risk = 40.0 * (1.0 - soc_pct/100.0) if node.max_capacity > 0 else 0.0
        status_risk = 15.0 if node.status in ["Emergency", "Critical", "Offline"] else 0.0
        node.risk_score = min(100.0, max(0.0, disaster_risk + soc_risk + status_risk))

    # 5. Carbon & Cost Calculations (using physics engine)
    renewable_energy_this_tick = total_renewables * pe.SIM_HOURS_PER_TICK  # kWh
    
    # Carbon calculation with lifecycle accounting
    solar_energy = sum(n.generation_output for n in solar_farms) * pe.SIM_HOURS_PER_TICK
    wind_energy = sum(n.generation_output for n in wind_farms) * pe.SIM_HOURS_PER_TICK
    
    solar_carbon = pe.calculate_carbon(solar_energy, "Solar Farm", sim_state.grid_emission_factor)
    wind_carbon = pe.calculate_carbon(wind_energy, "Wind Farm", sim_state.grid_emission_factor)
    
    net_carbon_delta = solar_carbon["net_carbon_avoided_kg"] + wind_carbon["net_carbon_avoided_kg"]
    gross_carbon_delta = solar_carbon["gross_carbon_avoided_kg"] + wind_carbon["gross_carbon_avoided_kg"]
    
    sim_state.carbon_saved = round(sim_state.carbon_saved + gross_carbon_delta, 4)
    
    if sim_state.total_carbon_avoided_net is None:
        sim_state.total_carbon_avoided_net = 0.0
    sim_state.total_carbon_avoided_net = round(sim_state.total_carbon_avoided_net + net_carbon_delta, 4)
    
    # Cost calculation
    cost_delta = pe.calculate_cost(renewable_energy_this_tick, "Solar Farm")  # Avg renewable
    if sim_state.total_cost_avoided is None:
        sim_state.total_cost_avoided = 0.0
    sim_state.total_cost_avoided = round(sim_state.total_cost_avoided + cost_delta["net_savings_inr"], 2)
    
    # Accumulate validation totals
    if sim_state.total_renewable_energy_kwh is None:
        sim_state.total_renewable_energy_kwh = 0.0
    sim_state.total_renewable_energy_kwh += renewable_energy_this_tick
    
    if sim_state.total_demand_energy_kwh is None:
        sim_state.total_demand_energy_kwh = 0.0
    sim_state.total_demand_energy_kwh += total_demand * pe.SIM_HOURS_PER_TICK

    # 6. Update Validation Metrics (capacity factors etc.)
    pe.compute_all_validation_metrics(nodes, sim_state, disaster, total_renewables, total_demand)

    # 7. Run AI Decision Engine (PRESERVED — unchanged interface)
    run_ai_decision_engine(db, sim_state, disaster)

    # 8. Write Battery History (every 10 steps)
    if step % 10 == 0:
        for node in nodes:
            if node.max_capacity > 0:
                effective_capacity = node.max_capacity * (1.0 - (node.capacity_fade_pct or 0) / 100.0)
                soc = round((node.current_storage / max(effective_capacity, 1.0)) * 100.0, 1)
                db.add(BatteryHistory(node_id=node.id, soc=soc, timestamp=datetime.datetime.utcnow()))

    # 9. Create Periodic Simulation Log
    log_message = ""
    if step == 1:
        log_message = "Grid Simulation Initialized. Advanced physics engine active. Indian grid parameters loaded."
    elif step % 15 == 0:
        avg_soc_val = 0.0
        storage_nodes = [n for n in nodes if n.max_capacity > 0]
        if storage_nodes:
            avg_soc_val = sum((n.current_storage / n.max_capacity) * 100.0 for n in storage_nodes) / len(storage_nodes)
        
        hour_of_day = sim_state.simulation_hour % 24.0
        sim_hour_str = f"{int(hour_of_day):02d}:{int((hour_of_day % 1) * 60):02d}"
        
        if disaster.active:
            log_message = (
                f"Grid OFFLINE [{sim_hour_str}]. AI managing islanded grid. "
                f"Renewables: {total_renewables:.1f}kW, Demand: {total_demand:.1f}kW, "
                f"Storage SoC: {avg_soc_val:.1f}%. "
                f"Cost saved: ₹{sim_state.total_cost_avoided:.0f}. "
                f"Net CO₂ avoided: {sim_state.total_carbon_avoided_net:.2f}kg."
            )
        else:
            log_message = (
                f"Grid ONLINE [{sim_hour_str}]. Running merit-order dispatch optimization. "
                f"Renewable generation at {total_renewables:.1f}kW. "
                f"Cumulative savings: ₹{sim_state.total_cost_avoided:.0f}."
            )

    if log_message:
        avg_soc_val = 0.0
        storage_nodes = [n for n in nodes if n.max_capacity > 0]
        if storage_nodes:
            avg_soc_val = sum((n.current_storage / n.max_capacity) * 100.0 for n in storage_nodes) / len(storage_nodes)
            
        active_ambs = db.query(EnergyAmbulance).filter(EnergyAmbulance.status != "Idle").count()
        
        sim_log = SimulationLog(
            step=step,
            disaster_type=disaster.type,
            grid_status=sim_state.grid_status,
            renewable_output=total_renewables,
            battery_soc=avg_soc_val,
            critical_infra_online=critical_infra_online,
            active_ambulances=active_ambs,
            carbon_saved_delta=gross_carbon_delta,
            message=log_message
        )
        db.add(sim_log)

    # 10. Energy Conservation Validator
    for n in nodes:
        if getattr(n, 'current_storage', 0) < 0.0:
            print(f"CRITICAL: {n.name} has negative storage ({n.current_storage}). Resetting to 0.")
            n.current_storage = 0.0
        if getattr(n, 'max_capacity', 0) > 0 and getattr(n, 'current_storage', 0) > n.max_capacity:
            print(f"CRITICAL: {n.name} exceeds max capacity ({n.current_storage} > {n.max_capacity}). Capping.")
            n.current_storage = n.max_capacity

    for a in db.query(EnergyAmbulance).all():
        if getattr(a, 'current_energy', 0) < 0.0:
            print(f"CRITICAL: {a.name} has negative energy ({a.current_energy}). Resetting to 0.")
            a.current_energy = 0.0
        if getattr(a, 'current_energy', 0) > getattr(a, 'battery_capacity', 1.0):
            print(f"CRITICAL: {a.name} exceeds capacity ({a.current_energy} > {a.battery_capacity}). Capping.")
            a.current_energy = a.battery_capacity

    db.commit()

