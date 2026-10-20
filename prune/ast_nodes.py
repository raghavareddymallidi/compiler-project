from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Union, Any
from prune.diagnostics import SourceLocation


@dataclass
class ASTNode:
    location: SourceLocation

    def to_dict(self) -> dict:
        d = {"type": self.__class__.__name__}
        for k, v in self.__dict__.items():
            if k == "location":
                d["location"] = v.to_dict() if v else None
            elif isinstance(v, ASTNode):
                d[k] = v.to_dict()
            elif isinstance(v, list):
                d[k] = [item.to_dict() if isinstance(item, ASTNode) else item for item in v]
            else:
                d[k] = v
        return d


# -------------------------------------------------------------
# Expressions
# -------------------------------------------------------------

class Expression(ASTNode):
    pass


@dataclass
class Identifier(Expression):
    name: str


@dataclass
class NumberLiteral(Expression):
    value: Union[int, float]
    raw: str


@dataclass
class StringLiteral(Expression):
    value: str


@dataclass
class BooleanLiteral(Expression):
    value: bool


@dataclass
class NullLiteral(Expression):
    pass


@dataclass
class BinaryExpr(Expression):
    operator: str
    left: Expression
    right: Expression


@dataclass
class UnaryExpr(Expression):
    operator: str
    argument: Expression
    prefix: bool = True


@dataclass
class CallExpr(Expression):
    callee: Expression
    arguments: List[Expression] = field(default_factory=list)


@dataclass
class AssignmentExpr(Expression):
    left: str
    right: Expression


# -------------------------------------------------------------
# Statements
# -------------------------------------------------------------

class Statement(ASTNode):
    pass


@dataclass
class ImportSpecifier(ASTNode):
    imported: str
    local: str


@dataclass
class ImportDecl(Statement):
    specifiers: List[ImportSpecifier]
    source: str  # e.g. "./math.prune"


@dataclass
class ExportSpecifier(ASTNode):
    local: str
    exported: str


@dataclass
class ExportNamedDecl(Statement):
    specifiers: List[ExportSpecifier]


@dataclass
class ExportDecl(Statement):
    declaration: Statement  # VarDecl or FunctionDecl


@dataclass
class VariableDeclarator(ASTNode):
    id: str
    init: Optional[Expression] = None


@dataclass
class VarDecl(Statement):
    kind: str  # "const" | "let" | "var"
    declarations: List[VariableDeclarator] = field(default_factory=list)


@dataclass
class BlockStmt(Statement):
    body: List[Statement] = field(default_factory=list)


@dataclass
class FunctionDecl(Statement):
    id: str
    params: List[str]
    body: BlockStmt


@dataclass
class ReturnStmt(Statement):
    argument: Optional[Expression] = None


@dataclass
class IfStmt(Statement):
    test: Expression
    consequent: Statement
    alternate: Optional[Statement] = None


@dataclass
class ExprStmt(Statement):
    expression: Expression


@dataclass
class Program(ASTNode):
    body: List[Statement] = field(default_factory=list)
