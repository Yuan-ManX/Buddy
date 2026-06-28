import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#e11d48',
  secondary: '#fda4af',
  bg: '#fff1f2',
  border: '#fecdd3',
  accent: '#ffe4e6',
  text: '#881337',
};

const TRIGGER_TYPES = ['manual', 'scheduled', 'event', 'webhook', 'condition', 'chain'];
const NODE_TYPES = ['trigger', 'action', 'condition', 'transform', 'agent', 'tool', 'delay', 'parallel', 'merge', 'output'];

interface WorkflowComposerStats {
  total_workflows: number;
  total_executions: number;
  total_nodes: number;
  total_edges: number;
  recent_executions: number;
}

export const WorkflowComposerPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<WorkflowComposerStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'create' | 'nodes' | 'execute' | 'view'>('overview');

  // Create workflow form
  const [workflowForm, setWorkflowForm] = useState({
    name: '', description: '', trigger_type: 'manual', tags: '',
  });

  // Add node form
  const [nodeForm, setNodeForm] = useState({
    workflow_id: '', node_type: 'action', label: '', description: '', position_x: '', position_y: '',
  });

  // Add edge form
  const [edgeForm, setEdgeForm] = useState({
    workflow_id: '', source_id: '', target_id: '', condition: '', label: '',
  });

  // Execute form
  const [executeForm, setExecuteForm] = useState({
    workflow_id: '', input_data: '{}',
  });

  // View forms
  const [viewWorkflowId, setViewWorkflowId] = useState('');
  const [viewExecutionId, setViewExecutionId] = useState('');
  const [viewResult, setViewResult] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.workflowComposer.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load workflow composer data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreateWorkflow = async () => {
    if (!workflowForm.name.trim()) return;
    try {
      await api.workflowComposer.createWorkflow({
        name: workflowForm.name.trim(),
        description: workflowForm.description || undefined,
        trigger_type: workflowForm.trigger_type,
        tags: workflowForm.tags ? workflowForm.tags.split(',').map((s: string) => s.trim()) : undefined,
      });
      toast.success(`Workflow "${workflowForm.name}" created`);
      setWorkflowForm({ name: '', description: '', trigger_type: 'manual', tags: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddNode = async () => {
    if (!nodeForm.workflow_id.trim() || !nodeForm.label.trim()) return;
    try {
      await api.workflowComposer.addNode({
        workflow_id: nodeForm.workflow_id.trim(),
        node_type: nodeForm.node_type,
        label: nodeForm.label.trim(),
        description: nodeForm.description || undefined,
        position_x: nodeForm.position_x ? Number(nodeForm.position_x) : undefined,
        position_y: nodeForm.position_y ? Number(nodeForm.position_y) : undefined,
      });
      toast.success(`Node "${nodeForm.label}" added`);
      setNodeForm({ workflow_id: '', node_type: 'action', label: '', description: '', position_x: '', position_y: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddEdge = async () => {
    if (!edgeForm.workflow_id.trim() || !edgeForm.source_id.trim() || !edgeForm.target_id.trim()) return;
    try {
      await api.workflowComposer.addEdge({
        workflow_id: edgeForm.workflow_id.trim(),
        source_id: edgeForm.source_id.trim(),
        target_id: edgeForm.target_id.trim(),
        condition: edgeForm.condition || undefined,
        label: edgeForm.label || undefined,
      });
      toast.success('Edge added');
      setEdgeForm({ workflow_id: '', source_id: '', target_id: '', condition: '', label: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleExecute = async () => {
    if (!executeForm.workflow_id.trim()) return;
    try {
      let inputData;
      try { inputData = JSON.parse(executeForm.input_data); } catch { inputData = {}; }
      await api.workflowComposer.execute({
        workflow_id: executeForm.workflow_id.trim(),
        input_data: inputData,
      });
      toast.success('Workflow executed');
      setExecuteForm({ workflow_id: '', input_data: '{}' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleGetWorkflow = async () => {
    if (!viewWorkflowId.trim()) return;
    try {
      const result = await api.workflowComposer.getWorkflow(viewWorkflowId.trim());
      setViewResult({ type: 'workflow', data: result });
      toast.success('Workflow loaded');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleGetExecution = async () => {
    if (!viewExecutionId.trim()) return;
    try {
      const result = await api.workflowComposer.getExecution(viewExecutionId.trim());
      setViewResult({ type: 'execution', data: result });
      toast.success('Execution loaded');
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>⚡ Workflow Composer</h2>
          <p className="panel-subtitle">Visual workflow design and automation orchestration</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading workflow composer...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>⚡ Workflow Composer</h2>
        <p className="panel-subtitle">Visual workflow design and automation orchestration</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_workflows}</span><span className="stat-label">Total Workflows</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_executions}</span><span className="stat-label">Total Executions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_nodes}</span><span className="stat-label">Total Nodes</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_edges}</span><span className="stat-label">Total Edges</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: '#3b82f6' }}>{stats.recent_executions}</span><span className="stat-label">Recent Executions</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'create', 'nodes', 'execute', 'view'] as const).map(s => (
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
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Workflow Composer Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Workflows</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_workflows}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Executions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_executions}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Nodes</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_nodes}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Edges</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_edges}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Recent Executions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#3b82f6' }}>{stats.recent_executions}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create */}
      {activeSection === 'create' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create Workflow</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Name *</label>
              <input
                type="text"
                value={workflowForm.name}
                onChange={e => setWorkflowForm(f => ({ ...f, name: e.target.value }))}
                placeholder="e.g., Data Processing Pipeline"
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={3}
                value={workflowForm.description}
                onChange={e => setWorkflowForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe what this workflow does..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Trigger Type</label>
                <select value={workflowForm.trigger_type} onChange={e => setWorkflowForm(f => ({ ...f, trigger_type: e.target.value }))}>
                  {TRIGGER_TYPES.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Tags (comma-separated)</label>
                <input
                  type="text"
                  value={workflowForm.tags}
                  onChange={e => setWorkflowForm(f => ({ ...f, tags: e.target.value }))}
                  placeholder="e.g., data, etl, production"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleCreateWorkflow}
              disabled={!workflowForm.name.trim()}
            >
              Create Workflow
            </button>
          </div>
        </div>
      )}

      {/* Nodes */}
      {activeSection === 'nodes' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Add Node</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Workflow ID *</label>
              <input
                type="text"
                value={nodeForm.workflow_id}
                onChange={e => setNodeForm(f => ({ ...f, workflow_id: e.target.value }))}
                placeholder="Workflow ID"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Node Type</label>
                <select value={nodeForm.node_type} onChange={e => setNodeForm(f => ({ ...f, node_type: e.target.value }))}>
                  {NODE_TYPES.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Label *</label>
                <input
                  type="text"
                  value={nodeForm.label}
                  onChange={e => setNodeForm(f => ({ ...f, label: e.target.value }))}
                  placeholder="e.g., Fetch User Data"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Description</label>
              <input
                type="text"
                value={nodeForm.description}
                onChange={e => setNodeForm(f => ({ ...f, description: e.target.value }))}
                placeholder="What does this node do?"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Position X</label>
                <input
                  type="number"
                  value={nodeForm.position_x}
                  onChange={e => setNodeForm(f => ({ ...f, position_x: e.target.value }))}
                  placeholder="X coordinate"
                />
              </div>
              <div className="form-group">
                <label>Position Y</label>
                <input
                  type="number"
                  value={nodeForm.position_y}
                  onChange={e => setNodeForm(f => ({ ...f, position_y: e.target.value }))}
                  placeholder="Y coordinate"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleAddNode}
              disabled={!nodeForm.workflow_id.trim() || !nodeForm.label.trim()}
            >
              Add Node
            </button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 24 }}>Add Edge</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Workflow ID *</label>
              <input
                type="text"
                value={edgeForm.workflow_id}
                onChange={e => setEdgeForm(f => ({ ...f, workflow_id: e.target.value }))}
                placeholder="Workflow ID"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Source Node ID *</label>
                <input
                  type="text"
                  value={edgeForm.source_id}
                  onChange={e => setEdgeForm(f => ({ ...f, source_id: e.target.value }))}
                  placeholder="Source node ID"
                />
              </div>
              <div className="form-group">
                <label>Target Node ID *</label>
                <input
                  type="text"
                  value={edgeForm.target_id}
                  onChange={e => setEdgeForm(f => ({ ...f, target_id: e.target.value }))}
                  placeholder="Target node ID"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Condition</label>
                <input
                  type="text"
                  value={edgeForm.condition}
                  onChange={e => setEdgeForm(f => ({ ...f, condition: e.target.value }))}
                  placeholder="e.g., success, failure"
                />
              </div>
              <div className="form-group">
                <label>Label</label>
                <input
                  type="text"
                  value={edgeForm.label}
                  onChange={e => setEdgeForm(f => ({ ...f, label: e.target.value }))}
                  placeholder="Edge label"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleAddEdge}
              disabled={!edgeForm.workflow_id.trim() || !edgeForm.source_id.trim() || !edgeForm.target_id.trim()}
            >
              Add Edge
            </button>
          </div>
        </div>
      )}

      {/* Execute */}
      {activeSection === 'execute' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Execute Workflow</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Workflow ID *</label>
              <input
                type="text"
                value={executeForm.workflow_id}
                onChange={e => setExecuteForm(f => ({ ...f, workflow_id: e.target.value }))}
                placeholder="Enter workflow ID"
              />
            </div>
            <div className="form-group">
              <label>Input Data (JSON)</label>
              <textarea
                rows={4}
                value={executeForm.input_data}
                onChange={e => setExecuteForm(f => ({ ...f, input_data: e.target.value }))}
                placeholder='{"key": "value"}'
                style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: '#22c55e' }}
              onClick={handleExecute}
              disabled={!executeForm.workflow_id.trim()}
            >
              Execute Workflow
            </button>
          </div>
        </div>
      )}

      {/* View */}
      {activeSection === 'view' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Get Workflow</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Workflow ID *</label>
              <input
                type="text"
                value={viewWorkflowId}
                onChange={e => setViewWorkflowId(e.target.value)}
                placeholder="Enter workflow ID"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleGetWorkflow}
              disabled={!viewWorkflowId.trim()}
            >
              Get Workflow
            </button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 24 }}>Get Execution</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Execution ID *</label>
              <input
                type="text"
                value={viewExecutionId}
                onChange={e => setViewExecutionId(e.target.value)}
                placeholder="Enter execution ID"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleGetExecution}
              disabled={!viewExecutionId.trim()}
            >
              Get Execution
            </button>
          </div>

          {viewResult && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginTop: 16 }}>
              <h4 style={{ color: themeColors.text }}>{viewResult.type === 'workflow' ? 'Workflow' : 'Execution'} Data</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(viewResult.data, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default WorkflowComposerPanel;