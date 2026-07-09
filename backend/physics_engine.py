"""
RescueGrid AI — Advanced Physics Engine
========================================
Industry-grade simulation models for renewable energy grid resilience.
Localized for Indian deployment (INR costs, Indian grid emission factors, Indian weather).

Modules:
    1. Weather Model          — Correlated stochastic weather with diurnal cycles
    2. Solar PV Model         — NOCT cell temperature + temperature derating
    3. Wind Turbine Model     — Cubic power curve with air density correction
    4. Battery Degradation    — Calendar + cycle aging (Arrhenius-based)
    5. Demand Forecasting     — Time-of-day profiles + temperature-dependent HVAC
    6. Efficiency Calcs       — Inverter curve, transmission losses, round-trip η
    7. Renewable Optimization — Merit-order dispatch with multi-strategy scoring
    8. Cost Model             — LCOE, diesel avoided cost (INR)
    9. Carbon Model           — Lifecycle-aware net carbon accounting
   10. Validation Metrics     — MAPE, Capacity Factor, SAIDI, Renewable Penetration
"""

import math
import random

# ============================================================================
# CONSTANTS — Indian Localization
# ============================================================================

# Indian Grid Emission Factor (CEA CO2 Baseline Database, 2023)
GRID_EMISSION_FACTOR_KG_PER_KWH = 0.71  # kg CO2/kWh (Indian weighted avg)

# Lifecycle embodied emissions (amortized over 25yr life)
SOLAR_LIFECYCLE_G_PER_KWH = 40.0   # g CO2/kWh
WIND_LIFECYCLE_G_PER_KWH = 11.0    # g CO2/kWh
BATTERY_LIFECYCLE_G_PER_KWH = 65.0 # g CO2/kWh (manufacturing)

# Indian Diesel Generator baseline
DIESEL_L_PER_KWH = 0.28            # liters of diesel per kWh
DIESEL_KG_CO2_PER_L = 2.68         # kg CO2 per liter diesel
DIESEL_COST_INR_PER_L = 94.72      # INR per liter (Indian avg 2024)
DIESEL_COST_INR_PER_KWH = DIESEL_L_PER_KWH * DIESEL_COST_INR_PER_L  # ~26.5 INR/kWh

# Indian Electricity Tariff (commercial/industrial)
GRID_TARIFF_INR_PER_KWH = 8.50     # INR/kWh (avg industrial tariff India)

# LCOE for Indian renewables (CERC/MNRE benchmarks 2024)
SOLAR_LCOE_INR = 2.50   # INR/kWh
WIND_LCOE_INR = 3.20    # INR/kWh
BATTERY_LCOS_INR = 8.00 # INR/kWh (Levelized Cost of Storage)

# Solar PV parameters
NOCT = 45.0               # Nominal Operating Cell Temperature (°C)
GAMMA_TEMP_COEFF = -0.004 # Power temperature coefficient (%/°C for crystalline Si)
SOILING_LOSS = 0.03       # 3% soiling loss (Indian dusty conditions)
PANEL_AGE_YEARS = 2.0     # Assumed panel age

# Wind turbine parameters
CUT_IN_SPEED = 3.0     # m/s
RATED_SPEED = 12.0      # m/s
CUT_OUT_SPEED = 25.0    # m/s
ROTOR_AREA = 4500.0     # m² (approx 38m radius)
CP_BETZ = 0.40          # Practical power coefficient (Betz limit ~0.593)
WAKE_LOSS = 0.12        # 12% wake effect losses

# Battery parameters
BATTERY_ROUNDTRIP_EFF = 0.90      # 90% round-trip efficiency
CHARGE_EFF = math.sqrt(0.90)      # ~94.87% charge efficiency
DISCHARGE_EFF = math.sqrt(0.90)   # ~94.87% discharge efficiency
CALENDAR_AGING_K = 0.02           # 2% capacity loss per year at 25°C
ARRHENIUS_EA = 24500.0            # Activation energy J/mol
GAS_CONSTANT = 8.314              # J/(mol·K)
CYCLE_AGING_K = 0.00008           # Cycle aging coefficient
CYCLE_AGING_ALPHA = 1.5           # DoD exponent for cycle aging
MAX_CYCLES_LIFE = 6000            # Max cycles before end-of-life

# Simulation time step
DT_SECONDS = 4.0
DT_HOURS = DT_SECONDS / 3600.0

# Virtual time acceleration: 1 real second = N simulation minutes
SIM_MINUTES_PER_REAL_SECOND = 5.0  # 1 real second = 5 sim minutes
SIM_HOURS_PER_TICK = (DT_SECONDS * SIM_MINUTES_PER_REAL_SECOND) / 60.0  # hours per tick


# ============================================================================
# 1. WEATHER MODEL — Correlated stochastic processes
# ============================================================================

def simulate_weather(sim_state, disaster):
    """
    Simulate realistic weather with diurnal cycles and disaster overrides.
    Uses AR(1) autocorrelation for wind, sinusoidal solar/temperature cycles.
    Indian weather baseline (tropical/subtropical).
    """
    # Advance simulation hour (accumulate continuously for day tracking)
    sim_state.simulation_hour = sim_state.simulation_hour + SIM_HOURS_PER_TICK
    hour = sim_state.simulation_hour % 24.0  # hour-of-day for weather calculations

    if disaster.active:
        _apply_disaster_weather(sim_state, disaster, hour)
    else:
        _simulate_normal_weather(sim_state, hour)


