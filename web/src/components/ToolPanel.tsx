import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { ToolDefinition, ToolResult } from '../types';

export const ToolPanel: React.FC = () => {
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [selectedTool, setSelectedTool] = useState<ToolDefinition | null>(null);
  const [arguments_, setArguments_] = useState<string>('{}');
  const [results, setResults] = useState<ToolResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadTools();
  }, []);

  const loadTools = async () => {
    try {
      const data = await api.tools.list();
      setTools(data);
    } catch (e) {
      setError('Failed to load tools');
    }
  };

  const executeTool = async () => {
    if (!selectedTool) return;
    setLoading(true);
    setError('');
    try {
      let args: Record<string, unknown>;
      try {
        args = JSON.parse(arguments_);
      } catch {
        setError('Invalid JSON arguments');
        setLoading(false);
        return;
      }
      const result = await api.tools.execute(selectedTool.name, args);
      setResults(prev => [result, ...prev].slice(0, 20));
    } catch (e: any) {
      setError(e.message || 'Tool execution failed');
    } finally {
      setLoading(false);
    }
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      knowledge: '#3b82f6',
      code: '#10b981',
      data: '#f59e0b',
      system: '#8b5cf6',
      communication: '#ec4899',
      creative: '#06b6d4',
    };
    return colors[category] || '#6b7280';
  };

  return (
    <div className="tool-panel">
      <h2>Tool System</h2>
      <p className="subtitle">Execute and manage agent tools</p>

      {error && <div className="error-banner">{error}</div>}

      <div className="tool-layout">
        <div className="tool-list">
          <h3>Available Tools ({tools.length})</h3>
          {tools.map(tool => (
            <div
              key={tool.name}
              className={`tool-item ${selectedTool?.name === tool.name ? 'selected' : ''}`}
              onClick={() => {
                setSelectedTool(tool);
                const defaults: Record<string, unknown> = {};
                tool.parameters.forEach(p => {
                  if (p.required) defaults[p.name] = p.type === 'integer' ? 0 : '';
                });
                setArguments_(JSON.stringify(defaults, null, 2));
              }}
            >
              <div className="tool-name">
                <span className="category-dot" style={{ background: getCategoryColor(tool.category) }} />
                {tool.name}
              </div>
              <div className="tool-desc">{tool.description}</div>
              <span className="tool-category">{tool.category}</span>
            </div>
          ))}
        </div>

        <div className="tool-detail">
          {selectedTool ? (
            <>
              <h3>{selectedTool.name}</h3>
              <p className="tool-description">{selectedTool.description}</p>
              <div className="tool-params">
                <h4>Parameters</h4>
                {selectedTool.parameters.map(p => (
                  <div key={p.name} className="param-item">
                    <span className="param-name">{p.name}</span>
                    <span className="param-type">{p.type}</span>
                    {p.required && <span className="param-required">required</span>}
                    <span className="param-desc">{p.description}</span>
                  </div>
                ))}
              </div>
              <div className="tool-args">
                <h4>Arguments (JSON)</h4>
                <textarea
                  value={arguments_}
                  onChange={e => setArguments_(e.target.value)}
                  rows={6}
                  placeholder='{"key": "value"}'
                />
              </div>
              <button
                className="btn-execute"
                onClick={executeTool}
                disabled={loading}
              >
                {loading ? 'Executing...' : 'Execute Tool'}
              </button>
            </>
          ) : (
            <div className="no-selection">Select a tool from the list to configure and execute</div>
          )}

          {results.length > 0 && (
            <div className="tool-results">
              <h4>Execution History</h4>
              {results.map((r, i) => (
                <div key={i} className={`result-item ${r.success ? 'success' : 'error'}`}>
                  <div className="result-header">
                    <span className="result-name">{r.name}</span>
                    <span className="result-status">{r.success ? 'OK' : 'ERR'}</span>
                    <span className="result-time">{r.duration_ms.toFixed(0)}ms</span>
                  </div>
                  <pre className="result-output">
                    {r.success ? r.output : r.error}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <style>{`
        .tool-panel { padding: 24px; max-width: 1400px; margin: 0 auto; }
        .tool-panel h2 { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }
        .subtitle { color: #6b7280; margin-bottom: 24px; }
        .tool-layout { display: grid; grid-template-columns: 320px 1fr; gap: 24px; }
        .tool-list { background: #fff; border-radius: 12px; padding: 16px; border: 1px solid #e5e7eb; max-height: 600px; overflow-y: auto; }
        .tool-list h3 { font-size: 0.9rem; color: #6b7280; margin-bottom: 12px; }
        .tool-item { padding: 12px; border-radius: 8px; cursor: pointer; margin-bottom: 8px; border: 1px solid transparent; transition: all 0.15s; }
        .tool-item:hover { background: #f9fafb; border-color: #e5e7eb; }
        .tool-item.selected { background: #eff6ff; border-color: #3b82f6; }
        .tool-name { font-weight: 600; display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
        .category-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
        .tool-desc { font-size: 0.85rem; color: #6b7280; margin-bottom: 4px; }
        .tool-category { font-size: 0.75rem; color: #9ca3af; text-transform: uppercase; }
        .tool-detail { background: #fff; border-radius: 12px; padding: 24px; border: 1px solid #e5e7eb; }
        .tool-detail h3 { font-size: 1.2rem; font-weight: 700; margin-bottom: 8px; }
        .tool-description { color: #4b5563; margin-bottom: 20px; }
        .tool-params { margin-bottom: 20px; }
        .tool-params h4, .tool-args h4 { font-size: 0.9rem; color: #374151; margin-bottom: 8px; }
        .param-item { padding: 8px 0; border-bottom: 1px solid #f3f4f6; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
        .param-name { font-weight: 600; font-family: monospace; font-size: 0.85rem; }
        .param-type { font-size: 0.75rem; color: #6b7280; background: #f3f4f6; padding: 1px 6px; border-radius: 4px; }
        .param-required { font-size: 0.7rem; color: #ef4444; background: #fef2f2; padding: 1px 6px; border-radius: 4px; }
        .param-desc { font-size: 0.8rem; color: #9ca3af; width: 100%; }
        .tool-args textarea { width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-family: monospace; font-size: 0.85rem; resize: vertical; }
        .btn-execute { margin-top: 16px; padding: 10px 24px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: background 0.15s; }
        .btn-execute:hover { background: #2563eb; }
        .btn-execute:disabled { background: #9ca3af; cursor: not-allowed; }
        .tool-results { margin-top: 24px; }
        .tool-results h4 { font-size: 0.9rem; color: #374151; margin-bottom: 12px; }
        .result-item { padding: 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #e5e7eb; }
        .result-item.success { border-left: 4px solid #10b981; }
        .result-item.error { border-left: 4px solid #ef4444; }
        .result-header { display: flex; gap: 12px; align-items: center; margin-bottom: 8px; }
        .result-name { font-weight: 600; font-family: monospace; }
        .result-status { font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; }
        .result-item.success .result-status { background: #d1fae5; color: #065f46; }
        .result-item.error .result-status { background: #fee2e2; color: #991b1b; }
        .result-time { font-size: 0.75rem; color: #9ca3af; }
        .result-output { font-size: 0.8rem; color: #374151; white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow-y: auto; background: #f9fafb; padding: 8px; border-radius: 4px; }
        .no-selection { color: #9ca3af; text-align: center; padding: 40px; }
        .error-banner { background: #fef2f2; color: #991b1b; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 0.9rem; }
      `}</style>
    </div>
  );
};