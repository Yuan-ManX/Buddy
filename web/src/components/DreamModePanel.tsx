import React, { useState, useEffect } from 'react';

interface DreamStats {
  is_dreaming: boolean;
  total_memories: number;
  total_sessions: number;
  total_memories_consolidated: number;
  total_proactive_tasks: number;
  total_snapshots: number;
  current_phase: string;
  idle_threshold_seconds: number;
  memories_by_importance: { high: number; medium: number; low: number };
  pinned_memories: number;
  last_session: any;
  proactive_tasks: { task_id: string; description: string; priority: number; auto_executable: boolean }[];
}

interface MemoryItem {
  entry_id: string;
  content: string;
  importance: number;
  pinned: boolean;
  access_count: number;
  tags: string[];
}

export const DreamModePanel: React.FC = () => {
  const [stats, setStats] = useState<DreamStats | null>(null);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [showAddMemory, setShowAddMemory] = useState(false);
  const [memoryForm, setMemoryForm] = useState({ content: '', source: 'manual', importance: 0.5, tags: '', workspace_id: '' });
  const [loading, setLoading] = useState(false);
  const [dreaming, setDreaming] = useState(false);

  useEffect(() => {
    fetchStats();
    fetchMemories();
    fetchTasks();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/dream-mode/stats');
      const data = await res.json();
      setStats(data);
      setDreaming(data.is_dreaming);
    } catch (e) { console.error('Failed to fetch dream stats:', e); }
  };

  const fetchMemories = async () => {
    try {
      const res = await fetch('/api/dream-mode/memories');
      const data = await res.json();
      setMemories(data.memories || []);
    } catch (e) { console.error('Failed to fetch memories:', e); }
  };

  const fetchTasks = async () => {
    try {
      const res = await fetch('/api/dream-mode/tasks');
      const data = await res.json();
      setTasks(data.tasks || []);
    } catch (e) { console.error('Failed to fetch tasks:', e); }
  };

  const startDream = async () => {
    setLoading(true);
    setDreaming(true);
    try {
      await fetch('/api/dream-mode/start', { method: 'POST' });
      fetchStats();
      fetchMemories();
      fetchTasks();
    } catch (e) { console.error('Dream start failed:', e); }
    setLoading(false);
    setDreaming(false);
  };

  const stopDream = async () => {
    await fetch('/api/dream-mode/stop', { method: 'POST' });
    fetchStats();
  };

  const addMemory = async () => {
    setLoading(true);
    try {
      await fetch('/api/dream-mode/add-memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...memoryForm,
          tags: memoryForm.tags.split(',').map(s => s.trim()).filter(Boolean),
        }),
      });
      setShowAddMemory(false);
      setMemoryForm({ content: '', source: 'manual', importance: 0.5, tags: '', workspace_id: '' });
      fetchStats();
      fetchMemories();
    } catch (e) { console.error('Add memory failed:', e); }
    setLoading(false);
  };

  const pinMemory = async (entryId: string) => {
    await fetch('/api/dream-mode/pin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entry_id: entryId }),
    });
    fetchMemories();
  };

  const createSnapshot = async () => {
    await fetch('/api/dream-mode/snapshot', { method: 'POST' });
    fetchStats();
  };

  const phaseColor = (phase: string) => {
    const colors: Record<string, string> = {
      light_sleep: '#a78bfa', deep_sleep: '#7c3aed', rem_sleep: '#ec4899',
      awake: '#16a34a', interrupted: '#f59e0b',
    };
    return colors[phase] || '#9ca3af';
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Dream Mode</h2>
          <p style={{ color: '#666', margin: '4px 0 0' }}>Background memory consolidation with proactive task discovery</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={createSnapshot} style={{ padding: '8px 16px', background: '#6b7280', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
            Snapshot
          </button>
          <button onClick={() => setShowAddMemory(true)} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
            + Add Memory
          </button>
          {stats && !stats.is_dreaming ? (
            <button onClick={startDream} disabled={loading} style={{ padding: '8px 16px', background: loading ? '#999' : '#7c3aed', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'default' : 'pointer' }}>
              {loading ? 'Dreaming...' : 'Start Dream'}
            </button>
          ) : (
            <button onClick={stopDream} style={{ padding: '8px 16px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
              Stop Dream
            </button>
          )}
        </div>
      </div>

      {/* Dream Status */}
      {stats && (
        <div style={{ background: dreaming ? '#faf5ff' : '#f0fdf4', borderRadius: 12, padding: 16, marginBottom: 24, border: `2px solid ${dreaming ? '#7c3aed' : '#16a34a'}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
            <div style={{ width: 12, height: 12, borderRadius: '50%', background: dreaming ? '#7c3aed' : '#16a34a', animation: dreaming ? 'pulse 1.5s infinite' : 'none' }} />
            <span style={{ fontWeight: 600, fontSize: 14 }}>{dreaming ? 'Dreaming' : 'Awake'}</span>
            <span style={{ background: phaseColor(stats.current_phase), color: '#fff', padding: '2px 8px', borderRadius: 6, fontSize: 11, textTransform: 'uppercase' }}>
              {stats.current_phase.replace('_', ' ')}
            </span>
          </div>
          <div style={{ display: 'flex', gap: 24, fontSize: 13, color: '#666' }}>
            <span>{stats.total_memories} total memories</span>
            <span>{stats.total_sessions} sessions</span>
            <span>{stats.pinned_memories} pinned</span>
            <span>{stats.total_snapshots} snapshots</span>
          </div>
        </div>
      )}

      {/* Stats */}
      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <div style={{ flex: 1, background: '#fef3c7', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#d97706' }}>{stats.memories_by_importance.high}</div>
            <div style={{ fontSize: 12, color: '#666' }}>High Importance</div>
          </div>
          <div style={{ flex: 1, background: '#eff6ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.memories_by_importance.medium}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Medium</div>
          </div>
          <div style={{ flex: 1, background: '#f3f4f6', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#6b7280' }}>{stats.memories_by_importance.low}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Low Importance</div>
          </div>
          <div style={{ flex: 1, background: '#faf5ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#7c3aed' }}>{stats.total_proactive_tasks}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Proactive Tasks</div>
          </div>
        </div>
      )}

      {/* Add Memory Form */}
      {showAddMemory && (
        <div style={{ background: '#f8fafc', borderRadius: 12, padding: 16, marginBottom: 16, border: '1px solid #e2e8f0' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Add Memory Entry</h3>
          <textarea value={memoryForm.content} onChange={e => setMemoryForm({ ...memoryForm, content: e.target.value })} placeholder="Memory content" rows={3} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', resize: 'vertical', marginBottom: 8 }} />
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <input value={memoryForm.importance} type="number" onChange={e => setMemoryForm({ ...memoryForm, importance: Number(e.target.value) })} min={0} max={1} step={0.1} style={{ width: 100, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }} placeholder="Importance" />
            <input value={memoryForm.tags} onChange={e => setMemoryForm({ ...memoryForm, tags: e.target.value })} placeholder="Tags (comma-separated)" style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }} />
            <input value={memoryForm.workspace_id} onChange={e => setMemoryForm({ ...memoryForm, workspace_id: e.target.value })} placeholder="Workspace ID" style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }} />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={addMemory} disabled={loading} style={{ padding: '8px 16px', background: loading ? '#999' : '#16a34a', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'default' : 'pointer' }}>
              {loading ? 'Adding...' : 'Add Memory'}
            </button>
            <button onClick={() => setShowAddMemory(false)} style={{ padding: '8px 16px', background: '#e5e7eb', color: '#374151', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
          </div>
        </div>
      )}

      {/* Proactive Tasks */}
      <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Proactive Tasks ({tasks.length})</h3>
      <div style={{ display: 'grid', gap: 8, marginBottom: 24 }}>
        {tasks.map(task => (
          <div key={task.task_id} style={{ background: '#fff', borderRadius: 12, padding: 12, border: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ background: task.auto_executable ? '#d1fae5' : '#fef3c7', color: task.auto_executable ? '#065f46' : '#92400e', padding: '2px 8px', borderRadius: 6, fontSize: 11 }}>
              {task.auto_executable ? 'Auto' : 'Manual'}
            </span>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500, fontSize: 13 }}>{task.description}</div>
            </div>
            <span style={{ background: '#f3f4f6', padding: '2px 8px', borderRadius: 6, fontSize: 11 }}>P{task.priority}</span>
          </div>
        ))}
        {tasks.length === 0 && <div style={{ color: '#888', fontSize: 13, textAlign: 'center', padding: 24 }}>No proactive tasks discovered yet. Start a dream session to discover tasks.</div>}
      </div>

      {/* Memory List */}
      <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Memories ({memories.length})</h3>
      <div style={{ display: 'grid', gap: 8 }}>
        {memories.map(mem => (
          <div key={mem.entry_id} style={{ background: '#fff', borderRadius: 12, padding: 12, border: '1px solid #e2e8f0', display: 'flex', alignItems: 'flex-start', gap: 12 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13 }}>{mem.content}</div>
              <div style={{ display: 'flex', gap: 8, marginTop: 4, fontSize: 11, color: '#888' }}>
                <span>Importance: {(mem.importance * 100).toFixed(0)}%</span>
                <span>Accesses: {mem.access_count}</span>
                {mem.tags.map(t => <span key={t} style={{ background: '#eff6ff', color: '#2563eb', padding: '1px 6px', borderRadius: 4 }}>{t}</span>)}
              </div>
            </div>
            {!mem.pinned && (
              <button onClick={() => pinMemory(mem.entry_id)} style={{ padding: '4px 10px', background: '#f3f4f6', color: '#374151', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 11, whiteSpace: 'nowrap' }}>
                Pin
              </button>
            )}
            {mem.pinned && <span style={{ fontSize: 11, color: '#7c3aed' }}>Pinned</span>}
          </div>
        ))}
        {memories.length === 0 && <div style={{ color: '#888', fontSize: 13, textAlign: 'center', padding: 24 }}>No memories yet. Add memories to begin.</div>}
      </div>
    </div>
  );
};