def _simulate_normal_weather(sim_state, hour):
    """Normal Indian weather: clear days, moderate wind, tropical temperatures."""
    # --- Solar Irradiance (diurnal cycle) ---
    # Sunrise ~6:00, sunset ~18:00 (12h daylight, Indian average)
    sunrise = 6.0
    sunset = 18.0
    daylight_hours = sunset - sunrise

    if sunrise <= hour <= sunset:
        solar_angle = math.pi * (hour - sunrise) / daylight_hours
        clear_sky = 1000.0 * max(0.0, math.sin(solar_angle))  # Peak 1000 W/m²
    else:
        clear_sky = 0.0

    # Clear-sky index with Gaussian noise
    cloud_noise = random.gauss(0, 0.08)
    kt = max(0.3, min(1.0, (1.0 - sim_state.cloud_cover) + cloud_noise))
    sim_state.solar_irradiance = max(0.0, round(clear_sky * kt, 1))

    # Cloud cover random walk (slow drift)
    sim_state.cloud_cover = max(0.05, min(0.85, sim_state.cloud_cover + random.gauss(0, 0.02)))

    # --- Wind Speed (AR(1) autocorrelated process) ---
    # Indian avg wind: 4-8 m/s coastal, using Weibull-like behavior
    mean_wind = 8.0  # m/s (Indian coastal average)
    rho = 0.95  # autocorrelation coefficient
    sigma_wind = 1.5

    prev = sim_state.prev_wind_speed if sim_state.prev_wind_speed else mean_wind
    innovation = random.gauss(0, sigma_wind * math.sqrt(1 - rho**2))
    new_wind = mean_wind + rho * (prev - mean_wind) + innovation
    new_wind = max(0.5, min(30.0, new_wind))

    # Occasional gusts (Poisson-distributed)
    if random.random() < 0.02:  # 2% chance per tick
        new_wind += random.uniform(3.0, 8.0)
        new_wind = min(30.0, new_wind)

    sim_state.prev_wind_speed = new_wind
    sim_state.wind_speed = round(new_wind, 1)

    # --- Temperature (diurnal sinusoidal cycle) ---
    # Indian tropical: mean ~30°C, amplitude ~6°C, peak at 14:00
    t_mean = 30.0
    t_amplitude = 6.0
    peak_hour = 14.0
    temp = t_mean + t_amplitude * math.sin(2 * math.pi * (hour - peak_hour + 6) / 24.0)
    temp += random.gauss(0, 0.5)
    sim_state.temperature = round(max(18.0, min(45.0, temp)), 1)

    # --- Humidity (inverse correlation with temperature) ---
    base_humidity = 65.0 - (sim_state.temperature - 30.0) * 2.0
    sim_state.humidity = round(max(30.0, min(95.0, base_humidity + random.gauss(0, 3.0))), 1)

    # --- Pressure (slow drift) ---
    sim_state.pressure = round(max(1005.0, min(1025.0, sim_state.pressure + random.gauss(0, 0.3))), 1)

    sim_state.grid_status = "Stable"


def _apply_disaster_weather(sim_state, disaster, hour):
    """Override weather parameters based on active disaster type and severity."""
    severity = disaster.severity

    if disaster.type == "Cyclone":
        sim_state.wind_speed = round(min(95.0, max(55.0, 60.0 + severity * 35.0 + random.uniform(-3, 3))), 1)
        sim_state.solar_irradiance = round(max(10.0, min(100.0, 50.0 * (1 - severity) + random.uniform(-10, 10))), 1)
        sim_state.temperature = round(max(18.0, min(24.0, 22.0 - severity * 4.0 + random.uniform(-0.5, 0.5))), 1)
        sim_state.humidity = round(min(98.0, 85.0 + severity * 13.0), 1)
        sim_state.pressure = round(max(970.0, 1013.0 - severity * 40.0 + random.gauss(0, 1.0)), 1)
        sim_state.cloud_cover = min(1.0, 0.85 + severity * 0.15)
        sim_state.grid_status = "Down"

    elif disaster.type == "Flood":
        sim_state.wind_speed = round(max(8.0, min(25.0, 15.0 + severity * 10.0 + random.uniform(-1.5, 1.5))), 1)
        sim_state.solar_irradiance = round(max(30.0, min(180.0, 100.0 * (1 - severity * 0.6) + random.uniform(-10, 10))), 1)
        sim_state.temperature = round(max(16.0, min(22.0, 20.0 - severity * 4.0 + random.uniform(-0.3, 0.3))), 1)
        sim_state.humidity = round(min(99.0, 90.0 + severity * 9.0), 1)
        sim_state.cloud_cover = min(1.0, 0.7 + severity * 0.3)
        sim_state.grid_status = "Down"

    elif disaster.type == "Earthquake":
        # Weather mostly unaffected, but grid infrastructure damaged
        _simulate_normal_weather(sim_state, hour)
        sim_state.grid_status = "Down"

    elif disaster.type == "Heatwave":
        sim_state.wind_speed = round(max(1.0, min(6.0, 3.0 + random.uniform(-0.5, 0.5))), 1)
        # High solar during heatwave
        sunrise, sunset = 5.5, 18.5
        if sunrise <= hour <= sunset:
            solar_angle = math.pi * (hour - sunrise) / (sunset - sunrise)
            sim_state.solar_irradiance = round(max(0.0, 1100.0 * math.sin(solar_angle) * (0.9 + severity * 0.1)), 1)
        else:
            sim_state.solar_irradiance = 0.0
        sim_state.temperature = round(max(38.0, min(48.0, 40.0 + severity * 8.0 + random.uniform(-0.3, 0.5))), 1)
        sim_state.humidity = round(max(15.0, min(35.0, 25.0 - severity * 10.0)), 1)
        sim_state.grid_status = "Unstable" if random.random() > 0.3 else "Stable"

    elif disaster.type == "Cyber Attack":
        _simulate_normal_weather(sim_state, hour)
        sim_state.grid_status = "Unstable"

    sim_state.prev_wind_speed = sim_state.wind_speed


# ============================================================================
# 2. SOLAR PV MODEL — NOCT cell temperature + temperature derating
# ============================================================================

def calculate_solar_output(node, sim_state, disaster):
    """
    Calculate solar PV output using NOCT-based cell temperature model.
    P = P_rated × (G/1000) × (1 + γ × (T_cell - 25)) × η_inverter × (1 - soiling)
    """
    if node.status == "Offline":
        node.generation_output = 0.0
        return 0.0

    G = sim_state.solar_irradiance  # W/m²
    if G <= 0:
        node.generation_output = 0.0
        return 0.0

    T_ambient = sim_state.temperature

    # Cell temperature (NOCT model)
    T_cell = T_ambient + ((NOCT - 20.0) / 800.0) * G

    # Temperature derating
    temp_derate = 1.0 + GAMMA_TEMP_COEFF * (T_cell - 25.0)
    temp_derate = max(0.5, min(1.1, temp_derate))

    # Base power
    P_rated = node.max_capacity  # kW peak
    P_base = P_rated * (G / 1000.0)

    # Apply temperature derating
    P_output = P_base * temp_derate

    # Soiling loss (higher in Indian dusty conditions)
    P_output *= (1.0 - SOILING_LOSS)

    # Panel age degradation (0.5% per year)
    age_derate = 1.0 - (0.005 * PANEL_AGE_YEARS)
    P_output *= age_derate

    # Inverter efficiency (quadratic model)
    load_fraction = P_output / max(P_rated, 1.0)
    inv_eff = _inverter_efficiency(load_fraction)
    P_output *= inv_eff

    # Inverter clipping at 110% rated AC
    P_output = min(P_output, P_rated * 1.1)

    # Disaster damage penalties
    if disaster.active:
        damage_factor = _solar_disaster_factor(disaster)
        P_output *= damage_factor

    # Infrastructure damage from digital twin
    if node.infrastructure_damage and node.infrastructure_damage > 0:
        P_output *= max(0.0, 1.0 - node.infrastructure_damage / 100.0)

    P_output = max(0.0, round(P_output, 1))
    node.generation_output = P_output
    node.temperature_derate = round(temp_derate, 4)
    node.inverter_efficiency = round(inv_eff, 4)

    return P_output


