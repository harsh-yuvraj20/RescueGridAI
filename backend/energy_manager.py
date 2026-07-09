from sqlalchemy.orm import Session
from .models import InfrastructureNode, SimulationState, DisasterStatus
from . import physics_engine as pe

def optimize_energy_distribution(db: Session, sim_state: SimulationState, disaster: DisasterStatus, nodes: list[InfrastructureNode]):
    """
    Hybrid Renewable Energy Management System (HRES) Layer.
    Executes BEFORE the AI Decision Engine.
    Allocates renewable energy to critical loads and manages stationary battery charging/discharging.
    Leaves any unresolved deficit in node.current_deficit for the AI to handle via ambulances.
    """
    
    # 1. Collect Available Energy
    solar_farms = [n for n in nodes if n.type == "Solar Farm" and n.status != "Offline"]
    wind_farms = [n for n in nodes if n.type == "Wind Farm" and n.status != "Offline"]
    battery_stations = [n for n in nodes if n.type == "Battery Station"]
    
    total_solar_kw = sum(n.generation_output for n in solar_farms)
    total_wind_kw = sum(n.generation_output for n in wind_farms)
    renewable_pool_kw = total_solar_kw + total_wind_kw
    
    # 2. Collect Demand & Categorize Consumers
    hospitals = [n for n in nodes if n.type == "Hospital"]
    water_plants = [n for n in nodes if n.type == "Water Plant"]
    telecom = [n for n in nodes if n.type == "Telecom Tower"]
    
    # Sort consumers within categories by current demand (descending) or criticality
    hospitals.sort(key=lambda n: n.current_demand, reverse=True)
    water_plants.sort(key=lambda n: n.current_demand, reverse=True)
    telecom.sort(key=lambda n: n.current_demand, reverse=True)
    
    # Ordered priority list for allocation
    priority_consumers = hospitals + water_plants + telecom
    total_consumer_demand_kw = sum(n.current_demand for n in priority_consumers)
    
    # 3. Renewable Energy Allocation
    remaining_renewable_kw = renewable_pool_kw
    
    for node in priority_consumers:
        # We start with the assumption that the node's demand is its deficit
        node.current_deficit = node.current_demand
        
        # If the grid is online and stable, the grid satisfies all demand, no deficit
        grid_online = not disaster.affected_grid and sim_state.grid_status == "Stable"
        if grid_online:
            node.current_deficit = 0.0
            continue
            
        # Allocate renewables
        if remaining_renewable_kw > 0:
            allocated = min(node.current_deficit, remaining_renewable_kw)
            node.current_deficit -= allocated
            remaining_renewable_kw -= allocated

    # 4 & 5. Energy Balancing & Smart Battery Strategy
    total_charging_kw = 0.0
    total_discharging_kw = 0.0
    grid_online = not disaster.affected_grid and sim_state.grid_status == "Stable"
    
    if grid_online:
        # If grid is online, charge batteries from the grid at a fixed rate
        for station in battery_stations:
            charge_kw = 50.0  # Base grid charging rate
            # We don't track grid charging in HRES metrics specifically, but it restores the battery
            pe.update_battery(station, charge_kw, sim_state)
            total_charging_kw += charge_kw
    else:
        # Grid is offline. Use renewables and stationary batteries
        
        if remaining_renewable_kw > 0:
            # Case 1: Surplus Generation -> Charge batteries
            # Smart Strategy: Forecast check (simplified): Always charge if surplus exists
            charge_per_station = remaining_renewable_kw / max(len(battery_stations), 1)
            for station in battery_stations:
                # pe.update_battery handles max_capacity capping internally
                pe.update_battery(station, charge_per_station, sim_state)
            total_charging_kw = remaining_renewable_kw
            
        else:
            # Case 2: Generation Deficit -> Discharge batteries to cover unserved load
            total_deficit_kw = sum(n.current_deficit for n in priority_consumers)
            
            if total_deficit_kw > 0 and battery_stations:
                discharge_needed_kw = total_deficit_kw
                discharge_per_station = discharge_needed_kw / len(battery_stations)
                
                actual_total_discharge_kw = 0.0
                for station in battery_stations:
                    # Determine how much we can actually pull (can't pull if empty)
                    # pe.update_battery uses negative for discharge
                    available_power = station.current_storage / pe.SIM_HOURS_PER_TICK
                    actual_pull_kw = min(discharge_per_station, available_power)
                    
                    pe.update_battery(station, -actual_pull_kw, sim_state)
                    actual_total_discharge_kw += actual_pull_kw
                
                total_discharging_kw = actual_total_discharge_kw
                
                # We discharged some power. Distribute it to reduce the current_deficit.
                # Since all batteries feed into the microgrid, we reduce the deficits in priority order.
                remaining_discharge_kw = actual_total_discharge_kw
                for node in priority_consumers:
                    if node.current_deficit > 0 and remaining_discharge_kw > 0:
                        covered = min(node.current_deficit, remaining_discharge_kw)
                        node.current_deficit -= covered
                        remaining_discharge_kw -= covered

    # 7. Curtailment Management
    curtailed_kw = 0.0
    if not grid_online and remaining_renewable_kw > 0:
        # We charged batteries with the surplus. Check if batteries are actually full.
        max_charge_capacity_kw = sum(max(0.0, (s.max_capacity - s.current_storage)) / pe.SIM_HOURS_PER_TICK for s in battery_stations)
        if remaining_renewable_kw > max_charge_capacity_kw:
            curtailed_kw = remaining_renewable_kw - max_charge_capacity_kw
            
    # Calculate Utilization
    used_renewable_kw = renewable_pool_kw - curtailed_kw
    utilization_pct = (used_renewable_kw / renewable_pool_kw * 100.0) if renewable_pool_kw > 0 else 0.0
    coverage_pct = (used_renewable_kw / total_consumer_demand_kw * 100.0) if total_consumer_demand_kw > 0 else 100.0

    # 9. Update SimulationState Metrics
    sim_state.renewable_pool = round(renewable_pool_kw, 2)
    sim_state.solar_contribution_pct = round((total_solar_kw / renewable_pool_kw * 100.0) if renewable_pool_kw > 0 else 0.0, 1)
    sim_state.wind_contribution_pct = round((total_wind_kw / renewable_pool_kw * 100.0) if renewable_pool_kw > 0 else 0.0, 1)
    sim_state.renewable_coverage_pct = round(min(100.0, coverage_pct), 1)
    sim_state.renewable_utilization_pct = round(min(100.0, utilization_pct), 1)
    sim_state.curtailed_energy = round(curtailed_kw * pe.SIM_HOURS_PER_TICK, 2)
    sim_state.battery_charging_power = round(total_charging_kw, 2)
    sim_state.battery_discharging_power = round(total_discharging_kw, 2)
    
    total_remaining_deficit = sum(n.current_deficit for n in priority_consumers)
    sim_state.renewable_deficit = round(total_remaining_deficit, 2)
