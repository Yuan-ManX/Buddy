import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: cyan for cognitive style transfer
const themeColors = {
  primary: '#0891b2',
  secondary: '#06b6d4',
  bg: '#ecfeff',
  border: '#a5f3fc',
  accent: '#cffafe',
  text: '#164e4a',
};

// Enum values must match backend StyleDimension / SourceType / FidelityMode / BlendStrategy / TransferStatus exactly (uppercase).
const STYLE_DIMENSIONS = ['ANALYTICAL', 'INTUITIVE', 'DEDUCTIVE', 'INDUCTIVE', 'ABDUCTIVE', 'LATERAL', 'CRITICAL', 'CREATIVE'];
const SOURCE_TYPES = ['DOMAIN', 'AGENT', 'TRACE', 'TEMPLATE'];
const FIDELITY_MODES = ['STRICT', 'ADAPTIVE', 'LOOSE'];
const BLEND_STRATEGIES = ['WEIGHTED', 'DOMINANT', 'MOSAIC', 'NOVEL'];
const TRANSFER_STATUS = ['PENDING', 'EXTRACTING', 'TRANSFERRING', 'VALIDATING', 'COMPLETED', 'FAILED'];

// Map a status value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  PENDING: '#9ca3af',
  EXTRACTING: '#0891b2',
  TRANSFERRING: '#0ea5e9',
  VALIDATING: '#6366f1',
  COMPLETED: '#16a34a',
  FAILED: '#dc2626',
};