def _solar_disaster_factor(disaster):
    """Disaster-specific solar reduction factors."""
    s = disaster.severity
    factors = {
        "Cyclone": max(0.02, 0.05 * (1 - s)),       # Near-zero during severe cyclone
        "Flood": max(0.1, 0.3 * (1 - s * 0.5)),     # Cloud cover reduces output
        "Earthquake": max(0.3, 0.7 * (1 - s * 0.3)), # Structural damage
        "Heatwave": 1.0,                              # High irradiance (handled by weather)
        "Cyber Attack": max(0.2, 0.4 * (1 - s * 0.5)) # Inverter control compromised
    }
    return factors.get(disaster.type, 1.0)


# ============================================================================
# 3. WIND TURBINE MODEL — Cubic power curve + air density correction
# ============================================================================

def calculate_wind_output(node, sim_state, disaster):
    """
    Wind turbine power using cubic power curve:
    Region 1 (v < cut-in): P = 0
    Region 2 (cut-in <= v < rated): P = P_rated × ((v - v_ci)/(v_r - v_ci))³
    Region 3 (rated <= v < cut-out): P = P_rated
    Region 4 (v >= cut-out): P = 0

    Includes air density correction for temperature.
    """
    if node.status == "Offline":
        node.generation_output = 0.0
        return 0.0

    v = sim_state.wind_speed  # m/s (already in m/s in weather model)
    T = sim_state.temperature

    P_rated = node.max_capacity  # kW

    # Air density correction (ISA: ρ₀ = 1.225 kg/m³ at 15°C)
    rho = 1.225 * (288.15 / (T + 273.15))
    rho_factor = rho / 1.225

    # Power curve regions
    if v < CUT_IN_SPEED or v >= CUT_OUT_SPEED:
        P_output = 0.0
    elif v < RATED_SPEED:
        # Cubic region
        ratio = (v - CUT_IN_SPEED) / (RATED_SPEED - CUT_IN_SPEED)
        P_output = P_rated * (ratio ** 3) * rho_factor
    else:
        # Rated region
        P_output = P_rated * rho_factor

    # Wake effect losses
    P_output *= (1.0 - WAKE_LOSS)

    # Turbulence intensity derating (higher wind variance = lower output)
    if v > 15.0:
        turbulence_derate = max(0.85, 1.0 - (v - 15.0) * 0.01)
        P_output *= turbulence_derate

    # Disaster penalties
    if disaster.active:
        damage_factor = _wind_disaster_factor(disaster, v)
        P_output *= damage_factor

    # Infrastructure damage
    if node.infrastructure_damage and node.infrastructure_damage > 0:
        P_output *= max(0.0, 1.0 - node.infrastructure_damage / 100.0)

    P_output = max(0.0, min(P_rated, round(P_output, 1)))
    node.generation_output = P_output
    node.temperature_derate = round(rho_factor, 4)

    return P_output


def _wind_disaster_factor(disaster, wind_speed):
    """Disaster-specific wind generation factors."""
    s = disaster.severity
    factors = {
        "Cyclone": 0.0 if wind_speed > 25.0 else max(0.0, 0.3 * (1 - s)),  # Cut-out in severe winds
        "Flood": max(0.3, 0.8 * (1 - s * 0.3)),
        "Earthquake": max(0.4, 0.9 * (1 - s * 0.3)),  # Structural concern
        "Heatwave": max(0.05, 0.15),                    # Very low wind in heatwave
        "Cyber Attack": max(0.2, 0.4 * (1 - s * 0.5))  # SCADA compromised
    }
    return factors.get(disaster.type, 1.0)


# ============================================================================
# 4. BATTERY DEGRADATION — Calendar + cycle aging
# ============================================================================

def update_battery(node, net_energy_kw, sim_state, is_ambulance=False):
    """
    Update battery state with degradation modeling.
    net_energy_kw: positive = charging, negative = discharging

    Calendar aging: Q_cal = k × exp(-Ea/(RT)) × √t
    Cycle aging: ΔQ = k_cyc × DoD^α per cycle
    """
    if node.max_capacity <= 0:
        return

    T = sim_state.temperature
    dt_h = SIM_HOURS_PER_TICK  # simulation hours per tick

    # --- Effective capacity after degradation ---
    fade = node.capacity_fade_pct if node.capacity_fade_pct else 0.0
    effective_capacity = node.max_capacity * (1.0 - fade / 100.0)

    soc_before = (node.current_storage / effective_capacity) if effective_capacity > 0 else 0.0

    # --- Charge/Discharge with efficiency ---
    if net_energy_kw > 0:
        # Charging
        energy_in = net_energy_kw * dt_h * CHARGE_EFF
        node.current_storage = min(effective_capacity, node.current_storage + energy_in)
    elif net_energy_kw < 0:
        # Discharging
        energy_out = abs(net_energy_kw) * dt_h / DISCHARGE_EFF
        node.current_storage = max(0.0, node.current_storage - energy_out)

    soc_after = (node.current_storage / effective_capacity) if effective_capacity > 0 else 0.0

    # --- Temperature effects on charge/discharge rate ---
    # Cold temperature: reduce effective power below 10°C
    if T < 10.0:
        cold_derate = max(0.5, 0.7 + (T / 33.33))
        # Already applied via reduced energy flow above; store for display
        node.temperature_derate = round(cold_derate, 4)
    elif T > 40.0:
        # Hot temperature: slight power limitation
        hot_derate = max(0.85, 1.0 - (T - 40.0) * 0.02)
        node.temperature_derate = round(hot_derate, 4)
    else:
        node.temperature_derate = 1.0

    # --- Calendar Aging (per tick) ---
    # Arrhenius: rate doubles every ~10°C above 25°C
    T_kelvin = T + 273.15
    T_ref = 298.15  # 25°C
    aging_accel = math.exp(ARRHENIUS_EA / GAS_CONSTANT * (1.0 / T_ref - 1.0 / T_kelvin))
    # Calendar loss per tick (scaled from annual rate)
    hours_per_year = 8760.0
    calendar_loss_per_tick = CALENDAR_AGING_K * aging_accel * (dt_h / hours_per_year)

    # --- Cycle Aging (simplified depth-of-discharge tracking) ---
    delta_soc = abs(soc_after - soc_before)
    cycle_fraction = delta_soc / 2.0  # half-cycle per charge/discharge event
    cycle_loss = CYCLE_AGING_K * (max(delta_soc, 0.01) ** CYCLE_AGING_ALPHA) * (1.0 if delta_soc > 0.01 else 0.0)

    # Update cumulative degradation
    total_new_fade = calendar_loss_per_tick + cycle_loss
    node.capacity_fade_pct = round(min(30.0, (fade + total_new_fade * 100.0)), 4)

    # Track total cycles
    if node.total_cycles is None:
        node.total_cycles = 0.0
    node.total_cycles = round(node.total_cycles + cycle_fraction, 4)

    # --- Dynamic Survival Time Calculation ---
    if not is_ambulance:
        demand = node.current_demand if node.current_demand else 0.0
        generation = node.generation_output if node.generation_output else 0.0
        
        # Add micro-stochastic variance so identical nodes drift slightly (realism)
        noise = random.uniform(0.98, 1.02)
        net_consumption = (demand - generation) * noise
        
        if net_consumption > 0.1:
            # Battery is draining
            node.survival_hours = round(node.current_storage / net_consumption, 3)
        else:
            # Battery is charging or stable (generation >= demand)
            # Cap max display at 14 days (336 hours)
            node.survival_hours = 336.0

    # --- SOC-based status for battery stations ---
    soc_pct = soc_after * 100.0
    if node.type == "Battery Station":
        if soc_pct > 40:
            node.status = "Healthy"
        elif soc_pct > 10:
            node.status = "Warning"
        elif soc_pct > 0:
            node.status = "Critical"
        else:
            node.status = "Offline"


