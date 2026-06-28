import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#7c3aed',
  secondary: '#c4b5fd',
  bg: '#f5f3ff',
  border: '#ddd6fe',
  accent: '#ede9fe',
  text: '#4c1d95',
};

const TIERS = ['hot', 'warm', 'cold'];
const DREAM_STRATEGIES = ['merge', 'summarize', 'archive', 'prioritize', 'prune'];

export const DreamConsolidatorPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'entry' | 'snapshot' | 'dream'>('overview');

  // Entry form
  const [entryForm, setEntryForm] = useState({
    content: '', tier: 'warm', importance: '0.5',
  });

  // Snapshot form
  const [snapshotForm, setSnapshotForm] = useState({
    tier: 'warm', description: '',
  });

  // Dream form
  const [dreamForm, setDreamForm] = useState({
    strategy: 'merge',
  });
  const [dreamResult, setDreamResult] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.dreamConsolidator.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load dream consolidator data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleAddEntry = async () => {
    if (!entryForm.content.trim()) return;
    try {
      await api.dreamConsolidator.addEntry({
        content: entryForm.content.trim(),
        tier: entryForm.tier,
        importance: Number(entryForm.importance),
      });
      toast.success('Memory entry added');
      setEntryForm({ content: '', tier: 'warm', importance: '0.5' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreateSnapshot = async () => {
    try {
      await api.dreamConsolidator.createSnapshot({
        tier: snapshotForm.tier || undefined,
        description: snapshotForm.description || undefined,
      });
      toast.success('Snapshot created');
      setSnapshotForm({ tier: 'warm', description: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleStartDream = async () => {
    try {
      const result = await api.dreamConsolidator.startDream({ strategy: dreamForm.strategy });
      setDreamResult(result);
      toast.success(`Dream cycle started (${dreamForm.strategy})`);
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>💤 Dream Consolidator</h2>
          <p className="panel-subtitle">Consolidate memories through offline dream cycles</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading dream consolidator...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>💤 Dream Consolidator</h2>
        <p className="panel-subtitle">Consolidate memories through offline dream cycles</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_entries ?? '-'}</span><span className="stat-label">Entries</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_dreams ?? '-'}</span><span className="stat-label">Dream Cycles</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.consolidated_entries ?? '-'}</span><span className="stat-label">Consolidated</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'entry', 'snapshot', 'dream'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Dream Consolidator Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Entries</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_entries ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Snapshots</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_snapshots ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Dream Cycles</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_dreams ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Consolidated</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.consolidated_entries ?? 0}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Entry */}
      {activeSection === 'entry' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Add Memory Entry</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Content *</label>
              <textarea
                rows={4}
                value={entryForm.content}
                onChange={e => setEntryForm(f => ({ ...f, content: e.target.value }))}
                placeholder="Memory content to consolidate..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Tier</label>
                <select value={entryForm.tier} onChange={e => setEntryForm(f => ({ ...f, tier: e.target.value }))}>
                  {TIERS.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Importance (0-1)</label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={entryForm.importance}
                  onChange={e => setEntryForm(f => ({ ...f, importance: e.target.value }))}
                  style={{ width: '100%' }}
                />
                <div style={{ fontSize: '0.75rem', color: themeColors.text }}>{Number(entryForm.importance).toFixed(2)}</div>
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleAddEntry}
              disabled={!entryForm.content.trim()}
            >
              Add Entry
            </button>
          </div>
        </div>
      )}

      {/* Snapshot */}
      {activeSection === 'snapshot' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create Snapshot</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Tier</label>
              <select value={snapshotForm.tier} onChange={e => setSnapshotForm(f => ({ ...f, tier: e.target.value }))}>
                {TIERS.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={3}
                value={snapshotForm.description}
                onChange={e => setSnapshotForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Optional snapshot description..."
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleCreateSnapshot}
            >
              Create Snapshot
            </button>
          </div>
        </div>
      )}

      {/* Dream */}
      {activeSection === 'dream' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Start Dream Cycle</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Strategy</label>
              <select value={dreamForm.strategy} onChange={e => setDreamForm({ strategy: e.target.value })}>
                {DREAM_STRATEGIES.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleStartDream}
            >
              💤 Start Dream
            </button>
          </div>

          {dreamResult && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Dream Result</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(dreamResult, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DreamConsolidatorPanel;
