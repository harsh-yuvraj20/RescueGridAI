from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class InfrastructureNodeBase(BaseModel):
    name: str
    type: str
    latitude: float
    longitude: float
    criticality: str
    base_demand: float
    current_demand: float
    max_capacity: float
    current_storage: float
    generation_output: float
    status: str
    survival_hours: float
    health_score: float
    risk_score: float
    infrastructure_damage: float
    # New physics fields
    total_energy_generated: float = 0.0
    total_energy_consumed: float = 0.0
    capacity_fade_pct: float = 0.0
    total_cycles: float = 0.0
    inverter_efficiency: float = 0.95
    temperature_derate: float = 1.0
    capacity_factor: float = 0.0

class InfrastructureNodeResponse(InfrastructureNodeBase):
    id: int

    class Config:
        from_attributes = True

class EnergyAmbulanceBase(BaseModel):
    name: str
    battery_capacity: float
    current_energy: float
    latitude: float
    longitude: float
    speed: float
    status: str
    current_mission: str
    target_node_id: Optional[int] = None
    eta_minutes: float
    mission_id: str
    source_name: str
    destination_name: str
    energy_delivered: float
    progress: float

class EnergyAmbulanceResponse(EnergyAmbulanceBase):
    id: int

    class Config:
        from_attributes = True

class DisasterStatusBase(BaseModel):
    type: str
    severity: float
    active: bool
    affected_grid: bool
    description: str

class DisasterStatusResponse(DisasterStatusBase):
    id: int
    start_time: datetime

    class Config:
        from_attributes = True

class SimulationStateBase(BaseModel):
    is_running: bool
    speed_multiplier: float
    current_step: int
    wind_speed: float
    solar_irradiance: float
    temperature: float
    grid_status: str
    carbon_saved: float
    demo_mode: bool
    demo_phase: int
    demo_timer: int
    # New weather fields
    humidity: float = 60.0
    cloud_cover: float = 0.2
    pressure: float = 1013.25
    simulation_hour: float = 10.0
    
    # New HRES fields
    renewable_pool: float = 0.0
    solar_contribution_pct: float = 0.0
    wind_contribution_pct: float = 0.0
    renewable_coverage_pct: float = 0.0
    renewable_utilization_pct: float = 0.0
    curtailed_energy: float = 0.0
    battery_charging_power: float = 0.0
    battery_discharging_power: float = 0.0
    renewable_deficit: float = 0.0

class SimulationStateResponse(SimulationStateBase):
    id: int

    class Config:
        from_attributes = True

class SimulationLogResponse(BaseModel):
    id: int
    timestamp: datetime
    step: int
    disaster_type: str
    grid_status: str
    renewable_output: float
    battery_soc: float
    critical_infra_online: int
    active_ambulances: int
    carbon_saved_delta: float
    message: str

    class Config:
        from_attributes = True

class AIDecisionResponse(BaseModel):
    id: int
    timestamp: datetime
    node_id: Optional[int] = None
    type: str
    description: str
    priority_score: float
    status: str
    confidence_score: float
    battery_level: float
    remaining_backup_time: float
    criticality_level: str
    renewable_availability: float
    disaster_severity: float
    ambulance_distance: float
    recovery_time: float
    explanation: str
    # New optimization fields
    optimization_strategies: str = ""
    selected_strategy: str = ""
    cost_score: float = 0.0
    reliability_score: float = 0.0
    sustainability_score: float = 0.0

    class Config:
        from_attributes = True

class BatteryHistoryResponse(BaseModel):
    id: int
    timestamp: datetime
    node_id: int
    soc: float

    class Config:
        from_attributes = True

# Dashboard overall status schema
class DashboardMetrics(BaseModel):
    grid_status: str
    renewable_output: float  # kW
    battery_soc: float       # average %
    critical_infra_online: int
    total_critical_infra: int
    active_ambulances: int
    total_ambulances: int
    carbon_saved: float      # kg CO2
    diesel_saved: float      # liters
    renewable_efficiency: float # %
    lives_impacted: int
    decision_latency: int     # ms
    avg_recovery_time: float  # hours
    # New engineering KPIs
    renewable_penetration: float = 0.0    # %
    grid_efficiency: float = 0.0          # %
    battery_soh: float = 100.0            # % State of Health
    renewable_utilization: float = 0.0    # %
    net_carbon_avoided: float = 0.0       # kg CO2 (lifecycle-adjusted)
    diesel_avoided_litres: float = 0.0    # litres
    cost_savings_inr: float = 0.0         # INR saved vs diesel
    critical_infra_availability: float = 100.0  # %
    system_efficiency: float = 0.0        # %
    simulation_hour: float = 10.0         # virtual hour of day

class DashboardState(BaseModel):
    metrics: DashboardMetrics
    weather: dict
    disaster: DisasterStatusResponse
    nodes: List[InfrastructureNodeResponse]
    ambulances: List[EnergyAmbulanceResponse]
    recent_decisions: List[AIDecisionResponse]
    recent_logs: List[SimulationLogResponse]
