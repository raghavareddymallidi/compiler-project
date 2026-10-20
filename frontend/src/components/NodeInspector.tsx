import React from "react";
import type { GraphNodeData } from "../types";
import { X, Route, Info } from "lucide-react";

interface NodeInspectorProps {
  selectedNode: GraphNodeData | null;
  onClose: () => void;
}

export const NodeInspector: React.FC<NodeInspectorProps> = ({ selectedNode, onClose }) => {
  if (!selectedNode) {
    return (
      <aside className="right-inspector">
        <div className="inspector-header">
          <span>Inspector</span>
        </div>
        <div className="inspector-body" style={{ color: "var(--text-dim)", textAlign: "center", paddingTop: 40 }}>
          <Info size={24} style={{ margin: "0 auto 8px auto", opacity: 0.5 }} />
          <div>Select any export node in the graph to inspect its reachability provenance and compiler decision.</div>
        </div>
      </aside>
    );
  }

  let statusColor = "#34d399";
  let statusText = "LIVE (Reachable)";
  if (selectedNode.is_entry) {
    statusColor = "#38bdf8";
    statusText = "ENTRY POINT";
  } else if (selectedNode.is_side_effect) {
    statusColor = "#fbbf24";
    statusText = "SIDE EFFECT (Preserved)";
  } else if (!selectedNode.is_reachable) {
    statusColor = "#f87171";
    statusText = "DEAD (Eliminated)";
  }

  return (
    <aside className="right-inspector">
      <div className="inspector-header">
        <span>Node Details</span>
        <button
          onClick={onClose}
          style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
        >
          <X size={14} />
        </button>
      </div>

      <div className="inspector-body">
        <div className="detail-row">
          <div className="detail-label">Symbol Name</div>
          <div className="detail-val" style={{ fontWeight: 600, color: "#fff" }}>
            {selectedNode.symbol}
          </div>
        </div>

        <div className="detail-row">
          <div className="detail-label">Module Path</div>
          <div className="detail-val">{selectedNode.module}</div>
        </div>

        <div className="detail-row">
          <div className="detail-label">Reachability Status</div>
          <div className="detail-val" style={{ color: statusColor, fontWeight: 600 }}>
            {statusText}
          </div>
        </div>

        <div className="detail-row">
          <div className="detail-label">Compiler Explanation</div>
          <div
            className="detail-val"
            style={{ fontSize: 11, lineHeight: 1.5, background: "#1a1a20", whiteSpace: "pre-wrap" }}
          >
            {selectedNode.explanation}
          </div>
        </div>

        {selectedNode.path && selectedNode.path.length > 0 && (
          <div className="detail-row">
            <div className="detail-label" style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <Route size={12} />
              <span>Reachability Path</span>
            </div>
            <div className="detail-val" style={{ fontSize: 11 }}>
              {selectedNode.path.map((step, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 4, margin: "2px 0" }}>
                  <span style={{ color: "var(--text-dim)" }}>{i + 1}.</span>
                  <span style={{ color: i === 0 ? "#38bdf8" : i === selectedNode.path.length - 1 ? "#34d399" : "var(--text-main)" }}>
                    {step}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {selectedNode.location && (
          <div className="detail-row">
            <div className="detail-label">Source Location</div>
            <div className="detail-val" style={{ fontSize: 11 }}>
              Line {selectedNode.location.line}, Column {selectedNode.location.column}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
