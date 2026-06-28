import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#d97706',
  secondary: '#fcd34d',
  bg: '#fffbeb',
  border: '#fde68a',
  accent: '#fef3c7',
  text: '#78350f',
};

const LANGUAGES = ['python', 'javascript', 'typescript', 'go', 'rust', 'java', 'kotlin', 'swift', 'sql', 'html', 'css', 'shell'];
const TEST_RESULTS = ['pass', 'fail', 'pending', 'skipped'];

interface CodeSynthesisStats {
  total_projects: number;
  total_components: number;
  active_projects: number;
  completed_projects: number;
}

export const CodeSynthesisPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<CodeSynthesisStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'project' | 'component' | 'test' | 'view'>('overview');

  // Create project form
  const [projectForm, setProjectForm] = useState({
    name: '', specification: '', language: 'python',
  });

  // Plan architecture form
  const [planForm, setPlanForm] = useState({
    project_id: '', components: '', data_flow: '', entry_point: '', patterns: '', rationale: '',
  });

  // Generate component form
  const [componentForm, setComponentForm] = useState({
    project_id: '', name: '', code: '', description: '', dependencies: '', test_code: '',
  });

  // Test form
  const [testForm, setTestForm] = useState({
    project_id: '', component_id: '', test_result: 'pass', output: '',
  });

  // Refine form
  const [refineForm, setRefineForm] = useState({
    project_id: '', component_id: '', improved_code: '', description: '',
  });

  // Finalize / View forms
  const [finalizeProjectId, setFinalizeProjectId] = useState('');
  const [viewProjectId, setViewProjectId] = useState('');
  const [viewComponentProjectId, setViewComponentProjectId] = useState('');
  const [viewComponentId, setViewComponentId] = useState('');
  const [viewResult, setViewResult] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.codeSynthesis.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load code synthesis data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreateProject = async () => {
    if (!projectForm.name.trim() || !projectForm.specification.trim()) return;
    try {
      await api.codeSynthesis.createProject({
        name: projectForm.name.trim(),
        specification: projectForm.specification.trim(),
        language: projectForm.language,
      });
      toast.success(`Project "${projectForm.name}" created`);
      setProjectForm({ name: '', specification: '', language: 'python' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePlanArchitecture = async () => {
    if (!planForm.project_id.trim()) return;
    try {
      await api.codeSynthesis.planArchitecture({
        project_id: planForm.project_id.trim(),
        components: planForm.components ? planForm.components.split(',').map((s: string) => s.trim()) : undefined,
        data_flow: planForm.data_flow || undefined,
        entry_point: planForm.entry_point || undefined,
        patterns: planForm.patterns ? planForm.patterns.split(',').map((s: string) => s.trim()) : undefined,
        rationale: planForm.rationale || undefined,
      });
      toast.success('Architecture planned');
      setPlanForm({ project_id: '', components: '', data_flow: '', entry_point: '', patterns: '', rationale: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleGenerateComponent = async () => {
    if (!componentForm.project_id.trim() || !componentForm.name.trim() || !componentForm.code.trim()) return;
    try {
      await api.codeSynthesis.generateComponent({
        project_id: componentForm.project_id.trim(),
        name: componentForm.name.trim(),
        code: componentForm.code.trim(),
        description: componentForm.description || undefined,
        dependencies: componentForm.dependencies ? componentForm.dependencies.split(',').map((s: string) => s.trim()) : undefined,
        test_code: componentForm.test_code || undefined,
      });
      toast.success(`Component "${componentForm.name}" generated`);
      setComponentForm({ project_id: '', name: '', code: '', description: '', dependencies: '', test_code: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTest = async () => {
    if (!testForm.project_id.trim() || !testForm.component_id.trim()) return;
    try {
      await api.codeSynthesis.test({
        project_id: testForm.project_id.trim(),
        component_id: testForm.component_id.trim(),
        test_result: testForm.test_result,
        output: testForm.output || undefined,
      });
      toast.success('Test result recorded');
      setTestForm({ project_id: '', component_id: '', test_result: 'pass', output: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRefine = async () => {
    if (!refineForm.project_id.trim() || !refineForm.component_id.trim() || !refineForm.improved_code.trim()) return;
    try {
      await api.codeSynthesis.refine({
        project_id: refineForm.project_id.trim(),
        component_id: refineForm.component_id.trim(),
        improved_code: refineForm.improved_code.trim(),
        description: refineForm.description || undefined,
      });
      toast.success('Component refined');
      setRefineForm({ project_id: '', component_id: '', improved_code: '', description: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleFinalize = async () => {
    if (!finalizeProjectId.trim()) return;
    try {
      await api.codeSynthesis.finalize(finalizeProjectId.trim());
      toast.success('Project finalized');
      setFinalizeProjectId('');
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleGetProject = async () => {
    if (!viewProjectId.trim()) return;
    try {
      const result = await api.codeSynthesis.getProject(viewProjectId.trim());
      setViewResult({ type: 'project', data: result });
      toast.success('Project loaded');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleGetComponent = async () => {
    if (!viewComponentProjectId.trim() || !viewComponentId.trim()) return;
    try {
      const result = await api.codeSynthesis.getComponent(viewComponentProjectId.trim(), viewComponentId.trim());
      setViewResult({ type: 'component', data: result });
      toast.success('Component loaded');
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>💻 Code Synthesis</h2>
          <p className="panel-subtitle">Autonomous code generation pipeline from natural language</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading code synthesis...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>💻 Code Synthesis</h2>
        <p className="panel-subtitle">Autonomous code generation pipeline from natural language</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_projects}</span><span className="stat-label">Total Projects</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_components}</span><span className="stat-label">Total Components</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: '#22c55e' }}>{stats.active_projects}</span><span className="stat-label">Active</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: '#8b5cf6' }}>{stats.completed_projects}</span><span className="stat-label">Completed</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'project', 'component', 'test', 'view'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Code Synthesis Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Projects</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_projects}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Components</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_components}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Projects</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#22c55e' }}>{stats.active_projects}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Completed</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#8b5cf6' }}>{stats.completed_projects}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Project */}
      {activeSection === 'project' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create Project</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Name *</label>
              <input
                type="text"
                value={projectForm.name}
                onChange={e => setProjectForm(f => ({ ...f, name: e.target.value }))}
                placeholder="e.g., REST API Service"
              />
            </div>
            <div className="form-group">
              <label>Specification *</label>
              <textarea
                rows={4}
                value={projectForm.specification}
                onChange={e => setProjectForm(f => ({ ...f, specification: e.target.value }))}
                placeholder="Describe the project requirements in natural language..."
              />
            </div>
            <div className="form-group">
              <label>Language</label>
              <select value={projectForm.language} onChange={e => setProjectForm(f => ({ ...f, language: e.target.value }))}>
                {LANGUAGES.map(l => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleCreateProject}
              disabled={!projectForm.name.trim() || !projectForm.specification.trim()}
            >
              Create Project
            </button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 24 }}>Plan Architecture</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Project ID *</label>
              <input
                type="text"
                value={planForm.project_id}
                onChange={e => setPlanForm(f => ({ ...f, project_id: e.target.value }))}
                placeholder="Project ID"
              />
            </div>
            <div className="form-group">
              <label>Components (comma-separated)</label>
              <input
                type="text"
                value={planForm.components}
                onChange={e => setPlanForm(f => ({ ...f, components: e.target.value }))}
                placeholder="e.g., auth_service, user_api, database_layer"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Data Flow</label>
                <input
                  type="text"
                  value={planForm.data_flow}
                  onChange={e => setPlanForm(f => ({ ...f, data_flow: e.target.value }))}
                  placeholder="How data flows through the system"
                />
              </div>
              <div className="form-group">
                <label>Entry Point</label>
                <input
                  type="text"
                  value={planForm.entry_point}
                  onChange={e => setPlanForm(f => ({ ...f, entry_point: e.target.value }))}
                  placeholder="e.g., main.py, index.js"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Patterns (comma-separated)</label>
                <input
                  type="text"
                  value={planForm.patterns}
                  onChange={e => setPlanForm(f => ({ ...f, patterns: e.target.value }))}
                  placeholder="e.g., MVC, repository, factory"
                />
              </div>
              <div className="form-group">
                <label>Rationale</label>
                <input
                  type="text"
                  value={planForm.rationale}
                  onChange={e => setPlanForm(f => ({ ...f, rationale: e.target.value }))}
                  placeholder="Why this architecture?"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handlePlanArchitecture}
              disabled={!planForm.project_id.trim()}
            >
              Plan Architecture
            </button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 24 }}>Finalize Project</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Project ID *</label>
              <input
                type="text"
                value={finalizeProjectId}
                onChange={e => setFinalizeProjectId(e.target.value)}
                placeholder="Enter project ID to finalize"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: '#22c55e' }}
              onClick={handleFinalize}
              disabled={!finalizeProjectId.trim()}
            >
              Finalize Project
            </button>
          </div>
        </div>
      )}

      {/* Component */}
      {activeSection === 'component' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Generate Component</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Project ID *</label>
                <input
                  type="text"
                  value={componentForm.project_id}
                  onChange={e => setComponentForm(f => ({ ...f, project_id: e.target.value }))}
                  placeholder="Project ID"
                />
              </div>
              <div className="form-group">
                <label>Name *</label>
                <input
                  type="text"
                  value={componentForm.name}
                  onChange={e => setComponentForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="e.g., UserController"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Description</label>
              <input
                type="text"
                value={componentForm.description}
                onChange={e => setComponentForm(f => ({ ...f, description: e.target.value }))}
                placeholder="What does this component do?"
              />
            </div>
            <div className="form-group">
              <label>Code *</label>
              <textarea
                rows={6}
                value={componentForm.code}
                onChange={e => setComponentForm(f => ({ ...f, code: e.target.value }))}
                placeholder="Paste or write the component code..."
                style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
              />
            </div>
            <div className="form-group">
              <label>Dependencies (comma-separated)</label>
              <input
                type="text"
                value={componentForm.dependencies}
                onChange={e => setComponentForm(f => ({ ...f, dependencies: e.target.value }))}
                placeholder="e.g., requests, flask, sqlalchemy"
              />
            </div>
            <div className="form-group">
              <label>Test Code</label>
              <textarea
                rows={4}
                value={componentForm.test_code}
                onChange={e => setComponentForm(f => ({ ...f, test_code: e.target.value }))}
                placeholder="Paste or write test code..."
                style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleGenerateComponent}
              disabled={!componentForm.project_id.trim() || !componentForm.name.trim() || !componentForm.code.trim()}
            >
              Generate Component
            </button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 24 }}>Refine Component</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Project ID *</label>
                <input
                  type="text"
                  value={refineForm.project_id}
                  onChange={e => setRefineForm(f => ({ ...f, project_id: e.target.value }))}
                  placeholder="Project ID"
                />
              </div>
              <div className="form-group">
                <label>Component ID *</label>
                <input
                  type="text"
                  value={refineForm.component_id}
                  onChange={e => setRefineForm(f => ({ ...f, component_id: e.target.value }))}
                  placeholder="Component ID"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Improved Code *</label>
              <textarea
                rows={6}
                value={refineForm.improved_code}
                onChange={e => setRefineForm(f => ({ ...f, improved_code: e.target.value }))}
                placeholder="Paste the improved version of the code..."
                style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <input
                type="text"
                value={refineForm.description}
                onChange={e => setRefineForm(f => ({ ...f, description: e.target.value }))}
                placeholder="What was improved?"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleRefine}
              disabled={!refineForm.project_id.trim() || !refineForm.component_id.trim() || !refineForm.improved_code.trim()}
            >
              Refine Component
            </button>
          </div>
        </div>
      )}

      {/* Test */}
      {activeSection === 'test' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Record Test Result</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Project ID *</label>
                <input
                  type="text"
                  value={testForm.project_id}
                  onChange={e => setTestForm(f => ({ ...f, project_id: e.target.value }))}
                  placeholder="Project ID"
                />
              </div>
              <div className="form-group">
                <label>Component ID *</label>
                <input
                  type="text"
                  value={testForm.component_id}
                  onChange={e => setTestForm(f => ({ ...f, component_id: e.target.value }))}
                  placeholder="Component ID"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Test Result</label>
              <select value={testForm.test_result} onChange={e => setTestForm(f => ({ ...f, test_result: e.target.value }))}>
                {TEST_RESULTS.map(r => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Output</label>
              <textarea
                rows={3}
                value={testForm.output}
                onChange={e => setTestForm(f => ({ ...f, output: e.target.value }))}
                placeholder="Test execution output..."
                style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleTest}
              disabled={!testForm.project_id.trim() || !testForm.component_id.trim()}
            >
              Record Test Result
            </button>
          </div>
        </div>
      )}

      {/* View */}
      {activeSection === 'view' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Get Project</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Project ID *</label>
              <input
                type="text"
                value={viewProjectId}
                onChange={e => setViewProjectId(e.target.value)}
                placeholder="Enter project ID"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleGetProject}
              disabled={!viewProjectId.trim()}
            >
              Get Project
            </button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 24 }}>Get Component</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Project ID *</label>
                <input
                  type="text"
                  value={viewComponentProjectId}
                  onChange={e => setViewComponentProjectId(e.target.value)}
                  placeholder="Project ID"
                />
              </div>
              <div className="form-group">
                <label>Component ID *</label>
                <input
                  type="text"
                  value={viewComponentId}
                  onChange={e => setViewComponentId(e.target.value)}
                  placeholder="Component ID"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleGetComponent}
              disabled={!viewComponentProjectId.trim() || !viewComponentId.trim()}
            >
              Get Component
            </button>
          </div>

          {viewResult && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginTop: 16 }}>
              <h4 style={{ color: themeColors.text }}>{viewResult.type === 'project' ? 'Project' : 'Component'} Data</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(viewResult.data, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CodeSynthesisPanel;