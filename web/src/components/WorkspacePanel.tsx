import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import type { WorkSpaceManagerConfig, WorkSpaceManagerStats, WorkSpaceManagerSnapshot } from '../types';

export const WorkspacePanel: React.FC = () => {
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [workspaces, setWorkspaces] = useState<WorkSpaceManagerConfig[]>([]);
  const [stats, setStats] = useState<WorkSpaceManagerStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'list' | 'files' | 'memory' | 'skills' | 'snapshots'>('list');
  const [selectedWsId, setSelectedWsId] = useState<string | null>(null);
  const [newWorkspace, setNewWorkspace] = useState({
    name: '', description: '', isolate_files: true, isolate_memory: true, isolate_skills: true, tags: '',
  });

  // File management
  const [files, setFiles] = useState<Array<{ path: string; size: number; modified_at: string }>>([]);
  const [fileContent, setFileContent] = useState<string>('');
  const [selectedFilePath, setSelectedFilePath] = useState<string>('');
  const [newFileName, setNewFileName] = useState('');
  const [newFileContent, setNewFileContent] = useState('');

  // Memory management
  const [memories, setMemories] = useState<Array<Record<string, unknown>>>([]);
  const [newMemoryKey, setNewMemoryKey] = useState('');
  const [newMemoryValue, setNewMemoryValue] = useState('');
  const [newMemoryTags, setNewMemoryTags] = useState('');

  // Skill management
  const [skills, setSkills] = useState<Array<{ name: string; definition: Record<string, unknown> }>>([]);
  const [newSkillName, setNewSkillName] = useState('');
  const [newSkillDef, setNewSkillDef] = useState('{}');

  // Snapshots
  const [snapshots, setSnapshots] = useState<WorkSpaceManagerSnapshot[]>([]);
  const [snapshotDesc, setSnapshotDesc] = useState('');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [wsStats, wsList] = await Promise.all([
        api.workspaceManager.stats(),
        api.workspaceManager.list(),
      ]);
      setStats(wsStats);
      setWorkspaces(wsList.workspaces as unknown as WorkSpaceManagerConfig[]);
    } catch (e: any) {
      setError(e.message || 'Failed to load workspaces');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreate = async () => {
    if (!newWorkspace.name.trim()) return;
    try {
      const result = await api.workspaceManager.create({
        name: newWorkspace.name.trim(),
        description: newWorkspace.description.trim(),
        isolate_files: newWorkspace.isolate_files,
        isolate_memory: newWorkspace.isolate_memory,
        isolate_skills: newWorkspace.isolate_skills,
        tags: newWorkspace.tags ? newWorkspace.tags.split(',').map(t => t.trim()).filter(Boolean) : undefined,
      });
      setShowCreate(false);
      setNewWorkspace({ name: '', description: '', isolate_files: true, isolate_memory: true, isolate_skills: true, tags: '' });
      toast.success('Workspace created');
      loadData();
    } catch (e: any) {
      toast.error(e.message || 'Failed to create workspace');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.workspaceManager.delete(id);
      setDeleteConfirm(null);
      if (selectedWsId === id) setSelectedWsId(null);
      toast.success('Workspace deleted');
      loadData();
    } catch (e: any) {
      toast.error(e.message || 'Failed to delete workspace');
    }
  };

  const handleActivate = async (id: string) => {
    try {
      await api.workspaceManager.activate(id);
      toast.success('Workspace activated');
      loadData();
    } catch (e: any) {
      toast.error(e.message || 'Failed to activate workspace');
    }
  };

  const selectWorkspace = async (wsId: string) => {
    setSelectedWsId(wsId);
    setActiveSection('files');
    try {
      const [fileList, memList] = await Promise.all([
        api.workspaceManager.listFiles(wsId),
        api.workspaceManager.listMemories(wsId),
      ]);
      setFiles(fileList.files);
      setMemories(memList.memories);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load workspace details');
    }
  };

  const handleReadFile = async (path: string) => {
    if (!selectedWsId) return;
    try {
      const result = await api.workspaceManager.readFile(selectedWsId, path);
      setSelectedFilePath(path);
      setFileContent(result.content);
    } catch (e: any) {
      toast.error(e.message || 'Failed to read file');
    }
  };

  const handleWriteFile = async () => {
    if (!selectedWsId || !newFileName.trim() || !newFileContent.trim()) return;
    try {
      await api.workspaceManager.writeFile(selectedWsId, newFileName, newFileContent);
      setNewFileName(''); setNewFileContent('');
      toast.success('File written');
      const fileList = await api.workspaceManager.listFiles(selectedWsId);
      setFiles(fileList.files);
    } catch (e: any) {
      toast.error(e.message || 'Failed to write file');
    }
  };

  const handleAddMemory = async () => {
    if (!selectedWsId || !newMemoryKey.trim() || !newMemoryValue.trim()) return;
    try {
      const tags = newMemoryTags ? newMemoryTags.split(',').map(t => t.trim()).filter(Boolean) : undefined;
      let value: unknown = newMemoryValue;
      try { value = JSON.parse(newMemoryValue); } catch {}
      await api.workspaceManager.addMemory(selectedWsId, newMemoryKey, value, tags);
      setNewMemoryKey(''); setNewMemoryValue(''); setNewMemoryTags('');
      toast.success('Memory added');
      const memList = await api.workspaceManager.listMemories(selectedWsId);
      setMemories(memList.memories);
    } catch (e: any) {
      toast.error(e.message || 'Failed to add memory');
    }
  };

  const handleAddSkill = async () => {
    if (!selectedWsId || !newSkillName.trim() || !newSkillDef.trim()) return;
    try {
      const def = JSON.parse(newSkillDef);
      await api.workspaceManager.addSkill(selectedWsId, newSkillName, def);
      setNewSkillName(''); setNewSkillDef('{}');
      toast.success('Skill added');
    } catch (e: any) {
      toast.error(e.message || 'Failed to add skill');
    }
  };

  const handleSnapshot = async () => {
    if (!selectedWsId) return;
    try {
      const snap = await api.workspaceManager.snapshot(selectedWsId, snapshotDesc || undefined);
      setSnapshots(prev => [snap, ...prev]);
      setSnapshotDesc('');
      toast.success('Snapshot created');
    } catch (e: any) {
      toast.error(e.message || 'Failed to create snapshot');
    }
  };

  const handleExport = async (id: string) => {
    try {
      const data = await api.workspaceManager.get(id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `workspace-${id}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Workspace exported');
    } catch (e: any) {
      toast.error(e.message || 'Failed to export workspace');
    }
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const imported = JSON.parse(text);
      await api.workspaceManager.create({
        name: imported.name || 'Imported Workspace',
        description: imported.description || '',
      });
      toast.success('Workspace imported');
      loadData();
    } catch (err: any) {
      toast.error(err.message || 'Failed to import workspace');
    }
    e.target.value = '';
  };

  const formatTime = (iso: string) => iso ? new Date(iso).toLocaleString() : 'N/A';
  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>WorkSpaces</h2>
          <p className="panel-subtitle">Manage isolated workspaces with independent file systems, memory, and skills</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading workspaces...</span></div>
        <style>{styles}</style>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div>
          <h2>WorkSpaces</h2>
          <p className="panel-subtitle">Manage isolated workspaces with independent file systems, memory, and skills</p>
        </div>
        {error && <div className="error-banner">{error}</div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <span className="stat-icon">WS</span>
            <div className="stat-content">
              <span className="stat-value">{stats.total_workspaces}</span>
              <span className="stat-label">Total Workspaces</span>
            </div>
          </div>
          <div className="stat-item">
            <span className="stat-icon">Active</span>
            <div className="stat-content">
              <span className="stat-value" style={{ fontSize: '0.85rem', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {stats.active_workspace || 'None'}
              </span>
              <span className="stat-label">Active Workspace</span>
            </div>
          </div>
          <div className="stat-item">
            <span className="stat-icon">Docs</span>
            <div className="stat-content">
              <span className="stat-value">{stats.total_files}</span>
              <span className="stat-label">Total Files</span>
            </div>
          </div>
          <div className="stat-item">
            <span className="stat-icon">Mem</span>
            <div className="stat-content">
              <span className="stat-value">{stats.total_memories}</span>
              <span className="stat-label">Total Memories</span>
            </div>
          </div>
          <div className="stat-item">
            <span className="stat-icon">Skills</span>
            <div className="stat-content">
              <span className="stat-value">{stats.total_skills}</span>
              <span className="stat-label">Total Skills</span>
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="action-bar">
        <button className="btn-primary-sm" onClick={() => setShowCreate(true)}>+ New Workspace</button>
        <button className="btn-secondary-sm" onClick={handleImportClick}>Import</button>
        <button className="btn-secondary-sm" onClick={loadData}>Refresh</button>
        <input ref={fileInputRef} type="file" accept=".json" style={{ display: 'none' }} onChange={handleImportFile} />
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Create Workspace</h3>
            <div className="form-group">
              <label>Name</label>
              <input type="text" value={newWorkspace.name}
                onChange={e => setNewWorkspace({ ...newWorkspace, name: e.target.value })}
                placeholder="Workspace name" autoFocus />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea rows={2} value={newWorkspace.description}
                onChange={e => setNewWorkspace({ ...newWorkspace, description: e.target.value })}
                placeholder="Optional description" />
            </div>
            <div className="form-group">
              <label>Tags (comma-separated)</label>
              <input type="text" value={newWorkspace.tags}
                onChange={e => setNewWorkspace({ ...newWorkspace, tags: e.target.value })}
                placeholder="project, ai, dev" />
            </div>
            <div style={{ display: 'flex', gap: '16px', marginBottom: '14px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', cursor: 'pointer' }}>
                <input type="checkbox" checked={newWorkspace.isolate_files}
                  onChange={e => setNewWorkspace({ ...newWorkspace, isolate_files: e.target.checked })} />
                Isolate Files
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', cursor: 'pointer' }}>
                <input type="checkbox" checked={newWorkspace.isolate_memory}
                  onChange={e => setNewWorkspace({ ...newWorkspace, isolate_memory: e.target.checked })} />
                Isolate Memory
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', cursor: 'pointer' }}>
                <input type="checkbox" checked={newWorkspace.isolate_skills}
                  onChange={e => setNewWorkspace({ ...newWorkspace, isolate_skills: e.target.checked })} />
                Isolate Skills
              </label>
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleCreate}>Create</button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="modal-overlay" onClick={() => setDeleteConfirm(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Delete Workspace</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 20, fontSize: '0.9rem' }}>
              Are you sure you want to delete this workspace? This action cannot be undone.
            </p>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setDeleteConfirm(null)}>Cancel</button>
              <button className="btn-danger" onClick={() => handleDelete(deleteConfirm)}>Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Workspace List */}
      <div className="workspace-list">
        {workspaces.length === 0 ? (
          <div className="panel-empty">
            <p>No workspaces yet</p>
            <p>Create your first workspace to get started</p>
          </div>
        ) : (
          workspaces.map((ws: any) => {
            const isActive = stats?.active_workspace === ws.workspace_id;
            return (
              <div key={ws.workspace_id} className={`workspace-card ${isActive ? 'active' : ''}`}>
                <div className="workspace-card-header">
                  <div className="workspace-title-row">
                    {isActive && <span className="active-dot" title="Active workspace" />}
                    <h4 className="workspace-name">{ws.name}</h4>
                    {isActive && <span className="active-badge">Active</span>}
                  </div>
                  <div className="workspace-card-actions">
                    <button className="btn-mini" onClick={() => selectWorkspace(ws.workspace_id)} title="Open workspace">
                      Open
                    </button>
                    <button className="btn-mini" onClick={() => handleExport(ws.workspace_id)} title="Export workspace">
                      Export
                    </button>
                    {!isActive && (
                      <button className="btn-mini" onClick={() => handleActivate(ws.workspace_id)} title="Activate">
                        Activate
                      </button>
                    )}
                    <button className="btn-mini danger" onClick={() => setDeleteConfirm(ws.workspace_id)} title="Delete">
                      Delete
                    </button>
                  </div>
                </div>
                {ws.description && <p className="workspace-description">{ws.description}</p>}
                <div className="workspace-meta-row">
                  <div className="workspace-meta">
                    <span className="meta-item">{ws.file_count ?? 0} files</span>
                    <span className="meta-item">{ws.memory_entries ?? 0} memories</span>
                    <span className="meta-item">{ws.skill_count ?? 0} skills</span>
                  </div>
                  <div className="workspace-meta-right">
                    <span className="meta-time">Created: {formatTime(ws.created_at)}</span>
                  </div>
                </div>
                {ws.tags && ws.tags.length > 0 && (
                  <div style={{ marginTop: '8px', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {ws.tags.map((tag: string) => (
                      <span key={tag} className="memory-card-tag">{tag}</span>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Workspace Detail View */}
      {selectedWsId && (
        <div className="workspace-detail" style={{ marginTop: '24px' }}>
          <div className="workspace-detail-header">
            <h3>Workspace Details</h3>
            <div className="section-tabs">
              {(['list', 'files', 'memory', 'skills', 'snapshots'] as const).map(sec => (
                <button
                  key={sec}
                  className={`section-tab ${activeSection === sec ? 'active' : ''}`}
                  onClick={() => setActiveSection(sec)}
                >
                  {sec.charAt(0).toUpperCase() + sec.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Files Section */}
          {activeSection === 'files' && (
            <div>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
                <input type="text" value={newFileName} onChange={e => setNewFileName(e.target.value)}
                  placeholder="File path (e.g. src/main.py)" style={{ flex: 1, minWidth: '200px', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-card)', color: 'var(--text)' }} />
                <button className="btn-primary-sm" onClick={handleWriteFile}>Write File</button>
              </div>
              <textarea rows={4} value={newFileContent} onChange={e => setNewFileContent(e.target.value)}
                placeholder="File content..." style={{ width: '100%', padding: '10px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem', fontFamily: 'monospace', background: 'var(--bg-card)', color: 'var(--text)', marginBottom: '12px', resize: 'vertical' }} />

              {files.length === 0 ? (
                <div className="panel-empty">No files in this workspace</div>
              ) : (
                <div className="subagent-tasks">
                  {files.map(f => (
                    <div key={f.path} className="skill-card" style={{ cursor: 'pointer' }} onClick={() => handleReadFile(f.path)}>
                      <div className="skill-card-info">
                        <div className="skill-card-name">{f.path}</div>
                        <div className="skill-card-cat">{formatBytes(f.size)} · {formatTime(f.modified_at)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {selectedFilePath && fileContent && (
                <div style={{ marginTop: '16px' }}>
                  <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '8px', color: 'var(--text)' }}>
                    {selectedFilePath}
                  </h4>
                  <pre style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '8px', padding: '12px', fontSize: '0.8rem', fontFamily: 'monospace', overflow: 'auto', maxHeight: '300px', whiteSpace: 'pre-wrap', color: 'var(--text)' }}>
                    {fileContent}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* Memory Section */}
          {activeSection === 'memory' && (
            <div>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
                <input type="text" value={newMemoryKey} onChange={e => setNewMemoryKey(e.target.value)}
                  placeholder="Key" style={{ width: '150px', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-card)', color: 'var(--text)' }} />
                <input type="text" value={newMemoryValue} onChange={e => setNewMemoryValue(e.target.value)}
                  placeholder="Value" style={{ flex: 1, minWidth: '200px', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-card)', color: 'var(--text)' }} />
                <input type="text" value={newMemoryTags} onChange={e => setNewMemoryTags(e.target.value)}
                  placeholder="Tags (comma-separated)" style={{ width: '150px', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-card)', color: 'var(--text)' }} />
                <button className="btn-primary-sm" onClick={handleAddMemory}>Add Memory</button>
              </div>
              {memories.length === 0 ? (
                <div className="panel-empty">No memories in this workspace</div>
              ) : (
                <div className="subagent-tasks">
                  {memories.map((mem: any, i: number) => (
                    <div key={i} className="skill-card">
                      <div className="skill-card-info">
                        <div className="skill-card-name">{mem.key || `Entry ${i + 1}`}</div>
                        <div className="skill-card-desc">{typeof mem.value === 'string' ? mem.value : JSON.stringify(mem.value)}</div>
                        {mem.tags && mem.tags.length > 0 && (
                          <div style={{ display: 'flex', gap: '4px', marginTop: '4px' }}>
                            {mem.tags.map((tag: string) => (
                              <span key={tag} className="memory-card-tag">{tag}</span>
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

          {/* Skills Section */}
          {activeSection === 'skills' && (
            <div>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
                <input type="text" value={newSkillName} onChange={e => setNewSkillName(e.target.value)}
                  placeholder="Skill name" style={{ width: '200px', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-card)', color: 'var(--text)' }} />
                <input type="text" value={newSkillDef} onChange={e => setNewSkillDef(e.target.value)}
                  placeholder='Definition (JSON)' style={{ flex: 1, minWidth: '200px', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-card)', color: 'var(--text)', fontFamily: 'monospace' }} />
                <button className="btn-primary-sm" onClick={handleAddSkill}>Add Skill</button>
              </div>
              <div className="panel-empty">Skills registered in this workspace will appear here.</div>
            </div>
          )}

          {/* Snapshots Section */}
          {activeSection === 'snapshots' && (
            <div>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                <input type="text" value={snapshotDesc} onChange={e => setSnapshotDesc(e.target.value)}
                  placeholder="Snapshot description" style={{ flex: 1, padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-card)', color: 'var(--text)' }} />
                <button className="btn-primary-sm" onClick={handleSnapshot}>Create Snapshot</button>
              </div>
              {snapshots.length === 0 ? (
                <div className="panel-empty">No snapshots yet</div>
              ) : (
                <div className="subagent-tasks">
                  {snapshots.map(snap => (
                    <div key={snap.snapshot_id} className="skill-card">
                      <div className="skill-card-info">
                        <div className="skill-card-name">{snap.description || snap.snapshot_id}</div>
                        <div className="skill-card-cat">
                          {snap.file_count} files · {snap.memory_entries} memories · {snap.skill_count} skills · {formatTime(snap.created_at)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <style>{styles}</style>
    </div>
  );
};

const styles = `
.panel-container { padding: 24px; max-width: 1400px; margin: 0 auto; }
.panel-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.panel-header h2 { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; color: var(--text, #1f2937); }
.panel-subtitle { color: var(--text-secondary, #6b7280); margin-bottom: 0; font-size: 0.85rem; }
.panel-loading { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 0; color: var(--text-secondary); gap: 16px; font-size: 0.95rem; }
.spinner { width: 32px; height: 32px; border: 3px solid var(--border); border-top-color: #3b82f6; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.error-banner { background: #fef2f2; color: #991b1b; padding: 10px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 0.85rem; }
.panel-empty { text-align: center; padding: 40px 0; color: var(--text-secondary); }
.panel-empty p { font-size: 0.9rem; margin-bottom: 4px; }

.stats-bar { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.stat-item { flex: 1; min-width: 120px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 14px 18px; display: flex; align-items: center; gap: 12px; }
.stat-icon { font-size: 0.75rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; min-width: 36px; }
.stat-content { display: flex; flex-direction: column; }
.stat-value { font-size: 1.3rem; font-weight: 800; color: var(--text); }
.stat-label { font-size: 0.72rem; color: var(--text-secondary); font-weight: 600; }

.action-bar { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
.btn-primary-sm { padding: 8px 16px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
.btn-primary-sm:hover { background: #2563eb; }
.btn-secondary-sm { padding: 8px 16px; background: var(--bg-card); color: var(--text); border: 1px solid var(--border); border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
.btn-secondary-sm:hover { border-color: #3b82f6; color: #3b82f6; }

.workspace-list { display: flex; flex-direction: column; gap: 12px; }
.workspace-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; transition: all 0.15s; }
.workspace-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.workspace-card.active { border-color: #86efac; background: #f0fdf4; }
.workspace-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.workspace-title-row { display: flex; align-items: center; gap: 8px; }
.active-dot { width: 10px; height: 10px; border-radius: 50%; background: #22c55e; flex-shrink: 0; box-shadow: 0 0 6px rgba(34, 197, 94, 0.5); }
.workspace-name { font-size: 1rem; font-weight: 700; color: var(--text); margin: 0; }
.active-badge { font-size: 0.65rem; font-weight: 700; background: #22c55e; color: #fff; padding: 2px 8px; border-radius: 12px; text-transform: uppercase; }
.workspace-card-actions { display: flex; gap: 6px; flex-shrink: 0; }
.workspace-description { font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 12px; line-height: 1.4; }
.workspace-meta-row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.workspace-meta { display: flex; gap: 16px; flex-wrap: wrap; }
.meta-item { font-size: 0.8rem; color: var(--text-secondary); }
.workspace-meta-right { display: flex; gap: 16px; flex-wrap: wrap; }
.meta-time { font-size: 0.75rem; color: var(--text-secondary); }
.memory-card-tag { padding: 2px 8px; background: var(--bg); border: 1px solid var(--border); border-radius: 4px; font-size: 0.7rem; color: var(--text-secondary); font-weight: 600; }

.btn-mini { padding: 4px 10px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 6px; font-size: 0.72rem; cursor: pointer; color: var(--text); transition: all 0.15s; white-space: nowrap; }
.btn-mini:hover { border-color: #3b82f6; color: #3b82f6; }
.btn-mini.danger { color: #dc2626; border-color: #fecaca; background: #fef2f2; }
.btn-mini.danger:hover { background: #fee2e2; }

.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px; color: var(--text); }
.form-group input, .form-group textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 0.9rem; background: var(--bg-card); color: var(--text); font-family: inherit; }
.form-group textarea { resize: vertical; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: var(--bg-card); border-radius: 16px; padding: 28px; width: 90%; max-width: 500px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
.modal h3 { font-size: 1.15rem; font-weight: 700; margin-bottom: 20px; color: var(--text); }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px; }
.btn-primary { padding: 10px 20px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; }
.btn-primary:hover { background: #2563eb; }
.btn-secondary { padding: 10px 20px; background: var(--bg-card); color: var(--text); border: 1px solid var(--border); border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; }
.btn-danger { padding: 10px 20px; background: #ef4444; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; }
.btn-danger:hover { background: #dc2626; }

.workspace-detail { border: 1px solid var(--border); border-radius: 12px; padding: 20px; background: var(--bg-card); }
.workspace-detail-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px; }
.workspace-detail h3 { font-size: 1.1rem; font-weight: 700; color: var(--text); margin: 0; }
.section-tabs { display: flex; gap: 4px; }
.section-tab { padding: 6px 14px; border: 1px solid var(--border); border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; background: var(--bg-card); color: var(--text-secondary); transition: all 0.15s; }
.section-tab:hover { border-color: #3b82f6; color: #3b82f6; }
.section-tab.active { background: #3b82f6; color: #fff; border-color: #3b82f6; }
.subagent-tasks { display: flex; flex-direction: column; gap: 8px; }
.skill-card { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; transition: all 0.15s; }
.skill-card:hover { border-color: #3b82f6; }
.skill-card-info { flex: 1; min-width: 0; }
.skill-card-name { font-size: 0.9rem; font-weight: 700; color: var(--text); }
.skill-card-desc { font-size: 0.8rem; color: var(--text-secondary); margin-top: 2px; }
.skill-card-cat { font-size: 0.72rem; color: var(--text-muted); margin-top: 2px; }
`;

export default WorkspacePanel;