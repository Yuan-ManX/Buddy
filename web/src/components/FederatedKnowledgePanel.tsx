import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface FederatedKnowledgeStats {
  total_shares: number;
  total_subscriptions: number;
  active_topics: number;
  knowledge_exchange_rate: number;
}

interface KnowledgeShare {
  share_id: string;
  agent_id: string;
  knowledge_type: string;
  content: string;
  confidence: number;
  tags: string[];
  source: string;
  version: number;
  created_at: string;
}

interface SubscriptionDetails {
  subscription_id: string;
  agent_id: string;
  topics: string[];
  active: boolean;
  created_at: string;
}

interface MergedResult {
  unified_content: string;
  conflicts: ConflictEntry[];
  confidence: number;
  sources: string[];
}

interface ConflictEntry {
  source: string;
  content: string;
  type: string;
}

interface ShareResponse {
  message: string;
  share: KnowledgeShare;
}

interface RequestResponse {
  message: string;
  results: KnowledgeShare[];
}

interface SubscribeResponse {
  message: string;
  subscription: SubscriptionDetails;
}

interface MergeResponse {
  message: string;
  merged: MergedResult;
}

// ── Request helper ──

const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try {
      const parsed = JSON.parse(body);
      message = parsed.detail || parsed.error || body;
    } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Component ──

