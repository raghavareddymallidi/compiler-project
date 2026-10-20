from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from prune.ast_nodes import ASTNode, Statement, ExportDecl, FunctionDecl, VarDecl
from prune.symbols import ModuleSymbolTable, SymbolResolver, extract_referenced_identifiers
from prune.side_effects import classify_statement, Purity
from prune.diagnostics import SourceLocation, Diagnostic, DiagnosticSeverity


@dataclass
class ExportNode:
    id: str  # e.g. "math.prune:add"
    module_path: str
    symbol_name: str
    is_entry_point: bool = False
    is_reachable: bool = False
    is_side_effect: bool = False
    reachability_path: List[str] = field(default_factory=list)
    explanation: str = ""
    location: Optional[SourceLocation] = None
    declaration_node: Optional[ASTNode] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "module_path": self.module_path,
            "symbol_name": self.symbol_name,
            "is_entry_point": self.is_entry_point,
            "is_reachable": self.is_reachable,
            "is_side_effect": self.is_side_effect,
            "reachability_path": self.reachability_path,
            "explanation": self.explanation,
            "location": self.location.to_dict() if self.location else None,
        }


@dataclass
class ImportEdge:
    from_node: str
    to_node: str
    kind: str = "import"  # "import" | "reference" | "init"

    def to_dict(self) -> dict:
        return {
            "from_node": self.from_node,
            "to_node": self.to_node,
            "kind": self.kind,
        }


