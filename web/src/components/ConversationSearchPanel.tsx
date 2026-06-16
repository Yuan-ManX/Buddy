import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

interface SearchResult {
  conversation_id: string;
  role: string;
  content: string;
  summary: string;
  topics: string[];
  relevance_score: number;
  timestamp: string;
  conversation_title: string;
}

interface RecapResult {
  query: string;
  found: boolean;
  result_count?: number;
  summary?: string;
  key_decisions?: string[];
  action_items?: string[];
  relevance?: string;
  sources?: Array<{
    conversation_id: string;
    title: string;
    relevance: number;
    timestamp: string;
  }>;
  message?: string;
}

interface ConversationInfo {
  conversation_id: string;
  title: string;
  summary: string;
  topics: string[];
  entry_count: number;
  total_tokens: number;
  last_message_at: string;
  tags: string[];
}

export const ConversationSearchPanel: React.FC = () => {
  const [conversations, setConversations] = useState<ConversationInfo[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [recap, setRecap] = useState<RecapResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'browse' | 'search' | 'recap' | 'timeline'>('browse');
  const [daysBack, setDaysBack] = useState(30);

  const loadConversations = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.conversationSearch.list(30);
      setConversations(data.conversations || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load conversations');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    try {
      setLoading(true);
      setError(null);
      const data = await api.conversationSearch.search(searchQuery, 10);
      setSearchResults(data.results || []);
      setActiveSection('search');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRecap = async () => {
    if (!searchQuery.trim()) return;
    try {
      setLoading(true);
      setError(null);
      const data = await api.conversationSearch.recap(searchQuery, daysBack);
      setRecap(data);
      setActiveSection('recap');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Recap failed');
    } finally {
      setLoading(false);
    }
  };

  const handleTopicSearch = async (topic: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.conversationSearch.searchByTopic(topic, 10);
      setSearchResults(data.results || []);
      setActiveSection('search');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Topic search failed');
    } finally {
      setLoading(false);
    }
  };

  if (loading && conversations.length === 0) {
    return <div className="panel-loading">Loading conversation search...</div>;
  }

  return (
    <div className="conversation-search-panel">
      <div className="panel-header">
        <h2>Conversation Search</h2>
        <div className="panel-header-actions">
          <button
            className={`btn btn-sm ${activeSection === 'browse' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveSection('browse')}
          >
            Browse
          </button>
          <button
            className={`btn btn-sm ${activeSection === 'search' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveSection('search')}
          >
            Search
          </button>
          <button
            className={`btn btn-sm ${activeSection === 'recap' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveSection('recap')}
          >
            Recap
          </button>
        </div>
      </div>

      {error && <div className="panel-error">{error}</div>}

      {/* Search Bar */}
      <div className="search-bar">
        <input
          type="text"
          placeholder="Search past conversations..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
        />
        <button className="btn btn-primary" onClick={handleSearch}>Search</button>
        <button className="btn btn-secondary" onClick={handleRecap}>Generate Recap</button>
        <select value={daysBack} onChange={e => setDaysBack(Number(e.target.value))} style={{ width: 'auto' }}>
          <option value={7}>7 days</option>
          <option value={30}>30 days</option>
          <option value={90}>90 days</option>
        </select>
      </div>

      {/* Browse Section */}
      {activeSection === 'browse' && (
        <div className="conversation-list">
          {conversations.length === 0 ? (
            <div className="panel-empty">No conversations indexed yet. Conversations are auto-indexed as you chat.</div>
          ) : (
            conversations.map((conv) => (
              <div key={conv.conversation_id} className="conversation-card">
                <div className="conv-header">
                  <h4>{conv.title || 'Untitled Conversation'}</h4>
                  <span className="text-muted">
                    {new Date(conv.last_message_at).toLocaleDateString()}
                  </span>
                </div>
                <p className="conv-summary">{conv.summary}</p>
                <div className="conv-topics">
                  {conv.topics.slice(0, 5).map(topic => (
                    <button
                      key={topic}
                      className="tag tag-clickable"
                      onClick={() => handleTopicSearch(topic)}
                    >
                      {topic}
                    </button>
                  ))}
                </div>
                <div className="conv-meta">
                  <span>{conv.entry_count} messages</span>
                  <span>{conv.total_tokens.toLocaleString()} tokens</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Search Results */}
      {activeSection === 'search' && (
        <div className="search-results">
          {searchResults.length === 0 ? (
            <div className="panel-empty">Enter a search query above to find relevant past conversations.</div>
          ) : (
            <div>
              <div className="results-count">{searchResults.length} results found</div>
              {searchResults.map((result, idx) => (
                <div key={idx} className="search-result-card">
                  <div className="result-header">
                    <span className="relevance-badge">
                      {Math.round(result.relevance_score * 100)}% match
                    </span>
                    <span className="text-muted">{result.role}</span>
                    <span className="text-muted">
                      {new Date(result.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="result-content">{result.content}</p>
                  {result.topics.length > 0 && (
                    <div className="result-topics">
                      {result.topics.slice(0, 3).map(topic => (
                        <span key={topic} className="tag">{topic}</span>
                      ))}
                    </div>
                  )}
                  {result.conversation_title && (
                    <div className="result-source">
                      from: {result.conversation_title}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Recap Section */}
      {activeSection === 'recap' && (
        <div className="recap-section">
          {recap ? (
            recap.found ? (
              <div className="recap-result">
                <div className="recap-header">
                  <h3>Recap: {recap.query}</h3>
                  <span className="text-muted">{recap.result_count} conversations found</span>
                </div>

                <div className="recap-summary">
                  <h4>Summary</h4>
                  <p>{recap.summary}</p>
                </div>

                {recap.key_decisions && recap.key_decisions.length > 0 && (
                  <div className="recap-decisions">
                    <h4>Key Decisions</h4>
                    <ul>
                      {recap.key_decisions.map((d, i) => (
                        <li key={i}>{d}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {recap.action_items && recap.action_items.length > 0 && (
                  <div className="recap-actions">
                    <h4>Action Items</h4>
                    <ul>
                      {recap.action_items.map((a, i) => (
                        <li key={i}>{a}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {recap.relevance && (
                  <div className="recap-relevance">
                    <h4>Relevance</h4>
                    <p>{recap.relevance}</p>
                  </div>
                )}

                {recap.sources && recap.sources.length > 0 && (
                  <div className="recap-sources">
                    <h4>Sources</h4>
                    {recap.sources.map((s, i) => (
                      <div key={i} className="source-item">
                        <span className="source-title">{s.title || s.conversation_id}</span>
                        <span className="source-relevance">{Math.round(s.relevance * 100)}%</span>
                        <span className="text-muted">{new Date(s.timestamp).toLocaleDateString()}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="panel-empty">{recap.message}</div>
            )
          ) : (
            <div className="panel-empty">Enter a query and click "Generate Recap" to summarize past conversations.</div>
          )}
        </div>
      )}
    </div>
  );
};