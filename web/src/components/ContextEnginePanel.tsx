import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

interface ContextStats {
  assembler: { total_assemblies: number; avg_tokens: number; total_sources: number };
  compressor: { total_compressions: number; avg_ratio: number; tokens_saved: number; by_strategy: Record<string, number> };
  injector: { total_injections: number; avg_elements: number };
  window: { total_entries: number; active_window_size: number; max_window_size: number };
}

export const ContextEnginePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<ContextStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'assemble' | 'compress' | 'inject'>('overview');

  // Assemble form
  const [assembleForm, setAssembleForm] = useState({
    system_prompt: '',
    sources: '',
    total_budget: '8000',
  });
  const [assembleResult, setAssembleResult] = useState<any>(null);

  // Compress form
  const [compressForm, setCompressForm] = useState({
    text: '',
    target_tokens: '4000',
    strategy: 'hybrid',
  });
  const [compressResult, setCompressResult] = useState<any>(null);

  // Inject form
  const [injectForm, setInjectForm] = useState({
    task: '',
    elements: '',
    template: '{task}\n\n{context}',
  });
  const [injectResult, setInjectResult] = useState<any>(null);

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch('/api/context/stats');
      const data = await res.json();
      setStats(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const handleAssemble = async () => {
    try {
      let sources = {};
      try {
        sources = JSON.parse(assembleForm.sources || '{}');
      } catch {}
      const res = await fetch('/api/context/assemble', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sources,
          system_prompt: assembleForm.system_prompt,
          total_budget: parseInt(assembleForm.total_budget) || 8000,
        }),
      });
      const data = await res.json();
      setAssembleResult(data);
      loadStats();
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  const handleCompress = async () => {
    try {
      const res = await fetch('/api/context/compress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: compressForm.text,
          target_tokens: parseInt(compressForm.target_tokens) || 4000,
          strategy: compressForm.strategy,
        }),
      });
      const data = await res.json();
      setCompressResult(data);
      loadStats();
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  const handleInject = async () => {
    try {
      let elements = [];
      try {
        elements = JSON.parse(injectForm.elements || '[]');
      } catch {}
      const res = await fetch('/api/context/inject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task: injectForm.task,
          elements,
          template: injectForm.template,
        }),
      });
      const data = await res.json();
      setInjectResult(data);
      loadStats();
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  if (loading) return <div className="panel loading">Loading context engine...</div>;

  return (
    <div className="panel context-panel">
      <div className="panel-header">
        <h2>Context Engine</h2>
        <span className="panel-badge">
          {stats ? `${stats.assembler?.total_assemblies || 0} assemblies` : 'Loading'}
        </span>
      </div>

      {error && <div className="panel-error">{error}</div>}

      <div className="panel-tabs">
        {(['overview', 'assemble', 'compress', 'inject'] as const).map((s) => (
          <button
            key={s}
            className={`panel-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      <div className="panel-content">
        {activeSection === 'overview' && stats && (
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{stats.assembler?.total_assemblies || 0}</div>
              <div className="stat-label">Total Assemblies</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.assembler?.avg_tokens || 0}</div>
              <div className="stat-label">Avg Tokens</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.compressor?.total_compressions || 0}</div>
              <div className="stat-label">Compressions</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{(stats.compressor?.avg_ratio || 0).toFixed(2)}x</div>
              <div className="stat-label">Avg Ratio</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.compressor?.tokens_saved || 0}</div>
              <div className="stat-label">Tokens Saved</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.injector?.total_injections || 0}</div>
              <div className="stat-label">Injections</div>
            </div>

            {stats.compressor?.by_strategy && (
              <div className="section-card full-width">
                <h3>Compression Strategies</h3>
                <div className="distribution-bars">
                  {Object.entries(stats.compressor.by_strategy).map(([k, v]) => (
                    <div key={k} className="dist-row">
                      <span className="dist-label">{k}</span>
                      <div className="dist-bar-container">
                        <div className="dist-bar" style={{ width: `${Math.min((Number(v) / Math.max(...Object.values(stats.compressor.by_strategy).map(Number)) || 1) * 100, 100)}%` }} />
                      </div>
                      <span className="dist-value">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {stats.window && (
              <div className="section-card full-width">
                <h3>Context Window</h3>
                <div className="stats-inline">
                  <span>Active: <strong>{stats.window.active_window_size}</strong> / {stats.window.max_window_size}</span>
                  <span>Total Entries: <strong>{stats.window.total_entries}</strong></span>
                </div>
              </div>
            )}
          </div>
        )}

        {activeSection === 'assemble' && (
          <div className="form-section">
            <h3>Assemble Context</h3>
            <div className="form-group">
              <label>System Prompt</label>
              <textarea value={assembleForm.system_prompt} onChange={e => setAssembleForm({ ...assembleForm, system_prompt: e.target.value })} placeholder="You are a helpful assistant..." rows={3} />
            </div>
            <div className="form-group">
              <label>Sources (JSON)</label>
              <textarea value={assembleForm.sources} onChange={e => setAssembleForm({ ...assembleForm, sources: e.target.value })} placeholder='{"memory": "...", "conversation": "..."}' rows={3} />
            </div>
            <div className="form-group">
              <label>Token Budget</label>
              <input type="number" value={assembleForm.total_budget} onChange={e => setAssembleForm({ ...assembleForm, total_budget: e.target.value })} />
            </div>
            <button className="btn-primary" onClick={handleAssemble}>Assemble</button>
            {assembleResult && (
              <div className="result-card">
                <div className="result-meta">
                  <span>Tokens: {assembleResult.token_count}</span>
                  <span>Budget Used: {JSON.stringify(assembleResult.budget_used)}</span>
                </div>
                <pre className="result-context">{assembleResult.context?.substring(0, 500)}{(assembleResult.context?.length || 0) > 500 ? '...' : ''}</pre>
              </div>
            )}
          </div>
        )}

        {activeSection === 'compress' && (
          <div className="form-section">
            <h3>Compress Context</h3>
            <div className="form-group">
              <label>Text to Compress</label>
              <textarea value={compressForm.text} onChange={e => setCompressForm({ ...compressForm, text: e.target.value })} placeholder="Paste text to compress..." rows={6} />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Target Tokens</label>
                <input type="number" value={compressForm.target_tokens} onChange={e => setCompressForm({ ...compressForm, target_tokens: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={compressForm.strategy} onChange={e => setCompressForm({ ...compressForm, strategy: e.target.value })}>
                  <option value="hybrid">Hybrid</option>
                  <option value="semantic">Semantic</option>
                  <option value="extractive">Extractive</option>
                  <option value="abstractive">Abstractive</option>
                </select>
              </div>
            </div>
            <button className="btn-primary" onClick={handleCompress}>Compress</button>
            {compressResult && (
              <div className="result-card">
                <div className="result-meta">
                  <span>Original: {compressResult.original_tokens} tokens</span>
                  <span>Compressed: {compressResult.compressed_tokens} tokens</span>
                  <span>Ratio: {compressResult.compression_ratio?.toFixed(2)}x</span>
                  <span>Quality: {compressResult.quality_score?.toFixed(2)}</span>
                </div>
                <pre className="result-context">{compressResult.compressed_text?.substring(0, 500)}</pre>
              </div>
            )}
          </div>
        )}

        {activeSection === 'inject' && (
          <div className="form-section">
            <h3>Inject Context into Prompt</h3>
            <div className="form-group">
              <label>Task / Prompt</label>
              <textarea value={injectForm.task} onChange={e => setInjectForm({ ...injectForm, task: e.target.value })} placeholder="The task to be performed..." rows={3} />
            </div>
            <div className="form-group">
              <label>Context Elements (JSON array)</label>
              <textarea value={injectForm.elements} onChange={e => setInjectForm({ ...injectForm, elements: e.target.value })} placeholder='["Memory: ...", "Previous: ..."]' rows={3} />
            </div>
            <div className="form-group">
              <label>Template</label>
              <input type="text" value={injectForm.template} onChange={e => setInjectForm({ ...injectForm, template: e.target.value })} />
            </div>
            <button className="btn-primary" onClick={handleInject}>Inject</button>
            {injectResult && (
              <div className="result-card">
                <div className="result-meta">
                  <span>Elements Used: {injectResult.elements_used}</span>
                </div>
                <pre className="result-context">{injectResult.injected_text?.substring(0, 500)}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};