class DependencyGraph:
    """Per-export dependency graph for multi-module projects."""

    def __init__(self):
        self.nodes: Dict[str, ExportNode] = {}
        self.edges: List[ImportEdge] = []
        self.adjacency: Dict[str, Set[str]] = {}
        self.reverse_adjacency: Dict[str, Set[str]] = {}
        self.cycles: List[List[str]] = []

    def add_node(self, node: ExportNode) -> None:
        self.nodes[node.id] = node
        if node.id not in self.adjacency:
            self.adjacency[node.id] = set()
        if node.id not in self.reverse_adjacency:
            self.reverse_adjacency[node.id] = set()

    def add_edge(self, from_id: str, to_id: str, kind: str = "import") -> None:
        if from_id not in self.adjacency:
            self.adjacency[from_id] = set()
        if to_id not in self.reverse_adjacency:
            self.reverse_adjacency[to_id] = set()

        self.adjacency[from_id].add(to_id)
        self.reverse_adjacency[to_id].add(from_id)
        self.edges.append(ImportEdge(from_node=from_id, to_node=to_id, kind=kind))

    @classmethod
    def build(cls, tables: Dict[str, ModuleSymbolTable], entry_paths: List[str], resolver: SymbolResolver) -> DependencyGraph:
        graph = cls()

        # Phase 1: Create nodes for all exports and top-level side effects in each module
        for path, table in tables.items():
            is_entry = path in entry_paths

            # Top-level side effects node if module contains top-level calls or impure stmts
            impure_stmts = [s for s in table.top_level_statements if classify_statement(s) != Purity.PURE]
            if impure_stmts:
                init_id = f"{path}:<init>"
                graph.add_node(ExportNode(
                    id=init_id,
                    module_path=path,
                    symbol_name="<init>",
                    is_entry_point=is_entry,
                    is_side_effect=True,
                    explanation="Top-level module initialization and side effects",
                    location=impure_stmts[0].location
                ))

            # Export nodes
            for exp_name, sym in table.exports.items():
                node_id = f"{path}:{exp_name}"
                graph.add_node(ExportNode(
                    id=node_id,
                    module_path=path,
                    symbol_name=exp_name,
                    is_entry_point=is_entry,
                    is_side_effect=False,
                    location=sym.location,
                    declaration_node=sym.declaration_node
                ))

        # Helper to find which node provides a local identifier in a module
        def resolve_local_target(from_path: str, ident: str) -> Optional[str]:
            table = tables[from_path]
            # Is it imported?
            if ident in table.imports:
                imp_source, imp_name, _ = table.imports[ident]
                target_path = resolver._resolve_module_path(from_path, imp_source)
                if target_path:
                    target_id = f"{target_path}:{imp_name}"
                    if target_id in graph.nodes:
                        return target_id
            # Is it an export in the same module?
            if ident in table.exports:
                target_id = f"{from_path}:{ident}"
                if target_id in graph.nodes:
                    return target_id
            return None

        # Helper to find all dependencies of a declaration (including local internal helpers)
        def find_symbol_deps(from_path: str, sym_node: ASTNode) -> Set[str]:
            refs = extract_referenced_identifiers(sym_node)
            resolved_targets: Set[str] = set()
            table = tables[from_path]

            visited_locals: Set[str] = set()
            to_process = list(refs)

            while to_process:
                ref = to_process.pop()
                target_id = resolve_local_target(from_path, ref)
                if target_id and target_id not in resolved_targets:
                    resolved_targets.add(target_id)
                elif ref in table.locals and ref not in visited_locals:
                    # Check if local helper references imported symbols
                    visited_locals.add(ref)
                    local_sym = table.locals[ref]
                    if local_sym.declaration_node:
                        local_refs = extract_referenced_identifiers(local_sym.declaration_node)
                        for lr in local_refs:
                            if lr not in visited_locals:
                                to_process.append(lr)

            return resolved_targets

        # Phase 2: Add edges from export nodes to target export nodes
        for path, table in tables.items():
            for exp_name, sym in table.exports.items():
                from_id = f"{path}:{exp_name}"
                if sym.declaration_node:
                    targets = find_symbol_deps(path, sym.declaration_node)
                    for t in targets:
                        if t != from_id:
                            graph.add_edge(from_id, t, kind="reference")

            # Edges from top-level init
            impure_stmts = [s for s in table.top_level_statements if classify_statement(s) != Purity.PURE]
            if impure_stmts:
                init_id = f"{path}:<init>"
                for stmt in impure_stmts:
                    targets = find_symbol_deps(path, stmt)
                    for t in targets:
                        if t != init_id:
                            graph.add_edge(init_id, t, kind="init")

            # Connect module imports to imported module's <init>
            for local_name, (imp_source, _, _) in table.imports.items():
                target_path = resolver._resolve_module_path(path, imp_source)
                if target_path:
                    target_init_id = f"{target_path}:<init>"
                    if target_init_id in graph.nodes:
                        for exp_name, sym in table.exports.items():
                            from_id = f"{path}:{exp_name}"
                            graph.add_edge(from_id, target_init_id, kind="init")

        # Phase 3: Detect circular dependencies
        graph.detect_cycles()

        # Phase 4: Run reachability analysis
        graph.compute_reachability(entry_paths)

        return graph

    def detect_cycles(self) -> List[List[str]]:
        """Detects cycles in the dependency graph using DFS."""
        visited: Dict[str, int] = {}  # 0: unvisited, 1: visiting, 2: visited
        parent_map: Dict[str, str] = {}
        cycles: List[List[str]] = []

        def dfs(node_id: str, path: List[str]):
            visited[node_id] = 1
            for neighbor in sorted(self.adjacency.get(node_id, [])):
                if visited.get(neighbor, 0) == 1:
                    # Found cycle
                    cycle_start_idx = path.index(neighbor) if neighbor in path else 0
                    cycle_path = path[cycle_start_idx:] + [neighbor]
                    cycles.append(cycle_path)
                elif visited.get(neighbor, 0) == 0:
                    dfs(neighbor, path + [neighbor])
            visited[node_id] = 2

        for nid in sorted(self.nodes.keys()):
            if visited.get(nid, 0) == 0:
                dfs(nid, [nid])

        self.cycles = cycles
        return cycles

    def compute_reachability(self, entry_paths: List[str]) -> None:
        """Computes reachability of all nodes starting from entry modules."""
        queue: List[Tuple[str, List[str]]] = []
        visited: Set[str] = set()

        # Roots: All exports and top-level side effects in entry modules
        for node_id, node in self.nodes.items():
            if node.module_path in entry_paths:
                node.is_entry_point = True
                queue.append((node_id, [node_id]))
                visited.add(node_id)
                node.is_reachable = True
                node.reachability_path = [node_id]
                node.explanation = f"Entry-point export in '{node.module_path}'"

        # Breadth-first traversal along dependency edges
        while queue:
            curr_id, path = queue.pop(0)
            for neighbor_id in sorted(self.adjacency.get(curr_id, [])):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    n_path = path + [neighbor_id]
                    if neighbor_id in self.nodes:
                        n_node = self.nodes[neighbor_id]
                        n_node.is_reachable = True
                        n_node.reachability_path = n_path
                        readable_path = " -> ".join(n_path)
                        n_node.explanation = f"Retained: Reachable from entry via path: {readable_path}"
                    queue.append((neighbor_id, n_path))

        # Mark unreachable nodes and explain
        for node_id, node in self.nodes.items():
            if not node.is_reachable:
                node.is_reachable = False
                node.explanation = f"Eliminated: Unreachable from any entry point in {entry_paths}"

    def to_react_flow(self) -> dict:
        """Converts graph into React Flow compatible node and edge structures."""
        rf_nodes = []
        rf_edges = []

        # Position nodes grouped by module
        modules = sorted(list({node.module_path for node in self.nodes.values()}))
        mod_x = {mod: i * 350 for i, mod in enumerate(modules)}
        mod_y_counters: Dict[str, int] = {mod: 0 for mod in modules}

        for node_id, node in self.nodes.items():
            y_idx = mod_y_counters[node.module_path]
            mod_y_counters[node.module_path] += 1

            status = "reachable" if node.is_reachable else "unreachable"
            if node.is_entry_point:
                status = "entry"
            if node.is_side_effect:
                status = "side_effect"

            rf_nodes.append({
                "id": node.id,
                "type": "custom",
                "data": {
                    "id": node.id,
                    "label": f"{node.symbol_name}",
                    "module": node.module_path,
                    "symbol": node.symbol_name,
                    "status": status,
                    "is_reachable": node.is_reachable,
                    "is_entry": node.is_entry_point,
                    "is_side_effect": node.is_side_effect,
                    "explanation": node.explanation,
                    "path": node.reachability_path,
                    "location": node.location.to_dict() if node.location else None
                },
                "position": {"x": mod_x[node.module_path] + 50, "y": y_idx * 120 + 50}
            })

        for edge_idx, edge in enumerate(self.edges):
            rf_edges.append({
                "id": f"e_{edge.from_node}_{edge.to_node}_{edge_idx}",
                "source": edge.from_node,
                "target": edge.to_node,
                "label": edge.kind,
                "animated": True if edge.kind == "init" else False,
            })

        return {
            "nodes": rf_nodes,
            "edges": rf_edges,
            "cycles": self.cycles,
            "total_exports": len(self.nodes),
            "reachable_exports": sum(1 for n in self.nodes.values() if n.is_reachable),
            "removed_exports": sum(1 for n in self.nodes.values() if not n.is_reachable),
        }
