import React, { useState } from 'react';
import type { Agent, SubAgentResult } from '../types';
import { api } from '../api/client';

interface SubAgentPanelProps {
  agent: Agent;
}

export const SubAgentPanel: React.FC<SubAgentPanelProps> = ({ agent }) => {
  const [tasks, setTasks] = useState<Array<{ name: string; instructions: string; task: string }>>([
    { name: '', instructions: '', task: '' },
  ]);
  const [results, setResults] = useState<SubAgentResult[] | null>(null);
  const [aggregated, setAggregated] = useState<string | null>(null);
  const [executing, setExecuting] = useState(false);
  const [model, setModel] = useState('gpt-4o-mini');

  const addTask = () => {
    setTasks([...tasks, { name: '', instructions: '', task: '' }]);
  };

  const removeTask = (index: number) => {
    setTasks(tasks.filter((_, i) => i !== index));
  };

  const updateTask = (index: number, field: string, value: string) => {
    const updated = [...tasks];
    updated[index] = { ...updated[index], [field]: value };
    setTasks(updated);
  };

  const handleExecute = async () => {
    const validTasks = tasks.filter((t) => t.task.trim());
    if (validTasks.length === 0) return;

    setExecuting(true);
    setResults(null);
    setAggregated(null);

    try {
      const res = await api.subagents.execute(agent.id, validTasks, model);
      setResults(res);
    } catch (err) {
      console.error('Sub-agent execution failed:', err);
    } finally {
      setExecuting(false);
    }
  };

  const handleAggregate = async () => {
    const validTasks = tasks.filter((t) => t.task.trim());
    if (validTasks.length === 0) return;

    setExecuting(true);
    setResults(null);
    setAggregated(null);

    try {
      const res = await api.subagents.aggregate(agent.id, validTasks, model);
      setAggregated(res.aggregated);
    } catch (err) {
      console.error('Aggregation failed:', err);
    } finally {
      setExecuting(false);
    }
  };

  const STATUS_COLORS: Record<string, string> = {
    completed: '#10b981',
    running: '#f59e0b',
    failed: '#ef4444',
    idle: '#6b7280',
  };

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div>
          <h2>Sub-Agent Orchestration — {agent.name}</h2>
          <span className="panel-subtitle">
            Execute tasks in parallel with multiple sub-agents
          </span>
        </div>
      </div>

      <div className="subagent-config">
        <div className="form-group">
          <label>Model</label>
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            <option value="gpt-4o-mini">GPT-4o Mini (Fast)</option>
            <option value="gpt-4o">GPT-4o (Standard)</option>
            <option value="gpt-4">GPT-4 (Premium)</option>
          </select>
        </div>
      </div>

      <div className="subagent-tasks">
        {tasks.map((t, i) => (
          <div key={i} className="subagent-task-card">
            <div className="subagent-task-header">
              <span className="subagent-task-index">Worker {i + 1}</span>
              {tasks.length > 1 && (
                <button className="btn-sm btn-danger" onClick={() => removeTask(i)}>Remove</button>
              )}
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  placeholder="Worker name"
                  value={t.name}
                  onChange={(e) => updateTask(i, 'name', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Instructions</label>
                <input
                  type="text"
                  placeholder="Worker instructions"
                  value={t.instructions}
                  onChange={(e) => updateTask(i, 'instructions', e.target.value)}
                />
              </div>
            </div>
            <div className="form-group">
              <label>Task</label>
              <textarea
                placeholder="Describe the task for this worker..."
                value={t.task}
                onChange={(e) => updateTask(i, 'task', e.target.value)}
                rows={2}
              />
            </div>
          </div>
        ))}

        <button className="btn-secondary btn-full" onClick={addTask}>
          + Add Worker
        </button>
      </div>

      <div className="subagent-actions">
        <button
          className="btn-primary"
          onClick={handleExecute}
          disabled={executing || tasks.every((t) => !t.task.trim())}
        >
          {executing ? 'Executing...' : 'Execute Parallel'}
        </button>
        <button
          className="btn-secondary"
          onClick={handleAggregate}
          disabled={executing || tasks.every((t) => !t.task.trim())}
        >
          Execute & Aggregate
        </button>
      </div>

      {aggregated && (
        <div className="subagent-aggregated">
          <div className="subagent-aggregated-header">Aggregated Report</div>
          <pre className="subagent-aggregated-content">{aggregated}</pre>
        </div>
      )}

      {results && (
        <div className="subagent-results">
          <h3>Results ({results.length} workers)</h3>
          {results.map((r, i) => (
            <div key={i} className={`subagent-result-card ${r.status}`}>
              <div className="subagent-result-header">
                <div
                  className="subagent-result-status"
                  style={{ background: STATUS_COLORS[r.status] || '#6b7280' }}
                >
                  {r.status}
                </div>
                <span className="subagent-result-id">{r.agent_id}</span>
                <span className="subagent-result-tokens">{r.tokens_used} tokens</span>
              </div>
              <div className="subagent-result-task">{r.task.slice(0, 200)}</div>
              <div className="subagent-result-content">{r.result.slice(0, 500)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};