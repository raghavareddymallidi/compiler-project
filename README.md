# Prune — From-Scratch Compiler, Optimizer & Explainable Bundler

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19-cyan.svg)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-6.0-purple.svg)](https://vitejs.dev)

**Prune** is an academic compiler, optimizer, and module bundler written **from scratch** in Python, paired with an interactive developer utility web application built in React, TypeScript, and React Flow.

Unlike typical bundlers that operate at whole-file granularity, Prune constructs a **fine-grained per-export dependency graph**, safely eliminates unreachable export declarations, performs arithmetic/logical **constant folding** and **common subexpression elimination (CSE)**, preserves observable top-level module **side effects**, resolves circular dependencies, and produces **100% executable, hygienic JavaScript bundles**.

Crucially, Prune is **explainable**: every optimization or dead-code elimination decision is recorded as a structured event detailing *what* was transformed or removed, *why*, and *through which exact reachability path*.

---

## Compiler Architecture & Pipeline

```
Source Modules (.prune / .js)
        │
        ▼
   Handwritten Lexer           ──> Precise tokens with line, column, and start/end byte offsets
        │
        ▼
Recursive-Descent Parser       ──> Clean AST nodes with precedence climbing (no external parsers)
        │
        ▼
Module & Symbol Resolution     ──> Scopes, relative path resolution, duplicate & unresolved checks
        │
        ▼
Per-Export Dependency Graph    ──> Fine-grained export nodes, import edges, Tarjan/DFS cycle detection
        │
        ▼
Reachability & Purity Analysis ──> BFS from entry roots, conservative top-level side-effect classifier
        │
        ▼
Optimization Pipeline          ──> Constant Folding, Common Subexpression Elimination (CSE), DCE
        │
        ▼
Topological Ordering & Codegen ──> Hygienic module prefixing (avoids collisions), deterministic emit
        │
        ▼
Bundle & Optimization Trace    ──> Executable bundle (Node.js/browser) + Explainable optimization report
```

---

## Supported Language Subset

Prune compiles a coherent, well-defined subset of JavaScript/ECMAScript with module support (`.prune` / `.js`):

- **Module Statements**:
  - Named imports: `import { add, sub as subtract } from './math.prune';`
  - Named exports: `export const PI = 3.14;`, `export let counter = 0;`, `export function add(a, b) { return a + b; }`
  - Export specifiers: `export { fnA, fnB as aliasB };`
- **Declarations & Statements**:
  - `const`, `let`, `var` declarations
  - Function declarations: `function name(params) { body }`
  - `return expr;`
  - `if (test) stmt else stmt`
  - Block statements `{ ... }`
  - Expression statements `call();`
- **Expressions**:
  - Arithmetic: `+`, `-`, `*`, `/`, `%` (precedence climbing)
  - Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
  - Logical: `&&`, `||`, `!`
  - Assignments: `variable = expr`
  - Function calls: `callee(arg1, arg2, ...)`
  - Literals: Integers, floats, strings (`"..."`, `'...'`), booleans (`true`, `false`), `null`
  - Single-line (`//`) and multi-line (`/* */`) comments

For formal EBNF specifications, see [`docs/grammar.md`](docs/grammar.md).

---

## Optimization Levels

| Level | Optimizations Applied | Description |
|---|---|---|
| **`-O0`** | None | Full lexical, syntactic, and semantic validation. Builds graph and bundles all modules without pruning or folding. |
| **`-O1`** | **Constant Folding + DCE** | Evaluates constant arithmetic/logical expressions; eliminates dead exports unreachable from entry points. |
| **`-O2`** | **O1 + CSE + Side-Effects** | Level O1 plus Common Subexpression Elimination (CSE) over pure expressions within functions and side-effect preservation. |

For detailed descriptions of the optimization algorithms, see [`docs/optimization-passes.md`](docs/optimization-passes.md).

---

## Quickstart & Installation

### Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Node.js 18+ and npm

### Setup
```bash
# Clone and enter workspace
git clone <repo-url>
cd "compiler project"

# Setup Python virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Setup Frontend dependencies
cd frontend
npm install
cd ..
```

---

## Command-Line Interface (CLI)

Prune includes a developer CLI built with Typer and Rich:

```bash
# Build and bundle from an entry point
python3 -m prune.cli build examples/main_project/src/main.prune --level O2 --output dist/bundle.js -v

# Analyze dependencies and dead exports without generating a file
python3 -m prune.cli analyze examples/main_project/src/main.prune

# View per-export dependency graph
python3 -m prune.cli graph examples/main_project/src/main.prune

# Output graph as structured JSON
python3 -m prune.cli graph examples/main_project/src/main.prune --format json

# Generate explainability optimization report
python3 -m prune.cli report examples/main_project/src/main.prune --level O2
```

### Validating Bundle Runtime Execution
To verify that the generated bundle is real, executable JavaScript:
```bash
node -e "const b = require('./dist/bundle.js'); console.log('Execution result:', b.run('Alice', 2));"
```
Output:
```text
Run result: 262
```

---

## Running the Web Application

The interactive web UI features an export dependency graph (React Flow), side-by-side Monaco code editor, filterable optimization trace, compiler diagnostics code frame, and bundle metrics.

### 1. Launch FastAPI Backend
```bash
source .venv/bin/activate
uvicorn prune.server:app --reload --port 8000
```
API Documentation is available at `http://localhost:8000/docs`.

### 2. Launch React Frontend
```bash
cd frontend
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## Testing & Verification

Prune includes a 34-test Python suite, Node.js runtime validation, and Vitest component tests:

```bash
# 1. Run all 34 compiler, optimizer, and backend tests
pytest -v

# 2. Run frontend component tests
cd frontend
npm test

# 3. Test production build of frontend
npm run build
```

See [`docs/feature-verification.md`](docs/feature-verification.md) for the complete feature verification matrix.

---

## Demonstration Sequence for Evaluators

When presenting Prune to a Compiler Design evaluator:

1. **Dead Code Elimination Demo**:
   - In the web app, select the **Standard Multi-Module** fixture.
   - Click **Build & Analyze**.
   - Note how `src/math.prune:deadMultiply` and `src/utils.prune:deadFormatter` turn red with a `DEAD` badge in the Dependency Graph.
   - Inspect the node: the inspector explains *"Eliminated: Unreachable from any entry point"*.
   - In the right-hand **Optimized Bundle** editor, observe that `deadMultiply` was omitted while `add` and `greet` were retained.
2. **Constant Folding & CSE Demo**:
   - In the Optimization Trace tab, filter by **Constant Folding** to view `(15 + 25 * 2) ==> 65`.
   - Switch optimization level to **`-O2`** and build. Filter by **CSE** to see `(baseVal * multiplier)` replaced by reusable variable `score1`.
3. **Top-Level Side Effects Demo**:
   - Select the **Side-Effect Preservation** fixture.
   - Note that `telemetry.prune`'s export `reportBug` is dead and eliminated, BUT its top-level call `setupTelemetry()` is preserved in the bundle.
4. **Circular Dependency Detection Demo**:
   - Select the **Circular Dependency Scenario** fixture.
   - Click **Build & Analyze** and observe the prominent cycle alert: `src/serviceA.prune → src/serviceB.prune → src/serviceA.prune`.
5. **Compiler Diagnostic Demo**:
   - Select the **Compiler Diagnostic Frame** fixture and view the rich terminal-style code frame pointing with `^` to the exact column error.
