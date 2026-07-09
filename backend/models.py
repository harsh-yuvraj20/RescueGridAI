import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base

class InfrastructureNode(Base):
    __tablename__ = "infrastructure_nodes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # Hospital, Water Plant, Telecom Tower, Solar Farm, Wind Farm, Battery Station
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    criticality = Column(String, default="Low")  # High, Medium, Low
    
    # Energy variables
    base_demand = Column(Float, default=0.0)  # in kW
    current_demand = Column(Float, default=0.0)  # in kW
    max_capacity = Column(Float, default=0.0)  # in kWh (for batteries or peak solar/wind capacity)
    current_storage = Column(Float, default=0.0)  # in kWh
    generation_output = Column(Float, default=0.0)  # in kW (for solar/wind farms)
    
    status = Column(String, default="Healthy")  # Healthy, Warning, Critical, Offline
    survival_hours = Column(Float, default=168.0)  # 7 days max, initially
    
    # Advanced Digital Twin scores
    health_score = Column(Float, default=100.0)      # 0 to 100%
    risk_score = Column(Float, default=0.0)          # 0 to 100%
    infrastructure_damage = Column(Float, default=0.0) # 0 to 100%
    
    # --- NEW: Physics Engine Fields ---
    total_energy_generated = Column(Float, default=0.0)   # Cumulative kWh generated
    total_energy_consumed = Column(Float, default=0.0)    # Cumulative kWh consumed
    capacity_fade_pct = Column(Float, default=0.0)        # Battery degradation %
    total_cycles = Column(Float, default=0.0)             # Cumulative battery cycles
    inverter_efficiency = Column(Float, default=0.95)     # Current inverter η
    temperature_derate = Column(Float, default=1.0)       # Current thermal derate factor
    capacity_factor = Column(Float, default=0.0)          # Running capacity factor (0-1)
    
    # --- NEW: HRES Fields ---
    current_deficit = Column(Float, default=0.0)          # Unserved load after renewables & batteries
    
    # Relationships
    ambulances = relationship("EnergyAmbulance", back_populates="target_node")

class EnergyAmbulance(Base):
    __tablename__ = "energy_ambulances"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    battery_capacity = Column(Float, default=200.0)  # in kWh
    current_energy = Column(Float, default=200.0)  # in kWh
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed = Column(Float, default=50.0)  # in km/h
    status = Column(String, default="Idle")  # Idle, Dispatched, Charging Node, Returning
    current_mission = Column(String, default="Idle - Ready for deployment")
    target_node_id = Column(Integer, ForeignKey("infrastructure_nodes.id"), nullable=True)
    eta_minutes = Column(Float, default=0.0)
    
    # Advanced mission details
    mission_id = Column(String, default="")
    source_name = Column(String, default="")
    destination_name = Column(String, default="")
    energy_delivered = Column(Float, default=0.0)  # Total kWh delivered in life
    progress = Column(Float, default=0.0)          # 0 to 100% progress of current mission
    
    # Relationships
    target_node = relationship("InfrastructureNode", back_populates="ambulances")

class DisasterStatus(Base):
    __tablename__ = "disaster_status"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, default="Normal")  # Normal, Cyclone, Flood, Earthquake, Heatwave, Cyber Attack
    severity = Column(Float, default=0.0)  # 0.0 to 1.0
    active = Column(Boolean, default=False)
    affected_grid = Column(Boolean, default=False)  # Is electrical grid offline?
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    description = Column(String, default="Normal conditions. Grid stable.")

