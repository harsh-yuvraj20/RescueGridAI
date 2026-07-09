import os
import asyncio
import datetime
import random
import math
import json
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from .database import engine, Base, get_db, SessionLocal
from .models import InfrastructureNode, EnergyAmbulance, DisasterStatus, SimulationState, SimulationLog, AIDecision, BatteryHistory
from .schemas import DashboardState, DisasterStatusBase, InfrastructureNodeResponse, EnergyAmbulanceResponse, AIDecisionResponse, SimulationLogResponse, BatteryHistoryResponse, DashboardMetrics
from .seed import seed_database
from .simulation import run_simulation_step
from .report_generator import generate_pdf_report
from . import physics_engine as pe

from sqlalchemy.exc import OperationalError

# Try to initialize database cleanly, fallback to recreate if schema mismatches
try:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Test queries to trigger schema errors if new columns are missing
    db.query(InfrastructureNode).first()
    db.query(SimulationState).first()
    seed_database(db)
    db.close()
except OperationalError:
    print("Schema mismatch detected! Automatically recreating the database...")
    # Clean up any open sessions
    try:
        db.close()
    except:
        pass
    
    # Drop all existing tables and recreate them with the latest schema
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Reseed the fresh database
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    print("Database schema upgraded and seeded successfully.")
except Exception as e:
    print(f"Critical error during database initialization: {e}")
    try:
        db.close()
    except:
        pass

app = FastAPI(title="RescueGrid AI Backend", description="AI-Powered Renewable Energy Resilience Platform APIs")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background simulation runner task
sim_task = None

async def run_simulation_loop():
    print("Starting simulation loop...")
    while True:
        try:
            db_session = SessionLocal()
            try:
                sim_state = db_session.query(SimulationState).first()
                if sim_state and sim_state.is_running:
                    run_simulation_step(db_session)
                    sleep_duration = max(0.5, 4.0 / sim_state.speed_multiplier)
                else:
                    sleep_duration = 4.0
            finally:
                db_session.close()
        except Exception as e:
            print(f"Error in background simulation loop: {e}")
            import traceback
            traceback.print_exc()
            sleep_duration = 4.0
        
        await asyncio.sleep(sleep_duration)

@app.on_event("startup")
async def startup_event():
    global sim_task
    sim_task = asyncio.create_task(run_simulation_loop())

@app.on_event("shutdown")
async def shutdown_event():
    global sim_task
    if sim_task:
        sim_task.cancel()

# --- INPUT SCHEMAS FOR NEW APIS ---
class AskQuery(BaseModel):
    query: str

# --- REST APIs ---

