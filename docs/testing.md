# Prune Testing Strategy & Verification Guide

Prune uses a dual-layer test suite:
1. **Compiler & Backend**: 34 unit and integration tests using `pytest` verifying the Lexer, Parser, Symbol Resolver, Per-Export Dependency Graph, Reachability Analysis, Optimization Passes (Constant Folding, CSE, DCE), Topological Ordering, Code Generation, Diagnostics, CLI, and FastAPI backend.
2. **Runtime Verification**: Bundled output is dynamically evaluated inside Node.js (`node -e`) to prove that generated JavaScript executes with correct runtime semantics.
3. **Frontend**: Component tests using `vitest` and `@testing-library/react` verifying accurate rendering of statistics, diagnostics code frames, and graph node reachability inspector.

## Running Tests

### 1. Run Compiler & Backend Test Suite
```bash
# Activate virtual environment
source .venv/bin/activate

# Run all 34 pytest tests
pytest -v

# Run with test coverage
pytest --cov=prune --cov-report=term-missing
```

### 2. Run Frontend Tests
```bash
cd frontend
npm test
```

### 3. Run Production Frontend Build
```bash
cd frontend
npm run build
```

### 4. Run CLI End-to-End Build & Execution
```bash
# Build the example project with O2 optimizations
python3 -m prune.cli build examples/main_project/src/main.prune --level O2 --output dist/bundle.js -v

# Execute the bundle in Node.js
node -e "const b = require('./dist/bundle.js'); console.log('Bundle execution result:', b.run('Alice', 2));"
```
Expected output:
```text
Run result: 262
```

## Test Coverage Breakdown

| Area | Test File | Test Count | Key Invariants Verified |
|---|---|---|---|
| **Lexer** | `tests/test_lexer.py` | 7 | Tokens, comments, strings, escape characters, line/col offsets, error diagnostics |
| **Parser** | `tests/test_parser.py` | 4 | Recursive-descent AST creation, precedence climbing, statements, syntax errors |
| **Symbols & Scopes** | `tests/test_graph.py`, `tests/test_compiler.py` | 4 | Duplicate declaration prevention, unresolved imports, missing exports |
| **Export Graph & Cycles** | `tests/test_graph.py` | 2 | Per-export granularity, DFS cycle detection, BFS reachability paths |
| **Constant Folding** | `tests/test_constant_folding.py` | 3 | Arithmetic precedence, division-by-zero protection, boolean/unary folding |
| **CSE** | `tests/test_cse.py` | 2 | Elimination of duplicate pure expressions, safety on variable reassignment |
| **DCE & Side Effects** | `tests/test_dce.py` | 2 | Pruning dead exports, retaining live exports, preserving top-level side effects |
| **Codegen & Scoping** | `tests/test_codegen.py` | 2 | Name collision avoidance, module scoping, Node.js runtime execution |
| **Compiler & Entry Points** | `tests/test_compiler.py` | 4 | Multiple entry points, independent reachability, O0 vs O1 vs O2 behavior |
| **CLI** | `tests/test_cli.py` | 3 | Help flag, build/report/analyze subcommands, exit codes |
| **FastAPI Backend** | `tests/test_api.py` | 4 | Health check, samples endpoint, compile payload, diagnostic responses |
| **End-to-End** | `tests/test_e2e.py` | 1 | Full 3-module compilation with live/dead exports, side effects, executed with Node |
| **Frontend Components** | `frontend/src/components.test.tsx` | 3 | Statistics metrics, code frames, node inspector provenance |
