import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#059669',
  secondary: '#34d399',
  bg: '#ecfdf5',
  border: '#6ee7b7',
  accent: '#d1fae5',
  text: '#065f46',
};

export const ResearchEnginePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'create' | 'projects'>('overview');

  const [createForm, setCreateForm] = useState({
    title: '', research_question: '', description: '',
  });
  const [creating, setCreating] = useState(false);
  const [reports, setReports] = useState<any[] | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.researchEngine.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load research engine data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreate = async () => {
    if (!createForm.title.trim() || !createForm.research_question.trim()) return;
    try {
      setCreating(true);
      const result = await api.researchEngine.createProject({
        title: createForm.title,
        research_question: createForm.research_question,
        description: createForm.description || undefined,
      });
      toast.success(`Project created: ${result.title}`);
      setCreateForm({ title: '', research_question: '', description: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
    finally { setCreating(false); }
  };

  const handleLoadReports = async () => {
    try {
      const r = await api.researchEngine.reports(10);
      setReports(r.reports || r);
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🔬 Autonomous Research Engine</h2>
          <p className="panel-subtitle">Self-directed research and investigation</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading research engine...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🔬 Autonomous Research Engine</h2>
        <p className="panel-subtitle">Self-directed research and investigation</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_projects ?? '-'}</span><span className="stat-label">Total Projects</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_reports ?? '-'}</span><span className="stat-label">Total Reports</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.active_projects ?? '-'}</span><span className="stat-label">Active Projects</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_sources ?? '-'}</span><span className="stat-label">Total Sources</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'create', 'projects'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Research Engine Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Hypotheses</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_hypotheses ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Findings</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_findings ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Confidence</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.avg_confidence?.toFixed?.(2) ?? '-'}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create Project */}
      {activeSection === 'create' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create Research Project</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Title</label>
              <input
                type="text"
                value={createForm.title}
                onChange={e => setCreateForm(f => ({ ...f, title: e.target.value }))}
                placeholder="Project title..."
              />
            </div>
            <div className="form-group">
              <label>Research Question</label>
              <input
                type="text"
                value={createForm.research_question}
                onChange={e => setCreateForm(f => ({ ...f, research_question: e.target.value }))}
                placeholder="What are you researching?"
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={3}
                value={createForm.description}
                onChange={e => setCreateForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Detailed project description..."
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleCreate}
              disabled={creating || !createForm.title.trim() || !createForm.research_question.trim()}
            >
              {creating ? 'Creating...' : '🔬 Create Project'}
            </button>
          </div>
        </div>
      )}

      {/* Projects / Reports */}
      {activeSection === 'projects' && (
        <div className="dashboard-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Reports</h3>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleLoadReports}>Load Reports</button>
          </div>
          {reports ? (
            reports.length === 0 ? (
              <div className="panel-empty">No research reports yet</div>
            ) : (
              <div className="forge-skill-list">
                {reports.map((r: any, idx: number) => (
                  <div key={r.report_id || idx} className="forge-skill-card" style={{ borderLeft: `4px solid ${themeColors.primary}` }}>
                    <div className="forge-skill-header">
                      <div className="forge-skill-name" style={{ color: themeColors.text }}>{r.title}</div>
                      <span className="dashboard-badge" style={{ background: themeColors.primary, color: '#fff' }}>
                        {r.confidence_score != null ? `${(r.confidence_score * 100).toFixed?.(0) ?? r.confidence_score}%` : '-'}
                      </span>
                    </div>
                    <div className="forge-skill-meta">
                      <div style={{ color: themeColors.text, marginBottom: 4 }}>{r.executive_summary?.slice(0, 200)}</div>
                      <div>Sources: {r.sources_count ?? 0} | Hypotheses: {r.hypotheses_tested ?? 0}</div>
                      {r.conclusions?.length > 0 && (
                        <div style={{ marginTop: 4 }}>
                          {r.conclusions.map((c: string, i: number) => (
                            <span key={i} style={{ display: 'inline-block', padding: '2px 8px', margin: '2px', background: themeColors.accent, color: themeColors.text, borderRadius: 12, fontSize: '0.75rem' }}>{c.slice(0, 60)}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            <div className="panel-empty">Click "Load Reports" to view recent research reports</div>
          )}
        </div>
      )}
    </div>
  );
};

export default ResearchEnginePanel;