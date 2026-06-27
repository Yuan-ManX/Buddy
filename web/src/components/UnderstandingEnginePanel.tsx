import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#0d9488',
  secondary: '#5eead4',
  bg: '#f0fdfa',
  border: '#99f6e4',
  accent: '#ccfbf1',
  text: '#134e4a',
};

export const UnderstandingEnginePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'process' | 'detect' | 'results'>('overview');

  const [processForm, setProcessForm] = useState({
    content: '', modality: '', processing_mode: 'direct',
  });
  const [detectContent, setDetectContent] = useState('');
  const [detectResult, setDetectResult] = useState<any>(null);
  const [results, setResults] = useState<any[] | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.understandingEngine.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleProcess = async () => {
    if (!processForm.content.trim()) return;
    try {
      await api.understandingEngine.process({
        content: processForm.content,
        modality: processForm.modality || undefined,
        processing_mode: processForm.processing_mode,
      });
      toast.success('Content processed successfully');
      setProcessForm({ content: '', modality: '', processing_mode: 'direct' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDetect = async () => {
    if (!detectContent.trim()) return;
    try {
      const result = await api.understandingEngine.detect(detectContent);
      setDetectResult(result);
      toast.success('Modality detected');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleLoadResults = async () => {
    try {
      const r = await api.understandingEngine.results();
      setResults(r);
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🔍 Multi-Modal Understanding</h2>
          <p className="panel-subtitle">Cross-modal processing and understanding engine</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading understanding engine...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🔍 Multi-Modal Understanding</h2>
        <p className="panel-subtitle">Cross-modal processing and understanding engine</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_inputs ?? '-'}</span><span className="stat-label">Total Inputs</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_results ?? '-'}</span><span className="stat-label">Results</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_fusions ?? '-'}</span><span className="stat-label">Fusions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.avg_confidence?.toFixed?.(2) ?? '-'}</span><span className="stat-label">Avg Confidence</span></div></div>
        </div>
      )}

      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'process', 'detect', 'results'] as const).map(s => (
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

      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Understanding Engine Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              {stats.modality_distribution && Object.entries(stats.modality_distribution).map(([mod, count]: [string, any]) => (
                <div key={mod} style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                  <div style={{ fontWeight: 600, color: themeColors.text, textTransform: 'capitalize' }}>{mod}</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{count}</div>
                </div>
              ))}
            </div>
          </div>
          <div style={{ padding: 16, background: themeColors.accent, borderRadius: 8 }}>
            <h4 style={{ color: themeColors.text }}>Performance</h4>
            <div className="dashboard-stat-row">
              <span>Avg Processing Time</span>
              <strong style={{ color: themeColors.primary }}>{stats.avg_processing_ms ?? '-'}ms</strong>
            </div>
          </div>
        </div>
      )}

      {activeSection === 'process' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Process Content</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Content</label>
              <textarea rows={5} value={processForm.content} onChange={e => setProcessForm(f => ({ ...f, content: e.target.value }))}
                placeholder="Enter content to process..." />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Modality (auto-detect if empty)</label>
                <select value={processForm.modality} onChange={e => setProcessForm(f => ({ ...f, modality: e.target.value }))}>
                  <option value="">Auto-detect</option>
                  {['text', 'code', 'structured_data', 'markdown', 'json', 'yaml', 'table', 'list', 'query', 'command'].map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Processing Mode</label>
                <select value={processForm.processing_mode} onChange={e => setProcessForm(f => ({ ...f, processing_mode: e.target.value }))}>
                  {['direct', 'parse', 'extract', 'transform', 'summarize', 'classify'].map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleProcess}>Process Content</button>
          </div>
        </div>
      )}

      {activeSection === 'detect' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Detect Modality</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Content to Analyze</label>
              <textarea rows={4} value={detectContent} onChange={e => setDetectContent(e.target.value)}
                placeholder="Paste content to auto-detect its modality and language..." />
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleDetect}>Detect</button>
          </div>
          {detectResult && (
            <div style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Detection Result</h4>
              <div className="dashboard-stat-row">
                <span>Modality</span>
                <strong style={{ color: themeColors.primary, textTransform: 'capitalize' }}>{detectResult.modality}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Detected Language</span>
                <strong style={{ color: themeColors.primary }}>{detectResult.detected_language || 'N/A'}</strong>
              </div>
            </div>
          )}
        </div>
      )}

      {activeSection === 'results' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Recent Results</h3>
          <button className="btn-primary" style={{ background: themeColors.primary, marginBottom: 16 }} onClick={handleLoadResults}>Load Results</button>
          {results && (
            <div>
              {results.length === 0 ? (
                <div className="panel-empty">No results yet</div>
              ) : (
                <div className="forge-skill-list">
                  {results.map((r: any, idx: number) => (
                    <div key={r.result_id || idx} className="forge-skill-card" style={{ borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div className="forge-skill-header">
                        <div className="forge-skill-name" style={{ color: themeColors.text }}>
                          [{r.modality}] {r.processing_mode}
                        </div>
                        <span className="dashboard-badge" style={{ background: themeColors.primary, color: '#fff' }}>
                          {r.confidence?.toFixed?.(2) ?? '-'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.85rem', color: themeColors.text, marginTop: 4 }}>
                        {r.understanding?.substring?.(0, 200) ?? '-'}
                      </div>
                      {r.extracted_keywords && r.extracted_keywords.length > 0 && (
                        <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                          {r.extracted_keywords.map((kw: string, ki: number) => (
                            <span key={ki} style={{ padding: '2px 8px', background: themeColors.accent, borderRadius: 12, fontSize: '0.75rem', color: themeColors.text }}>{kw}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default UnderstandingEnginePanel;