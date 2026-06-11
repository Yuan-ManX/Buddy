import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { Agent, RAGDocument, RAGSearchResult, RAGStats } from '../types';

interface Props {
  agent: Agent;
}

export const KnowledgeBasePanel: React.FC<Props> = ({ agent }) => {
  const [documents, setDocuments] = useState<RAGDocument[]>([]);
  const [stats, setStats] = useState<RAGStats | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<RAGSearchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showIngest, setShowIngest] = useState(false);
  const [ingestForm, setIngestForm] = useState({
    content: '',
    title: '',
    source: 'direct',
  });
  const [activeView, setActiveView] = useState<'documents' | 'search'>('documents');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [docsRes, statsRes] = await Promise.all([
        api.rag.documents(agent.id),
        api.rag.stats(agent.id),
      ]);
      setDocuments(docsRes.documents);
      setStats(statsRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load knowledge base');
    } finally {
      setLoading(false);
    }
  }, [agent.id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) return;
    try {
      setSearching(true);
      setError(null);
      const res = await api.rag.search(agent.id, searchQuery.trim(), 10, true);
      setSearchResults(res.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setSearching(false);
    }
  }, [agent.id, searchQuery]);

  const handleIngest = useCallback(async () => {
    if (!ingestForm.content.trim()) return;
    try {
      setError(null);
      await api.rag.ingestText(agent.id, {
        content: ingestForm.content,
        title: ingestForm.title || `Document ${new Date().toLocaleDateString()}`,
        source: ingestForm.source,
      });
      setShowIngest(false);
      setIngestForm({ content: '', title: '', source: 'direct' });
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to ingest document');
    }
  }, [agent.id, ingestForm, loadData]);

  const handleDelete = useCallback(async (docId: string) => {
    try {
      await api.rag.deleteDocument(agent.id, docId);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document');
    }
  }, [agent.id, loadData]);

  if (loading) {
    return (
      <div className="panel">
        <div className="panel-header"><h2>Knowledge Base</h2></div>
        <div className="panel-body"><div className="loading-spinner">Loading...</div></div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Knowledge Base</h2>
        <div className="panel-actions">
          <button
            className={`btn-sm ${activeView === 'documents' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveView('documents')}
          >
            Documents ({stats?.document_count || 0})
          </button>
          <button
            className={`btn-sm ${activeView === 'search' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveView('search')}
          >
            Search
          </button>
          <button className="btn-sm btn-primary" onClick={() => setShowIngest(true)}>
            + Ingest
          </button>
        </div>
      </div>

      {stats && (
        <div className="kb-stats">
          <div className="kb-stat-item">
            <span className="kb-stat-value">{stats.document_count}</span>
            <span className="kb-stat-label">Documents</span>
          </div>
          <div className="kb-stat-item">
            <span className="kb-stat-value">{stats.chunk_count}</span>
            <span className="kb-stat-label">Chunks</span>
          </div>
          <div className="kb-stat-item">
            <span className="kb-stat-value">{stats.embedded_chunks}/{stats.chunk_count}</span>
            <span className="kb-stat-label">Embedded</span>
          </div>
          <div className="kb-stat-item">
            <span className="kb-stat-value">{(stats.total_tokens / 1000).toFixed(1)}k</span>
            <span className="kb-stat-label">Tokens</span>
          </div>
        </div>
      )}

      {error && (
        <div className="panel-error">
          <span>{error}</span>
          <button onClick={() => setError(null)}>x</button>
        </div>
      )}

      {showIngest && (
        <div className="modal-overlay" onClick={() => setShowIngest(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Ingest Document</h3>
            <div className="form-group">
              <label>Title</label>
              <input
                type="text"
                placeholder="Document title"
                value={ingestForm.title}
                onChange={(e) => setIngestForm({ ...ingestForm, title: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Content</label>
              <textarea
                placeholder="Paste document content here..."
                value={ingestForm.content}
                onChange={(e) => setIngestForm({ ...ingestForm, content: e.target.value })}
                rows={8}
              />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowIngest(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleIngest}>Ingest</button>
            </div>
          </div>
        </div>
      )}

      {activeView === 'documents' && (
        <div className="panel-body">
          {documents.length === 0 ? (
            <div className="empty-state">
              <p>No documents in knowledge base.</p>
              <p className="text-muted">Click "+ Ingest" to add documents for RAG-powered responses.</p>
            </div>
          ) : (
            <div className="kb-doc-list">
              {documents.map((doc) => (
                <div key={doc.id} className="kb-doc-card">
                  <div className="kb-doc-header">
                    <strong>{doc.title}</strong>
                    <button
                      className="btn-sm btn-danger"
                      onClick={() => handleDelete(doc.id)}
                      title="Delete document"
                    >
                      x
                    </button>
                  </div>
                  <div className="kb-doc-meta">
                    <span>{doc.chunk_count} chunks</span>
                    <span>{doc.total_tokens} tokens</span>
                    <span className="text-muted">{doc.source}</span>
                    <span className="text-muted">{new Date(doc.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeView === 'search' && (
        <div className="panel-body">
          <div className="kb-search-bar">
            <input
              type="text"
              placeholder="Search knowledge base..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
            <button className="btn-primary btn-sm" onClick={handleSearch} disabled={searching}>
              {searching ? 'Searching...' : 'Search'}
            </button>
          </div>

          {searchResults.length > 0 && (
            <div className="kb-search-results">
              {searchResults.map((r, i) => (
                <div key={r.chunk_id || i} className="kb-search-result">
                  <div className="kb-result-header">
                    <span className="kb-result-similarity">
                      {(r.similarity * 100).toFixed(0)}% match
                    </span>
                    <span className="text-muted">{r.title}</span>
                    {r.source && <span className="text-muted">{r.source}</span>}
                  </div>
                  <p className="kb-result-content">{r.content}</p>
                </div>
              ))}
            </div>
          )}

          {searchQuery && !searching && searchResults.length === 0 && (
            <div className="empty-state">
              <p>No results found for "{searchQuery}".</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};