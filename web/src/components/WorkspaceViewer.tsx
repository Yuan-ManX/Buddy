import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { WorkspaceFile, ExecutionResult } from '../types';

export const WorkspaceViewer: React.FC = () => {
  const [agentId, setAgentId] = useState('');
  const [agents, setAgents] = useState<Array<{ id: string; name: string }>>([]);
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<WorkspaceFile | null>(null);
  const [newFileName, setNewFileName] = useState('');
  const [codeInput, setCodeInput] = useState('print("Hello from Buddy!")\n');
  const [execResult, setExecResult] = useState<ExecutionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'files' | 'code'>('files');

  useEffect(() => {
    loadAgents();
  }, []);

  useEffect(() => {
    if (agentId) loadFiles();
  }, [agentId]);

  const loadAgents = async () => {
    try {
      const data = await api.agents.list();
      setAgents(data.items.map(a => ({ id: a.id, name: a.name })));
      if (data.items.length > 0) setAgentId(data.items[0].id);
    } catch {}
  };

  const loadFiles = async () => {
    if (!agentId) return;
    try {
      const data = await api.workspace.files(agentId);
      setFiles(data);
    } catch {}
  };

  const selectFile = async (path: string) => {
    try {
      const file = await api.workspace.getFile(agentId, path);
      setSelectedFile(file);
      setActiveTab('files');
    } catch (e: any) {
      setError(e.message || 'Failed to load file');
    }
  };

  const createFile = async () => {
    if (!newFileName.trim()) return;
    setLoading(true);
    try {
      const file = await api.workspace.createFile(agentId, {
        name: newFileName,
        content: '# New file\n',
      });
      setFiles(prev => [...prev, file]);
      setNewFileName('');
      setSelectedFile(file);
    } catch (e: any) {
      setError(e.message || 'Failed to create file');
    } finally {
      setLoading(false);
    }
  };

  const updateFile = async () => {
    if (!selectedFile) return;
    setLoading(true);
    try {
      const updated = await api.workspace.updateFile(
        agentId,
        selectedFile.path,
        selectedFile.content || ''
      );
      setSelectedFile(updated);
      setFiles(prev => prev.map(f => f.path === updated.path ? updated : f));
    } catch (e: any) {
      setError(e.message || 'Failed to update file');
    } finally {
      setLoading(false);
    }
  };

  const deleteFile = async (path: string) => {
    try {
      await api.workspace.deleteFile(agentId, path);
      setFiles(prev => prev.filter(f => f.path !== path));
      if (selectedFile?.path === path) setSelectedFile(null);
    } catch (e: any) {
      setError(e.message || 'Failed to delete file');
    }
  };

  const executeCode = async (language: 'python' | 'shell') => {
    setLoading(true);
    setError('');
    try {
      let result: ExecutionResult;
      if (language === 'python') {
        result = await api.workspace.executePython(agentId, codeInput);
      } else {
        result = await api.workspace.executeShell(agentId, codeInput);
      }
      setExecResult(result);
    } catch (e: any) {
      setError(e.message || 'Execution failed');
    } finally {
      setLoading(false);
    }
  };

  const getLanguageIcon = (language: string) => {
    const icons: Record<string, string> = {
      python: '🐍', javascript: '🟨', typescript: '🟦', html: '🌐',
      css: '🎨', json: '📋', markdown: '📝', shell: '💻',
      rust: '🦀', go: '🔵', java: '☕', sql: '🗄',
    };
    return icons[language] || '📄';
  };

  return (
    <div className="workspace-viewer">
      <h2>Workspace</h2>
      <p className="subtitle">Sandboxed file system and code execution</p>

      {error && <div className="error-banner">{error}</div>}

      <div className="ws-agent-select">
        <label>Agent:</label>
        <select value={agentId} onChange={e => setAgentId(e.target.value)}>
          {agents.map(a => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
      </div>

      <div className="ws-tabs">
        <button
          className={`ws-tab ${activeTab === 'files' ? 'active' : ''}`}
          onClick={() => setActiveTab('files')}
        >
          Files
        </button>
        <button
          className={`ws-tab ${activeTab === 'code' ? 'active' : ''}`}
          onClick={() => setActiveTab('code')}
        >
          Code Runner
        </button>
      </div>

      {activeTab === 'files' && (
        <div className="ws-files-layout">
          <div className="ws-file-list">
            <div className="ws-create-file">
              <input
                type="text"
                placeholder="New file name..."
                value={newFileName}
                onChange={e => setNewFileName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && createFile()}
              />
              <button onClick={createFile} disabled={!newFileName.trim()}>+</button>
            </div>
            {files.map(file => (
              <div
                key={file.path}
                className={`ws-file-item ${selectedFile?.path === file.path ? 'selected' : ''}`}
                onClick={() => selectFile(file.path)}
              >
                <span className="file-icon">{getLanguageIcon(file.language)}</span>
                <div className="file-info">
                  <span className="file-name">{file.name}</span>
                  <span className="file-meta">{file.language} · {file.size} bytes</span>
                </div>
                <button
                  className="file-delete"
                  onClick={e => { e.stopPropagation(); deleteFile(file.path); }}
                >
                  ×
                </button>
              </div>
            ))}
            {files.length === 0 && (
              <div className="empty-state">No files in workspace</div>
            )}
          </div>

          <div className="ws-file-editor">
            {selectedFile ? (
              <>
                <div className="editor-header">
                  <span>{selectedFile.name}</span>
                  <span className="editor-lang">{selectedFile.language}</span>
                  <button onClick={updateFile} disabled={loading} className="btn-save">
                    Save
                  </button>
                </div>
                <textarea
                  className="editor-area"
                  value={selectedFile.content || ''}
                  onChange={e => setSelectedFile({ ...selectedFile, content: e.target.value })}
                  spellCheck={false}
                />
              </>
            ) : (
              <div className="no-selection">Select a file to edit</div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'code' && (
        <div className="ws-code-runner">
          <div className="code-input-area">
            <div className="code-header">
              <span className="code-lang">Python / Shell</span>
              <div className="code-actions">
                <button
                  onClick={() => executeCode('python')}
                  disabled={loading}
                  className="btn-run"
                >
                  Run Python
                </button>
                <button
                  onClick={() => executeCode('shell')}
                  disabled={loading}
                  className="btn-shell"
                >
                  Run Shell
                </button>
              </div>
            </div>
            <textarea
              className="code-editor"
              value={codeInput}
              onChange={e => setCodeInput(e.target.value)}
              spellCheck={false}
              rows={10}
            />
          </div>

          {execResult && (
            <div className={`code-output ${execResult.success ? 'success' : 'error'}`}>
              <div className="output-header">
                <span className={`output-status ${execResult.success ? 'success' : 'error'}`}>
                  {execResult.success ? 'Success' : 'Error'} (exit: {execResult.exit_code})
                </span>
                <span className="output-time">{execResult.execution_time.toFixed(3)}s</span>
              </div>
              <pre className="output-content">
                {execResult.output || execResult.error}
              </pre>
            </div>
          )}
        </div>
      )}

      <style>{`
        .workspace-viewer { padding: 24px; max-width: 1400px; margin: 0 auto; }
        .workspace-viewer h2 { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }
        .subtitle { color: #6b7280; margin-bottom: 24px; }
        .ws-agent-select { margin-bottom: 16px; display: flex; align-items: center; gap: 12px; }
        .ws-agent-select label { font-weight: 600; font-size: 0.9rem; }
        .ws-agent-select select { padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.9rem; background: #fff; }
        .ws-tabs { display: flex; gap: 4px; margin-bottom: 20px; background: #f3f4f6; border-radius: 8px; padding: 4px; width: fit-content; }
        .ws-tab { padding: 8px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 600; background: transparent; color: #6b7280; transition: all 0.15s; }
        .ws-tab.active { background: #fff; color: #1f2937; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .ws-files-layout { display: grid; grid-template-columns: 300px 1fr; gap: 24px; }
        .ws-file-list { background: #fff; border-radius: 12px; padding: 16px; border: 1px solid #e5e7eb; max-height: 600px; overflow-y: auto; }
        .ws-create-file { display: flex; gap: 8px; margin-bottom: 12px; }
        .ws-create-file input { flex: 1; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
        .ws-create-file button { padding: 8px 14px; background: #3b82f6; color: #fff; border: none; border-radius: 6px; font-weight: 700; cursor: pointer; }
        .ws-file-item { display: flex; align-items: center; gap: 10px; padding: 10px; border-radius: 6px; cursor: pointer; margin-bottom: 4px; transition: all 0.15s; }
        .ws-file-item:hover { background: #f9fafb; }
        .ws-file-item.selected { background: #eff6ff; }
        .file-icon { font-size: 1.2rem; }
        .file-info { flex: 1; display: flex; flex-direction: column; }
        .file-name { font-size: 0.85rem; font-weight: 600; }
        .file-meta { font-size: 0.7rem; color: #9ca3af; }
        .file-delete { padding: 2px 8px; background: none; border: none; color: #ef4444; cursor: pointer; font-size: 1.2rem; opacity: 0; transition: opacity 0.15s; }
        .ws-file-item:hover .file-delete { opacity: 1; }
        .ws-file-editor { background: #fff; border-radius: 12px; border: 1px solid #e5e7eb; overflow: hidden; }
        .editor-header { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #f9fafb; border-bottom: 1px solid #e5e7eb; }
        .editor-header span:first-child { font-weight: 600; font-size: 0.9rem; }
        .editor-lang { font-size: 0.75rem; color: #6b7280; background: #f3f4f6; padding: 2px 8px; border-radius: 4px; }
        .btn-save { margin-left: auto; padding: 6px 16px; background: #3b82f6; color: #fff; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
        .btn-save:disabled { background: #9ca3af; }
        .editor-area { width: 100%; min-height: 400px; padding: 16px; border: none; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.85rem; resize: vertical; outline: none; }
        .ws-code-runner { background: #fff; border-radius: 12px; border: 1px solid #e5e7eb; padding: 20px; }
        .code-input-area { margin-bottom: 20px; }
        .code-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .code-lang { font-weight: 600; font-size: 0.9rem; }
        .code-actions { display: flex; gap: 8px; }
        .btn-run { padding: 8px 16px; background: #10b981; color: #fff; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
        .btn-run:hover { background: #059669; }
        .btn-run:disabled { background: #9ca3af; }
        .btn-shell { padding: 8px 16px; background: #8b5cf6; color: #fff; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
        .btn-shell:hover { background: #7c3aed; }
        .btn-shell:disabled { background: #9ca3af; }
        .code-editor { width: 100%; padding: 16px; border: 1px solid #d1d5db; border-radius: 8px; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.85rem; resize: vertical; background: #1a1a2e; color: #e2e8f0; }
        .code-output { border-radius: 8px; overflow: hidden; border: 1px solid #e5e7eb; }
        .code-output.success { border-color: #10b981; }
        .code-output.error { border-color: #ef4444; }
        .output-header { display: flex; justify-content: space-between; padding: 10px 16px; background: #f9fafb; border-bottom: 1px solid #e5e7eb; }
        .output-status { font-weight: 600; font-size: 0.85rem; }
        .output-status.success { color: #10b981; }
        .output-status.error { color: #ef4444; }
        .output-time { font-size: 0.8rem; color: #9ca3af; }
        .output-content { padding: 16px; font-family: 'SF Mono', monospace; font-size: 0.85rem; white-space: pre-wrap; max-height: 300px; overflow-y: auto; background: #1a1a2e; color: #e2e8f0; margin: 0; }
        .no-selection { color: #9ca3af; text-align: center; padding: 60px; }
        .empty-state { color: #9ca3af; text-align: center; padding: 40px; font-size: 0.9rem; }
        .error-banner { background: #fef2f2; color: #991b1b; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 0.9rem; }
      `}</style>
    </div>
  );
};