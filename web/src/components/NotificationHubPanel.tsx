import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#dc2626',
  secondary: '#f87171',
  bg: '#fef2f2',
  border: '#fca5a5',
  accent: '#fee2e2',
  text: '#7f1d1d',
};

export const NotificationHubPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'send' | 'subscribe' | 'notifications' | 'templates'>('overview');

  const [sendForm, setSendForm] = useState({
    title: '', body: '', recipient_id: '', priority: 'normal', channel: '', topic: '', sender_id: '', action_url: '',
  });
  const [subscribeForm, setSubscribeForm] = useState({ subscriber_id: '', topics: '', channels: '' });
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [recipientFilter, setRecipientFilter] = useState('');

  const [templateForm, setTemplateForm] = useState({
    name: '', title_template: '', body_template: '', default_priority: 'normal', default_channel: '', variables: '',
  });
  const [sendTemplateForm, setSendTemplateForm] = useState({
    template_name: '', recipient_id: '', variables: '', channel: '', priority: '',
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, unread] = await Promise.all([
        api.notificationHub.stats(),
        api.notificationHub.unreadCount(),
      ]);
      setStats(s);
      setUnreadCount(unread.count ?? unread.unread_count ?? 0);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load notification hub data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleSend = async () => {
    if (!sendForm.title.trim() || !sendForm.body.trim()) return;
    try {
      await api.notificationHub.send({
        title: sendForm.title,
        body: sendForm.body,
        recipient_id: sendForm.recipient_id || undefined,
        priority: sendForm.priority,
        channel: sendForm.channel || undefined,
        topic: sendForm.topic || undefined,
        sender_id: sendForm.sender_id || undefined,
        action_url: sendForm.action_url || undefined,
      });
      toast.success('Notification sent');
      setSendForm({ title: '', body: '', recipient_id: '', priority: 'normal', channel: '', topic: '', sender_id: '', action_url: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSubscribe = async () => {
    if (!subscribeForm.subscriber_id.trim()) return;
    try {
      await api.notificationHub.subscribe({
        subscriber_id: subscribeForm.subscriber_id,
        topics: subscribeForm.topics ? subscribeForm.topics.split(',').map(s => s.trim()) : undefined,
        channels: subscribeForm.channels ? subscribeForm.channels.split(',').map(s => s.trim()) : undefined,
      });
      toast.success('Subscription created');
      setSubscribeForm({ subscriber_id: '', topics: '', channels: '' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleLoadNotifications = async () => {
    try {
      const result = await api.notificationHub.notifications(recipientFilter);
      const list = result.notifications || result.items || result;
      setNotifications(Array.isArray(list) ? list : []);
      toast.success('Notifications loaded');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleMarkRead = async (notificationId: string) => {
    try {
      await api.notificationHub.markRead(notificationId);
      toast.success('Marked as read');
      handleLoadNotifications();
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreateTemplate = async () => {
    if (!templateForm.name.trim() || !templateForm.title_template.trim() || !templateForm.body_template.trim()) return;
    try {
      await api.notificationHub.createTemplate({
        name: templateForm.name,
        title_template: templateForm.title_template,
        body_template: templateForm.body_template,
        default_priority: templateForm.default_priority || undefined,
        default_channel: templateForm.default_channel || undefined,
        variables: templateForm.variables ? templateForm.variables.split(',').map(s => s.trim()) : undefined,
      });
      toast.success('Template created');
      setTemplateForm({ name: '', title_template: '', body_template: '', default_priority: 'normal', default_channel: '', variables: '' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSendFromTemplate = async () => {
    if (!sendTemplateForm.template_name.trim()) return;
    try {
      let vars: Record<string, string> | undefined;
      if (sendTemplateForm.variables.trim()) {
        vars = {};
        sendTemplateForm.variables.split(',').forEach(pair => {
          const [k, v] = pair.split('=').map(s => s.trim());
          if (k && v) vars![k] = v;
        });
      }
      await api.notificationHub.sendFromTemplate({
        template_name: sendTemplateForm.template_name,
        recipient_id: sendTemplateForm.recipient_id || undefined,
        variables: vars,
        channel: sendTemplateForm.channel || undefined,
        priority: sendTemplateForm.priority || undefined,
      });
      toast.success('Notification sent from template');
      setSendTemplateForm({ template_name: '', recipient_id: '', variables: '', channel: '', priority: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const priorityColors: Record<string, string> = {
    urgent: '#ef4444', high: '#f59e0b', normal: '#3b82f6', low: '#9ca3af',
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🔔 Notification Hub</h2>
          <p className="panel-subtitle">Send, subscribe, and manage notifications across channels</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading notification hub...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>🔔 Notification Hub</h2>
        <p className="panel-subtitle">Send, subscribe, and manage notifications across channels</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_notifications ?? stats.notification_count ?? '-'}</span><span className="stat-label">Total Notifications</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{unreadCount}</span><span className="stat-label">Unread</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_subscribers ?? stats.subscriber_count ?? '-'}</span><span className="stat-label">Subscribers</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_templates ?? stats.template_count ?? '-'}</span><span className="stat-label">Templates</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'send', 'subscribe', 'notifications', 'templates'] as const).map(s => (
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
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
            {Object.entries(stats).filter(([k]) => !['by_priority', 'by_channel', 'by_topic'].includes(k)).map(([key, value]: [string, any]) => (
              <div key={key} style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontSize: '0.85rem', color: '#6b7280', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>
                  {typeof value === 'number' ? value : typeof value === 'object' ? JSON.stringify(value).slice(0, 40) : String(value)}
                </div>
              </div>
            ))}
          </div>
          {stats.by_priority && Object.keys(stats.by_priority).length > 0 && (
            <div style={{ marginTop: 20 }}>
              <h4 style={{ color: themeColors.text }}>By Priority</h4>
              {Object.entries(stats.by_priority).map(([priority, count]: [string, any]) => (
                <div key={priority} className="dashboard-stat-row">
                  <span style={{ fontWeight: 500, textTransform: 'capitalize', color: priorityColors[priority] || '#666' }}>{priority}</span>
                  <strong style={{ color: themeColors.primary }}>{count}</strong>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Send Notification */}
      {activeSection === 'send' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Send Notification</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Title</label>
              <input type="text" value={sendForm.title}
                onChange={e => setSendForm(f => ({ ...f, title: e.target.value }))}
                placeholder="Notification title" />
            </div>
            <div className="form-group">
              <label>Body</label>
              <textarea rows={3} value={sendForm.body}
                onChange={e => setSendForm(f => ({ ...f, body: e.target.value }))}
                placeholder="Notification body content..." />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Recipient ID</label>
                <input type="text" value={sendForm.recipient_id}
                  onChange={e => setSendForm(f => ({ ...f, recipient_id: e.target.value }))}
                  placeholder="user-123" />
              </div>
              <div className="form-group">
                <label>Priority</label>
                <select value={sendForm.priority} onChange={e => setSendForm(f => ({ ...f, priority: e.target.value }))}>
                  {['urgent', 'high', 'normal', 'low'].map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Channel</label>
                <input type="text" value={sendForm.channel}
                  onChange={e => setSendForm(f => ({ ...f, channel: e.target.value }))}
                  placeholder="email, push, sms" />
              </div>
              <div className="form-group">
                <label>Topic</label>
                <input type="text" value={sendForm.topic}
                  onChange={e => setSendForm(f => ({ ...f, topic: e.target.value }))}
                  placeholder="system, alerts" />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Sender ID</label>
                <input type="text" value={sendForm.sender_id}
                  onChange={e => setSendForm(f => ({ ...f, sender_id: e.target.value }))}
                  placeholder="agent-456" />
              </div>
              <div className="form-group">
                <label>Action URL</label>
                <input type="text" value={sendForm.action_url}
                  onChange={e => setSendForm(f => ({ ...f, action_url: e.target.value }))}
                  placeholder="https://..." />
              </div>
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleSend}>Send Notification</button>
          </div>
        </div>
      )}

      {/* Subscribe */}
      {activeSection === 'subscribe' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Subscribe to Notifications</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Subscriber ID</label>
              <input type="text" value={subscribeForm.subscriber_id}
                onChange={e => setSubscribeForm(f => ({ ...f, subscriber_id: e.target.value }))}
                placeholder="user-123" />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Topics (comma-separated)</label>
                <input type="text" value={subscribeForm.topics}
                  onChange={e => setSubscribeForm(f => ({ ...f, topics: e.target.value }))}
                  placeholder="system, alerts, updates" />
              </div>
              <div className="form-group">
                <label>Channels (comma-separated)</label>
                <input type="text" value={subscribeForm.channels}
                  onChange={e => setSubscribeForm(f => ({ ...f, channels: e.target.value }))}
                  placeholder="email, push, sms" />
              </div>
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleSubscribe}>Subscribe</button>
          </div>
        </div>
      )}

      {/* Notifications List */}
      {activeSection === 'notifications' && (
        <div className="dashboard-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Notifications</h3>
            <div style={{ display: 'flex', gap: 8 }}>
              <input type="text" value={recipientFilter}
                onChange={e => setRecipientFilter(e.target.value)}
                placeholder="Filter by recipient ID..."
                style={{ width: 200 }} />
              <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleLoadNotifications}>Load</button>
            </div>
          </div>
          <div style={{ marginBottom: 8, color: themeColors.text, fontWeight: 600 }}>
            Unread: {unreadCount}
          </div>
          {notifications.length === 0 ? (
            <div className="panel-empty">Click "Load" to view notifications</div>
          ) : (
            <div className="forge-skill-list">
              {notifications.map((notif: any, idx: number) => (
                <div key={notif.id || notif.notification_id || idx} className="forge-skill-card" style={{ borderLeft: `4px solid ${priorityColors[notif.priority] || themeColors.primary}` }}>
                  <div className="forge-skill-header">
                    <div className="forge-skill-name" style={{ color: notif.read ? '#6b7280' : themeColors.text }}>
                      {notif.read ? notif.title : <strong>{notif.title}</strong>}
                    </div>
                    <span className="dashboard-badge" style={{ background: priorityColors[notif.priority] || themeColors.primary, color: '#fff' }}>
                      {notif.priority || 'normal'}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{notif.body}</div>
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 4, fontSize: '0.8rem', color: '#6b7280' }}>
                      {notif.channel && <span>Channel: {notif.channel}</span>}
                      {notif.topic && <span>Topic: {notif.topic}</span>}
                      {notif.recipient_id && <span>To: {notif.recipient_id}</span>}
                      {notif.created_at && <span>{new Date(notif.created_at).toLocaleString()}</span>}
                    </div>
                  </div>
                  {!notif.read && (
                    <div style={{ marginTop: 8 }}>
                      <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff', border: 'none' }}
                        onClick={() => handleMarkRead(notif.id || notif.notification_id)}>
                        Mark as Read
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Templates */}
      {activeSection === 'templates' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create Template</h3>
          <div className="skill-execute" style={{ marginBottom: 24, position: 'static' }}>
            <div className="form-group">
              <label>Template Name</label>
              <input type="text" value={templateForm.name}
                onChange={e => setTemplateForm(f => ({ ...f, name: e.target.value }))}
                placeholder="welcome-message" />
            </div>
            <div className="form-group">
              <label>Title Template</label>
              <input type="text" value={templateForm.title_template}
                onChange={e => setTemplateForm(f => ({ ...f, title_template: e.target.value }))}
                placeholder="Welcome {{user_name}}!" />
            </div>
            <div className="form-group">
              <label>Body Template</label>
              <textarea rows={3} value={templateForm.body_template}
                onChange={e => setTemplateForm(f => ({ ...f, body_template: e.target.value }))}
                placeholder="Hello {{user_name}}, welcome to {{platform}}..." />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Default Priority</label>
                <select value={templateForm.default_priority} onChange={e => setTemplateForm(f => ({ ...f, default_priority: e.target.value }))}>
                  {['urgent', 'high', 'normal', 'low'].map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Default Channel</label>
                <input type="text" value={templateForm.default_channel}
                  onChange={e => setTemplateForm(f => ({ ...f, default_channel: e.target.value }))}
                  placeholder="email" />
              </div>
              <div className="form-group">
                <label>Variables (comma-separated)</label>
                <input type="text" value={templateForm.variables}
                  onChange={e => setTemplateForm(f => ({ ...f, variables: e.target.value }))}
                  placeholder="user_name, platform" />
              </div>
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleCreateTemplate}>Create Template</button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 24 }}>Send from Template</h3>
          <div className="skill-execute" style={{ position: 'static' }}>
            <div className="form-group">
              <label>Template Name</label>
              <input type="text" value={sendTemplateForm.template_name}
                onChange={e => setSendTemplateForm(f => ({ ...f, template_name: e.target.value }))}
                placeholder="welcome-message" />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Recipient ID</label>
                <input type="text" value={sendTemplateForm.recipient_id}
                  onChange={e => setSendTemplateForm(f => ({ ...f, recipient_id: e.target.value }))}
                  placeholder="user-123" />
              </div>
              <div className="form-group">
                <label>Variables (key=value, comma-separated)</label>
                <input type="text" value={sendTemplateForm.variables}
                  onChange={e => setSendTemplateForm(f => ({ ...f, variables: e.target.value }))}
                  placeholder="user_name=John, platform=Buddy" />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Channel</label>
                <input type="text" value={sendTemplateForm.channel}
                  onChange={e => setSendTemplateForm(f => ({ ...f, channel: e.target.value }))}
                  placeholder="email" />
              </div>
              <div className="form-group">
                <label>Priority</label>
                <select value={sendTemplateForm.priority} onChange={e => setSendTemplateForm(f => ({ ...f, priority: e.target.value }))}>
                  <option value="">Default</option>
                  {['urgent', 'high', 'normal', 'low'].map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleSendFromTemplate}>Send from Template</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationHubPanel;