import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// ── Props ──

interface PlatformConsolePanelProps {
  onNavigate?: (tab: string) => void;
}

// ── Local Types ──

type HealthStatus = 'healthy' | 'degraded' | 'unhealthy' | 'offline';
type TabId = 'dashboard' | 'components' | 'resources' | 'fleet' | 'audit' | 'features' | 'analytics' | 'diagnostics';
type SeverityLevel = 'critical' | 'error' | 'warning' | 'info';
type AlertSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';
type FleetStatus = 'active' | 'idle' | 'offline' | 'error';
type FleetRole = 'orchestrator' | 'worker' | 'specialist' | 'monitor' | 'gateway';
type DiagnosticsResult = 'pass' | 'fail' | 'warning';

interface PlatformHealth {
  status: HealthStatus;
  uptime_seconds: number;
  active_agents: number;
  total_requests: number;
  error_rate: number;
  alerts: PlatformAlert[];
  components: ComponentHealth[];
  timestamp: string;
}

interface PlatformAlert {
  id: string;
  severity: AlertSeverity;
  component: string;
  message: string;
  created_at: string;
  acknowledged: boolean;
}

interface ComponentHealth {
  id: string;
  name: string;
  icon: string;
  status: HealthStatus;
  latency_ms: number;
  error_count: number;
  last_checked: string;
  metrics?: ComponentMetric[];
  history?: number[];
}

interface ComponentMetric {
  label: string;
  value: string;
  status: HealthStatus;
}

interface ResourceSnapshot {
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  active_connections: number;
  max_connections: number;
  queue_depth: number;
  tokens_used: number;
  tokens_total: number;
  suggestions: ResourceSuggestion[];
}

interface ResourceSuggestion {
  id: string;
  message: string;
  impact: 'high' | 'medium' | 'low';
}

interface FleetAgent {
  id: string;
  name: string;
  role: FleetRole;
  status: FleetStatus;
  current_task: string;
  uptime_seconds: number;
  version: string;
  last_heartbeat: string;
}

interface AuditEntry {
  id: string;
  timestamp: string;
  component: string;
  action: string;
  agent: string;
  detail: string;
  severity: SeverityLevel;
}

interface AuditResponse {
  entries: AuditEntry[];
  total: number;
  page: number;
  page_size: number;
}

interface FeatureFlag {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  rollout_percentage: number;
  target_agents: string[];
  created_at: string;
  updated_at: string;
}

interface AnalyticsData {
  request_volume: { date: string; count: number }[];
  error_rate_trend: { date: string; rate: number }[];
  top_agents: { name: string; requests: number }[];
}

interface CostData {
  total_cost: number;
  breakdown: { category: string; cost: number; percentage: number }[];
}

interface DiagnosticsReport {
  id: string;
  results: {
    component: string;
    status: DiagnosticsResult;
    message: string;
    details: string;
  }[];
  recommendations: string[];
  timestamp: string;
}

interface FleetResponse {
  agents: FleetAgent[];
}

// ── Constants ──

const TAB_IDS: TabId[] = ['dashboard', 'components', 'resources', 'fleet', 'audit', 'features', 'analytics', 'diagnostics'];

const TAB_LABELS: Record<TabId, string> = {
  dashboard: 'Dashboard',
  components: 'Components',
  resources: 'Resources',
  fleet: 'Fleet',
  audit: 'Audit Log',
  features: 'Features',
  analytics: 'Analytics',
  diagnostics: 'Diagnostics',
};

const HEALTH_COLORS: Record<HealthStatus, string> = {
  healthy: '#22c55e',
  degraded: '#f59e0b',
  unhealthy: '#ef4444',
  offline: '#6b7280',
};

const HEALTH_LABELS: Record<HealthStatus, string> = {
  healthy: 'Healthy',
  degraded: 'Degraded',
  unhealthy: 'Unhealthy',
  offline: 'Offline',
};

const SEVERITY_COLORS: Record<SeverityLevel, string> = {
  critical: '#ef4444',
  error: '#f97316',
  warning: '#f59e0b',
  info: '#3b82f6',
};

const ALERT_SEVERITY_COLORS: Record<AlertSeverity, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#f59e0b',
  low: '#3b82f6',
  info: '#6b7280',
};

const FLEET_STATUS_COLORS: Record<FleetStatus, string> = {
  active: '#22c55e',
  idle: '#3b82f6',
  offline: '#6b7280',
  error: '#ef4444',
};

const FLEET_ROLE_LABELS: Record<FleetRole, string> = {
  orchestrator: 'Orchestrator',
  worker: 'Worker',
  specialist: 'Specialist',
  monitor: 'Monitor',
  gateway: 'Gateway',
};

const DIAGNOSTICS_RESULT_COLORS: Record<DiagnosticsResult, string> = {
  pass: '#22c55e',
  fail: '#ef4444',
  warning: '#f59e0b',
};

const DIAGNOSTICS_RESULT_ICONS: Record<DiagnosticsResult, string> = {
  pass: '\u2713',
  fail: '\u2717',
  warning: '\u26A0',
};

const DEFAULT_COMPONENTS: { id: string; name: string; icon: string }[] = [
  { id: 'api-gateway', name: 'API Gateway', icon: '\u2194\uFE0F' },
  { id: 'agent-runtime', name: 'Agent Runtime', icon: '\u2699\uFE0F' },
  { id: 'task-scheduler', name: 'Task Scheduler', icon: '\u23F0' },
  { id: 'memory-store', name: 'Memory Store', icon: '\uD83E\uDDE0' },
  { id: 'skill-engine', name: 'Skill Engine', icon: '\uD83D\uDD27' },
  { id: 'knowledge-base', name: 'Knowledge Base', icon: '\uD83D\uDCDA' },
  { id: 'event-bus', name: 'Event Bus', icon: '\uD83D\uDCE1' },
  { id: 'auth-service', name: 'Auth Service', icon: '\uD83D\uDD10' },
  { id: 'model-proxy', name: 'Model Proxy', icon: '\uD83E\uDD16' },
  { id: 'monitoring', name: 'Monitoring', icon: '\uD83D\uDCCA' },
];

const REFRESH_INTERVALS = [
  { label: '5s', value: 5000 },
  { label: '15s', value: 15000 },
  { label: '30s', value: 30000 },
  { label: '60s', value: 60000 },
  { label: 'Off', value: 0 },
];

const AUDIT_PAGE_SIZE = 20;
const ANALYTICS_DAYS_OPTIONS = [7, 30, 90];

// ── Helpers ──

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString();
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

// ── Component ──

