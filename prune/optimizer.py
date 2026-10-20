from __future__ import annotations
import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from prune.ast_nodes import (
    ASTNode, Program, Statement, Expression, ImportDecl, ImportSpecifier,
    ExportDecl, ExportNamedDecl, ExportSpecifier, VarDecl, VariableDeclarator,
    FunctionDecl, IfStmt, ReturnStmt, BlockStmt, ExprStmt,
    AssignmentExpr, BinaryExpr, UnaryExpr, CallExpr,
    Identifier, NumberLiteral, StringLiteral, BooleanLiteral, NullLiteral
)
from prune.diagnostics import SourceLocation
from prune.graph import DependencyGraph, ExportNode
from prune.side_effects import classify_statement, is_expression_pure, Purity
from prune.symbols import ModuleSymbolTable, extract_referenced_identifiers


@dataclass
class OptimizationEvent:
    event_type: str  # "constant_folding" | "dead_code_elimination" | "cse" | "side_effect_retained" | "cycle_warning"
    file: str
    line: int
    column: int
    symbol: Optional[str] = None
    original: str = ""
    optimized: str = ""
    decision: str = ""  # "transformed" | "removed" | "retained" | "warned"
    reason: str = ""
    reachability_path: Optional[List[str]] = None

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "symbol": self.symbol,
            "original": self.original,
            "optimized": self.optimized,
            "decision": self.decision,
            "reason": self.reason,
            "reachability_path": self.reachability_path,
        }


# -------------------------------------------------------------
# Constant Folding Pass
# -------------------------------------------------------------

