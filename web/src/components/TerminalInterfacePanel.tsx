import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#10b981',
  secondary: '#34d399',
  bg: '#0f172a',
  bgLight: '#1e293b',
  border: '#334155',
  accent: '#1e293b',
  text: '#e2e8f0',
  green: '#10b981',
  dim: '#94a3b8',
};

export const TerminalInterfacePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'execute' | 'commands' | 'createScript' | 'runScript' | 'scripts'>('overview');

  const [executeForm, setExecuteForm] = useState({ session_id: '', command_line: '' });
  const [executeResult, setExecuteResult] = useState<any>(null);
  const [commands, setCommands] = useState<any[]>([]);

  const [createScriptForm, setCreateScriptForm] = useState({
    name: '', commands: '', description: '',
  });
  const [runScriptForm, setRunScriptForm] = useState({ session_id: '', script_name: '' });
  const [runScriptResult, setRunScriptResult] = useState<any>(null);
  const [scripts, setScripts] = useState<any[]>([]);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, cmds] = await Promise.all([
        api.terminalInterface.stats(),
        api.terminalInterface.commands(),
      ]);
      setStats(s);
      setCommands(cmds.commands || cmds.items || cmds);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load terminal interface data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleExecute = async () => {
    if (!executeForm.command_line.trim()) return;
    try {
      const result = await api.terminalInterface.execute({
        session_id: executeForm.session_id || undefined,
        command_line: executeForm.command_line,
      });
      setExecuteResult(result);
      toast.success('Command executed');
      setExecuteForm(f => ({ ...f, command_line: '' }));
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreateScript = async () => {
    if (!createScriptForm.name.trim() || !createScriptForm.commands.trim()) return;
    try {
      await api.terminalInterface.createScript({
        name: createScriptForm.name,
        commands: createScriptForm.commands.split('\n').map(s => s.trim()).filter(Boolean),
        description: createScriptForm.description || undefined,
      });
      toast.success('Script created');
      setCreateScriptForm({ name: '', commands: '', description: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRunScript = async () => {
    if (!runScriptForm.script_name.trim()) return;
    try {
      const result = await api.terminalInterface.runScript({
        session_id: runScriptForm.session_id || undefined,
        script_name: runScriptForm.script_name,
      });
      setRunScriptResult(result);
      toast.success('Script executed');
      setRunScriptForm(f => ({ ...f, script_name: '' }));
    } catch (e: any) { toast.error(e.message); }
  };

  const handleLoadScripts = async () => {
    try {
      const result = await api.terminalInterface.scripts();
      setScripts(result.scripts || result.items || result);
      toast.success('Scripts loaded');
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>⌨️ Terminal Interface</h2>
          <p className="panel-subtitle">Execute commands, manage scripts, and interact with the system terminal</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading terminal interface...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>⌨️ Terminal Interface</h2>
        <p className="panel-subtitle">Execute commands, manage scripts, and interact with the system terminal</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.green}}>{stats.total_sessions ?? stats.session_count ?? '-'}</span><span className="stat-label">Sessions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.green}}>{stats.total_executions ?? stats.execution_count ?? '-'}</span><span className="stat-label">Executions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.green}}>{stats.total_scripts ?? stats.script_count ?? '-'}</span><span className="stat-label">Scripts</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.green}}>{stats.success_rate != null ? `${(stats.success_rate * 100).toFixed(0)}%` : '-'}</span><span className="stat-label">Success Rate</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'execute', 'commands', 'createScript', 'runScript', 'scripts'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
            style={activeSection === s ? { background: themeColors.green, borderColor: themeColors.green, color: themeColors.bg } : {}}
          >
            {s === 'createScript' ? 'Create Script' : s === 'runScript' ? 'Run Script' : s === 'scripts' ? 'Scripts List' : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
            {Object.entries(stats).filter(([k]) => !['by_command', 'recent_executions'].includes(k)).map(([key, value]: [string, any]) => (
              <div key={key} style={{ padding: 16, background: themeColors.bgLight, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontSize: '0.85rem', color: themeColors.dim, textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.green, fontFamily: 'monospace' }}>
                  {typeof value === 'number' ? value : typeof value === 'object' ? JSON.stringify(value).slice(0, 40) : String(value)}
                </div>
              </div>
            ))}
          </div>
          {stats.by_command && Object.keys(stats.by_command).length > 0 && (
            <div style={{ marginTop: 20, padding: 16, background: themeColors.bgLight, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.green }}>Command Usage</h4>
              {Object.entries(stats.by_command).map(([cmd, count]: [string, any]) => (
                <div key={cmd} className="dashboard-stat-row" style={{ borderBottom: `1px solid ${themeColors.border}`, padding: '8px 0' }}>
                  <span style={{ fontFamily: 'monospace', color: themeColors.green }}>$ {cmd}</span>
                  <strong style={{ color: themeColors.text }}>{count}</strong>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Execute Command */}
      {activeSection === 'execute' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.green }}>Execute Command</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label style={{ color: themeColors.dim }}>Session ID (optional)</label>
              <input type="text" value={executeForm.session_id}
                onChange={e => setExecuteForm(f => ({ ...f, session_id: e.target.value }))}
                placeholder="session-abc-123"
                style={{ background: themeColors.bgLight, border: `1px solid ${themeColors.border}`, color: themeColors.text, fontFamily: 'monospace' }} />
            </div>
            <div className="form-group">
              <label style={{ color: themeColors.dim }}>Command Line</label>
              <div style={{ display: 'flex', background: themeColors.bg, borderRadius: 6, border: `1px solid ${themeColors.border}`, overflow: 'hidden' }}>
                <span style={{ padding: '10px 8px 10px 12px', color: themeColors.green, fontFamily: 'monospace', fontWeight: 700, userSelect: 'none' }}>$</span>
                <input type="text" value={executeForm.command_line}
                  onChange={e => setExecuteForm(f => ({ ...f, command_line: e.target.value }))}
                  placeholder="echo 'Hello, Buddy!'"
                  style={{ flex: 1, border: 'none', background: 'transparent', color: themeColors.text, fontFamily: 'monospace', fontSize: '0.95rem', padding: '10px 12px 10px 0' }} />
              </div>
            </div>
            <button className="btn-primary" style={{ background: themeColors.green, color: themeColors.bg, fontWeight: 700 }} onClick={handleExecute}>
              Execute
            </button>
          </div>
          {executeResult && (
            <div style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <h4 style={{ color: themeColors.green, margin: 0 }}>Output</h4>
                <span style={{ color: themeColors.dim, fontFamily: 'monospace', fontSize: '0.8rem' }}>
                  exit: {executeResult.exit_code ?? '?'}
                </span>
              </div>
              <pre style={{
                whiteSpace: 'pre-wrap',
                color: themeColors.text,
                fontFamily: 'monospace',
                fontSize: '0.85rem',
                background: themeColors.bgLight,
                padding: 12,
                borderRadius: 6,
                margin: 0,
                maxHeight: 400,
                overflow: 'auto',
              }}>
                {executeResult.stdout || executeResult.output || JSON.stringify(executeResult, null, 2)}
              </pre>
              {(executeResult.stderr || executeResult.error) && (
                <pre style={{
                  whiteSpace: 'pre-wrap',
                  color: '#ef4444',
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                  background: '#1a0a0a',
                  padding: 12,
                  borderRadius: 6,
                  marginTop: 8,
                  maxHeight: 200,
                  overflow: 'auto',
                }}>
                  {executeResult.stderr || executeResult.error}
                </pre>
              )}
            </div>
          )}
        </div>
      )}

      {/* Commands List */}
      {activeSection === 'commands' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.green }}>Available Commands ({Array.isArray(commands) ? commands.length : 0})</h3>
          {!Array.isArray(commands) || commands.length === 0 ? (
            <div className="panel-empty" style={{ color: themeColors.dim }}>No commands available</div>
          ) : (
            <div className="forge-skill-list">
              {commands.map((cmd: any, idx: number) => (
                <div key={cmd.name || cmd.command || idx} className="forge-skill-card" style={{ background: themeColors.bgLight, borderLeft: `4px solid ${themeColors.green}`, borderColor: themeColors.border }}>
                  <div className="forge-skill-header">
                    <div className="forge-skill-name" style={{ color: themeColors.green, fontFamily: 'monospace' }}>{cmd.name || cmd.command}</div>
                    {cmd.category && (
                      <span className="dashboard-badge" style={{ background: themeColors.border, color: themeColors.text }}>
                        {cmd.category}
                      </span>
                    )}
                  </div>
                  <div className="forge-skill-meta">
                    {cmd.description && <div style={{ color: themeColors.dim }}>{cmd.description}</div>}
                    {cmd.usage && <div style={{ color: themeColors.dim, fontFamily: 'monospace' }}>Usage: {cmd.usage}</div>}
                    {cmd.parameters?.length > 0 && (
                      <div style={{ color: themeColors.dim, marginTop: 4 }}>
                        {cmd.parameters.map((p: any) => (
                          <span key={p.name} style={{ display: 'inline-block', padding: '2px 8px', margin: '2px', background: themeColors.border, color: themeColors.text, borderRadius: 4, fontSize: '0.75rem', fontFamily: 'monospace' }}>
                            {p.name}: {p.type}
                          </span>
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

      {/* Create Script */}
      {activeSection === 'createScript' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.green }}>Create Script</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label style={{ color: themeColors.dim }}>Script Name</label>
              <input type="text" value={createScriptForm.name}
                onChange={e => setCreateScriptForm(f => ({ ...f, name: e.target.value }))}
                placeholder="backup-system"
                style={{ background: themeColors.bgLight, border: `1px solid ${themeColors.border}`, color: themeColors.text, fontFamily: 'monospace' }} />
            </div>
            <div className="form-group">
              <label style={{ color: themeColors.dim }}>Description</label>
              <input type="text" value={createScriptForm.description}
                onChange={e => setCreateScriptForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Backup critical system files"
                style={{ background: themeColors.bgLight, border: `1px solid ${themeColors.border}`, color: themeColors.text }} />
            </div>
            <div className="form-group">
              <label style={{ color: themeColors.dim }}>Commands (one per line)</label>
              <textarea
                rows={6}
                value={createScriptForm.commands}
                onChange={e => setCreateScriptForm(f => ({ ...f, commands: e.target.value }))}
                placeholder={`echo "Starting backup..."\ntar -czf backup.tar.gz /data\nls -la backup.tar.gz`}
                style={{ background: themeColors.bg, border: `1px solid ${themeColors.border}`, color: themeColors.text, fontFamily: 'monospace', fontSize: '0.9rem' }}
              />
            </div>
            <button className="btn-primary" style={{ background: themeColors.green, color: themeColors.bg, fontWeight: 700 }} onClick={handleCreateScript}>
              Create Script
            </button>
          </div>
        </div>
      )}

      {/* Run Script */}
      {activeSection === 'runScript' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.green }}>Run Script</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label style={{ color: themeColors.dim }}>Session ID (optional)</label>
                <input type="text" value={runScriptForm.session_id}
                  onChange={e => setRunScriptForm(f => ({ ...f, session_id: e.target.value }))}
                  placeholder="session-abc-123"
                  style={{ background: themeColors.bgLight, border: `1px solid ${themeColors.border}`, color: themeColors.text, fontFamily: 'monospace' }} />
              </div>
              <div className="form-group" style={{ flex: 2 }}>
                <label style={{ color: themeColors.dim }}>Script Name</label>
                <input type="text" value={runScriptForm.script_name}
                  onChange={e => setRunScriptForm(f => ({ ...f, script_name: e.target.value }))}
                  placeholder="backup-system"
                  style={{ background: themeColors.bgLight, border: `1px solid ${themeColors.border}`, color: themeColors.text, fontFamily: 'monospace' }} />
              </div>
            </div>
            <button className="btn-primary" style={{ background: themeColors.green, color: themeColors.bg, fontWeight: 700 }} onClick={handleRunScript}>
              Run Script
            </button>
          </div>
          {runScriptResult && (
            <div style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.green }}>Script Output</h4>
              <pre style={{
                whiteSpace: 'pre-wrap',
                color: themeColors.text,
                fontFamily: 'monospace',
                fontSize: '0.85rem',
                background: themeColors.bgLight,
                padding: 12,
                borderRadius: 6,
                maxHeight: 400,
                overflow: 'auto',
              }}>
                {typeof runScriptResult === 'string' ? runScriptResult : JSON.stringify(runScriptResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Scripts List */}
      {activeSection === 'scripts' && (
        <div className="dashboard-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ color: themeColors.green }}>Scripts</h3>
            <button className="btn-primary" style={{ background: themeColors.green, color: themeColors.bg }} onClick={handleLoadScripts}>Load Scripts</button>
          </div>
          {scripts.length === 0 ? (
            <div className="panel-empty" style={{ color: themeColors.dim }}>Click "Load Scripts" to view available scripts</div>
          ) : (
            <div className="forge-skill-list">
              {scripts.map((script: any, idx: number) => (
                <div key={script.name || script.id || idx} className="forge-skill-card" style={{ background: themeColors.bgLight, borderLeft: `4px solid ${themeColors.green}`, borderColor: themeColors.border }}>
                  <div className="forge-skill-header">
                    <div className="forge-skill-name" style={{ color: themeColors.green, fontFamily: 'monospace' }}>{script.name}</div>
                    {script.command_count != null && (
                      <span className="dashboard-badge" style={{ background: themeColors.border, color: themeColors.text }}>
                        {script.command_count} commands
                      </span>
                    )}
                  </div>
                  <div className="forge-skill-meta">
                    {script.description && <div style={{ color: themeColors.dim }}>{script.description}</div>}
                    {script.commands?.length > 0 && (
                      <div style={{ marginTop: 4, color: themeColors.dim, fontFamily: 'monospace', fontSize: '0.8rem' }}>
                        {script.commands.map((cmd: string, ci: number) => (
                          <div key={ci} style={{ padding: '2px 0' }}>$ {cmd}</div>
                        ))}
                      </div>
                    )}
                    {script.created_at && <div style={{ fontSize: '0.8rem', color: themeColors.dim, marginTop: 4 }}>Created: {new Date(script.created_at).toLocaleString()}</div>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TerminalInterfacePanel;