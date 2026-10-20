from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import List, Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from prune.compiler import Compiler, CompilationResult


app = typer.Typer(
    name="prune",
    help="Prune — A From-Scratch Compiler, Optimizer & Explainable Bundler",
    no_args_is_help=True
)
console = Console()
error_console = Console(stderr=True)


def handle_compilation_failure(result: CompilationResult) -> None:
    error_console.print("\n[bold red]Compilation Failed:[/bold red]")
    for diag in result.diagnostics:
        code_frame = diag.get("code_frame")
        if code_frame:
            error_console.print(code_frame)
        else:
            loc = diag.get("location")
            loc_str = f"{loc['filename']}:{loc['line']}:{loc['column']}" if loc else "<unknown>"
            error_console.print(f"[{diag['severity'].upper()}] {loc_str}: {diag['message']}")
            if diag.get("suggestion"):
                error_console.print(f"  [dim]hint: {diag['suggestion']}[/dim]")
    sys.exit(1)


@app.command()
def build(
    entry: Optional[str] = typer.Argument(None, help="Primary entry point module file"),
    entries: List[str] = typer.Option([], "--entry", "-e", help="Specify one or more entry points"),
    level: str = typer.Option("O1", "--level", "-l", help="Optimization level: O0, O1, O2"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path for the bundle"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show optimization details")
):
    """Compile and bundle project modules from entry point(s)."""
    all_entries = list(entries)
    if entry and entry not in all_entries:
        all_entries.insert(0, entry)

    if not all_entries:
        error_console.print("[bold red]Error:[/bold red] No entry point specified. Run `prune build --help` for usage.")
        sys.exit(1)

    compiler = Compiler(level=level)
    result = compiler.compile_filesystem(all_entries)

    if not result.success:
        handle_compilation_failure(result)

    # Determine output destination
    out_path = Path(output) if output else Path("dist/bundle.js")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result.bundle, encoding="utf-8")

    stats = result.stats or {}
    console.print(f"[bold green]✓ Build successful![/bold green] Bundle written to: [bold]{out_path}[/bold]")
    console.print(f"  Level: [cyan]{level.upper()}[/cyan] | Modules: [cyan]{stats.get('total_modules', 0)}[/cyan] | "
                  f"Exports: [green]{stats.get('reachable_exports', 0)} retained[/green], [red]{stats.get('removed_exports', 0)} eliminated[/red] | "
                  f"Size: [cyan]{stats.get('bundle_bytes', 0)} bytes[/cyan] (-{stats.get('reduction_percentage', 0)}%)")

    if verbose and result.events:
        table = Table(title="Optimization Events", show_header=True)
        table.add_column("Type", style="cyan")
        table.add_column("Decision", style="magenta")
        table.add_column("Location", style="dim")
        table.add_column("Reason")

        for ev in result.events:
            table.add_row(
                ev["event_type"],
                ev["decision"],
                f"{ev['file']}:{ev['line']}:{ev['column']}",
                ev["reason"]
            )
        console.print(table)


@app.command()
def analyze(
    entry: str = typer.Argument(..., help="Entry point module file"),
    level: str = typer.Option("O1", "--level", "-l", help="Optimization level: O0, O1, O2"),
):
    """Analyze module dependencies, dead exports, and side effects without writing a bundle."""
    compiler = Compiler(level=level)
    result = compiler.compile_filesystem([entry])

    if not result.success:
        handle_compilation_failure(result)

    stats = result.stats or {}
    console.print(Panel(
        f"[bold]Modules analyzed:[/bold] {stats.get('total_modules', 0)}\n"
        f"[bold]Total exports discovered:[/bold] {stats.get('total_exports', 0)}\n"
        f"[bold]Reachable exports:[/bold] [green]{stats.get('reachable_exports', 0)}[/green]\n"
        f"[bold]Eliminated exports:[/bold] [red]{stats.get('removed_exports', 0)}[/red]\n"
        f"[bold]Optimization transformations:[/bold] {stats.get('optimization_events_count', 0)}\n"
        f"[bold]Side-effect warnings:[/bold] {stats.get('side_effect_warnings_count', 0)}\n"
        f"[bold]Cycles detected:[/bold] {stats.get('cycles_count', 0)}",
        title=f"Prune Static Analysis: {entry}"
    ))


@app.command()
def graph(
    entry: str = typer.Argument(..., help="Entry point module file"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text or json"),
):
    """Display the per-export dependency graph."""
    compiler = Compiler(level="O1")
    result = compiler.compile_filesystem([entry])

    if not result.success:
        handle_compilation_failure(result)

    if format.lower() == "json":
        typer.echo(json.dumps(result.graph, indent=2))
        return

    nodes = result.graph.get("nodes", [])
    edges = result.graph.get("edges", [])

    table = Table(title=f"Dependency Graph for {entry}", show_header=True)
    table.add_column("Export Node", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Reachability Path / Explanation")

    for n in nodes:
        d = n["data"]
        status = "[green]LIVE[/green]" if d["is_reachable"] else "[red]DEAD[/red]"
        if d["is_entry"]:
            status += " [bold](ENTRY)[/bold]"
        table.add_row(d["id"], status, d["explanation"])

    console.print(table)


@app.command()
def report(
    entry: str = typer.Argument(..., help="Entry point module file"),
    format: str = typer.Option("text", "--format", "-f", help="Report format: text or json"),
    level: str = typer.Option("O1", "--level", "-l", help="Optimization level: O0, O1, O2"),
):
    """Generate a structured explainability report detailing every compiler optimization."""
    compiler = Compiler(level=level)
    result = compiler.compile_filesystem([entry])

    if not result.success:
        handle_compilation_failure(result)

    if format.lower() == "json":
        output_data = {
            "entry_point": entry,
            "level": level,
            "stats": result.stats,
            "events": result.events,
            "cycles": result.graph.get("cycles", []) if result.graph else [],
        }
        typer.echo(json.dumps(output_data, indent=2))
        return

    console.print(f"[bold cyan]Prune Optimization Report — Entry: {entry} ({level.upper()})[/bold cyan]\n")
    for ev in result.events:
        loc = f"{ev['file']}:{ev['line']}:{ev['column']}"
        console.print(f"• [[bold]{ev['event_type']}[/bold]] ({ev['decision'].upper()}) at {loc}:")
        console.print(f"    {ev['reason']}")
        if ev.get("original") and ev.get("optimized"):
            console.print(f"    [dim]{ev['original']}  ==>  {ev['optimized']}[/dim]")


if __name__ == "__main__":
    app()
