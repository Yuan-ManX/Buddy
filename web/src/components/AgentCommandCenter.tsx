import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

interface SubsystemStatus {
  status: string;
  message?: string;
  [key: string]: unknown;
}

interface CommandCenterData {
  timestamp: string;
  agent_id: string | null;
  subsystems: Record<string, SubsystemStatus>;
  summary: {
    total_subsystems: number;
    active_subsystems: number;
    error_subsystems: number;
    overall_status: string;
  };
}

const SUBSYSTEM_META: Record<string, { label: string; icon: string; description: string; color: string; route: string }> = {
  goal_decomposer: { label: 'Goal Decomposer', icon: '🎯', description: 'Hierarchical task decomposition engine', color: '#4f6ef7', route: 'goalDecomposer' },
  self_reflection: { label: 'Self-Reflection', icon: '🪞', description: 'Agent introspection and improvement', color: '#8b5cf6', route: 'selfReflection' },
  memory_consolidator: { label: 'Memory Consolidator', icon: '🧠', description: 'Multi-layer memory management', color: '#22c55e', route: 'memoryConsolidator' },
  context_compressor: { label: 'Context Compressor', icon: '📦', description: 'Intelligent context optimization', color: '#f59e0b', route: 'contextCompressor' },
  governance: { label: 'Governance', icon: '⚖️', description: 'Policy-based access control', color: '#ef4444', route: 'governance' },
  smart_router: { label: 'Smart Router', icon: '🧭', description: 'Intelligent model selection', color: '#06b6d4', route: 'smartrouter' },
  identity_core: { label: 'Identity Core', icon: '🆔', description: 'Self-awareness and memory', color: '#ec4899', route: 'identitycore' },
  workspace_manager: { label: 'Workspace Manager', icon: '🗂️', description: 'Isolated project environments', color: '#84cc16', route: 'workspaces' },
  agent_mesh: { label: 'Agent Mesh', icon: '🕸️', description: 'Multi-agent collaboration', color: '#a855f7', route: 'agentmesh' },
  learning_loop: { label: 'Learning Loop', icon: '🔄', description: 'Continuous self-improvement', color: '#14b8a6', route: 'learningloop' },
  persona: { label: 'Persona', icon: '👤', description: 'Agent personality management', color: '#f97316', route: 'persona' },
};

