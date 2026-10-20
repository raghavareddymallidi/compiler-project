# Prune Compiler Architecture

Prune is an explainable compiler and module bundler written from scratch in Python. It does not use any third-party parser, AST generator, or bundler (such as Babel, Acorn, Webpack, or Rollup).

## Pipeline Flow

```
                      +-------------------+
                      |   Source Files    |
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |       Lexer       |  (Handwritten Tokenizer)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |   Token Stream    |  (Precise line/col/offsets)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |   R-D Parser      |  (Recursive-Descent with precedence climbing)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |    Module AST     |  (Structured AST Nodes)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      | Symbol Resolution |  (Scopes, exports, imports, duplicate check)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      | Export Dep Graph  |  (Fine-grained per-export nodes & edges)
                      +-------------------+
                                |
         +----------------------+----------------------+
         |                                             |
         v                                             v
+-------------------+                         +-------------------+
|  Cycle Detection  | (Tarjan SCC)            | Side-Effect Check | (Top-level statements)
+-------------------+                         +-------------------+
         |                                             |
         +----------------------+----------------------+
                                |
                                v
                      +-------------------+
                      | Reachability & DCE|  (Graph traversal from entry points)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      | Optimizer Passes  |  (Constant Folding, CSE, Side-effect preservation)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      | Topological Sort  |  (Deterministic module & declaration ordering)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |  Code Generator   |  (Hygienic renaming, IIFE/ESM bundle emit)
                      +-------------------+
                                |
                                v
                      +-------------------+
                      | Bundle & Explain  |  (Trace events, diagnostics, provenance)
                      +-------------------+
```

## Core Subsystems

1. **`prune.lexer`**: Scans characters, handles comments, produces typed tokens with exact `SourceLocation` (line, column, start/end byte offsets).
2. **`prune.parser`**: Recursive-descent parser constructing typed AST nodes with source positions.
3. **`prune.symbols`**: Symbol table, scoping, and module resolution. Validates imports against defining exports, detects duplicates and missing modules.
4. **`prune.graph`**: Builds export-level dependency graph (`ExportNode`, `ImportEdge`). Computes entry-point reachability using BFS/DFS. Detects dependency cycles using Tarjan's SCC algorithm.
5. **`prune.side_effects`**: Syntax-aware classifier determining if top-level expressions/statements produce observable side effects.
6. **`prune.optimizer`**:
   - `ConstantFoldingPass`: Recursively evaluates pure binary and unary expressions on literals without `eval()`.
   - `CSEPass`: Identifies identical subexpressions within local scopes, verifying that operand variables were not reassigned.
   - `DeadCodeEliminationPass`: Prunes unreachable export AST nodes based on graph reachability.
   - `OptimizationRecorder`: Logs each action (retained, removed, transformed, warning) with provenance.
7. **`prune.codegen`**: Emits clean JavaScript bundle. Renames top-level identifiers with module prefixes to avoid cross-module collisions while preserving semantics.
8. **`prune.diagnostics`**: Produces compiler-quality diagnostics with ASCII code frames highlighting the error location.
9. **`prune.compiler`**: The unified compiler coordinator powering both the CLI and FastAPI backend.
