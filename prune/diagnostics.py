from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class DiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class SourceLocation:
    filename: str
    line: int
    column: int
    start_offset: int = 0
    end_offset: int = 0

    def __str__(self) -> str:
        return f"{self.filename}:{self.line}:{self.column}"

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "line": self.line,
            "column": self.column,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
        }


@dataclass
class Diagnostic:
    message: str
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    location: Optional[SourceLocation] = None
    rule: Optional[str] = None
    suggestion: Optional[str] = None
    source_code: Optional[str] = None

    def render_code_frame(self) -> str:
        """Render a readable terminal/text code frame highlighting the error."""
        if not self.location or not self.source_code:
            loc_str = str(self.location) if self.location else "<unknown>"
            return f"[{self.severity.value.upper()}] {loc_str}: {self.message}"

        lines = self.source_code.splitlines()
        target_line_idx = self.location.line - 1
        output_lines = [f"[{self.severity.value.upper()}] {self.location.filename}:{self.location.line}:{self.location.column}: {self.message}"]

        start_line = max(0, target_line_idx - 1)
        end_line = min(len(lines), target_line_idx + 2)

        for idx in range(start_line, end_line):
            lineno = idx + 1
            line_content = lines[idx]
            prefix = f"{lineno:4d} | "
            if idx == target_line_idx:
                output_lines.append(f"> {prefix}{line_content}")
                # Col is 1-indexed
                col_offset = max(0, self.location.column - 1)
                pointer = " " * (len(prefix) + 2 + col_offset) + "^"
                output_lines.append(pointer)
            else:
                output_lines.append(f"  {prefix}{line_content}")

        if self.suggestion:
            output_lines.append(f"  hint: {self.suggestion}")

        return "\n".join(output_lines)

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "severity": self.severity.value,
            "location": self.location.to_dict() if self.location else None,
            "rule": self.rule,
            "suggestion": self.suggestion,
            "code_frame": self.render_code_frame() if self.source_code else None,
        }


class CompilerDiagnosticError(Exception):
    """Raised when compilation fails due to user errors (syntax, resolve, etc.)."""
    def __init__(self, diagnostic: Diagnostic):
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


@dataclass
class DiagnosticCollector:
    diagnostics: List[Diagnostic] = field(default_factory=list)

    def add(self, diagnostic: Diagnostic) -> None:
        self.diagnostics.append(diagnostic)

    def error(self, message: str, location: Optional[SourceLocation] = None,
              source_code: Optional[str] = None, suggestion: Optional[str] = None,
              rule: Optional[str] = None) -> None:
        self.add(Diagnostic(
            message=message,
            severity=DiagnosticSeverity.ERROR,
            location=location,
            source_code=source_code,
            suggestion=suggestion,
            rule=rule
        ))

    def warning(self, message: str, location: Optional[SourceLocation] = None,
                source_code: Optional[str] = None, suggestion: Optional[str] = None,
                rule: Optional[str] = None) -> None:
        self.add(Diagnostic(
            message=message,
            severity=DiagnosticSeverity.WARNING,
            location=location,
            source_code=source_code,
            suggestion=suggestion,
            rule=rule
        ))

    @property
    def has_errors(self) -> bool:
        return any(d.severity == DiagnosticSeverity.ERROR for d in self.diagnostics)

    def to_list(self) -> List[dict]:
        return [d.to_dict() for d in self.diagnostics]