export const CognitiveStyleTransferPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'style' | 'transfer'>('overview');

  // Styles / transfers / blends
  const [styles, setStyles] = useState<any[]>([]);
  const [transfers, setTransfers] = useState<any[]>([]);
  const [blends, setBlends] = useState<any[]>([]);
  const [fingerprintResult, setFingerprintResult] = useState<any>(null);
  const [matchResult, setMatchResult] = useState<any>(null);
  const [applyResult, setApplyResult] = useState<any>(null);

  // Extract style form
  const [styleForm, setStyleForm] = useState({
    source_id: '',
    source_type: 'DOMAIN',
    description: '',
  });

  // Create transfer form
  const [transferForm, setTransferForm] = useState({
    source_style_id: '',
    target_domain: '',
    fidelity: 'ADAPTIVE',
    description: '',
  });

  // Blend form
  const [blendForm, setBlendForm] = useState({
    style_ids: '',
    strategy: 'WEIGHTED',
    weights: '',
  });

  // Fingerprint / match / validate / apply action forms
  const [fingerprintForm, setFingerprintForm] = useState({ style_id: '' });
  const [matchForm, setMatchForm] = useState({ style_id: '', top_k: '5' });
  const [validateForm, setValidateForm] = useState({ transfer_id: '' });
  const [applyForm, setApplyForm] = useState({ style_id: '', problem_description: '' });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveStyleTransfer.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive style transfer stats');
    } finally {
      setLoading(false);
    }
  };

  const loadStyles = async () => {
    try {
      const result = await api.cognitiveStyleTransfer.listStyles();
      const list = Array.isArray(result) ? result : (result?.styles ?? []);
      setStyles(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load styles');
    }
  };

  const loadTransfers = async () => {
    try {
      const result = await api.cognitiveStyleTransfer.listTransfers();
      const list = Array.isArray(result) ? result : (result?.transfers ?? []);
      setTransfers(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load transfers');
    }
  };

  const loadBlends = async () => {
    try {
      const result = await api.cognitiveStyleTransfer.listBlends();
      const list = Array.isArray(result) ? result : (result?.blends ?? []);
      setBlends(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load blends');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadStyles();
      loadTransfers();
      loadBlends();
    }
  }, [activeSection]);

  const handleExtractStyle = async () => {
    if (!styleForm.source_id.trim()) {
      toast.error('Source ID is required');
      return;
    }
    const payload: any = {
      source_id: styleForm.source_id.trim(),
      source_type: styleForm.source_type,
    };
    if (styleForm.description.trim()) payload.description = styleForm.description.trim();
    try {
      await api.cognitiveStyleTransfer.extractStyle(payload);
      toast.success('Style extracted');
      setStyleForm({ source_id: '', source_type: 'DOMAIN', description: '' });
      await loadStyles();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreateTransfer = async () => {
    if (!transferForm.source_style_id.trim() || !transferForm.target_domain.trim()) {
      toast.error('Source style ID and target domain are required');
      return;
    }
    const payload: any = {
      source_style_id: transferForm.source_style_id.trim(),
      target_domain: transferForm.target_domain.trim(),
      fidelity: transferForm.fidelity,
    };
    if (transferForm.description.trim()) payload.description = transferForm.description.trim();
    try {
      await api.cognitiveStyleTransfer.createTransfer(payload);
      toast.success('Transfer created');
      setTransferForm({ source_style_id: '', target_domain: '', fidelity: 'ADAPTIVE', description: '' });
      await loadTransfers();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleBlendStyles = async () => {
    if (!blendForm.style_ids.trim()) {
      toast.error('At least two style IDs are required');
      return;
    }
    const ids = blendForm.style_ids.split(',').map(s => s.trim()).filter(Boolean);
    if (ids.length < 2) {
      toast.error('Provide at least two comma-separated style IDs');
      return;
    }
    const payload: any = { style_ids: ids, strategy: blendForm.strategy };
    if (blendForm.weights.trim()) {
      const nums = blendForm.weights.split(',').map(s => Number(s.trim())).filter(n => !Number.isNaN(n));
      if (nums.length > 0) payload.weights = nums;
    }
    try {
      await api.cognitiveStyleTransfer.blendStyles(payload);
      toast.success('Styles blended');
      setBlendForm({ style_ids: '', strategy: 'WEIGHTED', weights: '' });
      await loadBlends();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleFingerprint = async () => {
    if (!fingerprintForm.style_id.trim()) {
      toast.error('Style ID is required');
      return;
    }
    try {
      const result = await api.cognitiveStyleTransfer.fingerprintStyle(fingerprintForm.style_id.trim());
      setFingerprintResult(result);
      toast.success('Fingerprint computed');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleMatch = async () => {
    if (!matchForm.style_id.trim()) {
      toast.error('Style ID is required');
      return;
    }
    const topK = matchForm.top_k.trim() ? Number(matchForm.top_k) : undefined;
    try {
      const result = await api.cognitiveStyleTransfer.matchStyles(matchForm.style_id.trim(), topK);
      setMatchResult(result);
      toast.success('Matches computed');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleValidate = async () => {
    if (!validateForm.transfer_id.trim()) {
      toast.error('Transfer ID is required');
      return;
    }
    try {
      await api.cognitiveStyleTransfer.validateTransfer(validateForm.transfer_id.trim());
      toast.success('Transfer validated');
      setValidateForm({ transfer_id: '' });
      await loadTransfers();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleApplyStyle = async () => {
    if (!applyForm.style_id.trim() || !applyForm.problem_description.trim()) {
      toast.error('Style ID and problem description are required');
      return;
    }
    try {
      const result = await api.cognitiveStyleTransfer.applyStyle(applyForm.style_id.trim(), applyForm.problem_description.trim());
      setApplyResult(result);
      toast.success('Style applied');
    } catch (e: any) { toast.error(e.message); }
  };

  const renderBadge = (value: string, color: string) => (
    <span style={{
      display: 'inline-block',
      padding: '2px 8px',
      borderRadius: 10,
      fontSize: 11,
      fontWeight: 600,
      color: '#fff',
      background: color,
      marginRight: 4,
    }}>{value}</span>
  );

  const statusColor = (s: string) => STATUS_COLORS[s] ?? themeColors.primary;

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🎨 Cognitive Style Transfer</h2>
          <p className="panel-subtitle">Extract reasoning styles, transfer them across domains, and blend fingerprints</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive style transfer...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🎨 Cognitive Style Transfer</h2>
        <p className="panel-subtitle">Extract reasoning styles, transfer them across domains, and blend fingerprints</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_styles ?? '-'}</span><span className="stat-label">Styles</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_transfers ?? '-'}</span><span className="stat-label">Transfers</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_blends ?? '-'}</span><span className="stat-label">Blends</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_fingerprints ?? '-'}</span><span className="stat-label">Fingerprints</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.completed_transfers ?? '-'}</span><span className="stat-label">Completed</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'style', 'transfer'] as const).map(s => (
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

      {/* Overview Section */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Style Transfer Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Styles</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_styles ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Transfers</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_transfers ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Blends</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_blends ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Fingerprints</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_fingerprints ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Completed Transfers</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.completed_transfers ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Styles</h3>
            <button onClick={() => loadStyles()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {styles.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No styles recorded. Extract one in the Style section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {styles.slice(0, 10).map((s: any, i: number) => {
                  const id = s.style_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{s.source_id ?? 'unnamed'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{s.description ?? ''} · {id}</div>
                        </div>
                        <div>
                          {s.source_type && renderBadge(s.source_type, themeColors.secondary)}
                          {s.dimension && renderBadge(s.dimension, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Style Section */}
      {activeSection === 'style' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Extract Style</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Source ID *</label>
                <input value={styleForm.source_id} onChange={e => setStyleForm({ ...styleForm, source_id: e.target.value })} placeholder="e.g. agent_42 or domain_key" />
              </div>
              <div className="form-group">
                <label>Source Type</label>
                <select value={styleForm.source_type} onChange={e => setStyleForm({ ...styleForm, source_type: e.target.value })}>
                  {SOURCE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={styleForm.description} onChange={e => setStyleForm({ ...styleForm, description: e.target.value })} placeholder="Optional description of the style" />
              </div>
            </div>
            <button onClick={handleExtractStyle} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Extract Style</button>
          </div>

          {/* Fingerprint */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Compute Fingerprint</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Style ID *</label>
                <input value={fingerprintForm.style_id} onChange={e => setFingerprintForm({ ...fingerprintForm, style_id: e.target.value })} placeholder="style id" />
              </div>
            </div>
            <button onClick={handleFingerprint} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Compute Fingerprint</button>
            {fingerprintResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(fingerprintResult, null, 2)}</pre>
            )}
          </div>

          {/* Match Styles */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Match Styles</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Style ID *</label>
                <input value={matchForm.style_id} onChange={e => setMatchForm({ ...matchForm, style_id: e.target.value })} placeholder="style id" />
              </div>
              <div className="form-group">
                <label>Top K</label>
                <input value={matchForm.top_k} onChange={e => setMatchForm({ ...matchForm, top_k: e.target.value })} type="number" min="1" />
              </div>
            </div>
            <button onClick={handleMatch} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Match Styles</button>
            {matchResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(matchResult, null, 2)}</pre>
            )}
          </div>

          {/* Apply Style */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Apply Style</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Style ID *</label>
                <input value={applyForm.style_id} onChange={e => setApplyForm({ ...applyForm, style_id: e.target.value })} placeholder="style id" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Problem Description *</label>
                <input value={applyForm.problem_description} onChange={e => setApplyForm({ ...applyForm, problem_description: e.target.value })} placeholder="Describe the problem to apply the style to" />
              </div>
            </div>
            <button onClick={handleApplyStyle} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Apply Style</button>
            {applyResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(applyResult, null, 2)}</pre>
            )}
          </div>

          {/* Styles List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Styles ({styles.length})</h3>
            <button onClick={() => loadStyles()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {styles.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No styles recorded. Extract one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {styles.slice(0, 30).map((s: any, i: number) => {
                  const id = s.style_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{s.source_id ?? 'unnamed'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{s.dimension ?? 'no_dim'}]</span></div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                      {s.description && (
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7, marginTop: 4 }}>{s.description}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Transfer Section */}
      {activeSection === 'transfer' && (
        <div className="dashboard-section">
          {/* Create Transfer */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Create Transfer</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Source Style ID *</label>
                <input value={transferForm.source_style_id} onChange={e => setTransferForm({ ...transferForm, source_style_id: e.target.value })} placeholder="source style id" />
              </div>
              <div className="form-group">
                <label>Target Domain *</label>
                <input value={transferForm.target_domain} onChange={e => setTransferForm({ ...transferForm, target_domain: e.target.value })} placeholder="e.g. code_review" />
              </div>
              <div className="form-group">
                <label>Fidelity</label>
                <select value={transferForm.fidelity} onChange={e => setTransferForm({ ...transferForm, fidelity: e.target.value })}>
                  {FIDELITY_MODES.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={transferForm.description} onChange={e => setTransferForm({ ...transferForm, description: e.target.value })} placeholder="Optional description" />
              </div>
            </div>
            <button onClick={handleCreateTransfer} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Transfer</button>
          </div>

          {/* Validate Transfer */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Validate Transfer</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Transfer ID *</label>
                <input value={validateForm.transfer_id} onChange={e => setValidateForm({ ...validateForm, transfer_id: e.target.value })} placeholder="transfer id" />
              </div>
            </div>
            <button onClick={handleValidate} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Validate Transfer</button>
          </div>

          {/* Blend Styles */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Blend Styles</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Style IDs * (comma-separated, min 2)</label>
                <input value={blendForm.style_ids} onChange={e => setBlendForm({ ...blendForm, style_ids: e.target.value })} placeholder="id1, id2, id3" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={blendForm.strategy} onChange={e => setBlendForm({ ...blendForm, strategy: e.target.value })}>
                  {BLEND_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Weights (comma-separated)</label>
                <input value={blendForm.weights} onChange={e => setBlendForm({ ...blendForm, weights: e.target.value })} placeholder="0.5, 0.3, 0.2" />
              </div>
            </div>
            <button onClick={handleBlendStyles} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Blend Styles</button>
          </div>

          {/* Transfers List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Transfers ({transfers.length})</h3>
            <button onClick={() => loadTransfers()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {transfers.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No transfers recorded. Create one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {transfers.slice(0, 30).map((t: any, i: number) => {
                  const id = t.transfer_id ?? t.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{t.target_domain ?? 'unknown_domain'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>source: {t.source_style_id ?? '-'} · {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {t.fidelity && renderBadge(t.fidelity, themeColors.secondary)}
                          {t.status && renderBadge(t.status, statusColor(t.status))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Blends List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Blends ({blends.length})</h3>
            <button onClick={() => loadBlends()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {blends.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No blends recorded. Blend some styles above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {blends.slice(0, 30).map((b: any, i: number) => {
                  const id = b.blend_id ?? b.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>Blend {id}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{Array.isArray(b.style_ids) ? b.style_ids.join(', ') : (b.style_ids ?? '-')}</div>
                        </div>
                        {b.strategy && renderBadge(b.strategy, themeColors.secondary)}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CognitiveStyleTransferPanel;
