import pytest
from prune.parser import Parser
from prune.symbols import SymbolResolver
from prune.graph import DependencyGraph
from prune.optimizer import DeadCodeEliminationPass, OptimizationPipeline
from prune.ast_nodes import ExportDecl, FunctionDecl, VarDecl


def test_dce_removes_unreachable_export_and_retains_live():
    source_math = """
    export function liveAdd(a, b) { return a + b; }
    export function deadSubtract(a, b) { return a - b; }
    """
    source_main = """
    import { liveAdd } from './math.prune';
    export function run() {
        return liveAdd(1, 2);
    }
    """

    modules = {
        "math.prune": Parser.from_source(source_math, filename="math.prune").parse(),
        "main.prune": Parser.from_source(source_main, filename="main.prune").parse(),
    }

    resolver = SymbolResolver(modules)
    tables = resolver.resolve()
    graph = DependencyGraph.build(tables, entry_paths=["main.prune"], resolver=resolver)

    pipeline = OptimizationPipeline(level="O1")
    opt_modules, events = pipeline.run(modules, tables, graph)

    math_body = opt_modules["math.prune"].body
    # deadSubtract should be removed, liveAdd retained
    exported_fns = []
    for stmt in math_body:
        if isinstance(stmt, ExportDecl) and isinstance(stmt.declaration, FunctionDecl):
            exported_fns.append(stmt.declaration.id)

    assert "liveAdd" in exported_fns
    assert "deadSubtract" not in exported_fns

    dce_events = [e for e in events if e.event_type == "dead_code_elimination"]
    removed_events = [e for e in dce_events if e.decision == "removed"]
    assert any(e.symbol == "deadSubtract" for e in removed_events)


def test_dce_preserves_top_level_side_effects():
    # Module with top-level console/logger call
    source_logger = """
    print("Logger initialized");
    export function log(msg) { return msg; }
    """
    source_main = """
    export function main() { return 42; }
    """

    modules = {
        "logger.prune": Parser.from_source(source_logger, filename="logger.prune").parse(),
        "main.prune": Parser.from_source(source_main, filename="main.prune").parse(),
    }

    resolver = SymbolResolver(modules)
    tables = resolver.resolve()
    graph = DependencyGraph.build(tables, entry_paths=["main.prune"], resolver=resolver)

    pipeline = OptimizationPipeline(level="O1")
    opt_modules, events = pipeline.run(modules, tables, graph)

    logger_body = opt_modules["logger.prune"].body
    # Even though logger.log is dead, the top-level print statement should be preserved!
    has_print_stmt = any(s.__class__.__name__ == "ExprStmt" for s in logger_body)
    assert has_print_stmt is True

    side_effect_events = [e for e in events if e.event_type == "side_effect_retained"]
    assert len(side_effect_events) >= 1
