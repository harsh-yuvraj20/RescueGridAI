import os
import sys
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure we can import from backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.database import Base, SessionLocal, engine
from backend.models import SimulationState, DisasterStatus, EnergyAmbulance, InfrastructureNode, AIDecision
from backend.simulation import run_simulation_step
import backend.physics_engine as pe

def run_validation():
    print("Starting 1000-tick automated validation run...")
    db = SessionLocal()
    
    # 1. Reset Disaster & Simulation state for a clean run
    sim_state = db.query(SimulationState).first()
    disaster = db.query(DisasterStatus).first()
    
    sim_state.current_step = 0
    sim_state.demo_mode = False
    
    disaster.active = False
    disaster.type = "Normal"
    disaster.severity = 0.0
    disaster.affected_grid = False
    
    # Reset ambulances
    ambs = db.query(EnergyAmbulance).all()
    for amb in ambs:
        amb.status = "Idle"
        amb.current_energy = amb.battery_capacity
        amb.energy_delivered = 0.0
        amb.target_node_id = None
        amb.mission_id = ""
        amb.progress = 100.0
        
    db.commit()

    # Track metrics
    amb_missions_completed = {amb.id: 0 for amb in ambs}
    total_energy_delivered = 0.0
    
    print("Beginning simulation loop...")
    for tick in range(1, 1001):
        if tick % 100 == 0:
            print(f"--- TICK {tick} ---")
            
        # Disaster triggers
        if tick == 50:
            print("\n>>> TRIGGERING CYCLONE (Severity 0.9) <<<")
            disaster.active = True
            disaster.type = "Cyclone"
            disaster.severity = 0.9
            disaster.affected_grid = True
            db.commit()
        elif tick == 300:
            print("\n>>> ENDING CYCLONE <<<")
            disaster.active = False
            disaster.type = "Normal"
            disaster.severity = 0.0
            disaster.affected_grid = False
            db.commit()
        elif tick == 500:
            print("\n>>> TRIGGERING EARTHQUAKE (Severity 0.9) <<<")
            disaster.active = True
            disaster.type = "Earthquake"
            disaster.severity = 0.9
            disaster.affected_grid = True
            db.commit()
        elif tick == 700:
            print("\n>>> ENDING EARTHQUAKE <<<")
            disaster.active = False
            disaster.type = "Normal"
            disaster.severity = 0.0
            disaster.affected_grid = False
            db.commit()

        # Save previous ambulance status to detect completed missions
        prev_amb_status = {amb.id: amb.status for amb in db.query(EnergyAmbulance).all()}
        
        # Run simulation tick
        run_simulation_step(db)
        db.commit()
        
        # Check transitions for metrics
        current_ambs = db.query(EnergyAmbulance).all()
        for amb in current_ambs:
            if prev_amb_status[amb.id] == "Recharging" and amb.status == "Idle":
                amb_missions_completed[amb.id] += 1
                
    # Final Metrics Collection
    print("\n======================================================")
    print("VALIDATION SIMULATION COMPLETE (1000 Ticks)")
    print("======================================================")
    
    total_ambs = db.query(EnergyAmbulance).all()
    for amb in total_ambs:
        print(f"Ambulance {amb.name} ({amb.id}):")
        print(f"  - Missions Completed: {amb_missions_completed[amb.id]}")
        print(f"  - Final Status: {amb.status}")
        print(f"  - Energy Delivered: {amb.energy_delivered:.1f} kWh")
        print(f"  - Final Current Energy: {amb.current_energy:.1f} kWh / {amb.battery_capacity} kWh")
        total_energy_delivered += amb.energy_delivered

    decisions = db.query(AIDecision).all()
    print(f"\nTotal AI Decisions Logged: {len(decisions)}")
    print(f"Pending Decisions: {sum(1 for d in decisions if d.status == 'Pending')}")
    print(f"Executing Decisions: {sum(1 for d in decisions if d.status == 'Executing')}")
    
    print("\nCheck [AMB_VALIDATION] tags in the log above for detailed state transitions.")

if __name__ == "__main__":
    run_validation()
