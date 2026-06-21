import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

interface Provider {
  provider_id: string;
  name: string;
  provider_type: string;
  status: string;
  default_model: string;
  available_models: string[];
  weight: number;
  rate_limit_rpm: number;
}

export const GatewayPanel: React.FC = () => {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAddProvider, setShowAddProvider] = useState(false);
  const [providerName, setProviderName] = useState('');
  const [providerType, setProviderType] = useState('openai');
  const [apiBase, setApiBase] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [defaultModel, setDefaultModel] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [providersRes, statsRes] = await Promise.all([
        api.gateway.providers(),
        api.gateway.stats(),
      ]);
      setProviders(providersRes.providers || []);
      setStats(statsRes);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleAddProvider = async () => {
    if (!providerName.trim()) return;
    try {
      await api.gateway.addProvider({
        name: providerName.trim(),
        provider_type: providerType,
        api_base: apiBase,
        api_key: apiKey,
        default_model: defaultModel,
      });
      setShowAddProvider(false);
      setProviderName('');
      setApiBase('');
      setApiKey('');
      setDefaultModel('');
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleRemoveProvider = async (providerId: string) => {
    if (!confirm('Remove this provider?')) return;
    try {
      await api.gateway.removeProvider(providerId);
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleTestRoute = async () => {
    try {
      const res = await api.gateway.testRoute({
        model: 'gpt-4',
        messages: [{ role: 'user', content: 'Hello' }],
      });
      alert(`Route Test Result:\nProvider: ${res.provider_id}\nModel: ${res.model}\nSuccess: ${res.success}`);
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const providerTypes = ['openai', 'anthropic', 'azure', 'google', 'local', 'custom', 'mistral', 'cohere', 'deepseek', 'together'];

  const statusColor = (status: string) => {
    switch (status) {
      case 'online': return 'var(--green)';
      case 'degraded': return 'var(--yellow)';
      case 'offline': return 'var(--red)';
      case 'rate_limited': return 'var(--orange)';
      default: return 'var(--text-muted)';
    }
  };

  return (
    <div className="gateway-panel">
      <div className="panel-header">
        <h2>API Gateway</h2>
        <span className="panel-subtitle">Provider Catalog & Intelligent Routing</span>
      </div>

      {error && <div className="panel-error">{error}<button onClick={() => setError(null)}>Dismiss</button></div>}

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-value">{stats.catalog.total_providers}</span>
            <span className="stat-label">Providers</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.catalog.online_providers}</span>
            <span className="stat-label">Online</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.total_requests}</span>
            <span className="stat-label">Requests</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.avg_latency_ms}ms</span>
            <span className="stat-label">Avg Latency</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.active_rules}</span>
            <span className="stat-label">Routing Rules</span>
          </div>
        </div>
      )}

      <div className="panel-actions">
        <button className="btn-primary" onClick={() => setShowAddProvider(true)}>+ Add Provider</button>
        <button className="btn-secondary" onClick={handleTestRoute}>Test Route</button>
      </div>

      {showAddProvider && (
        <div className="create-form">
          <h3>Add Provider</h3>
          <input className="input" placeholder="Provider name" value={providerName} onChange={e => setProviderName(e.target.value)} />
          <select className="input" value={providerType} onChange={e => setProviderType(e.target.value)}>
            {providerTypes.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <input className="input" placeholder="API Base URL" value={apiBase} onChange={e => setApiBase(e.target.value)} />
          <input className="input" placeholder="API Key (optional)" type="password" value={apiKey} onChange={e => setApiKey(e.target.value)} />
          <input className="input" placeholder="Default model" value={defaultModel} onChange={e => setDefaultModel(e.target.value)} />
          <div className="form-actions">
            <button className="btn-primary" onClick={handleAddProvider}>Add</button>
            <button className="btn-secondary" onClick={() => setShowAddProvider(false)}>Cancel</button>
          </div>
        </div>
      )}

      <div className="provider-list">
        <h3>Providers</h3>
        {loading && <div className="loading">Loading...</div>}
        {providers.map(p => (
          <div key={p.provider_id} className="provider-card">
            <div className="provider-header">
              <div className="provider-info">
                <span className="provider-name">{p.name}</span>
                <span className="provider-type-badge">{p.provider_type}</span>
              </div>
              <div className="provider-status-area">
                <span className="provider-status" style={{ color: statusColor(p.status) }}>{p.status}</span>
                <button className="btn-danger-sm" onClick={() => handleRemoveProvider(p.provider_id)}>Remove</button>
              </div>
            </div>
            <div className="provider-details">
              <span className="provider-detail">Default: {p.default_model}</span>
              <span className="provider-detail">Models: {p.available_models.join(', ') || 'none'}</span>
              <span className="provider-detail">Rate Limit: {p.rate_limit_rpm} RPM</span>
              <span className="provider-detail">Weight: {p.weight}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};