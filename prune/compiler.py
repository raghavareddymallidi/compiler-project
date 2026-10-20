from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from prune.lexer import Lexer
from prune.parser import Parser
from prune.ast_nodes import Program
from prune.symbols import SymbolResolver, ModuleSymbolTable
from prune.graph import DependencyGraph
from prune.optimizer import OptimizationPipeline, OptimizationEvent
from prune.codegen import CodeGenerator
from prune.diagnostics import Diagnostic, DiagnosticCollector, CompilerDiagnosticError, DiagnosticSeverity, SourceLocation


@dataclass
class CompilationStats:
    total_modules: int = 0
    total_exports: int = 0
    reachable_exports: int = 0
    removed_exports: int = 0
    optimization_events_count: int = 0
    side_effect_warnings_count: int = 0
    cycles_count: int = 0
    source_bytes: int = 0
    bundle_bytes: int = 0
    reduction_percentage: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_modules": self.total_modules,
            "total_exports": self.total_exports,
            "reachable_exports": self.reachable_exports,
            "removed_exports": self.removed_exports,
            "optimization_events_count": self.optimization_events_count,
            "side_effect_warnings_count": self.side_effect_warnings_count,
            "cycles_count": self.cycles_count,
            "source_bytes": self.source_bytes,
            "bundle_bytes": self.bundle_bytes,
            "reduction_percentage": round(self.reduction_percentage, 2),
        }


@dataclass
class CompilationResult:
    success: bool
    bundle: str = ""
    entry_point: str = ""
    optimization_level: str = "O1"
    graph: Optional[dict] = None
    events: List[dict] = field(default_factory=list)
    diagnostics: List[dict] = field(default_factory=list)
    stats: Optional[dict] = None
    modules: Dict[str, str] = field(default_factory=dict)  # path -> original source code

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "bundle": self.bundle,
            "entry_point": self.entry_point,
            "optimization_level": self.optimization_level,
            "graph": self.graph,
            "events": self.events,
            "diagnostics": self.diagnostics,
            "stats": self.stats,
            "modules": self.modules,
        }


