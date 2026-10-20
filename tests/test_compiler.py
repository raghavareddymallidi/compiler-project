import pytest
from prune.compiler import Compiler


def test_multiple_entry_points():
    files = {
        "shared.prune": """
        export function utilA() { return "A"; }
        export function utilB() { return "B"; }
        export function deadC() { return "C"; }
        """,
        "app.prune": """
        import { utilA } from './shared.prune';
        export function startApp() { return utilA(); }
        """,
        "admin.prune": """
        import { utilB } from './shared.prune';
        export function startAdmin() { return utilB(); }
        """
    }

    compiler = Compiler(level="O1")

    # Entry point 1: app.prune (should only pull utilA, not utilB or deadC)
    res_app = compiler.compile_virtual(files, ["app.prune"])
    assert res_app.success is True
    assert "utilA" in res_app.bundle
    assert "utilB" not in res_app.bundle
    assert "deadC" not in res_app.bundle

    # Entry point 2: admin.prune (should only pull utilB, not utilA or deadC)
    res_admin = compiler.compile_virtual(files, ["admin.prune"])
    assert res_admin.success is True
    assert "utilB" in res_admin.bundle
    assert "utilA" not in res_admin.bundle
    assert "deadC" not in res_admin.bundle


def test_optimization_levels_o0_o1_o2():
    files = {
        "helper.prune": """
        export function usedHelper() { return 1; }
        export function unusedDead() { return 999; }
        """,
        "main.prune": """
        import { usedHelper } from './helper.prune';
        export function testOpt() {
            const folded = 10 + 20 * 2;
            const cse1 = 5 * folded;
            const cse2 = 5 * folded;
            return cse1 + cse2 + usedHelper();
        }
        """
    }

    # O0: Retains unusedDead, does not fold constant
    c_o0 = Compiler(level="O0")
    res_o0 = c_o0.compile_virtual(files, ["main.prune"])
    assert res_o0.success is True
    assert "unusedDead" in res_o0.bundle
    assert "10 + (20 * 2)" in res_o0.bundle or "(10 + (20 * 2))" in res_o0.bundle

    # O1: Eliminates unusedDead, folds constant (50), but no CSE
    c_o1 = Compiler(level="O1")
    res_o1 = c_o1.compile_virtual(files, ["main.prune"])
    assert res_o1.success is True
    assert "unusedDead" not in res_o1.bundle
    assert "50" in res_o1.bundle

    # O2: Eliminates unusedDead, folds constant, and applies CSE!
    c_o2 = Compiler(level="O2")
    res_o2 = c_o2.compile_virtual(files, ["main.prune"])
    assert res_o2.success is True
    cse_events = [e for e in res_o2.events if e["event_type"] == "cse"]
    assert len(cse_events) >= 1


def test_unresolved_import_diagnostic():
    files = {
        "main.prune": "import { missingFn } from './nonexistent.prune';\nexport function x() { return 1; }"
    }
    compiler = Compiler(level="O1")
    res = compiler.compile_virtual(files, ["main.prune"])
    assert res.success is False
    assert any("Cannot resolve module" in d["message"] for d in res.diagnostics)


def test_missing_export_diagnostic():
    files = {
        "math.prune": "export function add(a, b) { return a + b; }",
        "main.prune": "import { multiply } from './math.prune';\nexport function run() { return multiply(2, 3); }"
    }
    compiler = Compiler(level="O1")
    res = compiler.compile_virtual(files, ["main.prune"])
    assert res.success is False
    assert any("has no export named 'multiply'" in d["message"] for d in res.diagnostics)