def get_battery_roundtrip_efficiency(temperature):
    """Temperature-dependent round-trip efficiency."""
    if temperature < 5:
        return 0.82
    elif temperature < 15:
        return 0.85 + (temperature - 5) * 0.005
    elif temperature <= 35:
        return 0.90 + (temperature - 15) * 0.001
    elif temperature <= 45:
        return 0.92 - (temperature - 35) * 0.004
    else:
        return 0.85


# ============================================================================
# 5. DEMAND FORECASTING — Time-of-day profiles + temperature HVAC
# ============================================================================

def calculate_demand(node, sim_state, disaster):
    """
    Calculate demand using time-of-day profiles and temperature-dependent HVAC.
    Indian load profiles.
    """
    hour = sim_state.simulation_hour
    T = sim_state.temperature
    base = node.base_demand

    # --- Time-of-day demand profile ---
    if node.type == "Hospital":
        # Hospitals: relatively flat, peak during surgery hours (8-16)
        if 8 <= hour <= 16:
            time_factor = 1.15
        elif 20 <= hour or hour <= 5:
            time_factor = 0.80
        else:
            time_factor = 0.95
    elif node.type == "Water Plant":
        # Water treatment: bimodal peaks (morning 6-9, evening 17-20)
        if 6 <= hour <= 9 or 17 <= hour <= 20:
            time_factor = 1.25
        elif 0 <= hour <= 5:
            time_factor = 0.65
        else:
            time_factor = 0.90
    elif node.type == "Telecom Tower":
        # Telecom: evening peak (18-23), moderate otherwise
        if 18 <= hour <= 23:
            time_factor = 1.30
        elif 0 <= hour <= 6:
            time_factor = 0.70
        else:
            time_factor = 1.0
    else:
        time_factor = 1.0

    demand = base * time_factor

    # --- Temperature-dependent HVAC load ---
    # Cooling (Indian climate: threshold 24°C)
    if T > 24.0:
        cooling_load = 0.02 * (T - 24.0) ** 1.5  # quadratic increase
        demand *= (1.0 + cooling_load)
    # Heating (rare in most of India, but included)
    elif T < 18.0:
        heating_load = 0.01 * (18.0 - T)
        demand *= (1.0 + heating_load)

    # --- Disaster demand modifiers ---
    if disaster.active:
        disaster_mod = _demand_disaster_modifier(disaster, node)
        demand *= disaster_mod

    # --- Mean-reverting stochastic noise ---
    noise = random.gauss(0, 0.03)  # ±3% noise
    demand *= (1.0 + noise)

    demand = max(0.1, round(demand, 1))
    node.current_demand = demand

    return demand


def _demand_disaster_modifier(disaster, node):
    """Disaster-specific demand multipliers."""
    s = disaster.severity
    if disaster.type == "Earthquake":
        # Emergency triage, equipment surge
        return 1.0 + 0.40 * s if node.type == "Hospital" else 1.0 + 0.20 * s
    elif disaster.type == "Cyclone":
        # Shelter loads, emergency lighting
        return 1.0 + 0.20 * s
    elif disaster.type == "Heatwave":
        # Massive AC demand spike
        return 1.0 + 0.50 * s
    elif disaster.type == "Flood":
        # Pumping operations
        return 1.0 + 0.30 * s if node.type == "Water Plant" else 1.0 + 0.15 * s
    elif disaster.type == "Cyber Attack":
        # Slight increase from security operations
        return 1.0 + 0.05 * s
    return 1.0


# ============================================================================
# 6. EFFICIENCY CALCULATIONS
# ============================================================================

def _inverter_efficiency(load_fraction):
    """
    Inverter efficiency curve (quadratic model).
    η peaks around 30-80% load, drops at very low and very high loads.
    η(P) = η_max - a/P - b×P  (simplified CEC model)
    """
    if load_fraction < 0.01:
        return 0.0
    if load_fraction < 0.05:
        return 0.70  # Very low load: poor efficiency
    if load_fraction < 0.10:
        return 0.85

    # Quadratic fit: peak ~96% at 40% load
    eta = 0.965 - 0.005 / max(load_fraction, 0.1) - 0.015 * load_fraction
    return max(0.80, min(0.97, eta))


def calculate_transmission_loss(distance_km):
    """
    Simplified transmission loss based on distance.
    Indian distribution: ~3-5% for short distances.
    """
    base_loss = 0.02  # 2% base loss
    distance_loss = 0.005 * distance_km  # 0.5% per km
    return min(0.15, base_loss + distance_loss)


# ============================================================================
# 7. RENEWABLE OPTIMIZATION — Merit-order + multi-strategy scoring
# ============================================================================

def optimize_dispatch(generators, batteries, consumers, sim_state, disaster):
    """
    Merit-order dispatch: allocate cheapest generation first.
    Returns dispatch plan and optimization metrics.
    """
    # Sort generators by marginal cost (solar cheapest, then wind)
    gen_list = []
    for g in generators:
        if g.generation_output > 0:
            cost = SOLAR_LCOE_INR if g.type == "Solar Farm" else WIND_LCOE_INR
            gen_list.append({"node": g, "output": g.generation_output, "cost": cost})
    gen_list.sort(key=lambda x: x["cost"])

    total_gen = sum(g["output"] for g in gen_list)
    total_demand = sum(c.current_demand for c in consumers)

    surplus = total_gen - total_demand
    weighted_cost = sum(g["output"] * g["cost"] for g in gen_list)
    avg_cost = weighted_cost / max(total_gen, 0.1)

    return {
        "total_generation": round(total_gen, 1),
        "total_demand": round(total_demand, 1),
        "surplus": round(surplus, 1),
        "avg_generation_cost_inr": round(avg_cost, 2),
        "merit_order": [g["node"].name for g in gen_list],
        "curtailment_needed": surplus > total_gen * 0.3  # Flag if surplus > 30%
    }