class ConstantFoldingPass:
    """Folds arithmetic, comparison, and logical expressions with constant operands."""

    def __init__(self, events: List[OptimizationEvent], filename: str):
        self.events = events
        self.filename = filename

    def run(self, program: Program) -> Program:
        new_body = [self._fold_statement(stmt) for stmt in program.body]
        return Program(location=program.location, body=new_body)

    def _fold_statement(self, stmt: Statement) -> Statement:
        if isinstance(stmt, VarDecl):
            new_decls = []
            for d in stmt.declarations:
                new_init = self._fold_expression(d.init) if d.init else None
                new_decls.append(VariableDeclarator(location=d.location, id=d.id, init=new_init))
            return VarDecl(location=stmt.location, kind=stmt.kind, declarations=new_decls)

        elif isinstance(stmt, ExportDecl):
            inner = self._fold_statement(stmt.declaration)
            return ExportDecl(location=stmt.location, declaration=inner)

        elif isinstance(stmt, FunctionDecl):
            new_body = self._fold_statement(stmt.body)
            assert isinstance(new_body, BlockStmt)
            return FunctionDecl(location=stmt.location, id=stmt.id, params=stmt.params, body=new_body)

        elif isinstance(stmt, BlockStmt):
            new_body = [self._fold_statement(s) for s in stmt.body]
            return BlockStmt(location=stmt.location, body=new_body)

        elif isinstance(stmt, ReturnStmt):
            new_arg = self._fold_expression(stmt.argument) if stmt.argument else None
            return ReturnStmt(location=stmt.location, argument=new_arg)

        elif isinstance(stmt, IfStmt):
            new_test = self._fold_expression(stmt.test)
            new_cons = self._fold_statement(stmt.consequent)
            new_alt = self._fold_statement(stmt.alternate) if stmt.alternate else None
            return IfStmt(location=stmt.location, test=new_test, consequent=new_cons, alternate=new_alt)

        elif isinstance(stmt, ExprStmt):
            new_expr = self._fold_expression(stmt.expression)
            return ExprStmt(location=stmt.location, expression=new_expr)

        return stmt

    def _fold_expression(self, expr: Expression) -> Expression:
        if isinstance(expr, UnaryExpr):
            arg = self._fold_expression(expr.argument)
            # Fold unary
            if expr.operator == "!":
                if isinstance(arg, BooleanLiteral):
                    res = not arg.value
                    self.events.append(OptimizationEvent(
                        event_type="constant_folding",
                        file=self.filename,
                        line=expr.location.line,
                        column=expr.location.column,
                        original=f"!{arg.value}",
                        optimized=str(res).lower(),
                        decision="transformed",
                        reason="Folded unary NOT expression on constant boolean"
                    ))
                    return BooleanLiteral(location=expr.location, value=res)
            elif expr.operator == "-":
                if isinstance(arg, NumberLiteral):
                    res = -arg.value
                    self.events.append(OptimizationEvent(
                        event_type="constant_folding",
                        file=self.filename,
                        line=expr.location.line,
                        column=expr.location.column,
                        original=f"-{arg.value}",
                        optimized=str(res),
                        decision="transformed",
                        reason="Folded unary negation on constant number"
                    ))
                    return NumberLiteral(location=expr.location, value=res, raw=str(res))
            elif expr.operator == "+":
                if isinstance(arg, NumberLiteral):
                    return arg
            return UnaryExpr(location=expr.location, operator=expr.operator, argument=arg, prefix=expr.prefix)

        elif isinstance(expr, BinaryExpr):
            left = self._fold_expression(expr.left)
            right = self._fold_expression(expr.right)
            folded = self._try_fold_binary(expr.operator, left, right, expr.location)
            if folded:
                return folded
            return BinaryExpr(location=expr.location, operator=expr.operator, left=left, right=right)

        elif isinstance(expr, CallExpr):
            new_callee = self._fold_expression(expr.callee)
            new_args = [self._fold_expression(a) for a in expr.arguments]
            return CallExpr(location=expr.location, callee=new_callee, arguments=new_args)

        elif isinstance(expr, AssignmentExpr):
            new_right = self._fold_expression(expr.right)
            return AssignmentExpr(location=expr.location, left=expr.left, right=new_right)

        return expr

    def _try_fold_binary(self, op: str, left: Expression, right: Expression, loc: SourceLocation) -> Optional[Expression]:
        # Numeric operations
        if isinstance(left, NumberLiteral) and isinstance(right, NumberLiteral):
            lval = left.value
            rval = right.value

            if op == "+":
                val = lval + rval
            elif op == "-":
                val = lval - rval
            elif op == "*":
                val = lval * rval
            elif op == "/":
                if rval == 0:
                    # Division by zero: DO NOT fold, preserve expression safely!
                    return None
                val = lval / rval
                # If integer division without remainder, keep int
                if isinstance(val, float) and val.is_integer():
                    val = int(val)
            elif op == "%":
                if rval == 0:
                    return None
                val = lval % rval
            elif op == "==":
                return BooleanLiteral(location=loc, value=(lval == rval))
            elif op == "!=":
                return BooleanLiteral(location=loc, value=(lval != rval))
            elif op == "<":
                return BooleanLiteral(location=loc, value=(lval < rval))
            elif op == "<=":
                return BooleanLiteral(location=loc, value=(lval <= rval))
            elif op == ">":
                return BooleanLiteral(location=loc, value=(lval > rval))
            elif op == ">=":
                return BooleanLiteral(location=loc, value=(lval >= rval))
            else:
                return None

            raw_str = str(val)
            self.events.append(OptimizationEvent(
                event_type="constant_folding",
                file=self.filename,
                line=loc.line,
                column=loc.column,
                original=f"{left.raw} {op} {right.raw}",
                optimized=raw_str,
                decision="transformed",
                reason=f"Folded binary arithmetic expression ({left.raw} {op} {right.raw}) into literal {raw_str}"
            ))
            return NumberLiteral(location=loc, value=val, raw=raw_str)

        # String concatenation: "a" + "b"
        if isinstance(left, StringLiteral) and isinstance(right, StringLiteral) and op == "+":
            val = left.value + right.value
            self.events.append(OptimizationEvent(
                event_type="constant_folding",
                file=self.filename,
                line=loc.line,
                column=loc.column,
                original=f'"{left.value}" + "{right.value}"',
                optimized=f'"{val}"',
                decision="transformed",
                reason=f"Folded string concatenation into literal"
            ))
            return StringLiteral(location=loc, value=val)

        # Boolean operations
        if isinstance(left, BooleanLiteral) and isinstance(right, BooleanLiteral):
            if op == "&&":
                bval = left.value and right.value
            elif op == "||":
                bval = left.value or right.value
            elif op == "==":
                bval = left.value == right.value
            elif op == "!=":
                bval = left.value != right.value
            else:
                return None
            return BooleanLiteral(location=loc, value=bval)

        return None


# -------------------------------------------------------------
# Common Subexpression Elimination (CSE)
# -------------------------------------------------------------

