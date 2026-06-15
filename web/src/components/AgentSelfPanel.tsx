import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { Agent, AgentSelfProfile, AgentSelfStats } from '../types';

interface Props {
  agent: Agent;
}

export const AgentSelfPanel: React.FC<Props> = ({ agent }) => {
  const [profile, setProfile] = useState<AgentSelfProfile | null>(null);
  const [stats, setStats] = useState<AgentSelfStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [snapshotResult, setSnapshotResult] = useState<string | null>(null);
  const [exportData, setExportData] = useState<string | null>(null);
  const [importText, setImportText] = useState('');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [p, s] = await Promise.all([
        api.agentSelf.profile(agent.id),
        api.agentSelf.stats(agent.id),
      ]);
      setProfile(p);
      setStats(s);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agent self data');
    } finally {
      setLoading(false);
    }
  }, [agent.id]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleSnapshot = async () => {
    try {
      const result = await api.agentSelf.snapshot(agent.id);
      setSnapshotResult(`Snapshot created: ${result.trait_count} traits, ${result.pattern_count} patterns`);
      setTimeout(() => setSnapshotResult(null), 3000);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create snapshot');
    }
  };

  const handleExport = async () => {
    try {
      const data = await api.agentSelf.export(agent.id);
      setExportData(JSON.stringify(data, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export');
    }
  };

  const handleImport = async () => {
    if (!importText.trim()) return;
    try {
      await api.agentSelf.import(agent.id, JSON.parse(importText));
      setImportText('');
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import');
    }
  };

  if (loading) return <div className="panel-loading">Loading agent self identity...</div>;

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Agent Self Identity</h2>
        <div className="panel-header-actions">
          <button className="btn-primary" onClick={handleSnapshot}>Create Snapshot</button>
          <button className="btn-secondary" onClick={handleExport}>Export</button>
          <button className="btn-secondary" onClick={loadData}>Refresh</button>
        </div>
      </div>

      {error && <div className="panel-error">{error}</div>}
      {snapshotResult && <div className="panel-success">{snapshotResult}</div>}

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.total_traits}</div>
            <div className="stat-label">Traits</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.total_patterns}</div>
            <div className="stat-label">Patterns</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.evolution_step}</div>
            <div className="stat-label">Evolution Step</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.interaction_count}</div>
            <div className="stat-label">Interactions</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{(stats.alignment_score * 100).toFixed(0)}%</div>
            <div className="stat-label">Alignment</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.snapshot_count}</div>
            <div className="stat-label">Snapshots</div>
          </div>
        </div>
      )}

      {profile && profile.traits && Object.keys(profile.traits).length > 0 && (
        <div className="panel-section">
          <h3>Self Traits</h3>
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Trait</th>
                  <th>Value</th>
                  <th>Category</th>
                  <th>Confidence</th>
                  <th>Origin</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(profile.traits).map(([id, trait]) => (
                  <tr key={id}>
                    <td>{trait.name}</td>
                    <td>{trait.value}</td>
                    <td><span className="badge">{trait.category}</span></td>
                    <td>
                      <div className="progress-bar-mini">
                        <div className="progress-fill" style={{ width: `${(trait.confidence * 100).toFixed(0)}%` }} />
                      </div>
                      {(trait.confidence * 100).toFixed(0)}%
                    </td>
                    <td>{trait.origin}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {profile && profile.patterns && Object.keys(profile.patterns).length > 0 && (
        <div className="panel-section">
          <h3>Behavioral Patterns</h3>
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Frequency</th>
                  <th>Success Rate</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(profile.patterns).map(([id, pattern]) => (
                  <tr key={id}>
                    <td><span className="badge badge-blue">{pattern.pattern_type}</span></td>
                    <td>{pattern.frequency}</td>
                    <td>{(pattern.avg_success_rate * 100).toFixed(0)}%</td>
                    <td>{pattern.description || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="panel-section">
        <h3>Import Self Model</h3>
        <div className="form-row">
          <textarea
            className="form-textarea"
            rows={4}
            placeholder="Paste exported self model JSON here..."
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
          />
          <button className="btn-primary" onClick={handleImport} disabled={!importText.trim()}>
            Import
          </button>
        </div>
      </div>

      {exportData && (
        <div className="panel-section">
          <h3>Exported Self Model</h3>
          <pre className="code-block">{exportData}</pre>
          <button className="btn-secondary" onClick={() => setExportData(null)}>Close</button>
        </div>
      )}
    </div>
  );
};