import sys
sys.path.insert(0, '.')
from backend.database import SessionLocal, init_db
from backend.simulation import run_simulation_step
from backend.models import SimulationState

# Init DB to ensure schema has new columns
init_db()

db = SessionLocal()
try:
    print('Running simulation step with new HRES Energy Manager...')
    run_simulation_step(db)
    
    state = db.query(SimulationState).first()
    if state:
        print(f'HRES Metrics:')
        print(f'  Renewable Pool: {state.renewable_pool} kW')
        print(f'  Solar Contribution: {state.solar_contribution_pct}%')
        print(f'  Wind Contribution: {state.wind_contribution_pct}%')
        print(f'  Renewable Coverage: {state.renewable_coverage_pct}%')
        print(f'  Renewable Utilization: {state.renewable_utilization_pct}%')
        print(f'  Curtailed Energy: {state.curtailed_energy} kWh')
        print(f'  Battery Charging: {state.battery_charging_power} kW')
        print(f'  Battery Discharging: {state.battery_discharging_power} kW')
        print(f'  Renewable Deficit: {state.renewable_deficit} kW')
        
    print('SUCCESS')
finally:
    db.close()
