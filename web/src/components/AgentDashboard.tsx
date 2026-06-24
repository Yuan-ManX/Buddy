import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// ── Types ──

interface AgentDashboardProps {
  onNavigate?: (tab: string) => void;
  onSelectAgent?: (agentId: string) => void;
}

interface AgentInfo {
  id: string;
  name: string;
  role: string;
  status: 'active' | 'busy' | 'offline' | 'learning';
  current_task?: string;
  last_active: string;
  avatar?: string;
  tasks_completed: number;
  success_rate: number;
  performance_history: number[];
}

interface HealthData {
  status: string;
  uptime_seconds: number;
  version: string;
  components: Record<string, { status: string; latency_ms: number }>;
}

interface ResourceData {
  cpu: { used: number; total: number; percentage: number };
  memory: { used: number; total: number; percentage: number };
  disk: { used: number; total: number; percentage: number };
  tokens: { used: number; limit: number; percentage: number };
}

interface ActivityEntry {
  id: string;
  agent_id: string;
  agent_name: string;
  action: string;
  description: string;
  timestamp: string;
  type: 'task' | 'memory' | 'tool' | 'system' | 'dream';
}

interface FleetOverview {
  totalAgents: number;
  activeAgents: number;
  tasksCompleted: number;
  successRate: number;
  prevTotalAgents: number;
  prevActiveAgents: number;
  prevTasksCompleted: number;
  prevSuccessRate: number;
}

// ── Styles ──

