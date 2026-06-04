import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

interface MCPServer {
  id: string;
  name: string;
  transport: string;
  endpoint: string;
  status: string;
  tool_count: number;
  resource_count: number;
  connected_at: string;
  last_error: string;
}

interface MCPTool {
  name: string;
  description: string;
  server_id: string;
  input_schema: Record<string, unknown>;
}

export const MCPServerPanel: React.FC = () => {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [selectedServer, setSelectedServer] = useState<MCPServer | null>(null);
  const [newServer, setNewServer] = useState({ name: '', transport: 'http', endpoint: '' });
  const [showRegister, setShowRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadServers();
    loadTools();
  }, []);

  const loadServers = async () => {
    try {
      const data = await api.mcp.servers();
      setServers(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load MCP servers');
    }
  };

  const loadTools = async () => {
    try {
      const data = await api.mcp.tools();
      setTools(data);
    } catch {}
  };

  const registerServer = async () => {
    if (!newServer.name.trim()) return;
    setLoading(true);
    setError('');
    try {
      await api.mcp.register(newServer);
      setNewServer({ name: '', transport: 'http', endpoint: '' });
      setShowRegister(false);
      await loadServers();
    } catch (e: any) {
      setError(e.message || 'Failed to register server');
    } finally {
      setLoading(false);
    }
  };

  const connectServer = async (serverId: string) => {
    setLoading(true);
    setError('');
    try {
      await api.mcp.connect(serverId);
      await loadServers();
      await loadTools();
    } catch (e: any) {
      setError(e.message || 'Failed to connect');
    } finally {
      setLoading(false);
    }
  };

  const disconnectServer = async (serverId: string) => {
    setLoading(true);
    try {
      await api.mcp.disconnect(serverId);
      await loadServers();
      await loadTools();
    } catch (e: any) {
      setError(e.message || 'Failed to disconnect');
    } finally {
      setLoading(false);
    }
  };

  const unregisterServer = async (serverId: string) => {
    try {
      await api.mcp.unregister(serverId);
      setServers(prev => prev.filter(s => s.id !== serverId));
      if (selectedServer?.id === serverId) setSelectedServer(null);
    } catch (e: any) {
      setError(e.message || 'Failed to unregister');
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      connected: '#10b981', connecting: '#f59e0b', disconnected: '#9ca3af', error: '#ef4444',
    };
    return colors[status] || '#6b7280';
  };

  return (
    <div className="mcp-panel">
      <h2>MCP Servers</h2>
      <p className="subtitle">Model Context Protocol tool server management</p>

      {error && <div className="error-banner">{error}</div>}

      <div className="mcp-header">
        <button className="btn-add" onClick={() => setShowRegister(true)}>+ Register Server</button>
      </div>

      {showRegister && (
        <div className="modal-overlay" onClick={() => setShowRegister(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Register MCP Server</h3>
            <div className="form-group">
              <label>Name</label>
              <input
                type="text"
                placeholder="Server name"
                value={newServer.name}
                onChange={e => setNewServer({ ...newServer, name: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Transport</label>
              <select value={newServer.transport} onChange={e => setNewServer({ ...newServer, transport: e.target.value })}>
                <option value="http">HTTP</option>
                <option value="stdio">STDIO</option>
                <option value="websocket">WebSocket</option>
              </select>
            </div>
            <div className="form-group">
              <label>Endpoint</label>
              <input
                type="text"
                placeholder="http://localhost:9000"
                value={newServer.endpoint}
                onChange={e => setNewServer({ ...newServer, endpoint: e.target.value })}
              />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowRegister(false)}>Cancel</button>
              <button className="btn-primary" onClick={registerServer} disabled={loading || !newServer.name.trim()}>
                Register
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="mcp-layout">
        <div className="mcp-server-list">
          <h3>Servers ({servers.length})</h3>
          {servers.map(server => (
            <div
              key={server.id}
              className={`server-card ${selectedServer?.id === server.id ? 'selected' : ''}`}
              onClick={() => setSelectedServer(server)}
            >
              <div className="server-header">
                <span className="server-name">{server.name}</span>
                <span className="server-status" style={{ color: getStatusColor(server.status) }}>
                  ● {server.status}
                </span>
              </div>
              <div className="server-meta">
                <span>{server.transport}</span>
                <span>{server.tool_count} tools</span>
              </div>
            </div>
          ))}
          {servers.length === 0 && (
            <div className="empty-state">No MCP servers registered</div>
          )}
        </div>

        <div className="mcp-detail">
          {selectedServer ? (
            <>
              <div className="detail-header">
                <h3>{selectedServer.name}</h3>
                <div className="detail-actions">
                  {selectedServer.status === 'disconnected' && (
                    <button className="btn-connect" onClick={() => connectServer(selectedServer.id)} disabled={loading}>
                      Connect
                    </button>
                  )}
                  {selectedServer.status === 'connected' && (
                    <button className="btn-disconnect" onClick={() => disconnectServer(selectedServer.id)} disabled={loading}>
                      Disconnect
                    </button>
                  )}
                  <button className="btn-delete" onClick={() => unregisterServer(selectedServer.id)}>Remove</button>
                </div>
              </div>
              <div className="detail-info">
                <div className="info-row">
                  <span className="info-label">Transport</span>
                  <span className="info-value">{selectedServer.transport}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Endpoint</span>
                  <span className="info-value">{selectedServer.endpoint || 'N/A'}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Status</span>
                  <span className="info-value" style={{ color: getStatusColor(selectedServer.status) }}>
                    {selectedServer.status}
                  </span>
                </div>
                {selectedServer.connected_at && (
                  <div className="info-row">
                    <span className="info-label">Connected</span>
                    <span className="info-value">{new Date(selectedServer.connected_at).toLocaleString()}</span>
                  </div>
                )}
                {selectedServer.last_error && (
                  <div className="info-row">
                    <span className="info-label">Last Error</span>
                    <span className="info-value error">{selectedServer.last_error}</span>
                  </div>
                )}
              </div>
              <div className="server-tools">
                <h4>Server Tools</h4>
                {tools.filter(t => t.server_id === selectedServer.id).map(tool => (
                  <div key={tool.name} className="tool-item">
                    <span className="tool-name">{tool.name}</span>
                    <span className="tool-desc">{tool.description}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="no-selection">Select a server to view details</div>
          )}
        </div>
      </div>

      <style>{`
        .mcp-panel { padding: 24px; max-width: 1200px; margin: 0 auto; }
        .mcp-panel h2 { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }
        .subtitle { color: #6b7280; margin-bottom: 24px; }
        .mcp-header { margin-bottom: 20px; }
        .btn-add { padding: 10px 20px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
        .btn-add:hover { background: #2563eb; }
        .mcp-layout { display: grid; grid-template-columns: 320px 1fr; gap: 24px; }
        .mcp-server-list { background: #fff; border-radius: 12px; padding: 16px; border: 1px solid #e5e7eb; max-height: 600px; overflow-y: auto; }
        .mcp-server-list h3 { font-size: 0.9rem; color: #6b7280; margin-bottom: 12px; }
        .server-card { padding: 12px; border-radius: 8px; cursor: pointer; margin-bottom: 8px; border: 1px solid #e5e7eb; transition: all 0.15s; }
        .server-card:hover { border-color: #3b82f6; }
        .server-card.selected { background: #eff6ff; border-color: #3b82f6; }
        .server-header { display: flex; justify-content: space-between; margin-bottom: 4px; }
        .server-name { font-weight: 600; font-size: 0.9rem; }
        .server-status { font-size: 0.75rem; font-weight: 600; }
        .server-meta { display: flex; gap: 16px; font-size: 0.75rem; color: #9ca3af; }
        .mcp-detail { background: #fff; border-radius: 12px; padding: 24px; border: 1px solid #e5e7eb; }
        .detail-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .detail-header h3 { font-size: 1.1rem; font-weight: 700; }
        .detail-actions { display: flex; gap: 8px; }
        .btn-connect { padding: 8px 16px; background: #10b981; color: #fff; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; }
        .btn-disconnect { padding: 8px 16px; background: #f59e0b; color: #fff; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; }
        .btn-delete { padding: 8px 16px; background: #ef4444; color: #fff; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; }
        .detail-info { margin-bottom: 24px; }
        .info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f3f4f6; }
        .info-label { font-size: 0.85rem; color: #6b7280; }
        .info-value { font-size: 0.85rem; font-weight: 600; }
        .info-value.error { color: #ef4444; }
        .server-tools h4 { font-size: 0.9rem; color: #374151; margin-bottom: 12px; }
        .tool-item { padding: 10px; background: #f9fafb; border-radius: 6px; margin-bottom: 6px; }
        .tool-name { font-weight: 600; font-family: monospace; font-size: 0.85rem; display: block; }
        .tool-desc { font-size: 0.8rem; color: #6b7280; }
        .no-selection { color: #9ca3af; text-align: center; padding: 60px; }
        .empty-state { color: #9ca3af; text-align: center; padding: 40px; font-size: 0.9rem; }
        .error-banner { background: #fef2f2; color: #991b1b; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 0.9rem; }
        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; z-index: 100; }
        .modal { background: #fff; border-radius: 12px; padding: 24px; width: 440px; max-width: 90vw; }
        .modal h3 { font-size: 1.1rem; font-weight: 700; margin-bottom: 16px; }
        .form-group { margin-bottom: 12px; }
        .form-group label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 4px; }
        .form-group input, .form-group select { width: 100%; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.9rem; }
        .modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; }
        .btn-primary { padding: 8px 20px; background: #3b82f6; color: #fff; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; }
        .btn-secondary { padding: 8px 20px; background: #f3f4f6; color: #374151; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; }
      `}</style>
    </div>
  );
};