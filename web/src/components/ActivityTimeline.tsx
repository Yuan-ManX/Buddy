import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';

interface ActivityEvent {
  id: string;
  type: string;
  source: string;
  data: Record<string, unknown>;
  timestamp: string;
}

type ActivityType = 'chat' | 'tool' | 'task' | 'memory' | 'error' | 'all';
type TimeRange = '1h' | '6h' | '24h' | '7d' | 'all';

const ACTIVITY_TYPE_CONFIG: Record<ActivityType, { label: string; icon: string; color: string }> = {
  chat: { label: 'Chat', icon: '💬', color: '#3b82f6' },
  tool: { label: 'Tool', icon: '🔧', color: '#10b981' },
  task: { label: 'Task', icon: '📋', color: '#f59e0b' },
  memory: { label: 'Memory', icon: '🧠', color: '#8b5cf6' },
  error: { label: 'Error', icon: '❌', color: '#ef4444' },
  all: { label: 'All', icon: '📡', color: '#6b7280' },
};

function classifyEventType(event: ActivityEvent): ActivityType {
  const type = event.type.toLowerCase();
  const source = event.source.toLowerCase();
  if (type.includes('error') || type.includes('fail') || source.includes('error')) return 'error';
  if (type.includes('tool') || source.includes('tool') || type.includes('execution')) return 'tool';
  if (type.includes('task') || source.includes('task') || type.includes('claim')) return 'task';
  if (type.includes('memory') || source.includes('memory') || type.includes('dream') || type.includes('semantic')) return 'memory';
  if (type.includes('chat') || source.includes('chat') || type.includes('message') || type.includes('conversation')) return 'chat';
  return 'chat';
}

function formatTimestamp(ts: string): string {
  const d = new Date(ts);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return d.toLocaleDateString();
}

function getEventDescription(event: ActivityEvent): string {
  const { type, source, data } = event;
  const agentName = (data.agent_name as string) || (data.agent_id as string) || source;
  const typeLabel = type.replace(/_/g, ' ');
  const content = data.content || data.title || data.description || data.result || '';
  const summary = typeof content === 'string' ? content.slice(0, 120) : JSON.stringify(content).slice(0, 120);
  return `${agentName} — ${typeLabel}${summary ? ': ' + summary : ''}`;
}

const PAGE_SIZE = 20;

