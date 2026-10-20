import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatsViewer } from "./components/StatsViewer";
import { DiagnosticsViewer } from "./components/DiagnosticsViewer";
import { NodeInspector } from "./components/NodeInspector";
import type { CompilationStats, Diagnostic, GraphNodeData } from "./types";

describe("StatsViewer Component", () => {
  it("renders size reduction percentage and metric cards accurately", () => {
    const stats: CompilationStats = {
      total_modules: 3,
      total_exports: 5,
      reachable_exports: 3,
      removed_exports: 2,
      optimization_events_count: 7,
      side_effect_warnings_count: 1,
      cycles_count: 0,
      source_bytes: 400,
      bundle_bytes: 250,
      reduction_percentage: 37.5,
    };

    render(<StatsViewer stats={stats} />);
    expect(screen.getByText("37.5%")).toBeDefined();
    expect(screen.getByText("Size Reduction")).toBeDefined();
    expect(screen.getByText("2 dead exports pruned")).toBeDefined();
    expect(screen.getByText("400 bytes")).toBeDefined();
    expect(screen.getByText("250 bytes")).toBeDefined();
  });
});

describe("DiagnosticsViewer Component", () => {
  it("renders diagnostics with code frames and suggestions", () => {
    const diags: Diagnostic[] = [
      {
        message: "Expected variable name",
        severity: "error",
        location: {
          filename: "bad.prune",
          line: 2,
          column: 5,
          start_offset: 20,
          end_offset: 21,
        },
        suggestion: "Specify a valid identifier name",
        code_frame: "  2 | const = 100;\n    |       ^",
      },
    ];

    render(<DiagnosticsViewer diagnostics={diags} />);
    expect(screen.getByText(/Expected variable name/)).toBeDefined();
    expect(screen.getByText(/bad.prune:2:5/)).toBeDefined();
    expect(screen.getByText(/Specify a valid identifier name/)).toBeDefined();
    expect(screen.getByText(/const = 100;/)).toBeDefined();
  });
});

describe("NodeInspector Component", () => {
  it("displays reachability provenance and compiler explanation for selected node", () => {
    const node: GraphNodeData = {
      id: "math.prune:add",
      label: "add",
      module: "math.prune",
      symbol: "add",
      status: "reachable",
      is_reachable: true,
      is_entry: false,
      is_side_effect: false,
      explanation: "Retained: Reachable from entry via path: main.prune:run -> math.prune:add",
      path: ["main.prune:run", "math.prune:add"],
      location: {
        filename: "math.prune",
        line: 2,
        column: 16,
        start_offset: 15,
        end_offset: 18,
      },
    };

    render(<NodeInspector selectedNode={node} onClose={() => {}} />);
    expect(screen.getByText("add")).toBeDefined();
    expect(screen.getByText("LIVE (Reachable)")).toBeDefined();
    expect(screen.getByText(/Retained: Reachable from entry/)).toBeDefined();
    expect(screen.getByText("main.prune:run")).toBeDefined();
    expect(screen.getByText("math.prune:add")).toBeDefined();
  });
});
