from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from prune.ast_nodes import (
    ASTNode, Program, Statement, Expression, ImportDecl, ImportSpecifier,
    ExportDecl, ExportNamedDecl, ExportSpecifier, VarDecl, VariableDeclarator,
    FunctionDecl, IfStmt, ReturnStmt, BlockStmt, ExprStmt,
    AssignmentExpr, BinaryExpr, UnaryExpr, CallExpr,
    Identifier, NumberLiteral, StringLiteral, BooleanLiteral, NullLiteral
)
from prune.diagnostics import SourceLocation, Diagnostic, DiagnosticSeverity, CompilerDiagnosticError


class SymbolKind(Enum):
    VARIABLE = "variable"
    FUNCTION = "function"
    IMPORT = "import"
    PARAMETER = "parameter"


@dataclass
class Symbol:
    name: str
    kind: SymbolKind
    declaration_node: Optional[ASTNode]
    module_path: str
    location: SourceLocation
    # If kind == IMPORT: which module and exported symbol name
    import_source: Optional[str] = None
    imported_name: Optional[str] = None


@dataclass
class ModuleSymbolTable:
    module_path: str
    program: Program
    # Local declarations in module scope
    locals: Dict[str, Symbol] = field(default_factory=dict)
    # Exports available to other modules: exported_name -> local Symbol
    exports: Dict[str, Symbol] = field(default_factory=dict)
    # Imports: local_name -> (import_source_path, imported_name, location)
    imports: Dict[str, Tuple[str, str, SourceLocation]] = field(default_factory=dict)
    # Top-level statements that are NOT pure declarations (e.g. top-level calls)
    top_level_statements: List[Statement] = field(default_factory=list)


def extract_referenced_identifiers(node: ASTNode, bound_params: Optional[Set[str]] = None) -> Set[str]:
    """Recursively extracts all free identifier names referenced within an AST node."""
    bound = set(bound_params or ())
    referenced: Set[str] = set()

    def walk(n: Optional[ASTNode]):
        if n is None:
            return

        if isinstance(n, Identifier):
            if n.name not in bound:
                referenced.add(n.name)
        elif isinstance(n, AssignmentExpr):
            if n.left not in bound:
                referenced.add(n.left)
            walk(n.right)
        elif isinstance(n, BinaryExpr):
            walk(n.left)
            walk(n.right)
        elif isinstance(n, UnaryExpr):
            walk(n.argument)
        elif isinstance(n, CallExpr):
            walk(n.callee)
            for arg in n.arguments:
                walk(arg)
        elif isinstance(n, ReturnStmt):
            walk(n.argument)
        elif isinstance(n, ExprStmt):
            walk(n.expression)
        elif isinstance(n, IfStmt):
            walk(n.test)
            walk(n.consequent)
            walk(n.alternate)
        elif isinstance(n, BlockStmt):
            for s in n.body:
                walk(s)
        elif isinstance(n, VarDecl):
            for d in n.declarations:
                walk(d.init)
        elif isinstance(n, VariableDeclarator):
            walk(n.init)
        elif isinstance(n, FunctionDecl):
            # Function declaration within expression or block: add params to bound
            sub_bound = bound | set(n.params)
            for s in n.body.body:
                # walk with sub_bound
                walk_with_bound(s, sub_bound)

    def walk_with_bound(curr: Optional[ASTNode], b: Set[str]):
        if curr is None:
            return
        if isinstance(curr, Identifier):
            if curr.name not in b:
                referenced.add(curr.name)
        elif isinstance(curr, AssignmentExpr):
            if curr.left not in b:
                referenced.add(curr.left)
            walk_with_bound(curr.right, b)
        elif isinstance(curr, BinaryExpr):
            walk_with_bound(curr.left, b)
            walk_with_bound(curr.right, b)
        elif isinstance(curr, UnaryExpr):
            walk_with_bound(curr.argument, b)
        elif isinstance(curr, CallExpr):
            walk_with_bound(curr.callee, b)
            for arg in curr.arguments:
                walk_with_bound(arg, b)
        elif isinstance(curr, ReturnStmt):
            walk_with_bound(curr.argument, b)
        elif isinstance(curr, ExprStmt):
            walk_with_bound(curr.expression, b)
        elif isinstance(curr, IfStmt):
            walk_with_bound(curr.test, b)
            walk_with_bound(curr.consequent, b)
            walk_with_bound(curr.alternate, b)
        elif isinstance(curr, BlockStmt):
            for s in curr.body:
                walk_with_bound(s, b)
        elif isinstance(curr, VarDecl):
            for d in curr.declarations:
                walk_with_bound(d.init, b)

    if isinstance(node, FunctionDecl):
        inner_bound = bound | set(node.params)
        for s in node.body.body:
            walk_with_bound(s, inner_bound)
    else:
        walk(node)

    return referenced