export const ActivityTimeline: React.FC = () => {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<ActivityType>('all');
  const [filterAgent, setFilterAgent] = useState('');
  const [timeRange, setTimeRange] = useState<TimeRange>('all');
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const timelineRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchEvents = useCallback(async (pageNum: number, append: boolean = false) => {
    try {
      if (pageNum === 1) setLoading(true);
      else setLoadingMore(true);
      setError(null);
      const res = await api.events.history(undefined, PAGE_SIZE * pageNum);
      const newEvents = res as unknown as ActivityEvent[];
      if (append) {
        setEvents(prev => [...prev, ...newEvents]);
      } else {
        setEvents(newEvents);
      }
      setHasMore(newEvents.length >= PAGE_SIZE);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load events');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    fetchEvents(1);
  }, [fetchEvents]);

  // Auto-refresh via polling every 5 seconds
  useEffect(() => {
    pollRef.current = setInterval(() => {
      fetchEvents(1);
    }, 5000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchEvents]);

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchEvents(nextPage, true);
  };

  const toggleExpand = (id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const filteredEvents = events.filter(ev => {
    if (filterType !== 'all' && classifyEventType(ev) !== filterType) return false;
    if (filterAgent && !ev.source.toLowerCase().includes(filterAgent.toLowerCase()) &&
        !JSON.stringify(ev.data).toLowerCase().includes(filterAgent.toLowerCase())) return false;
    if (timeRange !== 'all') {
      const eventTime = new Date(ev.timestamp).getTime();
      const now = Date.now();
      const ranges: Record<TimeRange, number> = { '1h': 3600000, '6h': 21600000, '24h': 86400000, '7d': 604800000, 'all': 0 };
      if (now - eventTime > ranges[timeRange]) return false;
    }
    return true;
  });

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div>
          <h2>Activity Timeline</h2>
          <p className="panel-subtitle">Real-time agent activity feed</p>
        </div>
      </div>

      {/* Filters */}
      <div className="activity-filters">
        <div className="activity-filter-group">
          <span className="activity-filter-label">Type:</span>
          <div className="activity-type-chips">
            {(Object.keys(ACTIVITY_TYPE_CONFIG) as ActivityType[]).map(t => (
              <button
                key={t}
                className={`activity-type-chip ${filterType === t ? 'active' : ''}`}
                style={{ '--chip-color': ACTIVITY_TYPE_CONFIG[t].color } as React.CSSProperties}
                onClick={() => setFilterType(t)}
              >
                {ACTIVITY_TYPE_CONFIG[t].icon} {ACTIVITY_TYPE_CONFIG[t].label}
              </button>
            ))}
          </div>
        </div>
        <div className="activity-filter-group">
          <span className="activity-filter-label">Agent:</span>
          <input
            className="activity-filter-input"
            type="text"
            placeholder="Filter by agent name..."
            value={filterAgent}
            onChange={e => setFilterAgent(e.target.value)}
          />
        </div>
        <div className="activity-filter-group">
          <span className="activity-filter-label">Time:</span>
          <select
            className="activity-filter-select"
            value={timeRange}
            onChange={e => setTimeRange(e.target.value as TimeRange)}
          >
            <option value="all">All Time</option>
            <option value="1h">Last Hour</option>
            <option value="6h">Last 6 Hours</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button className="btn-sm" onClick={() => fetchEvents(1)}>Retry</button>
        </div>
      )}

      {/* Timeline */}
      <div className="activity-timeline" ref={timelineRef}>
        {loading && events.length === 0 && (
          <div className="panel-loading">Loading activity feed...</div>
        )}

        {!loading && filteredEvents.length === 0 && (
          <div className="panel-empty activity-empty">
            <div className="activity-empty-icon">📡</div>
            <p>No activity events yet</p>
            <span>Events will appear here as agents interact with the system.</span>
          </div>
        )}

        {filteredEvents.map((event, idx) => {
          const activityType = classifyEventType(event);
          const config = ACTIVITY_TYPE_CONFIG[activityType];
          const isExpanded = expandedIds.has(event.id);

          return (
            <div key={event.id} className="activity-entry">
              <div className="activity-entry-line" />
              <div
                className="activity-entry-dot"
                style={{ background: config.color }}
              />
              <div
                className={`activity-entry-card ${isExpanded ? 'expanded' : ''}`}
                onClick={() => toggleExpand(event.id)}
              >
                <div className="activity-entry-header">
                  <span className="activity-entry-icon">{config.icon}</span>
                  <span className="activity-entry-type" style={{ color: config.color }}>
                    {config.label}
                  </span>
                  <span className="activity-entry-source">{event.source}</span>
                  <span className="activity-entry-time">{formatTimestamp(event.timestamp)}</span>
                  <span className="activity-entry-expand">{isExpanded ? '▾' : '▸'}</span>
                </div>
                <div className="activity-entry-desc">{getEventDescription(event)}</div>
                {isExpanded && (
                  <div className="activity-entry-detail">
                    <div className="activity-detail-grid">
                      <span className="activity-detail-label">Event ID</span>
                      <span className="activity-detail-value">{event.id}</span>
                      <span className="activity-detail-label">Type</span>
                      <span className="activity-detail-value">{event.type}</span>
                      <span className="activity-detail-label">Source</span>
                      <span className="activity-detail-value">{event.source}</span>
                      <span className="activity-detail-label">Timestamp</span>
                      <span className="activity-detail-value">{new Date(event.timestamp).toLocaleString()}</span>
                    </div>
                    <div className="activity-detail-data">
                      <span className="activity-detail-label">Data</span>
                      <pre className="activity-detail-json">{JSON.stringify(event.data, null, 2)}</pre>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {hasMore && !loading && filteredEvents.length > 0 && (
          <div className="activity-load-more">
            <button
              className="btn-secondary"
              onClick={handleLoadMore}
              disabled={loadingMore}
            >
              {loadingMore ? 'Loading...' : 'Load More'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ActivityTimeline;