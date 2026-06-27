import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#b45309',
  secondary: '#d97706',
  bg: '#fffbeb',
  border: '#fcd34d',
  accent: '#fef3c7',
  text: '#78350f',
};

export const DocumentIntelligencePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'upload' | 'documents' | 'extract' | 'summarize' | 'search' | 'compare'>('overview');

  const [uploadForm, setUploadForm] = useState({ filename: '', format: 'text', content: '', tags: '' });
  const [documents, setDocuments] = useState<any[]>([]);
  const [extractForm, setExtractForm] = useState({ doc_id: '', extraction_type: 'entities' });
  const [extractResult, setExtractResult] = useState<any>(null);
  const [summarizeForm, setSummarizeForm] = useState({ doc_id: '', max_length: '200' });
  const [summarizeResult, setSummarizeResult] = useState<any>(null);
  const [searchForm, setSearchForm] = useState({ query: '', doc_ids: '', limit: '10' });
  const [searchResults, setSearchResults] = useState<any[] | null>(null);
  const [compareForm, setCompareForm] = useState({ doc_a_id: '', doc_b_id: '' });
  const [compareResult, setCompareResult] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, docs] = await Promise.all([
        api.documentIntelligence.stats(),
        api.documentIntelligence.list(),
      ]);
      setStats(s);
      setDocuments(docs.documents || docs.items || docs);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load document intelligence data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleUpload = async () => {
    if (!uploadForm.filename.trim() || !uploadForm.content.trim()) return;
    try {
      await api.documentIntelligence.upload({
        filename: uploadForm.filename,
        format: uploadForm.format,
        content: uploadForm.content,
        tags: uploadForm.tags ? uploadForm.tags.split(',').map(s => s.trim()) : undefined,
      });
      toast.success('Document uploaded');
      setUploadForm({ filename: '', format: 'text', content: '', tags: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleExtract = async () => {
    if (!extractForm.doc_id.trim()) return;
    try {
      const result = await api.documentIntelligence.extract({
        doc_id: extractForm.doc_id,
        extraction_type: extractForm.extraction_type || undefined,
      });
      setExtractResult(result);
      toast.success('Extraction completed');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSummarize = async () => {
    if (!summarizeForm.doc_id.trim()) return;
    try {
      const result = await api.documentIntelligence.summarize({
        doc_id: summarizeForm.doc_id,
        max_length: parseInt(summarizeForm.max_length) || undefined,
      });
      setSummarizeResult(result);
      toast.success('Summarization completed');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSearch = async () => {
    if (!searchForm.query.trim()) return;
    try {
      const results = await api.documentIntelligence.search({
        query: searchForm.query,
        doc_ids: searchForm.doc_ids ? searchForm.doc_ids.split(',').map(s => s.trim()) : undefined,
        limit: parseInt(searchForm.limit) || 10,
      });
      setSearchResults(results.results || results.items || results);
      toast.success('Search completed');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCompare = async () => {
    if (!compareForm.doc_a_id.trim() || !compareForm.doc_b_id.trim()) return;
    try {
      const result = await api.documentIntelligence.compare({
        doc_a_id: compareForm.doc_a_id,
        doc_b_id: compareForm.doc_b_id,
      });
      setCompareResult(result);
      toast.success('Comparison completed');
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>📄 Document Intelligence Engine</h2>
          <p className="panel-subtitle">Upload, extract, summarize, search, and compare documents intelligently</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading document intelligence...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>📄 Document Intelligence Engine</h2>
        <p className="panel-subtitle">Upload, extract, summarize, search, and compare documents intelligently</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_documents ?? stats.document_count ?? '-'}</span><span className="stat-label">Documents</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_extractions ?? stats.extraction_count ?? '-'}</span><span className="stat-label">Extractions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_summaries ?? stats.summary_count ?? '-'}</span><span className="stat-label">Summaries</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_searches ?? stats.search_count ?? '-'}</span><span className="stat-label">Searches</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'upload', 'documents', 'extract', 'summarize', 'search', 'compare'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
            style={activeSection === s ? { background: themeColors.primary, borderColor: themeColors.primary } : {}}
          >
            {s === 'documents' ? 'Docs List' : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
            {Object.entries(stats).filter(([k]) => !['by_format', 'by_tag', 'recent_documents'].includes(k)).map(([key, value]: [string, any]) => (
              <div key={key} style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontSize: '0.85rem', color: '#6b7280', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>
                  {typeof value === 'number' ? value : typeof value === 'object' ? JSON.stringify(value).slice(0, 40) : String(value)}
                </div>
              </div>
            ))}
          </div>
          {stats.by_format && Object.keys(stats.by_format).length > 0 && (
            <div style={{ marginTop: 20 }}>
              <h4 style={{ color: themeColors.text }}>By Format</h4>
              {Object.entries(stats.by_format).map(([fmt, count]: [string, any]) => (
                <div key={fmt} className="dashboard-stat-row">
                  <span style={{ fontWeight: 500 }}>{fmt}</span>
                  <strong style={{ color: themeColors.primary }}>{count}</strong>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Upload */}
      {activeSection === 'upload' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Upload Document</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Filename</label>
              <input type="text" value={uploadForm.filename}
                onChange={e => setUploadForm(f => ({ ...f, filename: e.target.value }))}
                placeholder="document.pdf" />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Format</label>
                <select value={uploadForm.format} onChange={e => setUploadForm(f => ({ ...f, format: e.target.value }))}>
                  {['text', 'pdf', 'markdown', 'html', 'json', 'csv'].map(f => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>
              <div className="form-group" style={{ flex: 2 }}>
                <label>Tags (comma-separated)</label>
                <input type="text" value={uploadForm.tags}
                  onChange={e => setUploadForm(f => ({ ...f, tags: e.target.value }))}
                  placeholder="important, reference, project-x" />
              </div>
            </div>
            <div className="form-group">
              <label>Content</label>
              <textarea
                rows={6}
                value={uploadForm.content}
                onChange={e => setUploadForm(f => ({ ...f, content: e.target.value }))}
                placeholder="Enter document content..."
              />
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleUpload}>Upload Document</button>
          </div>
        </div>
      )}

      {/* Documents List */}
      {activeSection === 'documents' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Documents ({documents.length})</h3>
          {documents.length === 0 ? (
            <div className="panel-empty">No documents uploaded yet. Go to the Upload tab to add one.</div>
          ) : (
            <div className="forge-skill-list">
              {documents.map((doc: any, idx: number) => (
                <div key={doc.id || doc.doc_id || idx} className="forge-skill-card" style={{ borderLeft: `4px solid ${themeColors.primary}` }}>
                  <div className="forge-skill-header">
                    <div className="forge-skill-name" style={{ color: themeColors.text }}>{doc.filename || doc.name || doc.title || `Document ${idx + 1}`}</div>
                    <span className="dashboard-badge" style={{ background: themeColors.primary, color: '#fff' }}>
                      {doc.format || 'text'}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>ID: {doc.id || doc.doc_id || idx}</div>
                    {doc.size && <div>Size: {doc.size}</div>}
                    {doc.created_at && <div>Created: {new Date(doc.created_at).toLocaleString()}</div>}
                    {doc.tags?.length > 0 && (
                      <div style={{ marginTop: 4 }}>
                        {doc.tags.map((tag: string) => (
                          <span key={tag} style={{ display: 'inline-block', padding: '2px 8px', margin: '2px', background: themeColors.accent, color: themeColors.text, borderRadius: 12, fontSize: '0.75rem' }}>{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Extract */}
      {activeSection === 'extract' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Extract Information</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group" style={{ flex: 2 }}>
                <label>Document ID</label>
                <select value={extractForm.doc_id} onChange={e => setExtractForm(f => ({ ...f, doc_id: e.target.value }))}>
                  <option value="">Select a document...</option>
                  {documents.map((doc: any, idx: number) => (
                    <option key={doc.id || doc.doc_id || idx} value={doc.id || doc.doc_id || idx}>{doc.filename || doc.name || `Doc ${idx + 1}`}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Extraction Type</label>
                <select value={extractForm.extraction_type} onChange={e => setExtractForm(f => ({ ...f, extraction_type: e.target.value }))}>
                  {['entities', 'keywords', 'topics', 'dates', 'custom'].map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleExtract}>Extract</button>
          </div>
          {extractResult && (
            <div style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Extraction Result</h4>
              <pre style={{ whiteSpace: 'pre-wrap', color: themeColors.text, background: '#fff', padding: 12, borderRadius: 6, marginTop: 8 }}>
                {typeof extractResult === 'string' ? extractResult : JSON.stringify(extractResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Summarize */}
      {activeSection === 'summarize' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Summarize Document</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group" style={{ flex: 2 }}>
                <label>Document ID</label>
                <select value={summarizeForm.doc_id} onChange={e => setSummarizeForm(f => ({ ...f, doc_id: e.target.value }))}>
                  <option value="">Select a document...</option>
                  {documents.map((doc: any, idx: number) => (
                    <option key={doc.id || doc.doc_id || idx} value={doc.id || doc.doc_id || idx}>{doc.filename || doc.name || `Doc ${idx + 1}`}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Max Length (chars)</label>
                <input type="number" value={summarizeForm.max_length}
                  onChange={e => setSummarizeForm(f => ({ ...f, max_length: e.target.value }))}
                  min="50" max="5000" />
              </div>
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleSummarize}>Summarize</button>
          </div>
          {summarizeResult && (
            <div style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Summary</h4>
              <pre style={{ whiteSpace: 'pre-wrap', color: themeColors.text, background: '#fff', padding: 12, borderRadius: 6, marginTop: 8 }}>
                {typeof summarizeResult === 'string' ? summarizeResult : JSON.stringify(summarizeResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Search */}
      {activeSection === 'search' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Search Documents</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Search Query</label>
              <input type="text" value={searchForm.query}
                onChange={e => setSearchForm(f => ({ ...f, query: e.target.value }))}
                placeholder="Search across documents..." />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Document IDs (comma-separated, optional)</label>
                <input type="text" value={searchForm.doc_ids}
                  onChange={e => setSearchForm(f => ({ ...f, doc_ids: e.target.value }))}
                  placeholder="doc1, doc2" />
              </div>
              <div className="form-group">
                <label>Limit</label>
                <input type="number" value={searchForm.limit}
                  onChange={e => setSearchForm(f => ({ ...f, limit: e.target.value }))}
                  min="1" max="100" />
              </div>
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleSearch}>Search</button>
          </div>
          {searchResults && (
            <div style={{ marginTop: 20 }}>
              <h4 style={{ color: themeColors.text }}>Search Results ({searchResults.length})</h4>
              {searchResults.length === 0 ? (
                <div className="panel-empty">No results found</div>
              ) : (
                <div className="forge-skill-list">
                  {searchResults.map((item: any, idx: number) => (
                    <div key={item.id || idx} className="forge-skill-card" style={{ borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div className="forge-skill-header">
                        <div className="forge-skill-name" style={{ color: themeColors.text }}>{item.title || item.filename || item.name}</div>
                        {item.score != null && (
                          <span className="dashboard-badge" style={{ background: themeColors.primary, color: '#fff' }}>
                            Score: {typeof item.score === 'number' ? item.score.toFixed(2) : item.score}
                          </span>
                        )}
                      </div>
                      <div className="forge-skill-meta">
                        <div>{item.content || item.snippet || item.text || JSON.stringify(item).slice(0, 200)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Compare */}
      {activeSection === 'compare' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Compare Documents</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Document A ID</label>
                <select value={compareForm.doc_a_id} onChange={e => setCompareForm(f => ({ ...f, doc_a_id: e.target.value }))}>
                  <option value="">Select...</option>
                  {documents.map((doc: any, idx: number) => (
                    <option key={doc.id || doc.doc_id || idx} value={doc.id || doc.doc_id || idx}>{doc.filename || doc.name || `Doc ${idx + 1}`}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Document B ID</label>
                <select value={compareForm.doc_b_id} onChange={e => setCompareForm(f => ({ ...f, doc_b_id: e.target.value }))}>
                  <option value="">Select...</option>
                  {documents.map((doc: any, idx: number) => (
                    <option key={doc.id || doc.doc_id || idx} value={doc.id || doc.doc_id || idx}>{doc.filename || doc.name || `Doc ${idx + 1}`}</option>
                  ))}
                </select>
              </div>
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleCompare}>Compare</button>
          </div>
          {compareResult && (
            <div style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Comparison Result</h4>
              <pre style={{ whiteSpace: 'pre-wrap', color: themeColors.text, background: '#fff', padding: 12, borderRadius: 6, marginTop: 8 }}>
                {typeof compareResult === 'string' ? compareResult : JSON.stringify(compareResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DocumentIntelligencePanel;