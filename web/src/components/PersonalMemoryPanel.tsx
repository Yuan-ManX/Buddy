import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#7c3aed',
  secondary: '#a78bfa',
  bg: '#f5f3ff',
  border: '#c4b5fd',
  accent: '#ede9fe',
  text: '#4c1d95',
};

export const PersonalMemoryPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'capture' | 'retrieve' | 'profile' | 'consolidate'>('overview');

  const [captureForm, setCaptureForm] = useState({
    content: '', dimension: 'general', confidence: 0.5, access_level: 'private', tags: '', source: '',
  });
  const [retrieveForm, setRetrieveForm] = useState({
    query: '', dimension: '', tags: '', min_strength: '', limit: '10',
  });
  const [retrieveResults, setRetrieveResults] = useState<any[] | null>(null);
  const [profileData, setProfileData] = useState<any>(null);
  const [consolidating, setConsolidating] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.personalMemory.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load memory data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCapture = async () => {
    if (!captureForm.content.trim()) return;
    try {
      const result = await api.personalMemory.capture({
        content: captureForm.content,
        dimension: captureForm.dimension || undefined,
        confidence: captureForm.confidence,
        access_level: captureForm.access_level,
        tags: captureForm.tags ? captureForm.tags.split(',').map(s => s.trim()) : undefined,
        source: captureForm.source || undefined,
      });
      toast.success('Memory captured successfully');
      setCaptureForm({ content: '', dimension: 'general', confidence: 0.5, access_level: 'private', tags: '', source: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRetrieve = async () => {
    try {
      const results = await api.personalMemory.retrieve({
        query: retrieveForm.query || undefined,
        dimension: retrieveForm.dimension || undefined,
        tags: retrieveForm.tags || undefined,
        min_strength: retrieveForm.min_strength || undefined,
        limit: parseInt(retrieveForm.limit) || 10,
      });
      setRetrieveResults(results.memories || results.items || results);
      toast.success(`Retrieved ${Array.isArray(results.memories || results.items || results) ? (results.memories || results.items || results).length : 0} memories`);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleLoadProfile = async () => {
    try {
      const p = await api.personalMemory.profile();
      setProfileData(p);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleConsolidate = async () => {
    try {
      setConsolidating(true);
      const result = await api.personalMemory.consolidate();
      toast.success('Memory consolidation initiated');
      loadData();
    } catch (e: any) { toast.error(e.message); }
    finally { setConsolidating(false); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🧠 Personal Memory Engine</h2>
          <p className="panel-subtitle">Capture, store, and retrieve personal memories with semantic understanding</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading memory engine...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🧠 Personal Memory Engine</h2>
        <p className="panel-subtitle">Capture, store, and retrieve personal memories with semantic understanding</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_memories ?? stats.entry_count ?? '-'}</span><span className="stat-label">Total Memories</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_consolidations ?? stats.consolidation_count ?? '-'}</span><span className="stat-label">Consolidations</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.avg_confidence?.toFixed?.(2) ?? stats.average_confidence ?? '-'}</span><span className="stat-label">Avg Confidence</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.dimensions_count ?? Object.keys(stats.by_dimension || {}).length ?? '-'}</span><span className="stat-label">Dimensions</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'capture', 'retrieve', 'profile', 'consolidate'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Memory Engine Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              {stats.by_dimension && Object.entries(stats.by_dimension).map(([dim, count]: [string, any]) => (
                <div key={dim} style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                  <div style={{ fontWeight: 600, color: themeColors.text, textTransform: 'capitalize' }}>{dim}</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{count}</div>
                </div>
              ))}
              {!stats.by_dimension && (
                <div className="panel-empty">No dimension data available</div>
              )}
            </div>
          </div>
          {stats.by_access_level && Object.entries(stats.by_access_level).length > 0 && (
            <div style={{ padding: 16, background: themeColors.accent, borderRadius: 8, marginBottom: 16 }}>
              <h4 style={{ color: themeColors.text }}>Access Level Distribution</h4>
              {Object.entries(stats.by_access_level).map(([level, count]: [string, any]) => (
                <div key={level} className="dashboard-stat-row">
                  <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>{level}</span>
                  <strong style={{ color: themeColors.primary }}>{count}</strong>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Capture */}
      {activeSection === 'capture' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Capture New Memory</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Content</label>
              <textarea
                rows={4}
                value={captureForm.content}
                onChange={e => setCaptureForm(f => ({ ...f, content: e.target.value }))}
                placeholder="Enter the memory content to capture..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Dimension</label>
                <select value={captureForm.dimension} onChange={e => setCaptureForm(f => ({ ...f, dimension: e.target.value }))}>
                  {['general', 'personal', 'professional', 'technical', 'social', 'health', 'finance', 'learning'].map(d => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Confidence ({captureForm.confidence.toFixed(1)})</label>
                <input type="range" min="0" max="1" step="0.1" value={captureForm.confidence}
                  onChange={e => setCaptureForm(f => ({ ...f, confidence: parseFloat(e.target.value) }))} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Access Level</label>
                <select value={captureForm.access_level} onChange={e => setCaptureForm(f => ({ ...f, access_level: e.target.value }))}>
                  {['private', 'shared', 'public'].map(l => (
                    <option key={l} value={l}>{l}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Source</label>
                <input type="text" value={captureForm.source} onChange={e => setCaptureForm(f => ({ ...f, source: e.target.value }))}
                  placeholder="e.g., conversation, observation" />
              </div>
            </div>
            <div className="form-group">
              <label>Tags (comma-separated)</label>
              <input type="text" value={captureForm.tags} onChange={e => setCaptureForm(f => ({ ...f, tags: e.target.value }))}
                placeholder="memory, important, project-x" />
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleCapture}>Capture Memory</button>
          </div>
        </div>
      )}

      {/* Retrieve */}
      {activeSection === 'retrieve' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Retrieve Memories</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Search Query</label>
              <input type="text" value={retrieveForm.query} onChange={e => setRetrieveForm(f => ({ ...f, query: e.target.value }))}
                placeholder="Search memories by content..." />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Dimension Filter</label>
                <select value={retrieveForm.dimension} onChange={e => setRetrieveForm(f => ({ ...f, dimension: e.target.value }))}>
                  <option value="">All</option>
                  {['general', 'personal', 'professional', 'technical', 'social', 'health', 'finance', 'learning'].map(d => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Tags</label>
                <input type="text" value={retrieveForm.tags} onChange={e => setRetrieveForm(f => ({ ...f, tags: e.target.value }))}
                  placeholder="comma-separated" />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Min Strength</label>
                <input type="text" value={retrieveForm.min_strength} onChange={e => setRetrieveForm(f => ({ ...f, min_strength: e.target.value }))}
                  placeholder="0.0 - 1.0" />
              </div>
              <div className="form-group">
                <label>Limit</label>
                <input type="number" value={retrieveForm.limit} onChange={e => setRetrieveForm(f => ({ ...f, limit: e.target.value }))}
                  min="1" max="100" />
              </div>
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleRetrieve}>Search Memories</button>
          </div>

          {retrieveResults && (
            <div style={{ marginTop: 20 }}>
              <h4 style={{ color: themeColors.text }}>Results ({retrieveResults.length})</h4>
              {retrieveResults.length === 0 ? (
                <div className="panel-empty">No memories found matching your criteria</div>
              ) : (
                <div className="forge-skill-list">
                  {retrieveResults.map((mem: any, idx: number) => (
                    <div key={mem.id || mem.entry_id || idx} className="forge-skill-card" style={{ borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div className="forge-skill-header">
                        <div className="forge-skill-name" style={{ color: themeColors.text }}>{mem.content || mem.summary || mem.text}</div>
                        <span className="dashboard-badge" style={{ background: themeColors.primary, color: '#fff' }}>
                          {mem.dimension || mem.type || 'general'}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>Confidence: {(mem.confidence ?? mem.strength ?? 0).toFixed?.(2) ?? mem.confidence} | Source: {mem.source || 'unknown'}</div>
                        {mem.tags?.length > 0 && (
                          <div style={{ marginTop: 4 }}>
                            {mem.tags.map((tag: string) => (
                              <span key={tag} style={{ display: 'inline-block', padding: '2px 8px', margin: '2px', background: themeColors.accent, color: themeColors.text, borderRadius: 12, fontSize: '0.75rem' }}>{tag}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Profile */}
      {activeSection === 'profile' && (
        <div className="dashboard-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Memory Profile</h3>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleLoadProfile}>Load Profile</button>
          </div>
          {profileData ? (
            <div>
              <div style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h4 style={{ color: themeColors.text }}>Profile Summary</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 12, marginTop: 8 }}>
                  {Object.entries(profileData).filter(([k]) => !['memories', 'entries', 'dimensions'].includes(k)).map(([key, value]: [string, any]) => (
                    <div key={key} style={{ padding: 8, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                      <div style={{ fontSize: '0.8rem', color: '#6b7280', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</div>
                      <div style={{ fontWeight: 600, color: themeColors.primary }}>
                        {typeof value === 'object' ? JSON.stringify(value).slice(0, 50) : String(value)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              {profileData.dimensions && (
                <div style={{ padding: 16, background: themeColors.accent, borderRadius: 8 }}>
                  <h4 style={{ color: themeColors.text }}>Dimensions</h4>
                  <div className="forge-skill-list">
                    {Object.entries(profileData.dimensions).map(([dim, info]: [string, any]) => (
                      <div key={dim} className="forge-skill-card" style={{ borderLeft: `4px solid ${themeColors.primary}` }}>
                        <div className="forge-skill-header">
                          <div className="forge-skill-name" style={{ color: themeColors.text, textTransform: 'capitalize' }}>{dim}</div>
                        </div>
                        <div className="forge-skill-meta">
                          {typeof info === 'object' ? Object.entries(info).map(([k, v]: [string, any]) => (
                            <div key={k}>{k.replace(/_/g, ' ')}: {typeof v === 'number' ? v.toFixed(2) : String(v)}</div>
                          )) : <div>{String(info)}</div>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="panel-empty">Click "Load Profile" to view your memory profile</div>
          )}
        </div>
      )}

      {/* Consolidate */}
      {activeSection === 'consolidate' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Memory Consolidation</h3>
          <div style={{ padding: 24, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, textAlign: 'center' }}>
            <p style={{ color: themeColors.text, marginBottom: 16, fontSize: '1.05rem' }}>
              Consolidation merges related memories, removes duplicates, and strengthens important connections.
              This process improves retrieval accuracy and reduces memory fragmentation.
            </p>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary, padding: '12px 32px', fontSize: '1.1rem' }}
              onClick={handleConsolidate}
              disabled={consolidating}
            >
              {consolidating ? 'Consolidating...' : '🔄 Start Consolidation'}
            </button>
            {stats && (
              <div style={{ marginTop: 20, display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
                <div className="stat-item" style={{ flex: '1 0 auto', maxWidth: 150 }}>
                  <div className="stat-content">
                    <span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_memories ?? stats.entry_count ?? '-'}</span>
                    <span className="stat-label">Total Memories</span>
                  </div>
                </div>
                <div className="stat-item" style={{ flex: '1 0 auto', maxWidth: 150 }}>
                  <div className="stat-content">
                    <span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_consolidations ?? stats.consolidation_count ?? '-'}</span>
                    <span className="stat-label">Total Consolidations</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default PersonalMemoryPanel;