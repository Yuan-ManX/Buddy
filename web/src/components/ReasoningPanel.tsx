import React, { useState, useEffect } from 'react';

interface ReasoningTrace {
  trace_id: string;
  strategy: string;
  query: string;
  conclusion: string;
  confidence: number;
  step_count: number;
  completed_steps: number;
  created_at: number;
}

export const ReasoningPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [traces, setTraces] = useState<ReasoningTrace[]>([]);
  const [showStart, setShowStart] = useState(false);
  const [formData, setFormData] = useState({ agent_id: 'buddy-coder', query: '', strategy: 'chain_of_thought' });
  const [activeTraceId, setActiveTraceId] = useState('');
  const [stepContent, setStepContent] = useState('');
  const [hypothesisText, setHypothesisText] = useState('');
  const [conclusionText, setConclusionText] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchStats(); }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/reasoning/stats');
      setStats(await res.json());
    } catch (e) { console.error('Failed to fetch reasoning stats:', e); }
  };

  const startReasoning = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/reasoning/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      const data = await res.json();
      setActiveTraceId(data.trace_id);
      setShowStart(false);
      fetchStats();
    } catch (e) { console.error('Start failed:', e); }
    setLoading(false);
  };

  const addStep = async () => {
    if (!stepContent.trim()) return;
    try {
      const res = await fetch('/api/reasoning/add-step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trace_id: activeTraceId, content: stepContent, confidence: 0.8 }),
      });
      const data = await res.json();
      await fetch('/api/reasoning/complete-step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trace_id: activeTraceId, step_id: data.step_id }),
      });
      setStepContent('');
      fetchStats();
    } catch (e) { console.error('Add step failed:', e); }
  };

  const proposeHypothesis = async () => {
    if (!hypothesisText.trim()) return;
    await fetch('/api/reasoning/propose-hypothesis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trace_id: activeTraceId, statement: hypothesisText, confidence: 0.7 }),
    });
    setHypothesisText('');
    fetchStats();
  };

  const setConclusion = async () => {
    await fetch('/api/reasoning/set-conclusion', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trace_id: activeTraceId, conclusion: conclusionText, confidence: 0.85 }),
    });
    setConclusionText('');
    setActiveTraceId('');
    fetchStats();
  };

  const strategyColor = (s: string) => {
    const map: Record<string, string> = { chain_of_thought: '#3b82f6', tree_of_thought: '#8b5cf6', step_back: '#ec4899', decomposition: '#f59e0b', self_consistency: '#16a34a' };
    return map[s] || '#6b7280';
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Reasoning Engine</h2>
          <p style={{ color: '#666', margin: '4px 0 0' }}>Structured chain-of-thought reasoning with hypothesis testing and self-consistency</p>
        </div>
        <button onClick={() => setShowStart(true)} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
          + New Reasoning
        </button>
      </div>

      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <div style={{ flex: 1, background: '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a' }}>{stats.total_traces}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Traces</div>
          </div>
          <div style={{ flex: 1, background: '#eff6ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_steps}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Steps</div>
          </div>
          <div style={{ flex: 1, background: '#fef3c7', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#d97706' }}>{stats.active_agents || 0}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Active Agents</div>
          </div>
        </div>
      )}

      {/* Active Reasoning Session */}
      {activeTraceId && (
        <div style={{ background: '#fff', borderRadius: 12, padding: 16, marginBottom: 24, border: '2px solid #2563eb' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
            Active Trace: <span style={{ fontFamily: 'monospace', color: '#2563eb' }}>{activeTraceId}</span>
          </h3>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <input value={stepContent} onChange={e => setStepContent(e.target.value)} onKeyDown={e => e.key === 'Enter' && addStep()} placeholder="Add reasoning step..." style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }} />
            <button onClick={addStep} style={{ padding: '8px 16px', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', whiteSpace: 'nowrap' }}>Add Step</button>
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <input value={hypothesisText} onChange={e => setHypothesisText(e.target.value)} placeholder="Propose hypothesis..." style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }} />
            <button onClick={proposeHypothesis} style={{ padding: '8px 16px', background: '#f59e0b', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', whiteSpace: 'nowrap' }}>Hypothesize</button>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <input value={conclusionText} onChange={e => setConclusionText(e.target.value)} placeholder="Set conclusion..." style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }} />
            <button onClick={setConclusion} style={{ padding: '8px 16px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', whiteSpace: 'nowrap' }}>Conclude</button>
          </div>
        </div>
      )}

      {/* Start Modal */}
      {showStart && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: '#fff', borderRadius: 16, padding: 24, width: 500 }}>
            <h3 style={{ marginBottom: 16 }}>Start Reasoning Session</h3>
            <div style={{ marginBottom: 12 }}><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Agent ID</label><input value={formData.agent_id} onChange={e => setFormData({ ...formData, agent_id: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
            <div style={{ marginBottom: 12 }}><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Query</label><textarea value={formData.query} onChange={e => setFormData({ ...formData, query: e.target.value })} rows={3} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', resize: 'vertical' }} /></div>
            <div style={{ marginBottom: 12 }}><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Strategy</label>
              <select value={formData.strategy} onChange={e => setFormData({ ...formData, strategy: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }}>
                {['chain_of_thought', 'tree_of_thought', 'step_back', 'decomposition', 'self_consistency'].map(s => (
                  <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={() => setShowStart(false)} style={{ padding: '8px 16px', background: '#e5e7eb', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
              <button onClick={startReasoning} disabled={loading} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>{loading ? 'Starting...' : 'Start'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};