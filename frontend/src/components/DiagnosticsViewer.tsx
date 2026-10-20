import React from "react";
import type { Diagnostic } from "../types";
import { AlertCircle, CheckCircle } from "lucide-react";

interface DiagnosticsViewerProps {
  diagnostics: Diagnostic[];
}

export const DiagnosticsViewer: React.FC<DiagnosticsViewerProps> = ({ diagnostics }) => {
  if (diagnostics.length === 0) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: "#34d399", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
        <CheckCircle size={16} />
        <span>No compiler diagnostics or errors reported. Clean build!</span>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {diagnostics.map((diag, idx) => (
        <div
          key={idx}
          style={{
            backgroundColor: diag.severity === "error" ? "#2e1214" : "#2a220c",
            border: `1px solid ${diag.severity === "error" ? "#7f1d1d" : "#78350f"}`,
            borderRadius: 4,
            padding: 12,
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <AlertCircle size={16} color={diag.severity === "error" ? "#f87171" : "#fbbf24"} />
            <strong style={{ color: diag.severity === "error" ? "#fca5a5" : "#fde68a" }}>
              [{diag.severity.toUpperCase()}]{" "}
              {diag.location ? `${diag.location.filename}:${diag.location.line}:${diag.location.column}` : ""}
            </strong>
            <span style={{ color: "var(--text-main)" }}>— {diag.message}</span>
          </div>

          {diag.suggestion && (
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 24 }}>
              <em>hint:</em> {diag.suggestion}
            </div>
          )}

          {diag.code_frame && (
            <pre className="code-frame" style={{ marginTop: 4 }}>
              {diag.code_frame}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
};
