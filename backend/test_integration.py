import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models import InfrastructureNode, DisasterStatus, SimulationState

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Mock data
    sim = SimulationState(is_running=True)
    dis = DisasterStatus(type="Normal", active=False)
    node = InfrastructureNode(name="Test Hospital", type="Hospital", max_capacity=500.0, current_storage=250.0)
    db.add_all([sim, dis, node])
    db.commit()
    yield
    Base.metadata.drop_all(bind=engine)

def test_dashboard_endpoint():
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["weather"] is not None
    assert data["metrics"] is not None
    assert data["disaster"]["type"] == "Normal"

def test_validation_endpoint():
    response = client.get("/api/validation")
    assert response.status_code == 200
    data = response.json()
    assert "cost" in data
    assert "carbon" in data
    assert "critical_load_served_pct" in data

def test_disaster_demo_trigger():
    response = client.post("/api/demo/cyclone")
    assert response.status_code == 200
    assert response.json()["message"] == "Demo mode successfully triggered"
    
    # Verify DB update
    response = client.get("/api/dashboard")
    data = response.json()
    assert data["disaster"]["active"] is True
    assert data["disaster"]["type"] == "Cyclone"
    assert data["metrics"]["grid_status"] == "Unstable"
