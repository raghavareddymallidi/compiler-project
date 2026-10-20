import React, { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  Handle,
  Position,
  type NodeProps,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import type { DependencyGraphData, GraphNodeData } from "../types";
import { AlertTriangle } from "lucide-react";

// Custom node component for Prune's export nodes
const CustomExportNode: React.FC<NodeProps<GraphNodeData>> = ({ data, selected }) => {
  let statusClass = "reachable";
  let badgeLabel = "LIVE";
  let badgeClass = "live";

  if (data.is_entry) {
    statusClass = "entry";
    badgeLabel = "ENTRY";
    badgeClass = "entry";
  } else if (data.is_side_effect) {
    statusClass = "side_effect";
    badgeLabel = "SIDE EFFECT";
    badgeClass = "side";
  } else if (!data.is_reachable) {
    statusClass = "unreachable";
    badgeLabel = "DEAD";
    badgeClass = "dead";
  }

  return (
    <div
      className={`custom-graph-node ${statusClass}`}
      style={{
        boxShadow: selected ? "0 0 0 2px #38bdf8" : undefined,
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: "#71717a" }} />
      <div className="node-header">
        <span className="node-symbol">{data.symbol}</span>
        <span className={`node-badge ${badgeClass}`}>{badgeLabel}</span>
      </div>
      <div className="node-mod">{data.module}</div>
      <Handle type="source" position={Position.Right} style={{ background: "#71717a" }} />
    </div>
  );
};

interface DependencyGraphProps {
  graphData?: DependencyGraphData | null;
  onSelectNode: (nodeData: GraphNodeData | null) => void;
}

export const DependencyGraph: React.FC<DependencyGraphProps> = ({
  graphData,
  onSelectNode,
}) => {
  const nodeTypes = useMemo(() => ({ custom: CustomExportNode }), []);

  if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: "var(--text-muted)" }}>
        No dependency graph available. Click <strong>Build & Analyze</strong> to compile and generate graph.
      </div>
    );
  }

  const nodes: Node[] = graphData.nodes.map((n) => ({
    id: n.id,
    type: "custom",
    position: n.position,
    data: n.data,
  }));

  const edges: Edge[] = graphData.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    animated: e.animated,
    style: { stroke: e.animated ? "#fbbf24" : "#52525b", strokeWidth: 1.5 },
    labelStyle: { fill: "#a1a1aa", fontSize: 10, fontFamily: "var(--font-mono)" },
    labelBgStyle: { fill: "#18181b", fillOpacity: 0.8 },
  }));

  const hasCycles = graphData.cycles && graphData.cycles.length > 0;

  return (
    <div style={{ height: "100%", width: "100%", position: "relative" }}>
      {hasCycles && (
        <div
          style={{
            position: "absolute",
            top: 10,
            left: 10,
            zIndex: 10,
            backgroundColor: "#2e1214",
            border: "1px solid #f87171",
            padding: "6px 12px",
            borderRadius: 4,
            fontSize: 11,
            color: "#fca5a5",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <AlertTriangle size={14} color="#f87171" />
          <span>
            <strong>Cycle Detected:</strong> {graphData.cycles.map((c) => c.join(" → ")).join("; ")}
          </span>
        </div>
      )}

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        onNodeClick={(_, node) => onSelectNode(node.data as GraphNodeData)}
        onPaneClick={() => onSelectNode(null)}
      >
        <Background color="#27272a" gap={16} size={1} />
        <Controls />
      </ReactFlow>
    </div>
  );
};
