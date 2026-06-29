import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#0d9488',
  secondary: '#5eead4',
  bg: '#f0fdfa',
  border: '#99f6e4',
  accent: '#ccfbf1',
  text: '#134e4a',
};

const EVIDENCE_TYPES = ['observation', 'deduction', 'counter_example', 'corroboration', 'experimental', 'analogical'];
const TEST_OUTCOMES = ['pass', 'fail', 'inconclusive', 'partial'];

interface HypothesisEngineStats {
  total_sessions: number;
  total_hypotheses: number;
  total_tests: number;
  avg_confidence: number;
}

export const HypothesisEnginePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<HypothesisEngineStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'session' | 'evidence' | 'evaluate'>('overview');

  // Create session form
  const [sessionForm, setSessionForm] = useState({ topic: '', description: '' });

  // Propose hypothesis form
  const [proposeForm, setProposeForm] = useState({
    session_id: '', statement: '', rationale: '', confidence: 0.5,
  });

  // Add evidence form
  const [evidenceForm, setEvidenceForm] = useState({
    session_id: '', hypothesis_id: '', description: '', evidence_type: 'observation', weight: 0.5, supports: true,
  });

  // Design test form
  const [testDesignForm, setTestDesignForm] = useState({
    session_id: '', hypothesis_id: '', description: '', expected_result: '',
  });

  // Run test form
  const [runTestForm, setRunTestForm] = useState({
    session_id: '', hypothesis_id: '', test_id: '', actual_result: '', outcome: 'pass', confidence: '',
  });

  // Refine form
  const [refineForm, setRefineForm] = useState({
    session_id: '', hypothesis_id: '', new_statement: '', new_rationale: '',
  });

  // Evaluate form
  const [evalForm, setEvalForm] = useState({ session_id: '', hypothesis_id: '' });
  const [evaluationResult, setEvaluationResult] = useState<any>(null);
  const [compareResult, setCompareResult] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.hypothesisEngine.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load hypothesis engine data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreateSession = async () => {
    if (!sessionForm.topic.trim()) return;
    try {
      await api.hypothesisEngine.createSession({
        topic: sessionForm.topic.trim(),
        description: sessionForm.description || undefined,
      });
      toast.success(`Session "${sessionForm.topic}" created successfully`);
      setSessionForm({ topic: '', description: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePropose = async () => {
    if (!proposeForm.session_id.trim() || !proposeForm.statement.trim()) return;
    try {
      await api.hypothesisEngine.propose({
        session_id: proposeForm.session_id.trim(),
        statement: proposeForm.statement.trim(),
        rationale: proposeForm.rationale || undefined,
        confidence: proposeForm.confidence,
      });
      toast.success('Hypothesis proposed successfully');
      setProposeForm({ session_id: '', statement: '', rationale: '', confidence: 0.5 });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddEvidence = async () => {
    if (!evidenceForm.session_id.trim() || !evidenceForm.hypothesis_id.trim() || !evidenceForm.description.trim()) return;
    try {
      await api.hypothesisEngine.addEvidence({
        session_id: evidenceForm.session_id.trim(),
        hypothesis_id: evidenceForm.hypothesis_id.trim(),
        description: evidenceForm.description.trim(),
        evidence_type: evidenceForm.evidence_type,
        weight: evidenceForm.weight,
        supports: evidenceForm.supports,
      });
      toast.success('Evidence added successfully');
      setEvidenceForm({ session_id: '', hypothesis_id: '', description: '', evidence_type: 'observation', weight: 0.5, supports: true });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDesignTest = async () => {
    if (!testDesignForm.session_id.trim() || !testDesignForm.hypothesis_id.trim() || !testDesignForm.description.trim()) return;
    try {
      await api.hypothesisEngine.designTest({
        session_id: testDesignForm.session_id.trim(),
        hypothesis_id: testDesignForm.hypothesis_id.trim(),
        description: testDesignForm.description.trim(),
        expected_result: testDesignForm.expected_result || '',
      });
      toast.success('Test designed successfully');
      setTestDesignForm({ session_id: '', hypothesis_id: '', description: '', expected_result: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRunTest = async () => {
    if (!runTestForm.session_id.trim() || !runTestForm.hypothesis_id.trim() || !runTestForm.test_id.trim()) return;
    try {
      await api.hypothesisEngine.runTest({
        session_id: runTestForm.session_id.trim(),
        hypothesis_id: runTestForm.hypothesis_id.trim(),
        test_id: runTestForm.test_id.trim(),
        actual_result: runTestForm.actual_result || '',
        outcome: runTestForm.outcome,
        confidence: runTestForm.confidence ? Number(runTestForm.confidence) : undefined,
      });
      toast.success('Test executed successfully');
      setRunTestForm({ session_id: '', hypothesis_id: '', test_id: '', actual_result: '', outcome: 'pass', confidence: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRefine = async () => {
    if (!refineForm.session_id.trim() || !refineForm.hypothesis_id.trim() || !refineForm.new_statement.trim()) return;
    try {
      await api.hypothesisEngine.refine({
        session_id: refineForm.session_id.trim(),
        hypothesis_id: refineForm.hypothesis_id.trim(),
        new_statement: refineForm.new_statement.trim(),
        new_rationale: refineForm.new_rationale || undefined,
      });
      toast.success('Hypothesis refined successfully');
      setRefineForm({ session_id: '', hypothesis_id: '', new_statement: '', new_rationale: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleEvaluate = async () => {
    if (!evalForm.session_id.trim() || !evalForm.hypothesis_id.trim()) return;
    try {
      const result = await api.hypothesisEngine.evaluate(evalForm.session_id.trim(), evalForm.hypothesis_id.trim());
      setEvaluationResult(result);
      toast.success('Evaluation complete');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCompare = async () => {
    if (!evalForm.session_id.trim()) return;
    try {
      const result = await api.hypothesisEngine.compare(evalForm.session_id.trim());
      setCompareResult(result);
      toast.success('Comparison complete');
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🔬 Hypothesis Engine</h2>
          <p className="panel-subtitle">Scientific-method reasoning with hypothesis testing and refinement</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading hypothesis engine...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🔬 Hypothesis Engine</h2>
        <p className="panel-subtitle">Scientific-method reasoning with hypothesis testing and refinement</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_sessions}</span><span className="stat-label">Total Sessions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_hypotheses}</span><span className="stat-label">Total Hypotheses</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_tests}</span><span className="stat-label">Total Tests</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{(stats.avg_confidence * 100).toFixed(1)}%</span><span className="stat-label">Avg Confidence</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'session', 'evidence', 'evaluate'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
            style={activeSection === s ? { background: themeColors.primary, borderColor: themeColors.primary } : {}}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Hypothesis Engine Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Sessions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_sessions}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Hypotheses</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_hypotheses}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Tests Run</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_tests}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Confidence</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{(stats.avg_confidence * 100).toFixed(1)}%</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Session */}
      {activeSection === 'session' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create Hypothesis Session</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Topic *</label>
              <input
                type="text"
                value={sessionForm.topic}
                onChange={e => setSessionForm(f => ({ ...f, topic: e.target.value }))}
                placeholder="e.g., Climate Change Impact Analysis"
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={3}
                value={sessionForm.description}
                onChange={e => setSessionForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe the session scope and purpose..."
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleCreateSession}
              disabled={!sessionForm.topic.trim()}
            >
              Create Session
            </button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 24 }}>Propose Hypothesis</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Session ID *</label>
              <input
                type="text"
                value={proposeForm.session_id}
                onChange={e => setProposeForm(f => ({ ...f, session_id: e.target.value }))}
                placeholder="Enter session ID"
              />
            </div>
            <div className="form-group">
              <label>Statement *</label>
              <textarea
                rows={3}
                value={proposeForm.statement}
                onChange={e => setProposeForm(f => ({ ...f, statement: e.target.value }))}
                placeholder="e.g., If we increase system memory, response time will improve by 20%"
              />
            </div>
            <div className="form-group">
              <label>Rationale</label>
              <textarea
                rows={2}
                value={proposeForm.rationale}
                onChange={e => setProposeForm(f => ({ ...f, rationale: e.target.value }))}
                placeholder="Why do you believe this hypothesis?"
              />
            </div>
            <div className="form-group">
              <label>Confidence: {proposeForm.confidence.toFixed(1)}</label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={proposeForm.confidence}
                onChange={e => setProposeForm(f => ({ ...f, confidence: parseFloat(e.target.value) }))}
                style={{ width: '100%' }}
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handlePropose}
              disabled={!proposeForm.session_id.trim() || !proposeForm.statement.trim()}
            >
              Propose Hypothesis
            </button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 24 }}>Design Test</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Session ID *</label>
                <input
                  type="text"
                  value={testDesignForm.session_id}
                  onChange={e => setTestDesignForm(f => ({ ...f, session_id: e.target.value }))}
                  placeholder="Session ID"
                />
              </div>
              <div className="form-group">
                <label>Hypothesis ID *</label>
                <input
                  type="text"
                  value={testDesignForm.hypothesis_id}
                  onChange={e => setTestDesignForm(f => ({ ...f, hypothesis_id: e.target.value }))}
                  placeholder="Hypothesis ID"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Test Description *</label>
              <textarea
                rows={3}
                value={testDesignForm.description}
                onChange={e => setTestDesignForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe the test procedure..."
              />
            </div>
            <div className="form-group">
              <label>Expected Result</label>
              <input
                type="text"
                value={testDesignForm.expected_result}
                onChange={e => setTestDesignForm(f => ({ ...f, expected_result: e.target.value }))}
                placeholder="What do you expect to observe?"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleDesignTest}
              disabled={!testDesignForm.session_id.trim() || !testDesignForm.hypothesis_id.trim() || !testDesignForm.description.trim()}
            >
              Design Test
            </button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 24 }}>Run Test</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Session ID *</label>
                <input
                  type="text"
                  value={runTestForm.session_id}
                  onChange={e => setRunTestForm(f => ({ ...f, session_id: e.target.value }))}
                  placeholder="Session ID"
                />
              </div>
              <div className="form-group">
                <label>Hypothesis ID *</label>
                <input
                  type="text"
                  value={runTestForm.hypothesis_id}
                  onChange={e => setRunTestForm(f => ({ ...f, hypothesis_id: e.target.value }))}
                  placeholder="Hypothesis ID"
                />
              </div>
              <div className="form-group">
                <label>Test ID *</label>
                <input
                  type="text"
                  value={runTestForm.test_id}
                  onChange={e => setRunTestForm(f => ({ ...f, test_id: e.target.value }))}
                  placeholder="Test ID"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Actual Result</label>
              <textarea
                rows={2}
                value={runTestForm.actual_result}
                onChange={e => setRunTestForm(f => ({ ...f, actual_result: e.target.value }))}
                placeholder="What actually happened?"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Outcome</label>
                <select value={runTestForm.outcome} onChange={e => setRunTestForm(f => ({ ...f, outcome: e.target.value }))}>
                  {TEST_OUTCOMES.map(o => (
                    <option key={o} value={o}>{o}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Confidence (0-1)</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={runTestForm.confidence}
                  onChange={e => setRunTestForm(f => ({ ...f, confidence: e.target.value }))}
                  placeholder="0.0 - 1.0"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleRunTest}
              disabled={!runTestForm.session_id.trim() || !runTestForm.hypothesis_id.trim() || !runTestForm.test_id.trim()}
            >
              Run Test
            </button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 24 }}>Refine Hypothesis</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Session ID *</label>
                <input
                  type="text"
                  value={refineForm.session_id}
                  onChange={e => setRefineForm(f => ({ ...f, session_id: e.target.value }))}
                  placeholder="Session ID"
                />
              </div>
              <div className="form-group">
                <label>Hypothesis ID *</label>
                <input
                  type="text"
                  value={refineForm.hypothesis_id}
                  onChange={e => setRefineForm(f => ({ ...f, hypothesis_id: e.target.value }))}
                  placeholder="Hypothesis ID"
                />
              </div>
            </div>
            <div className="form-group">
              <label>New Statement *</label>
              <textarea
                rows={3}
                value={refineForm.new_statement}
                onChange={e => setRefineForm(f => ({ ...f, new_statement: e.target.value }))}
                placeholder="Updated hypothesis statement based on test results..."
              />
            </div>
            <div className="form-group">
              <label>New Rationale</label>
              <textarea
                rows={2}
                value={refineForm.new_rationale}
                onChange={e => setRefineForm(f => ({ ...f, new_rationale: e.target.value }))}
                placeholder="Updated reasoning..."
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleRefine}
              disabled={!refineForm.session_id.trim() || !refineForm.hypothesis_id.trim() || !refineForm.new_statement.trim()}
            >
              Refine Hypothesis
            </button>
          </div>
        </div>
      )}

      {/* Evidence */}
      {activeSection === 'evidence' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Add Evidence</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Session ID *</label>
                <input
                  type="text"
                  value={evidenceForm.session_id}
                  onChange={e => setEvidenceForm(f => ({ ...f, session_id: e.target.value }))}
                  placeholder="Session ID"
                />
              </div>
              <div className="form-group">
                <label>Hypothesis ID *</label>
                <input
                  type="text"
                  value={evidenceForm.hypothesis_id}
                  onChange={e => setEvidenceForm(f => ({ ...f, hypothesis_id: e.target.value }))}
                  placeholder="Hypothesis ID"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Description *</label>
              <textarea
                rows={3}
                value={evidenceForm.description}
                onChange={e => setEvidenceForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe the evidence..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Evidence Type</label>
                <select value={evidenceForm.evidence_type} onChange={e => setEvidenceForm(f => ({ ...f, evidence_type: e.target.value }))}>
                  {EVIDENCE_TYPES.map(t => (
                    <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Weight: {evidenceForm.weight.toFixed(1)}</label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={evidenceForm.weight}
                  onChange={e => setEvidenceForm(f => ({ ...f, weight: parseFloat(e.target.value) }))}
                  style={{ width: '100%' }}
                />
              </div>
            </div>
            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={evidenceForm.supports}
                  onChange={e => setEvidenceForm(f => ({ ...f, supports: e.target.checked }))}
                />
                {' '}Supports Hypothesis
              </label>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleAddEvidence}
              disabled={!evidenceForm.session_id.trim() || !evidenceForm.hypothesis_id.trim() || !evidenceForm.description.trim()}
            >
              Add Evidence
            </button>
          </div>
        </div>
      )}

      {/* Evaluate */}
      {activeSection === 'evaluate' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Evaluate Hypothesis</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Session ID *</label>
                <input
                  type="text"
                  value={evalForm.session_id}
                  onChange={e => setEvalForm(f => ({ ...f, session_id: e.target.value }))}
                  placeholder="Session ID"
                />
              </div>
              <div className="form-group">
                <label>Hypothesis ID *</label>
                <input
                  type="text"
                  value={evalForm.hypothesis_id}
                  onChange={e => setEvalForm(f => ({ ...f, hypothesis_id: e.target.value }))}
                  placeholder="Hypothesis ID"
                />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className="btn-primary"
                style={{ background: themeColors.primary }}
                onClick={handleEvaluate}
                disabled={!evalForm.session_id.trim() || !evalForm.hypothesis_id.trim()}
              >
                Evaluate
              </button>
              <button
                className="btn-primary"
                style={{ background: themeColors.secondary, color: themeColors.text }}
                onClick={handleCompare}
                disabled={!evalForm.session_id.trim()}
              >
                Compare All
              </button>
            </div>
          </div>

          {evaluationResult && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <h4 style={{ color: themeColors.text }}>Evaluation Result</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(evaluationResult, null, 2)}</pre>
            </div>
          )}

          {compareResult && (
            <div style={{ padding: '16px', background: themeColors.accent, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <h4 style={{ color: themeColors.text }}>Comparison Result</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(compareResult, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default HypothesisEnginePanel;