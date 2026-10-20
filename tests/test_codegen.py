import subprocess
import pytest
from prune.compiler import Compiler


def test_codegen_bundle_and_execution_with_node():
    files = {
        "math.prune": """
        export function add(a, b) {
            return a + b;
        }
        export function unusedSub(a, b) {
            return a - b;
        }
        """,
        "main.prune": """
        import { add } from './math.prune';
        export function compute(x) {
            const result = add(x, 10 + 20);
            return result;
        }
        """
    }

    compiler = Compiler(level="O1")
    result = compiler.compile_virtual(files, ["main.prune"])

    assert result.success is True
    assert "unusedSub" not in result.bundle
    assert "compute" in result.bundle

    # Execute with Node.js
    node_eval_script = f"""
    {result.bundle}
    const res = module.exports.compute(5);
    console.log("RESULT:" + res);
    """

    proc = subprocess.run(
        ["node", "-e", node_eval_script],
        capture_output=True,
        text=True
    )
    assert proc.returncode == 0
    assert "RESULT:35" in proc.stdout.strip()


def test_codegen_name_collision_handling():
    # Both modules have a local variable named 'helper'
    files = {
        "utils.prune": """
        const helper = 100;
        export function getUtilsVal() {
            return helper;
        }
        """,
        "main.prune": """
        import { getUtilsVal } from './utils.prune';
        const helper = 500;
        export function getTotal() {
            return helper + getUtilsVal();
        }
        """
    }

    compiler = Compiler(level="O1")
    result = compiler.compile_virtual(files, ["main.prune"])
    assert result.success is True

    # Execute with Node.js
    node_eval_script = f"""
    {result.bundle}
    const total = module.exports.getTotal();
    console.log("TOTAL:" + total);
    """

    proc = subprocess.run(
        ["node", "-e", node_eval_script],
        capture_output=True,
        text=True
    )
    assert proc.returncode == 0
    assert "TOTAL:600" in proc.stdout.strip()
