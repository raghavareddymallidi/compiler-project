import React, { useState, useEffect, useCallback } from "react";
import Editor from "@monaco-editor/react";
import { TopBar } from "./components/TopBar";
import { FileTree } from "./components/FileTree";
import { DependencyGraph } from "./components/DependencyGraph";
import { TraceViewer } from "./components/TraceViewer";
import { DiagnosticsViewer } from "./components/DiagnosticsViewer";
import { StatsViewer } from "./components/StatsViewer";
import { NodeInspector } from "./components/NodeInspector";
import { fetchSamples, compileCode } from "./api";
import type { SampleProject, CompilationResult, GraphNodeData, OptimizationEvent } from "./types";
import { GitBranch, Activity, AlertCircle, BarChart3, Columns, Code2, Layers } from "lucide-react";

export const App: React.FC = () => {
  const [samples, setSamples] = useState<Record<string, SampleProject>>({});
  const [selectedSampleKey, setSelectedSampleKey] = useState<string>("standard");
  const [files, setFiles] = useState<Record<string, string>>({});
  const [activeFile, setActiveFile] = useState<string>("");
  const [entryPoints, setEntryPoints] = useState<string[]>([]);
  const [selectedEntry, setSelectedEntry] = useState<string>("");
  const [optLevel, setOptLevel] = useState<string>("O1");

  // Compilation state
  const [isCompiling, setIsCompiling] = useState<boolean>(false);
  const [result, setResult] = useState<CompilationResult | null>(null);
  const [editorViewMode, setEditorViewMode] = useState<"split" | "source" | "bundle">("split");
  const [bottomTab, setBottomTab] = useState<"graph" | "trace" | "diagnostics" | "stats">("graph");

  // Selected node for right inspector
  const [selectedNode, setSelectedNode] = useState<GraphNodeData | null>(null);

  const triggerCompile = useCallback(
    async (
      currentFiles: Record<string, string>,
      currentEntries: string[],
      currentLevel: string
    ) => {
      setIsCompiling(true);
      try {
        const res = await compileCode(currentFiles, currentEntries, currentLevel);
        setResult(res);
        if (!res.success && res.diagnostics.length > 0) {
          setBottomTab("diagnostics");
        }
      } catch (err: any) {
        console.error("Compilation error:", err);
      } finally {
        setIsCompiling(false);
      }
    },
    []
  );

  const loadProjectFixture = useCallback(
    (key: string, fixture: SampleProject) => {
      setSelectedSampleKey(key);
      setFiles({ ...fixture.files });
      setEntryPoints([...fixture.entry_points]);
      const firstEntry = fixture.entry_points[0] || Object.keys(fixture.files)[0];
      setSelectedEntry(firstEntry);
      setActiveFile(firstEntry);
      setSelectedNode(null);

      // Automatically trigger initial compile for the fixture
      triggerCompile(fixture.files, [firstEntry], optLevel);
    },
    [optLevel, triggerCompile]
  );

  // Load samples from backend
  useEffect(() => {
    const init = async () => {
      try {
        const data = await fetchSamples();
        setSamples(data);
        if (data["standard"]) {
          loadProjectFixture("standard", data["standard"]);
        }
      } catch (err) {
        console.warn("Could not reach backend sample API, loading offline standard fallback", err);
      }
    };
    init();
  }, [loadProjectFixture]);

  const handleCompile = useCallback(() => {
    triggerCompile(files, [selectedEntry], optLevel);
  }, [files, selectedEntry, optLevel, triggerCompile]);

  const handleSelectSample = (key: string) => {
    if (samples[key]) {
      loadProjectFixture(key, samples[key]);
    }
  };

  const handleReset = () => {
    if (samples[selectedSampleKey]) {
      loadProjectFixture(selectedSampleKey, samples[selectedSampleKey]);
    }
  };

  // Keyboard shortcut Ctrl/Cmd + Enter to compile
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        handleCompile();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handleCompile]);

  // File mutations
  const handleFileChange = (newContent: string | undefined) => {
    if (activeFile && newContent !== undefined) {
      setFiles((prev) => ({ ...prev, [activeFile]: newContent }));
    }
  };

  const handleAddFile = (newFilename: string) => {
    setFiles((prev) => ({
      ...prev,
      [newFilename]: "// New module\nexport function example() {\n    return 42;\n}\n",
    }));
    setActiveFile(newFilename);
  };

  const handleDeleteFile = (filename: string) => {
    const updated = { ...files };
    delete updated[filename];
    setFiles(updated);
    if (activeFile === filename) {
      const remaining = Object.keys(updated);
      setActiveFile(remaining[0] || "");
    }
  };

  const handleSelectEvent = (event: OptimizationEvent) => {
    // If the event corresponds to a symbol, highlight or show inspector
    if (event.symbol) {
      setSelectedNode({
        id: `${event.file}:${event.symbol}`,
        label: event.symbol,
        module: event.file,
        symbol: event.symbol,
        status: event.decision === "removed" ? "unreachable" : "reachable",
        is_reachable: event.decision !== "removed",
        is_entry: false,
        is_side_effect: event.event_type === "side_effect_retained",
        explanation: event.reason,
        path: event.reachability_path || [],
        location: {
          filename: event.file,
          line: event.line,
          column: event.column,
          start_offset: 0,
          end_offset: 0,
        },
      });
    }
  };

  return (
    <div className="app-container">
      <TopBar
        samples={samples}
        selectedSampleKey={selectedSampleKey}
        onSelectSample={handleSelectSample}
        entryPoints={entryPoints.length > 0 ? entryPoints : Object.keys(files)}
        selectedEntry={selectedEntry}
        onSelectEntry={setSelectedEntry}
        optLevel={optLevel}
        onChangeOptLevel={(lvl) => {
          setOptLevel(lvl);
          triggerCompile(files, [selectedEntry], lvl);
        }}
        onCompile={handleCompile}
        isCompiling={isCompiling}
        result={result}
        onReset={handleReset}
      />

      <div className="main-workspace">
        {/* Left Sidebar: File Explorer */}
        <FileTree
          files={files}
          activeFile={activeFile}
          onSelectFile={setActiveFile}
          onAddFile={handleAddFile}
          onDeleteFile={handleDeleteFile}
        />

        {/* Center Panel: Code Editors & Visualizers */}
        <div className="center-area">
          {/* Editor Header Bar with View Toggles */}
          <div className="panel-header-tabs">
            <div className="tab-group">
              <button
                className={`tab-btn ${editorViewMode === "split" ? "active" : ""}`}
                onClick={() => setEditorViewMode("split")}
                title="Side-by-side Source and Bundle"
              >
                <Columns size={12} />
                Split View
              </button>
              <button
                className={`tab-btn ${editorViewMode === "source" ? "active" : ""}`}
                onClick={() => setEditorViewMode("source")}
                title="Original Source Module"
              >
                <Code2 size={12} />
                Source ({activeFile})
              </button>
              <button
                className={`tab-btn ${editorViewMode === "bundle" ? "active" : ""}`}
                onClick={() => setEditorViewMode("bundle")}
                title="Optimized Output Bundle"
              >
                <Layers size={12} />
                Optimized Bundle
              </button>
            </div>

            <div style={{ fontSize: 11, color: "var(--text-dim)", fontFamily: "var(--font-mono)" }}>
              Ctrl+Enter to build
            </div>
          </div>

          {/* Editors Container */}
          <div className="editor-container">
            {editorViewMode === "split" && (
              <div className="split-view">
                <div className="split-pane">
                  <div className="pane-label">
                    <span>SOURCE MODULE: {activeFile}</span>
                    <span>Editable</span>
                  </div>
                  <Editor
                    height="100%"
                    theme="vs-dark"
                    language="javascript"
                    value={files[activeFile] || ""}
                    onChange={handleFileChange}
                    options={{
                      fontSize: 12,
                      minimap: { enabled: false },
                      scrollBeyondLastLine: false,
                      tabSize: 2,
                    }}
                  />
                </div>
                <div className="split-pane">
                  <div className="pane-label">
                    <span>OPTIMIZED BUNDLE (JS)</span>
                    <span>Deterministic Output</span>
                  </div>
                  <Editor
                    height="100%"
                    theme="vs-dark"
                    language="javascript"
                    value={result?.bundle || "// Compile to inspect generated bundle"}
                    options={{
                      readOnly: true,
                      fontSize: 12,
                      minimap: { enabled: false },
                      scrollBeyondLastLine: false,
                      tabSize: 2,
                    }}
                  />
                </div>
              </div>
            )}

            {editorViewMode === "source" && (
              <div style={{ height: "100%", width: "100%" }}>
                <Editor
                  height="100%"
                  theme="vs-dark"
                  language="javascript"
                  value={files[activeFile] || ""}
                  onChange={handleFileChange}
                  options={{
                    fontSize: 12,
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    tabSize: 2,
                  }}
                />
              </div>
            )}

            {editorViewMode === "bundle" && (
              <div style={{ height: "100%", width: "100%" }}>
                <Editor
                  height="100%"
                  theme="vs-dark"
                  language="javascript"
                  value={result?.bundle || "// Compile to inspect generated bundle"}
                  options={{
                    readOnly: true,
                    fontSize: 12,
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    tabSize: 2,
                  }}
                />
              </div>
            )}
          </div>

          {/* Bottom Secondary Tabs: Dependency Graph, Trace, Diagnostics, Stats */}
          <div className="bottom-panel">
            <div className="panel-header-tabs">
              <div className="tab-group">
                <button
                  className={`tab-btn ${bottomTab === "graph" ? "active" : ""}`}
                  onClick={() => setBottomTab("graph")}
                >
                  <GitBranch size={12} />
                  Dependency Graph
                  {result?.graph?.nodes ? ` (${result.graph.nodes.length})` : ""}
                </button>
                <button
                  className={`tab-btn ${bottomTab === "trace" ? "active" : ""}`}
                  onClick={() => setBottomTab("trace")}
                >
                  <Activity size={12} />
                  Optimization Trace
                  {result?.events ? ` (${result.events.length})` : ""}
                </button>
                <button
                  className={`tab-btn ${bottomTab === "diagnostics" ? "active" : ""}`}
                  onClick={() => setBottomTab("diagnostics")}
                >
                  <AlertCircle size={12} />
                  Diagnostics
                  {result?.diagnostics && result.diagnostics.length > 0 ? (
                    <span style={{ color: "#f87171" }}>({result.diagnostics.length})</span>
                  ) : (
                    ""
                  )}
                </button>
                <button
                  className={`tab-btn ${bottomTab === "stats" ? "active" : ""}`}
                  onClick={() => setBottomTab("stats")}
                >
                  <BarChart3 size={12} />
                  Bundle Statistics
                </button>
              </div>
            </div>

            <div className="bottom-content">
              {bottomTab === "graph" && (
                <DependencyGraph
                  graphData={result?.graph}
                  onSelectNode={setSelectedNode}
                />
              )}
              {bottomTab === "trace" && (
                <TraceViewer
                  events={result?.events || []}
                  onSelectEvent={handleSelectEvent}
                />
              )}
              {bottomTab === "diagnostics" && (
                <DiagnosticsViewer diagnostics={result?.diagnostics || []} />
              )}
              {bottomTab === "stats" && <StatsViewer stats={result?.stats} />}
            </div>
          </div>
        </div>

        {/* Right Inspector Drawer */}
        <NodeInspector selectedNode={selectedNode} onClose={() => setSelectedNode(null)} />
      </div>
    </div>
  );
};

export default App;