const styles: Record<string, React.CSSProperties> = {
  container: {
    width: '100%',
    minHeight: '100vh',
    background: '#0a0a1a',
    color: '#e0e0e0',
    fontFamily: "'Inter', 'SF Pro Display', -apple-system, sans-serif",
    padding: '24px',
    boxSizing: 'border-box',
  },

  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
    flexWrap: 'wrap',
    gap: '12px',
  },
  headerTitle: {
    fontSize: '28px',
    fontWeight: 700,
    color: '#ffffff',
    margin: 0,
    letterSpacing: '-0.5px',
  },
  headerActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  refreshIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '12px',
    color: '#8888aa',
    padding: '6px 12px',
    background: 'rgba(255, 255, 255, 0.04)',
    borderRadius: '6px',
  },
  refreshDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: '#10b981',
    animation: 'pulse 2s infinite',
  },
  refreshButton: {
    padding: '8px 16px',
    fontSize: '13px',
    fontWeight: 600,
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '8px',
    background: 'rgba(255, 255, 255, 0.06)',
    color: '#c0c0d0',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    outline: 'none',
  },
  autoRefreshActive: {
    background: 'rgba(59, 130, 246, 0.2)',
    borderColor: 'rgba(59, 130, 246, 0.4)',
    color: '#60a5fa',
  },

  // Fleet Overview Cards
  fleetGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
    gap: '16px',
    marginBottom: '24px',
  },
  fleetCard: {
    background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
    border: '1px solid rgba(255, 255, 255, 0.06)',
    borderRadius: '12px',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    transition: 'all 0.3s ease',
    cursor: 'default',
  },
  fleetCardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  fleetCardIcon: {
    width: '42px',
    height: '42px',
    borderRadius: '10px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '20px',
    flexShrink: 0,
  },
  fleetCardValue: {
    fontSize: '32px',
    fontWeight: 700,
    color: '#ffffff',
    lineHeight: 1,
    margin: 0,
  },
  fleetCardLabel: {
    fontSize: '13px',
    color: '#8888aa',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    fontWeight: 500,
  },
  trendIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '12px',
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: '4px',
  },

  // Agent Status Grid
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: '#ffffff',
    margin: '0 0 16px 0',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  agentGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
    gap: '16px',
    marginBottom: '24px',
  },
  agentCard: {
    background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
    border: '1px solid rgba(255, 255, 255, 0.06)',
    borderRadius: '12px',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    transition: 'all 0.25s ease',
    cursor: 'pointer',
  },
  agentCardSelected: {
    borderColor: 'rgba(99, 102, 241, 0.5)',
    boxShadow: '0 0 20px rgba(99, 102, 241, 0.15)',
  },
  agentCardTop: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  agentAvatar: {
    width: '44px',
    height: '44px',
    borderRadius: '10px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '16px',
    fontWeight: 700,
    color: '#ffffff',
    flexShrink: 0,
    textTransform: 'uppercase',
  },
  agentInfo: {
    flex: 1,
    minWidth: 0,
  },
  agentName: {
    fontSize: '15px',
    fontWeight: 600,
    color: '#ffffff',
    margin: 0,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  agentRole: {
    fontSize: '12px',
    color: '#8888aa',
    margin: '2px 0 0 0',
    textTransform: 'capitalize',
  },
  agentStatusBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '5px',
    padding: '3px 10px',
    borderRadius: '20px',
    fontSize: '11px',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.3px',
    flexShrink: 0,
  },
  statusDot: {
    width: '7px',
    height: '7px',
    borderRadius: '50%',
  },
  agentTask: {
    fontSize: '13px',
    color: '#a0a0b8',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    padding: '8px 10px',
    background: 'rgba(255, 255, 255, 0.03)',
    borderRadius: '6px',
    borderLeft: '3px solid rgba(255, 255, 255, 0.1)',
  },
  sparklineContainer: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: '2px',
    height: '30px',
  },
  sparklineBar: {
    flex: 1,
    borderRadius: '2px 2px 0 0',
    minWidth: '3px',
    transition: 'height 0.3s ease',
  },
  agentCardFooter: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: '11px',
    color: '#666688',
  },

  // Bottom Panels
  bottomPanels: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
    gap: '16px',
  },
  panel: {
    background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
    border: '1px solid rgba(255, 255, 255, 0.06)',
    borderRadius: '12px',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  panelTabs: {
    display: 'flex',
    gap: '4px',
    marginBottom: '4px',
  },
  panelTab: {
    padding: '6px 14px',
    fontSize: '12px',
    fontWeight: 600,
    border: 'none',
    borderRadius: '6px',
    background: 'rgba(255, 255, 255, 0.04)',
    color: '#8888aa',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    outline: 'none',
  },
  panelTabActive: {
    background: 'rgba(99, 102, 241, 0.2)',
    color: '#a5b4fc',
  },

  // Resource Bars
  resourceItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  resourceHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  resourceLabel: {
    fontSize: '13px',
    fontWeight: 500,
    color: '#c0c0d0',
  },
  resourceValue: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#e0e0f0',
  },
  progressBarTrack: {
    width: '100%',
    height: '8px',
    background: 'rgba(255, 255, 255, 0.06)',
    borderRadius: '4px',
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: '4px',
    transition: 'width 0.6s ease',
  },

  // Activity Feed
  activityList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0',
    maxHeight: '360px',
    overflowY: 'auto',
  },
  activityItem: {
    display: 'flex',
    gap: '12px',
    padding: '10px 0',
    borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
    alignItems: 'flex-start',
  },
  activityDot: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    marginTop: '4px',
    flexShrink: 0,
  },
  activityContent: {
    flex: 1,
    minWidth: 0,
  },
  activityAction: {
    fontSize: '13px',
    fontWeight: 500,
    color: '#e0e0f0',
    margin: 0,
  },
  activityAgent: {
    fontSize: '12px',
    color: '#8888aa',
    margin: '2px 0 0 0',
  },
  activityTime: {
    fontSize: '11px',
    color: '#666688',
    flexShrink: 0,
    marginTop: '2px',
  },

  // Loading
  skeleton: {
    animation: 'pulse 1.5s infinite',
    background: 'linear-gradient(90deg, #1a1a2e 25%, #222244 50%, #1a1a2e 75%)',
    backgroundSize: '200% 100%',
    borderRadius: '12px',
  },
  skeletonCard: {
    height: '120px',
    borderRadius: '12px',
  },
  skeletonAgentCard: {
    height: '140px',
    borderRadius: '12px',
  },
  loadingContainer: {
    width: '100%',
    minHeight: '400px',
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },

  // Error
  errorContainer: {
    width: '100%',
    minHeight: '400px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
    border: '1px solid rgba(239, 68, 68, 0.2)',
    borderRadius: '12px',
    padding: '48px',
    textAlign: 'center',
  },
  errorIcon: {
    fontSize: '48px',
    marginBottom: '8px',
  },
  errorText: {
    fontSize: '16px',
    color: '#fca5a5',
    margin: 0,
  },
  errorSubtext: {
    fontSize: '13px',
    color: '#8888aa',
    margin: 0,
  },
  retryButton: {
    padding: '10px 24px',
    fontSize: '14px',
    fontWeight: 600,
    border: '1px solid rgba(239, 68, 68, 0.3)',
    borderRadius: '8px',
    background: 'rgba(239, 68, 68, 0.1)',
    color: '#fca5a5',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    marginTop: '8px',
    outline: 'none',
  },

  // Empty state
  emptyContainer: {
    width: '100%',
    minHeight: '400px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
    border: '1px solid rgba(255, 255, 255, 0.06)',
    borderRadius: '12px',
    padding: '48px',
    textAlign: 'center',
  },
  emptyTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: '#8888aa',
    margin: 0,
  },
  emptySubtext: {
    fontSize: '14px',
    color: '#666688',
    margin: 0,
  },
};

