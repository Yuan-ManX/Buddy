import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

interface PlatformPanelProps {
  subsystem: 'workspace' | 'taskWall' | 'roleCatalog' | 'failureAlchemy' | 'smartRouter' | 'twinBridge' | 'orgLayer';
}

interface NotificationState {
  type: 'success' | 'error' | 'info';
  message: string;
}

const SUBSYSTEM_META: Record<PlatformPanelProps['subsystem'], { title: string; icon: string; description: string }> = {
  workspace: { title: 'Workspace Isolation', icon: '🗂️', description: 'Per-project memory, skill, and file isolation boundaries' },
  taskWall: { title: 'Task Wall', icon: '📋', description: 'Central priority queue with deadlock detection and workstream switching' },
  roleCatalog: { title: 'Role Catalog', icon: '🎭', description: 'Unified role templates with RBAC permissions and capabilities' },
  failureAlchemy: { title: 'Failure Alchemy', icon: '⚗️', description: 'Convert failures into antibodies, vaccines, and improvement proposals' },
  smartRouter: { title: 'Smart Router', icon: '🧭', description: 'Difficulty-based model tier routing with learning feedback loop' },
  twinBridge: { title: 'Twin Bridge', icon: '👥', description: 'AI twin identity, hierarchical memory, and peer-to-peer protocol' },
  orgLayer: { title: 'Organization Layer', icon: '🏢', description: 'Organization, department, team, and member hierarchy' },
};

export function PlatformPanel({ subsystem }: PlatformPanelProps) {
  const meta = SUBSYSTEM_META[subsystem];
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState<NotificationState | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  const showNotification = useCallback((type: NotificationState['type'], message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 4000);
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      let result: any;
      switch (subsystem) {
        case 'workspace':
          result = await api.platformV3.listWorkspaces();
          break;
        case 'taskWall':
          result = await api.platformV3.listTasks();
          break;
        case 'roleCatalog':
          result = await api.platformV3.listRoles();
          break;
        case 'failureAlchemy':
          result = await api.platformV3.failureAlchemyStats();
          break;
        case 'smartRouter':
          result = await api.platformV3.smartRouterStats();
          break;
        case 'twinBridge':
          result = await api.platformV3.twinBridgeStats();
          break;
        case 'orgLayer':
          result = await api.platformV3.orgStats();
          break;
      }
      setData(result);
    } catch (err: any) {
      showNotification('error', err.message || 'Failed to load data');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [subsystem, showNotification]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreate = async (formData: Record<string, string>) => {
    try {
      switch (subsystem) {
        case 'workspace':
          await api.platformV3.createWorkspace(formData.name, formData.owner_agent_id || 'default-agent', formData.description);
          break;
        case 'taskWall':
          await api.platformV3.postTask(formData.title, formData.priority || 'medium', formData.description);
          break;
        case 'orgLayer':
          await api.platformV3.createOrg(formData.name, formData.description);
          break;
        case 'twinBridge':
          await api.platformV3.createTwin(formData.agent_id || 'default-agent', formData.name);
          break;
      }
      showNotification('success', 'Created successfully');
      setShowCreateForm(false);
      fetchData();
    } catch (err: any) {
      showNotification('error', err.message || 'Creation failed');
    }
  };

  return (
    <div style={{ padding: '24px', height: '100%', overflow: 'auto', boxSizing: 'border-box' }}>
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2 style={{ margin: '0 0 8px 0', fontSize: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '28px' }}>{meta.icon}</span>
            {meta.title}
          </h2>
          <p style={{ margin: 0, color: 'var(--text-secondary, #888)', fontSize: '14px' }}>{meta.description}</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {(subsystem === 'workspace' || subsystem === 'taskWall' || subsystem === 'orgLayer' || subsystem === 'twinBridge') && (
            <button onClick={() => setShowCreateForm(!showCreateForm)} style={btnStyle}>
              {showCreateForm ? 'Cancel' : '+ Create'}
            </button>
          )}
          <button onClick={fetchData} style={btnStyle}>Refresh</button>
        </div>
      </div>

      {notification && (
        <div style={{
          padding: '12px 16px', marginBottom: '16px', borderRadius: '8px',
          background: notification.type === 'error' ? 'rgba(244,63,94,0.1)' : notification.type === 'success' ? 'rgba(34,197,94,0.1)' : 'rgba(59,130,246,0.1)',
          border: `1px solid ${notification.type === 'error' ? 'rgba(244,63,94,0.3)' : notification.type === 'success' ? 'rgba(34,197,94,0.3)' : 'rgba(59,130,246,0.3)'}`,
          color: notification.type === 'error' ? '#f43f5e' : notification.type === 'success' ? '#22c55e' : '#3b82f6',
          fontSize: '14px',
        }}>
          {notification.message}
        </div>
      )}

      {showCreateForm && <CreateForm subsystem={subsystem} onSubmit={handleCreate} />}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '48px', color: 'var(--text-secondary, #888)' }}>Loading...</div>
      ) : data ? (
        <SubsystemContent subsystem={subsystem} data={data} onRefresh={fetchData} showNotification={showNotification} />
      ) : (
        <div style={{ textAlign: 'center', padding: '48px', color: 'var(--text-secondary, #888)' }}>No data available</div>
      )}
    </div>
  );
}

