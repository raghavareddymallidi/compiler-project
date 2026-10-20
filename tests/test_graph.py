import pytest
from prune.parser import Parser
from prune.symbols import SymbolResolver
from prune.graph import DependencyGraph


def test_per_export_graph_and_reachability():
    # math.prune has add (used) and deadExport (unused)
    source_math = """
    export function add(a, b) { return a + b; }
    export function deadExport() { return 999; }
    """
    # main.prune only imports add
    source_main = """
    import { add } from './math.prune';
    export function compute(x) {
        return add(x, 10);
    }
    """

    modules = {
        "math.prune": Parser.from_source(source_math, filename="math.prune").parse(),
        "main.prune": Parser.from_source(source_main, filename="main.prune").parse(),
    }

    resolver = SymbolResolver(modules)
    tables = resolver.resolve()
    graph = DependencyGraph.build(tables, entry_paths=["main.prune"], resolver=resolver)

    # Check nodes
    assert "main.prune:compute" in graph.nodes
    assert "math.prune:add" in graph.nodes
    assert "math.prune:deadExport" in graph.nodes

    # Check reachability
    assert graph.nodes["main.prune:compute"].is_reachable is True
    assert graph.nodes["math.prune:add"].is_reachable is True
    assert graph.nodes["math.prune:deadExport"].is_reachable is False

    # Check path and explanation
    assert graph.nodes["math.prune:add"].reachability_path == ["main.prune:compute", "math.prune:add"]
    assert "Eliminated" in graph.nodes["math.prune:deadExport"].explanation


def test_circular_dependency_detection():
    # a imports b, b imports a
    source_a = """
    import { fnB } from './b.prune';
    export function fnA() { return fnB(); }
    """
    source_b = """
    import { fnA } from './a.prune';
    export function fnB() { return fnA(); }
    """

    modules = {
        "a.prune": Parser.from_source(source_a, filename="a.prune").parse(),
        "b.prune": Parser.from_source(source_b, filename="b.prune").parse(),
    }

    resolver = SymbolResolver(modules)
    tables = resolver.resolve()
    graph = DependencyGraph.build(tables, entry_paths=["a.prune"], resolver=resolver)

    assert len(graph.cycles) > 0
    cycle = graph.cycles[0]
    # Check that cycle loops
    assert cycle[0] == cycle[-1]
