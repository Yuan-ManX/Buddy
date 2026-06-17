import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type {
  SynthesisStats, SynthesisReport, KnowledgeConflict, AgentRecommendation, SynthesisResult,
  FusionResult, TrustNetwork, CollectiveDecision, ResolvedConflict, DistilledKnowledge,
} from '../types';

export const SynthesisPanel: React.FC = () => {
  const [stats, setStats] = useState<SynthesisStats | null>(null);
  const [reports, setReports] = useState<SynthesisReport[]>([]);
  const [conflicts, setConflicts] = useState<KnowledgeConflict[]>([]);
  const [recommendations, setRecommendations] = useState<AgentRecommendation[]>([]);
  const [synthesisResult, setSynthesisResult] = useState<SynthesisResult | null>(null);
  const [contributeForm, setContributeForm] = useState({ agentId: '', agentName: '', content: '', insightType: 'strategy', confidence: 0.5 });
  const [recAgentId, setRecAgentId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'synthesize' | 'conflicts' | 'recommendations' | 'fuse' | 'trust-network' | 'decide' | 'resolved' | 'distill'>('overview');

  // Knowledge fusion state
  const [fusionAgentIds, setFusionAgentIds] = useState('');
  const [fusionTopic, setFusionTopic] = useState('');
  const [fusionResult, setFusionResult] = useState<FusionResult | null>(null);
  const [fusionLoading, setFusionLoading] = useState(false);

  // Trust network state
  const [trustNetwork, setTrustNetwork] = useState<TrustNetwork | null>(null);

  // Collective decision state
  const [decideTopic, setDecideTopic] = useState('');
  const [decideOptions, setDecideOptions] = useState('');
  const [decideAgentIds, setDecideAgentIds] = useState('');
  const [collectiveDecision, setCollectiveDecision] = useState<CollectiveDecision | null>(null);
  const [decideLoading, setDecideLoading] = useState(false);

  // Resolved conflicts state
  const [resolvedConflicts, setResolvedConflicts] = useState<ResolvedConflict[]>([]);

  // Distilled knowledge state
  const [distillTopic, setDistillTopic] = useState('');
  const [distilledKnowledge, setDistilledKnowledge] = useState<DistilledKnowledge[]>([]);
  const [distillLoading, setDistillLoading] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [s, r, c] = await Promise.all([
        api.synthesis.stats(),
        api.synthesis.reports(10),
        api.synthesis.conflicts(20),
      ]);
      setStats(s);
      setReports(r.reports);
      setConflicts(c.conflicts);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load synthesis data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleContribute = async () => {
    if (!contributeForm.agentId || !contributeForm.content) return;
    try {
      await api.synthesis.contribute(
        contributeForm.agentId,
        contributeForm.agentName || contributeForm.agentId,
        contributeForm.content,
        contributeForm.insightType,
        contributeForm.confidence
      );
      setContributeForm({ agentId: '', agentName: '', content: '', insightType: 'strategy', confidence: 0.5 });
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Contribution failed');
    }
  };

  const handleSynthesize = async (mode: string) => {
    try {
      const result = await api.synthesis.synthesize(mode);
      setSynthesisResult(result);
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Synthesis failed');
    }
  };

  const handleGetRecommendations = async () => {
    if (!recAgentId) return;
    try {
      const result = await api.synthesis.recommendations(recAgentId);
      setRecommendations(result.recommendations);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to get recommendations');
    }
  };

  // Knowledge fusion
  const handleFuse = async () => {
    if (!fusionAgentIds.trim()) return;
    setFusionLoading(true);
    try {
      const agentIds = fusionAgentIds.split(',').map((s) => s.trim()).filter(Boolean);
      const result = await api.synthesis.fuse(agentIds, fusionTopic || undefined);
      setFusionResult(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Fusion failed');
    } finally {
      setFusionLoading(false);
    }
  };

  const loadTrustNetwork = async () => {
    try {
      const result = await api.synthesis.trustNetwork();
      setTrustNetwork(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load trust network');
    }
  };

  // Collective decision
  const handleDecide = async () => {
    if (!decideTopic.trim() || !decideOptions.trim()) return;
    setDecideLoading(true);
    try {
      const options = decideOptions.split(',').map((s) => s.trim()).filter(Boolean);
      const agentIds = decideAgentIds ? decideAgentIds.split(',').map((s) => s.trim()).filter(Boolean) : undefined;
      const result = await api.synthesis.decide(decideTopic, options, agentIds);
      setCollectiveDecision(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Decision failed');
    } finally {
      setDecideLoading(false);
    }
  };

  const loadResolvedConflicts = async () => {
    try {
      const result = await api.synthesis.resolvedConflicts(20);
      setResolvedConflicts(result.conflicts);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load resolved conflicts');
    }
  };

  // Distilled knowledge
  const handleDistill = async () => {
    setDistillLoading(true);
    try {
      const result = await api.synthesis.distill(distillTopic || undefined, 20);
      setDistilledKnowledge(result.knowledge);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Distillation failed');
    } finally {
      setDistillLoading(false);
    }
  };

  if (loading) return <div className="panel-loading">Loading synthesis data...</div>;

  return (
    <div className="synthesis-panel">
      <div className="panel-header">
        <h2>Agent Synthesis</h2>
        <button onClick={loadData} className="btn btn-sm btn-primary">Refresh</button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="section-tabs">
        {(['overview', 'synthesize', 'conflicts', 'recommendations', 'fuse', 'trust-network', 'decide', 'resolved', 'distill'] as const).map((s) => (
          <button
            key={s}
            className={`tab-btn ${activeSection === s ? 'active' : ''}`}
            onClick={() => {
              setActiveSection(s);
              if (s === 'trust-network' && !trustNetwork) loadTrustNetwork();
              if (s === 'resolved' && resolvedConflicts.length === 0) loadResolvedConflicts();
            }}
          >
            {s === 'trust-network' ? 'Trust Network' : s === 'resolved' ? 'Resolved' : s === 'distill' ? 'Distill' : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {activeSection === 'overview' && stats && (
        <div className="synthesis-overview">
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Contributions</div>
              <div className="stat-value">{stats.total_contributions}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Reports</div>
              <div className="stat-value">{stats.total_synthesis_reports}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Conflicts</div>
              <div className="stat-value">{stats.total_conflicts}</div>
              <div className="stat-sub">Resolved: {stats.resolved_conflicts}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Active Agents</div>
              <div className="stat-value">{stats.active_agents}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Recent Insights</div>
              <div className="stat-value">{stats.recent_insights}</div>
            </div>
          </div>

          <div className="trust-scores">
            <h3>Agent Trust Scores</h3>
            {Object.keys(stats.agent_trust_scores).length === 0 ? (
              <p className="empty-state">No agents contributed yet.</p>
            ) : (
              <div className="trust-list">
                {Object.entries(stats.agent_trust_scores).map(([id, score]) => (
                  <div key={id} className="trust-item">
                    <span className="agent-id">{id}</span>
                    <div className="trust-bar">
                      <div className="trust-fill" style={{ width: `${score * 100}%` }} />
                    </div>
                    <span className="trust-value">{(score * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="recent-reports">
            <h3>Recent Synthesis Reports</h3>
            {reports.length === 0 ? (
              <p className="empty-state">No reports generated yet.</p>
            ) : (
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Agents</th>
                      <th>Contributions</th>
                      <th>Insights</th>
                      <th>Conflicts</th>
                      <th>Emergent Patterns</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reports.map((r) => (
                      <tr key={r.id}>
                        <td>{r.total_agents}</td>
                        <td>{r.total_contributions}</td>
                        <td>{r.insights_count}</td>
                        <td>{r.conflicts_count}</td>
                        <td className="truncate">{r.emergent_patterns.join(', ') || '-'}</td>
                        <td>{new Date(r.timestamp).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {activeSection === 'synthesize' && (
        <div className="synthesize-section">
          <div className="contribute-form">
            <h3>Contribute Insight</h3>
            <div className="form-grid">
              <input
                type="text"
                placeholder="Agent ID"
                value={contributeForm.agentId}
                onChange={(e) => setContributeForm({ ...contributeForm, agentId: e.target.value })}
                className="input"
              />
              <input
                type="text"
                placeholder="Agent Name"
                value={contributeForm.agentName}
                onChange={(e) => setContributeForm({ ...contributeForm, agentName: e.target.value })}
                className="input"
              />
              <select
                value={contributeForm.insightType}
                onChange={(e) => setContributeForm({ ...contributeForm, insightType: e.target.value })}
                className="select"
              >
                <option value="strategy">Strategy</option>
                <option value="tool_usage">Tool Usage</option>
                <option value="pattern">Pattern</option>
                <option value="behavior">Behavior</option>
                <option value="collaboration">Collaboration</option>
                <option value="emergent">Emergent</option>
              </select>
              <input
                type="number"
                min="0"
                max="1"
                step="0.1"
                value={contributeForm.confidence}
                onChange={(e) => setContributeForm({ ...contributeForm, confidence: parseFloat(e.target.value) || 0.5 })}
                className="input"
              />
            </div>
            <textarea
              placeholder="Insight content..."
              value={contributeForm.content}
              onChange={(e) => setContributeForm({ ...contributeForm, content: e.target.value })}
              className="textarea"
              rows={3}
            />
            <button onClick={handleContribute} className="btn btn-primary">Contribute</button>
          </div>

          <div className="synthesize-actions">
            <h3>Run Synthesis</h3>
            <div className="synthesis-modes">
              {['aggregate', 'consensus', 'detect', 'resolve'].map((mode) => (
                <button key={mode} onClick={() => handleSynthesize(mode)} className="btn btn-secondary">
                  {mode.charAt(0).toUpperCase() + mode.slice(1)}
                </button>
              ))}
            </div>
            {synthesisResult && (
              <div className="synthesis-result">
                <h4>Result: {synthesisResult.report_id}</h4>
                <div className="result-grid">
                  <div className="result-item">
                    <label>Insights</label>
                    <span>{synthesisResult.insights}</span>
                  </div>
                  <div className="result-item">
                    <label>Conflicts</label>
                    <span>{synthesisResult.conflicts}</span>
                  </div>
                  <div className="result-item">
                    <label>Agents</label>
                    <span>{synthesisResult.total_agents}</span>
                  </div>
                </div>
                {synthesisResult.emergent_patterns.length > 0 && (
                  <div className="emergent-patterns">
                    <h4>Emergent Patterns</h4>
                    <ul>
                      {synthesisResult.emergent_patterns.map((p, i) => (
                        <li key={i}>{p}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {activeSection === 'conflicts' && (
        <div className="conflicts-section">
          <h3>Knowledge Conflicts ({conflicts.length})</h3>
          {conflicts.length === 0 ? (
            <p className="empty-state">No conflicts detected.</p>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Agent A</th>
                    <th>Agent B</th>
                    <th>Topic</th>
                    <th>Resolved</th>
                    <th>Resolution</th>
                  </tr>
                </thead>
                <tbody>
                  {conflicts.map((c) => (
                    <tr key={c.id}>
                      <td>{c.agent_a}</td>
                      <td>{c.agent_b}</td>
                      <td className="truncate">{c.topic}</td>
                      <td><span className={`badge ${c.resolved ? 'badge-success' : 'badge-warning'}`}>{c.resolved ? 'Yes' : 'No'}</span></td>
                      <td className="truncate">{c.resolution || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeSection === 'recommendations' && (
        <div className="recommendations-section">
          <h3>Cross-Agent Learning</h3>
          <div className="recommendation-form">
            <input
              type="text"
              placeholder="Agent ID for recommendations"
              value={recAgentId}
              onChange={(e) => setRecAgentId(e.target.value)}
              className="input"
              onKeyDown={(e) => e.key === 'Enter' && handleGetRecommendations()}
            />
            <button onClick={handleGetRecommendations} className="btn btn-primary">Get Recommendations</button>
          </div>
          {recommendations.length === 0 ? (
            <p className="empty-state">Enter an agent ID to get cross-agent learning recommendations.</p>
          ) : (
            <div className="recommendations-list">
              {recommendations.map((r, i) => (
                <div key={i} className="recommendation-card">
                  <div className="rec-header">
                    <span className="badge badge-primary">{r.insight_type}</span>
                    <span className="from-agent">From: {r.from_agent}</span>
                    <span className="trust">Trust: {(r.source_trust * 100).toFixed(0)}%</span>
                  </div>
                  <p>{r.content}</p>
                  <span className="confidence">Confidence: {(r.confidence * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeSection === 'fuse' && (
        <div className="fuse-section">
          <h3>Knowledge Fusion</h3>
          <p className="section-description">Combine knowledge from multiple agents into a unified synthesis.</p>
          <div className="fuse-form">
            <div className="form-row">
              <input
                type="text"
                placeholder="Agent IDs (comma-separated)"
                value={fusionAgentIds}
                onChange={(e) => setFusionAgentIds(e.target.value)}
                className="input"
              />
              <input
                type="text"
                placeholder="Topic (optional)"
                value={fusionTopic}
                onChange={(e) => setFusionTopic(e.target.value)}
                className="input"
              />
            </div>
            <button onClick={handleFuse} className="btn btn-primary" disabled={fusionLoading || !fusionAgentIds.trim()}>
              {fusionLoading ? 'Fusing...' : 'Fuse Knowledge'}
            </button>
          </div>
          {fusionResult && (
            <div className="fusion-result">
              <div className="result-header">
                <span className="fusion-id">Fusion: {fusionResult.fusion_id}</span>
                <span className="confidence-badge">Confidence: {(fusionResult.confidence * 100).toFixed(0)}%</span>
              </div>
              <div className="source-agents">
                <span className="label">Source Agents:</span>
                {fusionResult.source_agents.map((a) => (
                  <span key={a} className="badge badge-primary">{a}</span>
                ))}
              </div>
              <div className="synthetic-knowledge">
                <h4>Unified Knowledge</h4>
                <p>{fusionResult.synthetic_knowledge}</p>
              </div>
              {fusionResult.supporting_evidence.length > 0 && (
                <div className="supporting-evidence">
                  <h4>Supporting Evidence</h4>
                  <ul>
                    {fusionResult.supporting_evidence.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeSection === 'trust-network' && (
        <div className="trust-network-section">
          <h3>Trust Network</h3>
          <p className="section-description">Agent trust relationships and interaction patterns.</p>
          {trustNetwork ? (
            <div className="trust-network-content">
              <div className="network-stats">
                <div className="stat-card">
                  <div className="stat-label">Nodes</div>
                  <div className="stat-value">{trustNetwork.nodes.length}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Edges</div>
                  <div className="stat-value">{trustNetwork.edges.length}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Avg Trust</div>
                  <div className="stat-value">{(trustNetwork.avg_trust * 100).toFixed(0)}%</div>
                </div>
              </div>
              <div className="network-nodes">
                <h4>Agent Trust Scores</h4>
                {trustNetwork.nodes.map((node) => (
                  <div key={node.agent_id} className="network-node">
                    <div className="node-header">
                      <span className="node-name">{node.agent_name || node.agent_id}</span>
                      <span className="node-trust-score">{(node.trust_score * 100).toFixed(0)}%</span>
                    </div>
                    <div className="trust-bar">
                      <div className="trust-fill" style={{ width: `${node.trust_score * 100}%` }} />
                    </div>
                    {node.connections.length > 0 && (
                      <div className="node-connections">
                        <span className="connections-label">Connections:</span>
                        {node.connections.map((c, i) => (
                          <span key={i} className="connection-badge" title={`Weight: ${c.weight.toFixed(2)}`}>
                            {c.target} ({c.weight.toFixed(1)})
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="empty-state-with-action">
              <p>No trust network data loaded.</p>
              <button onClick={loadTrustNetwork} className="btn btn-primary">Load Trust Network</button>
            </div>
          )}
        </div>
      )}

      {activeSection === 'decide' && (
        <div className="decide-section">
          <h3>Collective Decision</h3>
          <p className="section-description">Let agents vote on a decision topic.</p>
          <div className="decide-form">
            <input
              type="text"
              placeholder="Topic (e.g., 'Which approach is best?')"
              value={decideTopic}
              onChange={(e) => setDecideTopic(e.target.value)}
              className="input"
            />
            <input
              type="text"
              placeholder="Options (comma-separated)"
              value={decideOptions}
              onChange={(e) => setDecideOptions(e.target.value)}
              className="input"
            />
            <input
              type="text"
              placeholder="Agent IDs (optional, comma-separated)"
              value={decideAgentIds}
              onChange={(e) => setDecideAgentIds(e.target.value)}
              className="input"
            />
            <button onClick={handleDecide} className="btn btn-primary" disabled={decideLoading || !decideTopic.trim() || !decideOptions.trim()}>
              {decideLoading ? 'Deciding...' : 'Run Decision'}
            </button>
          </div>
          {collectiveDecision && (
            <div className="decision-result">
              <div className="result-header">
                <span className="decision-id">Decision: {collectiveDecision.decision_id}</span>
                <span className="confidence-badge">Confidence: {(collectiveDecision.confidence * 100).toFixed(0)}%</span>
              </div>
              <div className="winner-section">
                <h4>Winner: <span className="winner-option">{collectiveDecision.winner}</span></h4>
              </div>
              <div className="votes-section">
                <h4>Votes</h4>
                <div className="votes-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Agent</th>
                        {collectiveDecision.options.map((opt) => (
                          <th key={opt}>{opt}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(collectiveDecision.votes).map(([agent, voteRecord]) => (
                        <tr key={agent}>
                          <td>{agent}</td>
                          {collectiveDecision.options.map((opt) => (
                            <td key={opt}>{voteRecord[opt] || 0}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {activeSection === 'resolved' && (
        <div className="resolved-section">
          <h3>Resolved Conflicts</h3>
          <p className="section-description">Historical conflicts that have been resolved.</p>
          {resolvedConflicts.length === 0 ? (
            <div className="empty-state-with-action">
              <p>No resolved conflicts loaded.</p>
              <button onClick={loadResolvedConflicts} className="btn btn-primary">Load Resolved Conflicts</button>
            </div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Agent A</th>
                    <th>Agent B</th>
                    <th>Topic</th>
                    <th>Strategy</th>
                    <th>Resolution</th>
                    <th>Resolved At</th>
                  </tr>
                </thead>
                <tbody>
                  {resolvedConflicts.map((c) => (
                    <tr key={c.id}>
                      <td>{c.agent_a}</td>
                      <td>{c.agent_b}</td>
                      <td className="truncate">{c.topic}</td>
                      <td><span className="badge">{c.resolution_strategy}</span></td>
                      <td className="truncate">{c.resolution}</td>
                      <td>{new Date(c.resolved_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeSection === 'distill' && (
        <div className="distill-section">
          <h3>Distilled Knowledge</h3>
          <p className="section-description">Search and extract consolidated insights from agent knowledge.</p>
          <div className="distill-form">
            <input
              type="text"
              placeholder="Topic (optional, leave empty for all)"
              value={distillTopic}
              onChange={(e) => setDistillTopic(e.target.value)}
              className="input"
            />
            <button onClick={handleDistill} className="btn btn-primary" disabled={distillLoading}>
              {distillLoading ? 'Distilling...' : 'Search Knowledge'}
            </button>
          </div>
          {distilledKnowledge.length > 0 && (
            <div className="distilled-results">
              {distilledKnowledge.map((item) => (
                <div key={item.id} className="distilled-card">
                  <div className="distilled-header">
                    <span className="distilled-topic">{item.topic}</span>
                    <span className="confidence-badge">{(item.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <p className="distilled-summary">{item.summary}</p>
                  <div className="distilled-meta">
                    <span className="distilled-sources">
                      Sources: {item.source_agents.map((a) => (
                        <span key={a} className="badge badge-sm">{a}</span>
                      ))}
                    </span>
                    <span className="distilled-time">{new Date(item.created_at).toLocaleString()}</span>
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