@app.get("/api/dashboard", response_model=DashboardState)
def get_dashboard_data(db: Session = Depends(get_db)):
    sim_state = db.query(SimulationState).first()
    disaster = db.query(DisasterStatus).first()
    nodes = db.query(InfrastructureNode).all()
    ambulances = db.query(EnergyAmbulance).all()
    
    # Calculate Metrics
    hospitals = [n for n in nodes if n.type == "Hospital"]
    water_plants = [n for n in nodes if n.type == "Water Plant"]
    telecom_towers = [n for n in nodes if n.type == "Telecom Tower"]
    solar_farms = [n for n in nodes if n.type == "Solar Farm"]
    wind_farms = [n for n in nodes if n.type == "Wind Farm"]
    battery_stations = [n for n in nodes if n.type == "Battery Station"]
    
    grid_available = not disaster.affected_grid and sim_state.grid_status == "Stable"
    grid_str = "OFFLINE" if not grid_available else "ONLINE"
    
    # Renewable output
    solar_gen = sum(n.generation_output for n in solar_farms)
    wind_gen = sum(n.generation_output for n in wind_farms)
    total_renewables = solar_gen + wind_gen
    
    # Battery SOC average (across all Battery Stations and critical nodes backups)
    storage_nodes = [n for n in nodes if n.max_capacity > 0]
    total_max = sum(n.max_capacity for n in storage_nodes)
    total_curr = sum(n.current_storage for n in storage_nodes)
    avg_soc = (total_curr / total_max * 100.0) if total_max > 0 else 0.0
    
    # Critical Nodes online
    critical_nodes = hospitals + water_plants + telecom_towers
    total_critical = len(critical_nodes)
    online_critical = sum(1 for n in critical_nodes if n.status != "Offline")
    
    # Active ambulances
    active_ambs = sum(1 for a in ambulances if a.status != "Idle")
    
    # Efficiency calculation
    total_rated_capacity = sum(n.max_capacity for n in solar_farms + wind_farms)
    efficiency = (total_renewables / total_rated_capacity * 100.0) if total_rated_capacity > 0 else 0.0
    
    # --- ENGINEERING KPI DASHBOARD CALCULATIONS ---
    # Diesel saved (Indian calculation)
    diesel_saved_litres = (sim_state.total_carbon_avoided_net or 0) / pe.DIESEL_KG_CO2_PER_L
    
    # Cost savings in INR
    cost_savings_inr = sim_state.total_cost_avoided or 0.0
    
    # Estimated lives impacted: 500 per online hospital, 1000 per water plant, 100 per tower.
    lives_impacted = 0
    for node in critical_nodes:
        if node.status != "Offline":
            if node.type == "Hospital":
                lives_impacted += 500
            elif node.type == "Water Plant":
                lives_impacted += 1000
            elif node.type == "Telecom Tower":
                lives_impacted += 100
                
    # AI Decision Latency (simulated around 14ms - 28ms)
    decision_latency = 12 + (sim_state.current_step % 17)
    
    # Average Recovery Time
    depleted_nodes = [n for n in critical_nodes if n.status in ["Warning", "Critical", "Offline"]]
    if depleted_nodes:
        avg_recovery = sum(n.survival_hours for n in depleted_nodes) / len(depleted_nodes)
    else:
        avg_recovery = 0.0
    if disaster.active:
        avg_recovery += (5.0 * disaster.severity)  # storm delay

    # --- NEW: Engineering KPIs ---
    # Renewable Penetration
    total_demand = sum(n.current_demand for n in critical_nodes)
    renewable_penetration = pe.calculate_renewable_penetration(total_renewables, total_demand) if total_demand > 0 else 0.0

    # Battery State of Health (avg across all battery-equipped nodes)
    battery_soh = pe.calculate_battery_health(nodes)

    # Renewable Utilization
    renewable_utilization = (total_renewables / max(total_rated_capacity, 0.1)) * 100.0

    # Grid Efficiency / System Efficiency
    system_efficiency = pe.calculate_system_efficiency(total_renewables, total_demand, 0)

    # Critical Infrastructure Availability
    critical_infra_availability = (online_critical / max(total_critical, 1)) * 100.0

    # Net carbon avoided (lifecycle-adjusted)
    net_carbon = sim_state.total_carbon_avoided_net or 0.0

    metrics = {
        "grid_status": grid_str,
        "renewable_output": round(total_renewables, 1),
        "battery_soc": round(avg_soc, 1),
        "critical_infra_online": online_critical,
        "total_critical_infra": total_critical,
        "active_ambulances": active_ambs,
        "total_ambulances": len(ambulances),
        "carbon_saved": round(sim_state.carbon_saved, 1),
        "diesel_saved": round(diesel_saved_litres, 1),
        "renewable_efficiency": round(efficiency, 1),
        "lives_impacted": lives_impacted,
        "decision_latency": decision_latency,
        "avg_recovery_time": round(avg_recovery, 1),
        # New engineering KPIs
        "renewable_penetration": round(renewable_penetration, 1),
        "grid_efficiency": round(system_efficiency, 1),
        "battery_soh": round(battery_soh, 1),
        "renewable_utilization": round(min(100.0, renewable_utilization), 1),
        "net_carbon_avoided": round(net_carbon, 2),
        "diesel_avoided_litres": round(diesel_saved_litres, 1),
        "cost_savings_inr": round(cost_savings_inr, 1),
        "critical_infra_availability": round(critical_infra_availability, 1),
        "system_efficiency": round(system_efficiency, 1),
        "simulation_hour": round(sim_state.simulation_hour, 1),
        # HRES Metrics
        "renewable_pool": round(getattr(sim_state, 'renewable_pool', 0.0), 1),
        "solar_contribution_pct": round(getattr(sim_state, 'solar_contribution_pct', 0.0), 1),
        "wind_contribution_pct": round(getattr(sim_state, 'wind_contribution_pct', 0.0), 1),
        "renewable_coverage_pct": round(getattr(sim_state, 'renewable_coverage_pct', 0.0), 1),
        "hres_renewable_utilization": round(getattr(sim_state, 'renewable_utilization_pct', 0.0), 1),
        "curtailed_energy": round(getattr(sim_state, 'curtailed_energy', 0.0), 1),
        "battery_charging_power": round(getattr(sim_state, 'battery_charging_power', 0.0), 1),
        "battery_discharging_power": round(getattr(sim_state, 'battery_discharging_power', 0.0), 1),
        "renewable_deficit": round(getattr(sim_state, 'renewable_deficit', 0.0), 1),
    }
    
    # Weather (extended)
    weather = {
        "wind_speed": round(sim_state.wind_speed, 1),
        "solar_irradiance": round(sim_state.solar_irradiance / 1000.0, 3),
        "temperature": round(sim_state.temperature, 1),
        "humidity": round(sim_state.humidity or 60.0, 1),
        "cloud_cover": round((sim_state.cloud_cover or 0.2) * 100.0, 1),  # Convert to %
        "pressure": round(sim_state.pressure or 1013.0, 1),
        "simulation_hour": round(sim_state.simulation_hour, 1),
    }
    
    # Recent items
    recent_decisions = db.query(AIDecision).order_by(AIDecision.timestamp.desc()).limit(8).all()
    recent_logs = db.query(SimulationLog).order_by(SimulationLog.timestamp.desc()).limit(12).all()
    
    return {
        "metrics": metrics,
        "weather": weather,
        "disaster": disaster,
        "nodes": nodes,
        "ambulances": ambulances,
        "recent_decisions": recent_decisions,
        "recent_logs": recent_logs
    }

