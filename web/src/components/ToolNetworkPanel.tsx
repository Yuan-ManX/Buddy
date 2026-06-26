import React, { useState, useEffect, useCallback } from 'react';

const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try { const parsed = JSON.parse(body); message = parsed.detail || parsed.error || body; } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

interface ToolNetworkStats {
  total_tools: number;
  total_chains: number;
  total_executions: number;
  total_successful: number;
  total_failed: number;
  cache_hit_rate: number;
  avg_execution_time_ms: number;
}

interface Tool {
  id: string;
  name: string;
  description: string;
  category: string;
  version: string;
  status: string;
  input_schema: Record<string, unknown>;
  execution_count: number;
  success_rate: number;
  avg_duration_ms: number;
}

interface ToolChain {
  id: string;
  name: string;
  description: string;
  tool_ids: string[];
  execution_count: number;
  success_rate: number;
  created_at: string;
}

interface ToolExecution {
  id: string;
  tool_id: string;
  tool_name: string;
  chain_id: string;
  status: string;
  input: string;
  output: string;
  duration_ms: number;
  error: string;
  created_at: string;
}

interface CacheStats {
  total_entries: number;
  hit_count: number;
  miss_count: number;
  hit_rate: number;
  total_size_bytes: number;
}

type Tab = 'overview' | 'tools' | 'chains' | 'executions' | 'cache';

