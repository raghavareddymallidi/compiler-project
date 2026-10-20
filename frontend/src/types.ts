export interface SourceLocation {
  filename: string;
  line: number;
  column: number;
  start_offset: number;
  end_offset: number;
}

export interface Diagnostic {
  message: string;
  severity: "error" | "warning" | "info";
  location?: SourceLocation | null;
  rule?: string | null;
  suggestion?: string | null;
  code_frame?: string | null;
}

export interface OptimizationEvent {
  event_type: "constant_folding" | "dead_code_elimination" | "cse" | "side_effect_retained" | "cycle_warning";
  file: string;
  line: number;
  column: number;
  symbol?: string | null;
  original: string;
  optimized: string;
  decision: "transformed" | "removed" | "retained" | "warned";
  reason: string;
  reachability_path?: string[] | null;
}

export interface GraphNodeData {
  id: string;
  label: string;
  module: string;
  symbol: string;
  status: "reachable" | "unreachable" | "entry" | "side_effect";
  is_reachable: boolean;
  is_entry: boolean;
  is_side_effect: boolean;
  explanation: string;
  path: string[];
  location?: SourceLocation | null;
}

export interface ReactFlowNode {
  id: string;
  type: string;
  data: GraphNodeData;
  position: { x: number; y: number };
}

export interface ReactFlowEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  animated?: boolean;
}

export interface DependencyGraphData {
  nodes: ReactFlowNode[];
  edges: ReactFlowEdge[];
  cycles: string[][];
  total_exports: number;
  reachable_exports: number;
  removed_exports: number;
}

export interface CompilationStats {
  total_modules: number;
  total_exports: number;
  reachable_exports: number;
  removed_exports: number;
  optimization_events_count: number;
  side_effect_warnings_count: number;
  cycles_count: number;
  source_bytes: number;
  bundle_bytes: number;
  reduction_percentage: number;
}

export interface CompilationResult {
  success: boolean;
  bundle: string;
  entry_point: string;
  optimization_level: string;
  graph?: DependencyGraphData | null;
  events: OptimizationEvent[];
  diagnostics: Diagnostic[];
  stats?: CompilationStats | null;
  modules: Record<string, string>;
}

export interface SampleProject {
  name: string;
  description: string;
  entry_points: string[];
  files: Record<string, string>;
}
