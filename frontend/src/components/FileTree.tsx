import React, { useState } from "react";
import { FileCode, Plus, Trash2 } from "lucide-react";

interface FileTreeProps {
  files: Record<string, string>;
  activeFile: string;
  onSelectFile: (file: string) => void;
  onAddFile: (filename: string) => void;
  onDeleteFile: (filename: string) => void;
}

export const FileTree: React.FC<FileTreeProps> = ({
  files,
  activeFile,
  onSelectFile,
  onAddFile,
  onDeleteFile,
}) => {
  const [isAdding, setIsAdding] = useState(false);
  const [newFileName, setNewFileName] = useState("");

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = newFileName.trim();
    if (clean) {
      onAddFile(clean.endsWith(".prune") ? clean : `${clean}.prune`);
      setNewFileName("");
      setIsAdding(false);
    }
  };

  const fileKeys = Object.keys(files).sort();

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span>Files ({fileKeys.length})</span>
        <button
          className="btn-secondary"
          style={{ padding: "2px 5px", fontSize: "11px" }}
          onClick={() => setIsAdding(!isAdding)}
          title="Add new file"
        >
          <Plus size={12} />
        </button>
      </div>

      {isAdding && (
        <form onSubmit={handleCreate} style={{ padding: "6px 8px", borderBottom: "1px solid var(--border-color)" }}>
          <input
            type="text"
            className="select-input"
            style={{ width: "100%", fontSize: "11px" }}
            placeholder="src/file.prune"
            value={newFileName}
            onChange={(e) => setNewFileName(e.target.value)}
            autoFocus
          />
        </form>
      )}

      <ul className="file-list">
        {fileKeys.map((path) => {
          const isActive = path === activeFile;
          return (
            <li
              key={path}
              className={`file-item ${isActive ? "active" : ""}`}
              onClick={() => onSelectFile(path)}
            >
              <div className="file-item-left" title={path}>
                <FileCode size={13} color={isActive ? "#38bdf8" : "#8e8e93"} />
                <span>{path}</span>
              </div>
              {fileKeys.length > 1 && (
                <button
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--text-dim)",
                    cursor: "pointer",
                    padding: "2px",
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteFile(path);
                  }}
                  title="Delete file"
                >
                  <Trash2 size={12} />
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </aside>
  );
};