class SymbolResolver:
    """Collects symbols per module and resolves cross-module imports and exports."""

    def __init__(self, modules: Dict[str, Program]):
        # normalized_path -> Program
        self.modules = modules
        self.tables: Dict[str, ModuleSymbolTable] = {}

    def resolve(self) -> Dict[str, ModuleSymbolTable]:
        # Phase 1: Build local symbol tables for each module
        for path, program in self.modules.items():
            self.tables[path] = self._build_module_table(path, program)

        # Phase 2: Resolve cross-module imports against target module exports
        for path, table in self.tables.items():
            for local_name, (import_source, imported_name, loc) in table.imports.items():
                resolved_target_path = self._resolve_module_path(path, import_source)
                if not resolved_target_path or resolved_target_path not in self.tables:
                    raise CompilerDiagnosticError(Diagnostic(
                        message=f"Cannot resolve module '{import_source}' from '{path}'",
                        severity=DiagnosticSeverity.ERROR,
                        location=loc,
                        suggestion=f"Verify that file '{import_source}' exists relative to '{path}'"
                    ))

                target_table = self.tables[resolved_target_path]
                if imported_name not in target_table.exports:
                    available = ", ".join(repr(k) for k in target_table.exports.keys()) or "none"
                    raise CompilerDiagnosticError(Diagnostic(
                        message=f"Module '{import_source}' has no export named '{imported_name}' (available exports: {available})",
                        severity=DiagnosticSeverity.ERROR,
                        location=loc,
                        suggestion=f"Check the spelling of export '{imported_name}' in {import_source}"
                    ))

        return self.tables

    def _resolve_module_path(self, current_module_path: str, import_spec: str) -> Optional[str]:
        """Resolves relative import paths like './math.prune' or './math'."""
        curr_dir = Path(current_module_path).parent

        # Try exact or extensions
        possible_paths = [
            (curr_dir / import_spec).resolve(),
            (curr_dir / f"{import_spec}.prune").resolve(),
            (curr_dir / f"{import_spec}.js").resolve(),
        ]

        # Check against loaded modules first (relative keys)
        for cand in [import_spec, f"{import_spec}.prune", f"{import_spec}.js"]:
            # Normalize candidate relative to curr_dir
            norm_cand = str(Path(curr_dir / cand).as_posix())
            if norm_cand in self.modules:
                return norm_cand
            # Also check if cand is verbatim key in modules
            if cand in self.modules:
                return cand

        # Also check with normalized posix paths
        for p in self.modules.keys():
            for cand in possible_paths:
                try:
                    if Path(p).resolve() == cand:
                        return p
                except Exception:
                    pass

        return None

    def _build_module_table(self, module_path: str, program: Program) -> ModuleSymbolTable:
        table = ModuleSymbolTable(module_path=module_path, program=program)

        for stmt in program.body:
            if isinstance(stmt, ImportDecl):
                for spec in stmt.specifiers:
                    if spec.local in table.locals:
                        raise CompilerDiagnosticError(Diagnostic(
                            message=f"Duplicate identifier '{spec.local}' in module '{module_path}'",
                            severity=DiagnosticSeverity.ERROR,
                            location=spec.location,
                            suggestion=f"Identifier '{spec.local}' is already declared in this module"
                        ))
                    sym = Symbol(
                        name=spec.local,
                        kind=SymbolKind.IMPORT,
                        declaration_node=stmt,
                        module_path=module_path,
                        location=spec.location,
                        import_source=stmt.source,
                        imported_name=spec.imported
                    )
                    table.locals[spec.local] = sym
                    table.imports[spec.local] = (stmt.source, spec.imported, spec.location)

            elif isinstance(stmt, ExportDecl):
                decl = stmt.declaration
                if isinstance(decl, VarDecl):
                    for v in decl.declarations:
                        if v.id in table.locals:
                            raise CompilerDiagnosticError(Diagnostic(
                                message=f"Duplicate identifier '{v.id}' in module '{module_path}'",
                                severity=DiagnosticSeverity.ERROR,
                                location=v.location
                            ))
                        sym = Symbol(
                            name=v.id,
                            kind=SymbolKind.VARIABLE,
                            declaration_node=decl,
                            module_path=module_path,
                            location=v.location
                        )
                        table.locals[v.id] = sym
                        table.exports[v.id] = sym
                elif isinstance(decl, FunctionDecl):
                    if decl.id in table.locals:
                        raise CompilerDiagnosticError(Diagnostic(
                            message=f"Duplicate identifier '{decl.id}' in module '{module_path}'",
                            severity=DiagnosticSeverity.ERROR,
                            location=decl.location
                        ))
                    sym = Symbol(
                        name=decl.id,
                        kind=SymbolKind.FUNCTION,
                        declaration_node=decl,
                        module_path=module_path,
                        location=decl.location
                    )
                    table.locals[decl.id] = sym
                    table.exports[decl.id] = sym

            elif isinstance(stmt, ExportNamedDecl):
                for spec in stmt.specifiers:
                    if spec.local not in table.locals:
                        # Wait until all declarations are parsed? Or deferred check
                        pass

            elif isinstance(stmt, VarDecl):
                for v in stmt.declarations:
                    if v.id in table.locals:
                        raise CompilerDiagnosticError(Diagnostic(
                            message=f"Duplicate identifier '{v.id}' in module '{module_path}'",
                            severity=DiagnosticSeverity.ERROR,
                            location=v.location
                        ))
                    sym = Symbol(
                        name=v.id,
                        kind=SymbolKind.VARIABLE,
                        declaration_node=stmt,
                        module_path=module_path,
                        location=v.location
                    )
                    table.locals[v.id] = sym

            elif isinstance(stmt, FunctionDecl):
                if stmt.id in table.locals:
                    raise CompilerDiagnosticError(Diagnostic(
                        message=f"Duplicate identifier '{stmt.id}' in module '{module_path}'",
                        severity=DiagnosticSeverity.ERROR,
                        location=stmt.location
                    ))
                sym = Symbol(
                    name=stmt.id,
                    kind=SymbolKind.FUNCTION,
                    declaration_node=stmt,
                    module_path=module_path,
                    location=stmt.location
                )
                table.locals[stmt.id] = sym

            else:
                table.top_level_statements.append(stmt)

        # Second pass for ExportNamedDecl to map local to exported
        for stmt in program.body:
            if isinstance(stmt, ExportNamedDecl):
                for spec in stmt.specifiers:
                    if spec.local not in table.locals:
                        raise CompilerDiagnosticError(Diagnostic(
                            message=f"Cannot export undeclared identifier '{spec.local}' in module '{module_path}'",
                            severity=DiagnosticSeverity.ERROR,
                            location=spec.location,
                            suggestion=f"Declare '{spec.local}' before exporting it"
                        ))
                    table.exports[spec.exported] = table.locals[spec.local]

        return table
