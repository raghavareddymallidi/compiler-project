import subprocess
import pytest
from prune.compiler import Compiler


def test_end_to_end_representative_project():
    files = {
        "src/main.prune": """
        import { add } from './math.prune';
        import { initTracker, getCounter } from './analytics.prune';

        export function calculateTotal(base) {
            // Constant folding opportunity: 10 * 5 -> 50
            const bonus = 10 * 5;
            // CSE opportunity
            const term1 = base * bonus;
            const term2 = base * bonus;
            return add(term1, term2) + getCounter();
        }
        """,
        "src/math.prune": """
        export function add(a, b) {
            return a + b;
        }

        // Dead export that must be removed
        export function deadPower(a, b) {
            return a * a;
        }
        """,
        "src/analytics.prune": """
        let counter = 0;

        // Top-level side-effect initialization statement
        initTracker();

        export function initTracker() {
            counter = 100;
        }

        export function getCounter() {
            return counter;
        }

        // Dead export
        export function deadMetric() {
            return 404;
        }
        """
    }

    compiler = Compiler(level="O2")
    result = compiler.compile_virtual(files, ["src/main.prune"])

    assert result.success is True
    assert result.bundle != ""

    # Check that dead exports are absent from the bundle
    assert "deadPower" not in result.bundle
    assert "deadMetric" not in result.bundle

    # Check that live exports and side effects are retained
    assert "calculateTotal" in result.bundle
    assert "initTracker" in result.bundle

    # Check stats
    stats = result.stats
    assert stats["total_modules"] == 3
    assert stats["removed_exports"] >= 2
    assert stats["reachable_exports"] >= 3

    # Execute with Node.js
    node_eval_script = f"""
    {result.bundle}
    // base = 2:
    // bonus = 50
    // term1 = 2 * 50 = 100
    // term2 = 100
    // add(100, 100) = 200
    // counter = 100 from initTracker() top-level side effect
    // total = 200 + 100 = 300
    const total = module.exports.calculateTotal(2);
    console.log("FINAL_RESULT:" + total);
    """

    proc = subprocess.run(
        ["node", "-e", node_eval_script],
        capture_output=True,
        text=True
    )
    assert proc.returncode == 0
    assert "FINAL_RESULT:300" in proc.stdout.strip()
