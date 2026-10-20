import pytest
from fastapi.testclient import TestClient
from prune.server import app

client = TestClient(app)


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


def test_api_samples():
    response = client.get("/api/samples")
    assert response.status_code == 200
    samples = response.json()
    assert "standard" in samples
    assert "side_effects" in samples
    assert "circular_dependency" in samples


def test_api_compile_success():
    payload = {
        "files": {
            "math.prune": "export function add(a, b) { return a + b; }\nexport function dead() { return 0; }",
            "main.prune": "import { add } from './math.prune';\nexport function run() { return add(5, 5); }"
        },
        "entry_points": ["main.prune"],
        "optimization_level": "O1"
    }
    response = client.post("/api/compile", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "add" in data["bundle"]
    assert "dead" not in data["bundle"]
    assert data["stats"]["reachable_exports"] >= 1
    assert data["graph"] is not None


def test_api_compile_syntax_error():
    payload = {
        "files": {
            "main.prune": "const = 42;"
        },
        "entry_points": ["main.prune"],
        "optimization_level": "O1"
    }
    response = client.post("/api/compile", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert len(data["diagnostics"]) > 0
    assert "Expected variable name" in data["diagnostics"][0]["message"]
