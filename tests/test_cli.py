import subprocess
import json
import pytest
from typer.testing import CliRunner
from prune.cli import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Prune — A From-Scratch Compiler" in result.stdout
    assert "build" in result.stdout
    assert "analyze" in result.stdout
    assert "graph" in result.stdout
    assert "report" in result.stdout


def test_cli_build_and_report(tmp_path):
    main_file = tmp_path / "main.prune"
    main_file.write_text("""
    export function answer() {
        return 42;
    }
    export function dead() {
        return 0;
    }
    """)

    out_file = tmp_path / "dist" / "bundle.js"

    # Build command
    build_res = runner.invoke(app, ["build", str(main_file), "--output", str(out_file), "--level", "O1"])
    assert build_res.exit_code == 0
    assert out_file.exists()
    bundle_content = out_file.read_text()
    assert "answer" in bundle_content

    # Report command with json
    report_res = runner.invoke(app, ["report", str(main_file), "--format", "json"])
    assert report_res.exit_code == 0
    data = json.loads(report_res.stdout)
    assert data["entry_point"] == str(main_file)
    assert "events" in data

    # Analyze command
    analyze_res = runner.invoke(app, ["analyze", str(main_file)])
    assert analyze_res.exit_code == 0
    assert "Modules analyzed" in analyze_res.stdout


def test_cli_error_exit_code(tmp_path):
    bad_file = tmp_path / "bad.prune"
    bad_file.write_text("const = 100;")

    result = runner.invoke(app, ["build", str(bad_file)])
    assert result.exit_code != 0