function SubsystemContent({ subsystem, data, onRefresh, showNotification }: {
  subsystem: PlatformPanelProps['subsystem'];
  data: any;
  onRefresh: () => void;
  showNotification: (type: NotificationState['type'], message: string) => void;
}) {
  switch (subsystem) {
    case 'workspace':
      return <WorkspaceContent data={data} onRefresh={onRefresh} showNotification={showNotification} />;
    case 'taskWall':
      return <TaskWallContent data={data} onRefresh={onRefresh} showNotification={showNotification} />;
    case 'roleCatalog':
      return <RoleCatalogContent data={data} />;
    case 'failureAlchemy':
      return <FailureAlchemyContent data={data} onRefresh={onRefresh} />;
    case 'smartRouter':
      return <SmartRouterContent data={data} onRefresh={onRefresh} showNotification={showNotification} />;
    case 'twinBridge':
      return <TwinBridgeContent data={data} onRefresh={onRefresh} />;
    case 'orgLayer':
      return <OrgLayerContent data={data} onRefresh={onRefresh} showNotification={showNotification} />;
    default:
      return null;
  }
}

// ── Workspace Content ─────────────────────────────────

function WorkspaceContent({ data, onRefresh, showNotification }: { data: any; onRefresh: () => void; showNotification: any }) {
  const workspaces = data.workspaces || [];
  const [selectedWs, setSelectedWs] = useState<string | null>(null);
  const [memory, setMemory] = useState<any[]>([]);
  const [newMemory, setNewMemory] = useState('');

  const loadMemory = async (wsId: string) => {
    try {
      const result = await api.platformV3.listWorkspaceMemory(wsId);
      setMemory(result.memory || []);
    } catch { setMemory([]); }
  };

  const addMemory = async () => {
    if (!selectedWs || !newMemory.trim()) return;
    try {
      await api.platformV3.addWorkspaceMemory(selectedWs, newMemory);
      setNewMemory('');
      loadMemory(selectedWs);
      showNotification('success', 'Memory added');
    } catch (err: any) {
      showNotification('error', err.message);
    }
  };

  const archiveWs = async (wsId: string) => {
    try {
      await api.platformV3.archiveWorkspace(wsId);
      showNotification('success', 'Workspace archived');
      onRefresh();
    } catch (err: any) {
      showNotification('error', err.message);
    }
  };

  return (
    <div>
      <div style={statsRowStyle}>
        <StatCard label="Workspaces" value={workspaces.length} icon="🗂️" />
        <StatCard label="Active" value={workspaces.filter((w: any) => !w.is_archived).length} icon="✅" />
        <StatCard label="Archived" value={workspaces.filter((w: any) => w.is_archived).length} icon="📦" />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
        <div>
          <h3 style={sectionHeaderStyle}>Workspaces</h3>
          {workspaces.length === 0 ? (
            <EmptyState message="No workspaces yet" />
          ) : (
            workspaces.map((ws: any) => (
              <div key={ws.workspace_id} style={{
                ...cardStyle,
                border: selectedWs === ws.workspace_id ? '2px solid var(--accent, #3b82f6)' : '1px solid var(--border, #333)',
              }} onClick={() => { setSelectedWs(ws.workspace_id); loadMemory(ws.workspace_id); }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '15px' }}>{ws.name}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary, #888)' }}>Owner: {ws.owner_agent_id}</div>
                  </div>
                  {ws.is_archived && <span style={badgeStyle('archived')}>Archived</span>}
                </div>
                {ws.description && <p style={{ margin: '8px 0 0 0', fontSize: '13px', color: 'var(--text-secondary, #888)' }}>{ws.description}</p>}
                {!ws.is_archived && (
                  <button onClick={(e) => { e.stopPropagation(); archiveWs(ws.workspace_id); }} style={{ ...btnSmStyle, marginTop: '8px' }}>Archive</button>
                )}
              </div>
            ))
          )}
        </div>
        <div>
          <h3 style={sectionHeaderStyle}>Memory {selectedWs ? `(${memory.length})` : ''}</h3>
          {!selectedWs ? (
            <EmptyState message="Select a workspace to view memory" />
          ) : (
            <>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                <input
                  value={newMemory}
                  onChange={(e) => setNewMemory(e.target.value)}
                  placeholder="Add memory entry..."
                  style={{ flex: 1, ...inputStyle }}
                  onKeyDown={(e) => e.key === 'Enter' && addMemory()}
                />
                <button onClick={addMemory} style={btnStyle}>Add</button>
              </div>
              {memory.map((m: any) => (
                <div key={m.id} style={cardStyle}>
                  <div style={{ fontSize: '13px' }}>{m.content}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary, #888)', marginTop: '4px' }}>
                    Source: {m.source} · {new Date(m.timestamp).toLocaleString()}
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Task Wall Content ─────────────────────────────────

function TaskWallContent({ data, onRefresh, showNotification }: { data: any; onRefresh: () => void; showNotification: any }) {
  const tasks = data.tasks || [];
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    api.platformV3.taskWallStats().then(setStats).catch(() => {});
  }, [tasks.length]);

  const claimTask = async () => {
    try {
      const result = await api.platformV3.claimTask('default-agent', []);
      if (result.task) {
        showNotification('success', `Claimed: ${result.task.title}`);
        onRefresh();
      } else {
        showNotification('info', result.message || 'No tasks available');
      }
    } catch (err: any) {
      showNotification('error', err.message);
    }
  };

  const completeTask = async (taskId: string) => {
    try {
      await api.platformV3.completeTask(taskId);
      showNotification('success', 'Task completed');
      onRefresh();
    } catch (err: any) {
      showNotification('error', err.message);
    }
  };

  const priorityColor: Record<string, string> = { critical: '#ef4444', high: '#f97316', medium: '#eab308', low: '#22c55e', deferred: '#6b7280' };

  return (
    <div>
      <div style={statsRowStyle}>
        <StatCard label="Total Tasks" value={stats?.total_posted || tasks.length} icon="📋" />
        <StatCard label="Completed" value={stats?.total_completed || 0} icon="✅" />
        <StatCard label="Failed" value={stats?.total_failed || 0} icon="❌" />
        <StatCard label="Parked" value={stats?.total_parked || 0} icon="🅿️" />
        <StatCard label="Deadlocks" value={stats?.deadlock_count || 0} icon="🔒" />
      </div>
      <div style={{ marginBottom: '16px' }}>
        <button onClick={claimTask} style={btnStyle}>Claim Next Task</button>
      </div>
      {tasks.length === 0 ? (
        <EmptyState message="No tasks on the wall" />
      ) : (
        tasks.map((task: any) => (
          <div key={task.task_id} style={cardStyle}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ ...badgeStyle(task.priority), background: priorityColor[task.priority] ? `${priorityColor[task.priority]}20` : undefined, color: priorityColor[task.priority] || undefined }}>
                    {task.priority}
                  </span>
                  <span style={{ fontWeight: 600, fontSize: '15px' }}>{task.title}</span>
                </div>
                {task.description && <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: 'var(--text-secondary, #888)' }}>{task.description}</p>}
                <div style={{ fontSize: '12px', color: 'var(--text-secondary, #888)', marginTop: '8px', display: 'flex', gap: '12px' }}>
                  <span>Status: <strong>{task.status}</strong></span>
                  {task.assigned_agent_id && <span>Agent: {task.assigned_agent_id}</span>}
                  {task.required_roles?.length > 0 && <span>Roles: {task.required_roles.join(', ')}</span>}
                </div>
              </div>
              {task.status === 'claimed' || task.status === 'in_progress' ? (
                <button onClick={() => completeTask(task.task_id)} style={btnSmStyle}>Complete</button>
              ) : null}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// ── Role Catalog Content ──────────────────────────────

function RoleCatalogContent({ data }: { data: any }) {
  const roles = data.roles || [];
  const [filter, setFilter] = useState('');
  const filtered = roles.filter((r: any) => !filter || r.name?.toLowerCase().includes(filter.toLowerCase()) || r.capabilities?.some((c: string) => c.includes(filter.toLowerCase())));

  const levelColor: Record<number, string> = { 100: '#f59e0b', 80: '#3b82f6', 60: '#8b5cf6', 40: '#10b981', 20: '#6b7280' };

  return (
    <div>
      <div style={statsRowStyle}>
        <StatCard label="Total Roles" value={data.count || roles.length} icon="🎭" />
        <StatCard label="Executives" value={roles.filter((r: any) => r.level >= 100).length} icon="👔" />
        <StatCard label="Management" value={roles.filter((r: any) => r.level >= 60 && r.level < 100).length} icon="📋" />
        <StatCard label="Engineers" value={roles.filter((r: any) => r.level < 60).length} icon="💻" />
      </div>
      <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter roles by name or capability..." style={{ ...inputStyle, width: '100%', marginBottom: '16px' }} />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '12px' }}>
        {filtered.map((role: any) => (
          <div key={role.role_id} style={cardStyle}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 600, fontSize: '15px' }}>{role.name}</span>
              <span style={{ ...badgeStyle(role.level_name?.toLowerCase() || ''), color: levelColor[role.level] || '#888' }}>{role.level_name}</span>
            </div>
            {role.description && <p style={{ margin: '4px 0 8px 0', fontSize: '13px', color: 'var(--text-secondary, #888)' }}>{role.description}</p>}
            {role.capabilities?.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                {role.capabilities.slice(0, 5).map((cap: string) => (
                  <span key={cap} style={{ ...badgeStyle('cap'), fontSize: '11px' }}>{cap}</span>
                ))}
                {role.capabilities.length > 5 && <span style={{ fontSize: '11px', color: 'var(--text-secondary, #888)' }}>+{role.capabilities.length - 5}</span>}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Failure Alchemy Content ───────────────────────────

function FailureAlchemyContent({ data, onRefresh }: { data: any; onRefresh: () => void }) {
  const [failures, setFailures] = useState<any[]>([]);
  const [antibodies, setAntibodies] = useState<any[]>([]);
  const [proposals, setProposals] = useState<any[]>([]);
  const [tab, setTab] = useState<'failures' | 'antibodies' | 'proposals'>('failures');

  useEffect(() => {
    api.platformV3.listFailures(20).then(r => setFailures(r.failures || [])).catch(() => {});
    api.platformV3.listAntibodies().then(r => setAntibodies(r.antibodies || [])).catch(() => {});
    api.platformV3.listProposals().then(r => setProposals(r.proposals || [])).catch(() => {});
  }, [data]);

  const tabs = [
    { id: 'failures' as const, label: `Failures (${failures.length})` },
    { id: 'antibodies' as const, label: `Antibodies (${antibodies.length})` },
    { id: 'proposals' as const, label: `Proposals (${proposals.length})` },
  ];

  return (
    <div>
      <div style={statsRowStyle}>
        <StatCard label="Total Failures" value={data.total_failures || failures.length} icon="❌" />
        <StatCard label="Antibodies" value={antibodies.length} icon="🧬" />
        <StatCard label="Proposals" value={proposals.length} icon="💡" />
        <StatCard label="Patterns" value={data.unique_patterns || 0} icon="🔍" />
      </div>
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{ ...tabStyle, active: tab === t.id } as any}>{t.label}</button>
        ))}
      </div>
      {tab === 'failures' && (failures.length === 0 ? <EmptyState message="No failures recorded" /> : failures.map((f: any) => (
        <div key={f.failure_id} style={cardStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontWeight: 600, color: '#f43f5e' }}>{f.error_type}</span>
            <span style={{ ...badgeStyle(f.severity), fontSize: '11px' }}>{f.severity}</span>
          </div>
          <p style={{ margin: '4px 0', fontSize: '13px' }}>{f.error_message}</p>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary, #888)' }}>
            Agent: {f.agent_id} · Task: {f.task_title || f.task_id} · {new Date(f.timestamp).toLocaleString()}
          </div>
        </div>
      )))}
      {tab === 'antibodies' && (antibodies.length === 0 ? <EmptyState message="No antibodies generated yet" /> : antibodies.map((a: any) => (
        <div key={a.pattern_signature} style={cardStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontWeight: 600, fontSize: '14px' }}>{a.pattern_signature}</span>
            <span style={{ ...badgeStyle('effectiveness'), fontSize: '11px' }}>Effectiveness: {(a.effectiveness_score * 100).toFixed(0)}%</span>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary, #888)', marginTop: '4px' }}>Failures: {a.failure_count}</div>
          {a.prevention_rules?.length > 0 && (
            <ul style={{ margin: '8px 0 0 16px', fontSize: '13px' }}>
              {a.prevention_rules.map((r: string, i: number) => <li key={i}>{r}</li>)}
            </ul>
          )}
        </div>
      )))}
      {tab === 'proposals' && (proposals.length === 0 ? <EmptyState message="No improvement proposals" /> : proposals.map((p: any) => (
        <div key={p.proposal_id || p.pattern_signature} style={cardStyle}>
          <div style={{ fontWeight: 600, fontSize: '14px' }}>{p.title || p.proposal_id}</div>
          <p style={{ margin: '4px 0', fontSize: '13px', color: 'var(--text-secondary, #888)' }}>{p.description || p.recommendation}</p>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary, #888)' }}>Status: {p.status || 'pending'}</div>
        </div>
      )))}
    </div>
  );
}

// ── Smart Router Content ──────────────────────────────

function SmartRouterContent({ data, onRefresh, showNotification }: { data: any; onRefresh: () => void; showNotification: any }) {
  const [testInput, setTestInput] = useState('');
  const [classification, setClassification] = useState<any>(null);
  const [decisions, setDecisions] = useState<any[]>([]);

  const classify = async () => {
    if (!testInput.trim()) return;
    try {
      const result = await api.platformV3.classifyDifficulty(testInput);
      setClassification(result);
    } catch (err: any) {
      showNotification('error', err.message);
    }
  };

  const route = async () => {
    if (!testInput.trim()) return;
    try {
      const result = await api.platformV3.routeTask(testInput);
      showNotification('success', `Routed to ${result.tier} (${result.model})`);
      setClassification(result);
    } catch (err: any) {
      showNotification('error', err.message);
    }
  };

  useEffect(() => {
    api.platformV3.listRoutingDecisions(10).then(r => setDecisions(r.decisions || [])).catch(() => {});
  }, [data]);

  const tierColor: Record<string, string> = { economy: '#22c55e', standard: '#3b82f6', flagship: '#f59e0b', experimental: '#8b5cf6' };

  return (
    <div>
      <div style={statsRowStyle}>
        <StatCard label="Total Routed" value={data.total_routed || 0} icon="🧭" />
        <StatCard label="Cost Saved" value={`$${(data.total_cost_saved || 0).toFixed(2)}`} icon="💰" />
        <StatCard label="Avg Confidence" value={`${((data.avg_confidence || 0) * 100).toFixed(0)}%`} icon="📊" />
      </div>
      <div style={{ ...cardStyle, marginBottom: '16px' }}>
        <h4 style={{ margin: '0 0 12px 0' }}>Test Task Routing</h4>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input value={testInput} onChange={(e) => setTestInput(e.target.value)} placeholder="Enter a task description..." style={{ flex: 1, ...inputStyle }} onKeyDown={(e) => e.key === 'Enter' && classify()} />
          <button onClick={classify} style={btnStyle}>Classify</button>
          <button onClick={route} style={btnStyle}>Route</button>
        </div>
        {classification && (
          <div style={{ marginTop: '12px', padding: '12px', background: 'var(--bg-secondary, #1a1a2e)', borderRadius: '8px' }}>
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <span>Difficulty: <strong style={{ color: tierColor[classification.difficulty] || '#888' }}>{classification.difficulty}</strong></span>
              {classification.tier && <span>Tier: <strong style={{ color: tierColor[classification.tier] }}>{classification.tier}</strong></span>}
              {classification.model && <span>Model: <strong>{classification.model}</strong></span>}
              <span>Confidence: <strong>{((classification.confidence || 0) * 100).toFixed(0)}%</strong></span>
            </div>
            {classification.reasoning && <p style={{ margin: '8px 0 0 0', fontSize: '13px', color: 'var(--text-secondary, #888)' }}>{classification.reasoning}</p>}
          </div>
        )}
      </div>
      <h3 style={sectionHeaderStyle}>Recent Decisions</h3>
      {decisions.length === 0 ? <EmptyState message="No routing decisions yet" /> : decisions.map((d: any) => (
        <div key={d.decision_id} style={cardStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '14px' }}>{d.task_description}</span>
            <span style={{ ...badgeStyle(d.tier), color: tierColor[d.tier] }}>{d.tier}</span>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary, #888)', marginTop: '4px' }}>
            {d.model} · {d.estimated_tokens} tokens · {new Date(d.timestamp).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Twin Bridge Content ───────────────────────────────

function TwinBridgeContent({ data, onRefresh }: { data: any; onRefresh: () => void }) {
  const [twins, setTwins] = useState<any[]>([]);

  useEffect(() => {
    api.platformV3.listTwins().then(r => setTwins(r.twins || [])).catch(() => {});
  }, [data]);

  return (
    <div>
      <div style={statsRowStyle}>
        <StatCard label="Total Twins" value={data.total_twins || twins.length} icon="👥" />
        <StatCard label="Active" value={twins.filter((t: any) => t.last_active).length} icon="✅" />
        <StatCard label="Bridge Connections" value={data.bridge_connections || 0} icon="🌉" />
        <StatCard label="Peer Connections" value={data.peer_connections || 0} icon="🔗" />
      </div>
      <h3 style={sectionHeaderStyle}>AI Twins</h3>
      {twins.length === 0 ? <EmptyState message="No twins created yet" /> : twins.map((twin: any) => (
        <div key={twin.twin_id} style={cardStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <span style={{ fontWeight: 600, fontSize: '15px' }}>{twin.name || twin.twin_id}</span>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary, #888)' }}>User: {twin.user_id}</div>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <span style={badgeStyle('l0')}>L0: {twin.l0_memory?.length || 0}</span>
              <span style={badgeStyle('l1')}>L1: {twin.l1_memory?.length || 0}</span>
              <span style={badgeStyle('l2')}>L2: {twin.l2_memory?.length || 0}</span>
            </div>
          </div>
          {twin.communication_style && <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: 'var(--text-secondary, #888)' }}>Style: {twin.communication_style}</p>}
          {twin.expertise_areas?.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '8px' }}>
              {twin.expertise_areas.map((area: string) => <span key={area} style={{ ...badgeStyle('expertise'), fontSize: '11px' }}>{area}</span>)}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Organization Layer Content ────────────────────────

function OrgLayerContent({ data, onRefresh, showNotification }: { data: any; onRefresh: () => void; showNotification: any }) {
  const [orgs, setOrgs] = useState<any[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<string | null>(null);
  const [structure, setStructure] = useState<any>(null);

  useEffect(() => {
    api.platformV3.listOrgs().then(r => setOrgs(r.orgs || [])).catch(() => {});
  }, [data]);

  const loadStructure = async (orgId: string) => {
    try {
      const result = await api.platformV3.getOrgStructure(orgId);
      setStructure(result);
      setSelectedOrg(orgId);
    } catch { setStructure(null); }
  };

  return (
    <div>
      <div style={statsRowStyle}>
        <StatCard label="Organizations" value={data.total_orgs || orgs.length} icon="🏢" />
        <StatCard label="Departments" value={data.total_departments || 0} icon="🏢" />
        <StatCard label="Teams" value={data.total_teams || 0} icon="👥" />
        <StatCard label="Members" value={data.total_members || 0} icon="👤" />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '16px' }}>
        <div>
          <h3 style={sectionHeaderStyle}>Organizations</h3>
          {orgs.length === 0 ? <EmptyState message="No organizations yet" /> : orgs.map((org: any) => (
            <div key={org.org_id} style={{
              ...cardStyle,
              border: selectedOrg === org.org_id ? '2px solid var(--accent, #3b82f6)' : '1px solid var(--border, #333)',
            }} onClick={() => loadStructure(org.org_id)}>
              <div style={{ fontWeight: 600, fontSize: '15px' }}>{org.name}</div>
              {org.description && <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: 'var(--text-secondary, #888)' }}>{org.description}</p>}
            </div>
          ))}
        </div>
        <div>
          <h3 style={sectionHeaderStyle}>Structure {selectedOrg ? '' : '(select an org)'}</h3>
          {!structure ? <EmptyState message="Select an organization to view structure" /> : (
            <div>
              {structure.departments?.map((dept: any) => (
                <div key={dept.department_id} style={{ ...cardStyle, marginLeft: '0' }}>
                  <div style={{ fontWeight: 600, fontSize: '14px' }}>📁 {dept.name}</div>
                  {dept.teams?.map((team: any) => (
                    <div key={team.team_id} style={{ marginLeft: '20px', marginTop: '8px' }}>
                      <div style={{ fontSize: '13px', fontWeight: 500 }}>👥 {team.name}</div>
                      {team.members?.map((m: any) => (
                        <div key={m.member_id} style={{ marginLeft: '20px', fontSize: '12px', color: 'var(--text-secondary, #888)' }}>
                          👤 {m.agent_id} ({m.role_id})
                        </div>
                      ))}
                      {team.workspace_ids?.length > 0 && (
                        <div style={{ marginLeft: '20px', fontSize: '12px', color: 'var(--text-secondary, #888)' }}>
                          Workspaces: {team.workspace_ids.join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Create Form ───────────────────────────────────────

function CreateForm({ subsystem, onSubmit }: { subsystem: PlatformPanelProps['subsystem']; onSubmit: (data: Record<string, string>) => void }) {
  const [formData, setFormData] = useState<Record<string, string>>({});

  const fields: Record<string, { key: string; label: string; placeholder: string; required?: boolean }[]> = {
    workspace: [
      { key: 'name', label: 'Name', placeholder: 'My Workspace', required: true },
      { key: 'owner_agent_id', label: 'Owner Agent ID', placeholder: 'agent-001', required: true },
      { key: 'description', label: 'Description', placeholder: 'Optional description' },
    ],
    taskWall: [
      { key: 'title', label: 'Title', placeholder: 'Task title', required: true },
      { key: 'priority', label: 'Priority', placeholder: 'medium' },
      { key: 'description', label: 'Description', placeholder: 'Task description' },
    ],
    orgLayer: [
      { key: 'name', label: 'Name', placeholder: 'Organization name', required: true },
      { key: 'description', label: 'Description', placeholder: 'Optional description' },
    ],
    twinBridge: [
      { key: 'name', label: 'Twin Name', placeholder: 'My AI Twin', required: true },
      { key: 'agent_id', label: 'Agent ID', placeholder: 'agent-001' },
    ],
  };

  const currentFields = fields[subsystem] || [];
  if (currentFields.length === 0) return null;

  return (
    <div style={{ ...cardStyle, marginBottom: '16px' }}>
      <h4 style={{ margin: '0 0 12px 0' }}>Create New</h4>
      {currentFields.map(f => (
        <div key={f.key} style={{ marginBottom: '8px' }}>
          <label style={{ fontSize: '13px', display: 'block', marginBottom: '4px' }}>{f.label}</label>
          <input
            value={formData[f.key] || ''}
            onChange={(e) => setFormData({ ...formData, [f.key]: e.target.value })}
            placeholder={f.placeholder}
            style={{ ...inputStyle, width: '100%' }}
          />
        </div>
      ))}
      <button
        onClick={() => {
          const required = currentFields.filter(f => f.required);
          if (required.every(f => formData[f.key]?.trim())) {
            onSubmit(formData);
          }
        }}
        style={{ ...btnStyle, marginTop: '8px' }}
      >
        Create
      </button>
    </div>
  );
}

// ── Shared UI Components ──────────────────────────────

const btnStyle: React.CSSProperties = {
  padding: '8px 16px',
  borderRadius: '8px',
  border: '1px solid var(--border, #333)',
  background: 'var(--bg-secondary, #1a1a2e)',
  color: 'var(--text, #eee)',
  cursor: 'pointer',
  fontSize: '13px',
  fontWeight: 500,
};

const btnSmStyle: React.CSSProperties = {
  ...btnStyle,
  padding: '4px 10px',
  fontSize: '12px',
};

const inputStyle: React.CSSProperties = {
  padding: '8px 12px',
  borderRadius: '8px',
  border: '1px solid var(--border, #333)',
  background: 'var(--bg-secondary, #1a1a2e)',
  color: 'var(--text, #eee)',
  fontSize: '14px',
  outline: 'none',
};

const cardStyle: React.CSSProperties = {
  padding: '16px',
  borderRadius: '12px',
  border: '1px solid var(--border, #333)',
  background: 'var(--bg-secondary, #1a1a2e)',
  marginBottom: '12px',
  cursor: 'default',
};

const statsRowStyle: React.CSSProperties = {
  display: 'flex',
  gap: '12px',
  marginBottom: '16px',
  flexWrap: 'wrap',
};

const sectionHeaderStyle: React.CSSProperties = {
  margin: '0 0 12px 0',
  fontSize: '16px',
  fontWeight: 600,
};

const tabStyle: React.CSSProperties = {
  padding: '8px 16px',
  borderRadius: '8px',
  border: '1px solid var(--border, #333)',
  background: 'var(--bg-secondary, #1a1a2e)',
  color: 'var(--text, #eee)',
  cursor: 'pointer',
  fontSize: '13px',
};

function StatCard({ label, value, icon }: { label: string; value: any; icon: string }) {
  return (
    <div style={{
      padding: '16px',
      borderRadius: '12px',
      border: '1px solid var(--border, #333)',
      background: 'var(--bg-secondary, #1a1a2e)',
      minWidth: '120px',
      flex: '1',
    }}>
      <div style={{ fontSize: '24px', marginBottom: '4px' }}>{icon}</div>
      <div style={{ fontSize: '24px', fontWeight: 700 }}>{typeof value === 'number' ? value : value}</div>
      <div style={{ fontSize: '12px', color: 'var(--text-secondary, #888)' }}>{label}</div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-secondary, #888)', fontSize: '14px' }}>
      {message}
    </div>
  );
}

function badgeStyle(type: string): React.CSSProperties {
  const colors: Record<string, string> = {
    critical: '#ef4444',
    high: '#f97316',
    medium: '#eab308',
    low: '#22c55e',
    deferred: '#6b7280',
    archived: '#6b7280',
    cap: '#3b82f6',
    expertise: '#8b5cf6',
    effectiveness: '#22c55e',
    l0: '#22c55e',
    l1: '#3b82f6',
    l2: '#8b5cf6',
  };
  const color = colors[type] || '#6b7280';
  return {
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: 500,
    background: `${color}20`,
    color,
  };
}
