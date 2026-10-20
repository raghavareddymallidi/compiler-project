import React, { useState } from "react";
import type { OptimizationEvent } from "../types";
import { Filter } from "lucide-react";

interface TraceViewerProps {
  events: OptimizationEvent[];
  onSelectEvent?: (event: OptimizationEvent) => void;
}

export const TraceViewer: React.FC<TraceViewerProps> = ({ events, onSelectEvent }) => {
  const [filterType, setFilterType] = useState<string>("ALL");

  const filteredEvents = events.filter((ev) => {
    if (filterType === "ALL") return true;
    return ev.event_type.toLowerCase() === filterType.toLowerCase();
  });

  if (events.length === 0) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: "var(--text-muted)" }}>
        No optimization events recorded yet. Run compilation to see explainable traces.
      </div>
    );
  }

  const getDecisionBadge = (decision: string) => {
    const style: React.CSSProperties = {
      fontSize: "10px",
      fontWeight: "600",
      padding: "2px 6px",
      borderRadius: "3px",
      textTransform: "uppercase",
    };
    if (decision === "removed") {
      return <span style={{ ...style, background: "#3b1219", color: "#f87171" }}>Removed</span>;
    }
    if (decision === "retained") {
      return <span style={{ ...style, background: "#0a2618", color: "#34d399" }}>Retained</span>;
    }
    if (decision === "transformed") {
      return <span style={{ ...style, background: "#172554", color: "#60a5fa" }}>Folded / CSE</span>;
    }
    return <span style={{ ...style, background: "#3a2503", color: "#fbbf24" }}>Warned</span>;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 8 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, paddingBottom: 4 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 5, color: "var(--text-muted)", fontSize: 11 }}>
          <Filter size={12} />
          <span>Filter:</span>
        </div>
        <select
          className="select-input"
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
        >
          <option value="ALL">All Events ({events.length})</option>
          <option value="dead_code_elimination">Dead Code Elimination</option>
          <option value="constant_folding">Constant Folding</option>
          <option value="cse">Common Subexpression Elimination (CSE)</option>
          <option value="side_effect_retained">Side-Effect Preservation</option>
          <option value="cycle_warning">Cycles & Warnings</option>
        </select>
        <span style={{ fontSize: 11, color: "var(--text-dim)" }}>
          Showing {filteredEvents.length} events
        </span>
      </div>

      <div style={{ flex: 1, overflowY: "auto" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: 130 }}>Type</th>
              <th style={{ width: 90 }}>Decision</th>
              <th style={{ width: 140 }}>Location</th>
              <th>Reason & Transformation</th>
            </tr>
          </thead>
          <tbody>
            {filteredEvents.map((ev, idx) => (
              <tr
                key={idx}
                onClick={() => onSelectEvent && onSelectEvent(ev)}
                style={{ cursor: onSelectEvent ? "pointer" : "default" }}
              >
                <td style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)" }}>
                  {ev.event_type}
                </td>
                <td>{getDecisionBadge(ev.decision)}</td>
                <td style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-dim)" }}>
                  {ev.file}:{ev.line}:{ev.column}
                </td>
                <td>
                  <div>{ev.reason}</div>
                  {ev.original && ev.optimized && (
                    <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginTop: 2 }}>
                      <span style={{ color: "#f87171" }}>{ev.original}</span>
                      {"  →  "}
                      <span style={{ color: "#34d399" }}>{ev.optimized}</span>
                    </div>
                  )}
                  {ev.reachability_path && ev.reachability_path.length > 0 && (
                    <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "#38bdf8", marginTop: 2 }}>
                      Path: {ev.reachability_path.join(" → ")}
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
