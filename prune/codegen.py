from __future__ import annotations
import re
from typing import Dict, List, Set, Optional, Tuple
from prune.ast_nodes import (
    ASTNode, Program, Statement, Expression, ImportDecl, ExportDecl, ExportNamedDecl,
    VarDecl, VariableDeclarator, FunctionDecl, IfStmt, ReturnStmt, BlockStmt,
    ExprStmt, AssignmentExpr, BinaryExpr, UnaryExpr, CallExpr,
    Identifier, NumberLiteral, StringLiteral, BooleanLiteral, NullLiteral
)
from prune.symbols import ModuleSymbolTable, SymbolResolver
from prune.graph import DependencyGraph


def sanitize_module_id(path: str) -> str:
    """Creates a valid JavaScript identifier prefix from a file path."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", path)
    clean = re.sub(r"_+", "_", clean).strip("_")
    return f"_{clean}" if clean else "_mod"


class CodeGenerator:
    """Generates a deterministic bundled JavaScript file with hygienic scoping and provenance."""

    def __init__(self, entry_paths: List[str], tables: Dict[str, ModuleSymbolTable],
                 resolver: SymbolResolver, graph: DependencyGraph):
        self.entry_paths = entry_paths
        self.tables = tables
        self.resolver = resolver
        self.graph = graph

        # Mapping: (module_path, local_symbol_name) -> mangled_js_name
        self.symbol_map: Dict[Tuple[str, str], str] = {}
        self._build_symbol_mapping()

    def _build_symbol_mapping(self) -> None:
        # Step 1: Assign unique prefixed names to each module's local & export symbols
        for mod_path, table in self.tables.items():
            mod_prefix = sanitize_module_id(mod_path)
            for local_name, sym in table.locals.items():
                if sym.kind.value != "import":
                    mangled = f"{mod_prefix}_{local_name}"
                    self.symbol_map[(mod_path, local_name)] = mangled

        # Step 2: Map imported symbols to their defining module's mangled name
        for mod_path, table in self.tables.items():
            for local_name, (imp_source, imp_name, _) in table.imports.items():
                target_path = self.resolver._resolve_module_path(mod_path, imp_source)
                if target_path and target_path in self.tables:
                    target_table = self.tables[target_path]
                    if imp_name in target_table.exports:
                        target_sym = target_table.exports[imp_name]
                        # Target symbol name in target module
                        mangled = self.symbol_map.get((target_path, target_sym.name), f"{sanitize_module_id(target_path)}_{target_sym.name}")
                        self.symbol_map[(mod_path, local_name)] = mangled

    def compute_module_order(self, modules: Dict[str, Program]) -> List[str]:
        """Topological sort of modules based on import dependencies."""
        adj: Dict[str, Set[str]] = {m: set() for m in modules.keys()}
        in_degree: Dict[str, int] = {m: 0 for m in modules.keys()}

        for m_path, table in self.tables.items():
            for _, (imp_source, _, _) in table.imports.items():
                target = self.resolver._resolve_module_path(m_path, imp_source)
                if target and target in modules and target != m_path:
                    # target must be emitted before m_path!
                    # Edge target -> m_path
                    if m_path not in adj[target]:
                        adj[target].add(m_path)
                        in_degree[m_path] += 1

        # Kahn's algorithm
        queue = [m for m, deg in sorted(in_degree.items()) if deg == 0]
        ordered: List[str] = []

        while queue:
            curr = queue.pop(0)
            ordered.append(curr)
            for neighbor in sorted(adj.get(curr, [])):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # If cycles exist, append any remaining modules deterministically
        for m in sorted(modules.keys()):
            if m not in ordered:
                ordered.append(m)

        return ordered

    def generate(self, modules: Dict[str, Program]) -> str:
        ordered_modules = self.compute_module_order(modules)
        lines: List[str] = [
            "// ============================================================================",
            "// Bundled by Prune — From-Scratch Explainable Bundler",
            "// ============================================================================",
            "(() => {",
            '  "use strict";',
            ""
        ]

        # Emit code for each module in topological order
        for mod_path in ordered_modules:
            prog = modules[mod_path]
            lines.append(f"  // --- Module: {mod_path} ---")

            # Hoist function declarations before top-level expression statements
            fn_stmts: List[Statement] = []
            other_stmts: List[Statement] = []
            for stmt in prog.body:
                if isinstance(stmt, (ImportDecl, ExportNamedDecl)):
                    continue
                if isinstance(stmt, FunctionDecl) or (isinstance(stmt, ExportDecl) and isinstance(stmt.declaration, FunctionDecl)):
                    fn_stmts.append(stmt)
                else:
                    other_stmts.append(stmt)

            for stmt in fn_stmts + other_stmts:
                stmt_str = self._emit_statement(stmt, mod_path, indent=2)
                if stmt_str.strip():
                    lines.append(stmt_str)

            lines.append("")

        # Expose exports of the primary entry module
        lines.append("  // --- Bundle Export Interface ---")
        lines.append("  const __prune_exports__ = {};")
        for entry_path in self.entry_paths:
            if entry_path in self.tables:
                entry_table = self.tables[entry_path]
                for exp_name, sym in sorted(entry_table.exports.items()):
                    node_id = f"{entry_path}:{exp_name}"
                    node = self.graph.nodes.get(node_id)
                    # Only export if reachable!
                    if node and node.is_reachable:
                        mangled_name = self.symbol_map.get((entry_path, sym.name), sym.name)
                        lines.append(f'  __prune_exports__["{exp_name}"] = {mangled_name};')

        lines.extend([
            "  if (typeof module !== 'undefined' && module.exports) {",
            "    module.exports = __prune_exports__;",
            "  } else if (typeof window !== 'undefined') {",
            "    window.PruneBundle = __prune_exports__;",
            "  }",
            "  return __prune_exports__;",
            "})();"
        ])

        return "\n".join(lines) + "\n"

    # -------------------------------------------------------------
    # Statement Emitters
    # -------------------------------------------------------------

    def _emit_statement(self, stmt: Statement, mod_path: str, indent: int = 2) -> str:
        pad = " " * indent
        loc_comment = f"{pad}// [{mod_path}:{stmt.location.line}:{stmt.location.column}]\n"

        if isinstance(stmt, ExportDecl):
            # Unwrap the declaration and emit it with mangled identifier
            return self._emit_statement(stmt.declaration, mod_path, indent)

        elif isinstance(stmt, VarDecl):
            decls_str = []
            for d in stmt.declarations:
                mangled_id = self.symbol_map.get((mod_path, d.id), d.id)
                if d.init:
                    init_str = self._emit_expression(d.init, mod_path)
                    decls_str.append(f"{mangled_id} = {init_str}")
                else:
                    decls_str.append(mangled_id)
            return f"{loc_comment}{pad}{stmt.kind} {', '.join(decls_str)};"

        elif isinstance(stmt, FunctionDecl):
            mangled_fn = self.symbol_map.get((mod_path, stmt.id), stmt.id)
            params_str = ", ".join(stmt.params)
            body_str = self._emit_block(stmt.body, mod_path, indent)
            return f"{loc_comment}{pad}function {mangled_fn}({params_str}) {body_str}"

        elif isinstance(stmt, ExprStmt):
            expr_str = self._emit_expression(stmt.expression, mod_path)
            return f"{loc_comment}{pad}{expr_str};"

        elif isinstance(stmt, ReturnStmt):
            if stmt.argument:
                return f"{pad}return {self._emit_expression(stmt.argument, mod_path)};"
            return f"{pad}return;"

        elif isinstance(stmt, IfStmt):
            test_str = self._emit_expression(stmt.test, mod_path)
            cons_str = self._emit_statement(stmt.consequent, mod_path, indent)
            if stmt.alternate:
                alt_str = self._emit_statement(stmt.alternate, mod_path, indent)
                return f"{pad}if ({test_str}) {{\n{cons_str}\n{pad}}} else {{\n{alt_str}\n{pad}}}"
            return f"{pad}if ({test_str}) {{\n{cons_str}\n{pad}}}"

        elif isinstance(stmt, BlockStmt):
            return self._emit_block(stmt, mod_path, indent)

        return ""

    def _emit_block(self, block: BlockStmt, mod_path: str, indent: int) -> str:
        pad = " " * indent
        inner_lines = []
        for s in block.body:
            stmt_code = self._emit_statement(s, mod_path, indent + 2)
            if stmt_code.strip():
                inner_lines.append(stmt_code)
        joined = "\n".join(inner_lines)
        return f"{{\n{joined}\n{pad}}}"

    # -------------------------------------------------------------
    # Expression Emitters
    # -------------------------------------------------------------

    def _emit_expression(self, expr: Expression, mod_path: str) -> str:
        if isinstance(expr, Identifier):
            # Resolve to mangled name if in module scope
            return self.symbol_map.get((mod_path, expr.name), expr.name)

        elif isinstance(expr, NumberLiteral):
            return expr.raw

        elif isinstance(expr, StringLiteral):
            # Escape strings
            escaped = expr.value.replace('"', '\\"')
            return f'"{escaped}"'

        elif isinstance(expr, BooleanLiteral):
            return "true" if expr.value else "false"

        elif isinstance(expr, NullLiteral):
            return "null"

        elif isinstance(expr, UnaryExpr):
            arg_str = self._emit_expression(expr.argument, mod_path)
            return f"{expr.operator}{arg_str}"

        elif isinstance(expr, BinaryExpr):
            l_str = self._emit_expression(expr.left, mod_path)
            r_str = self._emit_expression(expr.right, mod_path)
            return f"({l_str} {expr.operator} {r_str})"

        elif isinstance(expr, CallExpr):
            callee_str = self._emit_expression(expr.callee, mod_path)
            args_str = ", ".join(self._emit_expression(a, mod_path) for a in expr.arguments)
            return f"{callee_str}({args_str})"

        elif isinstance(expr, AssignmentExpr):
            mangled_lhs = self.symbol_map.get((mod_path, expr.left), expr.left)
            rhs_str = self._emit_expression(expr.right, mod_path)
            return f"{mangled_lhs} = {rhs_str}"

        return ""
