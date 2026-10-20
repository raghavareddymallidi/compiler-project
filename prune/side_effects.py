from __future__ import annotations
from enum import Enum
from typing import Optional, List
from prune.ast_nodes import (
    ASTNode, Statement, Expression, VarDecl, FunctionDecl,
    ExprStmt, ReturnStmt, IfStmt, BlockStmt,
    CallExpr, AssignmentExpr, BinaryExpr, UnaryExpr,
    Identifier, NumberLiteral, StringLiteral, BooleanLiteral, NullLiteral
)
from prune.diagnostics import SourceLocation


class Purity(Enum):
    PURE = "pure"
    POTENTIALLY_IMPURE = "potentially_impure"
    UNKNOWN = "unknown"


def is_expression_pure(expr: Optional[Expression]) -> bool:
    """Conservatively check if an expression has no observable side effects."""
    if expr is None:
        return True

    if isinstance(expr, (NumberLiteral, StringLiteral, BooleanLiteral, NullLiteral, Identifier)):
        return True

    if isinstance(expr, UnaryExpr):
        return is_expression_pure(expr.argument)

    if isinstance(expr, BinaryExpr):
        return is_expression_pure(expr.left) and is_expression_pure(expr.right)

    # Any function call or assignment is potentially impure
    if isinstance(expr, (CallExpr, AssignmentExpr)):
        return False

    return False


def classify_statement(stmt: Statement) -> Purity:
    """Classifies a top-level statement's purity for module initialization."""
    if isinstance(stmt, FunctionDecl):
        # A function declaration by itself is pure until executed!
        return Purity.PURE

    if isinstance(stmt, VarDecl):
        # Pure if all initializers are pure expressions
        for decl in stmt.declarations:
            if decl.init and not is_expression_pure(decl.init):
                return Purity.POTENTIALLY_IMPURE
        return Purity.PURE

    if isinstance(stmt, ExprStmt):
        # Expression statement at top level (e.g., function call or mutation)
        if is_expression_pure(stmt.expression):
            return Purity.PURE
        return Purity.POTENTIALLY_IMPURE

    if isinstance(stmt, IfStmt):
        # If statements might execute side effects
        return Purity.POTENTIALLY_IMPURE

    if isinstance(stmt, BlockStmt):
        for s in stmt.body:
            if classify_statement(s) != Purity.PURE:
                return Purity.POTENTIALLY_IMPURE
        return Purity.PURE

    return Purity.UNKNOWN