def expr_to_key(expr: Expression) -> Optional[str]:
    """Generates a structural key for pure expressions eligible for CSE."""
    if not is_expression_pure(expr):
        return None
    if isinstance(expr, BinaryExpr):
        lkey = expr_to_key(expr.left)
        rkey = expr_to_key(expr.right)
        if lkey and rkey:
            return f"({lkey} {expr.operator} {rkey})"
    elif isinstance(expr, Identifier):
        return expr.name
    elif isinstance(expr, NumberLiteral):
        return f"NUM:{expr.value}"
    elif isinstance(expr, StringLiteral):
        return f"STR:{expr.value}"
    return None


class CSEPass:
    """Conservative Common Subexpression Elimination for pure expressions within functions."""

    def __init__(self, events: List[OptimizationEvent], filename: str):
        self.events = events
        self.filename = filename

    def run(self, program: Program) -> Program:
        new_body = [self._transform_statement(stmt) for stmt in program.body]
        return Program(location=program.location, body=new_body)

    def _transform_statement(self, stmt: Statement) -> Statement:
        if isinstance(stmt, ExportDecl):
            inner = self._transform_statement(stmt.declaration)
            return ExportDecl(location=stmt.location, declaration=inner)

        elif isinstance(stmt, FunctionDecl):
            new_block = self._optimize_block(stmt.body)
            return FunctionDecl(location=stmt.location, id=stmt.id, params=stmt.params, body=new_block)

        return stmt

    def _optimize_block(self, block: BlockStmt) -> BlockStmt:
        # Straightforward CSE within straight-line function body statements
        seen_exprs: Dict[str, str] = {}  # expr_key -> variable_name holding the value
        new_stmts: List[Statement] = []

        for stmt in block.body:
            if isinstance(stmt, VarDecl):
                new_decls = []
                for d in stmt.declarations:
                    if d.init and isinstance(d.init, BinaryExpr):
                        key = expr_to_key(d.init)
                        if key and key in seen_exprs:
                            # Subexpression already computed in previous variable!
                            prev_var = seen_exprs[key]
                            new_init = Identifier(location=d.init.location, name=prev_var)
                            self.events.append(OptimizationEvent(
                                event_type="cse",
                                file=self.filename,
                                line=d.location.line,
                                column=d.location.column,
                                symbol=d.id,
                                original=key,
                                optimized=prev_var,
                                decision="transformed",
                                reason=f"Eliminated common subexpression '{key}', reused existing value from variable '{prev_var}'"
                            ))
                            new_decls.append(VariableDeclarator(location=d.location, id=d.id, init=new_init))
                            continue
                        elif key:
                            seen_exprs[key] = d.id

                    new_decls.append(d)
                new_stmts.append(VarDecl(location=stmt.location, kind=stmt.kind, declarations=new_decls))

            elif isinstance(stmt, ExprStmt) and isinstance(stmt.expression, AssignmentExpr):
                # Variable reassignment invalidates subexpressions containing that variable!
                assigned_var = stmt.expression.left
                keys_to_remove = [k for k in seen_exprs if assigned_var in k]
                for k in keys_to_remove:
                    del seen_exprs[k]
                new_stmts.append(stmt)
            else:
                new_stmts.append(stmt)

        return BlockStmt(location=block.location, body=new_stmts)


# -------------------------------------------------------------
# Dead Code Elimination Pass
# -------------------------------------------------------------

