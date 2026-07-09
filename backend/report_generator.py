import os
import json
from datetime import datetime
from sqlalchemy.orm import Session
from .models import InfrastructureNode, EnergyAmbulance, DisasterStatus, SimulationState, AIDecision, SimulationLog
from . import physics_engine as pe

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

def generate_pdf_report(db: Session, filepath: str):
    """
    Generates an Engineering Evaluation Document summarizing the simulation.
    Includes Validation Metrics, Scenario Comparison, Cost & Carbon analysis.
    """
    # Fetch data
    sim_state = db.query(SimulationState).first()
    disaster = db.query(DisasterStatus).first()
    nodes = db.query(InfrastructureNode).all()
    ambulances = db.query(EnergyAmbulance).all()
    decisions = db.query(AIDecision).order_by(AIDecision.timestamp.desc()).limit(15).all()

    # Calculate metrics
    generators = [n for n in nodes if n.type in ["Solar Farm", "Wind Farm"]]
    consumers = [n for n in nodes if n.type in ["Hospital", "Water Plant", "Telecom Tower"]]
    total_gen = sum(n.generation_output for n in generators)
    total_demand = sum(n.current_demand for n in consumers)
    
    val_metrics = pe.compute_all_validation_metrics(nodes, sim_state, disaster, total_gen, total_demand)
    scenario_comp = pe.generate_scenario_comparison(nodes, ambulances, sim_state, disaster)
    
    total_renewable_kwh = sim_state.total_renewable_energy_kwh or 0.0
    total_battery_kwh = sim_state.total_battery_throughput_kwh or 0.0
    cost_metrics = pe.calculate_cumulative_cost(total_renewable_kwh, total_battery_kwh)
    carbon_equivs = pe.carbon_equivalents(sim_state.total_carbon_avoided_net or 0.0)

    if not REPORTLAB_AVAILABLE:
        # Fallback to generating a text-based/markdown report if ReportLab is not installed
        with open(filepath, "w") as f:
            f.write("# RESCUEGRID AI - ENGINEERING EVALUATION REPORT\n")
            f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## 1. EXECUTIVE SUMMARY\n")
            f.write(f"- Grid Status: {sim_state.grid_status}\n")
            f.write(f"- Active Disaster: {disaster.type} (Severity: {disaster.severity})\n")
            f.write(f"- Net Carbon Avoided: {sim_state.total_carbon_avoided_net} kg\n")
            f.write(f"- Cost Savings: INR {sim_state.total_cost_avoided}\n\n")
            
            f.write("## 2. SCENARIO COMPARISON (WITH vs WITHOUT AI)\n")
            with_ai = scenario_comp["with_rescuegrid"]
            without_ai = scenario_comp["without_rescuegrid"]
            f.write(f"- Hospital Runtime: {with_ai['hospital_runtime_hours']}h (AI) vs {without_ai['hospital_runtime_hours']}h (Diesel)\n")
            f.write(f"- Operating Cost: INR {with_ai['operating_cost_inr']} (AI) vs INR {without_ai['operating_cost_inr']} (Diesel)\n")
            f.write(f"- Carbon Emissions: {with_ai['carbon_emissions_kg']} kg (AI) vs {without_ai['carbon_emissions_kg']} kg (Diesel)\n\n")
        return

    # ReportLab PDF generation
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'], fontSize=24, leading=28, textColor=colors.HexColor('#10B981'), spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor('#6B7280'), spaceAfter=20
    )
    h1_style = ParagraphStyle(
        'SectionHeader', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor('#1E3A8A'), spaceBefore=15, spaceAfter=8, keepWithNext=True
    )
    body_style = ParagraphStyle('BodyTextCustom', parent=styles['Normal'], fontSize=9.5, leading=13, textColor=colors.HexColor('#374151'))
    bold_body_style = ParagraphStyle('BodyTextBold', parent=body_style, fontName='Helvetica-Bold')

    story = []

    # Title & Header
    story.append(Paragraph("RescueGrid AI", title_style))
    story.append(Paragraph("Engineering Evaluation Document: AI-Powered Grid Resilience", ParagraphStyle('Tag', parent=title_style, fontSize=12, leading=14, textColor=colors.HexColor('#059669'))))
    story.append(Paragraph(f"AUDIT REPORT &nbsp;|&nbsp; Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
    story.append(Spacer(1, 10))

    # Executive Summary Card
    story.append(Paragraph("1. Executive Summary", h1_style))
    
    grid_str = "OFFLINE (Islanded)" if not (not disaster.affected_grid and sim_state.grid_status == "Stable") else "ONLINE (Stable)"
    grid_color = "red" if not (not disaster.affected_grid and sim_state.grid_status == "Stable") else "green"
    
    summary_data = [
        [
            Paragraph("<b>Grid Status:</b>", body_style), Paragraph(f"<font color='{grid_color}'><b>{grid_str}</b></font>", body_style),
            Paragraph("<b>Active Disaster:</b>", body_style), Paragraph(f"<font color='red'><b>{disaster.type}</b></font> (Sev: {disaster.severity:.2f})", body_style)
        ],
        [
            Paragraph("<b>Total Renewables:</b>", body_style), Paragraph(f"{total_gen:.1f} kW", body_style),
            Paragraph("<b>Net Carbon Avoided:</b>", body_style), Paragraph(f"<b>{(sim_state.total_carbon_avoided_net or 0):.2f} kg</b>", body_style)
        ],
        [
            Paragraph("<b>Total Cost Savings:</b>", body_style), Paragraph(f"<b>₹{(sim_state.total_cost_avoided or 0):.0f}</b>", body_style),
            Paragraph("<b>Critical Infra Online:</b>", body_style), Paragraph(f"{val_metrics['critical_load_served_pct']:.1f}%", body_style)
        ]
    ]
    t_summary = Table(summary_data, colWidths=[1.5*inch, 1.8*inch, 1.6*inch, 2.3*inch])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F3F4F6')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#D1D5DB')),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 15))

    # Section 2: Validation Metrics
    story.append(Paragraph("2. Engineering Validation Metrics", h1_style))
    
    val_data = [
        [Paragraph("<b>Metric</b>", bold_body_style), Paragraph("<b>Value</b>", bold_body_style), Paragraph("<b>Description</b>", bold_body_style)],
        [Paragraph("Renewable Penetration", body_style), Paragraph(f"{val_metrics['renewable_penetration_pct']:.1f}%", body_style), Paragraph("Percentage of total demand covered by renewable generation", body_style)],
        [Paragraph("Grid Reliability Index", body_style), Paragraph(f"{val_metrics['grid_reliability_pct']:.1f}%", body_style), Paragraph("System Average Interruption equivalent for critical nodes", body_style)],
        [Paragraph("Battery State of Health", body_style), Paragraph(f"{val_metrics['battery_health_avg_pct']:.1f}%", body_style), Paragraph("Average effective capacity vs rated capacity (degradation tracked)", body_style)],
        [Paragraph("Avg Capacity Factor", body_style), Paragraph(f"{val_metrics['avg_capacity_factor']:.4f}", body_style), Paragraph("Average CF across all solar and wind assets", body_style)],
        [Paragraph("System Efficiency", body_style), Paragraph(f"{val_metrics['system_efficiency_pct']:.1f}%", body_style), Paragraph("Ratio of useful consumption to total generation", body_style)],
    ]
    
    t_val = Table(val_data, colWidths=[2.0*inch, 1.5*inch, 3.5*inch])
    t_val.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E5E7EB')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
    ]))
    story.append(t_val)
    story.append(Spacer(1, 15))
    
    # Section 3: Scenario Comparison
    story.append(Paragraph("3. Scenario Comparison: WITH vs WITHOUT AI", h1_style))
    story.append(Paragraph("Comparing the RescueGrid AI optimized micro-grid performance against a standard diesel-backup baseline during the current scenario.", body_style))
    story.append(Spacer(1, 5))
    
    with_ai = scenario_comp["with_rescuegrid"]
    without_ai = scenario_comp["without_rescuegrid"]
    impr = scenario_comp["improvements"]
    
    comp_data = [
        [Paragraph("<b>Metric</b>", bold_body_style), Paragraph("<b>WITH RescueGrid AI</b>", bold_body_style), Paragraph("<b>WITHOUT AI (Diesel)</b>", bold_body_style), Paragraph("<b>Improvement</b>", bold_body_style)],
        [Paragraph("Hospital Avg Runtime", body_style), Paragraph(f"{with_ai['hospital_runtime_hours']} hrs", body_style), Paragraph(f"{without_ai['hospital_runtime_hours']} hrs", body_style), Paragraph(f"<font color='green'>+{impr['hospital_runtime']}%</font>", body_style)],
        [Paragraph("Operating Cost", body_style), Paragraph(f"₹ {with_ai['operating_cost_inr']}", body_style), Paragraph(f"₹ {without_ai['operating_cost_inr']}", body_style), Paragraph(f"<font color='green'>-{impr['cost_savings']}%</font>", body_style)],
        [Paragraph("Carbon Emissions", body_style), Paragraph(f"{with_ai['carbon_emissions_kg']} kg", body_style), Paragraph(f"{without_ai['carbon_emissions_kg']} kg", body_style), Paragraph(f"<font color='green'>-{impr['carbon_reduction']}%</font>", body_style)],
        [Paragraph("Diesel Consumption", body_style), Paragraph(f"{with_ai['diesel_consumption_litres']} L", body_style), Paragraph(f"{without_ai['diesel_consumption_litres']} L", body_style), Paragraph(f"<font color='green'>{impr['diesel_eliminated']}</font>", body_style)],
        [Paragraph("Critical Load Coverage", body_style), Paragraph(f"{with_ai['critical_load_coverage_pct']}%", body_style), Paragraph(f"{without_ai['critical_load_coverage_pct']}%", body_style), Paragraph(f"<font color='green'>+{impr['critical_load_coverage']}%</font>", body_style)],
    ]
    
    t_comp = Table(comp_data, colWidths=[2.0*inch, 1.8*inch, 1.8*inch, 1.4*inch])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E5E7EB')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
    ]))
    story.append(t_comp)
    
    story.append(PageBreak())

    # Section 4: AI Optimization Log
    story.append(Paragraph("4. AI Optimization & Dispatch Log", h1_style))
    story.append(Paragraph("The following logs detail the explainable AI decisions driven by the multi-strategy optimization engine.", body_style))
    story.append(Spacer(1, 8))

    dec_table_data = [[
        Paragraph("<b>Time</b>", bold_body_style),
        Paragraph("<b>Action Type</b>", bold_body_style),
        Paragraph("<b>Reasoning & Strategy Evaluation</b>", bold_body_style)
    ]]
    for d in decisions:
        time_str = d.timestamp.strftime('%H:%M:%S')
        
        reasoning_text = d.explanation
        if d.optimization_strategies and d.optimization_strategies != "[]":
            try:
                strats = json.loads(d.optimization_strategies)
                if strats:
                    scores = f"<br/><b>Cost Score:</b> {d.cost_score:.1f} | <b>Reliability:</b> {d.reliability_score:.1f} | <b>Sustainability:</b> {d.sustainability_score:.1f}"
                    reasoning_text += scores
            except:
                pass
                
        dec_table_data.append([
            Paragraph(time_str, body_style),
            Paragraph(f"<b>{d.type}</b><br/>{d.status}", body_style),
            Paragraph(reasoning_text, body_style)
        ])

    t_dec = Table(dec_table_data, colWidths=[0.8*inch, 1.2*inch, 5.0*inch])
    t_dec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E5E7EB')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_dec)
    
    story.append(Spacer(1, 15))
    
    # Section 5: Cost & Carbon Equivalents
    story.append(Paragraph("5. Sustainability Impact", h1_style))
    sus_data = [
        [Paragraph("<b>Cost Analysis</b>", bold_body_style), Paragraph("<b>Carbon & Environmental Equivalents</b>", bold_body_style)],
        [
            Paragraph(
                f"Generation Cost (Solar/Wind): ₹ {cost_metrics['total_generation_cost_inr']}<br/>"
                f"Diesel Baseline Cost: ₹ {cost_metrics['diesel_baseline_cost_inr']}<br/>"
                f"<b>Total Cost Avoided: ₹ {cost_metrics['total_cost_avoided_inr']}</b>",
                body_style
            ),
            Paragraph(
                f"Equivalent Trees Planted: {carbon_equivs['trees_equivalent']} trees<br/>"
                f"Cars Off Road: {carbon_equivs['cars_off_road_equivalent']} cars<br/>"
                f"Households Powered: {carbon_equivs['households_month']} homes/month",
                body_style
            )
        ]
    ]
    
    t_sus = Table(sus_data, colWidths=[3.5*inch, 3.5*inch])
    t_sus.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E5E7EB')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_sus)

    # Build document
    doc.build(story)