class Compiler:
    """Unified Prune Compiler Engine used by CLI, FastAPI backend, and tests."""

    def __init__(self, level: str = "O1"):
        self.level = level.upper()
        self.collector = DiagnosticCollector()

    def compile_virtual(self, files: Dict[str, str], entry_points: List[str]) -> CompilationResult:
        """Compiles an in-memory dictionary of files (path -> content)."""
        if not entry_points:
            diag = Diagnostic(
                message="No entry point specified for compilation",
                severity=DiagnosticSeverity.ERROR,
                suggestion="Specify at least one entry point file (e.g. 'main.prune')"
            )
            return CompilationResult(
                success=False,
                entry_point="",
                optimization_level=self.level,
                diagnostics=[diag.to_dict()],
                modules=files
            )

        # Total original source bytes
        source_bytes = sum(len(content.encode("utf-8")) for content in files.values())

        # Step 1: Lex and Parse all modules
        parsed_modules: Dict[str, Program] = {}
        for path, content in files.items():
            try:
                parser = Parser.from_source(content, filename=path)
                parsed_modules[path] = parser.parse()
            except CompilerDiagnosticError as e:
                self.collector.add(e.diagnostic)
                return CompilationResult(
                    success=False,
                    entry_point=entry_points[0],
                    optimization_level=self.level,
                    diagnostics=self.collector.to_list(),
                    modules=files
                )

        # Step 2: Validate entry points exist
        for ep in entry_points:
            if ep not in parsed_modules:
                diag = Diagnostic(
                    message=f"Entry point '{ep}' not found among project files",
                    severity=DiagnosticSeverity.ERROR,
                    suggestion=f"Available files: {', '.join(files.keys())}"
                )
                self.collector.add(diag)
                return CompilationResult(
                    success=False,
                    entry_point=ep,
                    optimization_level=self.level,
                    diagnostics=self.collector.to_list(),
                    modules=files
                )

        # Step 3: Module & Symbol Resolution
        resolver = SymbolResolver(parsed_modules)
        try:
            tables = resolver.resolve()
        except CompilerDiagnosticError as e:
            self.collector.add(e.diagnostic)
            return CompilationResult(
                success=False,
                entry_point=entry_points[0],
                optimization_level=self.level,
                diagnostics=self.collector.to_list(),
                modules=files
            )

        # Step 4: Per-Export Dependency Graph & Cycle Detection & Reachability
        graph = DependencyGraph.build(tables, entry_paths=entry_points, resolver=resolver)

        # Step 5: Optimization Passes (O0 / O1 / O2)
        pipeline = OptimizationPipeline(level=self.level)
        optimized_modules, events = pipeline.run(parsed_modules, tables, graph)

        # Step 6: Code Generation & Bundling
        codegen = CodeGenerator(
            entry_paths=entry_points,
            tables=tables,
            resolver=resolver,
            graph=graph
        )
        bundle = codegen.generate(optimized_modules)
        bundle_bytes = len(bundle.encode("utf-8"))

        # Step 7: Compute Statistics
        total_exports = len(graph.nodes)
        reachable_exports = sum(1 for n in graph.nodes.values() if n.is_reachable)
        removed_exports = total_exports - reachable_exports

        reduction_pct = 0.0
        if source_bytes > 0:
            reduction_pct = max(0.0, (1.0 - (bundle_bytes / source_bytes)) * 100.0)

        side_effect_count = sum(1 for e in events if e.event_type == "side_effect_retained")
        cycles_count = len(graph.cycles)

        stats = CompilationStats(
            total_modules=len(files),
            total_exports=total_exports,
            reachable_exports=reachable_exports,
            removed_exports=removed_exports,
            optimization_events_count=len(events),
            side_effect_warnings_count=side_effect_count,
            cycles_count=cycles_count,
            source_bytes=source_bytes,
            bundle_bytes=bundle_bytes,
            reduction_percentage=reduction_pct
        )

        return CompilationResult(
            success=True,
            bundle=bundle,
            entry_point=entry_points[0],
            optimization_level=self.level,
            graph=graph.to_react_flow(),
            events=[e.to_dict() for e in events],
            diagnostics=self.collector.to_list(),
            stats=stats.to_dict(),
            modules=files
        )

    def compile_filesystem(self, entry_paths: List[str]) -> CompilationResult:
        """Reads files from filesystem starting from entry path(s) and compiles."""
        files: Dict[str, str] = {}
        visited_paths: Set[str] = set()
        to_visit = list(entry_paths)

        while to_visit:
            p_str = to_visit.pop(0)
            p = Path(p_str)
            if not p.exists():
                diag = Diagnostic(
                    message=f"File not found: '{p_str}'",
                    severity=DiagnosticSeverity.ERROR,
                    suggestion="Verify the file path exists"
                )
                self.collector.add(diag)
                return CompilationResult(
                    success=False,
                    entry_point=entry_paths[0] if entry_paths else "",
                    optimization_level=self.level,
                    diagnostics=self.collector.to_list()
                )

            norm_key = p.as_posix()
            if norm_key in visited_paths:
                continue

            visited_paths.add(norm_key)
            try:
                content = p.read_text(encoding="utf-8")
                files[norm_key] = content
            except Exception as e:
                diag = Diagnostic(
                    message=f"Could not read file '{p_str}': {e}",
                    severity=DiagnosticSeverity.ERROR
                )
                self.collector.add(diag)
                return CompilationResult(
                    success=False,
                    entry_point=entry_paths[0],
                    optimization_level=self.level,
                    diagnostics=self.collector.to_list()
                )

            # Discover relative imports in this file to load dependencies
            try:
                tokens = Lexer(content, filename=norm_key).tokenize()
                parser = Parser(tokens, source=content, filename=norm_key)
                prog = parser.parse()
                for stmt in prog.body:
                    if stmt.__class__.__name__ == "ImportDecl":
                        imp_source = getattr(stmt, "source")
                        # Resolve path relative to p.parent
                        cand = p.parent / imp_source
                        if not cand.exists():
                            for ext in [".prune", ".js"]:
                                if (p.parent / f"{imp_source}{ext}").exists():
                                    cand = p.parent / f"{imp_source}{ext}"
                                    break
                        to_visit.append(cand.as_posix())
            except Exception:
                # Syntax errors will be captured cleanly in compile_virtual
                pass

        # Normalize entry_paths to match files keys
        norm_entries = [Path(ep).as_posix() for ep in entry_paths]
        return self.compile_virtual(files, norm_entries)
