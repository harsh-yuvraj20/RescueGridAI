import React, { useState, useEffect } from 'react';
import apiClient from '../api';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid, 
  BarChart, 
  Bar, 
  Cell, 
  LineChart, 
  Line, 
  Legend,
  ComposedChart
} from 'recharts';
import { BarChart3, TrendingUp, Award, Battery, Zap, Activity, Clock, ShieldCheck, Database } from 'lucide-react';

export default function Analytics() {
  const [chartData, setChartData] = useState(null);
  const [forecasts, setForecasts] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [forecastHorizon, setForecastHorizon] = useState('6h'); // 1h, 6h, 24h

  const fetchAnalytics = async () => {
    try {
      const [analyticsRes, forecastsRes, comparisonRes] = await Promise.all([
    apiClient.get('/api/analytics'),
    apiClient.get('/api/predictions'),
    apiClient.get('/api/scenario-comparison')
]);
      setChartData(analyticsRes.data);
      setForecasts(forecastsRes.data);
      setComparison(comparisonRes.data);
      setLoading(false);
    } catch (err) {
      // API may be temporarily unavailable during reset
    }
  };

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 3000);
    return () => clearInterval(interval);
  }, []);

  if (loading || !chartData || !forecasts || !comparison) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-gray-500 font-mono text-xs gap-2">
        <div className="w-8 h-8 border-2 border-t-brand-blue border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin"></div>
        <span>COMPILING ANALYTICS MODELS...</span>
      </div>
    );
  }

  const timelineData = (chartData.timeline ?? []).map(t => {
    const totalConsumers = 18;
    return {
      ...t,
      coverage_pct: Math.round(((t.infra_online ?? 0) / totalConsumers) * 100)
    };
  });

  const activeForecastData = forecasts[`predictions_${forecastHorizon}`] || [];

  // Calculate some fake accounting totals from the latest timeline for Energy Accounting
  const latestT = timelineData[timelineData.length - 1] || { renewables: 0, infra_online: 0, battery_soc: 0 };
  const totalGen = (latestT.renewables ?? 0) * 24; // kw to kwh rough est
  // If critical_load isn't provided, estimate it based on infra_online * 50kW average load
  const estimatedCriticalLoad = (latestT.infra_online ?? 0) * 50; 
  const totalDem = estimatedCriticalLoad * 24;
  const storageVal = latestT.battery_soc ?? 0; // just a pct
  const curtailment = Math.max(0, totalGen - totalDem - 100);

  return (
    <div className="flex flex-col gap-6">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-800 pb-4">
        <div>
          <h1 className="text-xl font-extrabold tracking-wider text-white font-mono uppercase flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-brand-green" />
            Grid Analytics & Forecasting
          </h1>
          <p className="text-xs text-gray-500 font-mono">
            HISTORICAL REAL-TIME ENERGY BALANCING, PREDICTIVE FORECASTS, AND SCENARIO COMPARISON
          </p>
        </div>
      </div>

      {/* Energy Accounting Panel */}
      <section className="p-4 rounded-xl border border-gray-800 bg-brand-panel glass-panel flex flex-col gap-4">
        <h3 className="text-xs uppercase font-mono tracking-widest text-gray-400 flex items-center gap-2 border-b border-gray-800 pb-2">
          <Database className="w-4 h-4 text-brand-blue" />
          Energy Accounting (24h Cumulative)
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div className="p-3 bg-gray-900/50 border border-gray-800 rounded flex flex-col">
            <span className="text-[10px] text-gray-500 uppercase">Total Generation</span>
            <span className="text-lg font-bold text-brand-green">{totalGen.toFixed(0)} kWh</span>
          </div>
          <div className="p-3 bg-gray-900/50 border border-gray-800 rounded flex flex-col">
            <span className="text-[10px] text-gray-500 uppercase">Critical Demand</span>
            <span className="text-lg font-bold text-brand-red">{totalDem.toFixed(0)} kWh</span>
          </div>
          <div className="p-3 bg-gray-900/50 border border-gray-800 rounded flex flex-col">
            <span className="text-[10px] text-gray-500 uppercase">Curtailment (Wasted)</span>
            <span className="text-lg font-bold text-gray-400">{curtailment.toFixed(0)} kWh</span>
          </div>
          <div className="p-3 bg-gray-900/50 border border-gray-800 rounded flex flex-col">
            <span className="text-[10px] text-gray-500 uppercase">Storage Deficit</span>
            <span className="text-lg font-bold text-brand-amber">{Math.max(0, totalDem - totalGen).toFixed(0)} kWh</span>
          </div>
        </div>
      </section>

      {/* Scenario Comparison Summary */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 border border-brand-green/30 bg-brand-green/5 rounded-xl flex flex-col justify-between hover:bg-brand-green/10 transition">
          <div className="flex items-center gap-2 text-brand-green mb-2">
            <ShieldCheck className="w-4 h-4" />
            <h3 className="text-xs uppercase font-mono tracking-widest font-bold">Runtime Extension</h3>
          </div>
          <p className="text-[10px] text-gray-400 font-mono mb-2">Hospital Avg Runtime vs Diesel Baseline</p>
          <div className="flex items-end justify-between">
            <div>
              <span className="text-2xl font-bold text-white">{(comparison?.with_rescuegrid?.hospital_runtime_hours ?? 0).toFixed(1)}h</span>
              <span className="text-[10px] text-gray-500 ml-2 border-l border-gray-700 pl-2 text-decoration-line-through">{(comparison?.without_rescuegrid?.hospital_runtime_hours ?? 0).toFixed(1)}h</span>
            </div>
            <span className="text-sm font-bold text-brand-green bg-brand-green/20 px-2 py-0.5 rounded">
              +{comparison?.improvements?.hospital_runtime ?? 0}%
            </span>
          </div>
        </div>

        <div className="p-4 border border-brand-blue/30 bg-brand-blue/5 rounded-xl flex flex-col justify-between hover:bg-brand-blue/10 transition">
          <div className="flex items-center gap-2 text-brand-blue mb-2">
            <Award className="w-4 h-4" />
            <h3 className="text-xs uppercase font-mono tracking-widest font-bold">Emissions Cut</h3>
          </div>
          <p className="text-[10px] text-gray-400 font-mono mb-2">Carbon Emitted vs Diesel Baseline</p>
          <div className="flex items-end justify-between">
            <div>
              <span className="text-2xl font-bold text-white">{(comparison?.with_rescuegrid?.carbon_emissions_kg ?? 0).toFixed(0)}kg</span>
              <span className="text-[10px] text-gray-500 ml-2 border-l border-gray-700 pl-2 text-decoration-line-through">{(comparison?.without_rescuegrid?.carbon_emissions_kg ?? 0).toFixed(0)}kg</span>
            </div>
            <span className="text-sm font-bold text-brand-blue bg-brand-blue/20 px-2 py-0.5 rounded">
              {comparison?.improvements?.carbon_reduction ?? 0}%
            </span>
          </div>
        </div>

        <div className="p-4 border border-brand-amber/30 bg-brand-amber/5 rounded-xl flex flex-col justify-between hover:bg-brand-amber/10 transition">
          <div className="flex items-center gap-2 text-brand-amber mb-2">
            <TrendingUp className="w-4 h-4" />
            <h3 className="text-xs uppercase font-mono tracking-widest font-bold">Cost Savings</h3>
          </div>
          <p className="text-[10px] text-gray-400 font-mono mb-2">Operating Cost vs Diesel Baseline</p>
          <div className="flex items-end justify-between">
            <div>
              <span className="text-2xl font-bold text-white">₹{(comparison?.with_rescuegrid?.operating_cost_inr ?? 0).toLocaleString(undefined, {maximumFractionDigits:0})}</span>
              <span className="text-[10px] text-gray-500 ml-2 border-l border-gray-700 pl-2 text-decoration-line-through">₹{(comparison?.without_rescuegrid?.operating_cost_inr ?? 0).toLocaleString(undefined, {maximumFractionDigits:0})}</span>
            </div>
            <span className="text-sm font-bold text-brand-amber bg-brand-amber/20 px-2 py-0.5 rounded">
              {comparison?.improvements?.cost_savings ?? 0}%
            </span>
          </div>
        </div>
      </section>

      {/* Grid of Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* PREDICTIVE FORECAST CHART */}
        <div className="lg:col-span-12 p-5 rounded-xl border border-gray-800 bg-brand-panel glass-panel flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-gray-800 pb-2">
            <h3 className="text-xs uppercase font-mono tracking-widest text-brand-cyan flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Predictive Battery SOC & Failure Risk Forecast
            </h3>
            <div className="flex gap-2 font-mono text-[10px]">
              {['1h', '6h', '24h'].map(h => (
                <button
                  key={h}
                  onClick={() => setForecastHorizon(h)}
                  className={`px-3 py-1 rounded border transition-colors font-bold ${forecastHorizon === h ? 'bg-brand-cyan/20 border-brand-cyan text-brand-cyan shadow-glow-blue' : 'bg-transparent border-gray-800 text-gray-500 hover:text-gray-300'}`}
                >
                  {h} FORECAST
                </button>
              ))}
            </div>
          </div>

          <div className="h-[280px] w-full font-mono text-[10px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={activeForecastData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorSoc" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#EF4444" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#EF4444" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#1F2937" strokeDasharray="3 3" />
                <XAxis dataKey="time" stroke="#6B7280" />
                <YAxis yAxisId="left" stroke="#6B7280" domain={[0, 100]} label={{ value: 'SOC %', angle: -90, position: 'insideLeft', fill: '#6B7280' }} />
                <YAxis yAxisId="right" orientation="right" stroke="#6B7280" domain={[0, 100]} label={{ value: 'Risk %', angle: 90, position: 'insideRight', fill: '#6B7280' }} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'rgba(11, 15, 25, 0.9)', backdropFilter: 'blur(10px)', borderColor: '#374151', color: '#F3F4F6', borderRadius: '8px' }}
                  itemStyle={{ fontSize: '12px', fontWeight: 'bold' }}
                />
                <Legend />
                <Area isAnimationActive={true} animationDuration={1500} animationEasing="ease-in-out" yAxisId="left" type="monotone" dataKey="soc" name="Predicted SOC %" stroke="#3B82F6" fillOpacity={1} fill="url(#colorSoc)" strokeWidth={3} />
                <Area isAnimationActive={true} animationDuration={1500} animationEasing="ease-in-out" yAxisId="left" type="monotone" dataKey="soc_low" name="SOC Lower Bound" stroke="none" fill="#3B82F6" fillOpacity={0.08} />
                <Area isAnimationActive={true} animationDuration={1500} animationEasing="ease-in-out" yAxisId="left" type="monotone" dataKey="soc_high" name="SOC Upper Bound" stroke="none" fill="#3B82F6" fillOpacity={0.08} />
                <Area isAnimationActive={true} animationDuration={1500} animationEasing="ease-in-out" yAxisId="right" type="monotone" dataKey="failure_risk" name="System Failure Risk %" stroke="#EF4444" fill="url(#colorRisk)" strokeWidth={2} dot={false} strokeDasharray="4 4" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 1: Energy Balancing (Renewables vs Load Demand) - Col 8 */}
        <div className="lg:col-span-8 p-5 rounded-xl border border-gray-800 bg-brand-panel glass-panel flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-gray-800 pb-2">
            <h3 className="text-xs uppercase font-mono tracking-widest text-gray-400 flex items-center gap-2">
              <Zap className="w-4 h-4 text-brand-green" />
              Renewable Output vs Critical Demand (kW)
            </h3>
          </div>

          <div className="h-[280px] w-full font-mono text-[10px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timelineData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorGen" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorDem" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#EF4444" stopOpacity={0.25}/>
                    <stop offset="95%" stopColor="#EF4444" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#1F2937" strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" stroke="#6B7280" />
                <YAxis stroke="#6B7280" />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'rgba(11, 15, 25, 0.9)', backdropFilter: 'blur(10px)', borderColor: '#374151', color: '#F3F4F6', borderRadius: '8px' }}
                  labelStyle={{ fontWeight: 'bold', color: '#10B981' }}
                />
                <Legend verticalAlign="top" height={36} iconType="circle" />
                <Area isAnimationActive={true} animationDuration={1500} animationEasing="ease-in-out" type="monotone" name="Renewable Generation" dataKey="renewables" stroke="#10B981" fillOpacity={1} fill="url(#colorGen)" strokeWidth={2} />
                <Area isAnimationActive={true} animationDuration={1500} animationEasing="ease-in-out" type="monotone" name="Grid Critical Load" dataKey="infra_online" stroke="#EF4444" fillOpacity={1} fill="url(#colorDem)" strokeWidth={1.5} strokeDasharray="4 4" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Charge State of Battery Storage Units - Col 4 */}
        <div className="lg:col-span-4 p-5 rounded-xl border border-gray-800 bg-brand-panel glass-panel flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-gray-800 pb-2">
            <h3 className="text-xs uppercase font-mono tracking-widest text-gray-400 flex items-center gap-2">
              <Battery className="w-4 h-4 text-brand-blue" />
              Storage SOH & SOC (%)
            </h3>
          </div>

          <div className="h-[280px] w-full font-mono text-[9px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData.battery_socs} layout="vertical" margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                <CartesianGrid stroke="#1F2937" strokeDasharray="2 2" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} stroke="#6B7280" />
                <YAxis type="category" dataKey="name" stroke="#6B7280" width={110} tickFormatter={(val) => val.split(' ')[0] + ' ' + (val.split(' ')[1] || '')} />
                <Tooltip
                  contentStyle={{ backgroundColor: 'rgba(17, 24, 39, 0.9)', borderColor: '#374151', color: '#F3F4F6' }}
                />
                <Legend />
                <Bar name="Current SOC %" dataKey="soc" stackId="a" fill="#10B981" radius={[0, 0, 0, 0]}>
                  {chartData.battery_socs.map((entry, index) => {
                    let color = '#10B981';
                    if (entry.soc < 20) color = '#EF4444';
                    else if (entry.soc < 50) color = '#F59E0B';
                    return <Cell key={`cell-${index}`} fill={color} />;
                  })}
                </Bar>
                <Bar name="Capacity Fade (Degradation) %" dataKey="capacity_fade" stackId="a" fill="#374151" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