export const AgentCommandCenter: React.FC<{ onNavigate: (tab: string) => void }> = ({ onNavigate }) => {
  const toast = useToast();
  const [data, setData] = useState<CommandCenterData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const result = await request<CommandCenterData>('/command-center/status');
      setData(result);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load command center data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, loadData]);

  const overallStatusColor = data?.summary.overall_status === 'healthy'
    ? '#22c55e'
    : data?.summary.overall_status === 'degraded'
      ? '#f59e0b'
      : '#ef4444';

  if (loading && !data) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Agent Command Center</h2>
          <p className="panel-subtitle">Unified control hub for all agent subsystems</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading subsystems...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2>Agent Command Center</h2>
            <p className="panel-subtitle">Central coordination hub for all AI-native agent subsystems</p>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button
              className={`btn-sm ${autoRefresh ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setAutoRefresh(!autoRefresh)}
              style={{ fontSize: '0.8rem' }}
            >
              {autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}
            </button>
            <button className="btn-sm btn-secondary" onClick={loadData} style={{ fontSize: '0.8rem' }}>
              Refresh
            </button>
          </div>
        </div>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Overall Status */}
      {data && (
        <>
          <div style={{
            display: 'flex',
            gap: 16,
            marginBottom: 20,
            padding: 20,
            background: 'var(--bg-card)',
            borderRadius: 12,
            border: '1px solid var(--border)',
            boxShadow: 'var(--shadow-sm)',
          }}>
            <div style={{
              width: 80,
              height: 80,
              borderRadius: '50%',
              background: `${overallStatusColor}15`,
              border: `3px solid ${overallStatusColor}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              <div style={{
                width: 50,
                height: 50,
                borderRadius: '50%',
                background: overallStatusColor,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.5rem',
                color: '#fff',
                fontWeight: 700,
              }}>
                {data.summary.active_subsystems}
              </div>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span style={{
                  display: 'inline-block',
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  background: overallStatusColor,
                  boxShadow: `0 0 8px ${overallStatusColor}80`,
                }} />
                <span style={{ fontWeight: 700, fontSize: '1.1rem', textTransform: 'capitalize' }}>
                  {data.summary.overall_status}
                </span>
              </div>
              <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Subsystems</div>
                  <div style={{ fontWeight: 700 }}>{data.summary.total_subsystems}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Active</div>
                  <div style={{ fontWeight: 700, color: '#22c55e' }}>{data.summary.active_subsystems}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Errors</div>
                  <div style={{ fontWeight: 700, color: data.summary.error_subsystems > 0 ? '#ef4444' : '#22c55e' }}>
                    {data.summary.error_subsystems}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Last Updated</div>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                    {new Date(data.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
              {/* Health bar */}
              <div style={{ width: '100%', background: '#e5e7eb', borderRadius: 4, marginTop: 12, height: 6 }}>
                <div style={{
                  width: `${(data.summary.active_subsystems / data.summary.total_subsystems) * 100}%`,
                  background: overallStatusColor,
                  height: '100%',
                  borderRadius: 4,
                  transition: 'width 0.5s ease',
                }} />
              </div>
            </div>
          </div>

          {/* Subsystem Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: 12,
          }}>
            {Object.entries(data.subsystems).map(([key, subsystem]) => {
              const meta = SUBSYSTEM_META[key] || {
                label: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
                icon: '⚙️',
                description: '',
                color: '#6b7280',
                route: key,
              };
              const isActive = subsystem.status === 'active';
              const isError = subsystem.status === 'error';

              return (
                <div
                  key={key}
                  onClick={() => onNavigate(meta.route)}
                  style={{
                    padding: 16,
                    background: 'var(--bg-card)',
                    borderRadius: 10,
                    border: `1px solid var(--border)`,
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    position: 'relative',
                    overflow: 'hidden',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                    e.currentTarget.style.borderColor = meta.color;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                    e.currentTarget.style.borderColor = 'var(--border)';
                  }}
                >
                  {/* Status indicator */}
                  <div style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: 4,
                    height: '100%',
                    background: isActive ? meta.color : isError ? '#ef4444' : '#9ca3af',
                  }} />

                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                    <span style={{ fontSize: '1.5rem' }}>{meta.icon}</span>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{meta.label}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{meta.description}</div>
                    </div>
                    <div style={{ marginLeft: 'auto' }}>
                      <span style={{
                        display: 'inline-block',
                        width: 10,
                        height: 10,
                        borderRadius: '50%',
                        background: isActive ? '#22c55e' : isError ? '#ef4444' : '#9ca3af',
                        boxShadow: isActive ? '0 0 6px #22c55e80' : 'none',
                      }} />
                    </div>
                  </div>

                  {/* Subsystem metrics */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
                    {isError ? (
                      <span style={{ fontSize: '0.8rem', color: '#ef4444' }}>
                        {subsystem.message || 'Error loading subsystem'}
                      </span>
                    ) : (
                      Object.entries(subsystem)
                        .filter(([k]) => k !== 'status' && k !== 'message')
                        .slice(0, 4)
                        .map(([metricKey, value]) => (
                          <span key={metricKey} style={{
                            fontSize: '0.75rem',
                            padding: '3px 8px',
                            background: `${meta.color}10`,
                            color: meta.color,
                            borderRadius: 6,
                            fontWeight: 600,
                          }}>
                            {metricKey.replace(/_/g, ' ')}: {typeof value === 'number' ? value.toLocaleString() : String(value)}
                          </span>
                        ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Quick Actions */}
          <div style={{ marginTop: 20 }}>
            <h3 style={{ marginBottom: 12, fontSize: '1rem', color: 'var(--text-secondary)' }}>Quick Actions</h3>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {[
                { label: 'Decompose Goal', route: 'goalDecomposer', color: '#4f6ef7' },
                { label: 'Run Reflection', route: 'selfReflection', color: '#8b5cf6' },
                { label: 'Consolidate Memory', route: 'memoryConsolidator', color: '#22c55e' },
                { label: 'Compress Context', route: 'contextCompressor', color: '#f59e0b' },
                { label: 'View Policies', route: 'governance', color: '#ef4444' },
                { label: 'Route Model', route: 'smartrouter', color: '#06b6d4' },
                { label: 'Manage Identity', route: 'identitycore', color: '#ec4899' },
                { label: 'Open Workspace', route: 'workspaces', color: '#84cc16' },
              ].map(action => (
                <button
                  key={action.route}
                  onClick={(e) => { e.stopPropagation(); onNavigate(action.route); }}
                  style={{
                    padding: '8px 16px',
                    background: `${action.color}10`,
                    color: action.color,
                    border: `1px solid ${action.color}30`,
                    borderRadius: 8,
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = action.color;
                    e.currentTarget.style.color = '#fff';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = `${action.color}10`;
                    e.currentTarget.style.color = action.color;
                  }}
                >
                  {action.label}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

// Helper to make direct API calls
async function request<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try { message = JSON.parse(body).detail || body; } catch {}
    throw new Error(message);
  }
  return res.json();
}

export default AgentCommandCenter;