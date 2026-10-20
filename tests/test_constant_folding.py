import pytest
from prune.parser import Parser
from prune.optimizer import ConstantFoldingPass, OptimizationEvent
from prune.ast_nodes import VarDecl, NumberLiteral, BooleanLiteral, BinaryExpr


def test_fold_arithmetic_precedence():
    source = "const result = 10 + 20 * 2;"
    prog = Parser.from_source(source).parse()
    events = []
    folded_prog = ConstantFoldingPass(events, "test.prune").run(prog)

    var_decl = folded_prog.body[0]
    assert isinstance(var_decl, VarDecl)
    init = var_decl.declarations[0].init
    assert isinstance(init, NumberLiteral)
    assert init.value == 50
    assert len(events) >= 1
    assert any(e.optimized == "50" for e in events)


def test_fold_division_by_zero_safety():
    source = "const x = 10 / 0;"
    prog = Parser.from_source(source).parse()
    events = []
    # Should NOT crash and should NOT fold 10 / 0
    folded_prog = ConstantFoldingPass(events, "test.prune").run(prog)

    var_decl = folded_prog.body[0]
    assert isinstance(var_decl, VarDecl)
    init = var_decl.declarations[0].init
    assert isinstance(init, BinaryExpr)
    assert init.operator == "/"


def test_fold_unary_and_boolean():
    source = "const flag = !false; const neg = -42;"
    prog = Parser.from_source(source).parse()
    events = []
    folded_prog = ConstantFoldingPass(events, "test.prune").run(prog)

    d1 = folded_prog.body[0].declarations[0].init
    assert isinstance(d1, BooleanLiteral)
    assert d1.value is True

    d2 = folded_prog.body[1].declarations[0].init
    assert isinstance(d2, NumberLiteral)
    assert d2.value == -42
