import React from "react";
import type { CompilationStats } from "../types";

interface StatsViewerProps {
  stats?: CompilationStats | null;
}

export const StatsViewer: React.FC<StatsViewerProps> = ({ stats }) => {
  if (!stats) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: "var(--text-muted)" }}>
        No statistics available yet. Run compilation to compute metrics.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-card-title">Size Reduction</div>
          <div className="stat-card-value" style={{ color: "#34d399" }}>
            {stats.reduction_percentage}%
          </div>
          <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 4 }}>
            {stats.source_bytes}B → {stats.bundle_bytes}B
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-title">Reachable Exports</div>
          <div className="stat-card-value" style={{ color: "#38bdf8" }}>
            {stats.reachable_exports} <span style={{ fontSize: 12, color: "var(--text-dim)" }}>/ {stats.total_exports}</span>
          </div>
          <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 4 }}>
            {stats.removed_exports} dead exports pruned
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-title">Transformations</div>
          <div className="stat-card-value" style={{ color: "#a78bfa" }}>
            {stats.optimization_events_count}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 4 }}>
            Constant folds, CSE & DCE passes
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-title">Modules & Cycles</div>
          <div className="stat-card-value" style={{ color: stats.cycles_count > 0 ? "#f87171" : "var(--text-main)" }}>
            {stats.total_modules} <span style={{ fontSize: 12, color: "var(--text-dim)" }}>({stats.cycles_count} cycles)</span>
          </div>
          <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 4 }}>
            {stats.side_effect_warnings_count} side effects observed
          </div>
        </div>
      </div>

      <table className="data-table" style={{ marginTop: 8 }}>
        <thead>
          <tr>
            <th>Metric</th>
            <th>Value</th>
            <th>Explanation</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style={{ fontWeight: 500 }}>Total Source Size</td>
            <td style={{ fontFamily: "var(--font-mono)" }}>{stats.source_bytes} bytes</td>
            <td style={{ color: "var(--text-muted)" }}>Sum of raw UTF-8 bytes of all input modules</td>
          </tr>
          <tr>
            <td style={{ fontWeight: 500 }}>Generated Bundle Size</td>
            <td style={{ fontFamily: "var(--font-mono)" }}>{stats.bundle_bytes} bytes</td>
            <td style={{ color: "var(--text-muted)" }}>Size of optimized, topologically-sorted JS bundle</td>
          </tr>
          <tr>
            <td style={{ fontWeight: 500 }}>Export Retention Ratio</td>
            <td style={{ fontFamily: "var(--font-mono)" }}>
              {stats.total_exports > 0 ? Math.round((stats.reachable_exports / stats.total_exports) * 100) : 0}%
            </td>
            <td style={{ color: "var(--text-muted)" }}>Percentage of discovered export symbols retained as live</td>
          </tr>
          <tr>
            <td style={{ fontWeight: 500 }}>Observable Side Effects</td>
            <td style={{ fontFamily: "var(--font-mono)" }}>{stats.side_effect_warnings_count}</td>
            <td style={{ color: "var(--text-muted)" }}>Top-level statements with observable side effects preserved in output</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};
