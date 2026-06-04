import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

interface AgentSimple {
  id: string;
  name: string;
}

interface CollaborationResult {
  thread_id: string;
  query: string;
  participants: string[];
  rounds: number;
  consensus: string;
  discussion: Array<{ round: number; responses: Array<{ agent: string; response: string }> }>;
}

export const CollaborationPanel: React.FC = () => {
  const [agents, setAgents] = useState<AgentSimple[]>([]);
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [query, setQuery] = useState('');
  const [maxRounds, setMaxRounds] = useState(3);
  const [result, setResult] = useState<CollaborationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [transferTo, setTransferTo] = useState('');
  const [transferContext, setTransferContext] = useState('');
  const toast = useToast();

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      const data = await api.agents.list();
      const list = data.items.map(a => ({ id: a.id, name: a.name }));
      setAgents(list);
      if (list.length >= 2) setSelectedAgents([list[0].id, list[1].id]);
    } catch {}
  };

  const toggleAgent = (id: string) => {
    setSelectedAgents(prev =>
      prev.includes(id)
        ? prev.filter(a => a !== id)
        : [...prev, id]
    );
  };

  const startCollaboration = async () => {
    if (selectedAgents.length < 2 || !query.trim()) return;
    setLoading(true);
    setError('');
    try {
      const data = await api.collaborate.execute({
        query: query.trim(),
        agent_ids: selectedAgents,
        max_rounds: maxRounds,
      });
      setResult(data);
    } catch (e: any) {
      setError(e.message || 'Collaboration failed');
    } finally {
      setLoading(false);
    }
  };

  const transferTask = async () => {
    if (!transferTo || !transferContext.trim()) return;
    setLoading(true);
    try {
      const data = await api.collaborate.transfer({
        from_agent_id: selectedAgents[0] || '',
        to_agent_id: transferTo,
        context: transferContext,
      });
      setTransferContext('');
      setError('');
      toast.info(`Task transferred to ${data.to_name}`);
    } catch (e: any) {
      setError(e.message || 'Transfer failed');
    } finally {
      setLoading(false);
    }
  };

  const getAgentName = (id: string) => agents.find(a => a.id === id)?.name || id;

  return (
    <div className="collab-panel">
      <h2>Agent Collaboration</h2>
      <p className="subtitle">Multi-agent discussion, task transfer, and response verification</p>

      {error && <div className="error-banner">{error}</div>}

      <div className="collab-section">
        <h3>Collaborative Discussion</h3>
        <div className="agent-selector">
          <label>Select Agents:</label>
          <div className="agent-chips">
            {agents.map(agent => (
              <button
                key={agent.id}
                className={`agent-chip ${selectedAgents.includes(agent.id) ? 'active' : ''}`}
                onClick={() => toggleAgent(agent.id)}
              >
                {agent.name}
              </button>
            ))}
          </div>
        </div>
        <div className="collab-inputs">
          <input
            type="text"
            placeholder="What should the agents discuss?"
            value={query}
            onChange={e => setQuery(e.target.value)}
            className="query-input"
          />
          <div className="collab-controls">
            <label>Rounds:</label>
            <select value={maxRounds} onChange={e => setMaxRounds(Number(e.target.value))}>
              {[1, 2, 3, 5, 10].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
            <button
              onClick={startCollaboration}
              disabled={loading || selectedAgents.length < 2 || !query.trim()}
            >
              {loading ? 'Discussing...' : 'Start Discussion'}
            </button>
          </div>
        </div>
      </div>

      {result && (
        <div className="collab-result">
          <h4>Discussion Result</h4>
          <div className="result-meta">
            <span>Thread: {result.thread_id}</span>
            <span>Rounds: {result.rounds}</span>
            <span>Agents: {result.participants.length}</span>
          </div>
          <div className="consensus-section">
            <h5>Consensus</h5>
            <div className="consensus-text">{result.consensus}</div>
          </div>
          <div className="discussion-rounds">
            {result.discussion.map((round, i) => (
              <div key={i} className="round-item">
                <h5>Round {round.round}</h5>
                {round.responses.map((resp, j) => (
                  <div key={j} className="agent-response">
                    <span className="resp-agent">{resp.agent}</span>
                    <div className="resp-text">{resp.response}</div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="transfer-section">
        <h3>Task Transfer</h3>
        <div className="transfer-inputs">
          <select value={transferTo} onChange={e => setTransferTo(e.target.value)}>
            <option value="">Select target agent...</option>
            {agents.map(a => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
          <textarea
            placeholder="Describe the task context to transfer..."
            value={transferContext}
            onChange={e => setTransferContext(e.target.value)}
            rows={3}
          />
          <button onClick={transferTask} disabled={loading || !transferTo || !transferContext.trim()}>
            Transfer Task
          </button>
        </div>
      </div>

      <style>{`
        .collab-panel { padding: 24px; max-width: 1000px; margin: 0 auto; }
        .collab-panel h2 { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }
        .subtitle { color: #6b7280; margin-bottom: 24px; }
        .collab-section { background: #fff; border-radius: 12px; padding: 24px; border: 1px solid #e5e7eb; margin-bottom: 24px; }
        .collab-section h3, .transfer-section h3 { font-size: 1.1rem; font-weight: 700; margin-bottom: 16px; }
        .agent-selector { margin-bottom: 16px; }
        .agent-selector label { font-size: 0.85rem; font-weight: 600; color: #6b7280; display: block; margin-bottom: 8px; }
        .agent-chips { display: flex; gap: 8px; flex-wrap: wrap; }
        .agent-chip { padding: 6px 14px; border: 1px solid #d1d5db; border-radius: 20px; background: #fff; cursor: pointer; font-size: 0.85rem; transition: all 0.15s; }
        .agent-chip.active { background: #3b82f6; color: #fff; border-color: #3b82f6; }
        .agent-chip:hover { border-color: #3b82f6; }
        .collab-inputs { display: flex; flex-direction: column; gap: 12px; }
        .query-input { width: 100%; padding: 12px 16px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.95rem; }
        .collab-controls { display: flex; align-items: center; gap: 12px; }
        .collab-controls select { padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.9rem; }
        .collab-controls button { padding: 10px 24px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
        .collab-controls button:hover { background: #2563eb; }
        .collab-controls button:disabled { background: #9ca3af; }
        .collab-result { background: #fff; border-radius: 12px; padding: 24px; border: 1px solid #e5e7eb; margin-bottom: 24px; }
        .collab-result h4 { font-size: 1rem; font-weight: 700; margin-bottom: 12px; }
        .result-meta { display: flex; gap: 20px; font-size: 0.8rem; color: #9ca3af; margin-bottom: 16px; }
        .consensus-section { margin-bottom: 20px; }
        .consensus-section h5 { font-size: 0.85rem; font-weight: 600; color: #374151; margin-bottom: 8px; }
        .consensus-text { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 16px; font-size: 0.9rem; color: #374151; line-height: 1.5; }
        .round-item { margin-bottom: 16px; }
        .round-item h5 { font-size: 0.85rem; font-weight: 600; color: #6b7280; margin-bottom: 8px; }
        .agent-response { margin-bottom: 10px; }
        .resp-agent { font-weight: 600; font-size: 0.8rem; color: #3b82f6; margin-bottom: 4px; display: block; }
        .resp-text { background: #f9fafb; border-radius: 6px; padding: 12px; font-size: 0.85rem; color: #374151; }
        .transfer-section { background: #fff; border-radius: 12px; padding: 24px; border: 1px solid #e5e7eb; }
        .transfer-inputs { display: flex; flex-direction: column; gap: 12px; }
        .transfer-inputs select { padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.9rem; }
        .transfer-inputs textarea { width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.9rem; resize: vertical; }
        .transfer-inputs button { padding: 10px 20px; background: #8b5cf6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; align-self: flex-start; }
        .transfer-inputs button:hover { background: #7c3aed; }
        .transfer-inputs button:disabled { background: #9ca3af; }
        .error-banner { background: #fef2f2; color: #991b1b; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 0.9rem; }
      `}</style>
    </div>
  );
};