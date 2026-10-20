import pytest
from prune.parser import Parser
from prune.optimizer import CSEPass, OptimizationEvent
from prune.ast_nodes import FunctionDecl, VarDecl, Identifier, BinaryExpr


def test_cse_replaces_duplicate_pure_expression():
    source = """
    function compute(x, y) {
        const a = x * y;
        const b = x * y;
        return a + b;
    }
    """
    prog = Parser.from_source(source).parse()
    events = []
    opt_prog = CSEPass(events, "test.prune").run(prog)

    fn = opt_prog.body[0]
    assert isinstance(fn, FunctionDecl)
    body_stmts = fn.body.body

    # const a = x * y;
    stmt1 = body_stmts[0]
    assert isinstance(stmt1, VarDecl)
    assert isinstance(stmt1.declarations[0].init, BinaryExpr)

    # const b = a; (reused!)
    stmt2 = body_stmts[1]
    assert isinstance(stmt2, VarDecl)
    init2 = stmt2.declarations[0].init
    assert isinstance(init2, Identifier)
    assert init2.name == "a"

    assert len(events) == 1
    assert events[0].event_type == "cse"
    assert events[0].symbol == "b"


def test_cse_does_not_replace_when_operand_reassigned():
    source = """
    function compute(x, y) {
        const a = x * y;
        x = 99;
        const b = x * y;
        return a + b;
    }
    """
    prog = Parser.from_source(source).parse()
    events = []
    opt_prog = CSEPass(events, "test.prune").run(prog)

    fn = opt_prog.body[0]
    body_stmts = fn.body.body

    # const b should NOT be replaced by a because x was reassigned
    stmt3 = body_stmts[2]
    assert isinstance(stmt3, VarDecl)
    init3 = stmt3.declarations[0].init
    assert isinstance(init3, BinaryExpr)
    assert len(events) == 0
