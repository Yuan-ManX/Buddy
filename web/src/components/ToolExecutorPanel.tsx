import React, { useState, useEffect } from 'react';

interface ToolDef {
  function: { name: string; description: string; parameters: any };
}

interface ToolStats {
  total_tools: number;
  total_executions: number;
  total_errors: number;
  tools: Array<{ name: string; category: string; risk: string }>;
}

export const ToolExecutorPanel: React.FC = () => {
  const [stats, setStats] = useState<ToolStats | null>(null);
  const [tools, setTools] = useState<ToolDef[]>([]);
  const [selectedTool, setSelectedTool] = useState('');
  const [args, setArgs] = useState('{}');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchStats(); fetchTools(); }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/tool-executor/stats');
      setStats(await res.json());
    } catch (e) { console.error('Failed to fetch tool stats:', e); }
  };

  const fetchTools = async () => {
    try {
      const res = await fetch('/api/tool-executor/tools');
      const data = await res.json();
      setTools(data.tools || []);
    } catch (e) { console.error('Failed to fetch tools:', e); }
  };

  const executeTool = async () => {
    if (!selectedTool) return;
    setLoading(true);
    try {
      let parsedArgs;
      try { parsedArgs = JSON.parse(args); } catch { parsedArgs = {}; }
      const res = await fetch('/api/tool-executor/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool_name: selectedTool, arguments: parsedArgs }),
      });
      setResult(await res.json());
      fetchStats();
    } catch (e) { console.error('Execute failed:', e); }
    setLoading(false);
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>Tool Executor</h2>
      <p style={{ color: '#666', marginBottom: 24 }}>Unified tool execution engine with built-in and custom tools</p>

      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <div style={{ flex: 1, background: '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a' }}>{stats.total_tools}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Available Tools</div>
          </div>
          <div style={{ flex: 1, background: '#eff6ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_executions}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Total Executions</div>
          </div>
          <div style={{ flex: 1, background: '#fef2f2', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#dc2626' }}>{stats.total_errors}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Total Errors</div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Tool</label>
          <select value={selectedTool} onChange={e => setSelectedTool(e.target.value)} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }}>
            <option value="">Select a tool...</option>
            {tools.map(t => (
              <option key={t.function.name} value={t.function.name}>{t.function.name}</option>
            ))}
          </select>
        </div>
        <div style={{ flex: 2 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Arguments (JSON)</label>
          <input value={args} onChange={e => setArgs(e.target.value)} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontFamily: 'monospace' }} />
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end' }}>
          <button onClick={executeTool} disabled={loading} style={{ padding: '8px 16px', background: loading ? '#999' : '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'default' : 'pointer' }}>
            {loading ? 'Running...' : 'Execute'}
          </button>
        </div>
      </div>

      {selectedTool && tools.find(t => t.function.name === selectedTool) && (
        <div style={{ background: '#f8fafc', borderRadius: 12, padding: 16, marginBottom: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>{tools.find(t => t.function.name === selectedTool)?.function.name}</div>
          <div style={{ fontSize: 13, color: '#666' }}>{tools.find(t => t.function.name === selectedTool)?.function.description}</div>
        </div>
      )}

      {result && (
        <div style={{ background: result.success ? '#f0fdf4' : '#fef2f2', borderRadius: 12, padding: 16, border: `1px solid ${result.success ? '#86efac' : '#fca5a5'}` }}>
          <div style={{ fontWeight: 600, marginBottom: 8, color: result.success ? '#16a34a' : '#dc2626' }}>
            {result.success ? 'Execution Successful' : 'Execution Failed'} ({result.duration_ms?.toFixed(0)}ms)
          </div>
          {result.error && <div style={{ color: '#dc2626', marginBottom: 8 }}>{result.error}</div>}
          <pre style={{ margin: 0, fontSize: 13, whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto' }}>
            {JSON.stringify(result.result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};