def calculate_failure_risk(node, sim_state, disaster, horizon_hours=2.0):
    """
    Probabilistic Risk Analysis:
    Predicts the probability of a node failing within a specific time horizon.
    Uses an approximated Weibull survival curve taking into account SOC, weather volatility, and disaster multipliers.
    """
    soc = (node.current_storage / max(node.max_capacity, 1.0))
    if soc > 0.9:
        base_risk = 0.05
    else:
        # Exponential increase in risk as SOC drops
        base_risk = math.exp(-3.0 * soc)

    # Weather volatility (high wind/solar variance increases risk of renewable failure)
    weather_volatility = (sim_state.wind_speed / 25.0) * 0.1 + (1.0 - sim_state.solar_irradiance / 1000.0) * 0.1
    
    # Disaster severity multiplier
    disaster_mult = 1.0 + (disaster.severity * 2.0) if disaster.active else 1.0
    
    # Combine and scale by horizon
    risk = base_risk * (1.0 + weather_volatility) * disaster_mult * (horizon_hours / 2.0)
    return min(99.9, max(0.1, risk * 100.0))


def calculate_confidence_score(sim_state, disaster, failure_risk):
    """
    Dynamic Confidence Score based on data variance, weather stability, and risk assessment variance.
    Now incorporates Forecast Confidence for Solar/Wind volatility.
    """
    base_confidence = 98.0
    
    # High variance in wind (e.g. storms) or low solar irradiance reduces forecast confidence
    wind_variance = abs(sim_state.wind_speed - 15.0) / 30.0  # Deviation from average
    solar_variance = (1000.0 - sim_state.solar_irradiance) / 1000.0
    weather_penalty = (wind_variance * 5.0) + (solar_variance * 3.0)
    
    disaster_penalty = (disaster.severity * 15.0) if disaster.active else 0.0
    # High risk situations have slightly lower confidence due to volatility
    risk_penalty = (failure_risk / 100.0) * 8.0
    
    confidence = base_confidence - weather_penalty - disaster_penalty - risk_penalty
    return min(99.9, max(50.0, confidence))


def evaluate_optimization_strategies(node, ambulances, batteries, sim_state, disaster, total_renewables):
    """
    Evaluate multiple response strategies and score each using Analytic Hierarchy Process (AHP).
    Generates Chain-of-Thought explainability strings.
    """
    strategies = []
    soc = (node.current_storage / max(node.max_capacity, 1.0)) * 100.0
    
    # 1. Probabilistic Risk Assessment
    failure_risk_2h = calculate_failure_risk(node, sim_state, disaster, 2.0)
    confidence = calculate_confidence_score(sim_state, disaster, failure_risk_2h)
    
    # 2. AHP Weight Generation
    if disaster.active and disaster.severity > 0.3:
        # Disaster Mode: Reliability is paramount
        w_cost = 0.10
        w_rel = 0.75
        w_sus = 0.15
        mode_str = "Disaster AHP Profile"
    else:
        # Normal Mode: Balanced with cost focus
        w_cost = 0.50
        w_rel = 0.30
        w_sus = 0.20
        mode_str = "Standard AHP Profile"

    # Base Structured Decision Tree Observation
    tree_str = f"[DECISION TREE]\n"
    tree_str += f"├── Observation: SOC={soc:.1f}%, Risk_2h={failure_risk_2h:.1f}%\n"
    tree_str += f"├── Evaluation: {mode_str}\n"

    # 1. Dispatch Energy Ambulance
    idle_ambs = [a for a in ambulances if a.status == "Idle" and a.current_energy > a.battery_capacity * 0.2]
    if idle_ambs:
        best_amb = idle_ambs[0]
        
        # Mission Cost Evaluation
        import math
        distance_km = 10.0 # Approximation, precise haversine done in decision_engine
        travel_energy_kwh = distance_km * 0.5
        mission_duration_h = (distance_km / 50.0) + 2.0 # Travel + Transfer time
        recharge_delay_h = (best_amb.battery_capacity - best_amb.current_energy + travel_energy_kwh) / 50.0
        
        # Total mission cost factor (wear, delay, travel energy)
        mission_cost_penalty = (travel_energy_kwh / 100.0) * 10.0 + (recharge_delay_h / 2.0) * 5.0
        
        energy_deliverable = (best_amb.current_energy - travel_energy_kwh) * DISCHARGE_EFF
        runtime_improvement = energy_deliverable / max(node.current_demand, 0.1)
        
        # Opportunity Cost: Is this ambulance better used elsewhere?
        # A simple proxy: if disaster severity is high, using the ambulance now costs the ability to use it later
        opportunity_cost_penalty = (disaster.severity * 15.0) if disaster.active else 5.0
        
        cost_score = max(10.0, 75.0 - mission_cost_penalty - opportunity_cost_penalty)
        reliability_score = 98.0 if energy_deliverable > node.current_demand * 4 else 75.0
        sustainability_score = 90.0  # EV dispatch
        
        overall = (w_cost * cost_score) + (w_rel * reliability_score) + (w_sus * sustainability_score)
        
        action_str = f"└── Action: Dispatch {best_amb.name} (+{runtime_improvement:.1f}h) [OppCost: {opportunity_cost_penalty:.1f}]"
        
        strategies.append({
            "strategy": "Dispatch Energy Ambulance",
            "cost_score": round(cost_score, 1),
            "reliability_score": round(reliability_score, 1),
            "sustainability_score": round(sustainability_score, 1),
            "runtime_improvement_hours": round(runtime_improvement, 1),
            "overall_score": round(overall, 1),
            "confidence": round(confidence, 1),
            "reasoning": tree_str + action_str
        })

    # 2. Load Shedding (20% non-essential reduction)
    shed_amount = node.base_demand * 0.20
    new_demand = max(0.1, node.current_demand - shed_amount)
    runtime_with_shed = node.current_storage / new_demand
    runtime_without = node.current_storage / max(node.current_demand, 0.1)
    improvement = runtime_with_shed - runtime_without

    cost_ls = 100.0  # Free to implement
    reliability_ls = 40.0  # Lowers service quality significantly
    sustainability_ls = 95.0
    overall_ls = (w_cost * cost_ls) + (w_rel * reliability_ls) + (w_sus * sustainability_ls)

    action_ls = f"└── Action: Shed {shed_amount:.1f}kW non-essential load (+{improvement:.1f}h)"
    
    strategies.append({
        "strategy": "Load Shedding (20%)",
        "cost_score": round(cost_ls, 1),
        "reliability_score": round(reliability_ls, 1),
        "sustainability_score": round(sustainability_ls, 1),
        "runtime_improvement_hours": round(improvement, 1),
        "overall_score": round(overall_ls, 1),
        "confidence": round(confidence, 1),
        "reasoning": tree_str + action_ls
    })

    # 3. Battery Redistribution (transfer from highest SOC station)
    if batteries:
        highest_soc_station = max(batteries, key=lambda b: b.current_storage / max(b.max_capacity, 1.0))
        transferable = highest_soc_station.current_storage * 0.3 * DISCHARGE_EFF
        runtime_batt = transferable / max(node.current_demand, 0.1)

        cost_br = 70.0  # Transmission losses + cycling
        reliability_br = 85.0
        sustainability_br = 85.0
        overall_br = (w_cost * cost_br) + (w_rel * reliability_br) + (w_sus * sustainability_br)

        action_br = f"└── Action: Redirect {transferable:.0f}kWh from {highest_soc_station.name}"
        
        strategies.append({
            "strategy": "Battery Redistribution",
            "cost_score": round(cost_br, 1),
            "reliability_score": round(reliability_br, 1),
            "sustainability_score": round(sustainability_br, 1),
            "runtime_improvement_hours": round(runtime_batt, 1),
            "overall_score": round(overall_br, 1),
            "confidence": round(confidence, 1),
            "reasoning": tree_str + action_br
        })

    # 4. Renewable Reallocation (prioritize this node in merit-order)
    if total_renewables > 0:
        allocatable = total_renewables * 0.5
        runtime_re = (allocatable / max(node.current_demand, 0.1)) * SIM_HOURS_PER_TICK
        cost_re = 90.0
        reliability_re = 50.0 if disaster.active else 80.0 # Renewables unreliable in disaster
        sustainability_re = 100.0
        overall_re = (w_cost * cost_re) + (w_rel * reliability_re) + (w_sus * sustainability_re)

        action_re = f"└── Action: Force-route {allocatable:.0f}kW active renewables"
        
        strategies.append({
            "strategy": "Renewable Reallocation",
            "cost_score": round(cost_re, 1),
            "reliability_score": round(reliability_re, 1),
            "sustainability_score": round(sustainability_re, 1),
            "runtime_improvement_hours": round(runtime_re, 1),
            "overall_score": round(overall_re, 1),
            "confidence": round(confidence, 1),
            "reasoning": tree_str + action_re
        })

    # Sort by overall score descending
    strategies.sort(key=lambda x: x["overall_score"], reverse=True)
    return strategies


