import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import './AgentFlowPanel.css';

interface FlowStats {
  total_executions: number;
  total_tokens: number;
  recent: {
    count: number;
    success_rate: number;
    avg_quality: number;
    avg_duration_ms: number;
  };
  corrections: Record<string, number>;
  last_execution: {
    flow_id: string;
    success: boolean;
    quality: number;
    corrections: number;
  } | null;
}

interface FlowExecution {
  flow_id: string;
  success: boolean;
  quality_score: number;
  duration_ms: number;
  tokens: number;
  tool_calls: number;
  corrections: number;
  output_preview: string;
  timestamp: string;
}

interface ReasoningPath {
  path_id: string;
  strategy: string;
  confidence: number;
  duration_ms: number;
  result_preview: string;
}

interface ToolCallResult {
  call_id: string;
  tool_name: string;
  success: boolean;
  duration_ms: number;
  result_preview: string;
}

interface CorrectionRecord {
  phase: string;
  issue: string;
  strategy: string;
  quality_before?: number;
  quality_after?: number;
}

type TabId = 'structured' | 'parallel' | 'toolchain' | 'correction' | 'stream' | 'history' | 'stats';

export const AgentFlowPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('structured');
  const [stats, setStats] = useState<FlowStats | null>(null);
  const [history, setHistory] = useState<FlowExecution[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Structured output state
  const [structuredPrompt, setStructuredPrompt] = useState('');
  const [schemaFields, setSchemaFields] = useState('{"name": {"type": "string", "description": "Item name"}, "score": {"type": "number", "description": "Score value"}}');
  const [requiredFields, setRequiredFields] = useState('name,score');
  const [structuredResult, setStructuredResult] = useState<any>(null);

  // Parallel reasoning state
  const [reasoningPrompt, setReasoningPrompt] = useState('');
  const [numPaths, setNumPaths] = useState(3);
  const [reasoningPaths, setReasoningPaths] = useState<ReasoningPath[]>([]);
  const [bestPath, setBestPath] = useState<any>(null);
  const [synthesizedOutput, setSynthesizedOutput] = useState('');

  // Tool chain state
  const [toolChainTask, setToolChainTask] = useState('');
  const [toolChainResults, setToolChainResults] = useState<ToolCallResult[]>([]);
  const [toolChainOutput, setToolChainOutput] = useState('');

  // Correction state
  const [correctionPrompt, setCorrectionPrompt] = useState('');
  const [qualityThreshold, setQualityThreshold] = useState(0.7);
  const [correctionResult, setCorrectionResult] = useState<any>(null);
  const [corrections, setCorrections] = useState<CorrectionRecord[]>([]);

  // Stream state
  const [streamPrompt, setStreamPrompt] = useState('');
  const [streamContent, setStreamContent] = useState('');
  const [streaming, setStreaming] = useState(false);

  const loadStats = useCallback(async () => {
    try {
      const res = await api.agentFlow.stats();
      setStats(res);
    } catch (err) {
      console.error('Failed to load flow stats:', err);
    }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const res = await api.agentFlow.history();
      setHistory(res.executions || []);
    } catch (err) {
      console.error('Failed to load flow history:', err);
    }
  }, []);

  useEffect(() => {
    loadStats();
    loadHistory();
  }, [loadStats, loadHistory]);

  // Structured output execution
  const handleStructuredExecute = async () => {
    if (!structuredPrompt.trim()) return;
    setLoading(true);
    setError(null);
    setStructuredResult(null);
    try {
      let fields = {};
      try { fields = JSON.parse(schemaFields); } catch { fields = {}; }
      const reqFields = requiredFields.split(',').map(f => f.trim()).filter(Boolean);

      const res = await api.agentFlow.executeStructured({
        prompt: structuredPrompt,
        fields,
        required_fields: reqFields,
        strict_mode: true,
        schema_name: 'StructuredOutput',
      });
      setStructuredResult(res);
      loadStats();
      loadHistory();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Parallel reasoning execution
  const handleReasoningExecute = async () => {
    if (!reasoningPrompt.trim()) return;
    setLoading(true);
    setError(null);
    setReasoningPaths([]);
    setBestPath(null);
    setSynthesizedOutput('');
    try {
      const res = await api.agentFlow.reasonParallel({
        prompt: reasoningPrompt,
        num_paths: numPaths,
        synthesize: true,
      });
      setReasoningPaths(res.reasoning_paths || []);
      setBestPath(res.best_path);
      setSynthesizedOutput(res.final_output || '');
      loadStats();
      loadHistory();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Tool chain execution
  const handleToolChainExecute = async () => {
    if (!toolChainTask.trim()) return;
    setLoading(true);
    setError(null);
    setToolChainResults([]);
    setToolChainOutput('');
    try {
      const res = await api.agentFlow.executeToolChain({
        task: toolChainTask,
        tools: [],
        max_rounds: 5,
      });
      setToolChainResults(res.tool_calls || []);
      setToolChainOutput(res.final_output || '');
      loadStats();
      loadHistory();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Self-correction execution
  const handleCorrectionExecute = async () => {
    if (!correctionPrompt.trim()) return;
    setLoading(true);
    setError(null);
    setCorrectionResult(null);
    setCorrections([]);
    try {
      const res = await api.agentFlow.executeWithCorrection({
        prompt: correctionPrompt,
        quality_threshold: qualityThreshold,
        max_corrections: 3,
      });
      setCorrectionResult(res);
      setCorrections(res.corrections || []);
      loadStats();
      loadHistory();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Stream execution
  const handleStreamExecute = async () => {
    if (!streamPrompt.trim() || streaming) return;
    setStreaming(true);
    setStreamContent('');
    setError(null);
    try {
      const response = await api.agentFlow.stream({ prompt: streamPrompt });
      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6).trim();
          if (data === '[DONE]' || data === '{"type":"done"}') continue;
          try {
            const parsed = JSON.parse(data);
            if (parsed.type === 'token') {
              setStreamContent(prev => prev + parsed.content);
            }
          } catch {}
        }
      }
      loadStats();
      loadHistory();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setStreaming(false);
    }
  };

  const tabs: { id: TabId; label: string; icon: string }[] = [
    { id: 'structured', label: 'Structured Output', icon: '{}' },
    { id: 'parallel', label: 'Parallel Reasoning', icon: '⇉' },
    { id: 'toolchain', label: 'Tool Chain', icon: '⚙' },
    { id: 'correction', label: 'Self-Correction', icon: '↻' },
    { id: 'stream', label: 'Stream Demo', icon: '~' },
    { id: 'history', label: 'History', icon: '📋' },
    { id: 'stats', label: 'Statistics', icon: '📊' },
  ];

  const getStrategyColor = (strategy: string) => {
    const colors: Record<string, string> = {
      chain_of_thought: '#4a90d9',
      tree_of_thought: '#7b68ee',
      self_consistency: '#20b2aa',
      reflexion: '#ff6b6b',
      decomposition: '#ffa726',
      first_principles: '#ab47bc',
      analogical: '#66bb6a',
    };
    return colors[strategy] || '#888';
  };

  const renderStats = () => (
    <div className="flow-stats-grid">
      <div className="flow-stat-card">
        <div className="flow-stat-value">{stats?.total_executions ?? 0}</div>
        <div className="flow-stat-label">Total Executions</div>
      </div>
      <div className="flow-stat-card">
        <div className="flow-stat-value">{stats?.total_tokens ?? 0}</div>
        <div className="flow-stat-label">Total Tokens</div>
      </div>
      <div className="flow-stat-card">
        <div className="flow-stat-value">{((stats?.recent?.success_rate ?? 0) * 100).toFixed(1)}%</div>
        <div className="flow-stat-label">Success Rate</div>
      </div>
      <div className="flow-stat-card">
        <div className="flow-stat-value">{stats?.recent?.avg_quality.toFixed(2) ?? '0.00'}</div>
        <div className="flow-stat-label">Avg Quality</div>
      </div>
      <div className="flow-stat-card">
        <div className="flow-stat-value">{stats?.recent?.avg_duration_ms.toFixed(0) ?? '0'}ms</div>
        <div className="flow-stat-label">Avg Duration</div>
      </div>
    </div>
  );

  return (
    <div className="agent-flow-panel">
      <div className="flow-panel-header">
        <h2>AgentFlow Engine</h2>
        <span className="flow-panel-subtitle">Self-Correcting Agent Execution</span>
      </div>

      {renderStats()}

      <div className="flow-tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`flow-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="flow-tab-icon">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="flow-error">
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className="flow-tab-content">
        {/* Structured Output Tab */}
        {activeTab === 'structured' && (
          <div className="flow-section">
            <div className="flow-input-group">
              <label>Prompt</label>
              <textarea
                value={structuredPrompt}
                onChange={e => setStructuredPrompt(e.target.value)}
                placeholder="Enter a task that requires structured output..."
                rows={3}
              />
            </div>
            <div className="flow-input-row">
              <div className="flow-input-group">
                <label>Schema Fields (JSON)</label>
                <textarea
                  value={schemaFields}
                  onChange={e => setSchemaFields(e.target.value)}
                  rows={4}
                  className="flow-code-input"
                />
              </div>
              <div className="flow-input-group">
                <label>Required Fields (comma-separated)</label>
                <input
                  type="text"
                  value={requiredFields}
                  onChange={e => setRequiredFields(e.target.value)}
                  placeholder="name,score"
                />
              </div>
            </div>
            <button
              className="flow-execute-btn"
              onClick={handleStructuredExecute}
              disabled={loading || !structuredPrompt.trim()}
            >
              {loading ? 'Executing...' : 'Execute Structured Output'}
            </button>

            {structuredResult && (
              <div className="flow-result">
                <div className="flow-result-header">
                  <span className={`flow-badge ${structuredResult.success ? 'success' : 'error'}`}>
                    {structuredResult.success ? 'Success' : 'Failed'}
                  </span>
                  <span className="flow-meta">Quality: {structuredResult.quality_score}</span>
                  <span className="flow-meta">Corrections: {structuredResult.total_corrections}</span>
                  <span className="flow-meta">{structuredResult.total_duration_ms}ms</span>
                </div>
                <pre className="flow-output">{JSON.stringify(structuredResult.structured_output, null, 2)}</pre>
                {structuredResult.corrections?.length > 0 && (
                  <div className="flow-corrections">
                    <h4>Corrections Applied</h4>
                    {structuredResult.corrections.map((c: CorrectionRecord, i: number) => (
                      <div key={i} className="flow-correction-item">
                        <span className="flow-correction-phase">{c.phase}</span>
                        <span className="flow-correction-strategy">{c.strategy}</span>
                        <span className="flow-correction-issue">{c.issue}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Parallel Reasoning Tab */}
        {activeTab === 'parallel' && (
          <div className="flow-section">
            <div className="flow-input-group">
              <label>Problem to Reason About</label>
              <textarea
                value={reasoningPrompt}
                onChange={e => setReasoningPrompt(e.target.value)}
                placeholder="Enter a complex problem for multi-path reasoning..."
                rows={3}
              />
            </div>
            <div className="flow-input-row">
              <div className="flow-input-group">
                <label>Number of Reasoning Paths</label>
                <select value={numPaths} onChange={e => setNumPaths(Number(e.target.value))}>
                  {[2, 3, 4, 5].map(n => (
                    <option key={n} value={n}>{n} paths</option>
                  ))}
                </select>
              </div>
            </div>
            <button
              className="flow-execute-btn"
              onClick={handleReasoningExecute}
              disabled={loading || !reasoningPrompt.trim()}
            >
              {loading ? 'Reasoning...' : 'Run Parallel Reasoning'}
            </button>

            {reasoningPaths.length > 0 && (
              <div className="flow-result">
                <div className="flow-reasoning-grid">
                  {reasoningPaths.map((path, i) => (
                    <div key={path.path_id} className="flow-reasoning-card">
                      <div className="flow-reasoning-card-header">
                        <span className="flow-path-badge" style={{ background: getStrategyColor(path.strategy) }}>
                          {path.strategy.replace(/_/g, ' ')}
                        </span>
                        <span className="flow-confidence">
                          Confidence: {(path.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="flow-reasoning-preview">{path.result_preview}</div>
                      <div className="flow-reasoning-meta">{path.duration_ms}ms</div>
                    </div>
                  ))}
                </div>

                {bestPath && (
                  <div className="flow-best-path">
                    <h4>Best Path: {bestPath.strategy.replace(/_/g, ' ')} ({(bestPath.confidence * 100).toFixed(0)}%)</h4>
                  </div>
                )}

                {synthesizedOutput && (
                  <div className="flow-synthesis">
                    <h4>Synthesized Answer</h4>
                    <div className="flow-output-text">{synthesizedOutput}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Tool Chain Tab */}
        {activeTab === 'toolchain' && (
          <div className="flow-section">
            <div className="flow-input-group">
              <label>Task for Tool Chain</label>
              <textarea
                value={toolChainTask}
                onChange={e => setToolChainTask(e.target.value)}
                placeholder="Describe a multi-step task that requires tool usage..."
                rows={3}
              />
            </div>
            <button
              className="flow-execute-btn"
              onClick={handleToolChainExecute}
              disabled={loading || !toolChainTask.trim()}
            >
              {loading ? 'Executing Tool Chain...' : 'Execute Tool Chain'}
            </button>

            {toolChainResults.length > 0 && (
              <div className="flow-result">
                <div className="flow-tool-chain-timeline">
                  {toolChainResults.map((tc, i) => (
                    <div key={tc.call_id} className="flow-tool-step">
                      <div className="flow-tool-step-indicator">
                        <span className={`flow-tool-dot ${tc.success ? 'success' : 'error'}`} />
                        {i < toolChainResults.length - 1 && <span className="flow-tool-line" />}
                      </div>
                      <div className="flow-tool-step-content">
                        <div className="flow-tool-step-header">
                          <strong>{tc.tool_name}</strong>
                          <span className={`flow-tool-status ${tc.success ? 'success' : 'error'}`}>
                            {tc.success ? 'OK' : 'Failed'}
                          </span>
                        </div>
                        <pre className="flow-tool-result">{tc.result_preview}</pre>
                        <span className="flow-tool-duration">{tc.duration_ms}ms</span>
                      </div>
                    </div>
                  ))}
                </div>
                {toolChainOutput && (
                  <div className="flow-tool-chain-output">
                    <h4>Final Output</h4>
                    <div className="flow-output-text">{toolChainOutput}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Self-Correction Tab */}
        {activeTab === 'correction' && (
          <div className="flow-section">
            <div className="flow-input-group">
              <label>Task for Self-Correction</label>
              <textarea
                value={correctionPrompt}
                onChange={e => setCorrectionPrompt(e.target.value)}
                placeholder="Enter a task that benefits from iterative refinement..."
                rows={3}
              />
            </div>
            <div className="flow-input-row">
              <div className="flow-input-group">
                <label>Quality Threshold</label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={qualityThreshold}
                  onChange={e => setQualityThreshold(Number(e.target.value))}
                />
                <span className="flow-range-value">{qualityThreshold.toFixed(2)}</span>
              </div>
            </div>
            <button
              className="flow-execute-btn"
              onClick={handleCorrectionExecute}
              disabled={loading || !correctionPrompt.trim()}
            >
              {loading ? 'Refining...' : 'Run Self-Correction'}
            </button>

            {correctionResult && (
              <div className="flow-result">
                <div className="flow-result-header">
                  <span className="flow-meta">Quality: {correctionResult.quality_score}</span>
                  <span className="flow-meta">Corrections: {correctionResult.total_corrections}</span>
                  <span className="flow-meta">{correctionResult.total_duration_ms}ms</span>
                </div>
                <div className="flow-output-text">{correctionResult.final_output}</div>
                {corrections.length > 0 && (
                  <div className="flow-corrections">
                    <h4>Correction History</h4>
                    {corrections.map((c, i) => (
                      <div key={i} className="flow-correction-item">
                        <span className="flow-correction-phase">{c.phase}</span>
                        <span className="flow-correction-strategy">{c.strategy}</span>
                        <span className="flow-correction-issue">{c.issue}</span>
                        {c.quality_before !== undefined && (
                          <span className="flow-quality-change">
                            {c.quality_before?.toFixed(2)} → {c.quality_after?.toFixed(2)}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Stream Demo Tab */}
        {activeTab === 'stream' && (
          <div className="flow-section">
            <div className="flow-input-group">
              <label>Prompt for Streaming</label>
              <textarea
                value={streamPrompt}
                onChange={e => setStreamPrompt(e.target.value)}
                placeholder="Enter a prompt to see real-time streaming output..."
                rows={3}
              />
            </div>
            <button
              className="flow-execute-btn"
              onClick={handleStreamExecute}
              disabled={streaming || !streamPrompt.trim()}
            >
              {streaming ? 'Streaming...' : 'Start Stream'}
            </button>
            {streaming && (
              <button className="flow-stop-btn" onClick={() => setStreaming(false)}>
                Stop
              </button>
            )}
            {streamContent && (
              <div className="flow-stream-output">
                <div className="flow-stream-content">{streamContent}</div>
              </div>
            )}
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="flow-section">
            <button className="flow-refresh-btn" onClick={loadHistory}>
              Refresh
            </button>
            <div className="flow-history-list">
              {history.length === 0 ? (
                <p className="flow-empty">No execution history yet. Run some operations above.</p>
              ) : (
                history.map(exec => (
                  <div key={exec.flow_id} className="flow-history-item">
                    <div className="flow-history-header">
                      <span className="flow-history-id">{exec.flow_id}</span>
                      <span className={`flow-badge ${exec.success ? 'success' : 'error'}`}>
                        {exec.success ? 'Success' : 'Failed'}
                      </span>
                    </div>
                    <div className="flow-history-meta">
                      <span>Quality: {exec.quality_score.toFixed(2)}</span>
                      <span>{exec.duration_ms}ms</span>
                      <span>{exec.tokens} tokens</span>
                      <span>{exec.tool_calls} tool calls</span>
                      <span>{exec.corrections} corrections</span>
                    </div>
                    <div className="flow-history-preview">{exec.output_preview}</div>
                    <div className="flow-history-time">{new Date(exec.timestamp).toLocaleString()}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Statistics Tab */}
        {activeTab === 'stats' && (
          <div className="flow-section">
            <button className="flow-refresh-btn" onClick={loadStats}>
              Refresh Stats
            </button>
            {stats && (
              <div className="flow-detailed-stats">
                <div className="flow-stats-section">
                  <h3>Execution Overview</h3>
                  <div className="flow-stats-grid">
                    <div className="flow-stat-card">
                      <div className="flow-stat-value">{stats.total_executions}</div>
                      <div className="flow-stat-label">Total Executions</div>
                    </div>
                    <div className="flow-stat-card">
                      <div className="flow-stat-value">{stats.total_tokens.toLocaleString()}</div>
                      <div className="flow-stat-label">Total Tokens</div>
                    </div>
                    <div className="flow-stat-card">
                      <div className="flow-stat-value">{((stats.recent.success_rate) * 100).toFixed(1)}%</div>
                      <div className="flow-stat-label">Recent Success Rate</div>
                    </div>
                    <div className="flow-stat-card">
                      <div className="flow-stat-value">{stats.recent.avg_quality.toFixed(3)}</div>
                      <div className="flow-stat-label">Avg Quality Score</div>
                    </div>
                    <div className="flow-stat-card">
                      <div className="flow-stat-value">{stats.recent.avg_duration_ms.toFixed(0)}ms</div>
                      <div className="flow-stat-label">Avg Duration</div>
                    </div>
                    <div className="flow-stat-card">
                      <div className="flow-stat-value">{stats.recent.count}</div>
                      <div className="flow-stat-label">Recent Executions</div>
                    </div>
                  </div>
                </div>

                {Object.keys(stats.corrections).length > 0 && (
                  <div className="flow-stats-section">
                    <h3>Correction Strategies</h3>
                    <div className="flow-correction-stats">
                      {Object.entries(stats.corrections).map(([strategy, count]) => (
                        <div key={strategy} className="flow-correction-stat-item">
                          <span className="flow-correction-stat-name">{strategy}</span>
                          <span className="flow-correction-stat-count">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {stats.last_execution && (
                  <div className="flow-stats-section">
                    <h3>Last Execution</h3>
                    <div className="flow-last-execution">
                      <div><strong>Flow ID:</strong> {stats.last_execution.flow_id}</div>
                      <div><strong>Success:</strong> {stats.last_execution.success ? 'Yes' : 'No'}</div>
                      <div><strong>Quality:</strong> {stats.last_execution.quality.toFixed(3)}</div>
                      <div><strong>Corrections:</strong> {stats.last_execution.corrections}</div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};