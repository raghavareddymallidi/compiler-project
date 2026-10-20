# Prune Optimization Passes & Levels

Prune features an explainable optimization framework where every transformation emits an event detailing why a decision was made.

## Optimization Levels

- **`-O0` (No Optimizations)**:
  - Lexical, syntactic, and semantic validation.
  - Per-export dependency graph construction and cycle detection.
  - Generates bundle containing all definitions without dead-code elimination, constant folding, or CSE.
- **`-O1` (Standard Optimizations)**:
  - All validations from `-O0`.
  - **Dead-Code Elimination (DCE)**: Prunes all exports unreachable from the entry point(s).
  - **Constant Folding**: Evaluates constant arithmetic/logical expressions at compile-time.
- **`-O2` (Aggressive Safe Optimizations)**:
  - All passes from `-O1`.
  - **Common Subexpression Elimination (CSE)**: Evaluates duplicated pure expressions once and reuses the result within basic blocks, guarding against reassignment.
  - **Side-Effect Aware Dead Code Elimination**: Safely strips unreferenced local variables while strictly preserving observable top-level calls.

## Detailed Pass Descriptions

### 1. Dead-Code Elimination (DCE)
- **Granularity**: Individual named export symbols (not whole files).
- **Algorithm**:
  1. Initialize `reachable_set` with all exports and top-level side-effect statements of the entry module(s).
  2. Perform graph traversal (BFS/DFS) along outgoing dependency edges (`Node A -> imports -> Node B`).
  3. Mark all reached nodes as LIVE (`RETAINED`).
  4. For all remaining unvisited export nodes, mark as DEAD (`REMOVED`) and filter their AST declarations out of code generation.
  5. Log explanation event with exact reachability path (e.g. `entry.prune:main -> math.prune:add`).

### 2. Constant Folding
- **Evaluator**: Pure Python arithmetic evaluator on AST nodes (NEVER `eval()`).
- **Supported Operations**:
  - Binary: `+`, `-`, `*`, `/`, `%`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `&&`, `||`
  - Unary: `-`, `+`, `!`
- **Safety Checks**:
  - Division by zero is detected and NOT folded (preserves runtime behavior / warnings).
  - Non-literal operands prevent folding.
  - Preserves exact source location on replacement literal AST node.

### 3. Common Subexpression Elimination (CSE)
- **Safety Preconditions**:
  - Expressions must be pure (no function calls, no mutations).
  - Variables referenced in the subexpression must NOT have been reassigned between the first computation and subsequent occurrences.
  - Scoped to straight-line blocks or function bodies.
- **Action**:
  - First occurrence is captured into a compiler-generated temp variable (`_cse_temp_N`).
  - Subsequent duplicate occurrences are replaced with the temp identifier.

### 4. Side-Effect Classification
- **Pure**: Literals, identifiers, binary/unary expressions of pure sub-expressions, function definitions.
- **Potentially Impure**: Function calls, variable assignments to external scopes, global references.
- **Rule**: If a module contains top-level impure statements, those statements are ALWAYS retained in the bundle in their original order, even if all exports from that module are eliminated.
