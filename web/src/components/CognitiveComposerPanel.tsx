// CognitiveComposerPanel: visualize cross-engine cognitive compositions.
//
// Lets the operator:
//   - Pick one of the built-in compositions (holistic / analytical / creative)
//   - Enter an agent ID and evaluate the composition
//   - See a radar chart of contributing engine weights
//   - See the fused score and regime with full JSON output
//
// All visuals are pure SVG — no chart library dependency.

import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

interface CompositionMeta {
  name: string;
  fusion_strategy: string;
  engine_count: number;
  description: string;
}

interface EvaluateResult {
  composition_name: string;
  agent_id: string;
  fusion_strategy: string;
  fused_score: number;
  fused_regime: string;
  contributing_engines: string[];
  engine_results: Record<string, any>;
  notes: string;
}

const BUILTIN_COMPOSITIONS = ['holistic', 'analytical', 'creative'];

export const CognitiveComposerPanel: React.FC = () => {
  const toast = useToast();
  const [compositions, setCompositions] = useState<CompositionMeta[]>([]);
  const [selected, setSelected] = useState<string>('holistic');
  const [agentId, setAgentId] = useState<string>('');
  const [result, setResult] = useState<EvaluateResult | null>(null);
  const [loading, setLoading] = useState(false);

  const loadCompositions = async () => {
    try {
      const res = await api.cognitiveComposer.listCompositions();
      setCompositions(res.compositions || []);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load compositions');
    }
  };

  useEffect(() => {
    loadCompositions();
  }, []);

  const handleEvaluate = async () => {
    if (!agentId.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    setLoading(true);
    try {
      const r = await api.cognitiveComposer.evaluate(agentId.trim(), selected);
      setResult(r);
      toast.success(`Evaluated ${r.composition_name}: score=${r.fused_score.toFixed(3)}, regime=${r.fused_regime}`);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Build radar chart data from engine_results. Each engine is one axis.
  const radarData = result
    ? Object.entries(result.engine_results)
        .map(([key, entry]: [string, any]) => ({
          label: key,
          score: typeof entry?.score === 'number' ? entry.score : 0,
        }))
        .filter(d => d.score > 0)
        .slice(0, 12)
    : [];

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>🎼 Cognitive Composer</h2>
        <p className="panel-subtitle">
          Fuse outputs across multiple cognitive engines into a single composition.
          Built-in: holistic, analytical, creative.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 24, marginTop: 16 }}>
        {/* Left: composition selector + agent input */}
        <div>
          <h3 style={{ marginBottom: 8 }}>Composition</h3>
          <select
            value={selected}
            onChange={e => setSelected(e.target.value)}
            style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: '1px solid #d1d5db' }}
          >
            {compositions.length === 0 && BUILTIN_COMPOSITIONS.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
            {compositions.map(c => (
              <option key={c.name} value={c.name}>
                {c.name} ({c.fusion_strategy})
              </option>
            ))}
          </select>

          {compositions.find(c => c.name === selected) && (
            <p style={{ fontSize: 12, color: '#6b7280', marginTop: 8 }}>
              {compositions.find(c => c.name === selected)?.description}
            </p>
          )}

          <h3 style={{ marginTop: 16, marginBottom: 8 }}>Agent ID</h3>
          <input
            type="text"
            value={agentId}
            onChange={e => setAgentId(e.target.value)}
            placeholder="agent-strategy-001"
            style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: '1px solid #d1d5db' }}
          />

          <button
            onClick={handleEvaluate}
            disabled={loading}
            style={{
              marginTop: 16,
              padding: '8px 16px',
              background: '#4f46e5',
              color: '#fff',
              border: 'none',
              borderRadius: 4,
              cursor: loading ? 'wait' : 'pointer',
              width: '100%',
            }}
          >
            {loading ? 'Evaluating...' : 'Evaluate Composition'}
          </button>

          {result && (
            <div style={{ marginTop: 16, padding: 12, background: '#f3f4f6', borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: '#6b7280' }}>Fused Score</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#4f46e5' }}>
                {result.fused_score.toFixed(3)}
              </div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 8 }}>Fused Regime</div>
              <div style={{ fontSize: 16, fontWeight: 600 }}>{result.fused_regime}</div>
              <div style={{ fontSize: 11, color: '#6b7280', marginTop: 8 }}>
                {result.contributing_engines.length} engines · {result.fusion_strategy}
              </div>
            </div>
          )}
        </div>

        {/* Right: radar chart + JSON output */}
        <div>
          <h3 style={{ marginBottom: 8 }}>Engine Contribution Radar</h3>
          {radarData.length < 3 ? (
            <div style={{
              width: '100%',
              height: 240,
              background: '#f9fafb',
              borderRadius: 4,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#9ca3af',
              fontSize: 12,
            }}>
              Evaluate a composition with at least 3 contributing engines to see the radar chart.
            </div>
          ) : (
            <RadarChart data={radarData} size={240} />
          )}

          {result && (
            <div style={{ marginTop: 16 }}>
              <h3 style={{ marginBottom: 8 }}>Raw Result JSON</h3>
              <pre style={{
                background: '#1f2937',
                color: '#e5e7eb',
                padding: 12,
                borderRadius: 4,
                fontSize: 11,
                overflow: 'auto',
                maxHeight: 200,
              }}>
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>

      {/* Compositions table */}
      <div style={{ marginTop: 24 }}>
        <h3 style={{ marginBottom: 8 }}>All Registered Compositions</h3>
        {compositions.length === 0 ? (
          <p style={{ color: '#6b7280', fontSize: 13 }}>No compositions loaded.</p>
        ) : (
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>
                <th style={{ padding: '4px 8px' }}>Name</th>
                <th style={{ padding: '4px 8px' }}>Strategy</th>
                <th style={{ padding: '4px 8px', textAlign: 'right' }}>Engines</th>
                <th style={{ padding: '4px 8px' }}>Description</th>
              </tr>
            </thead>
            <tbody>
              {compositions.map(c => (
                <tr key={c.name} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '4px 8px', fontWeight: 600 }}>{c.name}</td>
                  <td style={{ padding: '4px 8px', fontFamily: 'monospace' }}>{c.fusion_strategy}</td>
                  <td style={{ padding: '4px 8px', textAlign: 'right' }}>{c.engine_count}</td>
                  <td style={{ padding: '4px 8px', color: '#6b7280' }}>{c.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

// ── Pure-SVG radar chart ───────────────────────────────────────

const RadarChart: React.FC<{
  data: { label: string; score: number }[];
  size: number;
}> = ({ data, size }) => {
  const center = size / 2;
  const radius = size / 2 - 40;
  const angleStep = (2 * Math.PI) / data.length;

  // Concentric grid rings at 0.25, 0.5, 0.75, 1.0
  const rings = [0.25, 0.5, 0.75, 1.0];

  // Compute polygon points for the data
  const dataPoints = data.map((d, i) => {
    const angle = i * angleStep - Math.PI / 2;
    const r = d.score * radius;
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
      labelX: center + (radius + 12) * Math.cos(angle),
      labelY: center + (radius + 12) * Math.sin(angle),
      label: d.label,
      score: d.score,
    };
  });

  const polygonPath = dataPoints.map(p => `${p.x},${p.y}`).join(' ');

  return (
    <svg width={size} height={size} style={{ display: 'block', margin: '0 auto' }}>
      {/* Grid rings */}
      {rings.map(r => {
        const ringPoints = data.map((_, i) => {
          const angle = i * angleStep - Math.PI / 2;
          const x = center + r * radius * Math.cos(angle);
          const y = center + r * radius * Math.sin(angle);
          return `${x},${y}`;
        }).join(' ');
        return (
          <polygon
            key={r}
            points={ringPoints}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={1}
          />
        );
      })}

      {/* Spokes */}
      {dataPoints.map((p, i) => {
        const angle = i * angleStep - Math.PI / 2;
        const x = center + radius * Math.cos(angle);
        const y = center + radius * Math.sin(angle);
        return (
          <line
            key={i}
            x1={center}
            y1={center}
            x2={x}
            y2={y}
            stroke="#e5e7eb"
            strokeWidth={1}
          />
        );
      })}

      {/* Data polygon */}
      <polygon
        points={polygonPath}
        fill="rgba(79, 70, 229, 0.2)"
        stroke="#4f46e5"
        strokeWidth={2}
      />

      {/* Data point dots */}
      {dataPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3} fill="#4f46e5" />
      ))}

      {/* Labels */}
      {dataPoints.map((p, i) => (
        <text
          key={i}
          x={p.labelX}
          y={p.labelY}
          fontSize={9}
          fill="#374151"
          textAnchor="middle"
          dominantBaseline="middle"
        >
          {p.label}
        </text>
      ))}
    </svg>
  );
};