export const FederatedKnowledgePanel: React.FC = () => {
  const toast = useToast();

  const [stats, setStats] = useState<FederatedKnowledgeStats | null>(null);
  const [shares, setShares] = useState<KnowledgeShare[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'share' | 'request' | 'subscribe' | 'merge'>('overview');

  // Share form
  const [shareForm, setShareForm] = useState({
    agent_id: '',
    knowledge_type: 'fact',
    content: '',
    confidence: 0.8,
    tags: '',
  });
  const [sharing, setSharing] = useState(false);
  const [shareResult, setShareResult] = useState<ShareResponse | null>(null);

  // Request form
  const [requestForm, setRequestForm] = useState({
    agent_id: '',
    query: '',
    knowledge_type: '',
  });
  const [requesting, setRequesting] = useState(false);
  const [requestResults, setRequestResults] = useState<KnowledgeShare[] | null>(null);

  // Subscribe form
  const [subscribeForm, setSubscribeForm] = useState({
    agent_id: '',
    topics: '',
  });
  const [subscribing, setSubscribing] = useState(false);
  const [subscribeResult, setSubscribeResult] = useState<SubscribeResponse | null>(null);

  // Merge state
  const [selectedShares, setSelectedShares] = useState<Set<string>>(new Set());
  const [merging, setMerging] = useState(false);
  const [mergeResult, setMergeResult] = useState<MergeResponse | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, sh] = await Promise.all([
        request<FederatedKnowledgeStats>('/federated-knowledge/stats').catch(() => null),
        request<KnowledgeShare[]>('/federated-knowledge/shares').catch(() => []),
      ]);
      setStats(s);
      setShares(Array.isArray(sh) ? sh : (sh as any)?.shares || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load federated knowledge data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const refreshShares = async () => {
    try {
      const sh = await request<KnowledgeShare[]>('/federated-knowledge/shares').catch(() => []);
      setShares(Array.isArray(sh) ? sh : (sh as any)?.shares || []);
    } catch {}
  };

  // ── Share handler ──
  const handleShare = async () => {
    if (!shareForm.agent_id.trim() || !shareForm.content.trim()) return;
    try {
      setSharing(true);
      const result = await request<ShareResponse>('/federated-knowledge/share', {
        method: 'POST',
        body: JSON.stringify({
          agent_id: shareForm.agent_id,
          knowledge_type: shareForm.knowledge_type,
          content: shareForm.content,
          confidence: shareForm.confidence,
          tags: shareForm.tags
            .split(',')
            .map(t => t.trim())
            .filter(Boolean),
        }),
      });
      toast.success(result.message || 'Knowledge shared successfully');
      setShareResult(result);
      setShareForm({ agent_id: '', knowledge_type: 'fact', content: '', confidence: 0.8, tags: '' });
      refreshShares();
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setSharing(false);
    }
  };

  // ── Request handler ──
  const handleRequest = async () => {
    if (!requestForm.agent_id.trim() || !requestForm.query.trim()) return;
    try {
      setRequesting(true);
      const result = await request<RequestResponse>('/federated-knowledge/request', {
        method: 'POST',
        body: JSON.stringify({
          agent_id: requestForm.agent_id,
          query: requestForm.query,
          knowledge_type: requestForm.knowledge_type || undefined,
        }),
      });
      toast.success(result.message || 'Knowledge requested successfully');
      setRequestResults(result.results || []);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setRequesting(false);
    }
  };

  // ── Subscribe handler ──
  const handleSubscribe = async () => {
    if (!subscribeForm.agent_id.trim() || !subscribeForm.topics.trim()) return;
    try {
      setSubscribing(true);
      const result = await request<SubscribeResponse>('/federated-knowledge/subscribe', {
        method: 'POST',
        body: JSON.stringify({
          agent_id: subscribeForm.agent_id,
          topics: subscribeForm.topics
            .split(',')
            .map(t => t.trim())
            .filter(Boolean),
        }),
      });
      toast.success(result.message || 'Subscribed successfully');
      setSubscribeResult(result);
      setSubscribeForm({ agent_id: '', topics: '' });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setSubscribing(false);
    }
  };

  // ── Merge handler ──
  const handleMerge = async () => {
    if (selectedShares.size === 0) return;
    try {
      setMerging(true);
      const result = await request<MergeResponse>('/federated-knowledge/merge', {
        method: 'POST',
        body: JSON.stringify({
          share_ids: Array.from(selectedShares),
        }),
      });
      toast.success(result.message || 'Knowledge merged successfully');
      setMergeResult(result);
      setSelectedShares(new Set());
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setMerging(false);
    }
  };

  const toggleShareSelection = (shareId: string) => {
    setSelectedShares(prev => {
      const next = new Set(prev);
      if (next.has(shareId)) {
        next.delete(shareId);
      } else {
        next.add(shareId);
      }
      return next;
    });
  };

  const knowledgeTypeColors: Record<string, string> = {
    fact: '#3b82f6',
    procedure: '#22c55e',
    pattern: '#8b5cf6',
    insight: '#f59e0b',
    warning: '#ef4444',
    preference: '#06b6d4',
    discovery: '#ec4899',
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Federated Knowledge Exchange</h2>
          <p className="panel-subtitle">Share, request, and merge knowledge across federated agents</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading federated knowledge data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Federated Knowledge Exchange</h2>
        <p className="panel-subtitle">Share, request, subscribe, and merge knowledge across federated agents</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_shares}</span>
              <span className="stat-label">Total Shares</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#22c55e' }}>{stats.total_subscriptions}</span>
              <span className="stat-label">Subscriptions</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#3b82f6' }}>{stats.active_topics}</span>
              <span className="stat-label">Active Topics</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: stats.knowledge_exchange_rate >= 0.8 ? '#22c55e' : '#f59e0b' }}>
                {(stats.knowledge_exchange_rate * 100).toFixed(1)}%
              </span>
              <span className="stat-label">Exchange Rate</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'share', 'request', 'subscribe', 'merge'] as const).map(t => (
          <button
            key={t}
            className={`forge-tab ${activeTab === t ? 'active' : ''}`}
            onClick={() => setActiveTab(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Overview Tab ── */}
      {activeTab === 'overview' && (
        <div className="dashboard-section">
          {stats && (
            <>
              <h3>Federated Knowledge Overview</h3>
              <div className="dashboard-stat-row">
                <span>Total Shares</span>
                <strong>{stats.total_shares}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Subscriptions</span>
                <strong style={{ color: '#22c55e' }}>{stats.total_subscriptions}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Active Topics</span>
                <strong style={{ color: '#3b82f6' }}>{stats.active_topics}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Knowledge Exchange Rate</span>
                <strong style={{ color: stats.knowledge_exchange_rate >= 0.8 ? '#22c55e' : '#f59e0b' }}>
                  {(stats.knowledge_exchange_rate * 100).toFixed(1)}%
                </strong>
              </div>

              <h3 style={{ marginTop: 24 }}>Recent Shares</h3>
              {shares.length === 0 ? (
                <div className="panel-empty">No knowledge shares yet</div>
              ) : (
                <div className="forge-skill-list">
                  {shares.slice(0, 5).map(share => (
                    <div key={share.share_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{share.agent_id}</div>
                        <span className="dashboard-badge" style={{
                          background: knowledgeTypeColors[share.knowledge_type] || '#9ca3af',
                          color: '#fff',
                        }}>
                          {share.knowledge_type}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>{share.content.length > 120 ? share.content.slice(0, 120) + '...' : share.content}</div>
                        <div>Confidence: {(share.confidence * 100).toFixed(0)}% | Tags: {share.tags?.join(', ') || 'none'}</div>
                        <div>Source: {share.source} | v{share.version}</div>
                        <div>Created: {new Date(share.created_at).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Share Tab ── */}
      {activeTab === 'share' && (
        <div className="dashboard-section">
          <h3>Share Knowledge</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Agent ID</label>
              <input
                type="text"
                value={shareForm.agent_id}
                onChange={e => setShareForm(f => ({ ...f, agent_id: e.target.value }))}
                placeholder="Enter agent ID"
              />
            </div>
            <div className="form-group">
              <label>Knowledge Type</label>
              <select
                value={shareForm.knowledge_type}
                onChange={e => setShareForm(f => ({ ...f, knowledge_type: e.target.value }))}
              >
                <option value="fact">Fact</option>
                <option value="procedure">Procedure</option>
                <option value="pattern">Pattern</option>
                <option value="insight">Insight</option>
                <option value="warning">Warning</option>
                <option value="preference">Preference</option>
                <option value="discovery">Discovery</option>
              </select>
            </div>
            <div className="form-group">
              <label>Content</label>
              <textarea
                rows={4}
                value={shareForm.content}
                onChange={e => setShareForm(f => ({ ...f, content: e.target.value }))}
                placeholder="Enter the knowledge content to share"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Confidence (0-1)</label>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.05}
                  value={shareForm.confidence}
                  onChange={e => setShareForm(f => ({ ...f, confidence: parseFloat(e.target.value) || 0 }))}
                />
              </div>
              <div className="form-group">
                <label>Tags (comma-separated)</label>
                <input
                  type="text"
                  value={shareForm.tags}
                  onChange={e => setShareForm(f => ({ ...f, tags: e.target.value }))}
                  placeholder="e.g. ml, python, optimization"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              onClick={handleShare}
              disabled={sharing || !shareForm.agent_id.trim() || !shareForm.content.trim()}
            >
              {sharing ? 'Sharing...' : 'Share Knowledge'}
            </button>
          </div>

          {shareResult && (
            <div className="dashboard-section">
              <h3>Share Result</h3>
              <div className="forge-skill-card">
                <div className="forge-skill-header">
                  <div className="forge-skill-name">{shareResult.share.share_id}</div>
                  <span className="dashboard-badge" style={{
                    background: knowledgeTypeColors[shareResult.share.knowledge_type] || '#9ca3af',
                    color: '#fff',
                  }}>
                    {shareResult.share.knowledge_type}
                  </span>
                </div>
                <div className="forge-skill-meta">
                  <div>Agent: {shareResult.share.agent_id}</div>
                  <div>Content: {shareResult.share.content}</div>
                  <div>Confidence: {(shareResult.share.confidence * 100).toFixed(0)}%</div>
                  <div>Tags: {shareResult.share.tags?.join(', ') || 'none'}</div>
                  <div>Source: {shareResult.share.source} | v{shareResult.share.version}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Request Tab ── */}
      {activeTab === 'request' && (
        <div className="dashboard-section">
          <h3>Request Knowledge</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Agent ID</label>
              <input
                type="text"
                value={requestForm.agent_id}
                onChange={e => setRequestForm(f => ({ ...f, agent_id: e.target.value }))}
                placeholder="Enter agent ID"
              />
            </div>
            <div className="form-group">
              <label>Query</label>
              <input
                type="text"
                value={requestForm.query}
                onChange={e => setRequestForm(f => ({ ...f, query: e.target.value }))}
                placeholder="What knowledge are you looking for?"
              />
            </div>
            <div className="form-group">
              <label>Knowledge Type (optional)</label>
              <select
                value={requestForm.knowledge_type}
                onChange={e => setRequestForm(f => ({ ...f, knowledge_type: e.target.value }))}
              >
                <option value="">Any</option>
                <option value="fact">Fact</option>
                <option value="procedure">Procedure</option>
                <option value="pattern">Pattern</option>
                <option value="insight">Insight</option>
                <option value="warning">Warning</option>
                <option value="preference">Preference</option>
                <option value="discovery">Discovery</option>
              </select>
            </div>
            <button
              className="btn-primary"
              onClick={handleRequest}
              disabled={requesting || !requestForm.agent_id.trim() || !requestForm.query.trim()}
            >
              {requesting ? 'Requesting...' : 'Request Knowledge'}
            </button>
          </div>

          {requestResults && requestResults.length === 0 && (
            <div className="panel-empty">No matching knowledge found</div>
          )}
          {requestResults && requestResults.length > 0 && (
            <div className="dashboard-section">
              <h3>Results ({requestResults.length})</h3>
              <div className="forge-skill-list">
                {requestResults.map(share => (
                  <div key={share.share_id} className="forge-skill-card">
                    <div className="forge-skill-header">
                      <div className="forge-skill-name">{share.agent_id}</div>
                      <span className="dashboard-badge" style={{
                        background: knowledgeTypeColors[share.knowledge_type] || '#9ca3af',
                        color: '#fff',
                      }}>
                        {share.knowledge_type}
                      </span>
                    </div>
                    <div className="forge-skill-meta">
                      <div>{share.content}</div>
                      <div>Confidence: {(share.confidence * 100).toFixed(0)}% | Tags: {share.tags?.join(', ') || 'none'}</div>
                      <div>Source: {share.source} | v{share.version}</div>
                      <div>Created: {new Date(share.created_at).toLocaleString()}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Subscribe Tab ── */}
      {activeTab === 'subscribe' && (
        <div className="dashboard-section">
          <h3>Subscribe to Topics</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Agent ID</label>
              <input
                type="text"
                value={subscribeForm.agent_id}
                onChange={e => setSubscribeForm(f => ({ ...f, agent_id: e.target.value }))}
                placeholder="Enter agent ID"
              />
            </div>
            <div className="form-group">
              <label>Topics (comma-separated)</label>
              <input
                type="text"
                value={subscribeForm.topics}
                onChange={e => setSubscribeForm(f => ({ ...f, topics: e.target.value }))}
                placeholder="e.g. ml, nlp, computer-vision"
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleSubscribe}
              disabled={subscribing || !subscribeForm.agent_id.trim() || !subscribeForm.topics.trim()}
            >
              {subscribing ? 'Subscribing...' : 'Subscribe'}
            </button>
          </div>

          {subscribeResult && (
            <div className="dashboard-section">
              <h3>Subscription Details</h3>
              <div className="forge-skill-card">
                <div className="forge-skill-header">
                  <div className="forge-skill-name">{subscribeResult.subscription.subscription_id}</div>
                  <span className="dashboard-badge" style={{
                    background: subscribeResult.subscription.active ? '#22c55e' : '#ef4444',
                    color: '#fff',
                  }}>
                    {subscribeResult.subscription.active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <div className="forge-skill-meta">
                  <div>Agent: {subscribeResult.subscription.agent_id}</div>
                  <div>Topics: {subscribeResult.subscription.topics?.join(', ') || 'none'}</div>
                  <div>Created: {new Date(subscribeResult.subscription.created_at).toLocaleString()}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Merge Tab ── */}
      {activeTab === 'merge' && (
        <div className="dashboard-section">
          <h3>Merge Knowledge</h3>
          <p style={{ color: '#9ca3af', marginBottom: 16 }}>Select knowledge shares to merge into unified knowledge</p>

          {shares.length === 0 ? (
            <div className="panel-empty">No knowledge shares available to merge</div>
          ) : (
            <>
              <div className="forge-skill-list">
                {shares.map(share => (
                  <div
                    key={share.share_id}
                    className="forge-skill-card"
                    style={{
                      borderColor: selectedShares.has(share.share_id) ? '#3b82f6' : undefined,
                      cursor: 'pointer',
                    }}
                    onClick={() => toggleShareSelection(share.share_id)}
                  >
                    <div className="forge-skill-header">
                      <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={selectedShares.has(share.share_id)}
                          onChange={() => toggleShareSelection(share.share_id)}
                          onClick={e => e.stopPropagation()}
                        />
                        <div className="forge-skill-name">{share.agent_id}</div>
                      </label>
                      <span className="dashboard-badge" style={{
                        background: knowledgeTypeColors[share.knowledge_type] || '#9ca3af',
                        color: '#fff',
                      }}>
                        {share.knowledge_type}
                      </span>
                    </div>
                    <div className="forge-skill-meta">
                      <div>{share.content.length > 120 ? share.content.slice(0, 120) + '...' : share.content}</div>
                      <div>Confidence: {(share.confidence * 100).toFixed(0)}% | Tags: {share.tags?.join(', ') || 'none'}</div>
                      <div>Source: {share.source} | v{share.version}</div>
                    </div>
                  </div>
                ))}
              </div>

              <button
                className="btn-primary"
                onClick={handleMerge}
                disabled={merging || selectedShares.size === 0}
                style={{ marginTop: 16 }}
              >
                {merging ? 'Merging...' : `Merge Selected (${selectedShares.size})`}
              </button>
            </>
          )}

          {mergeResult && (
            <div className="dashboard-section" style={{ marginTop: 24 }}>
              <h3>Merge Result</h3>
              <div className="forge-skill-card">
                <div className="forge-skill-header">
                  <div className="forge-skill-name">Unified Knowledge</div>
                  <span className="dashboard-badge" style={{
                    background: mergeResult.merged.confidence >= 0.8 ? '#22c55e' : '#f59e0b',
                    color: '#fff',
                  }}>
                    Confidence: {(mergeResult.merged.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="forge-skill-meta">
                  <div><strong>Content:</strong> {mergeResult.merged.unified_content}</div>
                  <div><strong>Sources:</strong> {mergeResult.merged.sources?.join(', ') || 'none'}</div>
                </div>
              </div>

              {mergeResult.merged.conflicts && mergeResult.merged.conflicts.length > 0 && (
                <>
                  <h4 style={{ marginTop: 16, color: '#f59e0b' }}>Conflicts ({mergeResult.merged.conflicts.length})</h4>
                  <div className="forge-skill-list">
                    {mergeResult.merged.conflicts.map((conflict, idx) => (
                      <div key={idx} className="forge-skill-card" style={{ borderColor: '#f59e0b' }}>
                        <div className="forge-skill-header">
                          <div className="forge-skill-name">{conflict.type}</div>
                          <span className="dashboard-badge" style={{ background: '#f59e0b', color: '#fff' }}>
                            {conflict.source}
                          </span>
                        </div>
                        <div className="forge-skill-meta">
                          <div>{conflict.content}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FederatedKnowledgePanel;