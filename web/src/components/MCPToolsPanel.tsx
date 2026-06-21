import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

interface MCPTool {
  name: string;
  description: string;
  category: string;
  server_name: string;
  requires_approval: boolean;
  tags: string[];
}

interface MCPServer {
  name: string;
  type: string;
  connected: boolean;
  tool_count: number;
}

interface MCPStats {
  total_servers: number;
  connected_servers: number;
  total_tools: number;
  total_resources: number;
  total_prompts: number;
  tools_by_category: Record<string, number>;
  servers: MCPServer[];
}

export const MCPToolsPanel: React.FC = () => {
  const [stats, setStats] = useState<MCPStats | null>(null);
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [showAddServer, setShowAddServer] = useState(false);
  const [serverName, setServerName] = useState('');
  const [serverType, setServerType] = useState('embedded');
  const [serverCommand, setServerCommand] = useState('');
  const [showAddTool, setShowAddTool] = useState(false);
  const [toolName, setToolName] = useState('');
  const [toolDescription, setToolDescription] = useState('');
  const [toolCategory, setToolCategory] = useState('custom');
  const [toolTestName, setToolTestName] = useState('');
  const [toolTestArgs, setToolTestArgs] = useState('{}');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, toolsRes] = await Promise.all([
        api.mcp.stats(),
        api.mcp.listTools(selectedCategory || undefined),
      ]);
      setStats(statsRes);
      setTools(toolsRes.tools || []);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedCategory]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleAddServer = async () => {
    if (!serverName.trim()) return;
    try {
      await api.mcp.addServer({
        name: serverName.trim(),
        server_type: serverType,
        command: serverCommand,
      });
      setShowAddServer(false);
      setServerName('');
      setServerCommand('');
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleAddTool = async () => {
    if (!toolName.trim() || !toolDescription.trim()) return;
    try {
      await api.mcp.addTool({
        name: toolName.trim(),
        description: toolDescription.trim(),
        category: toolCategory,
      });
      setShowAddTool(false);
      setToolName('');
      setToolDescription('');
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleTestTool = async () => {
    if (!toolTestName.trim()) return;
    try {
      let args = {};
      try { args = JSON.parse(toolTestArgs); } catch {}
      const res = await api.mcp.executeTool(toolTestName, args);
      alert(`Execution Result:\nSuccess: ${res.success}\nContent: ${JSON.stringify(res.content)}\n${res.error ? 'Error: ' + res.error : ''}`);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleConnectServer = async (name: string) => {
    try {
      await api.mcp.connectServer(name);
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const serverTypes = ['stdio', 'sse', 'http', 'websocket', 'embedded'];
  const categories = ['', 'file_system', 'database', 'api', 'browser', 'system', 'knowledge', 'code', 'communication', 'custom'];

  return (
    <div className="mcp-tools-panel">
      <div className="panel-header">
        <h2>MCP Tools</h2>
        <span className="panel-subtitle">Model Context Protocol Integration</span>
      </div>

      {error && <div className="panel-error">{error}<button onClick={() => setError(null)}>Dismiss</button></div>}

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-value">{stats.total_servers}</span>
            <span className="stat-label">Servers</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.connected_servers}</span>
            <span className="stat-label">Connected</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.total_tools}</span>
            <span className="stat-label">Tools</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.total_resources}</span>
            <span className="stat-label">Resources</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.total_prompts}</span>
            <span className="stat-label">Prompts</span>
          </div>
        </div>
      )}

      <div className="panel-actions">
        <button className="btn-primary" onClick={() => setShowAddServer(true)}>+ Add Server</button>
        <button className="btn-primary" onClick={() => setShowAddTool(true)}>+ Add Tool</button>
      </div>

      {showAddServer && (
        <div className="create-form">
          <h3>Add MCP Server</h3>
          <input className="input" placeholder="Server name" value={serverName} onChange={e => setServerName(e.target.value)} />
          <select className="input" value={serverType} onChange={e => setServerType(e.target.value)}>
            {serverTypes.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <input className="input" placeholder="Command (for stdio)" value={serverCommand} onChange={e => setServerCommand(e.target.value)} />
          <div className="form-actions">
            <button className="btn-primary" onClick={handleAddServer}>Add</button>
            <button className="btn-secondary" onClick={() => setShowAddServer(false)}>Cancel</button>
          </div>
        </div>
      )}

      {showAddTool && (
        <div className="create-form">
          <h3>Add MCP Tool</h3>
          <input className="input" placeholder="Tool name" value={toolName} onChange={e => setToolName(e.target.value)} />
          <input className="input" placeholder="Description" value={toolDescription} onChange={e => setToolDescription(e.target.value)} />
          <select className="input" value={toolCategory} onChange={e => setToolCategory(e.target.value)}>
            {categories.filter(c => c).map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <div className="form-actions">
            <button className="btn-primary" onClick={handleAddTool}>Add</button>
            <button className="btn-secondary" onClick={() => setShowAddTool(false)}>Cancel</button>
          </div>
        </div>
      )}

      {/* Server List */}
      {stats && stats.servers.length > 0 && (
        <div className="server-list">
          <h3>Servers</h3>
          {stats.servers.map(s => (
            <div key={s.name} className={`server-card ${s.connected ? 'connected' : ''}`}>
              <div className="server-info">
                <span className="server-name">{s.name}</span>
                <span className="server-type">{s.type}</span>
                <span className="server-tool-count">{s.tool_count} tools</span>
              </div>
              <div className="server-actions">
                <span className={`server-status ${s.connected ? 'online' : 'offline'}`}>
                  {s.connected ? 'Connected' : 'Disconnected'}
                </span>
                {!s.connected && (
                  <button className="btn-secondary-sm" onClick={() => handleConnectServer(s.name)}>Connect</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Category Filter */}
      <div className="category-filter">
        <h3>Tools</h3>
        <div className="category-tabs">
          {categories.map(c => (
            <button
              key={c}
              className={`category-tab ${selectedCategory === c ? 'active' : ''}`}
              onClick={() => setSelectedCategory(c)}
            >
              {c || 'All'}
            </button>
          ))}
        </div>
      </div>

      {/* Tools List */}
      <div className="tool-list">
        {loading && <div className="loading">Loading tools...</div>}
        {tools.map(t => (
          <div key={t.name} className="tool-card">
            <div className="tool-header">
              <span className="tool-name">{t.name}</span>
              <span className="tool-category-badge">{t.category}</span>
            </div>
            <p className="tool-description">{t.description}</p>
            <div className="tool-meta">
              {t.server_name && <span className="tool-server">Server: {t.server_name}</span>}
              {t.requires_approval && <span className="tool-approval">Requires Approval</span>}
              {t.tags.map(tag => <span key={tag} className="tool-tag">{tag}</span>)}
            </div>
          </div>
        ))}
      </div>

      {/* Test Tool */}
      <div className="test-tool-section">
        <h3>Test Tool Execution</h3>
        <div className="test-tool-form">
          <input className="input" placeholder="Tool name" value={toolTestName} onChange={e => setToolTestName(e.target.value)} />
          <textarea
            className="input"
            placeholder='Arguments (JSON, e.g. {"key": "value"})'
            value={toolTestArgs}
            onChange={e => setToolTestArgs(e.target.value)}
            rows={3}
          />
          <button className="btn-primary" onClick={handleTestTool}>Execute</button>
        </div>
      </div>
    </div>
  );
};