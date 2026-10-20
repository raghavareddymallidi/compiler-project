from __future__ import annotations
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prune.compiler import Compiler, CompilationResult


app = FastAPI(
    title="Prune Compiler & Bundler API",
    description="Explainable compiler, dead-code eliminator, and bundler backend",
    version="0.1.0"
)

# CORS configuration for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------
# Request & Response Schemas
# -------------------------------------------------------------

class CompileRequest(BaseModel):
    files: Dict[str, str] = Field(..., description="Map of filename to source code content")
    entry_points: List[str] = Field(..., description="List of entry point module paths")
    optimization_level: str = Field("O1", description="Optimization level: O0, O1, or O2")


class HealthResponse(BaseModel):
    status: str
    version: str


# -------------------------------------------------------------
# Pre-packaged Sample Projects
# -------------------------------------------------------------

DEMO_PROJECTS = {
    "standard": {
        "name": "Standard Multi-Module App",
        "description": "Demonstrates export-level dead code elimination, constant folding, and helper functions.",
        "entry_points": ["src/main.prune"],
        "files": {
            "src/main.prune": """import { add } from './math.prune';
import { greet } from './utils.prune';

export function run(username) {
    const greeting = greet(username);
    const score = add(10, 20 * 3);
    return greeting;
}
""",
            "src/math.prune": """export function add(a, b) {
    return a + b;
}

// Unreachable dead export: will be safely eliminated!
export function deadMultiply(a, b) {
    return a * b;
}
""",
            "src/utils.prune": """export function greet(name) {
    return "Hello, " + name;
}

// Another unused export
export function deadFormatter(text) {
    return text + "!";
}
"""
        }
    },
    "side_effects": {
        "name": "Side-Effect Preservation",
        "description": "Demonstrates preserving top-level initialization while purging unused exports.",
        "entry_points": ["src/index.prune"],
        "files": {
            "src/index.prune": """import { initApp } from './app.prune';

export function start() {
    return initApp();
}
""",
            "src/app.prune": """import { setupTelemetry } from './telemetry.prune';

export function initApp() {
    return "App Ready";
}
""",
            "src/telemetry.prune": """// Top-level side-effecting initialization
setupTelemetry();

export function setupTelemetry() {
    return "telemetry_active";
}

// Dead export
export function reportBug(bug) {
    return bug;
}
"""
        }
    },
    "cse_optimization": {
        "name": "Common Subexpression Elimination (CSE)",
        "description": "Demonstrates CSE optimization (O2) reusing duplicate expressions safely.",
        "entry_points": ["src/calc.prune"],
        "files": {
            "src/calc.prune": """export function processCoordinates(x, y) {
    const dist1 = (x * x) + (y * y);
    const dist2 = (x * x) + (y * y);
    return dist1 + dist2;
}
"""
        }
    },
    "circular_dependency": {
        "name": "Circular Dependency Scenario",
        "description": "Demonstrates cycle detection between interdependent modules.",
        "entry_points": ["src/serviceA.prune"],
        "files": {
            "src/serviceA.prune": """import { callB } from './serviceB.prune';

export function callA() {
    return callB();
}
""",
            "src/serviceB.prune": """import { callA } from './serviceA.prune';

export function callB() {
    return callA();
}
"""
        }
    },
    "syntax_error": {
        "name": "Compiler Diagnostic Frame",
        "description": "Demonstrates compiler syntax diagnostic with exact line/column and code frame.",
        "entry_points": ["src/broken.prune"],
        "files": {
            "src/broken.prune": """function brokenSyntax(x) {
    const = 100;
    return x;
}
"""
        }
    }
}


# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="ok", version="0.1.0")


@app.get("/api/samples")
def list_samples():
    """Returns available sample projects for easy demonstration in the UI."""
    return DEMO_PROJECTS


@app.post("/api/compile")
def compile_project(req: CompileRequest):
    """Compiles a project, producing bundle, graph, optimization trace, and statistics."""
    compiler = Compiler(level=req.optimization_level)
    result = compiler.compile_virtual(req.files, req.entry_points)
    return result.to_dict()


@app.post("/api/analyze")
def analyze_project(req: CompileRequest):
    """Runs compiler analysis and returns dependency graph, cycles, and diagnostics."""
    compiler = Compiler(level=req.optimization_level)
    result = compiler.compile_virtual(req.files, req.entry_points)
    return {
        "success": result.success,
        "graph": result.graph,
        "diagnostics": result.diagnostics,
        "stats": result.stats,
        "events": result.events
    }


@app.post("/api/graph")
def get_dependency_graph(req: CompileRequest):
    """Returns the export-level dependency graph formatted for React Flow."""
    compiler = Compiler(level=req.optimization_level)
    result = compiler.compile_virtual(req.files, req.entry_points)
    return result.graph or {}


# Mount built frontend assets so http://localhost:8000/ serves the web IDE directly
from pathlib import Path
from fastapi.staticfiles import StaticFiles

dist_path = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if dist_path.exists():
    app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="frontend")

