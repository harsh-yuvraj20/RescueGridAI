import datetime
from sqlalchemy.orm import Session
from .database import engine, Base
from .models import InfrastructureNode, EnergyAmbulance, DisasterStatus, SimulationState

def seed_database(db: Session):
    # Check if we already have data
    if db.query(InfrastructureNode).first() is not None:
        print("Database already seeded. Skipping.")
        return

    # Base coords centered around Chennai, India.
    # Coordinates are arranged around Chennai so the Leaflet map shows a coherent metro-area grid.
    # Center: 13.0827, 80.2707
    lat_center, lng_center = 13.0827, 80.2707

    # 1. Solar Farms (3)
    solar_farms = [
        InfrastructureNode(
            name="North Chennai Solar Field Alpha",
            type="Solar Farm",
            latitude=13.1150,   # Madhavaram area
            longitude=80.2300,
            criticality="Low",
            base_demand=5.0,  # operational demand
            current_demand=5.0,
            max_capacity=300.0,  # Peak output kW
            current_storage=0.0,
            generation_output=180.0,
            status="Healthy",
            survival_hours=168.0,
            # New physics fields
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Tambaram Solar Array Beta",
            type="Solar Farm",
            latitude=12.9250,   # Tambaram south
            longitude=80.1270,
            criticality="Low",
            base_demand=8.0,
            current_demand=8.0,
            max_capacity=450.0,  # Peak output kW
            current_storage=0.0,
            generation_output=220.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Tidel Park Rooftop Grid Gamma",
            type="Solar Farm",
            latitude=12.9880,   # Tidel Park / Taramani
            longitude=80.2420,
            criticality="Low",
            base_demand=3.0,
            current_demand=3.0,
            max_capacity=150.0,  # Peak output kW
            current_storage=0.0,
            generation_output=90.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        )
    ]

    # 2. Wind Farms (2)
    wind_farms = [
        InfrastructureNode(
            name="Ennore Coastal Wind Farm 1",
            type="Wind Farm",
            latitude=13.2100,   # Ennore / North Chennai coast
            longitude=80.2550,
            criticality="Low",
            base_demand=12.0,
            current_demand=12.0,
            max_capacity=600.0,  # Max capacity kW
            current_storage=0.0,
            generation_output=320.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Mahabalipuram Wind Farm 2",
            type="Wind Farm",
            latitude=12.8700,   # South towards Mahabalipuram (inland)
            longitude=80.1900,
            criticality="Low",
            base_demand=10.0,
            current_demand=10.0,
            max_capacity=400.0,
            current_storage=0.0,
            generation_output=180.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        )
    ]

    # 3. Battery Stations (4)
    battery_stations = [
        InfrastructureNode(
            name="TANGEDCO Megapack Substation A",
            type="Battery Station",
            latitude=13.0700,   # Near Perambur / Purasawalkam
            longitude=80.2350,
            criticality="Medium",
            base_demand=15.0,  # Standby power
            current_demand=15.0,
            max_capacity=1200.0,  # kWh battery
            current_storage=960.0,  # 80% initial SoC
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Guindy Battery Grid B",
            type="Battery Station",
            latitude=13.0100,   # Guindy industrial area
            longitude=80.2130,
            criticality="Medium",
            base_demand=12.0,
            current_demand=12.0,
            max_capacity=1000.0,  # kWh battery
            current_storage=800.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Porur Storage Hub C",
            type="Battery Station",
            latitude=13.0350,   # Porur area
            longitude=80.1580,
            criticality="Medium",
            base_demand=10.0,
            current_demand=10.0,
            max_capacity=800.0,  # kWh battery
            current_storage=640.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Ennore Energy Block D",
            type="Battery Station",
            latitude=13.1650,   # Ennore / Tiruvottiyur
            longitude=80.2480,
            criticality="Medium",
            base_demand=10.0,
            current_demand=10.0,
            max_capacity=1500.0,  # kWh battery
            current_storage=1200.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        )
    ]

    # 4. Hospitals (6) - Critical High
    hospitals = [
        InfrastructureNode(
            name="Rajiv Gandhi Government General Hospital",
            type="Hospital",
            latitude=13.0870,   # Park Town (actual location)
            longitude=80.2750,
            criticality="High",
            base_demand=95.0,  # kW demand
            current_demand=95.0,
            max_capacity=400.0,  # Local Battery Backup Capacity kWh
            current_storage=320.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Stanley Medical College Hospital",
            type="Hospital",
            latitude=13.1130,   # Royapuram (actual location)
            longitude=80.2700,
            criticality="High",
            base_demand=110.0,
            current_demand=110.0,
            max_capacity=500.0,
            current_storage=400.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Apollo Greams Road Emergency Center",
            type="Hospital",
            latitude=13.0620,   # Greams Road / Thousand Lights
            longitude=80.2520,
            criticality="High",
            base_demand=85.0,
            current_demand=85.0,
            max_capacity=350.0,
            current_storage=280.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Institute of Child Health Egmore",
            type="Hospital",
            latitude=13.0780,   # Egmore (actual location)
            longitude=80.2600,
            criticality="High",
            base_demand=70.0,
            current_demand=70.0,
            max_capacity=300.0,
            current_storage=240.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Royapettah Government Hospital",
            type="Hospital",
            latitude=13.0530,   # Royapettah (actual location)
            longitude=80.2650,
            criticality="High",
            base_demand=60.0,
            current_demand=60.0,
            max_capacity=250.0,
            current_storage=200.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Adyar Cancer Institute Critical Care",
            type="Hospital",
            latitude=13.0040,   # Adyar (actual location)
            longitude=80.2350,
            criticality="High",
            base_demand=80.0,
            current_demand=80.0,
            max_capacity=350.0,
            current_storage=280.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        )
    ]

    # 5. Water Plants (4) - Critical High
    water_plants = [
        InfrastructureNode(
            name="Kilpauk Water Works Filtration Plant",
            type="Water Plant",
            latitude=13.0930,   # Kilpauk (actual location)
            longitude=80.2420,
            criticality="High",
            base_demand=75.0,
            current_demand=75.0,
            max_capacity=300.0,
            current_storage=240.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Red Hills Reservoir Pump Station",
            type="Water Plant",
            latitude=13.1800,   # Red Hills (actual location - north)
            longitude=80.1750,
            criticality="High",
            base_demand=60.0,
            current_demand=60.0,
            max_capacity=250.0,
            current_storage=200.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Kodungaiyur Sewage Treatment Plant",
            type="Water Plant",
            latitude=13.1350,   # Kodungaiyur (actual location)
            longitude=80.2500,
            criticality="High",
            base_demand=80.0,
            current_demand=80.0,
            max_capacity=320.0,
            current_storage=256.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="South Chennai Desalination Center",
            type="Water Plant",
            latitude=12.9400,   # South Chennai (inland from coast)
            longitude=80.1650,
            criticality="High",
            base_demand=90.0,
            current_demand=90.0,
            max_capacity=400.0,
            current_storage=320.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        )
    ]

    # 6. Telecom Towers (8) - Critical Medium
    telecom_towers = [
        InfrastructureNode(
            name="Anna Salai Emergency 5G Tower 1",
            type="Telecom Tower",
            latitude=13.0700,   # Anna Salai / Mount Road
            longitude=80.2580,
            criticality="Medium",
            base_demand=15.0,
            current_demand=15.0,
            max_capacity=60.0,
            current_storage=48.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="T Nagar Metro Tower 2",
            type="Telecom Tower",
            latitude=13.0430,   # T Nagar (actual location)
            longitude=80.2340,
            criticality="Medium",
            base_demand=18.0,
            current_demand=18.0,
            max_capacity=70.0,
            current_storage=56.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="George Town Repeater 3",
            type="Telecom Tower",
            latitude=13.0950,   # George Town / Parry's Corner
            longitude=80.2700,
            criticality="Medium",
            base_demand=12.0,
            current_demand=12.0,
            max_capacity=50.0,
            current_storage=40.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Madhavaram Tower 4",
            type="Telecom Tower",
            latitude=13.1500,   # Madhavaram
            longitude=80.2280,
            criticality="Medium",
            base_demand=15.0,
            current_demand=15.0,
            max_capacity=60.0,
            current_storage=48.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Velachery Tower 5",
            type="Telecom Tower",
            latitude=12.9800,   # Velachery
            longitude=80.2180,
            criticality="Medium",
            base_demand=15.0,
            current_demand=15.0,
            max_capacity=60.0,
            current_storage=48.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="ECR Coastline Repeater 6",
            type="Telecom Tower",
            latitude=12.9600,   # Near ECR but inland
            longitude=80.2450,
            criticality="Medium",
            base_demand=20.0,
            current_demand=20.0,
            max_capacity=80.0,
            current_storage=64.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Chennai Port Communications Mast 7",
            type="Telecom Tower",
            latitude=13.1000,   # Near Chennai Port (on land)
            longitude=80.2750,
            criticality="Medium",
            base_demand=14.0,
            current_demand=14.0,
            max_capacity=55.0,
            current_storage=44.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        ),
        InfrastructureNode(
            name="Guindy Communications Node 8",
            type="Telecom Tower",
            latitude=13.0150,   # Guindy
            longitude=80.2000,
            criticality="Medium",
            base_demand=16.0,
            current_demand=16.0,
            max_capacity=65.0,
            current_storage=52.0,
            generation_output=0.0,
            status="Healthy",
            survival_hours=168.0,
            total_energy_generated=0.0,
            total_energy_consumed=0.0,
            capacity_fade_pct=0.0,
            total_cycles=0.0,
            inverter_efficiency=0.95,
            temperature_derate=1.0,
            capacity_factor=0.0,
        )
    ]

    all_nodes = solar_farms + wind_farms + battery_stations + hospitals + water_plants + telecom_towers
    db.add_all(all_nodes)
    db.commit()  # commit to get ids

    # 7. Energy Ambulances (5)
    # Position them initially at the battery stations and other strategic centers
    ambulances = [
        EnergyAmbulance(
            name="Energy Ambulance 1",
            battery_capacity=300.0,  # kWh capacity
            current_energy=300.0,   # 100% full
            latitude=battery_stations[0].latitude,
            longitude=battery_stations[0].longitude,
            speed=50.0,
            status="Idle",
            current_mission="Idle at TANGEDCO Substation A - Ready to dispatch",
            target_node_id=None,
            eta_minutes=0.0
        ),
        EnergyAmbulance(
            name="Energy Ambulance 2",
            battery_capacity=300.0,
            current_energy=300.0,
            latitude=battery_stations[1].latitude,
            longitude=battery_stations[1].longitude,
            speed=50.0,
            status="Idle",
            current_mission="Idle at Guindy Grid B - Ready to dispatch",
            target_node_id=None,
            eta_minutes=0.0
        ),
        EnergyAmbulance(
            name="Energy Ambulance 3",
            battery_capacity=250.0,
            current_energy=250.0,
            latitude=battery_stations[2].latitude,
            longitude=battery_stations[2].longitude,
            speed=55.0,
            status="Idle",
            current_mission="Idle at Porur Hub C - Ready to dispatch",
            target_node_id=None,
            eta_minutes=0.0
        ),
        EnergyAmbulance(
            name="Energy Ambulance 4",
            battery_capacity=400.0,  # Heavy duty
            current_energy=400.0,
            latitude=battery_stations[3].latitude,
            longitude=battery_stations[3].longitude,
            speed=45.0,
            status="Idle",
            current_mission="Idle at Ennore Block D - Ready to dispatch",
            target_node_id=None,
            eta_minutes=0.0
        ),
        EnergyAmbulance(
            name="Energy Ambulance 5",
            battery_capacity=300.0,
            current_energy=300.0,
            latitude=lat_center,  # City center emergency pool
            longitude=lng_center,
            speed=50.0,
            status="Idle",
            current_mission="Idle at Chennai Emergency Hub - Ready to dispatch",
            target_node_id=None,
            eta_minutes=0.0
        )
    ]
    db.add_all(ambulances)

    # 8. Disaster Status (Initial: Normal)
    disaster = DisasterStatus(
        type="Normal",
        severity=0.0,
        active=False,
        affected_grid=False,
        description="Normal conditions. Power grid is stable. Renewables operating at standard parameters."
    )
    db.add(disaster)

    # 9. Simulation State (with Indian weather defaults and physics engine fields)
    sim_state = SimulationState(
        is_running=True,
        speed_multiplier=1.0,
        current_step=0,
        wind_speed=8.0,           # Indian coastal avg wind (m/s)
        solar_irradiance=600.0,   # Morning irradiance W/m²
        temperature=30.0,         # Indian tropical avg °C
        grid_status="Stable",
        carbon_saved=0.0,
        # New weather fields
        humidity=65.0,            # Indian avg humidity %
        cloud_cover=0.2,          # Mostly clear
        pressure=1013.25,         # Standard pressure hPa
        simulation_hour=10.0,     # Start at 10:00 AM IST
        prev_wind_speed=8.0,      # For AR(1) autocorrelation
        # New cost & carbon fields
        total_cost_avoided=0.0,
        total_carbon_avoided_net=0.0,
        grid_emission_factor=0.71,  # Indian grid CO₂ factor (CEA 2023)
        # Validation accumulators
        total_renewable_energy_kwh=0.0,
        total_demand_energy_kwh=0.0,
        total_battery_throughput_kwh=0.0,
    )
    db.add(sim_state)

    db.commit()
    print("Database seeding completed successfully. Indian grid parameters loaded.")

