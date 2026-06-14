import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { Agent } from '../types';

interface AgentMetrics {
  agent_id: string;
  agent_name: string;
  total_tokens: number;
  success_rate: number;
  avg_response_time_ms: number;
  tasks_completed: number;
  tasks_failed: number;
  quality_score: number;
  accuracy: number;
}

interface ComparisonData {
  agents: AgentMetrics[];
  timestamp: string;
}

// Simple bar chart using SVG
function BarChart({ data, label, color, maxValue }: { data: { name: string; value: number }[]; label: string; color: string; maxValue?: number }) {
  const max = maxValue || Math.max(...data.map((d) => d.value), 1);
  const height = 200;
  const width = Math.max(data.length * 80, 300);
  const barWidth = 60;
  const gap = 20;

  return (
    <div className="comparison-chart">
      <div className="comparison-chart-title">{label}</div>
      <svg width={width} height={height} className="bar-chart">
        {data.map((d, i) => {
          const barHeight = (d.value / max) * (height - 40);
          const x = i * (barWidth + gap) + gap / 2;
          const y = height - barHeight - 20;
          return (
            <g key={d.name}>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                fill={color}
                rx="4"
                opacity="0.85"
              />
              <text
                x={x + barWidth / 2}
                y={y - 6}
                textAnchor="middle"
                className="bar-chart-value"
                fontSize="11"
                fontWeight="600"
                fill="var(--text-secondary)"
              >
                {d.value.toLocaleString()}
              </text>
              <text
                x={x + barWidth / 2}
                y={height - 4}
                textAnchor="middle"
                className="bar-chart-label"
                fontSize="10"
                fill="var(--text-muted)"
              >
                {d.name}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// Radar chart using SVG
function RadarChart({ data, metrics }: { data: Record<string, number[]>; metrics: string[] }) {
  const size = 240;
  const cx = size / 2;
  const cy = size / 2;
  const radius = 100;
  const levels = 5;
  const angleStep = (2 * Math.PI) / metrics.length;

  const agentColors = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6', '#06b6d4'];

  // Radar grid
  const gridLines = Array.from({ length: levels }, (_, l) => {
    const r = ((l + 1) / levels) * radius;
    const points = metrics
      .map((_, i) => {
        const angle = angleStep * i - Math.PI / 2;
        return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`;
      })
      .join(' ');
    return <polygon key={`grid-${l}`} points={points} fill="none" stroke="var(--border)" strokeWidth="1" />;
  });

  // Axis lines
  const axes = metrics.map((_, i) => {
    const angle = angleStep * i - Math.PI / 2;
    return (
      <line
        key={`axis-${i}`}
        x1={cx}
        y1={cy}
        x2={cx + radius * Math.cos(angle)}
        y2={cy + radius * Math.sin(angle)}
        stroke="var(--border)"
        strokeWidth="1"
      />
    );
  });

  // Labels
  const labels = metrics.map((m, i) => {
    const angle = angleStep * i - Math.PI / 2;
    const lx = cx + (radius + 24) * Math.cos(angle);
    const ly = cy + (radius + 24) * Math.sin(angle);
    return (
      <text key={`label-${i}`} x={lx} y={ly} textAnchor="middle" dominantBaseline="central" fontSize="10" fill="var(--text-muted)">
        {m}
      </text>
    );
  });

  // Data polygons
  const agentNames = Object.keys(data);
  const polygons = agentNames.map((name, ai) => {
    const values = data[name];
    if (!values || values.length !== metrics.length) return null;
    const points = values
      .map((v, i) => {
        const angle = angleStep * i - Math.PI / 2;
        const r = (v / 100) * radius;
        return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`;
      })
      .join(' ');
    const color = agentColors[ai % agentColors.length];
    return (
      <polygon
        key={`poly-${name}`}
        points={points}
        fill={color}
        fillOpacity="0.15"
        stroke={color}
        strokeWidth="2"
      />
    );
  });

  return (
    <div className="comparison-chart">
      <div className="comparison-chart-title">Performance Radar</div>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {gridLines}
        {axes}
        {labels}
        {polygons}
      </svg>
      <div className="radar-legend">
        {agentNames.map((name, i) => (
          <div key={name} className="radar-legend-item">
            <span className="radar-legend-dot" style={{ background: agentColors[i % agentColors.length] }} />
            <span>{name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Ranking table
function RankingTable({ agents, metric, label }: { agents: AgentMetrics[]; metric: keyof AgentMetrics; label: string }) {
  const sorted = [...agents].sort((a, b) => {
    const va = typeof a[metric] === 'number' ? a[metric] : 0;
    const vb = typeof b[metric] === 'number' ? b[metric] : 0;
    // Higher is better for success_rate, quality_score, accuracy; lower for response time
    if (metric === 'avg_response_time_ms') return (va as number) - (vb as number);
    return (vb as number) - (va as number);
  });

  const medals = ['🥇', '🥈', '🥉'];

  return (
    <div className="ranking-table-container">
      <div className="ranking-table-title">{label}</div>
      <table className="ranking-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Agent</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
          {sorted.slice(0, 5).map((a, i) => (
            <tr key={a.agent_id} className={i < 3 ? `rank-${i + 1}` : ''}>
              <td>{i < 3 ? medals[i] : i + 1}</td>
              <td>{a.agent_name}</td>
              <td>
                {metric === 'avg_response_time_ms'
                  ? `${(a[metric] as number).toFixed(0)}ms`
                  : metric === 'total_tokens'
                  ? (a[metric] as number).toLocaleString()
                  : `${((a[metric] as number) * 100).toFixed(1)}%`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Historical trend sparkline
function TrendLine({ data }: { data: number[] }) {
  if (data.length === 0) return null;
  const width = 200;
  const height = 40;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1 || 1)) * width;
    const y = height - ((v - min) / range) * (height - 8) - 4;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width={width} height={height} className="trend-sparkline">
      <polyline
        fill="none"
        stroke="#3b82f6"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}

export const AgentComparison: React.FC<{ agents: Agent[] }> = ({ agents }) => {
  const [metrics, setMetrics] = useState<AgentMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [history, setHistory] = useState<ComparisonData[]>([]);
  const [selectedMetric, setSelectedMetric] = useState<string>('success_rate');

  const loadMetrics = useCallback(async () => {
    if (agents.length === 0) return;
    try {
      setLoading(true);
      const agentMetrics: AgentMetrics[] = [];

      await Promise.all(
        agents.map(async (agent) => {
          try {
            const stats = await api.engine.stats(agent.id);
            agentMetrics.push({
              agent_id: agent.id,
              agent_name: agent.name,
              total_tokens: stats.routing?.total_requests || 0,
              success_rate: stats.tools?.success_rate ? parseFloat(stats.tools.success_rate) / 100 : 0,
              avg_response_time_ms: stats.reasoning?.avg_time_ms || 0,
              tasks_completed: 0,
              tasks_failed: 0,
              quality_score: stats.reasoning?.success_rate ? parseFloat(stats.reasoning.success_rate) : 0,
              accuracy: stats.tools?.success_rate ? parseFloat(stats.tools.success_rate) / 100 : 0,
            });
          } catch {
            agentMetrics.push({
              agent_id: agent.id,
              agent_name: agent.name,
              total_tokens: 0,
              success_rate: 0,
              avg_response_time_ms: 0,
              tasks_completed: 0,
              tasks_failed: 0,
              quality_score: 0,
              accuracy: 0,
            });
          }
        })
      );

      setMetrics(agentMetrics);

      // Store historical snapshot
      setHistory((prev) => {
        const updated = [
          ...prev,
          { agents: agentMetrics, timestamp: new Date().toISOString() },
        ];
        return updated.slice(-20);
      });
    } catch (err) {
      console.error('Agent comparison load error:', err);
    } finally {
      setLoading(false);
    }
  }, [agents]);

  useEffect(() => {
    loadMetrics();
    const interval = setInterval(loadMetrics, 30000);
    return () => clearInterval(interval);
  }, [loadMetrics]);

  if (loading && metrics.length === 0) {
    return (
      <div className="agent-comparison">
        <div className="panel-loading">Loading agent comparison data...</div>
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <div className="agent-comparison">
        <div className="panel-empty">No agents available for comparison.</div>
      </div>
    );
  }

  const barData = metrics.map((m) => ({
    name: m.agent_name,
    value: selectedMetric === 'total_tokens'
      ? m.total_tokens
      : selectedMetric === 'avg_response_time_ms'
      ? m.avg_response_time_ms
      : selectedMetric === 'success_rate'
      ? Math.round(m.success_rate * 100)
      : selectedMetric === 'quality_score'
      ? Math.round(m.quality_score * 100)
      : Math.round((m.tasks_completed / Math.max(m.tasks_completed + m.tasks_failed, 1)) * 100),
  }));

  const metricLabel = {
    total_tokens: 'Total Tokens Used',
    avg_response_time_ms: 'Avg Response Time (ms)',
    success_rate: 'Success Rate (%)',
    quality_score: 'Quality Score (%)',
    tasks_completed: 'Tasks Completed',
  }[selectedMetric] || 'Metric';

  const metricColor = {
    total_tokens: '#3b82f6',
    avg_response_time_ms: '#f59e0b',
    success_rate: '#22c55e',
    quality_score: '#8b5cf6',
    tasks_completed: '#06b6d4',
  }[selectedMetric] || '#3b82f6';

  // Radar data
  const radarData: Record<string, number[]> = {};
  metrics.forEach((m) => {
    radarData[m.agent_name] = [
      Math.round(m.success_rate * 100),
      Math.round(m.accuracy * 100),
      Math.round(m.quality_score * 100),
      Math.min(Math.round((1 - m.avg_response_time_ms / 10000) * 100), 100), // Invert: lower is better
      m.total_tokens > 0 ? Math.min(Math.round((m.total_tokens / 100000) * 100), 100) : 0,
    ];
  });

  return (
    <div className="agent-comparison">
      <div className="system-overview-header">
        <h2>Agent Comparison</h2>
        <button className="btn-sm" onClick={loadMetrics}>
          Refresh
        </button>
      </div>

      {/* Side-by-side comparison table */}
      <div className="system-overview-section">
        <h3>Side-by-Side Comparison</h3>
        <div className="comparison-table-wrapper">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Success Rate</th>
                <th>Quality Score</th>
                <th>Accuracy</th>
                <th>Avg Response</th>
                <th>Total Tokens</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m) => (
                <tr key={m.agent_id}>
                  <td className="comparison-agent-name">{m.agent_name}</td>
                  <td>
                    <span style={{ color: m.success_rate >= 0.8 ? '#22c55e' : m.success_rate >= 0.5 ? '#f59e0b' : '#ef4444' }}>
                      {(m.success_rate * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td>
                    <span style={{ color: m.quality_score >= 0.8 ? '#22c55e' : m.quality_score >= 0.5 ? '#f59e0b' : '#ef4444' }}>
                      {(m.quality_score * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td>
                    <span style={{ color: m.accuracy >= 0.8 ? '#22c55e' : m.accuracy >= 0.5 ? '#f59e0b' : '#ef4444' }}>
                      {(m.accuracy * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td>{m.avg_response_time_ms > 0 ? `${m.avg_response_time_ms.toFixed(0)}ms` : 'N/A'}</td>
                  <td>{m.total_tokens.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bar Chart */}
      <div className="system-overview-section">
        <div className="comparison-controls">
          <h3>Metric Comparison</h3>
          <select
            className="dashboard-refresh-select"
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value)}
          >
            <option value="total_tokens">Total Tokens</option>
            <option value="avg_response_time_ms">Response Time</option>
            <option value="success_rate">Success Rate</option>
            <option value="quality_score">Quality Score</option>
            <option value="tasks_completed">Tasks Completed</option>
          </select>
        </div>
        <BarChart
          data={barData}
          label={metricLabel}
          color={metricColor}
        />
      </div>

      {/* Charts Row */}
      <div className="comparison-charts-row">
        {/* Radar Chart */}
        <div className="system-overview-section comparison-radar-container">
          <RadarChart
            data={radarData}
            metrics={['Success', 'Accuracy', 'Quality', 'Speed', 'Volume']}
          />
        </div>

        {/* Rankings */}
        <div className="system-overview-section comparison-rankings">
          <RankingTable agents={metrics} metric="success_rate" label="Top by Success Rate" />
          <RankingTable agents={metrics} metric="quality_score" label="Top by Quality Score" />
          <RankingTable agents={metrics} metric="avg_response_time_ms" label="Fastest Response" />
        </div>
      </div>

      {/* Historical Trends */}
      {history.length > 1 && (
        <div className="system-overview-section">
          <h3>Historical Trend</h3>
          <div className="trend-list">
            {metrics.map((m) => {
              const trend = history.map((h) => {
                const agent = h.agents.find((a) => a.agent_id === m.agent_id);
                return agent ? Math.round(agent.success_rate * 100) : 0;
              });
              return (
                <div key={m.agent_id} className="trend-item">
                  <span className="trend-item-name">{m.agent_name}</span>
                  <TrendLine data={trend} />
                  <span className="trend-item-value">{(m.success_rate * 100).toFixed(1)}%</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};