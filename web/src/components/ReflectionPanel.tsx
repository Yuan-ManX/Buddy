import React, { useState, useEffect } from 'react';

interface ReflectionStats {
  total_reflections?: number;
  total_corrections?: number;
  active_agents?: number;
  total_errors?: number;
  total_corrections_agent?: number;
  average_quality_score?: number;
  confidence?: number;
  error_categories?: Record<string, number>;
}

interface ReflectionHistory {
  reflection_id: string;
  overall_score: number;
  error_count: number;
  status: string;
  created_at: number;
}

export const ReflectionPanel: React.FC = () => {
  const [stats, setStats] = useState<ReflectionStats | null>(null);
  const [history, setHistory] = useState<ReflectionHistory[]>([]);
  const [agentId, setAgentId] = useState('buddy-coder');
  const [showStart, setShowStart] = useState(false);
  const [formData, setFormData] = useState({ output: '', agent_id: 'buddy-coder' });
  const [reflectionId, setReflectionId] = useState('');
  const [showAssess, setShowAssess] = useState(false);
  const [assessForm, setAssessForm] = useState({ dimension: 'factual_accuracy', score: 0.8, reasoning: '' });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchStats();
    fetchHistory();
  }, [agentId]);

  const fetchStats = async () => {
    try {
      const res = await fetch(`/api/reflection/stats?agent_id=${agentId}`);
      const data = await res.json();
      if (data.agent_id) {
        setStats(data);
      } else {
        setStats(data);
      }
    } catch (e) { console.error('Failed to fetch reflection stats:', e); }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch(`/api/reflection/history/${agentId}`);
      const data = await res.json();
      setHistory(data.history || []);
    } catch (e) { console.error('Failed to fetch reflection history:', e); }
  };

  const startReflection = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/reflection/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      const data = await res.json();
      setReflectionId(data.reflection_id);
      setShowStart(false);
      fetchStats();
      fetchHistory();
    } catch (e) { console.error('Start failed:', e); }
    setLoading(false);
  };

  const assessQuality = async () => {
    setLoading(true);
    try {
      await fetch('/api/reflection/assess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reflection_id: reflectionId,
          scores: [{ ...assessForm }],
        }),
      });
      setShowAssess(false);
      fetchStats();
      fetchHistory();
    } catch (e) { console.error('Assess failed:', e); }
    setLoading(false);
  };

  const detectError = async (category: string) => {
    try {
      await fetch('/api/reflection/detect-error', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reflection_id: reflectionId,
          category,
          description: `Detected ${category.replace('_', ' ')}`,
          severity: 0.7,
          suggested_fix: 'Review and correct the output.',
        }),
      });
      fetchStats();
      fetchHistory();
    } catch (e) { console.error('Error detection failed:', e); }
  };

  const applyCorrection = async () => {
    try {
      await fetch('/api/reflection/correct', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reflection_id: reflectionId,
          corrected_output: 'Corrected output based on reflection.',
          improvement_summary: 'Applied self-correction.',
        }),
      });
      fetchStats();
      fetchHistory();
    } catch (e) { console.error('Correction failed:', e); }
  };

  const statusColor = (status: string) => {
    const map: Record<string, string> = {
      completed: '#16a34a', pending: '#f59e0b', analyzing: '#3b82f6',
      reflecting: '#8b5cf6', correcting: '#ec4899', failed: '#ef4444',
    };
    return map[status] || '#6b7280';
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Agent Reflection</h2>
          <p style={{ color: '#666', margin: '4px 0 0' }}>Self-reflection and self-correction loop for continuous improvement</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            value={agentId}
            onChange={e => setAgentId(e.target.value)}
            placeholder="Agent ID"
            style={{ padding: '6px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
          />
          <button onClick={() => setShowStart(true)} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
            + New Reflection
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <div style={{ flex: 1, background: '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a' }}>{stats.total_reflections ?? stats.total_reflections ?? 0}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Reflections</div>
          </div>
          <div style={{ flex: 1, background: '#eff6ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_corrections ?? stats.total_corrections_agent ?? 0}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Corrections</div>
          </div>
          <div style={{ flex: 1, background: '#fef3c7', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#d97706' }}>{stats.total_errors ?? 0}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Errors</div>
          </div>
          <div style={{ flex: 1, background: '#faf5ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#7c3aed' }}>{((stats.average_quality_score ?? 0) * 100).toFixed(0)}%</div>
            <div style={{ fontSize: 12, color: '#666' }}>Avg Quality</div>
          </div>
          <div style={{ flex: 1, background: '#fdf2f8', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#db2777' }}>{((stats.confidence ?? 1) * 100).toFixed(0)}%</div>
            <div style={{ fontSize: 12, color: '#666' }}>Confidence</div>
          </div>
        </div>
      )}

      {/* Error Categories */}
      {stats?.error_categories && Object.keys(stats.error_categories).length > 0 && (
        <div style={{ background: '#fff', borderRadius: 12, padding: 16, marginBottom: 24, border: '1px solid #e2e8f0' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Error Categories</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {Object.entries(stats.error_categories).map(([cat, count]) => (
              <span key={cat} style={{ background: '#fef2f2', color: '#ef4444', padding: '4px 12px', borderRadius: 8, fontSize: 12 }}>
                {cat.replace(/_/g, ' ')}: {count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Active Reflection Controls */}
      {reflectionId && (
        <div style={{ background: '#f8fafc', borderRadius: 12, padding: 16, marginBottom: 24, border: '2px solid #2563eb' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
            Active Reflection: <span style={{ fontFamily: 'monospace', color: '#2563eb' }}>{reflectionId}</span>
          </h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
            <button onClick={() => setShowAssess(true)} style={{ padding: '6px 14px', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
              Assess Quality
            </button>
            {['factual_error', 'logical_fallacy', 'hallucination', 'incomplete_answer', 'ambiguous'].map(cat => (
              <button key={cat} onClick={() => detectError(cat)} style={{ padding: '6px 14px', background: '#f59e0b', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
                + {cat.replace(/_/g, ' ')}
              </button>
            ))}
            <button onClick={applyCorrection} style={{ padding: '6px 14px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
              Apply Correction
            </button>
          </div>
        </div>
      )}

      {/* Start Reflection Modal */}
      {showStart && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: '#fff', borderRadius: 16, padding: 24, width: 500, maxHeight: '80vh', overflow: 'auto' }}>
            <h3 style={{ marginBottom: 16 }}>Start New Reflection</h3>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', fontSize: 13, marginBottom: 4 }}>Agent ID</label>
              <input value={formData.agent_id} onChange={e => setFormData({ ...formData, agent_id: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', fontSize: 13, marginBottom: 4 }}>Output to Reflect On</label>
              <textarea value={formData.output} onChange={e => setFormData({ ...formData, output: e.target.value })} rows={4} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', resize: 'vertical' }} />
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={() => setShowStart(false)} style={{ padding: '8px 16px', background: '#e5e7eb', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
              <button onClick={startReflection} disabled={loading} style={{ padding: '8px 16px', background: loading ? '#999' : '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>{loading ? 'Starting...' : 'Start'}</button>
            </div>
          </div>
        </div>
      )}

      {/* Assess Quality Modal */}
      {showAssess && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: '#fff', borderRadius: 16, padding: 24, width: 400 }}>
            <h3 style={{ marginBottom: 16 }}>Assess Quality</h3>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', fontSize: 13, marginBottom: 4 }}>Dimension</label>
              <select value={assessForm.dimension} onChange={e => setAssessForm({ ...assessForm, dimension: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }}>
                {['factual_accuracy', 'logical_coherence', 'completeness', 'relevance', 'clarity', 'actionability', 'safety', 'conciseness'].map(d => (
                  <option key={d} value={d}>{d.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', fontSize: 13, marginBottom: 4 }}>Score (0-1)</label>
              <input type="range" min="0" max="1" step="0.1" value={assessForm.score} onChange={e => setAssessForm({ ...assessForm, score: parseFloat(e.target.value) })} style={{ width: '100%' }} />
              <span style={{ fontSize: 13, color: '#666' }}>{assessForm.score}</span>
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', fontSize: 13, marginBottom: 4 }}>Reasoning</label>
              <input value={assessForm.reasoning} onChange={e => setAssessForm({ ...assessForm, reasoning: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} />
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={() => setShowAssess(false)} style={{ padding: '8px 16px', background: '#e5e7eb', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
              <button onClick={assessQuality} disabled={loading} style={{ padding: '8px 16px', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Assess</button>
            </div>
          </div>
        </div>
      )}

      {/* Reflection History */}
      <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0', fontWeight: 600 }}>Reflection History</div>
        <div style={{ maxHeight: 400, overflow: 'auto' }}>
          {history.length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>No reflections yet. Start one above.</div>
          ) : (
            history.map(r => (
              <div key={r.reflection_id} style={{ padding: '10px 16px', borderBottom: '1px solid #f3f4f6', display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ background: statusColor(r.status), color: '#fff', padding: '2px 8px', borderRadius: 6, fontSize: 11, textTransform: 'uppercase' }}>{r.status}</span>
                <span style={{ fontFamily: 'monospace', fontSize: 12, color: '#666' }}>{r.reflection_id}</span>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: 16, fontSize: 12, color: '#888' }}>
                  <span>Score: {(r.overall_score * 100).toFixed(0)}%</span>
                  <span>Errors: {r.error_count}</span>
                  <span>{new Date(r.created_at * 1000).toLocaleString()}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};