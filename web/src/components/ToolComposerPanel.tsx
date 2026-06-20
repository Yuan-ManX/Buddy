import React, { useState, useEffect } from 'react';

interface PipelineInfo {
  pipeline_id: string;
  name: string;
  description: string;
  stages: number;
  executions: number;
  created_at: number;
}

interface StageInfo {
  stage_id: string;
  stage_name: string;
  stage_type: string;
  order: number;
  condition: string;
}

interface NodeInfo {
  node_id: string;
  tool_name: string;
  parameters: Record<string, unknown>;
  max_retries: number;
}

export const ToolComposerPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [pipelines, setPipelines] = useState<PipelineInfo[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [showStage, setShowStage] = useState(false);
  const [showNode, setShowNode] = useState(false);
  const [activePipelineId, setActivePipelineId] = useState('');
  const [activeStageId, setActiveStageId] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    execution_mode: 'async',
    tags: '',
  });
  const [stageForm, setStageForm] = useState({
    pipeline_id: '',
    stage_type: 'sequential',
    stage_name: '',
    condition: '',
  });
  const [nodeForm, setNodeForm] = useState({
    pipeline_id: '',
    stage_id: '',
    tool_name: '',
    parameters: '{}',
    output_key: '',
    max_retries: 2,
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchStats(); }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/tool-composer/stats');
      const data = await res.json();
      setStats(data);
      if (data.pipelines) setPipelines(data.pipelines);
    } catch (e) { console.error('Fetch stats failed:', e); }
  };

  const createPipeline = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/tool-composer/create-pipeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.name,
          description: formData.description,
          execution_mode: formData.execution_mode,
          tags: formData.tags.split(',').map(s => s.trim()).filter(Boolean),
        }),
      });
      const data = await res.json();
      setActivePipelineId(data.pipeline_id);
      setShowCreate(false);
      fetchStats();
    } catch (e) { console.error('Create pipeline failed:', e); }
    setLoading(false);
  };

  const addStage = async () => {
    setLoading(true);
    try {
      await fetch('/api/tool-composer/add-stage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(stageForm),
      });
      setShowStage(false);
      fetchStats();
    } catch (e) { console.error('Add stage failed:', e); }
    setLoading(false);
  };

  const addNode = async () => {
    setLoading(true);
    try {
      await fetch('/api/tool-composer/add-node', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...nodeForm,
          parameters: JSON.parse(nodeForm.parameters || '{}'),
        }),
      });
      setShowNode(false);
      fetchStats();
    } catch (e) { console.error('Add node failed:', e); }
    setLoading(false);
  };

  const executePipeline = async (pipelineId: string) => {
    setLoading(true);
    try {
      const res = await fetch('/api/tool-composer/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pipeline_id: pipelineId }),
      });
      const data = await res.json();
      alert(`Execution ${data.status}: ${data.execution_id}`);
      fetchStats();
    } catch (e) { console.error('Execute failed:', e); }
    setLoading(false);
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Tool Composer</h2>
          <p style={{ color: '#666', margin: '4px 0 0' }}>Dynamic tool pipeline composition with sequential/parallel stages and conditional branching</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}
        >
          + New Pipeline
        </button>
      </div>

      {/* Stats Overview */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12, marginBottom: 24 }}>
          {[
            { label: 'Total Pipelines', value: stats.total_pipelines ?? 0, color: '#2563eb' },
            { label: 'Total Executions', value: stats.total_executions ?? 0, color: '#7c3aed' },
            { label: 'Total Stages', value: stats.total_stages ?? 0, color: '#059669' },
            { label: 'Total Nodes', value: stats.total_nodes ?? 0, color: '#d97706' },
          ].map((s) => (
            <div key={s.label} style={{ background: '#fff', borderRadius: 12, padding: 16, border: `1px solid ${s.color}20`, textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: s.color }}>{s.value}</div>
              <div style={{ fontSize: 12, color: '#666' }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Create Pipeline Modal */}
      {showCreate && (
        <div style={{ background: '#fff', borderRadius: 12, padding: 20, marginBottom: 16, border: '1px solid #e5e7eb' }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Create Pipeline</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <input
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              placeholder="Pipeline name"
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            />
            <input
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
              placeholder="Description"
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            />
            <select
              value={formData.execution_mode}
              onChange={e => setFormData({ ...formData, execution_mode: e.target.value })}
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            >
              <option value="sequential">Sequential</option>
              <option value="parallel">Parallel</option>
              <option value="auto">Auto</option>
            </select>
            <input
              value={formData.tags}
              onChange={e => setFormData({ ...formData, tags: e.target.value })}
              placeholder="Tags (comma-separated)"
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={() => setShowCreate(false)} style={{ padding: '8px 16px', background: '#f3f4f6', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
              <button onClick={createPipeline} disabled={loading} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
                {loading ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Stage Modal */}
      {showStage && (
        <div style={{ background: '#fff', borderRadius: 12, padding: 20, marginBottom: 16, border: '1px solid #e5e7eb' }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Add Stage</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <input
              value={stageForm.pipeline_id}
              onChange={e => setStageForm({ ...stageForm, pipeline_id: e.target.value })}
              placeholder="Pipeline ID"
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            />
            <input
              value={stageForm.stage_name}
              onChange={e => setStageForm({ ...stageForm, stage_name: e.target.value })}
              placeholder="Stage name"
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            />
            <select
              value={stageForm.stage_type}
              onChange={e => setStageForm({ ...stageForm, stage_type: e.target.value })}
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            >
              <option value="sequential">Sequential</option>
              <option value="parallel">Parallel</option>
              <option value="conditional">Conditional</option>
            </select>
            <input
              value={stageForm.condition}
              onChange={e => setStageForm({ ...stageForm, condition: e.target.value })}
              placeholder="Condition (for conditional stages)"
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={() => setShowStage(false)} style={{ padding: '8px 16px', background: '#f3f4f6', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
              <button onClick={addStage} disabled={loading} style={{ padding: '8px 16px', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
                {loading ? 'Adding...' : 'Add Stage'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Node Modal */}
      {showNode && (
        <div style={{ background: '#fff', borderRadius: 12, padding: 20, marginBottom: 16, border: '1px solid #e5e7eb' }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Add Tool Node</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <input
              value={nodeForm.pipeline_id}
              onChange={e => setNodeForm({ ...nodeForm, pipeline_id: e.target.value })}
              placeholder="Pipeline ID"
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            />
            <input
              value={nodeForm.stage_id}
              onChange={e => setNodeForm({ ...nodeForm, stage_id: e.target.value })}
              placeholder="Stage ID"
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            />
            <input
              value={nodeForm.tool_name}
              onChange={e => setNodeForm({ ...nodeForm, tool_name: e.target.value })}
              placeholder="Tool name"
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            />
            <input
              value={nodeForm.parameters}
              onChange={e => setNodeForm({ ...nodeForm, parameters: e.target.value })}
              placeholder="Parameters (JSON)"
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            />
            <input
              value={nodeForm.output_key}
              onChange={e => setNodeForm({ ...nodeForm, output_key: e.target.value })}
              placeholder="Output key"
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={() => setShowNode(false)} style={{ padding: '8px 16px', background: '#f3f4f6', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
              <button onClick={addNode} disabled={loading} style={{ padding: '8px 16px', background: '#059669', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
                {loading ? 'Adding...' : 'Add Node'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Pipeline List */}
      <div style={{ background: '#fff', borderRadius: 12, padding: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Pipelines</h3>
        {pipelines.length === 0 ? (
          <p style={{ color: '#9ca3af', fontSize: 13 }}>No pipelines created yet. Create one to get started.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {pipelines.map((p) => (
              <div key={p.pipeline_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', borderRadius: 8, border: '1px solid #e5e7eb', background: activePipelineId === p.pipeline_id ? '#f0f9ff' : '#fafafa' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{p.name}</div>
                  <div style={{ fontSize: 11, color: '#9ca3af' }}>{p.description} | Stages: {p.stages} | Executions: {p.executions}</div>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button
                    onClick={() => { setActivePipelineId(p.pipeline_id); setStageForm({ ...stageForm, pipeline_id: p.pipeline_id }); setShowStage(true); }}
                    style={{ padding: '4px 10px', fontSize: 11, background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
                  >
                    + Stage
                  </button>
                  <button
                    onClick={() => { setActivePipelineId(p.pipeline_id); setNodeForm({ ...nodeForm, pipeline_id: p.pipeline_id }); setShowNode(true); }}
                    style={{ padding: '4px 10px', fontSize: 11, background: '#059669', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
                  >
                    + Node
                  </button>
                  <button
                    onClick={() => executePipeline(p.pipeline_id)}
                    disabled={loading}
                    style={{ padding: '4px 10px', fontSize: 11, background: '#d97706', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
                  >
                    Execute
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};