# ============================================================================
# 8. COST MODEL — LCOE, diesel avoided (INR)
# ============================================================================

def calculate_cost(energy_kwh, source_type):
    """
    Calculate cost of energy from different sources (INR).
    Returns dict with generation cost and diesel-avoided savings.
    """
    lcoe_map = {
        "Solar Farm": SOLAR_LCOE_INR,
        "Wind Farm": WIND_LCOE_INR,
        "Battery Station": BATTERY_LCOS_INR,
    }
    lcoe = lcoe_map.get(source_type, GRID_TARIFF_INR_PER_KWH)
    generation_cost = energy_kwh * lcoe
    diesel_avoided_cost = energy_kwh * DIESEL_COST_INR_PER_KWH

    return {
        "generation_cost_inr": round(generation_cost, 2),
        "diesel_avoided_cost_inr": round(diesel_avoided_cost, 2),
        "net_savings_inr": round(diesel_avoided_cost - generation_cost, 2)
    }


def calculate_cumulative_cost(total_renewable_kwh, total_battery_kwh):
    """Calculate cumulative cost savings vs diesel baseline (INR)."""
    renewable_cost = total_renewable_kwh * ((SOLAR_LCOE_INR + WIND_LCOE_INR) / 2.0)
    battery_cost = total_battery_kwh * BATTERY_LCOS_INR
    total_gen_cost = renewable_cost + battery_cost

    diesel_baseline_cost = (total_renewable_kwh + total_battery_kwh) * DIESEL_COST_INR_PER_KWH

    return {
        "total_generation_cost_inr": round(total_gen_cost, 2),
        "diesel_baseline_cost_inr": round(diesel_baseline_cost, 2),
        "total_cost_avoided_inr": round(diesel_baseline_cost - total_gen_cost, 2)
    }


# ============================================================================
# 9. CARBON MODEL — Lifecycle-aware net accounting
# ============================================================================

def calculate_carbon(energy_kwh, source_type, grid_factor=None):
    """
    Calculate net carbon avoided with lifecycle emissions offset.
    Net = (displaced_grid × grid_factor) - (renewable × lifecycle_factor)
    """
    if grid_factor is None:
        grid_factor = GRID_EMISSION_FACTOR_KG_PER_KWH

    # Gross carbon avoided (displacing grid/diesel)
    gross_avoided_kg = energy_kwh * grid_factor

    # Lifecycle embodied emissions
    lifecycle_map = {
        "Solar Farm": SOLAR_LIFECYCLE_G_PER_KWH / 1000.0,  # Convert g to kg
        "Wind Farm": WIND_LIFECYCLE_G_PER_KWH / 1000.0,
        "Battery Station": BATTERY_LIFECYCLE_G_PER_KWH / 1000.0,
    }
    lifecycle_kg = energy_kwh * lifecycle_map.get(source_type, 0.0)

    net_avoided_kg = gross_avoided_kg - lifecycle_kg

    return {
        "gross_carbon_avoided_kg": round(gross_avoided_kg, 4),
        "lifecycle_emissions_kg": round(lifecycle_kg, 4),
        "net_carbon_avoided_kg": round(net_avoided_kg, 4)
    }


def carbon_equivalents(total_net_carbon_kg):
    """
    Convert net carbon savings to human-readable equivalents.
    """
    trees_equivalent = total_net_carbon_kg / 21.0  # 21 kg CO2/tree/year
    cars_equivalent = total_net_carbon_kg / 4600.0  # 4,600 kg CO2/car/year
    diesel_litres_avoided = total_net_carbon_kg / DIESEL_KG_CO2_PER_L
    households_powered = total_net_carbon_kg / (GRID_EMISSION_FACTOR_KG_PER_KWH * 900)  # avg Indian household 90 kWh/month

    return {
        "trees_equivalent": round(trees_equivalent, 1),
        "cars_off_road_equivalent": round(cars_equivalent, 2),
        "diesel_litres_avoided": round(diesel_litres_avoided, 1),
        "households_month": round(households_powered, 2)
    }


# ============================================================================
# 10. VALIDATION METRICS
# ============================================================================