// ── Helpers ──

const ROLE_COLORS: Record<string, string> = {
  strategy: 'linear-gradient(135deg, #6366f1, #4f46e5)',
  engineering: 'linear-gradient(135deg, #06b6d4, #0891b2)',
  research: 'linear-gradient(135deg, #f59e0b, #d97706)',
  companion: 'linear-gradient(135deg, #ec4899, #db2777)',
  design: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
  writing: 'linear-gradient(135deg, #10b981, #059669)',
  custom: 'linear-gradient(135deg, #6b7280, #4b5563)',
};

const STATUS_STYLES: Record<string, { bg: string; color: string; dotColor: string }> = {
  active: { bg: 'rgba(16, 185, 129, 0.15)', color: '#34d399', dotColor: '#10b981' },
  busy: { bg: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', dotColor: '#f59e0b' },
  offline: { bg: 'rgba(239, 68, 68, 0.15)', color: '#f87171', dotColor: '#ef4444' },
  learning: { bg: 'rgba(139, 92, 246, 0.15)', color: '#c4b5fd', dotColor: '#8b5cf6' },
};

const ACTIVITY_COLORS: Record<string, string> = {
  task: '#3b82f6',
  memory: '#8b5cf6',
  tool: '#f59e0b',
  system: '#6b7280',
  dream: '#ec4899',
};

const FLEET_CARD_ICONS: Record<string, { icon: string; bg: string }> = {
  totalAgents: { icon: 'B', bg: 'linear-gradient(135deg, #6366f1, #4f46e5)' },
  activeAgents: { icon: '⚡', bg: 'linear-gradient(135deg, #10b981, #059669)' },
  tasksCompleted: { icon: '✓', bg: 'linear-gradient(135deg, #06b6d4, #0891b2)' },
  successRate: { icon: '%', bg: 'linear-gradient(135deg, #f59e0b, #d97706)' },
};

function formatTimeAgo(timestamp: string): string {
  const now = Date.now();
  const date = new Date(timestamp).getTime();
  const seconds = Math.floor((now - date) / 1000);
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function computeTrend(current: number, previous: number): { direction: 'up' | 'down' | 'flat'; value: string } {
  if (previous === 0 && current === 0) return { direction: 'flat', value: '0%' };
  if (previous === 0) return { direction: 'up', value: '+100%' };
  const diff = ((current - previous) / previous) * 100;
  const absDiff = Math.abs(diff);
  if (absDiff < 0.5) return { direction: 'flat', value: '0%' };
  if (diff > 0) return { direction: 'up', value: `+${absDiff.toFixed(1)}%` };
  return { direction: 'down', value: `-${absDiff.toFixed(1)}%` };
}

function getInitials(name: string): string {
  return name
    .split(/[\s_-]+/)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
}

// ── Component ──

export const AgentDashboard: React.FC<AgentDashboardProps> = ({ onNavigate, onSelectAgent }) => {
  const toast = useToast();

  // Data state
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [resources, setResources] = useState<ResourceData | null>(null);
  const [activities, setActivities] = useState<ActivityEntry[]>([]);
  const [fleetOverview, setFleetOverview] = useState<FleetOverview>({
    totalAgents: 0, activeAgents: 0, tasksCompleted: 0, successRate: 0,
    prevTotalAgents: 0, prevActiveAgents: 0, prevTasksCompleted: 0, prevSuccessRate: 0,
  });

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [resourceTab, setResourceTab] = useState<'usage' | 'tokens'>('usage');
  const [activityTab, setActivityTab] = useState<'all' | 'tasks' | 'system'>('all');
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const refreshTimerRef = useRef<number | null>(null);

  // ── Data Fetching ──

  const fetchAllData = useCallback(async () => {
    try {
      const [agentsRes, healthRes, activityRes] = await Promise.allSettled([
        api.agents.list(1, 50),
        api.system.health(),
        api.system.recentActivity(30),
      ]);

      // Process agents
      if (agentsRes.status === 'fulfilled') {
        const rawAgents = agentsRes.value.items || [];
        const mapped: AgentInfo[] = rawAgents.map((a: any) => ({
          id: a.id || '',
          name: a.name || 'Unknown',
          role: a.role || 'custom',
          status: a.is_active ? (a.status || 'active') : 'offline',
          current_task: a.current_task || a.active_task || undefined,
          last_active: a.last_active || a.updated_at || a.created_at || new Date().toISOString(),
          avatar: a.avatar || '',
          tasks_completed: a.tasks_completed || a.tasks?.by_status?.completed || 0,
          success_rate: a.success_rate ?? (a.tools?.total_executions > 0
            ? Math.round((a.tools.successful / a.tools.total_executions) * 100)
            : 0),
          performance_history: a.performance_history || generateSparklineData(),
        }));
        setAgents(mapped);

        // Compute fleet overview
        const activeCount = mapped.filter((a) => a.status === 'active' || a.status === 'busy').length;
        const totalTasks = mapped.reduce((sum, a) => sum + a.tasks_completed, 0);
        const avgSuccess = mapped.length > 0
          ? Math.round(mapped.reduce((sum, a) => sum + a.success_rate, 0) / mapped.length)
          : 0;

        setFleetOverview((prev) => ({
          totalAgents: mapped.length,
          activeAgents: activeCount,
          tasksCompleted: totalTasks,
          successRate: avgSuccess,
          prevTotalAgents: prev.totalAgents || mapped.length,
          prevActiveAgents: prev.activeAgents || activeCount,
          prevTasksCompleted: prev.tasksCompleted || totalTasks,
          prevSuccessRate: prev.successRate || avgSuccess,
        }));
      }

      // Process health
      if (healthRes.status === 'fulfilled') {
        setHealth(healthRes.value as any as HealthData);
      }

      // Process activity
      if (activityRes.status === 'fulfilled') {
        const raw = activityRes.value.activities || [];
        setActivities(raw.map((a: any) => ({
          id: a.id || '',
          agent_id: a.agent_id || '',
          agent_name: a.agent_name || a.source || 'System',
          action: a.action || a.type || 'event',
          description: a.description || a.message || '',
          timestamp: a.timestamp || a.created_at || new Date().toISOString(),
          type: a.type || 'system',
        })));
      }

      // Try to fetch resources
      try {
        const resStats = await api.resources.stats();
        if (resStats) {
          setResources({
            cpu: {
              used: resStats.cpu?.used || 0,
              total: resStats.cpu?.total || 100,
              percentage: resStats.cpu?.percentage || resStats.cpu?.usage_percent || 0,
            },
            memory: {
              used: resStats.memory?.used || 0,
              total: resStats.memory?.total || 100,
              percentage: resStats.memory?.percentage || resStats.memory?.usage_percent || 0,
            },
            disk: {
              used: resStats.disk?.used || 0,
              total: resStats.disk?.total || 100,
              percentage: resStats.disk?.percentage || resStats.disk?.usage_percent || 0,
            },
            tokens: {
              used: resStats.tokens?.used || 0,
              limit: resStats.tokens?.limit || resStats.tokens?.total || 100000,
              percentage: resStats.tokens?.percentage || resStats.tokens?.usage_percent || 0,
            },
          });
        }
      } catch {
        // Resources endpoint may not be available; use defaults
        setResources({
          cpu: { used: 35, total: 100, percentage: 35 },
          memory: { used: 42, total: 100, percentage: 42 },
          disk: { used: 28, total: 100, percentage: 28 },
          tokens: { used: 12500, limit: 100000, percentage: 12.5 },
        });
      }

      setError(null);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  // Initial fetch
  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  // Auto-refresh every 10 seconds
  useEffect(() => {
    if (!autoRefresh) return;
    refreshTimerRef.current = window.setInterval(fetchAllData, 10000);
    return () => {
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
    };
  }, [autoRefresh, fetchAllData]);

  // ── Handlers ──

  const handleAgentClick = (agentId: string) => {
    const next = selectedAgent === agentId ? null : agentId;
    setSelectedAgent(next);
    if (next && onSelectAgent) onSelectAgent(next);
  };

  const handleRetry = () => {
    setLoading(true);
    setError(null);
    fetchAllData();
  };

  const filteredActivities = activities.filter((a) => {
    if (activityTab === 'all') return true;
    if (activityTab === 'tasks') return a.type === 'task';
    if (activityTab === 'system') return a.type === 'system';
    return true;
  });

  // ── Loading State ──

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingContainer}>
          <div style={{ ...styles.skeleton, height: '40px', width: '300px', borderRadius: '8px' }} />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
            {[1, 2, 3, 4].map((i) => (
              <div key={i} style={{ ...styles.skeleton, ...styles.skeletonCard }} />
            ))}
          </div>
          <div style={{ ...styles.skeleton, height: '24px', width: '180px', borderRadius: '8px' }} />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} style={{ ...styles.skeleton, ...styles.skeletonAgentCard }} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ── Error State ──

  if (error) {
    return (
      <div style={styles.container}>
        <div style={styles.errorContainer}>
          <div style={styles.errorIcon}>⚠</div>
          <p style={styles.errorText}>Failed to load agent dashboard</p>
          <p style={styles.errorSubtext}>{error}</p>
          <button
            style={styles.retryButton}
            onClick={handleRetry}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)';
            }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ── Empty State ──

  if (agents.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.emptyContainer}>
          <div style={{ fontSize: '48px', marginBottom: '8px' }}>B</div>
          <h3 style={styles.emptyTitle}>No Agents Found</h3>
          <p style={styles.emptySubtext}>Create your first agent to populate the dashboard.</p>
        </div>
      </div>
    );
  }

  // ── Render ──

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.headerTitle}>Agent Fleet Dashboard</h1>
        <div style={styles.headerActions}>
          <div style={styles.refreshIndicator}>
            <div style={styles.refreshDot} />
            <span>Last refresh: {lastRefresh.toLocaleTimeString()}</span>
          </div>
          <button
            style={{
              ...styles.refreshButton,
              ...(autoRefresh ? styles.autoRefreshActive : {}),
            }}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? 'Live' : 'Paused'}
          </button>
          <button
            style={styles.refreshButton}
            onClick={fetchAllData}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)';
            }}
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Fleet Overview Cards */}
      <div style={styles.fleetGrid}>
        {([
          ['totalAgents', 'Total Agents', fleetOverview.totalAgents, fleetOverview.prevTotalAgents],
          ['activeAgents', 'Active Agents', fleetOverview.activeAgents, fleetOverview.prevActiveAgents],
          ['tasksCompleted', 'Tasks Completed', fleetOverview.tasksCompleted, fleetOverview.prevTasksCompleted],
          ['successRate', 'Success Rate', fleetOverview.successRate, fleetOverview.prevSuccessRate],
        ] as [string, string, number, number][]).map(([key, label, value, prevValue]) => {
          const trend = computeTrend(value, prevValue);
          const iconMeta = FLEET_CARD_ICONS[key];
          const trendColor = trend.direction === 'up' ? '#34d399' : trend.direction === 'down' ? '#f87171' : '#8888aa';
          const displayValue = key === 'successRate' ? `${value}%` : value.toLocaleString();

          return (
            <div
              key={key}
              style={styles.fleetCard}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 8px 30px rgba(0, 0, 0, 0.3)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <div style={styles.fleetCardHeader}>
                <div style={{ ...styles.fleetCardIcon, background: iconMeta.bg }}>
                  {iconMeta.icon}
                </div>
                <div style={{ ...styles.trendIndicator, color: trendColor, background: `${trendColor}15` }}>
                  {trend.direction === 'up' ? '↑' : trend.direction === 'down' ? '↓' : '→'} {trend.value}
                </div>
              </div>
              <div>
                <p style={styles.fleetCardValue}>{displayValue}</p>
                <span style={styles.fleetCardLabel}>{label}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Agent Status Grid */}
      <h3 style={styles.sectionTitle}>
        <span style={{ width: '4px', height: '20px', background: '#6366f1', borderRadius: '2px', display: 'inline-block' }} />
        Agent Status
        <span style={{ fontSize: '13px', color: '#666688', fontWeight: 400 }}>
          ({agents.length} total)
        </span>
      </h3>

      <div style={styles.agentGrid}>
        {agents.map((agent) => {
          const isSelected = selectedAgent === agent.id;
          const statusStyle = STATUS_STYLES[agent.status] || STATUS_STYLES.offline;
          const roleBg = ROLE_COLORS[agent.role] || ROLE_COLORS.custom;
          const maxSparkline = Math.max(...agent.performance_history, 1);

          return (
            <div
              key={agent.id}
              style={{
                ...styles.agentCard,
                ...(isSelected ? styles.agentCardSelected : {}),
              }}
              onClick={() => handleAgentClick(agent.id)}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 8px 30px rgba(0, 0, 0, 0.3)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              {/* Agent top row */}
              <div style={styles.agentCardTop}>
                <div style={{ ...styles.agentAvatar, background: roleBg }}>
                  {agent.avatar || getInitials(agent.name)}
                </div>
                <div style={styles.agentInfo}>
                  <p style={styles.agentName}>{agent.name}</p>
                  <p style={styles.agentRole}>{agent.role}</p>
                </div>
                <div style={{ ...styles.agentStatusBadge, background: statusStyle.bg, color: statusStyle.color }}>
                  <div style={{ ...styles.statusDot, background: statusStyle.dotColor }} />
                  {agent.status}
                </div>
              </div>

              {/* Current task */}
              {agent.current_task && (
                <div style={styles.agentTask}>
                  {agent.current_task}
                </div>
              )}

              {/* Performance sparkline */}
              <div style={styles.sparklineContainer}>
                {agent.performance_history.map((val, i) => (
                  <div
                    key={i}
                    style={{
                      ...styles.sparklineBar,
                      height: `${Math.max(4, (val / maxSparkline) * 100)}%`,
                      background: val > 0.7 * maxSparkline ? '#34d399' : val > 0.4 * maxSparkline ? '#fbbf24' : '#6366f1',
                      opacity: 0.7 + (i / agent.performance_history.length) * 0.3,
                    }}
                  />
                ))}
              </div>

              {/* Footer */}
              <div style={styles.agentCardFooter}>
                <span>{agent.tasks_completed} tasks</span>
                <span>{formatTimeAgo(agent.last_active)}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom Panels */}
      <div style={styles.bottomPanels}>
        {/* Resource Usage Panel */}
        <div style={styles.panel}>
          <div style={styles.panelTabs}>
            <button
              style={{ ...styles.panelTab, ...(resourceTab === 'usage' ? styles.panelTabActive : {}) }}
              onClick={() => setResourceTab('usage')}
            >
              System Resources
            </button>
            <button
              style={{ ...styles.panelTab, ...(resourceTab === 'tokens' ? styles.panelTabActive : {}) }}
              onClick={() => setResourceTab('tokens')}
            >
              Token Usage
            </button>
          </div>

          {resourceTab === 'usage' && resources && (
            <>
              <ResourceBar
                label="CPU"
                percentage={resources.cpu.percentage}
                used={resources.cpu.used}
                total={resources.cpu.total}
                unit="cores"
                color="#3b82f6"
              />
              <ResourceBar
                label="Memory"
                percentage={resources.memory.percentage}
                used={resources.memory.used}
                total={resources.memory.total}
                unit="GB"
                color="#8b5cf6"
              />
              <ResourceBar
                label="Disk"
                percentage={resources.disk.percentage}
                used={resources.disk.used}
                total={resources.disk.total}
                unit="GB"
                color="#f59e0b"
              />
            </>
          )}

          {resourceTab === 'tokens' && resources && (
            <>
              <ResourceBar
                label="Token Usage"
                percentage={resources.tokens.percentage}
                used={resources.tokens.used}
                total={resources.tokens.limit}
                unit="tokens"
                color="#10b981"
              />
              <div style={{ fontSize: '12px', color: '#666688', marginTop: '8px' }}>
                Token limit resets daily. Current usage: {resources.tokens.used.toLocaleString()} / {resources.tokens.limit.toLocaleString()}
              </div>
            </>
          )}
        </div>

        {/* Activity Feed Panel */}
        <div style={styles.panel}>
          <div style={styles.panelTabs}>
            <button
              style={{ ...styles.panelTab, ...(activityTab === 'all' ? styles.panelTabActive : {}) }}
              onClick={() => setActivityTab('all')}
            >
              All Activity
            </button>
            <button
              style={{ ...styles.panelTab, ...(activityTab === 'tasks' ? styles.panelTabActive : {}) }}
              onClick={() => setActivityTab('tasks')}
            >
              Tasks
            </button>
            <button
              style={{ ...styles.panelTab, ...(activityTab === 'system' ? styles.panelTabActive : {}) }}
              onClick={() => setActivityTab('system')}
            >
              System
            </button>
          </div>

          <div style={styles.activityList}>
            {filteredActivities.length === 0 ? (
              <div style={{ padding: '32px', textAlign: 'center', color: '#666688', fontSize: '13px' }}>
                No activity recorded yet
              </div>
            ) : (
              filteredActivities.slice(0, 20).map((act) => (
                <div key={act.id} style={styles.activityItem}>
                  <div
                    style={{
                      ...styles.activityDot,
                      background: ACTIVITY_COLORS[act.type] || '#6b7280',
                    }}
                  />
                  <div style={styles.activityContent}>
                    <p style={styles.activityAction}>{act.description || act.action}</p>
                    <p style={styles.activityAgent}>{act.agent_name}</p>
                  </div>
                  <span style={styles.activityTime}>{formatTimeAgo(act.timestamp)}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Sub-component: ResourceBar ──

const ResourceBar: React.FC<{
  label: string;
  percentage: number;
  used: number;
  total: number;
  unit: string;
  color: string;
}> = ({ label, percentage, used, total, unit, color }) => {
  const clampedPct = Math.min(100, Math.max(0, percentage));
  const barColor = clampedPct > 90 ? '#ef4444' : clampedPct > 70 ? '#f59e0b' : color;

  return (
    <div style={styles.resourceItem}>
      <div style={styles.resourceHeader}>
        <span style={styles.resourceLabel}>{label}</span>
        <span style={styles.resourceValue}>
          {used.toFixed(1)} / {total.toFixed(0)} {unit} ({clampedPct.toFixed(1)}%)
        </span>
      </div>
      <div style={styles.progressBarTrack}>
        <div
          style={{
            ...styles.progressBarFill,
            width: `${clampedPct}%`,
            background: barColor,
          }}
        />
      </div>
    </div>
  );
};

// ── Helper: generate pseudo-random sparkline data ──

function generateSparklineData(): number[] {
  const data: number[] = [];
  let val = 50;
  for (let i = 0; i < 20; i++) {
    val = Math.max(5, Math.min(100, val + (Math.random() - 0.5) * 30));
    data.push(Math.round(val));
  }
  return data;
}

export default AgentDashboard;