class SimulationState(Base):
    __tablename__ = "simulation_state"

    id = Column(Integer, primary_key=True, index=True)
    is_running = Column(Boolean, default=True)
    speed_multiplier = Column(Float, default=1.0)
    current_step = Column(Integer, default=0)
    wind_speed = Column(Float, default=15.0)  # m/s
    solar_irradiance = Column(Float, default=600.0)  # W/m²
    temperature = Column(Float, default=24.0)  # Celsius
    grid_status = Column(String, default="Stable")  # Stable, Unstable, Down
    carbon_saved = Column(Float, default=0.0)  # cumulative kg of CO2 saved
    
    # --- NEW: Advanced Weather Fields ---
    humidity = Column(Float, default=60.0)              # % relative humidity
    cloud_cover = Column(Float, default=0.2)            # 0-1 fraction
    pressure = Column(Float, default=1013.25)           # hPa atmospheric pressure
    simulation_hour = Column(Float, default=10.0)       # Virtual hour of day (0-24)
    prev_wind_speed = Column(Float, default=15.0)       # For AR(1) autocorrelation
    
    # --- NEW: Cumulative Cost & Carbon ---
    total_cost_avoided = Column(Float, default=0.0)     # Cumulative INR saved vs diesel
    total_carbon_avoided_net = Column(Float, default=0.0)  # Net CO₂ kg with lifecycle
    grid_emission_factor = Column(Float, default=0.71)  # kg CO₂/kWh (Indian avg)
    
    # --- NEW: Validation Accumulators ---
    total_renewable_energy_kwh = Column(Float, default=0.0)  # Cumulative renewable kWh
    total_demand_energy_kwh = Column(Float, default=0.0)     # Cumulative demand kWh
    total_battery_throughput_kwh = Column(Float, default=0.0) # Cumulative battery kWh
    
    # --- NEW: HRES Energy Manager Metrics ---
    renewable_pool = Column(Float, default=0.0)
    solar_contribution_pct = Column(Float, default=0.0)
    wind_contribution_pct = Column(Float, default=0.0)
    renewable_coverage_pct = Column(Float, default=0.0)
    renewable_utilization_pct = Column(Float, default=0.0)
    curtailed_energy = Column(Float, default=0.0)
    battery_charging_power = Column(Float, default=0.0)
    battery_discharging_power = Column(Float, default=0.0)
    renewable_deficit = Column(Float, default=0.0)
    
    # Demo states
    demo_mode = Column(Boolean, default=False)
    demo_phase = Column(Integer, default=0)
    demo_timer = Column(Integer, default=0)

class SimulationLog(Base):
    __tablename__ = "simulation_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    step = Column(Integer, nullable=False)
    disaster_type = Column(String, nullable=False)
    grid_status = Column(String, nullable=False)
    renewable_output = Column(Float, default=0.0)
    battery_soc = Column(Float, default=0.0)  # average battery SoC % across all stations
    critical_infra_online = Column(Integer, default=0)  # count of critical nodes online
    active_ambulances = Column(Integer, default=0)
    carbon_saved_delta = Column(Float, default=0.0)
    message = Column(String, nullable=False)

class AIDecision(Base):
    __tablename__ = "ai_decisions"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    node_id = Column(Integer, ForeignKey("infrastructure_nodes.id"), nullable=True)
    type = Column(String, nullable=False)  # Dispatch, Load Shedding, Recharge, Grid Adjust, Solar Wind Balance
    description = Column(String, nullable=False)
    priority_score = Column(Float, default=0.0)
    status = Column(String, default="Pending")  # Pending, Executing, Completed
    
    # Advanced AI Explainability details
    confidence_score = Column(Float, default=95.0)
    battery_level = Column(Float, default=0.0)       # current SOC of node
    remaining_backup_time = Column(Float, default=0.0) # hours
    criticality_level = Column(String, default="Low")
    renewable_availability = Column(Float, default=0.0) # current kW solar/wind online
    disaster_severity = Column(Float, default=0.0)
    ambulance_distance = Column(Float, default=0.0)   # km
    recovery_time = Column(Float, default=0.0)        # estimated hours to healthy
    explanation = Column(String, default="")
    
    # --- NEW: Optimization Strategy Fields ---
    optimization_strategies = Column(Text, default="")  # JSON string of evaluated strategies
    selected_strategy = Column(String, default="")      # Name of chosen strategy
    cost_score = Column(Float, default=0.0)
    reliability_score = Column(Float, default=0.0)
    sustainability_score = Column(Float, default=0.0)

class BatteryHistory(Base):
    __tablename__ = "battery_history"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    node_id = Column(Integer, ForeignKey("infrastructure_nodes.id"), nullable=False)
    soc = Column(Float, nullable=False)  # State of Charge %