@app.post("/api/simulator/disaster")
def trigger_disaster(data: DisasterStatusBase, db: Session = Depends(get_db)):
    disaster = db.query(DisasterStatus).first()
    sim_state = db.query(SimulationState).first()
    
    if not disaster or not sim_state:
        raise HTTPException(status_code=404, detail="Simulation state not found")
        
    disaster.type = data.type
    disaster.severity = data.severity
    disaster.active = (data.type != "Normal")
    disaster.affected_grid = (data.type != "Normal")
    disaster.start_time = datetime.datetime.utcnow()
    
    descriptions = {
        "Normal": "Normal conditions. Power grid is stable. Renewables operating at standard parameters.",
        "Cyclone": "Category 4 Cyclone incoming. High winds, torrential rain. Main electrical grid is severed. Solar arrays tilting to lock profile.",
        "Flood": "Severe river flooding. Substation transformer bays flooded. Grid offline. Key roadways blocked.",
        "Earthquake": "Magnitude 7.2 earthquake. Major infrastructure collapse, substation fire. Grid offline. Roads heavily damaged.",
        "Heatwave": "Extreme temperature anomaly (43°C). High load on AC units. Grid under extreme stress, brownouts. Wind power low.",
        "Cyber Attack": "Ransomware attack on Grid SCADA. Energy transmission controls corrupted. Battery readings unstable. Capping outputs."
    }
    
    disaster.description = data.description if data.description else descriptions.get(data.type, "Disaster Alert Active.")
    
    if data.type == "Normal":
        sim_state.grid_status = "Stable"
        nodes = db.query(InfrastructureNode).all()
        for node in nodes:
            node.status = "Healthy"
            node.infrastructure_damage = 0.0
            node.health_score = 100.0
            if node.max_capacity > 0:
                node.current_storage = node.max_capacity * 0.8
        
        # Reset ambulances
        ambulances = db.query(EnergyAmbulance).all()
        for amb in ambulances:
            amb.status = "Idle"
            amb.current_energy = amb.battery_capacity
            amb.current_mission = "Idle - Ready for deployment"
            amb.target_node_id = None
            amb.eta_minutes = 0.0
            amb.progress = 0.0
            amb.mission_id = ""
            amb.source_name = ""
            amb.destination_name = ""
    else:
        sim_state.grid_status = "Down"

    # Log disaster trigger
    log_msg = f"CRITICAL ALERT: Disaster [{data.type.upper()}] active. Grid status updated to {sim_state.grid_status.upper()}."
    db.add(SimulationLog(
        step=sim_state.current_step,
        disaster_type=disaster.type,
        grid_status=sim_state.grid_status,
        message=log_msg
    ))
    
    db.query(AIDecision).filter(AIDecision.status == "Pending").delete()
    db.commit()
    return {"message": f"Disaster state updated to {data.type}"}