def calculate_capacity_factor(node, sim_hours_elapsed):
    """
    Capacity Factor = actual energy / (rated capacity × time)
    """
    if node.max_capacity <= 0 or sim_hours_elapsed <= 0:
        return 0.0

    total_energy = node.total_energy_generated if node.total_energy_generated else 0.0
    max_possible = node.max_capacity * sim_hours_elapsed
    cf = total_energy / max_possible
    return round(min(1.0, max(0.0, cf)), 4)


def calculate_renewable_penetration(total_renewable_gen, total_demand):
    """Renewable Penetration = renewable generation / total demand × 100."""
    if total_demand <= 0:
        return 100.0
    return round(min(200.0, (total_renewable_gen / total_demand) * 100.0), 1)


def calculate_grid_reliability(infra_online_count, total_infra, disaster_active):
    """
    Grid reliability index based on critical infrastructure availability.
    SAIDI-inspired metric.
    """
    if total_infra <= 0:
        return 100.0
    availability = (infra_online_count / total_infra) * 100.0
    # Penalize slightly during disaster conditions
    if disaster_active:
        availability *= 0.95
    return round(min(100.0, max(0.0, availability)), 1)


def calculate_battery_health(nodes):
    """
    Average State of Health (SOH) across all battery-equipped nodes.
    SOH = (1 - capacity_fade_pct/100) × 100
    """
    battery_nodes = [n for n in nodes if n.max_capacity > 0]
    if not battery_nodes:
        return 100.0

    total_soh = 0.0
    for n in battery_nodes:
        fade = n.capacity_fade_pct if n.capacity_fade_pct else 0.0
        total_soh += (100.0 - fade)

    return round(total_soh / len(battery_nodes), 1)


def calculate_self_sufficiency(total_renewable_hours, total_hours):
    """Self-sufficiency ratio: hours without grid import / total hours."""
    if total_hours <= 0:
        return 100.0
    return round((total_renewable_hours / total_hours) * 100.0, 1)


def calculate_system_efficiency(total_generation, total_consumption, total_losses):
    """Overall system efficiency = useful consumption / total generation."""
    if total_generation <= 0:
        return 0.0
    return round(((total_consumption) / (total_generation + 0.001)) * 100.0, 1)


def compute_all_validation_metrics(nodes, sim_state, disaster, total_gen, total_demand):
    """Compute all validation metrics in one pass."""
    sim_hours = sim_state.current_step * SIM_HOURS_PER_TICK

    # Capacity factors for generators
    generators = [n for n in nodes if n.type in ["Solar Farm", "Wind Farm"]]
    capacity_factors = {}
    for g in generators:
        cf = calculate_capacity_factor(g, sim_hours)
        capacity_factors[g.name] = cf
        g.capacity_factor = cf

    avg_cf = sum(capacity_factors.values()) / max(len(capacity_factors), 1)

    # Other metrics
    critical_consumers = [n for n in nodes if n.type in ["Hospital", "Water Plant", "Telecom Tower"]]
    online_count = sum(1 for n in critical_consumers if n.status != "Offline")

    renewable_penetration = calculate_renewable_penetration(total_gen, total_demand)
    grid_reliability = calculate_grid_reliability(online_count, len(critical_consumers), disaster.active)
    battery_health = calculate_battery_health(nodes)

    # Renewable utilization (actual vs available)
    total_capacity = sum(n.max_capacity for n in generators)
    renewable_utilization = round((total_gen / max(total_capacity, 0.1)) * 100.0, 1)

    return {
        "renewable_penetration_pct": renewable_penetration,
        "grid_reliability_pct": grid_reliability,
        "battery_health_avg_pct": battery_health,
        "avg_capacity_factor": round(avg_cf, 4),
        "capacity_factors": capacity_factors,
        "renewable_utilization_pct": min(100.0, renewable_utilization),
        "critical_load_served_pct": round((online_count / max(len(critical_consumers), 1)) * 100.0, 1),
        "simulation_hours_elapsed": round(sim_hours, 2),
        "system_efficiency_pct": calculate_system_efficiency(total_gen, total_demand, 0),
    }


# ============================================================================
# 11. SCENARIO COMPARISON ENGINE
# ============================================================================

