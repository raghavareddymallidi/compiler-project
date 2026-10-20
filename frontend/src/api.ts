import type { CompilationResult, SampleProject } from "./types";

const API_BASE = "http://localhost:8000/api";

export async function fetchHealth(): Promise<{ status: string; version: string }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("Backend offline");
  return res.json();
}

export async function fetchSamples(): Promise<Record<string, SampleProject>> {
  const res = await fetch(`${API_BASE}/samples`);
  if (!res.ok) throw new Error("Failed to load sample projects");
  return res.json();
}

export async function compileCode(
  files: Record<string, string>,
  entryPoints: string[],
  level: string
): Promise<CompilationResult> {
  const res = await fetch(`${API_BASE}/compile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      files,
      entry_points: entryPoints,
      optimization_level: level,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Compilation API error (${res.status})`);
  }

  return res.json();
}
