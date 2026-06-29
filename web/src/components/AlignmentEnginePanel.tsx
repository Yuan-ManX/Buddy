import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#059669',
  secondary: '#6ee7b7',
  bg: '#ecfdf5',
  border: '#a7f3d0',
  accent: '#d1fae5',
  text: '#064e3b',
};

const DIMENSIONS = [
  'values', 'communication_style', 'expertise_level', 'decision_making',
  'risk_tolerance', 'work_style', 'learning_preference', 'feedback_style',
  'priorities', 'goals', 'boundaries', 'tone', 'cultural_context', 'ethical_stance',
];

const SOURCES = ['explicit', 'inferred', 'observed', 'calibrated', 'default'];

export const AlignmentEnginePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'profile' | 'trait' | 'check'>('overview');

  // Profiles
  const [profiles, setProfiles] = useState<any[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<any | null>(null);

  // Create profile form
  const [createProfileForm, setCreateProfileForm] = useState({ user_id: '', agent_id: '' });

  // Trait form
  const [traitForm, setTraitForm] = useState({
    dimension: 'values', value: '', source: 'explicit', evidence: '', confidence: '',
  });

  // Signal form
  const [signalForm, setSignalForm] = useState({
    dimension: 'values', observed_value: '', evidence: '', weight: '1',
  });

  // Check form
  const [checkForm, setCheckForm] = useState({
    proposed_action: '', action_description: '', dimension: 'values',
  });
  const [checkResult, setCheckResult] = useState<any>(null);

  // Summary and process results
  const [summary, setSummary] = useState<any>(null);
  const [processResult, setProcessResult] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, p] = await Promise.all([
        api.alignmentEngine.stats(),
        api.alignmentEngine.listProfiles(),
      ]);
      setStats(s);
      setProfiles(Array.isArray(p) ? p : (p?.profiles ?? p?.items ?? []));
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load alignment engine data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreateProfile = async () => {
    if (!createProfileForm.user_id.trim() || !createProfileForm.agent_id.trim()) return;
    try {
      await api.alignmentEngine.createProfile({
        user_id: createProfileForm.user_id.trim(),
        agent_id: createProfileForm.agent_id.trim(),
      });
      toast.success(`Profile created for "${createProfileForm.user_id}"`);
      setCreateProfileForm({ user_id: '', agent_id: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSelectProfile = async (id: string) => {
    try {
      const profile = await api.alignmentEngine.getProfile(id);
      setSelectedProfile(profile);
      try {
        const s = await api.alignmentEngine.getSummary(id);
        setSummary(s);
      } catch {
        setSummary(null);
      }
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSetTrait = async () => {
    if (!selectedProfile || !traitForm.value.trim()) return;
    try {
      await api.alignmentEngine.setTrait(selectedProfile.profile_id, {
        dimension: traitForm.dimension,
        value: traitForm.value.trim(),
        source: traitForm.source,
        evidence: traitForm.evidence.trim() || undefined,
        confidence: traitForm.confidence ? Number(traitForm.confidence) : undefined,
      });
      toast.success(`Trait "${traitForm.dimension}" updated`);
      setTraitForm({
        dimension: 'values', value: '', source: 'explicit', evidence: '', confidence: '',
      });
      handleSelectProfile(selectedProfile.profile_id);
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordSignal = async () => {
    if (!selectedProfile || !signalForm.observed_value.trim()) return;
    try {
      await api.alignmentEngine.recordSignal(selectedProfile.profile_id, {
        dimension: signalForm.dimension,
        observed_value: signalForm.observed_value.trim(),
        evidence: signalForm.evidence.trim() || '',
        weight: Number(signalForm.weight) || 1,
      });
      toast.success(`Signal recorded for "${signalForm.dimension}"`);
      setSignalForm({
        dimension: 'values', observed_value: '', evidence: '', weight: '1',
      });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleProcessSignals = async () => {
    if (!selectedProfile) return;
    try {
      const result = await api.alignmentEngine.processSignals(selectedProfile.profile_id);
      setProcessResult(result);
      toast.success('Signals processed');
      handleSelectProfile(selectedProfile.profile_id);
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCheckAlignment = async () => {
    if (!selectedProfile || !checkForm.proposed_action.trim()) return;
    try {
      const result = await api.alignmentEngine.checkAlignment(selectedProfile.profile_id, {
        proposed_action: checkForm.proposed_action.trim(),
        action_description: checkForm.action_description.trim() || undefined,
        dimension: checkForm.dimension,
      });
      setCheckResult(result);
    } catch (e: any) { toast.error(e.message); }
  };

  const scoreColor = (score: number) => {
    if (score >= 0.6) return '#16a34a';
    if (score >= 0.4) return '#ca8a04';
    return '#dc2626';
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🎯 Alignment Engine</h2>
          <p className="panel-subtitle">Manage agent alignment profiles and traits</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading alignment engine...</span></div>
      </div>
    );
  }

  return (
    <div className="forge-panel" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2 style={{ color: themeColors.primary }}>🎯 Alignment Engine</h2>
        <p className="panel-subtitle">Manage agent alignment profiles and traits</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'profile', 'trait', 'check'] as const).map(s => (
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
        <div className="forge-section">
          <div className="forge-grid">
            <div className="forge-card forge-stat">
              <div style={{ fontWeight: 600, color: themeColors.text }}>Total Profiles</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_profiles ?? 0}</div>
            </div>
            <div className="forge-card forge-stat">
              <div style={{ fontWeight: 600, color: themeColors.text }}>Total Traits</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_traits ?? 0}</div>
            </div>
            <div className="forge-card forge-stat">
              <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Alignment</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>
                {typeof stats.avg_alignment === 'number' ? stats.avg_alignment.toFixed(3) : (stats.avg_alignment ?? '-')}
              </div>
            </div>
            <div className="forge-card forge-stat">
              <div style={{ fontWeight: 600, color: themeColors.text }}>Total Signals</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_signals ?? 0}</div>
            </div>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 16 }}>Profiles</h3>
          <table className="forge-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: themeColors.accent }}>
                <th style={{ padding: '8px', textAlign: 'left', color: themeColors.text }}>Profile ID</th>
                <th style={{ padding: '8px', textAlign: 'left', color: themeColors.text }}>User ID</th>
                <th style={{ padding: '8px', textAlign: 'left', color: themeColors.text }}>Agent ID</th>
                <th style={{ padding: '8px', textAlign: 'left', color: themeColors.text }}>Overall Alignment</th>
                <th style={{ padding: '8px', textAlign: 'left', color: themeColors.text }}>Traits Count</th>
              </tr>
            </thead>
            <tbody>
              {profiles.length === 0 && (
                <tr><td colSpan={5} style={{ padding: '8px', color: themeColors.text }}>No profiles yet.</td></tr>
              )}
              {profiles.map(p => (
                <tr key={p.profile_id} style={{ borderTop: `1px solid ${themeColors.border}` }}>
                  <td style={{ padding: '8px', color: themeColors.text }}>{p.profile_id}</td>
                  <td style={{ padding: '8px', color: themeColors.text }}>{p.user_id}</td>
                  <td style={{ padding: '8px', color: themeColors.text }}>{p.agent_id}</td>
                  <td style={{ padding: '8px', color: themeColors.text }}>{p.overall_alignment ?? '-'}</td>
                  <td style={{ padding: '8px', color: themeColors.text }}>{p.traits_count ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Profile */}
      {activeSection === 'profile' && (
        <div className="forge-section">
          <h3 style={{ color: themeColors.text }}>Create Profile</h3>
          <div className="forge-form">
            <div className="form-row">
              <div className="form-group">
                <label>User ID *</label>
                <input
                  className="forge-input"
                  type="text"
                  value={createProfileForm.user_id}
                  onChange={e => setCreateProfileForm(f => ({ ...f, user_id: e.target.value }))}
                  placeholder="e.g. user-123"
                />
              </div>
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  className="forge-input"
                  type="text"
                  value={createProfileForm.agent_id}
                  onChange={e => setCreateProfileForm(f => ({ ...f, agent_id: e.target.value }))}
                  placeholder="e.g. agent-abc"
                />
              </div>
            </div>
            <button
              className="forge-btn"
              style={{ background: themeColors.primary }}
              onClick={handleCreateProfile}
              disabled={!createProfileForm.user_id.trim() || !createProfileForm.agent_id.trim()}
            >
              Create Profile
            </button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 16 }}>Profiles</h3>
          <table className="forge-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: themeColors.accent }}>
                <th style={{ padding: '8px', textAlign: 'left', color: themeColors.text }}>Profile ID</th>
                <th style={{ padding: '8px', textAlign: 'left', color: themeColors.text }}>User ID</th>
                <th style={{ padding: '8px', textAlign: 'left', color: themeColors.text }}>Agent ID</th>
                <th style={{ padding: '8px' }}></th>
              </tr>
            </thead>
            <tbody>
              {profiles.length === 0 && (
                <tr><td colSpan={4} style={{ padding: '8px', color: themeColors.text }}>No profiles yet.</td></tr>
              )}
              {profiles.map(p => (
                <tr key={p.profile_id} style={{ borderTop: `1px solid ${themeColors.border}` }}>
                  <td style={{ padding: '8px', color: themeColors.text }}>{p.profile_id}</td>
                  <td style={{ padding: '8px', color: themeColors.text }}>{p.user_id}</td>
                  <td style={{ padding: '8px', color: themeColors.text }}>{p.agent_id}</td>
                  <td style={{ padding: '8px' }}>
                    <button className="forge-btn" style={{ background: themeColors.secondary }} onClick={() => handleSelectProfile(p.profile_id)}>
                      Select
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {selectedProfile && (
            <div className="forge-card" style={{ marginTop: 16 }}>
              <h4 style={{ color: themeColors.text }}>Profile Details</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 8 }}>
                <div><strong style={{ color: themeColors.text }}>Profile ID:</strong> <span style={{ color: themeColors.text }}>{selectedProfile.profile_id}</span></div>
                <div><strong style={{ color: themeColors.text }}>User ID:</strong> <span style={{ color: themeColors.text }}>{selectedProfile.user_id}</span></div>
                <div><strong style={{ color: themeColors.text }}>Agent ID:</strong> <span style={{ color: themeColors.text }}>{selectedProfile.agent_id}</span></div>
                <div><strong style={{ color: themeColors.text }}>Overall Alignment:</strong> <span style={{ color: themeColors.primary }}>{selectedProfile.overall_alignment ?? '-'}</span></div>
                <div><strong style={{ color: themeColors.text }}>Traits Count:</strong> <span style={{ color: themeColors.text }}>{selectedProfile.traits_count ?? 0}</span></div>
                <div><strong style={{ color: themeColors.text }}>Version:</strong> <span style={{ color: themeColors.text }}>{selectedProfile.version ?? '-'}</span></div>
              </div>

              {summary && (
                <div style={{ marginTop: 12 }}>
                  <h5 style={{ color: themeColors.text }}>Summary</h5>
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(summary, null, 2)}</pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Trait */}
      {activeSection === 'trait' && (
        <div className="forge-section">
          {!selectedProfile ? (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, color: themeColors.text }}>
              Select a profile first in the Profile tab.
            </div>
          ) : (
            <>
              <h3 style={{ color: themeColors.text }}>Set Trait (Profile: {selectedProfile.profile_id})</h3>
              <div className="forge-form">
                <div className="form-row">
                  <div className="form-group">
                    <label>Dimension</label>
                    <select
                      className="forge-select"
                      value={traitForm.dimension}
                      onChange={e => setTraitForm(f => ({ ...f, dimension: e.target.value }))}
                    >
                      {DIMENSIONS.map(d => <option key={d} value={d}>{d.replace(/_/g, ' ')}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Value *</label>
                    <input
                      className="forge-input"
                      type="text"
                      value={traitForm.value}
                      onChange={e => setTraitForm(f => ({ ...f, value: e.target.value }))}
                      placeholder="e.g. concise"
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Source</label>
                    <select
                      className="forge-select"
                      value={traitForm.source}
                      onChange={e => setTraitForm(f => ({ ...f, source: e.target.value }))}
                    >
                      {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Confidence (0-1)</label>
                    <input
                      className="forge-input"
                      type="number"
                      min="0"
                      max="1"
                      step="0.05"
                      value={traitForm.confidence}
                      onChange={e => setTraitForm(f => ({ ...f, confidence: e.target.value }))}
                      placeholder="0.0 - 1.0"
                    />
                  </div>
                </div>
                <div className="form-group">
                  <label>Evidence</label>
                  <input
                    className="forge-input"
                    type="text"
                    value={traitForm.evidence}
                    onChange={e => setTraitForm(f => ({ ...f, evidence: e.target.value }))}
                    placeholder="Optional supporting evidence"
                  />
                </div>
                <button
                  className="forge-btn"
                  style={{ background: themeColors.primary }}
                  onClick={handleSetTrait}
                  disabled={!traitForm.value.trim()}
                >
                  Set Trait
                </button>
              </div>

              <h3 style={{ color: themeColors.text, marginTop: 16 }}>Record Signal</h3>
              <div className="forge-form">
                <div className="form-row">
                  <div className="form-group">
                    <label>Dimension</label>
                    <select
                      className="forge-select"
                      value={signalForm.dimension}
                      onChange={e => setSignalForm(f => ({ ...f, dimension: e.target.value }))}
                    >
                      {DIMENSIONS.map(d => <option key={d} value={d}>{d.replace(/_/g, ' ')}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Observed Value *</label>
                    <input
                      className="forge-input"
                      type="text"
                      value={signalForm.observed_value}
                      onChange={e => setSignalForm(f => ({ ...f, observed_value: e.target.value }))}
                      placeholder="Observed value"
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Evidence</label>
                    <input
                      className="forge-input"
                      type="text"
                      value={signalForm.evidence}
                      onChange={e => setSignalForm(f => ({ ...f, evidence: e.target.value }))}
                      placeholder="Supporting evidence"
                    />
                  </div>
                  <div className="form-group">
                    <label>Weight</label>
                    <input
                      className="forge-input"
                      type="number"
                      min="0"
                      step="0.1"
                      value={signalForm.weight}
                      onChange={e => setSignalForm(f => ({ ...f, weight: e.target.value }))}
                      placeholder="1"
                    />
                  </div>
                </div>
                <button
                  className="forge-btn"
                  style={{ background: themeColors.primary }}
                  onClick={handleRecordSignal}
                  disabled={!signalForm.observed_value.trim()}
                >
                  Record Signal
                </button>
              </div>

              <h3 style={{ color: themeColors.text, marginTop: 16 }}>Process Signals</h3>
              <button
                className="forge-btn"
                style={{ background: themeColors.secondary, color: themeColors.text }}
                onClick={handleProcessSignals}
              >
                Process Signals
              </button>

              {processResult && (
                <div className="forge-card" style={{ marginTop: 12 }}>
                  <h4 style={{ color: themeColors.text }}>Process Result</h4>
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(processResult, null, 2)}</pre>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Check */}
      {activeSection === 'check' && (
        <div className="forge-section">
          {!selectedProfile ? (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, color: themeColors.text }}>
              Select a profile first in the Profile tab.
            </div>
          ) : (
            <>
              <h3 style={{ color: themeColors.text }}>Check Alignment (Profile: {selectedProfile.profile_id})</h3>
              <div className="forge-form">
                <div className="form-group">
                  <label>Proposed Action *</label>
                  <input
                    className="forge-input"
                    type="text"
                    value={checkForm.proposed_action}
                    onChange={e => setCheckForm(f => ({ ...f, proposed_action: e.target.value }))}
                    placeholder="e.g. send_marketing_email"
                  />
                </div>
                <div className="form-group">
                  <label>Action Description</label>
                  <input
                    className="forge-input"
                    type="text"
                    value={checkForm.action_description}
                    onChange={e => setCheckForm(f => ({ ...f, action_description: e.target.value }))}
                    placeholder="Optional description"
                  />
                </div>
                <div className="form-group">
                  <label>Dimension</label>
                  <select
                    className="forge-select"
                    value={checkForm.dimension}
                    onChange={e => setCheckForm(f => ({ ...f, dimension: e.target.value }))}
                  >
                    {DIMENSIONS.map(d => <option key={d} value={d}>{d.replace(/_/g, ' ')}</option>)}
                  </select>
                </div>
                <button
                  className="forge-btn"
                  style={{ background: themeColors.primary }}
                  onClick={handleCheckAlignment}
                  disabled={!checkForm.proposed_action.trim()}
                >
                  Check Alignment
                </button>
              </div>

              {checkResult && (
                <div className="forge-card" style={{ marginTop: 16 }}>
                  <h4 style={{ color: themeColors.text }}>Check Result</h4>
                  <div style={{ marginBottom: 8 }}>
                    <strong style={{ color: themeColors.text }}>Alignment Score: </strong>
                    <span style={{ color: scoreColor(Number(checkResult.alignment_score) || 0), fontWeight: 700 }}>
                      {checkResult.alignment_score ?? '-'}
                    </span>
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    <strong style={{ color: themeColors.text }}>Recommended Action: </strong>
                    <span style={{ color: themeColors.text }}>{checkResult.recommended_action ?? '-'}</span>
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    <strong style={{ color: themeColors.text }}>Reasoning: </strong>
                    <span style={{ color: themeColors.text }}>{checkResult.reasoning ?? '-'}</span>
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    <strong style={{ color: themeColors.text }}>Conflicts: </strong>
                    <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(checkResult.conflicts ?? [], null, 2)}</pre>
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    <strong style={{ color: themeColors.text }}>Suggestions: </strong>
                    <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(checkResult.suggestions ?? [], null, 2)}</pre>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default AlignmentEnginePanel;
