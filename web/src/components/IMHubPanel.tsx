import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { IMPlatformStatus, IMHubStats } from '../types';

export const IMHubPanel: React.FC = () => {
  const [stats, setStats] = useState<IMHubStats | null>(null);
  const [platforms, setPlatforms] = useState<IMPlatformStatus[]>([]);
  const [messages, setMessages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showConfigure, setShowConfigure] = useState(false);
  const [configForm, setConfigForm] = useState({
    platform: 'telegram', enabled: true, bot_token: '', app_id: '', app_secret: '', webhook_url: '', allowed_chat_ids: '', auto_reply: true,
  });
  const [sendForm, setSendForm] = useState({ platform: 'telegram', chat_id: '', text: '' });
  const [assignForm, setAssignForm] = useState({ chat_id: '', agent_id: '' });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [s, p, m] = await Promise.all([
        api.imHub.stats(),
        api.imHub.platforms(),
        api.imHub.messages(undefined, 30),
      ]);
      setStats(s);
      setPlatforms(p.platforms);
      setMessages(m.messages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load IM Hub data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleConfigure = async () => {
    try {
      await api.imHub.configure({
        platform: configForm.platform,
        enabled: configForm.enabled,
        bot_token: configForm.bot_token,
        app_id: configForm.app_id,
        app_secret: configForm.app_secret,
        webhook_url: configForm.webhook_url,
        allowed_chat_ids: configForm.allowed_chat_ids ? configForm.allowed_chat_ids.split(',').map(s => s.trim()) : [],
        auto_reply: configForm.auto_reply,
      });
      setShowConfigure(false);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to configure platform');
    }
  };

  const handleConnect = async (platform: string) => {
    try { await api.imHub.connect(platform); loadData(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Failed to connect'); }
  };

  const handleDisconnect = async (platform: string) => {
    try { await api.imHub.disconnect(platform); loadData(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Failed to disconnect'); }
  };

  const handleSend = async () => {
    if (!sendForm.chat_id || !sendForm.text) return;
    try {
      await api.imHub.send(sendForm.platform, sendForm.chat_id, sendForm.text);
      setSendForm({ ...sendForm, text: '' });
      loadData();
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to send message'); }
  };

  const handleAssign = async () => {
    if (!assignForm.chat_id || !assignForm.agent_id) return;
    try {
      await api.imHub.assignAgent(assignForm.chat_id, assignForm.agent_id);
      setAssignForm({ chat_id: '', agent_id: '' });
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to assign agent'); }
  };

  const getStatusColor = (status: string) => {
    if (status === 'connected') return 'badge-green';
    if (status === 'configured') return 'badge-blue';
    return 'badge-gray';
  };

  if (loading) return <div className="panel-loading">Loading IM Hub...</div>;

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>IM Integration Hub</h2>
        <div className="panel-header-actions">
          <button className="btn-primary" onClick={() => setShowConfigure(true)}>Configure Platform</button>
          <button className="btn-secondary" onClick={loadData}>Refresh</button>
        </div>
      </div>

      {error && <div className="panel-error">{error}</div>}

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.connected_platforms}</div>
            <div className="stat-label">Connected</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.total_messages}</div>
            <div className="stat-label">Messages</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.active_chats}</div>
            <div className="stat-label">Active Chats</div>
          </div>
        </div>
      )}

      {showConfigure && (
        <div className="modal-overlay" onClick={() => setShowConfigure(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Configure IM Platform</h2>
            <div className="form-group">
              <label>Platform</label>
              <select value={configForm.platform} onChange={e => setConfigForm({...configForm, platform: e.target.value})}>
                <option value="telegram">Telegram</option>
                <option value="slack">Slack</option>
                <option value="discord">Discord</option>
                <option value="feishu">Feishu</option>
              </select>
            </div>
            <div className="form-group">
              <label>Bot Token</label>
              <input type="text" value={configForm.bot_token} onChange={e => setConfigForm({...configForm, bot_token: e.target.value})} placeholder="Bot API token" />
            </div>
            <div className="form-group">
              <label>Webhook URL</label>
              <input type="text" value={configForm.webhook_url} onChange={e => setConfigForm({...configForm, webhook_url: e.target.value})} />
            </div>
            <div className="form-group">
              <label>
                <input type="checkbox" checked={configForm.enabled} onChange={e => setConfigForm({...configForm, enabled: e.target.checked})} />
                {' '}Enabled
              </label>
            </div>
            <div className="form-group">
              <label>
                <input type="checkbox" checked={configForm.auto_reply} onChange={e => setConfigForm({...configForm, auto_reply: e.target.checked})} />
                {' '}Auto Reply
              </label>
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowConfigure(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleConfigure}>Save</button>
            </div>
          </div>
        </div>
      )}

      <div className="panel-section">
        <h3>Platforms</h3>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Platform</th>
                <th>Config</th>
                <th>Connection</th>
                <th>Messages</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {platforms.map((p) => (
                <tr key={p.platform}>
                  <td className="item-name">{p.platform}</td>
                  <td><span className={`badge ${p.config_status === 'configured' ? 'badge-blue' : 'badge-gray'}`}>{p.config_status}</span></td>
                  <td><span className={`badge ${getStatusColor(p.connection_status)}`}>{p.connection_status}</span></td>
                  <td>{p.message_count}</td>
                  <td>
                    <div className="btn-group">
                      {p.config_status === 'configured' && p.connection_status !== 'connected' && (
                        <button className="btn-sm btn-green" onClick={() => handleConnect(p.platform)}>Connect</button>
                      )}
                      {p.connection_status === 'connected' && (
                        <button className="btn-sm btn-red" onClick={() => handleDisconnect(p.platform)}>Disconnect</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel-section">
        <h3>Send Message</h3>
        <div className="form-row">
          <select value={sendForm.platform} onChange={e => setSendForm({...sendForm, platform: e.target.value})} className="form-select">
            <option value="telegram">Telegram</option>
            <option value="slack">Slack</option>
            <option value="discord">Discord</option>
            <option value="feishu">Feishu</option>
          </select>
          <input type="text" placeholder="Chat ID" value={sendForm.chat_id} onChange={e => setSendForm({...sendForm, chat_id: e.target.value})} />
          <input type="text" placeholder="Message text..." value={sendForm.text} onChange={e => setSendForm({...sendForm, text: e.target.value})} />
          <button className="btn-primary" onClick={handleSend}>Send</button>
        </div>
      </div>

      <div className="panel-section">
        <h3>Assign Agent to Chat</h3>
        <div className="form-row">
          <input type="text" placeholder="Chat ID" value={assignForm.chat_id} onChange={e => setAssignForm({...assignForm, chat_id: e.target.value})} />
          <input type="text" placeholder="Agent ID" value={assignForm.agent_id} onChange={e => setAssignForm({...assignForm, agent_id: e.target.value})} />
          <button className="btn-primary" onClick={handleAssign}>Assign</button>
        </div>
      </div>

      {messages.length > 0 && (
        <div className="panel-section">
          <h3>Recent Messages</h3>
          <div className="message-list">
            {messages.map((msg, i) => (
              <div key={i} className="message-item">
                <div className="msg-meta">
                  <span className="badge badge-sm">{msg.platform}</span>
                  <span>{msg.chat_id}</span>
                </div>
                <div className="msg-content">{msg.text || msg.content}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};