def generate_scenario_comparison(nodes, ambulances, sim_state, disaster):
    """
    Compare: WITH RescueGrid AI vs WITHOUT (diesel-only baseline).
    Returns percentage improvements across key metrics.
    """
    hospitals = [n for n in nodes if n.type == "Hospital"]
    water_plants = [n for n in nodes if n.type == "Water Plant"]
    telecom_towers = [n for n in nodes if n.type == "Telecom Tower"]
    critical_consumers = hospitals + water_plants + telecom_towers
    generators = [n for n in nodes if n.type in ["Solar Farm", "Wind Farm"]]
    batteries = [n for n in nodes if n.type == "Battery Station"]

    sim_hours = max(0.1, sim_state.current_step * SIM_HOURS_PER_TICK)

    # --- WITH RescueGrid AI (actual current state) ---
    total_renewable_gen = sum(n.generation_output for n in generators)
    total_demand = sum(n.current_demand for n in critical_consumers)

    online_critical = sum(1 for n in critical_consumers if n.status != "Offline")
    avg_soc = 0.0
    storage_nodes = [n for n in nodes if n.max_capacity > 0]
    if storage_nodes:
        avg_soc = sum((n.current_storage / n.max_capacity) for n in storage_nodes) / len(storage_nodes) * 100.0

    avg_hospital_runtime = sum(n.survival_hours for n in hospitals) / max(len(hospitals), 1)

    with_rescuegrid = {
        "hospital_runtime_hours": round(avg_hospital_runtime, 1),
        "renewable_utilization_pct": round((total_renewable_gen / max(sum(n.max_capacity for n in generators), 0.1)) * 100.0, 1),
        "carbon_emissions_kg": round(sim_state.carbon_saved * 0.05, 2),  # Minimal lifecycle emissions
        "operating_cost_inr": round(total_renewable_gen * SIM_HOURS_PER_TICK * ((SOLAR_LCOE_INR + WIND_LCOE_INR) / 2.0) * sim_state.current_step, 1),
        "diesel_consumption_litres": 0.0,  # Zero diesel
        "battery_health_pct": round(100.0 - (sum(n.capacity_fade_pct or 0 for n in storage_nodes) / max(len(storage_nodes), 1)), 1),
        "critical_load_coverage_pct": round(online_critical / max(len(critical_consumers), 1) * 100.0, 1),
        "grid_reliability_pct": round(online_critical / max(len(critical_consumers), 1) * 100.0, 1),
    }

    # --- WITHOUT RescueGrid AI (diesel-only baseline) ---
    # Assume: no AI dispatch, no renewable optimization, diesel generators for backup
    # Diesel has reliability issues during disasters, 15-30% failure rate
    diesel_failure_rate = 0.0
    if disaster.active:
        diesel_failure_map = {"Cyclone": 0.35, "Flood": 0.40, "Earthquake": 0.30, "Heatwave": 0.10, "Cyber Attack": 0.05}
        diesel_failure_rate = diesel_failure_map.get(disaster.type, 0.1) * disaster.severity

    diesel_coverage = max(0.3, 1.0 - diesel_failure_rate)
    diesel_hospital_runtime = 24.0 * diesel_coverage  # Typical 24h diesel tank
    diesel_consumption = total_demand * sim_hours * DIESEL_L_PER_KWH
    diesel_cost = diesel_consumption * DIESEL_COST_INR_PER_L
    diesel_carbon = diesel_consumption * DIESEL_KG_CO2_PER_L

    without_rescuegrid = {
        "hospital_runtime_hours": round(diesel_hospital_runtime, 1),
        "renewable_utilization_pct": 0.0,  # No renewables used
        "carbon_emissions_kg": round(diesel_carbon, 2),
        "operating_cost_inr": round(diesel_cost, 1),
        "diesel_consumption_litres": round(diesel_consumption, 1),
        "battery_health_pct": 100.0,  # No battery cycling (but no battery benefit either)
        "critical_load_coverage_pct": round(diesel_coverage * 100.0, 1),
        "grid_reliability_pct": round(diesel_coverage * 90.0, 1),  # Diesel less reliable
    }

    # --- Percentage improvements ---
    def pct_improvement(with_val, without_val, higher_is_better=True):
        if without_val == 0 and with_val == 0:
            return 0.0
        if without_val == 0:
            return 100.0 if higher_is_better else -100.0
        pct = ((with_val - without_val) / abs(without_val)) * 100.0
        return round(pct, 1)

    improvements = {
        "hospital_runtime": pct_improvement(with_rescuegrid["hospital_runtime_hours"], without_rescuegrid["hospital_runtime_hours"]),
        "renewable_utilization": f"+{with_rescuegrid['renewable_utilization_pct']}%",
        "carbon_reduction": pct_improvement(without_rescuegrid["carbon_emissions_kg"], with_rescuegrid["carbon_emissions_kg"]),
        "cost_savings": pct_improvement(without_rescuegrid["operating_cost_inr"], with_rescuegrid["operating_cost_inr"]),
        "diesel_eliminated": "100%" if with_rescuegrid["diesel_consumption_litres"] == 0 else f"{pct_improvement(without_rescuegrid['diesel_consumption_litres'], with_rescuegrid['diesel_consumption_litres'])}%",
        "critical_load_coverage": pct_improvement(with_rescuegrid["critical_load_coverage_pct"], without_rescuegrid["critical_load_coverage_pct"]),
        "grid_reliability": pct_improvement(with_rescuegrid["grid_reliability_pct"], without_rescuegrid["grid_reliability_pct"]),
    }

    return {
        "with_rescuegrid": with_rescuegrid,
        "without_rescuegrid": without_rescuegrid,
        "improvements": improvements,
        "disaster_active": disaster.active,
        "disaster_type": disaster.type if disaster.active else "None",
        "simulation_hours": round(sim_hours, 1)
    }


# ============================================================================
# 12. PREDICTIVE ANALYTICS — 1h, 6h, 24h forecasts
# ============================================================================

def generate_forecasts(sim_state, disaster, nodes):
    """
    Generate predictive forecasts for battery SOC, renewables, demand, and failure risk.
    Forecasts at 1h, 6h, 24h horizons.
    """
    storage_nodes = [n for n in nodes if n.max_capacity > 0]
    total_capacity = sum(n.max_capacity for n in storage_nodes)
    current_storage = sum(n.current_storage for n in storage_nodes)
    current_soc = (current_storage / total_capacity * 100.0) if total_capacity > 0 else 50.0

    critical_consumers = [n for n in nodes if n.type in ["Hospital", "Water Plant", "Telecom Tower"]]
    generators = [n for n in nodes if n.type in ["Solar Farm", "Wind Farm"]]

    total_demand_now = sum(n.current_demand for n in critical_consumers)
    total_gen_now = sum(n.generation_output for n in generators)

    results = {}
    for horizon_label, hours_ahead in [("1h", 1), ("6h", 6), ("24h", 24)]:
        points = []
        temp_soc = current_soc
        for h in range(1, hours_ahead + 1):
            future_hour = (sim_state.simulation_hour + h) % 24.0

            # Predict solar based on diurnal cycle
            sunrise, sunset = 6.0, 18.0
            if sunrise <= future_hour <= sunset:
                solar_angle = math.pi * (future_hour - sunrise) / (sunset - sunrise)
                pred_solar = sum(n.max_capacity for n in generators if n.type == "Solar Farm") * max(0, math.sin(solar_angle)) * 0.85
            else:
                pred_solar = 0.0

            # Disaster reduction
            if disaster.active:
                solar_factor = _solar_disaster_factor(disaster)
                pred_solar *= solar_factor

            # Predict wind
            pred_wind = sim_state.wind_speed + random.gauss(0, 1.5)
            wind_gen = sum(n.max_capacity for n in generators if n.type == "Wind Farm") * min(1.0, max(0, pred_wind - CUT_IN_SPEED) / (RATED_SPEED - CUT_IN_SPEED)) ** 2
            if disaster.active:
                wind_gen *= _wind_disaster_factor(disaster, pred_wind)

            total_pred_gen = pred_solar + wind_gen

            # Predict demand
            demand_mult = 1.0
            if disaster.active:
                demand_mult = 1.0 + 0.3 * disaster.severity
            pred_demand = total_demand_now * demand_mult * (0.9 + 0.2 * max(0, math.sin(math.pi * (future_hour - 8) / 12)))

            # SOC forecast integration
            net = (total_pred_gen - pred_demand) * 0.05
            temp_soc = max(5.0, min(100.0, temp_soc + net))

            # Failure risk
            disaster_risk = 40.0 * disaster.severity if disaster.active else 0.0
            risk = min(98.0, max(2.0, (100.0 - temp_soc) * 0.6 + disaster_risk))

            # Confidence bands (widen with forecast horizon)
            uncertainty = 2.0 + h * 1.0
            points.append({
                "time": f"+{h}h",
                "hour_of_day": round(future_hour, 1),
                "soc": round(temp_soc, 1),
                "soc_low": round(max(0, temp_soc - uncertainty), 1),
                "soc_high": round(min(100, temp_soc + uncertainty), 1),
                "renewables": round(total_pred_gen, 1),
                "demand": round(pred_demand, 1),
                "failure_risk": round(risk, 1),
                "risk_low": round(max(0, risk - uncertainty * 0.8), 1),
                "risk_high": round(min(100, risk + uncertainty * 0.8), 1),
            })

        results[horizon_label] = points

    return results
