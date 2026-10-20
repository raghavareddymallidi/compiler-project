import pytest
from prune.parser import Parser
from prune.ast_nodes import (
    Program, ImportDecl, ExportDecl, ExportNamedDecl, VarDecl, FunctionDecl,
    IfStmt, ReturnStmt, BinaryExpr, UnaryExpr, CallExpr, Identifier, NumberLiteral, StringLiteral
)
from prune.diagnostics import CompilerDiagnosticError


def test_parse_import_and_export():
    source = """
    import { add, sub as subtract } from './math.prune';
    export const PI = 3.14;
    export function compute(x) {
        return add(x, PI);
    }
    export { compute as runCompute };
    """
    program = Parser.from_source(source, filename="main.prune").parse()
    assert len(program.body) == 4

    # Import
    imp = program.body[0]
    assert isinstance(imp, ImportDecl)
    assert imp.source == "./math.prune"
    assert len(imp.specifiers) == 2
    assert imp.specifiers[0].imported == "add"
    assert imp.specifiers[0].local == "add"
    assert imp.specifiers[1].imported == "sub"
    assert imp.specifiers[1].local == "subtract"

    # Export const
    exp_var = program.body[1]
    assert isinstance(exp_var, ExportDecl)
    assert isinstance(exp_var.declaration, VarDecl)
    assert exp_var.declaration.declarations[0].id == "PI"

    # Export function
    exp_fn = program.body[2]
    assert isinstance(exp_fn, ExportDecl)
    assert isinstance(exp_fn.declaration, FunctionDecl)
    assert exp_fn.declaration.id == "compute"
    assert exp_fn.declaration.params == ["x"]

    # Export named specifiers
    exp_named = program.body[3]
    assert isinstance(exp_named, ExportNamedDecl)
    assert exp_named.specifiers[0].local == "compute"
    assert exp_named.specifiers[0].exported == "runCompute"


def test_parse_operator_precedence():
    source = "const result = 1 + 2 * 3 == 7 && !false;"
    prog = Parser.from_source(source).parse()
    var_decl = prog.body[0]
    assert isinstance(var_decl, VarDecl)
    init = var_decl.declarations[0].init

    # Root should be &&
    assert isinstance(init, BinaryExpr)
    assert init.operator == "&&"

    # Left of && should be ==
    assert isinstance(init.left, BinaryExpr)
    assert init.left.operator == "=="

    # Left of == should be +
    left_eq = init.left.left
    assert isinstance(left_eq, BinaryExpr)
    assert left_eq.operator == "+"
    assert isinstance(left_eq.left, NumberLiteral)
    assert left_eq.left.value == 1

    # Right of + should be 2 * 3
    assert isinstance(left_eq.right, BinaryExpr)
    assert left_eq.right.operator == "*"

    # Right of && should be !false
    assert isinstance(init.right, UnaryExpr)
    assert init.right.operator == "!"


def test_parse_control_flow():
    source = """
    if (x > 10) {
        return 100;
    } else {
        return 0;
    }
    """
    prog = Parser.from_source(source).parse()
    assert len(prog.body) == 1
    if_stmt = prog.body[0]
    assert isinstance(if_stmt, IfStmt)
    assert isinstance(if_stmt.test, BinaryExpr)
    assert if_stmt.alternate is not None


def test_parse_syntax_error():
    source = "const = 42;"
    with pytest.raises(CompilerDiagnosticError) as exc_info:
        Parser.from_source(source).parse()
    diag = exc_info.value.diagnostic
    assert "Expected variable name" in diag.message