export const PlatformConsolePanel: React.FC<PlatformConsolePanelProps> = ({ onNavigate }) => {


  const styles = {
    // Layout
    container: {
      fontFamily: 'inherit',
      color: '#e4e6ed',
      backgroundColor: '#1a1a2e',
      width: '100%',
      minHeight: '100%',
      display: 'flex',
      flexDirection: 'column',
    } as React.CSSProperties,

    loadingContainer: {
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '300px',
    } as React.CSSProperties,

    loadingSpinner: {
      color: '#818cf8',
      fontSize: '0.95rem',
      padding: '40px',
    } as React.CSSProperties,

    // Status Bar
    statusBar: {
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '10px 16px',
      backgroundColor: '#16213e',
      borderBottom: '1px solid #0f3460',
      gap: '8px',
    } as React.CSSProperties,

    statusBarLeft: {
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'center',
      gap: '16px',
    } as React.CSSProperties,

    statusBarRight: {
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
    } as React.CSSProperties,

    statusMetric: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: '2px',
    } as React.CSSProperties,

    statusMetricLabel: {
      fontSize: '0.65rem',
      color: '#6b7280',
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
    } as React.CSSProperties,

    statusMetricValue: {
      fontSize: '0.85rem',
      fontWeight: 600,
      color: '#e4e6ed',
    } as React.CSSProperties,

    alertIcon: {
      fontSize: '0.8rem',
    } as React.CSSProperties,

    autoRefreshLabel: {
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      fontSize: '0.75rem',
      color: '#9ca3af',
      cursor: 'pointer',
    } as React.CSSProperties,

    autoRefreshCheckbox: {
      accentColor: '#818cf8',
      cursor: 'pointer',
    } as React.CSSProperties,

    refreshSelect: {
      padding: '4px 8px',
      borderRadius: '4px',
      border: '1px solid #2a2d3a',
      backgroundColor: '#1c1f2e',
      color: '#e4e6ed',
      fontSize: '0.75rem',
      outline: 'none',
      cursor: 'pointer',
    } as React.CSSProperties,

    // Status Badge
    statusBadge: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      padding: '4px 10px',
      borderRadius: '12px',
      border: '1px solid',
      fontSize: '0.75rem',
      fontWeight: 600,
      whiteSpace: 'nowrap',
    } as React.CSSProperties,

    statusDot: {
      width: '8px',
      height: '8px',
      borderRadius: '50%',
      display: 'inline-block',
    } as React.CSSProperties,

    severityBadge: {
      display: 'inline-block',
      padding: '2px 8px',
      borderRadius: '4px',
      fontSize: '0.65rem',
      fontWeight: 700,
      whiteSpace: 'nowrap',
    } as React.CSSProperties,

    // Tab Bar
    tabBar: {
      display: 'flex',
      backgroundColor: '#16213e',
      borderBottom: '1px solid #0f3460',
      overflowX: 'auto',
      scrollbarWidth: 'none',
    } as React.CSSProperties,

    tab: {
      padding: '10px 18px',
      fontSize: '0.8rem',
      fontWeight: 500,
      color: '#9ca3af',
      background: 'none',
      border: 'none',
      borderBottom: '2px solid transparent',
      cursor: 'pointer',
      whiteSpace: 'nowrap',
      transition: 'color 0.2s, border-color 0.2s',
    } as React.CSSProperties,

    tabActive: {
      color: '#818cf8',
      borderBottomColor: '#818cf8',
    } as React.CSSProperties,

    // Main Content
    mainContent: {
      flex: 1,
      padding: '20px',
      overflowY: 'auto',
    } as React.CSSProperties,

    tabContent: {
      display: 'flex',
      flexDirection: 'column',
      gap: '16px',
    } as React.CSSProperties,

    // Section
    section: {
      marginTop: '8px',
    } as React.CSSProperties,

    sectionTitle: {
      fontSize: '0.9rem',
      fontWeight: 600,
      color: '#c4c9d4',
      marginBottom: '10px',
      paddingBottom: '6px',
      borderBottom: '1px solid #2a2d3a',
    } as React.CSSProperties,

    // Dashboard
    dashboardGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
      gap: '12px',
    } as React.CSSProperties,

    componentCard: {
      backgroundColor: '#16213e',
      borderRadius: '8px',
      padding: '14px',
      border: '1px solid #0f3460',
    } as React.CSSProperties,

    componentCardHeader: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      marginBottom: '10px',
    } as React.CSSProperties,

    componentIcon: {
      fontSize: '1.2rem',
    } as React.CSSProperties,

    componentName: {
      fontSize: '0.85rem',
      fontWeight: 600,
      color: '#e4e6ed',
    } as React.CSSProperties,

    componentCardBody: {
      display: 'flex',
      flexDirection: 'column',
      gap: '6px',
    } as React.CSSProperties,

    metricRow: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '2px 0',
    } as React.CSSProperties,

    metricLabel: {
      fontSize: '0.7rem',
      color: '#6b7280',
      textTransform: 'uppercase',
      letterSpacing: '0.3px',
    } as React.CSSProperties,

    metricValue: {
      fontSize: '0.75rem',
      fontWeight: 500,
      color: '#e4e6ed',
    } as React.CSSProperties,

    // Alert List
    alertList: {
      display: 'flex',
      flexDirection: 'column',
      gap: '6px',
    } as React.CSSProperties,

    alertItem: {
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
      padding: '8px 12px',
      backgroundColor: '#16213e',
      borderRadius: '6px',
      border: '1px solid #0f3460',
      flexWrap: 'wrap',
    } as React.CSSProperties,

    alertComponent: {
      fontSize: '0.75rem',
      fontWeight: 600,
      color: '#c4c9d4',
      minWidth: '100px',
    } as React.CSSProperties,

    alertMessage: {
      fontSize: '0.75rem',
      color: '#9ca3af',
      flex: 1,
    } as React.CSSProperties,

    alertTime: {
      fontSize: '0.65rem',
      color: '#6b7280',
      whiteSpace: 'nowrap',
    } as React.CSSProperties,

    // Quick Actions
    quickActions: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: '10px',
    } as React.CSSProperties,

    actionBtn: {
      padding: '10px 20px',
      borderRadius: '8px',
      border: '1px solid #0f3460',
      backgroundColor: '#16213e',
      color: '#818cf8',
      fontSize: '0.8rem',
      fontWeight: 600,
      cursor: 'pointer',
      transition: 'background-color 0.2s',
    } as React.CSSProperties,

    // Components Tab
    componentRow: {
      backgroundColor: '#16213e',
      borderRadius: '8px',
      border: '1px solid #0f3460',
      overflow: 'hidden',
    } as React.CSSProperties,

    componentRowHeader: {
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      padding: '12px 16px',
      cursor: 'pointer',
      transition: 'background-color 0.15s',
    } as React.CSSProperties,

    componentRowIcon: {
      fontSize: '1.1rem',
    } as React.CSSProperties,

    componentRowName: {
      fontSize: '0.85rem',
      fontWeight: 600,
      color: '#e4e6ed',
      flex: 1,
    } as React.CSSProperties,

    componentRowLatency: {
      fontSize: '0.75rem',
      color: '#9ca3af',
    } as React.CSSProperties,

    expandArrow: {
      fontSize: '0.6rem',
      color: '#6b7280',
    } as React.CSSProperties,

    componentRowDetail: {
      padding: '12px 16px',
      borderTop: '1px solid #0f3460',
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
    } as React.CSSProperties,

    componentActions: {
      display: 'flex',
      gap: '8px',
      marginTop: '4px',
    } as React.CSSProperties,

    smallBtn: {
      padding: '6px 14px',
      borderRadius: '6px',
      border: '1px solid #0f3460',
      backgroundColor: '#1a1a2e',
      color: '#818cf8',
      fontSize: '0.7rem',
      fontWeight: 500,
      cursor: 'pointer',
    } as React.CSSProperties,

    // Resources Tab
    resourceCard: {
      backgroundColor: '#16213e',
      borderRadius: '8px',
      padding: '16px',
      border: '1px solid #0f3460',
    } as React.CSSProperties,

    resourceTitle: {
      fontSize: '0.8rem',
      fontWeight: 600,
      color: '#c4c9d4',
      marginBottom: '10px',
    } as React.CSSProperties,

    gaugeContainer: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: '4px',
    } as React.CSSProperties,

    gaugeValue: {
      fontSize: '1.5rem',
      fontWeight: 700,
      color: '#e4e6ed',
    } as React.CSSProperties,

    barContainer: {
      display: 'flex',
      flexDirection: 'column',
      gap: '6px',
    } as React.CSSProperties,

    barLabel: {
      display: 'flex',
      justifyContent: 'space-between',
      fontSize: '0.7rem',
      color: '#9ca3af',
    } as React.CSSProperties,

    barTrack: {
      width: '100%',
      height: '10px',
      borderRadius: '5px',
      backgroundColor: '#1a1a2e',
      overflow: 'hidden',
    } as React.CSSProperties,

    barFill: {
      height: '100%',
      borderRadius: '5px',
      transition: 'width 0.4s ease',
    } as React.CSSProperties,

    counterDisplay: {
      display: 'flex',
      alignItems: 'baseline',
      gap: '4px',
      justifyContent: 'center',
    } as React.CSSProperties,

    counterValue: {
      fontSize: '1.8rem',
      fontWeight: 700,
      color: '#22c55e',
    } as React.CSSProperties,

    counterMax: {
      fontSize: '0.85rem',
      color: '#6b7280',
    } as React.CSSProperties,

    suggestionItem: {
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
      padding: '8px 0',
    } as React.CSSProperties,

    impactBadge: {
      padding: '2px 8px',
      borderRadius: '4px',
      fontSize: '0.6rem',
      fontWeight: 700,
      color: '#fff',
      textTransform: 'uppercase',
      whiteSpace: 'nowrap',
    } as React.CSSProperties,

    suggestionText: {
      fontSize: '0.75rem',
      color: '#c4c9d4',
    } as React.CSSProperties,

    // Fleet Tab
    fleetFilters: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: '16px',
      marginBottom: '4px',
    } as React.CSSProperties,

    filterGroup: {
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      flexWrap: 'wrap',
    } as React.CSSProperties,

    filterLabel: {
      fontSize: '0.7rem',
      color: '#6b7280',
      textTransform: 'uppercase',
      fontWeight: 600,
    } as React.CSSProperties,

    filterBtn: {
      padding: '4px 10px',
      borderRadius: '4px',
      border: '1px solid #2a2d3a',
      backgroundColor: '#1c1f2e',
      color: '#9ca3af',
      fontSize: '0.7rem',
      cursor: 'pointer',
      transition: 'all 0.15s',
    } as React.CSSProperties,

    filterBtnActive: {
      backgroundColor: '#818cf8',
      borderColor: '#818cf8',
      color: '#fff',
    } as React.CSSProperties,

    fleetGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
      gap: '12px',
    } as React.CSSProperties,

    fleetCard: {
      backgroundColor: '#16213e',
      borderRadius: '8px',
      padding: '14px',
      border: '1px solid #0f3460',
      cursor: 'pointer',
      transition: 'border-color 0.15s',
    } as React.CSSProperties,

    fleetCardSelected: {
      borderColor: '#818cf8',
    } as React.CSSProperties,

    fleetCardHeader: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '10px',
    } as React.CSSProperties,

    fleetCardName: {
      fontSize: '0.85rem',
      fontWeight: 600,
      color: '#e4e6ed',
    } as React.CSSProperties,

    fleetStatusBadge: {
      padding: '2px 8px',
      borderRadius: '4px',
      fontSize: '0.65rem',
      fontWeight: 600,
      textTransform: 'uppercase',
    } as React.CSSProperties,

    fleetCardBody: {
      display: 'flex',
      flexDirection: 'column',
      gap: '4px',
    } as React.CSSProperties,

    fleetCardDetail: {
      marginTop: '10px',
      paddingTop: '10px',
      borderTop: '1px solid #0f3460',
    } as React.CSSProperties,

    // Audit Tab
    auditControls: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: '10px',
      alignItems: 'center',
    } as React.CSSProperties,

    searchInput: {
      flex: '1 1 200px',
      padding: '8px 12px',
      borderRadius: '6px',
      border: '1px solid #2a2d3a',
      backgroundColor: '#1c1f2e',
      color: '#e4e6ed',
      fontSize: '0.8rem',
      outline: 'none',
      boxSizing: 'border-box',
    } as React.CSSProperties,

    filterSelect: {
      padding: '8px 10px',
      borderRadius: '6px',
      border: '1px solid #2a2d3a',
      backgroundColor: '#1c1f2e',
      color: '#e4e6ed',
      fontSize: '0.75rem',
      outline: 'none',
      cursor: 'pointer',
    } as React.CSSProperties,

    exportBtn: {
      padding: '8px 16px',
      borderRadius: '6px',
      border: '1px solid #0f3460',
      backgroundColor: '#16213e',
      color: '#818cf8',
      fontSize: '0.75rem',
      fontWeight: 600,
      cursor: 'pointer',
    } as React.CSSProperties,

    auditTable: {
      backgroundColor: '#16213e',
      borderRadius: '8px',
      border: '1px solid #0f3460',
      overflow: 'hidden',
    } as React.CSSProperties,

    auditTableHeader: {
      display: 'grid',
      gridTemplateColumns: '1.2fr 1fr 1fr 1fr 1.5fr 0.6fr',
      padding: '10px 14px',
      backgroundColor: '#0f3460',
      gap: '8px',
    } as React.CSSProperties,

    auditTh: {
      fontSize: '0.65rem',
      fontWeight: 700,
      color: '#9ca3af',
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
    } as React.CSSProperties,

    auditRow: {
      display: 'grid',
      gridTemplateColumns: '1.2fr 1fr 1fr 1fr 1.5fr 0.6fr',
      padding: '9px 14px',
      borderBottom: '1px solid #0f3460',
      gap: '8px',
      alignItems: 'center',
    } as React.CSSProperties,

    auditTd: {
      fontSize: '0.7rem',
      color: '#c4c9d4',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
    } as React.CSSProperties,

    auditTdDetail: {
      fontSize: '0.7rem',
      color: '#9ca3af',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
    } as React.CSSProperties,

    auditSeverity: {
      fontWeight: 700,
      textTransform: 'uppercase',
      fontSize: '0.65rem',
    } as React.CSSProperties,

    pagination: {
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      gap: '14px',
      padding: '8px 0',
    } as React.CSSProperties,

    pageBtn: {
      padding: '6px 14px',
      borderRadius: '6px',
      border: '1px solid #0f3460',
      backgroundColor: '#16213e',
      color: '#818cf8',
      fontSize: '0.75rem',
      cursor: 'pointer',
    } as React.CSSProperties,

    pageInfo: {
      fontSize: '0.7rem',
      color: '#6b7280',
    } as React.CSSProperties,

    // Features Tab
    featureCard: {
      backgroundColor: '#16213e',
      borderRadius: '8px',
      padding: '16px',
      border: '1px solid #0f3460',
    } as React.CSSProperties,

    featureHeader: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '12px',
    } as React.CSSProperties,

    featureInfo: {
      display: 'flex',
      flexDirection: 'column',
      gap: '4px',
      flex: 1,
    } as React.CSSProperties,

    featureName: {
      fontSize: '0.9rem',
      fontWeight: 600,
      color: '#e4e6ed',
    } as React.CSSProperties,

    featureDesc: {
      fontSize: '0.75rem',
      color: '#9ca3af',
    } as React.CSSProperties,

    featureBody: {
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
    } as React.CSSProperties,

    toggleSwitch: {
      width: '44px',
      height: '24px',
      borderRadius: '12px',
      border: 'none',
      cursor: 'pointer',
      padding: 0,
      position: 'relative',
      transition: 'background-color 0.2s',
      flexShrink: 0,
    } as React.CSSProperties,

    toggleKnob: {
      width: '20px',
      height: '20px',
      borderRadius: '50%',
      backgroundColor: '#fff',
      display: 'block',
      transition: 'transform 0.2s',
    } as React.CSSProperties,

    rolloutSection: {
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
    } as React.CSSProperties,

    rolloutSlider: {
      flex: 1,
      accentColor: '#818cf8',
      cursor: 'pointer',
    } as React.CSSProperties,

    rolloutValue: {
      fontSize: '0.8rem',
      fontWeight: 600,
      color: '#818cf8',
      minWidth: '36px',
      textAlign: 'right',
    } as React.CSSProperties,

    // Analytics Tab
    analyticsControls: {
      display: 'flex',
      gap: '8px',
      marginBottom: '4px',
    } as React.CSSProperties,

    chartCard: {
      backgroundColor: '#16213e',
      borderRadius: '8px',
      padding: '16px',
      border: '1px solid #0f3460',
    } as React.CSSProperties,

    chartTitle: {
      fontSize: '0.85rem',
      fontWeight: 600,
      color: '#c4c9d4',
      marginBottom: '12px',
    } as React.CSSProperties,

    chartContainer: {
      display: 'flex',
      alignItems: 'flex-end',
      gap: '2px',
      height: '120px',
      padding: '0 4px',
    } as React.CSSProperties,

    barChartItem: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      height: '100%',
      justifyContent: 'flex-end',
    } as React.CSSProperties,

    barChartBar: {
      width: '100%',
      maxWidth: '20px',
      borderRadius: '2px 2px 0 0',
      minHeight: '2px',
      transition: 'height 0.3s ease',
    } as React.CSSProperties,

    barChartLabel: {
      fontSize: '0.5rem',
      color: '#6b7280',
      marginTop: '4px',
      writingMode: 'vertical-rl',
      textOrientation: 'mixed',
      transform: 'rotate(0deg)',
    } as React.CSSProperties,

    costBreakdown: {
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
    } as React.CSSProperties,

    costItem: {
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
    } as React.CSSProperties,

    costCategory: {
      fontSize: '0.75rem',
      color: '#c4c9d4',
      minWidth: '90px',
    } as React.CSSProperties,

    costBarTrack: {
      flex: 1,
      height: '8px',
      borderRadius: '4px',
      backgroundColor: '#1a1a2e',
      overflow: 'hidden',
    } as React.CSSProperties,

    costBarFill: {
      height: '100%',
      borderRadius: '4px',
      backgroundColor: '#818cf8',
      transition: 'width 0.4s ease',
    } as React.CSSProperties,

    costValue: {
      fontSize: '0.75rem',
      fontWeight: 600,
      color: '#e4e6ed',
      minWidth: '60px',
      textAlign: 'right',
    } as React.CSSProperties,

    topAgentsList: {
      display: 'flex',
      flexDirection: 'column',
      gap: '6px',
    } as React.CSSProperties,

    topAgentRow: {
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
      padding: '6px 0',
    } as React.CSSProperties,

    topAgentRank: {
      fontSize: '0.75rem',
      fontWeight: 700,
      color: '#818cf8',
      minWidth: '28px',
    } as React.CSSProperties,

    topAgentName: {
      fontSize: '0.8rem',
      color: '#e4e6ed',
      flex: 1,
    } as React.CSSProperties,

    topAgentRequests: {
      fontSize: '0.7rem',
      color: '#9ca3af',
    } as React.CSSProperties,

    // Diagnostics Tab
    diagnosticsActions: {
      marginBottom: '8px',
    } as React.CSSProperties,

    diagnosticsBtn: {
      padding: '12px 28px',
      borderRadius: '8px',
      border: 'none',
      backgroundColor: '#818cf8',
      color: '#fff',
      fontSize: '0.85rem',
      fontWeight: 600,
      cursor: 'pointer',
      transition: 'opacity 0.2s',
    } as React.CSSProperties,

    diagnosticsResultItem: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: '10px',
      padding: '10px 0',
      borderBottom: '1px solid #0f3460',
    } as React.CSSProperties,

    diagnosticsResultIcon: {
      fontSize: '1rem',
      fontWeight: 700,
      width: '22px',
      textAlign: 'center',
      flexShrink: 0,
      marginTop: '1px',
    } as React.CSSProperties,

    diagnosticsResultInfo: {
      display: 'flex',
      flexDirection: 'column',
      gap: '3px',
      flex: 1,
    } as React.CSSProperties,

    diagnosticsResultComponent: {
      fontSize: '0.8rem',
      fontWeight: 600,
      color: '#e4e6ed',
    } as React.CSSProperties,

    diagnosticsResultMessage: {
      fontSize: '0.7rem',
      color: '#c4c9d4',
    } as React.CSSProperties,

    diagnosticsResultDetails: {
      fontSize: '0.65rem',
      color: '#6b7280',
    } as React.CSSProperties,

    diagnosticsResultStatus: {
      fontSize: '0.7rem',
      fontWeight: 700,
      textTransform: 'uppercase',
      whiteSpace: 'nowrap',
    } as React.CSSProperties,

    recommendationItem: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: '8px',
      padding: '6px 0',
    } as React.CSSProperties,

    recommendationBullet: {
      color: '#818cf8',
      fontSize: '0.8rem',
      lineHeight: '1.4',
    } as React.CSSProperties,

    recommendationText: {
      fontSize: '0.75rem',
      color: '#c4c9d4',
    } as React.CSSProperties,

    // Empty State
    emptyState: {
      padding: '30px',
      textAlign: 'center',
      color: '#6b7280',
      fontSize: '0.85rem',
      backgroundColor: '#16213e',
      borderRadius: '8px',
      border: '1px solid #0f3460',
    } as React.CSSProperties,
  } as const;


  const toast = useToast();

  // Top-level state
  const [activeTab, setActiveTab] = useState<TabId>('dashboard');
  const [health, setHealth] = useState<PlatformHealth | null>(null);
  const [resources, setResources] = useState<ResourceSnapshot | null>(null);
  const [fleet, setFleet] = useState<FleetAgent[]>([]);
  const [audit, setAudit] = useState<AuditResponse | null>(null);
  const [features, setFeatures] = useState<FeatureFlag[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [costs, setCosts] = useState<CostData | null>(null);
  const [diagnosticsReport, setDiagnosticsReport] = useState<DiagnosticsReport | null>(null);

  // UI state
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(15000);
  const [diagnosticsLoading, setDiagnosticsLoading] = useState(false);
  const [auditSearch, setAuditSearch] = useState('');
  const [auditComponentFilter, setAuditComponentFilter] = useState('');
  const [auditSeverityFilter, setAuditSeverityFilter] = useState<SeverityLevel | ''>('');
  const [auditPage, setAuditPage] = useState(1);
  const [fleetStatusFilter, setFleetStatusFilter] = useState<FleetStatus | 'all'>('all');
  const [fleetRoleFilter, setFleetRoleFilter] = useState<FleetRole | 'all'>('all');
  const [selectedFleetAgent, setSelectedFleetAgent] = useState<FleetAgent | null>(null);
  const [analyticsDays, setAnalyticsDays] = useState(30);
  const [expandedComponent, setExpandedComponent] = useState<string | null>(null);
  const [updatingFeature, setUpdatingFeature] = useState<string | null>(null);
  const [costDays, setCostDays] = useState(30);

  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Data Fetching ──

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch('/api/platform-console/health');
      if (res.ok) {
        const data: PlatformHealth = await res.json();
        setHealth(data);
      }
    } catch {
      // Silently handle – health check may be unavailable
    }
  }, []);

  const fetchResources = useCallback(async () => {
    try {
      const res = await fetch('/api/platform-console/resources');
      if (res.ok) {
        const data: ResourceSnapshot = await res.json();
        setResources(data);
      }
    } catch {
      // Silently handle
    }
  }, []);

  const fetchFleet = useCallback(async () => {
    try {
      const res = await fetch('/api/platform-console/fleet');
      if (res.ok) {
        const data: FleetResponse = await res.json();
        setFleet(data.agents || []);
      }
    } catch {
      // Silently handle
    }
  }, []);

  const fetchAudit = useCallback(async (page: number, search: string, component: string, severity: string) => {
    try {
      const qs = new URLSearchParams();
      qs.set('page', String(page));
      qs.set('page_size', String(AUDIT_PAGE_SIZE));
      if (search) qs.set('search', search);
      if (component) qs.set('component', component);
      if (severity) qs.set('severity', severity);
      const res = await fetch(`/api/platform-console/audit?${qs.toString()}`);
      if (res.ok) {
        const data: AuditResponse = await res.json();
        setAudit(data);
      }
    } catch {
      // Silently handle
    }
  }, []);

  const fetchFeatures = useCallback(async () => {
    try {
      const res = await fetch('/api/platform-console/features');
      if (res.ok) {
        const data: FeatureFlag[] = await res.json();
        setFeatures(data);
      }
    } catch {
      // Silently handle
    }
  }, []);

  const fetchAnalytics = useCallback(async (days: number) => {
    try {
      const res = await fetch(`/api/platform-console/analytics?days=${days}`);
      if (res.ok) {
        const data: AnalyticsData = await res.json();
        setAnalytics(data);
      }
    } catch {
      // Silently handle
    }
  }, []);

  const fetchCosts = useCallback(async (days: number) => {
    try {
      const res = await fetch(`/api/platform-console/costs?days=${days}`);
      if (res.ok) {
        const data: CostData = await res.json();
        setCosts(data);
      }
    } catch {
      // Silently handle
    }
  }, []);

  const loadAllData = useCallback(async () => {
    setLoading(true);
    await Promise.all([
      fetchHealth(),
      fetchResources(),
      fetchFleet(),
      fetchFeatures(),
      fetchAudit(1, '', '', ''),
      fetchAnalytics(analyticsDays),
      fetchCosts(costDays),
    ]);
    setLoading(false);
  }, [fetchHealth, fetchResources, fetchFleet, fetchFeatures, fetchAudit, fetchAnalytics, fetchCosts, analyticsDays, costDays]);

  // Initial load
  useEffect(() => {
    loadAllData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh
  useEffect(() => {
    if (refreshTimer.current) {
      clearInterval(refreshTimer.current);
      refreshTimer.current = null;
    }
    if (autoRefresh && refreshInterval > 0) {
      refreshTimer.current = setInterval(() => {
        fetchHealth();
        fetchResources();
        fetchFleet();
      }, refreshInterval);
    }
    return () => {
      if (refreshTimer.current) {
        clearInterval(refreshTimer.current);
      }
    };
  }, [autoRefresh, refreshInterval, fetchHealth, fetchResources, fetchFleet]);

  // Refetch audit when filters change
  useEffect(() => {
    fetchAudit(auditPage, auditSearch, auditComponentFilter, auditSeverityFilter);
  }, [auditPage, auditSearch, auditComponentFilter, auditSeverityFilter, fetchAudit]);

  // Refetch analytics when days change
  useEffect(() => {
    fetchAnalytics(analyticsDays);
  }, [analyticsDays, fetchAnalytics]);

  useEffect(() => {
    fetchCosts(costDays);
  }, [costDays, fetchCosts]);

  // ── Handlers ──

  const handleTabChange = useCallback((tab: TabId) => {
    setActiveTab(tab);
    onNavigate?.(tab);
  }, [onNavigate]);

  const handleRunDiagnostics = useCallback(async () => {
    setDiagnosticsLoading(true);
    try {
      const res = await fetch('/api/platform-console/diagnostics', { method: 'POST' });
      if (res.ok) {
        const data: DiagnosticsReport = await res.json();
        setDiagnosticsReport(data);
        toast.success('Diagnostics completed successfully');
      } else {
        toast.error('Diagnostics failed');
      }
    } catch {
      toast.error('Failed to run diagnostics');
    } finally {
      setDiagnosticsLoading(false);
    }
  }, [toast]);

  const handleToggleFeature = useCallback(async (featureId: string, enabled: boolean) => {
    setUpdatingFeature(featureId);
    try {
      await fetch(`/api/platform-console/features/${featureId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      setFeatures((prev) =>
        prev.map((f) => (f.id === featureId ? { ...f, enabled } : f))
      );
      toast.success(`Feature ${enabled ? 'enabled' : 'disabled'}`);
    } catch {
      toast.error('Failed to update feature flag');
    } finally {
      setUpdatingFeature(null);
    }
  }, [toast]);

  const handleRolloutChange = useCallback(async (featureId: string, percentage: number) => {
    setUpdatingFeature(featureId);
    try {
      await fetch(`/api/platform-console/features/${featureId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rollout_percentage: percentage }),
      });
      setFeatures((prev) =>
        prev.map((f) => (f.id === featureId ? { ...f, rollout_percentage: percentage } : f))
      );
    } catch {
      toast.error('Failed to update rollout percentage');
    } finally {
      setUpdatingFeature(null);
    }
  }, [toast]);

  const handleQuickAction = useCallback(async (action: string) => {
    switch (action) {
      case 'diagnostics':
        handleTabChange('diagnostics');
        break;
      case 'optimize':
        toast.info('Resource optimization initiated');
        break;
      case 'maintenance':
        toast.info('Maintenance mode triggered');
        break;
      default:
        break;
    }
  }, [handleTabChange, toast]);

  // ── Derived Data ──

  const overallStatus: HealthStatus = health?.status || 'offline';

  const filteredFleet = useMemo(() => {
    return fleet.filter((a) => {
      if (fleetStatusFilter !== 'all' && a.status !== fleetStatusFilter) return false;
      if (fleetRoleFilter !== 'all' && a.role !== fleetRoleFilter) return false;
      return true;
    });
  }, [fleet, fleetStatusFilter, fleetRoleFilter]);

  const auditTotalPages = audit ? Math.ceil(audit.total / AUDIT_PAGE_SIZE) : 1;

  const components: ComponentHealth[] = health?.components || DEFAULT_COMPONENTS.map((c) => ({
    id: c.id,
    name: c.name,
    icon: c.icon,
    status: 'offline' as HealthStatus,
    latency_ms: 0,
    error_count: 0,
    last_checked: '',
    history: [],
    metrics: [],
  }));

  // ── Render Helpers ──

  const renderStatusBadge = (status: HealthStatus, label?: string) => (
    <span style={{
      ...styles.statusBadge,
      backgroundColor: `${HEALTH_COLORS[status]}22`,
      color: HEALTH_COLORS[status],
      borderColor: HEALTH_COLORS[status],
    }}>
      <span style={{
        ...styles.statusDot,
        backgroundColor: HEALTH_COLORS[status],
      }} />
      {label || HEALTH_LABELS[status]}
    </span>
  );

  const renderSeverityBadge = (severity: AlertSeverity) => (
    <span style={{
      ...styles.severityBadge,
      backgroundColor: `${ALERT_SEVERITY_COLORS[severity]}22`,
      color: ALERT_SEVERITY_COLORS[severity],
    }}>
      {severity.toUpperCase()}
    </span>
  );

  const renderSparkline = (data: number[], color: string) => {
    if (!data || data.length === 0) return null;
    const max = Math.max(...data, 1);
    const min = Math.min(...data, 0);
    const range = max - min || 1;
    const width = 80;
    const height = 24;
    const points = data.map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 2) - 1;
      return `${x},${y}`;
    }).join(' ');
    return (
      <svg width={width} height={height} style={{ display: 'block' }}>
        <polyline
          points={points}
          fill="none"
          stroke={color}
          strokeWidth="1.5"
        />
      </svg>
    );
  };

  // ── Tab Content Renderers ──

  const renderDashboardTab = () => (
    <div style={styles.tabContent}>
      {/* Component Health Cards */}
      <div style={styles.dashboardGrid}>
        {components.map((comp) => (
          <div key={comp.id} style={styles.componentCard}>
            <div style={styles.componentCardHeader}>
              <span style={styles.componentIcon}>{comp.icon}</span>
              <span style={styles.componentName}>{comp.name}</span>
            </div>
            <div style={styles.componentCardBody}>
              {renderStatusBadge(comp.status)}
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Latency</span>
                <span style={styles.metricValue}>{comp.latency_ms}ms</span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Errors</span>
                <span style={styles.metricValue}>{comp.error_count}</span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Last Checked</span>
                <span style={styles.metricValue}>
                  {comp.last_checked ? formatTimestamp(comp.last_checked) : 'N/A'}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Active Alerts */}
      {health?.alerts && health.alerts.length > 0 && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Active Alerts</h3>
          <div style={styles.alertList}>
            {health.alerts.map((alert) => (
              <div key={alert.id} style={styles.alertItem}>
                {renderSeverityBadge(alert.severity)}
                <span style={styles.alertComponent}>{alert.component}</span>
                <span style={styles.alertMessage}>{alert.message}</span>
                <span style={styles.alertTime}>{formatTimestamp(alert.created_at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Quick Actions</h3>
        <div style={styles.quickActions}>
          <button
            style={styles.actionBtn}
            onClick={() => handleQuickAction('diagnostics')}
          >
            Run Diagnostics
          </button>
          <button
            style={styles.actionBtn}
            onClick={() => handleQuickAction('optimize')}
          >
            Optimize Resources
          </button>
          <button
            style={styles.actionBtn}
            onClick={() => handleQuickAction('maintenance')}
          >
            Trigger Maintenance
          </button>
        </div>
      </div>
    </div>
  );

  const renderComponentsTab = () => (
    <div style={styles.tabContent}>
      {components.map((comp) => (
        <div key={comp.id} style={styles.componentRow}>
          <div
            style={styles.componentRowHeader}
            onClick={() => setExpandedComponent(expandedComponent === comp.id ? null : comp.id)}
          >
            <span style={styles.componentRowIcon}>{comp.icon}</span>
            <span style={styles.componentRowName}>{comp.name}</span>
            {renderStatusBadge(comp.status)}
            <span style={styles.componentRowLatency}>{comp.latency_ms}ms</span>
            {comp.history && comp.history.length > 0 && renderSparkline(comp.history, HEALTH_COLORS[comp.status])}
            <span style={styles.expandArrow}>
              {expandedComponent === comp.id ? '\u25B2' : '\u25BC'}
            </span>
          </div>
          {expandedComponent === comp.id && (
            <div style={styles.componentRowDetail}>
              {comp.metrics && comp.metrics.map((m: ComponentMetric, i: number) => (
                <div key={i} style={styles.metricRow}>
                  <span style={styles.metricLabel}>{m.label}</span>
                  <span style={{
                    ...styles.metricValue,
                    color: HEALTH_COLORS[m.status as HealthStatus],
                  }}>
                    {m.value}
                  </span>
                </div>
              ))}
              <div style={styles.componentActions}>
                <button style={styles.smallBtn}>Restart</button>
                <button style={styles.smallBtn}>View Logs</button>
                <button style={styles.smallBtn}>Configure</button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );

  const renderResourcesTab = () => (
    <div style={styles.tabContent}>
      {resources ? (
        <>
          {/* CPU Gauge */}
          <div style={styles.resourceCard}>
            <h4 style={styles.resourceTitle}>CPU Usage</h4>
            <div style={styles.gaugeContainer}>
              <svg width="120" height="70" viewBox="0 0 120 70">
                <path
                  d="M 10 60 A 50 50 0 0 1 110 60"
                  fill="none"
                  stroke="#2a2d3a"
                  strokeWidth="12"
                  strokeLinecap="round"
                />
                <path
                  d="M 10 60 A 50 50 0 0 1 110 60"
                  fill="none"
                  stroke={resources.cpu_percent > 80 ? '#ef4444' : resources.cpu_percent > 60 ? '#f59e0b' : '#22c55e'}
                  strokeWidth="12"
                  strokeLinecap="round"
                  strokeDasharray={`${(resources.cpu_percent / 100) * 157} 157`}
                />
              </svg>
              <span style={styles.gaugeValue}>{resources.cpu_percent}%</span>
            </div>
          </div>

          {/* Memory */}
          <div style={styles.resourceCard}>
            <h4 style={styles.resourceTitle}>Memory</h4>
            <div style={styles.barContainer}>
              <div style={styles.barLabel}>
                <span>{resources.memory_used_gb} GB / {resources.memory_total_gb} GB</span>
                <span>{resources.memory_percent}%</span>
              </div>
              <div style={styles.barTrack}>
                <div style={{
                  ...styles.barFill,
                  width: `${resources.memory_percent}%`,
                  backgroundColor: resources.memory_percent > 80 ? '#ef4444' : resources.memory_percent > 60 ? '#f59e0b' : '#22c55e',
                }} />
              </div>
            </div>
          </div>

          {/* Disk */}
          <div style={styles.resourceCard}>
            <h4 style={styles.resourceTitle}>Disk</h4>
            <div style={styles.barContainer}>
              <div style={styles.barLabel}>
                <span>{resources.disk_used_gb} GB / {resources.disk_total_gb} GB</span>
                <span>{resources.disk_percent}%</span>
              </div>
              <div style={styles.barTrack}>
                <div style={{
                  ...styles.barFill,
                  width: `${resources.disk_percent}%`,
                  backgroundColor: resources.disk_percent > 85 ? '#ef4444' : resources.disk_percent > 70 ? '#f59e0b' : '#22c55e',
                }} />
              </div>
            </div>
          </div>

          {/* Connections */}
          <div style={styles.resourceCard}>
            <h4 style={styles.resourceTitle}>Connections</h4>
            <div style={styles.counterDisplay}>
              <span style={styles.counterValue}>{resources.active_connections}</span>
              <span style={styles.counterMax}>/ {resources.max_connections}</span>
            </div>
          </div>

          {/* Queue Depth */}
          <div style={styles.resourceCard}>
            <h4 style={styles.resourceTitle}>Queue Depth</h4>
            <div style={styles.counterDisplay}>
              <span style={{
                ...styles.counterValue,
                color: resources.queue_depth > 100 ? '#ef4444' : resources.queue_depth > 50 ? '#f59e0b' : '#22c55e',
              }}>
                {resources.queue_depth}
              </span>
            </div>
          </div>

          {/* Token Usage */}
          <div style={styles.resourceCard}>
            <h4 style={styles.resourceTitle}>Token Usage</h4>
            <div style={styles.barContainer}>
              <div style={styles.barLabel}>
                <span>{formatNumber(resources.tokens_used)} / {formatNumber(resources.tokens_total)}</span>
                <span>{resources.tokens_total > 0 ? Math.round((resources.tokens_used / resources.tokens_total) * 100) : 0}%</span>
              </div>
              <div style={styles.barTrack}>
                <div style={{
                  ...styles.barFill,
                  width: resources.tokens_total > 0 ? `${(resources.tokens_used / resources.tokens_total) * 100}%` : '0%',
                  backgroundColor: '#818cf8',
                }} />
              </div>
            </div>
          </div>

          {/* Suggestions */}
          {resources.suggestions && resources.suggestions.length > 0 && (
            <div style={styles.section}>
              <h4 style={styles.resourceTitle}>Optimization Suggestions</h4>
              {resources.suggestions.map((s) => (
                <div key={s.id} style={styles.suggestionItem}>
                  <span style={{
                    ...styles.impactBadge,
                    backgroundColor: s.impact === 'high' ? '#ef4444' : s.impact === 'medium' ? '#f59e0b' : '#3b82f6',
                  }}>
                    {s.impact}
                  </span>
                  <span style={styles.suggestionText}>{s.message}</span>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <div style={styles.emptyState}>No resource data available</div>
      )}
    </div>
  );

  const renderFleetTab = () => (
    <div style={styles.tabContent}>
      {/* Filters */}
      <div style={styles.fleetFilters}>
        <div style={styles.filterGroup}>
          <span style={styles.filterLabel}>Status:</span>
          {(['all', 'active', 'idle', 'offline', 'error'] as const).map((s) => (
            <button
              key={s}
              style={{
                ...styles.filterBtn,
                ...(fleetStatusFilter === s ? styles.filterBtnActive : {}),
              }}
              onClick={() => setFleetStatusFilter(s)}
            >
              {s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
        <div style={styles.filterGroup}>
          <span style={styles.filterLabel}>Role:</span>
          {(['all', 'orchestrator', 'worker', 'specialist', 'monitor', 'gateway'] as const).map((r) => (
            <button
              key={r}
              style={{
                ...styles.filterBtn,
                ...(fleetRoleFilter === r ? styles.filterBtnActive : {}),
              }}
              onClick={() => setFleetRoleFilter(r)}
            >
              {r === 'all' ? 'All' : FLEET_ROLE_LABELS[r]}
            </button>
          ))}
        </div>
      </div>

      {/* Agent Grid */}
      <div style={styles.fleetGrid}>
        {filteredFleet.map((agent) => (
          <div
            key={agent.id}
            style={{
              ...styles.fleetCard,
              ...(selectedFleetAgent?.id === agent.id ? styles.fleetCardSelected : {}),
            }}
            onClick={() => setSelectedFleetAgent(selectedFleetAgent?.id === agent.id ? null : agent)}
          >
            <div style={styles.fleetCardHeader}>
              <span style={styles.fleetCardName}>{agent.name}</span>
              <span style={{
                ...styles.fleetStatusBadge,
                backgroundColor: `${FLEET_STATUS_COLORS[agent.status]}22`,
                color: FLEET_STATUS_COLORS[agent.status],
              }}>
                {agent.status}
              </span>
            </div>
            <div style={styles.fleetCardBody}>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Role</span>
                <span style={styles.metricValue}>{FLEET_ROLE_LABELS[agent.role]}</span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Version</span>
                <span style={styles.metricValue}>{agent.version}</span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Uptime</span>
                <span style={styles.metricValue}>{formatDuration(agent.uptime_seconds)}</span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Task</span>
                <span style={styles.metricValue}>{agent.current_task || 'None'}</span>
              </div>
            </div>
            {selectedFleetAgent?.id === agent.id && (
              <div style={styles.fleetCardDetail}>
                <div style={styles.metricRow}>
                  <span style={styles.metricLabel}>Last Heartbeat</span>
                  <span style={styles.metricValue}>{formatTimestamp(agent.last_heartbeat)}</span>
                </div>
              </div>
            )}
          </div>
        ))}
        {filteredFleet.length === 0 && (
          <div style={styles.emptyState}>No agents match the current filters</div>
        )}
      </div>
    </div>
  );

  const renderAuditTab = () => (
    <div style={styles.tabContent}>
      {/* Search and Filters */}
      <div style={styles.auditControls}>
        <input
          style={styles.searchInput}
          placeholder="Search audit logs..."
          value={auditSearch}
          onChange={(e) => { setAuditSearch(e.target.value); setAuditPage(1); }}
        />
        <select
          style={styles.filterSelect}
          value={auditComponentFilter}
          onChange={(e) => { setAuditComponentFilter(e.target.value); setAuditPage(1); }}
        >
          <option value="">All Components</option>
          {DEFAULT_COMPONENTS.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <select
          style={styles.filterSelect}
          value={auditSeverityFilter}
          onChange={(e) => { setAuditSeverityFilter(e.target.value as SeverityLevel | ''); setAuditPage(1); }}
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="error">Error</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
        </select>
        <button style={styles.exportBtn}>Export</button>
      </div>

      {/* Table */}
      <div style={styles.auditTable}>
        <div style={styles.auditTableHeader}>
          <span style={styles.auditTh}>Timestamp</span>
          <span style={styles.auditTh}>Component</span>
          <span style={styles.auditTh}>Action</span>
          <span style={styles.auditTh}>Agent</span>
          <span style={styles.auditTh}>Detail</span>
          <span style={styles.auditTh}>Severity</span>
        </div>
        {audit?.entries.map((entry) => (
          <div key={entry.id} style={styles.auditRow}>
            <span style={styles.auditTd}>{formatTimestamp(entry.timestamp)}</span>
            <span style={styles.auditTd}>{entry.component}</span>
            <span style={styles.auditTd}>{entry.action}</span>
            <span style={styles.auditTd}>{entry.agent}</span>
            <span style={styles.auditTdDetail}>{entry.detail}</span>
            <span style={styles.auditTd}>
              <span style={{
                ...styles.auditSeverity,
                color: SEVERITY_COLORS[entry.severity],
              }}>
                {entry.severity}
              </span>
            </span>
          </div>
        ))}
        {(!audit || audit.entries.length === 0) && (
          <div style={styles.emptyState}>No audit entries found</div>
        )}
      </div>

      {/* Pagination */}
      {audit && audit.total > 0 && (
        <div style={styles.pagination}>
          <button
            style={styles.pageBtn}
            disabled={auditPage <= 1}
            onClick={() => setAuditPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </button>
          <span style={styles.pageInfo}>
            Page {auditPage} of {auditTotalPages} ({audit.total} entries)
          </span>
          <button
            style={styles.pageBtn}
            disabled={auditPage >= auditTotalPages}
            onClick={() => setAuditPage((p) => Math.min(auditTotalPages, p + 1))}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );

  const renderFeaturesTab = () => (
    <div style={styles.tabContent}>
      {features.map((flag) => (
        <div key={flag.id} style={styles.featureCard}>
          <div style={styles.featureHeader}>
            <div style={styles.featureInfo}>
              <span style={styles.featureName}>{flag.name}</span>
              <span style={styles.featureDesc}>{flag.description}</span>
            </div>
            <button
              style={{
                ...styles.toggleSwitch,
                backgroundColor: flag.enabled ? '#22c55e' : '#374151',
              }}
              onClick={() => handleToggleFeature(flag.id, !flag.enabled)}
              disabled={updatingFeature === flag.id}
            >
              <span style={{
                ...styles.toggleKnob,
                transform: flag.enabled ? 'translateX(20px)' : 'translateX(2px)',
              }} />
            </button>
          </div>
          <div style={styles.featureBody}>
            <div style={styles.rolloutSection}>
              <span style={styles.metricLabel}>Rollout</span>
              <input
                type="range"
                min="0"
                max="100"
                value={flag.rollout_percentage}
                onChange={(e) => handleRolloutChange(flag.id, parseInt(e.target.value, 10))}
                disabled={updatingFeature === flag.id}
                style={styles.rolloutSlider}
              />
              <span style={styles.rolloutValue}>{flag.rollout_percentage}%</span>
            </div>
            <div style={styles.metricRow}>
              <span style={styles.metricLabel}>Target Agents</span>
              <span style={styles.metricValue}>
                {flag.target_agents.length > 0 ? flag.target_agents.join(', ') : 'All agents'}
              </span>
            </div>
            <div style={styles.metricRow}>
              <span style={styles.metricLabel}>Created</span>
              <span style={styles.metricValue}>{formatTimestamp(flag.created_at)}</span>
            </div>
          </div>
        </div>
      ))}
      {features.length === 0 && (
        <div style={styles.emptyState}>No feature flags configured</div>
      )}
    </div>
  );

  const renderAnalyticsTab = () => (
    <div style={styles.tabContent}>
      {/* Time Range Selector */}
      <div style={styles.analyticsControls}>
        {ANALYTICS_DAYS_OPTIONS.map((d) => (
          <button
            key={d}
            style={{
              ...styles.filterBtn,
              ...(analyticsDays === d ? styles.filterBtnActive : {}),
            }}
            onClick={() => setAnalyticsDays(d)}
          >
            {d === 7 ? '7d' : d === 30 ? '30d' : '90d'}
          </button>
        ))}
      </div>

      {analytics ? (
        <>
          {/* Request Volume Chart */}
          <div style={styles.chartCard}>
            <h4 style={styles.chartTitle}>Request Volume</h4>
            <div style={styles.chartContainer}>
              {analytics.request_volume.map((item, i) => {
                const maxCount = Math.max(...analytics.request_volume.map((d) => d.count), 1);
                const height = (item.count / maxCount) * 100;
                return (
                  <div key={i} style={styles.barChartItem}>
                    <div style={{
                      ...styles.barChartBar,
                      height: `${height}%`,
                      backgroundColor: '#818cf8',
                    }} />
                    <span style={styles.barChartLabel}>{item.date}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Error Rate Trend */}
          <div style={styles.chartCard}>
            <h4 style={styles.chartTitle}>Error Rate Trend</h4>
            <div style={styles.chartContainer}>
              {analytics.error_rate_trend.map((item, i) => {
                const maxRate = Math.max(...analytics.error_rate_trend.map((d) => d.rate), 0.01);
                const height = (item.rate / maxRate) * 100;
                return (
                  <div key={i} style={styles.barChartItem}>
                    <div style={{
                      ...styles.barChartBar,
                      height: `${height}%`,
                      backgroundColor: item.rate > 5 ? '#ef4444' : '#f59e0b',
                    }} />
                    <span style={styles.barChartLabel}>{item.date}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Cost Breakdown */}
          {costs && (
            <div style={styles.chartCard}>
              <h4 style={styles.chartTitle}>
                Cost Breakdown (Total: ${costs.total_cost.toFixed(2)})
              </h4>
              <div style={styles.costBreakdown}>
                {costs.breakdown.map((item, i) => (
                  <div key={i} style={styles.costItem}>
                    <span style={styles.costCategory}>{item.category}</span>
                    <div style={styles.costBarTrack}>
                      <div style={{
                        ...styles.costBarFill,
                        width: `${item.percentage}%`,
                      }} />
                    </div>
                    <span style={styles.costValue}>${item.cost.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Agents */}
          <div style={styles.chartCard}>
            <h4 style={styles.chartTitle}>Top Agents by Usage</h4>
            <div style={styles.topAgentsList}>
              {analytics.top_agents.map((agent, i) => (
                <div key={i} style={styles.topAgentRow}>
                  <span style={styles.topAgentRank}>#{i + 1}</span>
                  <span style={styles.topAgentName}>{agent.name}</span>
                  <span style={styles.topAgentRequests}>{formatNumber(agent.requests)} requests</span>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : (
        <div style={styles.emptyState}>No analytics data available</div>
      )}
    </div>
  );

  const renderDiagnosticsTab = () => (
    <div style={styles.tabContent}>
      <div style={styles.diagnosticsActions}>
        <button
          style={styles.diagnosticsBtn}
          onClick={handleRunDiagnostics}
          disabled={diagnosticsLoading}
        >
          {diagnosticsLoading ? 'Running Diagnostics...' : 'Run Diagnostics'}
        </button>
      </div>

      {diagnosticsReport && (
        <>
          {/* Results */}
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>Results</h3>
            {diagnosticsReport.results.map((result, i) => (
              <div key={i} style={styles.diagnosticsResultItem}>
                <span style={{
                  ...styles.diagnosticsResultIcon,
                  color: DIAGNOSTICS_RESULT_COLORS[result.status],
                }}>
                  {DIAGNOSTICS_RESULT_ICONS[result.status]}
                </span>
                <div style={styles.diagnosticsResultInfo}>
                  <span style={styles.diagnosticsResultComponent}>{result.component}</span>
                  <span style={styles.diagnosticsResultMessage}>{result.message}</span>
                  {result.details && (
                    <span style={styles.diagnosticsResultDetails}>{result.details}</span>
                  )}
                </div>
                <span style={{
                  ...styles.diagnosticsResultStatus,
                  color: DIAGNOSTICS_RESULT_COLORS[result.status],
                }}>
                  {result.status}
                </span>
              </div>
            ))}
          </div>

          {/* Recommendations */}
          {diagnosticsReport.recommendations.length > 0 && (
            <div style={styles.section}>
              <h3 style={styles.sectionTitle}>Recommendations</h3>
              {diagnosticsReport.recommendations.map((rec, i) => (
                <div key={i} style={styles.recommendationItem}>
                  <span style={styles.recommendationBullet}>{'\u2022'}</span>
                  <span style={styles.recommendationText}>{rec}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {!diagnosticsReport && !diagnosticsLoading && (
        <div style={styles.emptyState}>
          Click "Run Diagnostics" to analyze system health
        </div>
      )}
    </div>
  );

  // ── Main Render ──

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingContainer}>
          <div style={styles.loadingSpinner}>Loading Platform Console...</div>
        </div>
      </div>
    );
  }



  return (
    <div style={styles.container}>
      {/* Top Status Bar */}
      <div style={styles.statusBar}>
        <div style={styles.statusBarLeft}>
          {renderStatusBadge(overallStatus)}
          <div style={styles.statusMetric}>
            <span style={styles.statusMetricLabel}>Uptime</span>
            <span style={styles.statusMetricValue}>
              {health ? formatDuration(health.uptime_seconds) : '--'}
            </span>
          </div>
          <div style={styles.statusMetric}>
            <span style={styles.statusMetricLabel}>Active Agents</span>
            <span style={styles.statusMetricValue}>{health?.active_agents ?? '--'}</span>
          </div>
          <div style={styles.statusMetric}>
            <span style={styles.statusMetricLabel}>Total Requests</span>
            <span style={styles.statusMetricValue}>
              {health ? formatNumber(health.total_requests) : '--'}
            </span>
          </div>
          <div style={styles.statusMetric}>
            <span style={styles.statusMetricLabel}>Error Rate</span>
            <span style={{
              ...styles.statusMetricValue,
              color: (health?.error_rate ?? 0) > 5 ? '#ef4444' : (health?.error_rate ?? 0) > 1 ? '#f59e0b' : '#22c55e',
            }}>
              {health ? `${health.error_rate.toFixed(2)}%` : '--'}
            </span>
          </div>
          <div style={styles.statusMetric}>
            <span style={styles.statusMetricLabel}>Alerts</span>
            <span style={{
              ...styles.statusMetricValue,
              color: (health?.alerts?.length ?? 0) > 0 ? '#ef4444' : '#22c55e',
            }}>
              {health?.alerts?.length ?? 0}
              {(health?.alerts?.length ?? 0) > 0 && (
                <span style={styles.alertIcon}>
                  {health?.alerts?.some((a) => a.severity === 'critical') ? ' \u{1F6A8}' : ' \u26A0\uFE0F'}
                </span>
              )}
            </span>
          </div>
        </div>
        <div style={styles.statusBarRight}>
          <label style={styles.autoRefreshLabel}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              style={styles.autoRefreshCheckbox}
            />
            Auto-refresh
          </label>
          <select
            style={styles.refreshSelect}
            value={refreshInterval}
            onChange={(e) => setRefreshInterval(parseInt(e.target.value, 10))}
          >
            {REFRESH_INTERVALS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Tab Navigation */}
      <div style={styles.tabBar}>
        {TAB_IDS.map((tab) => (
          <button
            key={tab}
            style={{
              ...styles.tab,
              ...(activeTab === tab ? styles.tabActive : {}),
            }}
            onClick={() => handleTabChange(tab)}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div style={styles.mainContent}>
        {activeTab === 'dashboard' && renderDashboardTab()}
        {activeTab === 'components' && renderComponentsTab()}
        {activeTab === 'resources' && renderResourcesTab()}
        {activeTab === 'fleet' && renderFleetTab()}
        {activeTab === 'audit' && renderAuditTab()}
        {activeTab === 'features' && renderFeaturesTab()}
        {activeTab === 'analytics' && renderAnalyticsTab()}
        {activeTab === 'diagnostics' && renderDiagnosticsTab()}
      </div>
    </div>
  );

  // ── Styles ──


};

export default PlatformConsolePanel;