export const ToolNetworkPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Overview
  const [stats, setStats] = useState<ToolNetworkStats | null>(null);

  // Tools
  const [tools, setTools] = useState<Tool[]>([]);
  const [toolSearch, setToolSearch] = useState('');
  const [toolCategory, setToolCategory] = useState('');

  // Chains
  const [chains, setChains] = useState<ToolChain[]>([]);

  // Executions
  const [executions, setExecutions] = useState<ToolExecution[]>([]);
  const [execToolId, setExecToolId] = useState('');
  const [execPage, setExecPage] = useState(1);

  // Cache
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<ToolNetworkStats>('/tool-network/stats');
      setStats(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load tool network stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadTools = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      if (toolSearch) params.set('search', toolSearch);
      if (toolCategory) params.set('category', toolCategory);
      const data = await request<{ tools: Tool[] }>(`/tool-network/tools?${params.toString()}`);
      setTools(data.tools || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load tools');
    } finally {
      setLoading(false);
    }
  }, [toolSearch, toolCategory]);

  const loadChains = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<{ chains: ToolChain[] }>('/tool-network/chains');
      setChains(data.chains || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load chains');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadExecutions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      params.set('page', String(execPage));
      params.set('page_size', '20');
      if (execToolId) params.set('tool_id', execToolId);
      const data = await request<{ executions: ToolExecution[]; total: number }>(`/tool-network/executions?${params.toString()}`);
      setExecutions(data.executions || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load executions');
    } finally {
      setLoading(false);
    }
  }, [execPage, execToolId]);

  const loadCacheStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<CacheStats>('/tool-network/cache/stats');
      setCacheStats(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load cache stats');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
    loadTools();
    loadChains();
  }, []);

  const handleExecuteTool = async (toolId: string) => {
    const input = prompt('Enter tool input (JSON):');
    if (!input) return;
    try {
      const parsedInput = JSON.parse(input);
      await request('/tool-network/execute', {
        method: 'POST',
        body: JSON.stringify({ tool_id: toolId, input: parsedInput }),
      });
      loadStats();
      loadTools();
    } catch (e: any) {
      setError(e.message || 'Failed to execute tool');
    }
  };

  const handleCreateChain = async () => {
    const name = prompt('Chain name:');
    if (!name) return;
    const description = prompt('Description:') || '';
    const toolIdsStr = prompt('Tool IDs (comma-separated):');
    if (!toolIdsStr) return;
    try {
      await request('/tool-network/chains', {
        method: 'POST',
        body: JSON.stringify({
          name,
          description,
          tool_ids: toolIdsStr.split(',').map(s => s.trim()).filter(Boolean),
        }),
      });
      loadChains();
      loadStats();
    } catch (e: any) {
      setError(e.message || 'Failed to create chain');
    }
  };

  const handleExecuteChain = async (chainId: string) => {
    const input = prompt('Enter chain input (JSON):');
    if (!input) return;
    try {
      const parsedInput = JSON.parse(input);
      await request(`/tool-network/chains/${chainId}/execute`, {
        method: 'POST',
        body: JSON.stringify({ input: parsedInput }),
      });
      loadStats();
      loadChains();
      loadExecutions();
    } catch (e: any) {
      setError(e.message || 'Failed to execute chain');
    }
  };

  const handleClearCache = async () => {
    if (!confirm('Clear the entire tool cache?')) return;
    try {
      await request('/tool-network/cache', { method: 'DELETE' });
      loadCacheStats();
      loadStats();
    } catch (e: any) {
      setError(e.message || 'Failed to clear cache');
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'active': return '#10b981';
      case 'available': return '#10b981';
      case 'success': return '#10b981';
      case 'failed': return '#ef4444';
      case 'error': return '#ef4444';
      case 'running': return '#3b82f6';
      case 'deprecated': return '#f59e0b';
      default: return '#9ca3af';
    }
  };

  const tabStyle = (tab: Tab): React.CSSProperties => ({
    padding: '8px 16px',
    background: activeTab === tab ? '#3b82f6' : '#f3f4f6',
    color: activeTab === tab ? '#fff' : '#374151',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    fontWeight: activeTab === tab ? 600 : 400,
    fontSize: 13,
  });

  const statCardStyle: React.CSSProperties = {
    flex: 1,
    background: '#f9fafb',
    borderRadius: 12,
    padding: 16,
    textAlign: 'center',
    border: '1px solid #e5e7eb',
  };

  if (loading && !stats && tools.length === 0 && chains.length === 0) {
    return <div style={{ padding: 24, color: '#6b7280' }}>Loading tool network data...</div>;
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Tool Network</h2>
          <p style={{ color: '#6b7280', margin: '4px 0 0 0', fontSize: 13 }}>Tool registry, execution chains, and cache management</p>
        </div>
        <button
          onClick={() => { loadStats(); loadTools(); loadChains(); }}
          style={{ padding: '8px 16px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 500 }}
        >
          Refresh
        </button>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: '#fef2f2', borderRadius: 8, color: '#dc2626', marginBottom: 16, fontSize: 13 }}>
          {error}
          <button style={{ marginLeft: 12, color: '#dc2626', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }} onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
        {(['overview', 'tools', 'chains', 'executions', 'cache'] as Tab[]).map(tab => (
          <button key={tab} style={tabStyle(tab)} onClick={() => {
            setActiveTab(tab);
            if (tab === 'cache') loadCacheStats();
            if (tab === 'executions') loadExecutions();
          }}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && stats && (
        <div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_tools}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Total Tools</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#7c3aed' }}>{stats.total_chains}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Tool Chains</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#059669' }}>{stats.total_executions.toLocaleString()}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Total Executions</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#ea580c' }}>{stats.cache_hit_rate.toFixed(1)}%</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Cache Hit Rate</div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 16 }}>
            <div style={{ flex: 1, background: '#f9fafb', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb' }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0' }}>Execution Metrics</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Successful</span>
                  <span style={{ fontWeight: 600, color: '#10b981' }}>{stats.total_successful}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Failed</span>
                  <span style={{ fontWeight: 600, color: '#ef4444' }}>{stats.total_failed}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Success Rate</span>
                  <span style={{ fontWeight: 600 }}>
                    {stats.total_executions > 0 ? ((stats.total_successful / stats.total_executions) * 100).toFixed(1) : '0'}%
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Avg Execution Time</span>
                  <span style={{ fontWeight: 600 }}>{stats.avg_execution_time_ms.toFixed(1)}ms</span>
                </div>
              </div>
            </div>
            <div style={{ flex: 2, background: '#f9fafb', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb' }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0' }}>Top Tools</h3>
              {tools.length === 0 ? (
                <div style={{ color: '#9ca3af', fontSize: 13 }}>No tools registered.</div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>Tool</th>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>Category</th>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>Executions</th>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>Success Rate</th>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>Avg Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tools.sort((a, b) => b.execution_count - a.execution_count).slice(0, 10).map(tool => (
                      <tr key={tool.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                        <td style={{ padding: '6px 8px', fontWeight: 500 }}>{tool.name}</td>
                        <td style={{ padding: '6px 8px' }}>
                          <span style={{ background: '#f3f4f6', padding: '2px 8px', borderRadius: 12, fontSize: 11 }}>{tool.category}</span>
                        </td>
                        <td style={{ padding: '6px 8px' }}>{tool.execution_count}</td>
                        <td style={{ padding: '6px 8px', color: tool.success_rate >= 90 ? '#10b981' : tool.success_rate >= 70 ? '#f59e0b' : '#ef4444' }}>
                          {tool.success_rate.toFixed(1)}%
                        </td>
                        <td style={{ padding: '6px 8px' }}>{tool.avg_duration_ms.toFixed(0)}ms</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tools Tab */}
      {activeTab === 'tools' && (
        <div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16, alignItems: 'center' }}>
            <input
              value={toolSearch}
              onChange={e => setToolSearch(e.target.value)}
              placeholder="Search tools..."
              style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
              onKeyDown={e => e.key === 'Enter' && loadTools()}
            />
            <select
              value={toolCategory}
              onChange={e => { setToolCategory(e.target.value); }}
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            >
              <option value="">All Categories</option>
              {[...new Set(tools.map(t => t.category))].map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
            <button
              onClick={loadTools}
              style={{ padding: '8px 16px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 13 }}
            >
              Filter
            </button>
          </div>

          {tools.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No tools found.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {tools.map(tool => (
                <div key={tool.id} style={{ background: '#fff', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                        <h4 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>{tool.name}</h4>
                        <span style={{
                          display: 'inline-block',
                          padding: '2px 8px',
                          borderRadius: 12,
                          background: statusColor(tool.status),
                          color: '#fff',
                          fontSize: 11,
                          fontWeight: 600,
                        }}>
                          {tool.status}
                        </span>
                        <span style={{ fontSize: 11, color: '#9ca3af' }}>v{tool.version}</span>
                      </div>
                      <p style={{ fontSize: 13, color: '#6b7280', margin: '0 0 8px 0' }}>{tool.description}</p>
                      <div style={{ display: 'flex', gap: 16, fontSize: 13 }}>
                        <span style={{ color: '#6b7280' }}>Category: <strong>{tool.category}</strong></span>
                        <span style={{ color: '#6b7280' }}>Executions: <strong>{tool.execution_count}</strong></span>
                        <span style={{
                          color: tool.success_rate >= 90 ? '#10b981' : tool.success_rate >= 70 ? '#f59e0b' : '#ef4444',
                        }}>
                          Success: <strong>{tool.success_rate.toFixed(1)}%</strong>
                        </span>
                        <span style={{ color: '#6b7280' }}>Avg: <strong>{tool.avg_duration_ms.toFixed(0)}ms</strong></span>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                      <button
                        onClick={() => handleExecuteTool(tool.id)}
                        style={{ padding: '6px 12px', background: '#10b981', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}
                      >
                        Execute
                      </button>
                      <button
                        onClick={() => {
                          setExecToolId(tool.id);
                          setExecPage(1);
                          loadExecutions();
                          setActiveTab('executions');
                        }}
                        style={{ padding: '6px 12px', background: '#eff6ff', color: '#2563eb', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}
                      >
                        History
                      </button>
                    </div>
                  </div>
                  {tool.input_schema && Object.keys(tool.input_schema).length > 0 && (
                    <details style={{ marginTop: 8 }}>
                      <summary style={{ fontSize: 12, color: '#6b7280', cursor: 'pointer' }}>Input Schema</summary>
                      <pre style={{ margin: '8px 0 0 0', padding: 8, background: '#f9fafb', borderRadius: 6, fontSize: 12, fontFamily: 'monospace', overflow: 'auto' }}>
                        {JSON.stringify(tool.input_schema, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Chains Tab */}
      {activeTab === 'chains' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>Tool Chains</h3>
            <button
              onClick={handleCreateChain}
              style={{ padding: '8px 16px', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 500 }}
            >
              + New Chain
            </button>
          </div>
          {chains.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No tool chains defined. Create one to chain multiple tool executions.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {chains.map(chain => (
                <div key={chain.id} style={{ background: '#fff', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <h4 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 4px 0' }}>{chain.name}</h4>
                      <p style={{ fontSize: 13, color: '#6b7280', margin: '0 0 8px 0' }}>{chain.description}</p>
                      <div style={{ display: 'flex', gap: 16, fontSize: 13 }}>
                        <span style={{ color: '#6b7280' }}>Executions: <strong>{chain.execution_count}</strong></span>
                        <span style={{
                          color: chain.success_rate >= 90 ? '#10b981' : chain.success_rate >= 70 ? '#f59e0b' : '#ef4444',
                        }}>
                          Success: <strong>{chain.success_rate.toFixed(1)}%</strong>
                        </span>
                        <span style={{ color: '#6b7280' }}>Created: <strong>{new Date(chain.created_at).toLocaleDateString()}</strong></span>
                      </div>
                      <div style={{ marginTop: 8 }}>
                        <span style={{ fontSize: 12, color: '#6b7280' }}>Tools: </span>
                        {chain.tool_ids.map((toolId, idx) => (
                          <span key={toolId} style={{
                            display: 'inline-block',
                            margin: '2px 4px 2px 0',
                            padding: '2px 8px',
                            background: '#eff6ff',
                            color: '#2563eb',
                            borderRadius: 12,
                            fontSize: 11,
                            fontFamily: 'monospace',
                          }}>
                            {idx + 1}. {toolId}
                          </span>
                        ))}
                      </div>
                    </div>
                    <button
                      onClick={() => handleExecuteChain(chain.id)}
                      style={{ padding: '8px 16px', background: '#10b981', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 500, flexShrink: 0 }}
                    >
                      Execute Chain
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Executions Tab */}
      {activeTab === 'executions' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>Tool Executions</h3>
            <div style={{ display: 'flex', gap: 8 }}>
              <select
                value={execToolId}
                onChange={e => { setExecToolId(e.target.value); setExecPage(1); }}
                style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
              >
                <option value="">All Tools</option>
                {tools.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
              <button
                onClick={loadExecutions}
                style={{ padding: '6px 12px', background: '#f3f4f6', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}
              >
                Refresh
              </button>
            </div>
          </div>

          {executions.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No executions recorded.</div>
          ) : (
            <div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, background: '#fff', borderRadius: 12, overflow: 'hidden', border: '1px solid #e5e7eb' }}>
                <thead>
                  <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Tool</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Status</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Duration</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Input</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Output</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {executions.map(exec => (
                    <tr key={exec.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '10px 12px', fontWeight: 500 }}>{exec.tool_name}</td>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{
                          display: 'inline-block',
                          padding: '2px 8px',
                          borderRadius: 12,
                          background: statusColor(exec.status),
                          color: '#fff',
                          fontSize: 11,
                          fontWeight: 600,
                        }}>
                          {exec.status}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 12 }}>{exec.duration_ms}ms</td>
                      <td style={{ padding: '10px 12px', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 12, color: '#6b7280' }}>
                        {exec.input}
                      </td>
                      <td style={{ padding: '10px 12px', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 12, color: '#6b7280' }}>
                        {exec.output || (exec.error ? <span style={{ color: '#ef4444' }}>{exec.error}</span> : '-')}
                      </td>
                      <td style={{ padding: '10px 12px', fontSize: 12, color: '#6b7280' }}>{new Date(exec.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
                <button
                  onClick={() => { setExecPage(p => Math.max(1, p - 1)); loadExecutions(); }}
                  disabled={execPage === 1}
                  style={{ padding: '6px 12px', background: execPage === 1 ? '#f3f4f6' : '#e5e7eb', border: 'none', borderRadius: 6, cursor: execPage === 1 ? 'default' : 'pointer', fontSize: 12 }}
                >
                  Previous
                </button>
                <span style={{ padding: '6px 12px', fontSize: 13, color: '#6b7280' }}>Page {execPage}</span>
                <button
                  onClick={() => { setExecPage(p => p + 1); loadExecutions(); }}
                  disabled={executions.length < 20}
                  style={{ padding: '6px 12px', background: executions.length < 20 ? '#f3f4f6' : '#e5e7eb', border: 'none', borderRadius: 6, cursor: executions.length < 20 ? 'default' : 'pointer', fontSize: 12 }}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Cache Tab */}
      {activeTab === 'cache' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>Tool Cache</h3>
            <button
              onClick={handleClearCache}
              style={{ padding: '8px 16px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 500 }}
            >
              Clear Cache
            </button>
          </div>

          {!cacheStats ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>Loading cache stats...</div>
          ) : (
            <div>
              <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
                <div style={statCardStyle}>
                  <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{cacheStats.total_entries}</div>
                  <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Cached Entries</div>
                </div>
                <div style={statCardStyle}>
                  <div style={{ fontSize: 28, fontWeight: 700, color: '#10b981' }}>{cacheStats.hit_count.toLocaleString()}</div>
                  <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Cache Hits</div>
                </div>
                <div style={statCardStyle}>
                  <div style={{ fontSize: 28, fontWeight: 700, color: '#ef4444' }}>{cacheStats.miss_count.toLocaleString()}</div>
                  <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Cache Misses</div>
                </div>
                <div style={statCardStyle}>
                  <div style={{ fontSize: 28, fontWeight: 700, color: '#ea580c' }}>{cacheStats.hit_rate.toFixed(1)}%</div>
                  <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Hit Rate</div>
                </div>
              </div>

              <div style={{ background: '#f9fafb', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb' }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0' }}>Cache Details</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#6b7280' }}>Total Size</span>
                    <span style={{ fontWeight: 600 }}>{formatBytes(cacheStats.total_size_bytes)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#6b7280' }}>Avg Entry Size</span>
                    <span style={{ fontWeight: 600 }}>
                      {cacheStats.total_entries > 0 ? formatBytes(cacheStats.total_size_bytes / cacheStats.total_entries) : 'N/A'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#6b7280' }}>Hit/Miss Ratio</span>
                    <span style={{ fontWeight: 600 }}>
                      {cacheStats.hit_count}:{cacheStats.miss_count}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};