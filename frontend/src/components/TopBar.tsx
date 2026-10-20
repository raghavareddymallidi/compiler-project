import React from "react";
import { Play, RotateCcw, Box, CheckCircle2, AlertCircle } from "lucide-react";
import type { SampleProject, CompilationResult } from "../types";

interface TopBarProps {
  samples: Record<string, SampleProject>;
  selectedSampleKey: string;
  onSelectSample: (key: string) => void;
  entryPoints: string[];
  selectedEntry: string;
  onSelectEntry: (entry: string) => void;
  optLevel: string;
  onChangeOptLevel: (level: string) => void;
  onCompile: () => void;
  isCompiling: boolean;
  result: CompilationResult | null;
  onReset: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  samples,
  selectedSampleKey,
  onSelectSample,
  entryPoints,
  selectedEntry,
  onSelectEntry,
  optLevel,
  onChangeOptLevel,
  onCompile,
  isCompiling,
  result,
  onReset,
}) => {
  return (
    <header className="top-bar">
      <div className="top-bar-left">
        <div className="brand-title">
          <Box size={18} color="#38bdf8" />
          <span>PRUNE</span>
        </div>
        <span className="brand-badge">Compiler & Bundler</span>

        {/* Demo Project Selector */}
        <select
          className="select-input"
          value={selectedSampleKey}
          onChange={(e) => onSelectSample(e.target.value)}
          title="Select sample fixture"
        >
          {Object.entries(samples).map(([key, s]) => (
            <option key={key} value={key}>
              Sample: {s.name}
            </option>
          ))}
        </select>

        {/* Entry Point Selector */}
        <select
          className="select-input"
          value={selectedEntry}
          onChange={(e) => onSelectEntry(e.target.value)}
          title="Entry point file"
        >
          {entryPoints.map((ep) => (
            <option key={ep} value={ep}>
              Entry: {ep}
            </option>
          ))}
        </select>
      </div>

      <div className="top-bar-controls">
        {/* Optimization Level Switcher */}
        <div className="opt-btn-group" title="Optimization Level">
          {["O0", "O1", "O2"].map((lvl) => (
            <button
              key={lvl}
              className={`opt-btn ${optLevel === lvl ? "active" : ""}`}
              onClick={() => onChangeOptLevel(lvl)}
            >
              -{lvl}
            </button>
          ))}
        </div>

        {/* Reset button */}
        <button className="btn-secondary" onClick={onReset} title="Reset to sample code">
          <RotateCcw size={13} />
          Reset
        </button>

        {/* Compile button */}
        <button
          className="btn-primary"
          onClick={onCompile}
          disabled={isCompiling}
          title="Compile, optimize, and bundle"
        >
          <Play size={13} fill="#ffffff" />
          {isCompiling ? "Compiling..." : "Build & Analyze"}
        </button>

        {/* Quick status pill */}
        {result && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 5,
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              padding: "3px 8px",
              borderRadius: 3,
              backgroundColor: result.success ? "#0a2618" : "#2e1214",
              border: `1px solid ${result.success ? "#34d399" : "#f87171"}`,
              color: result.success ? "#34d399" : "#f87171",
            }}
          >
            {result.success ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
            <span>
              {result.success
                ? `Bundle: ${result.stats?.bundle_bytes || 0}B (-${result.stats?.reduction_percentage || 0}%)`
                : "Build Failed"}
            </span>
          </div>
        )}
      </div>
    </header>
  );
};
