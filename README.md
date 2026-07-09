# RescueGrid AI

**AI-Powered Renewable Energy Resilience Platform for Critical Infrastructure**

RescueGrid AI is a full-stack, production-quality simulation platform designed to manage renewable energy resources during extreme grid failures and natural disasters. The platform demonstrates how intelligent rule-based AI routing can sustain hospitals, water treatment plants, and telecom towers for up to 7 days without relying on fossil-fuel diesel generators by dynamically allocating wind, solar, and mobile BESS trucks (Energy Ambulances).

---

## 🚀 Key Features

*   **NASA-Inspired Digital Twin:** Real-time visual network schematic with animated dash intervals showing proportional power currents from generators (solar/wind farms) to consumers.
*   **Intelligent AI Decision Engine:** Multi-criteria weighted scoring algorithm calculating node priority, battery SOC, and remaining survival hours to schedule ambulance dispatches and load-shedding policies.
*   **Energy Ambulance Logistics:** Physics-based simulation of mobile battery vehicles moving across city coordinates with speed limits affected by cyclones, floods, and earthquakes.
*   **Disaster Simulator Cockpit:** Interactive controls for Cyclone, Flood, Earthquake, Heatwave, and Cyber Attack to study grid failures, panel damage, and telecommunication blackouts.
*   **Grid Analytics Portal:** Recharts graphs showing battery charge distribution, solar/wind outputs, load coverage rates, and cumulative carbon savings.
*   **Audit PDF Exporter:** Dynamic generation of professional grid status audit reports for download.

---

## 🛠️ Tech Stack

### Frontend
*   **React 19 & Vite:** Core rendering engine and tooling.
*   **Tailwind CSS:** Glassmorphism and dark dashboard layouts.
*   **Framer Motion:** Micro-animations and slide transitions.
*   **Leaflet Maps:** Geography maps displaying marker pins and coordinates.
*   **Recharts:** Time-series dashboards.
*   **Axios:** REST API integration.

### Backend
*   **FastAPI & Python:** High-performance asynchronous endpoint server.
*   **SQLAlchemy:** Database ORM mapping.
*   **SQLite (Local) / PostgreSQL (Supabase Production):** Hybrid database storage.
*   **ReportLab:** Programmatic PDF generation.

---

## 📂 Folder Structure

```
├── backend/
│   ├── database.py         # SQLAlchemy engine and session makers
│   ├── models.py           # Database entity tables
│   ├── schemas.py          # Pydantic schemas for request/response serialization
│   ├── seed.py             # Pre-configured seed data for 18 critical nodes
│   ├── simulation.py       # Core physics engine and grid simulator loop
│   ├── decision_engine.py  # Priority engine and ambulance dispatcher
│   ├── report_generator.py # PDF builder using ReportLab
│   ├── main.py             # REST API routes and async loop runner
│   ├── requirements.txt    # Python dependencies list
│   └── Dockerfile          # Python backend build instructions
├── frontend/
│   ├── src/
│   │   ├── components/     # Reusable UI widgets
│   │   ├── context/        # AppContext managing audio synth and polling hooks
│   │   ├── pages/          # Dashboard, Simulator, Analytics, Settings, etc.
│   │   ├── App.jsx         # App router and toast portals
│   │   ├── index.css       # LED glow rules and custom styling
│   │   └── main.jsx        # App bootstrapper
│   ├── index.html          # Google Fonts & Leaflet links
│   ├── vite.config.js      # Dev server port proxy bindings
│   ├── tailwind.config.js  # Color tokens and glow effects
│   ├── postcss.config.js   # CSS compiler setup
│   ├── package.json        # Frontend node dependencies
│   ├── nginx.conf          # Router fallback and proxy for Docker
│   └── Dockerfile          # Multi-stage production web-server build
└── docker-compose.yml      # Orchestrates frontend + backend
```

---

## ⚙️ Environment Variables

Copy the defaults to configure your environment:

### Backend `.env`
```env
DATABASE_URL=sqlite:///./rescuegrid.db # For Supabase: postgresql://user:pass@host:port/db
```

---

## 📦 Local Installation & Setup

### Docker Compose (Recommended)
Launch the entire system (Frontend on port `3000`, Backend on port `8000`) with one command:
```bash
docker-compose up --build
```

### Manual Local Setup

#### 1. Start the Backend
1. Navigate to the `backend/` folder.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
4. The database is initialized and seeded automatically on startup.

#### 2. Start the Frontend
1. Navigate to the `frontend/` folder.
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Launch the Vite dev server:
   ```bash
   npm run dev
   ```
4. Open your browser to [http://localhost:3000](http://localhost:3000).

---

## 🛰️ REST API Endpoints

### Dashboard & Analytics
*   `GET /api/dashboard` - Return current metrics, weather, active disasters, and nodes list.
*   `GET /api/analytics` - Return charting data including average SOC timeline.
*   `GET /api/history` - Return time-series battery charge histories.
*   `GET /api/report/export` - Generate and download the PDF Resilience Audit report.

### Simulation Control
*   `POST /api/simulator/control` - Trigger simulation loop state updates (`start`, `pause`, `reset`, `speed`).
*   `POST /api/simulator/disaster` - Change active disaster (Cyclone, Flood, Earthquake, Cyber Attack, Heatwave).

### Infrastructure & Ambulances
*   `GET /api/infrastructure` - Fetch nodes list.
*   `POST /api/infrastructure/{node_id}/toggle` - Trigger manual bypass of a critical node.
*   `GET /api/ambulance` - Fetch BESS ambulance positions and load levels.
*   `GET /api/decision` - Fetch recommendations.
*   `POST /api/decision/{decision_id}/action` - Execute load-shedding or routing changes.

---

## ☁️ Deployment Instructions

### Database → Supabase
1. Create a PostgreSQL project on Supabase.
2. Retrieve the Database URI connection string under Database Settings.
3. Inject the connection string into the `DATABASE_URL` environment variable for your hosted backend.

### Backend → Render
1. Create a new Web Service on Render linked to your project repository.
2. Specify Root Directory as `backend/` and runtime environment as `Python`.
3. Set Build Command to `pip install -r requirements.txt`.
4. Set Start Command to `uvicorn main:app --host 0.0.0.0 --port $PORT`.
5. Add `DATABASE_URL` under Environment Variables.

### Frontend → Vercel
1. Import your project repository to Vercel.
2. Specify Root Directory as `frontend/`.
3. Framework Preset: `Vite`.
4. Configure rewrite rules in `vercel.json` to proxy `/api` routes to your Render Web Service.
