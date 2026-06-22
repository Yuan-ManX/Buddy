import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import type { ContextCompressorStats, ContextChunk, CompressionResult, TokenBudget } from '../types';

export const ContextCompressorPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<ContextCompressorStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'chunks' | 'compress' | 'context' | 'budget'>('overview');

  // Chunk form
  const [chunkForm, setChunkForm] = useState({
    content: '', priority: 'medium', source: '',
  });

  // Compress state
  const [compressStrategy, setCompressStrategy] = useState('');
  const [compressTargetTokens, setCompressTargetTokens] = useState('');
  const [compressResult, setCompressResult] = useState<CompressionResult | null>(null);

  // Context state
  const [contextChunks, setContextChunks] = useState<ContextChunk[]>([]);
  const [contextBudget, setContextBudget] = useState<TokenBudget | null>(null);

  // Budget state
  const [budgetForm, setBudgetForm] = useState({
    max_tokens: '100000', auto_compress: true,
  });
  const [currentBudget, setCurrentBudget] = useState<TokenBudget | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.contextCompressor.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load context compressor data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleAddChunk = async () => {
    if (!chunkForm.content.trim()) return;
    try {
      await api.contextCompressor.addChunk({
        content: chunkForm.content,
        priority: chunkForm.priority,
        source: chunkForm.source || undefined,
      });
      toast.success('Context chunk added');
      setChunkForm({ content: '', priority: 'medium', source: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCompress = async () => {
    try {
      const result = await api.contextCompressor.compress({
        strategy: compressStrategy || undefined,
        target_tokens: compressTargetTokens ? parseInt(compressTargetTokens) : undefined,
      });
      setCompressResult(result);
      toast.success(`Compression complete: ${result.tokens_saved.toLocaleString()} tokens saved`);
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleLoadContext = async () => {
    try {
      const result = await api.contextCompressor.context();
      setContextChunks(result.chunks);
      setContextBudget(result.budget);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSetBudget = async () => {
    try {
      const result = await api.contextCompressor.setBudget({
        max_tokens: parseInt(budgetForm.max_tokens),
        auto_compress: budgetForm.auto_compress,
      });
      setCurrentBudget(result);
      toast.success('Token budget updated');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleClearContext = async () => {
    try {
      await api.contextCompressor.clear();
      toast.success('Context cleared');
      setContextChunks([]);
      setContextBudget(null);
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const priorityColors: Record<string, string> = {
    high: '#ef4444',
    medium: '#f59e0b',
    low: '#22c55e',
  };

  const priorityLabels: Record<string, string> = {
    high: 'High',
    medium: 'Medium',
    low: 'Low',
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Context Compressor</h2>
          <p className="panel-subtitle">Intelligent context compression and token budget management</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading context compressor data...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Context Compressor</h2>
        <p className="panel-subtitle">Intelligent context compression, chunk management, and token budget control</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.total_chunks}</span><span className="stat-label">Total Chunks</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.active_chunks}</span><span className="stat-label">Active</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.total_compressions}</span><span className="stat-label">Compressions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.total_tokens_saved.toLocaleString()}</span><span className="stat-label">Tokens Saved</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{(stats.average_compression_ratio * 100).toFixed(1)}%</span><span className="stat-label">Avg Ratio</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'chunks', 'compress', 'context', 'budget'] as const).map(s => (
          <button key={s} className={`forge-tab ${activeSection === s ? 'active' : ''}`} onClick={() => setActiveSection(s)}>
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <h3>Compression Summary</h3>
          <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
            <div style={{
              flex: 1,
              padding: 20,
              background: '#e8eaf6',
              borderRadius: 8,
              textAlign: 'center',
              border: '2px solid #4f6ef7',
            }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: '#4f6ef7' }}>{stats.total_chunks}</div>
              <div style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: 4 }}>Total Chunks</div>
            </div>
            <div style={{
              flex: 1,
              padding: 20,
              background: '#e8f5e9',
              borderRadius: 8,
              textAlign: 'center',
              border: '2px solid #22c55e',
            }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: '#22c55e' }}>{stats.total_tokens_saved.toLocaleString()}</div>
              <div style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: 4 }}>Tokens Saved</div>
            </div>
            <div style={{
              flex: 1,
              padding: 20,
              background: '#fef3c7',
              borderRadius: 8,
              textAlign: 'center',
              border: '2px solid #f59e0b',
            }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: '#f59e0b' }}>{(stats.average_compression_ratio * 100).toFixed(1)}%</div>
              <div style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: 4 }}>Avg Ratio</div>
            </div>
          </div>

          <div className="dashboard-stat-row"><span>Total Compressions</span><strong>{stats.total_compressions}</strong></div>
          <div className="dashboard-stat-row"><span>Active Chunks</span><strong>{stats.active_chunks}</strong></div>

          <h3 style={{ marginTop: 20 }}>By Strategy</h3>
          {Object.entries(stats.by_strategy).length > 0 ? (
            Object.entries(stats.by_strategy).map(([strategy, count]) => (
              <div key={strategy} className="dashboard-stat-row">
                <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{strategy.replace(/_/g, ' ')}</span>
                <strong>{count}</strong>
              </div>
            ))
          ) : (
            <div className="panel-empty">No compression data yet</div>
          )}
        </div>
      )}

      {/* Chunks */}
      {activeSection === 'chunks' && (
        <div className="dashboard-section">
          <h3>Add Context Chunk</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Content</label>
              <textarea
                rows={5}
                value={chunkForm.content}
                onChange={e => setChunkForm(f => ({ ...f, content: e.target.value }))}
                placeholder="Enter the context information to add..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Priority</label>
                <select value={chunkForm.priority} onChange={e => setChunkForm(f => ({ ...f, priority: e.target.value }))}>
                  {['high', 'medium', 'low'].map(p => (
                    <option key={p} value={p}>{priorityLabels[p]}</option>
                  ))}
                </select>
              </div>
              <div className="form-group" style={{ flex: 2 }}>
                <label>Source</label>
                <input
                  type="text"
                  value={chunkForm.source}
                  onChange={e => setChunkForm(f => ({ ...f, source: e.target.value }))}
                  placeholder="e.g., conversation, document, agent-output"
                />
              </div>
            </div>
            <button className="btn-primary" onClick={handleAddChunk}>Add Chunk</button>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3>Current Context Chunks</h3>
            <button className="btn-primary-sm" onClick={handleLoadContext}>Load Chunks</button>
          </div>

          {contextChunks.length === 0 ? (
            <div className="panel-empty">Click "Load Chunks" to view current context chunks.</div>
          ) : (
            <div className="forge-skill-list">
              {contextChunks.map((chunk: ContextChunk) => (
                <div key={chunk.chunk_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name" style={{ fontSize: '0.9rem', maxWidth: '70%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {chunk.content}
                    </div>
                    <span className="dashboard-badge" style={{ background: priorityColors[chunk.priority] || '#666', color: '#fff' }}>
                      {priorityLabels[chunk.priority] || chunk.priority}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Tokens: {chunk.token_count.toLocaleString()} | Source: {chunk.source || 'N/A'}</div>
                    <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: 4 }}>
                      ID: {chunk.chunk_id} | Created: {new Date(chunk.created_at).toLocaleString()}
                    </div>
                    <div style={{ marginTop: 8, padding: 8, background: '#f9fafb', borderRadius: 6, fontSize: '0.85rem', color: '#374151', maxHeight: 80, overflow: 'hidden' }}>
                      {chunk.content}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Compress */}
      {activeSection === 'compress' && (
        <div className="dashboard-section">
          <h3>Compress Context</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Strategy</label>
                <select value={compressStrategy} onChange={e => setCompressStrategy(e.target.value)}>
                  <option value="">Default</option>
                  {['summarize', 'prune', 'merge', 'extract_key_points', 'hierarchical', 'relevance_filter'].map(s => (
                    <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Target Tokens (optional)</label>
                <input
                  type="text"
                  value={compressTargetTokens}
                  onChange={e => setCompressTargetTokens(e.target.value)}
                  placeholder="e.g., 4000"
                />
              </div>
            </div>
            <button className="btn-primary" onClick={handleCompress}>Compress Context</button>
          </div>

          {compressResult && (
            <div style={{ marginTop: 16 }}>
              <h4>Compression Result</h4>
              <div className="forge-skill-card">
                <div className="forge-skill-header">
                  <div className="forge-skill-name">Compression #{compressResult.compression_id}</div>
                  <span className="dashboard-badge active">{compressResult.strategy}</span>
                </div>
                <div className="forge-skill-meta">
                  <div style={{ display: 'flex', gap: 16, marginBottom: 12, flexWrap: 'wrap' }}>
                    <div style={{
                      flex: '1 0 auto',
                      padding: 12,
                      background: '#fef2f2',
                      borderRadius: 6,
                      textAlign: 'center',
                      border: '1px solid #fecaca',
                    }}>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ef4444' }}>{compressResult.original_tokens.toLocaleString()}</div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Original Tokens</div>
                    </div>
                    <div style={{
                      flex: '1 0 auto',
                      padding: 12,
                      background: '#f0fdf4',
                      borderRadius: 6,
                      textAlign: 'center',
                      border: '1px solid #bbf7d0',
                    }}>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#22c55e' }}>{compressResult.compressed_tokens.toLocaleString()}</div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Compressed Tokens</div>
                    </div>
                    <div style={{
                      flex: '1 0 auto',
                      padding: 12,
                      background: '#eff6ff',
                      borderRadius: 6,
                      textAlign: 'center',
                      border: '1px solid #bfdbfe',
                    }}>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#3b82f6' }}>{(compressResult.compression_ratio * 100).toFixed(1)}%</div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Ratio</div>
                    </div>
                    <div style={{
                      flex: '1 0 auto',
                      padding: 12,
                      background: '#fefce8',
                      borderRadius: 6,
                      textAlign: 'center',
                      border: '1px solid #fef08a',
                    }}>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#eab308' }}>{compressResult.tokens_saved.toLocaleString()}</div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Tokens Saved</div>
                    </div>
                  </div>

                  {/* Compression bar */}
                  <div style={{ width: '100%', background: '#e5e7eb', borderRadius: 4, height: 12, marginBottom: 8 }}>
                    <div style={{
                      width: `${(compressResult.compressed_tokens / compressResult.original_tokens) * 100}%`,
                      background: '#22c55e',
                      height: '100%',
                      borderRadius: 4,
                    }} />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#9ca3af' }}>
                    <span>Compressed ({compressResult.compressed_tokens.toLocaleString()})</span>
                    <span>Original ({compressResult.original_tokens.toLocaleString()})</span>
                  </div>

                  {compressResult.summary && (
                    <div style={{ marginTop: 12, padding: 10, background: '#f9fafb', borderRadius: 6, fontSize: '0.85rem', color: '#374151' }}>
                      <strong>Summary:</strong> {compressResult.summary}
                    </div>
                  )}

                  <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: 8 }}>
                    {new Date(compressResult.created_at).toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Context */}
      {activeSection === 'context' && (
        <div className="dashboard-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3>Current Context</h3>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn-primary-sm" onClick={handleLoadContext}>Load Context</button>
              <button className="btn-sm" style={{ background: '#ef4444', color: '#fff', border: 'none' }} onClick={handleClearContext}>
                Clear Context
              </button>
            </div>
          </div>

          {contextBudget && (
            <div style={{ marginBottom: 16, padding: 16, background: '#f8fafc', borderRadius: 8 }}>
              <h4>Token Budget</h4>
              <div style={{ display: 'flex', gap: 16, marginTop: 8, flexWrap: 'wrap' }}>
                <div className="stat-item" style={{ flex: '1 0 auto' }}>
                  <div className="stat-content">
                    <span className="stat-value">{contextBudget.max_tokens.toLocaleString()}</span>
                    <span className="stat-label">Max Tokens</span>
                  </div>
                </div>
                <div className="stat-item" style={{ flex: '1 0 auto' }}>
                  <div className="stat-content">
                    <span className="stat-value" style={{ color: contextBudget.usage_percent > 80 ? '#ef4444' : '#3b82f6' }}>
                      {contextBudget.current_tokens.toLocaleString()}
                    </span>
                    <span className="stat-label">Current</span>
                  </div>
                </div>
                <div className="stat-item" style={{ flex: '1 0 auto' }}>
                  <div className="stat-content">
                    <span className="stat-value" style={{ color: contextBudget.remaining > 0 ? '#22c55e' : '#ef4444' }}>
                      {contextBudget.remaining.toLocaleString()}
                    </span>
                    <span className="stat-label">Remaining</span>
                  </div>
                </div>
                <div className="stat-item" style={{ flex: '1 0 auto' }}>
                  <div className="stat-content">
                    <span className="stat-value" style={{ color: contextBudget.usage_percent > 80 ? '#ef4444' : '#4f6ef7' }}>
                      {contextBudget.usage_percent.toFixed(1)}%
                    </span>
                    <span className="stat-label">Usage</span>
                  </div>
                </div>
              </div>
              <div style={{ width: '100%', background: '#e5e7eb', borderRadius: 4, marginTop: 12, height: 10 }}>
                <div style={{
                  width: `${contextBudget.usage_percent}%`,
                  background: contextBudget.usage_percent > 80
                    ? '#ef4444'
                    : contextBudget.usage_percent > 50
                      ? '#f59e0b'
                      : '#22c55e',
                  height: '100%',
                  borderRadius: 4,
                }} />
              </div>
              {contextBudget.auto_compress && (
                <div style={{ marginTop: 8, fontSize: '0.8rem', color: '#6b7280' }}>
                  <span className="dashboard-badge active">Auto-Compress</span> enabled
                </div>
              )}
            </div>
          )}

          {contextChunks.length === 0 ? (
            <div className="panel-empty">Click "Load Context" to view current context chunks.</div>
          ) : (
            <div className="forge-skill-list">
              {contextChunks.map((chunk: ContextChunk) => (
                <div key={chunk.chunk_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name" style={{ fontSize: '0.9rem', maxWidth: '60%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {chunk.content}
                    </div>
                    <span className="dashboard-badge" style={{ background: priorityColors[chunk.priority] || '#666', color: '#fff' }}>
                      {priorityLabels[chunk.priority] || chunk.priority}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{chunk.token_count.toLocaleString()} tokens | Source: {chunk.source || 'N/A'}</div>
                    <div style={{ marginTop: 8, padding: 8, background: '#f9fafb', borderRadius: 6, fontSize: '0.85rem', color: '#374151', maxHeight: 100, overflow: 'hidden' }}>
                      {chunk.content}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Budget */}
      {activeSection === 'budget' && (
        <div className="dashboard-section">
          <h3>Token Budget Management</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Max Tokens</label>
                <input
                  type="text"
                  value={budgetForm.max_tokens}
                  onChange={e => setBudgetForm(f => ({ ...f, max_tokens: e.target.value }))}
                  placeholder="100000"
                />
              </div>
              <div className="form-group">
                <label>Auto-Compress</label>
                <select
                  value={budgetForm.auto_compress ? 'true' : 'false'}
                  onChange={e => setBudgetForm(f => ({ ...f, auto_compress: e.target.value === 'true' }))}
                >
                  <option value="true">Enabled</option>
                  <option value="false">Disabled</option>
                </select>
              </div>
            </div>
            <button className="btn-primary" onClick={handleSetBudget}>Set Budget</button>
          </div>

          {currentBudget && (
            <div style={{ marginTop: 16 }}>
              <h4>Current Budget Status</h4>
              <div className="forge-skill-card">
                <div className="forge-skill-header">
                  <div className="forge-skill-name">Token Budget</div>
                  <span className="dashboard-badge" style={{
                    background: currentBudget.usage_percent > 80 ? '#ef4444' : '#22c55e',
                    color: '#fff',
                  }}>
                    {currentBudget.usage_percent > 80 ? 'WARNING' : 'HEALTHY'}
                  </span>
                </div>
                <div className="forge-skill-meta">
                  <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Max Tokens</div>
                      <div style={{ fontWeight: 700 }}>{currentBudget.max_tokens.toLocaleString()}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Current</div>
                      <div style={{ fontWeight: 700, color: '#3b82f6' }}>{currentBudget.current_tokens.toLocaleString()}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Remaining</div>
                      <div style={{ fontWeight: 700, color: '#22c55e' }}>{currentBudget.remaining.toLocaleString()}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Usage</div>
                      <div style={{ fontWeight: 700, color: currentBudget.usage_percent > 80 ? '#ef4444' : '#4f6ef7' }}>
                        {currentBudget.usage_percent.toFixed(1)}%
                      </div>
                    </div>
                  </div>
                  <div style={{ width: '100%', background: '#e5e7eb', borderRadius: 4, marginTop: 12, height: 10 }}>
                    <div style={{
                      width: `${currentBudget.usage_percent}%`,
                      background: currentBudget.usage_percent > 80
                        ? '#ef4444'
                        : currentBudget.usage_percent > 50
                          ? '#f59e0b'
                          : '#22c55e',
                      height: '100%',
                      borderRadius: 4,
                    }} />
                  </div>
                  <div style={{ marginTop: 8 }}>
                    {currentBudget.auto_compress ? (
                      <span className="dashboard-badge active">Auto-Compress</span>
                    ) : (
                      <span className="dashboard-badge inactive">Manual</span>
                    )}
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

export default ContextCompressorPanel;