class DeadCodeEliminationPass:
    """Eliminates unreachable exports while safely preserving reachable code and side effects."""

    def __init__(self, graph: DependencyGraph, events: List[OptimizationEvent]):
        self.graph = graph
        self.events = events

    def run(self, modules: Dict[str, Program], tables: Dict[str, ModuleSymbolTable]) -> Dict[str, Program]:
        optimized_modules: Dict[str, Program] = {}

        for mod_path, program in modules.items():
            new_body: List[Statement] = []

            for stmt in program.body:
                if isinstance(stmt, ExportDecl):
                    decl = stmt.declaration
                    # Check export reachability
                    export_name = None
                    if isinstance(decl, VarDecl):
                        export_name = decl.declarations[0].id
                    elif isinstance(decl, FunctionDecl):
                        export_name = decl.id

                    node_id = f"{mod_path}:{export_name}" if export_name else None
                    node = self.graph.nodes.get(node_id) if node_id else None

                    if node and not node.is_reachable:
                        # Unreachable export: ELIMINATE
                        self.events.append(OptimizationEvent(
                            event_type="dead_code_elimination",
                            file=mod_path,
                            line=stmt.location.line,
                            column=stmt.location.column,
                            symbol=export_name,
                            original=f"export {export_name}",
                            optimized="",
                            decision="removed",
                            reason=f"Eliminated dead export '{export_name}' (unreachable from entry point)",
                            reachability_path=None
                        ))
                        # Do not add to new_body!
                        continue
                    else:
                        # Reachable export: RETAIN
                        if node:
                            self.events.append(OptimizationEvent(
                                event_type="dead_code_elimination",
                                file=mod_path,
                                line=stmt.location.line,
                                column=stmt.location.column,
                                symbol=export_name,
                                original=f"export {export_name}",
                                optimized=f"export {export_name}",
                                decision="retained",
                                reason=node.explanation,
                                reachability_path=node.reachability_path
                            ))
                        new_body.append(stmt)

                elif isinstance(stmt, ExportNamedDecl):
                    new_specs = []
                    for spec in stmt.specifiers:
                        node_id = f"{mod_path}:{spec.exported}"
                        node = self.graph.nodes.get(node_id)
                        if node and not node.is_reachable:
                            self.events.append(OptimizationEvent(
                                event_type="dead_code_elimination",
                                file=mod_path,
                                line=spec.location.line,
                                column=spec.location.column,
                                symbol=spec.exported,
                                original=f"export {{ {spec.exported} }}",
                                optimized="",
                                decision="removed",
                                reason=f"Eliminated dead export '{spec.exported}'",
                                reachability_path=None
                            ))
                        else:
                            new_specs.append(spec)
                    if new_specs:
                        new_body.append(ExportNamedDecl(location=stmt.location, specifiers=new_specs))

                else:
                    # Check if top-level statement has side effects
                    purity = classify_statement(stmt)
                    if purity != Purity.PURE:
                        self.events.append(OptimizationEvent(
                            event_type="side_effect_retained",
                            file=mod_path,
                            line=stmt.location.line,
                            column=stmt.location.column,
                            original=stmt.__class__.__name__,
                            optimized=stmt.__class__.__name__,
                            decision="retained",
                            reason=f"Preserved top-level statement with potential side effects ({purity.value})"
                        ))
                    new_body.append(stmt)

            optimized_modules[mod_path] = Program(location=program.location, body=new_body)

        return optimized_modules


# -------------------------------------------------------------
# Optimization Pipeline
# -------------------------------------------------------------

class OptimizationPipeline:
    """Coordinates passes according to optimization level (O0, O1, O2)."""

    def __init__(self, level: str = "O1"):
        self.level = level.upper()
        self.events: List[OptimizationEvent] = []

    def run(self, modules: Dict[str, Program], tables: Dict[str, ModuleSymbolTable],
            graph: DependencyGraph) -> Tuple[Dict[str, Program], List[OptimizationEvent]]:

        # Record cycle warnings if any
        if graph.cycles:
            for cycle in graph.cycles:
                cycle_str = " -> ".join(cycle)
                self.events.append(OptimizationEvent(
                    event_type="cycle_warning",
                    file=cycle[0].split(":")[0],
                    line=1,
                    column=1,
                    original=cycle_str,
                    optimized=cycle_str,
                    decision="warned",
                    reason=f"Detected circular dependency cycle: {cycle_str}"
                ))

        if self.level == "O0":
            # Level O0: No dead-code elimination, no constant folding, no CSE.
            return modules, self.events

        # Level O1: Constant Folding + Dead Code Elimination
        current_modules = {}
        for mod_path, prog in modules.items():
            cf_pass = ConstantFoldingPass(self.events, filename=mod_path)
            current_modules[mod_path] = cf_pass.run(prog)

        dce_pass = DeadCodeEliminationPass(graph, self.events)
        current_modules = dce_pass.run(current_modules, tables)

        if self.level == "O2":
            # Level O2: Add CSE pass
            for mod_path, prog in current_modules.items():
                cse_pass = CSEPass(self.events, filename=mod_path)
                current_modules[mod_path] = cse_pass.run(prog)

        return current_modules, self.events