@app.post("/api/simulator/control")
def control_simulation(action: str, speed: Optional[float] = 1.0, db: Session = Depends(get_db)):
    sim_state = db.query(SimulationState).first()
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation state not found")
        
    if action == "start":
        sim_state.is_running = True
    elif action == "pause":
        sim_state.is_running = False
    elif action == "speed":
        sim_state.speed_multiplier = speed
    elif action == "reset":
        # Reset entire DB
        db.query(BatteryHistory).delete()
        db.query(AIDecision).delete()
        db.query(SimulationLog).delete()
        db.query(EnergyAmbulance).delete()
        db.query(InfrastructureNode).delete()
        db.query(DisasterStatus).delete()
        db.query(SimulationState).delete()
        db.commit()
        seed_database(db)
        return {"message": "Simulation reset completed"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    db.commit()
    return {"message": f"Simulation control updated: {action}"}

# --- PROFESSIONAL CYCLONE DEMO MODE ENDPOINT ---
@app.post("/api/demo/cyclone")
def start_cyclone_demo(db: Session = Depends(get_db)):
    sim_state = db.query(SimulationState).first()
    disaster = db.query(DisasterStatus).first()
    
    if not sim_state or not disaster:
        raise HTTPException(status_code=404, detail="Simulation state not found")
        
    # Set to demo mode
    sim_state.is_running = True
    sim_state.speed_multiplier = 2.0  # Speed up to run in 60s
    sim_state.demo_mode = True
    sim_state.demo_phase = 1
    sim_state.demo_timer = 1
    
    disaster.type = "Cyclone"
    disaster.active = True
    disaster.severity = 0.3
    disaster.affected_grid = False
    disaster.description = "DEMO PHASE 1: Cyclone warning broadcasted. Wind speeds rising, grid fluctuating."
    sim_state.grid_status = "Unstable"
    
    db.query(AIDecision).delete()
    db.query(SimulationLog).delete()
    
    db.add(SimulationLog(
        step=sim_state.current_step,
        disaster_type="Cyclone",
        grid_status="Unstable",
        message="JUDGE DEMO MODE INITIATED: Category 4 Cyclone scenario timeline active. Full physics engine + AI optimization engaged."
    ))
    
    db.commit()
    return {"message": "Demo mode successfully triggered"}

# --- PREDICTIVE ANALYTICS FORECAST ENDPOINT (UPGRADED) ---
@app.get("/api/predictions")
def get_predictive_forecasts(db: Session = Depends(get_db)):
    sim_state = db.query(SimulationState).first()
    disaster = db.query(DisasterStatus).first()
    nodes = db.query(InfrastructureNode).all()
    
    # Use physics engine forecasts
    forecasts = pe.generate_forecasts(sim_state, disaster, nodes)
    
    # Also include legacy format for backward compatibility
    predictions_6h = forecasts.get("6h", [])
    predictions_24h = forecasts.get("24h", [])
    
    return {
        "predictions_1h": forecasts.get("1h", []),
        "predictions_6h": predictions_6h,
        "predictions_24h": predictions_24h,
    }

# --- NEW: VALIDATION METRICS ENDPOINT ---
@app.get("/api/validation")
def get_validation_metrics(db: Session = Depends(get_db)):
    sim_state = db.query(SimulationState).first()
    disaster = db.query(DisasterStatus).first()
    nodes = db.query(InfrastructureNode).all()
    
    generators = [n for n in nodes if n.type in ["Solar Farm", "Wind Farm"]]
    consumers = [n for n in nodes if n.type in ["Hospital", "Water Plant", "Telecom Tower"]]
    
    total_gen = sum(n.generation_output for n in generators)
    total_demand = sum(n.current_demand for n in consumers)
    
    # Compute all validation metrics via physics engine
    metrics = pe.compute_all_validation_metrics(nodes, sim_state, disaster, total_gen, total_demand)
    
    # Add cost and carbon metrics
    total_renewable_kwh = sim_state.total_renewable_energy_kwh or 0.0
    total_demand_kwh = sim_state.total_demand_energy_kwh or 0.0
    total_battery_kwh = sim_state.total_battery_throughput_kwh or 0.0
    
    cost_metrics = pe.calculate_cumulative_cost(total_renewable_kwh, total_battery_kwh)
    carbon_equivalents = pe.carbon_equivalents(sim_state.total_carbon_avoided_net or 0.0)
    
    metrics["cost"] = {
        "total_generation_cost_inr": cost_metrics["total_generation_cost_inr"],
        "diesel_baseline_cost_inr": cost_metrics["diesel_baseline_cost_inr"],
        "total_cost_avoided_inr": cost_metrics["total_cost_avoided_inr"],
        "solar_lcoe_inr": pe.SOLAR_LCOE_INR,
        "wind_lcoe_inr": pe.WIND_LCOE_INR,
        "battery_lcos_inr": pe.BATTERY_LCOS_INR,
        "diesel_cost_inr_per_kwh": pe.DIESEL_COST_INR_PER_KWH,
    }
    metrics["carbon"] = {
        "gross_carbon_avoided_kg": round(sim_state.carbon_saved, 2),
        "net_carbon_avoided_kg": round(sim_state.total_carbon_avoided_net or 0.0, 2),
        "grid_emission_factor": sim_state.grid_emission_factor,
        "equivalents": carbon_equivalents,
    }
    metrics["diesel_avoided"] = {
        "litres": round((sim_state.total_carbon_avoided_net or 0.0) / pe.DIESEL_KG_CO2_PER_L, 1),
        "cost_inr": round((sim_state.total_carbon_avoided_net or 0.0) / pe.DIESEL_KG_CO2_PER_L * pe.DIESEL_COST_INR_PER_L, 1),
    }
    metrics["totals"] = {
        "total_renewable_energy_kwh": round(total_renewable_kwh, 2),
        "total_demand_energy_kwh": round(total_demand_kwh, 2),
        "total_battery_throughput_kwh": round(total_battery_kwh, 2),
    }
    
    return metrics

# --- NEW: SCENARIO COMPARISON ENDPOINT ---
@app.get("/api/scenario-comparison")
def get_scenario_comparison(db: Session = Depends(get_db)):
    sim_state = db.query(SimulationState).first()
    disaster = db.query(DisasterStatus).first()
    nodes = db.query(InfrastructureNode).all()
    ambulances = db.query(EnergyAmbulance).all()
    
    comparison = pe.generate_scenario_comparison(nodes, ambulances, sim_state, disaster)
    return comparison

# --- AI INCIDENT COMMANDER AGENT ---
@app.post("/api/incident-commander/ask")
def ask_incident_commander(data: AskQuery, db: Session = Depends(get_db)):
    query = data.query.lower()
    
    sim_state = db.query(SimulationState).first()
    disaster = db.query(DisasterStatus).first()
    nodes = db.query(InfrastructureNode).all()
    ambulances = db.query(EnergyAmbulance).all()
    
    # Basic statistics
    hospitals = [n for n in nodes if n.type == "Hospital"]
    water_plants = [n for n in nodes if n.type == "Water Plant"]
    telecom_towers = [n for n in nodes if n.type == "Telecom Tower"]
    critical_nodes = hospitals + water_plants + telecom_towers
    
    solar_farms = [n for n in nodes if n.type == "Solar Farm"]
    wind_farms = [n for n in nodes if n.type == "Wind Farm"]
    total_renewables = sum(n.generation_output for n in solar_farms + wind_farms)
    
    total_max = sum(n.max_capacity for n in nodes if n.max_capacity > 0)
    total_curr = sum(n.current_storage for n in nodes if n.max_capacity > 0)
    avg_soc = (total_curr / total_max * 100.0) if total_max > 0 else 0.0
    
    online_count = sum(1 for n in critical_nodes if n.status != "Offline")
    total_critical = len(critical_nodes)
    
    # 1. Ask about specific Hospital priorities
    if "hospital" in query or "st. jude" in query or "valley general" in query or "prioritized" in query:
        critical_hosp = sorted(hospitals, key=lambda x: x.current_storage / x.max_capacity if x.max_capacity > 0 else 1.0)
        top_h = critical_hosp[0]
        soc_pct = (top_h.current_storage / top_h.max_capacity) * 100.0 if top_h.max_capacity > 0 else 0.0
        
        response = (
            f"AI Incident Commander: Critical nodes are prioritized based on active battery exhaustion. "
            f"Currently, {top_h.name} has the lowest backup storage level at {top_h.current_storage:.1f} kWh ({soc_pct:.1f}%), "
            f"yielding approximately {top_h.survival_hours:.1f} hours of survival runtime. "
            f"Under our active dispatch protocols, High-criticality medical structures receive top prioritization weighting "
            f"over medium-criticality water assets or telecom stations. An ambulance has been routed to recharge its backups."
        )
        return {"response": response}
        
    # 2. Ask about Energy Ambulances
    elif "ambulance" in query or "dispatch" in query or "truck" in query:
        dispatched = [a for a in ambulances if a.status != "Idle"]
        idle = [a for a in ambulances if a.status == "Idle"]
        
        if dispatched:
            active_desc = ", ".join([f"{a.name} heading to {a.destination_name} (ETA: {a.eta_minutes}m)" for a in dispatched[:2]])
            response = (
                f"AI Incident Commander: We have {len(dispatched)} mobile BESS vehicles deployed on active routing missions: "
                f"{active_desc}. We currently maintain {len(idle)} backup vehicles idle in the emergency reserve pools. "
                f"Dispatches are assigned to the closest available vehicles using haversine calculation to minimize transit delay "
                f"along affected city routes."
            )
        else:
            response = (
                f"AI Incident Commander: All {len(ambulances)} Energy Ambulances are currently stationed at Megapack battery substations "
                f"in standby mode. Since the utility grid is stable or local node reserves are above safety margins, "
                f"the AI is holding dispatches to conserve battery cycles."
            )
        return {"response": response}
        
    # 3. Ask about Disaster effects (Cyclone, Flood, etc)
    elif "cyclone" in query or "flood" in query or "disaster" in query or "earthquake" in query:
        if disaster.active:
            response = (
                f"AI Incident Commander: An active {disaster.type} event is logged with a severity index of {(disaster.severity*100):.0f}%. "
                f"This triggers immediate physical limits: Solar array outputs are capped to 5% due to protective mechanical panel locking, "
                f"and road accessibility restricts Energy Ambulance speeds to {18 if disaster.type == 'Cyclone' else 12} km/h. "
                f"Our primary objective is to maintain critical hospital loads for up to 7 days by routing wind reserves and dispatches."
            )
        else:
            response = (
                f"AI Incident Commander: No environmental disasters are currently active on the grid. "
                f"If a Cyclone or Flood were to trigger, solar generation would drop by 80-95% due to cloud cover and structural safety angles, "
                f"and ambulances would face significant road closures, decreasing speeds by 60%."
            )
        return {"response": response}

    # 4. Ask about cost/savings
    elif "cost" in query or "savings" in query or "money" in query or "rupee" in query or "inr" in query:
        cost_avoided = sim_state.total_cost_avoided or 0.0
        carbon = sim_state.total_carbon_avoided_net or 0.0
        diesel_avoided = carbon / pe.DIESEL_KG_CO2_PER_L
        response = (
            f"AI Incident Commander: Cumulative cost savings vs diesel baseline: ₹{cost_avoided:.0f} INR. "
            f"Total diesel avoided: {diesel_avoided:.1f} litres. Net carbon avoided (lifecycle-adjusted): {carbon:.2f} kg CO₂. "
            f"Solar LCOE: ₹{pe.SOLAR_LCOE_INR}/kWh, Wind: ₹{pe.WIND_LCOE_INR}/kWh vs Diesel: ₹{pe.DIESEL_COST_INR_PER_KWH:.1f}/kWh."
        )
        return {"response": response}
        
    # 5. Fallback status summary
    else:
        response = (
            f"AI Incident Commander: Grid telemetry normal. Total renewable generation is currently at {total_renewables:.1f} kW. "
            f"Average storage state of charge is {avg_soc:.1f}% across all batteries. "
            f"Critical infrastructure load coverage rate is currently at {round(online_count/total_critical*100, 1)}% "
            f"({online_count} of {total_critical} nodes online). "
            f"Cumulative savings: ₹{sim_state.total_cost_avoided or 0:.0f} INR. "
            f"Ask me about hospital priorities, ambulance dispatches, storm impacts, or cost savings."
        )
        return {"response": response}

# --- REMAINING STANDARD APIS ---

@app.get("/api/infrastructure", response_model=List[InfrastructureNodeResponse])
def get_infrastructure(db: Session = Depends(get_db)):
    return db.query(InfrastructureNode).all()

@app.post("/api/infrastructure/{node_id}/toggle")
def toggle_node(node_id: int, db: Session = Depends(get_db)):
    node = db.query(InfrastructureNode).filter(InfrastructureNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node.status = "Offline" if node.status != "Offline" else "Healthy"
    db.commit()
    return {"message": f"Node {node.name} status toggled to {node.status}"}

@app.get("/api/ambulance", response_model=List[EnergyAmbulanceResponse])
def get_ambulances(db: Session = Depends(get_db)):
    return db.query(EnergyAmbulance).all()

@app.get("/api/decision", response_model=List[AIDecisionResponse])
def get_decisions(db: Session = Depends(get_db)):
    return db.query(AIDecision).order_by(AIDecision.timestamp.desc()).all()

@app.post("/api/decision/{decision_id}/action")
def execute_decision_action(decision_id: int, db: Session = Depends(get_db)):
    decision = db.query(AIDecision).filter(AIDecision.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    decision.status = "Completed"
    db.commit()
    return {"message": f"Recommendation '{decision.description}' marked as completed."}

@app.get("/api/history", response_model=List[BatteryHistoryResponse])
def get_battery_history(db: Session = Depends(get_db)):
    return db.query(BatteryHistory).order_by(BatteryHistory.timestamp.desc()).limit(100).all()

@app.get("/api/analytics")
def get_analytics_charts(db: Session = Depends(get_db)):
    nodes = db.query(InfrastructureNode).all()
    logs = db.query(SimulationLog).order_by(SimulationLog.timestamp.asc()).limit(50).all()
    sim_state = db.query(SimulationState).first()
    
    battery_socs = []
    for n in nodes:
        if n.max_capacity > 0:
            soc = (n.current_storage / n.max_capacity * 100.0) if n.max_capacity > 0 else 0.0
            battery_socs.append({
                "name": n.name,
                "type": n.type,
                "soc": round(soc, 1),
                "capacity_fade": round(n.capacity_fade_pct or 0, 2),
                "total_cycles": round(n.total_cycles or 0, 1),
                "capacity_factor": round(n.capacity_factor or 0, 4),
            })
            
    timeline = []
    for log in logs:
        timeline.append({
            "step": log.step,
            "timestamp": log.timestamp.strftime("%H:%M:%S"),
            "renewables": round(log.renewable_output, 1),
            "battery_soc": round(log.battery_soc, 1),
            "infra_online": log.critical_infra_online,
            "carbon_saved_delta": round(log.carbon_saved_delta, 2)
        })
    
    # Add engineering analytics
    cost_data = {
        "total_cost_avoided_inr": round(sim_state.total_cost_avoided or 0, 1),
        "solar_lcoe": pe.SOLAR_LCOE_INR,
        "wind_lcoe": pe.WIND_LCOE_INR,
        "diesel_cost_per_kwh": round(pe.DIESEL_COST_INR_PER_KWH, 1),
    }
    carbon_data = {
        "gross_avoided_kg": round(sim_state.carbon_saved, 2),
        "net_avoided_kg": round(sim_state.total_carbon_avoided_net or 0, 2),
        "grid_factor": sim_state.grid_emission_factor,
    }
        
    return {
        "battery_socs": battery_socs,
        "timeline": timeline,
        "cost": cost_data,
        "carbon": carbon_data,
    }

@app.get("/api/report/export")
def export_report_pdf(db: Session = Depends(get_db)):
    filepath = "rescuegrid_resilience_report.pdf"
    generate_pdf_report(db, filepath)
    
    if os.path.exists(filepath):
        return FileResponse(
            filepath,
            media_type="application/pdf",
            filename="rescuegrid_resilience_report.pdf"
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to generate PDF report")

