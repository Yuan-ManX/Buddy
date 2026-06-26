import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface ChainOfThoughtStats {
  total_reasoning_sessions: number;
  strategies_used: number;
  avg_confidence: number;
  avg_quality_score: number;
  total_thoughts_generated: number;
}

interface ReasonResult {
  conclusion: string;
  confidence: number;
  quality_scores: {
    logical_coherence: number;
    evidence_strength: number;
    completeness: number;
    clarity: number;
    overall: number;
  };
  uncertainties: string[];
  alternative_conclusions: string[];
}

interface ThoughtStep {
  step_number: number;
  type: string;
  content: string;
  confidence: number;
  evidence: string;
  assumptions: string;
}

interface QualityEvaluation {
  logical_coherence: number;
  evidence_strength: number;
  completeness: number;
  clarity: number;
  overall: number;
}

// ── Request helper ──

const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try {
      const parsed = JSON.parse(body);
      message = parsed.detail || parsed.error || body;
    } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Component ──

export const ChainOfThoughtPanel: React.FC = () => {
  const toast = useToast();

  const [stats, setStats] = useState<ChainOfThoughtStats | null>(null);
  const [trace, setTrace] = useState<ThoughtStep[]>([]);
  const [quality, setQuality] = useState<QualityEvaluation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'reason' | 'trace' | 'quality'>('overview');

  // Reason form
  const [reasonForm, setReasonForm] = useState({
    prompt: '',
    strategy: 'auto',
    max_steps: 10,
  });
  const [reasoning, setReasoning] = useState(false);
  const [reasonResult, setReasonResult] = useState<ReasonResult | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, t, q] = await Promise.all([
        request<ChainOfThoughtStats>('/chain-of-thought/stats').catch(() => null),
        request<ThoughtStep[]>('/chain-of-thought/trace').catch(() => []),
        request<QualityEvaluation>('/chain-of-thought/quality').catch(() => null),
      ]);
      setStats(s);
      setTrace(Array.isArray(t) ? t : (t as any)?.steps || []);
      setQuality(q);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load chain of thought data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleReason = async () => {
    if (!reasonForm.prompt.trim()) return;
    try {
      setReasoning(true);
      const result = await request<ReasonResult>('/chain-of-thought/reason', {
        method: 'POST',
        body: JSON.stringify({
          prompt: reasonForm.prompt,
          strategy: reasonForm.strategy,
          max_steps: reasonForm.max_steps,
        }),
      });
      setReasonResult(result);
      toast.success('Reasoning completed successfully');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setReasoning(false);
    }
  };

  // ── Progress bar helper ──

  const renderProgressBar = (label: string, value: number, max: number = 10) => {
    const pct = Math.min((value / max) * 100, 100);
    const color = pct >= 80 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#ef4444';
    return (
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{label}</span>
          <span style={{ fontSize: 13, fontWeight: 600, color }}>{value.toFixed(1)} / {max}</span>
        </div>
        <div style={{
          width: '100%',
          height: 8,
          background: 'var(--border-color)',
          borderRadius: 4,
          overflow: 'hidden',
        }}>
          <div style={{
            width: `${pct}%`,
            height: '100%',
            background: color,
            borderRadius: 4,
            transition: 'width 0.3s ease',
          }} />
        </div>
      </div>
    );
  };

  // ── Loading State ──

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Chain of Thought</h2>
          <p className="panel-subtitle">Step-by-step reasoning engine for complex problem solving</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading chain of thought data...</span>
        </div>
      </div>
    );
  }

  // ── Main Render ──

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Chain of Thought</h2>
        <p className="panel-subtitle">Step-by-step reasoning engine for complex problem solving</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_reasoning_sessions}</span>
              <span className="stat-label">Total Sessions</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#3b82f6' }}>{stats.strategies_used}</span>
              <span className="stat-label">Strategies Used</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#8b5cf6' }}>
                {(stats.avg_confidence * 100).toFixed(1)}%
              </span>
              <span className="stat-label">Avg Confidence</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#22c55e' }}>
                {stats.avg_quality_score.toFixed(1)}
              </span>
              <span className="stat-label">Avg Quality</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#06b6d4' }}>{stats.total_thoughts_generated}</span>
              <span className="stat-label">Thoughts Generated</span>
            </div>
          </div>
        </div>
      )}

      {/* Tab Bar */}
      <div className="tab-bar" style={{ margin: '16px 0' }}>
        {(['overview', 'reason', 'trace', 'quality'] as const).map(tab => (
          <button
            key={tab}
            className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Overview Tab ── */}
      {activeTab === 'overview' && (
        <div className="panel-section">
          <h3>Reasoning Overview</h3>
          {stats ? (
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value-large">{stats.total_reasoning_sessions}</div>
                <div className="stat-label">Total Reasoning Sessions</div>
              </div>
              <div className="stat-card">
                <div className="stat-value-large" style={{ color: '#3b82f6' }}>{stats.strategies_used}</div>
                <div className="stat-label">Strategies Used</div>
              </div>
              <div className="stat-card">
                <div className="stat-value-large" style={{ color: '#8b5cf6' }}>
                  {(stats.avg_confidence * 100).toFixed(1)}%
                </div>
                <div className="stat-label">Average Confidence</div>
              </div>
              <div className="stat-card">
                <div className="stat-value-large" style={{ color: '#22c55e' }}>
                  {stats.avg_quality_score.toFixed(1)}
                </div>
                <div className="stat-label">Average Quality Score</div>
              </div>
              <div className="stat-card">
                <div className="stat-value-large" style={{ color: '#06b6d4' }}>
                  {stats.total_thoughts_generated}
                </div>
                <div className="stat-label">Total Thoughts Generated</div>
              </div>
            </div>
          ) : (
            <div className="panel-empty">No statistics available yet. Run a reasoning task to get started.</div>
          )}

          {reasonResult && (
            <>
              <h3 style={{ marginTop: 24 }}>Latest Result</h3>
              <div className="forge-skill-card">
                <div className="forge-skill-header">
                  <div className="forge-skill-name">Conclusion</div>
                </div>
                <div className="forge-skill-meta">
                  <div style={{ marginBottom: 8, whiteSpace: 'pre-wrap' }}>{reasonResult.conclusion}</div>
                  <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                    <span>Confidence: <strong style={{ color: '#8b5cf6' }}>
                      {(reasonResult.confidence * 100).toFixed(1)}%
                    </strong></span>
                    <span>Overall Quality: <strong style={{ color: '#22c55e' }}>
                      {reasonResult.quality_scores.overall.toFixed(1)}/10
                    </strong></span>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Reason Tab ── */}
      {activeTab === 'reason' && (
        <div className="panel-section">
          <h3>Start Reasoning</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Prompt</label>
              <textarea
                rows={4}
                value={reasonForm.prompt}
                onChange={e => setReasonForm(f => ({ ...f, prompt: e.target.value }))}
                placeholder="Enter the problem or question you want to reason about..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Strategy</label>
                <select
                  value={reasonForm.strategy}
                  onChange={e => setReasonForm(f => ({ ...f, strategy: e.target.value }))}
                >
                  <option value="auto">Auto</option>
                  <option value="linear">Linear</option>
                  <option value="branching">Branching</option>
                  <option value="recursive">Recursive</option>
                  <option value="self_consistency">Self-Consistency</option>
                  <option value="tree_of_thought">Tree of Thought</option>
                </select>
              </div>
              <div className="form-group">
                <label>Max Steps</label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={reasonForm.max_steps}
                  onChange={e => setReasonForm(f => ({ ...f, max_steps: parseInt(e.target.value) || 10 }))}
                />
              </div>
            </div>
            <button
              className="btn-primary"
              onClick={handleReason}
              disabled={reasoning || !reasonForm.prompt.trim()}
            >
              {reasoning ? 'Reasoning...' : 'Start Reasoning'}
            </button>
          </div>

          {reasonResult && (
            <div style={{ marginTop: 24 }}>
              <h3>Reasoning Result</h3>

              <div className="forge-skill-card" style={{ marginBottom: 16 }}>
                <div className="forge-skill-header">
                  <div className="forge-skill-name">Conclusion</div>
                  <span className="dashboard-badge" style={{
                    background: '#8b5cf6',
                    color: '#fff',
                  }}>
                    Confidence: {(reasonResult.confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="forge-skill-meta">
                  <div style={{ whiteSpace: 'pre-wrap', marginBottom: 12 }}>{reasonResult.conclusion}</div>
                </div>
              </div>

              <h4>Quality Scores</h4>
              <div style={{ marginBottom: 16 }}>
                {renderProgressBar('Logical Coherence', reasonResult.quality_scores.logical_coherence)}
                {renderProgressBar('Evidence Strength', reasonResult.quality_scores.evidence_strength)}
                {renderProgressBar('Completeness', reasonResult.quality_scores.completeness)}
                {renderProgressBar('Clarity', reasonResult.quality_scores.clarity)}
                {renderProgressBar('Overall', reasonResult.quality_scores.overall)}
              </div>

              {reasonResult.uncertainties.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <h4>Uncertainties</h4>
                  <ul style={{ paddingLeft: 20, color: 'var(--text-secondary)' }}>
                    {reasonResult.uncertainties.map((u, i) => (
                      <li key={i} style={{ marginBottom: 4 }}>{u}</li>
                    ))}
                  </ul>
                </div>
              )}

              {reasonResult.alternative_conclusions.length > 0 && (
                <div>
                  <h4>Alternative Conclusions</h4>
                  <ul style={{ paddingLeft: 20, color: 'var(--text-secondary)' }}>
                    {reasonResult.alternative_conclusions.map((ac, i) => (
                      <li key={i} style={{ marginBottom: 4 }}>{ac}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Trace Tab ── */}
      {activeTab === 'trace' && (
        <div className="panel-section">
          <h3>Thought Trace ({trace.length} steps)</h3>
          {trace.length === 0 ? (
            <div className="panel-empty">No thought trace available. Run a reasoning task to generate steps.</div>
          ) : (
            <div className="forge-skill-list">
              {trace.map(step => (
                <div key={step.step_number} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">
                      Step {step.step_number}
                    </div>
                    <span className="dashboard-badge" style={{
                      background: '#3b82f6',
                      color: '#fff',
                    }}>
                      {step.type}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div style={{ whiteSpace: 'pre-wrap', marginBottom: 8 }}>{step.content}</div>
                    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 12 }}>
                      <span>
                        Confidence: <strong style={{ color: '#8b5cf6' }}>
                          {(step.confidence * 100).toFixed(1)}%
                        </strong>
                      </span>
                      {step.evidence && (
                        <span>
                          Evidence: <strong>{step.evidence}</strong>
                        </span>
                      )}
                      {step.assumptions && (
                        <span>
                          Assumptions: <strong>{step.assumptions}</strong>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Quality Tab ── */}
      {activeTab === 'quality' && (
        <div className="panel-section">
          <h3>Quality Evaluation</h3>
          {quality ? (
            <div style={{ maxWidth: 600 }}>
              {renderProgressBar('Logical Coherence', quality.logical_coherence)}
              {renderProgressBar('Evidence Strength', quality.evidence_strength)}
              {renderProgressBar('Completeness', quality.completeness)}
              {renderProgressBar('Clarity', quality.clarity)}
              {renderProgressBar('Overall Score', quality.overall)}
            </div>
          ) : (
            <div className="panel-empty">No quality evaluation available. Run a reasoning task to generate quality metrics.</div>
          )}
        </div>
      )}
    </div>
  );
};

export default ChainOfThoughtPanel;