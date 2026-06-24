import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SwarmConsolePanelProps {
  onNavigate?: (tab: string) => void;
}

interface SwarmMemberInfo {
  agent_id: string;
  agent_name: string;
  role: string;
  status: 'idle' | 'busy' | 'offline' | 'executing';
  task_count: number;
  success_rate: number;
  capabilities: string[];
}

interface SwarmInfo {
  swarm_id: string;
  topic: string;
  members: SwarmMemberInfo[];
  state: 'forming' | 'active' | 'consensus' | 'executing' | 'exploring' | 'synthesizing' | 'dissolved';
  formed_at: string;
  member_count: number;
  required_capabilities: string[];
  min_members: number;
  max_members: number;
}

interface ConsensusResult {
  decision: string;
  confidence: number;
  method: string;
  votes: Array<{ option: string; count: number; percentage: number }>;
  dissenting_opinions: string[];
  rounds: number;
}

interface TaskExecutionResult {
  task_id: string;
  status: string;
  agent_outputs: Array<{ agent_id: string; agent_name: string; output: string; status: string }>;
  timeline: Array<{ timestamp: string; event: string }>;
  complexity: string;
  priority: string;
}

interface SynthesizedResult {
  summary: string;
  per_agent: Array<{ agent_id: string; agent_name: string; contribution: string; score: number }>;
  consensus_history: ConsensusResult[];
  emergent_patterns: string[];
  exported_at: string | null;
}

interface SwarmMetrics {
  total_swarms: number;
  active_swarms: number;
  average_consensus_rounds: number;
  success_rate: number;
  optimal_swarm_sizes: number[];
  total_tasks_executed: number;
  average_formation_time_ms: number;
}

type ConsensusMethod = 'Majority' | 'Weighted' | 'Ranked Choice' | 'Delegated' | 'Supermajority' | 'Unanimous';

type ActivePanel = 'consensus' | 'execute' | 'explore' | 'synthesize' | null;

type ResultsTab = 'Summary' | 'Per-Agent' | 'Consensus History';

const ALL_CAPABILITIES = [
  'planning', 'coding', 'reviewing', 'testing',
  'designing', 'researching', 'deploying', 'monitoring',
] as const;

const CONSENSUS_METHODS: ConsensusMethod[] = [
  'Majority', 'Weighted', 'Ranked Choice', 'Delegated', 'Supermajority', 'Unanimous',
];

const ROLE_COLORS: Record<string, string> = {
  Leader: '#ffd700',
  Critic: '#ff4444',
  Executor: '#4488ff',
  Verifier: '#44cc44',
  Synthesizer: '#bb44ff',
  Explorer: '#44dddd',
  Mediator: '#ff8844',
  Specialist: '#ff66bb',
};

const STATE_COLORS: Record<SwarmInfo['state'], string> = {
  forming: '#ffd700',
  active: '#44cc44',
  consensus: '#4488ff',
  executing: '#ff8844',
  exploring: '#44dddd',
  synthesizing: '#bb44ff',
  dissolved: '#888888',
};

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    width: '100%',
    height: '100%',
    background: '#1a1a2e',
    color: '#e0e0e0',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    overflow: 'auto',
  } as const,

  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 24px',
    background: '#16213e',
    borderBottom: '1px solid #0f3460',
    flexShrink: 0,
  } as const,

  headerTitle: {
    fontSize: 20,
    fontWeight: 700,
    margin: 0,
    color: '#e0e0e0',
    letterSpacing: '-0.02em',
  } as const,

  headerSubtitle: {
    fontSize: 12,
    color: '#8899aa',
    margin: '2px 0 0 0',
  } as const,

  // ── Two-column layout ──
  mainLayout: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  } as const,

  sidebar: {
    width: 260,
    minWidth: 260,
    background: '#16213e',
    borderRight: '1px solid #0f3460',
    padding: '16px',
    overflowY: 'auto',
    flexShrink: 0,
  } as const,

  sidebarTitle: {
    fontSize: 13,
    fontWeight: 700,
    color: '#8899aa',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: 12,
  } as const,

  metricCard: {
    background: '#1a1a2e',
    borderRadius: 8,
    padding: '12px',
    marginBottom: 8,
    border: '1px solid #0f3460',
  } as const,

  metricValue: {
    fontSize: 22,
    fontWeight: 700,
    color: '#e0e0e0',
  } as const,

  metricLabel: {
    fontSize: 11,
    color: '#8899aa',
    marginTop: 2,
  } as const,

  metricSub: {
    fontSize: 10,
    color: '#667788',
    marginTop: 4,
  } as const,

  content: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflowY: 'auto',
    padding: '20px 24px',
    gap: 20,
  } as const,

  // ── Section cards ──
  section: {
    background: '#16213e',
    borderRadius: 12,
    border: '1px solid #0f3460',
    padding: 20,
  } as const,

  sectionTitle: {
    fontSize: 15,
    fontWeight: 700,
    color: '#e0e0e0',
    margin: '0 0 16px 0',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  } as const,

  // ── Form controls ──
  input: {
    width: '100%',
    padding: '10px 14px',
    borderRadius: 8,
    border: '1px solid #0f3460',
    background: '#1a1a2e',
    color: '#e0e0e0',
    fontSize: 13,
    outline: 'none',
    boxSizing: 'border-box',
  } as const,

  select: {
    width: '100%',
    padding: '10px 14px',
    borderRadius: 8,
    border: '1px solid #0f3460',
    background: '#1a1a2e',
    color: '#e0e0e0',
    fontSize: 13,
    outline: 'none',
    cursor: 'pointer',
  } as const,

  textarea: {
    width: '100%',
    padding: '10px 14px',
    borderRadius: 8,
    border: '1px solid #0f3460',
    background: '#1a1a2e',
    color: '#e0e0e0',
    fontSize: 13,
    outline: 'none',
    resize: 'vertical',
    boxSizing: 'border-box',
    fontFamily: 'inherit',
  } as const,

  label: {
    fontSize: 12,
    fontWeight: 600,
    color: '#8899aa',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    marginBottom: 6,
    display: 'block',
  } as const,

  // ── Buttons ──
  btnPrimary: {
    padding: '10px 20px',
    background: '#0f3460',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
    transition: 'background 0.2s',
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
  } as const,

  btnPrimaryDisabled: {
    padding: '10px 20px',
    background: '#0f3460',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    cursor: 'default',
    fontSize: 13,
    fontWeight: 600,
    opacity: 0.5,
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
  } as const,

  btnSecondary: {
    padding: '8px 16px',
    background: '#1a1a2e',
    color: '#8899aa',
    border: '1px solid #0f3460',
    borderRadius: 8,
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: 600,
    transition: 'all 0.2s',
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
  } as const,

  btnDanger: {
    padding: '8px 16px',
    background: '#3d1a1a',
    color: '#ff6666',
    border: '1px solid #5c2828',
    borderRadius: 8,
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: 600,
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
  } as const,

  btnAction: {
    padding: '10px 18px',
    background: '#0f3460',
    color: '#e0e0e0',
    border: '1px solid #1a4a7a',
    borderRadius: 8,
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
    transition: 'all 0.2s',
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
  } as const,

  // ── Tags / Chips ──
  tag: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '2px 8px',
    borderRadius: 4,
    fontSize: 10,
    fontWeight: 600,
    background: '#1a1a2e',
    color: '#8899aa',
    border: '1px solid #0f3460',
    margin: '2px',
  } as const,

  tagCapability: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '3px 10px',
    borderRadius: 12,
    fontSize: 10,
    fontWeight: 600,
    background: '#0f3460',
    color: '#44dddd',
    margin: '2px',
    cursor: 'pointer',
    border: '1px solid transparent',
    transition: 'all 0.15s',
  } as const,

  tagCapabilitySelected: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '3px 10px',
    borderRadius: 12,
    fontSize: 10,
    fontWeight: 600,
    background: '#1a4a7a',
    color: '#fff',
    margin: '2px',
    cursor: 'pointer',
    border: '1px solid #4488ff',
  } as const,

  roleBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '2px 10px',
    borderRadius: 12,
    fontSize: 10,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
  } as const,

  statusDot: {
    display: 'inline-block',
    width: 8,
    height: 8,
    borderRadius: '50%',
    marginRight: 6,
  } as const,

  // ── Member grid ──
  memberGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
    gap: 12,
  } as const,

  memberCard: {
    background: '#1a1a2e',
    borderRadius: 10,
    border: '1px solid #0f3460',
    padding: 14,
    cursor: 'pointer',
    transition: 'border-color 0.2s, box-shadow 0.2s',
  } as const,

  memberAvatar: {
    width: 40,
    height: 40,
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: 700,
    fontSize: 16,
    flexShrink: 0,
  } as const,

  // ── Modal overlay ──
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.7)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    backdropFilter: 'blur(4px)',
  } as const,

  modal: {
    background: '#16213e',
    borderRadius: 16,
    border: '1px solid #0f3460',
    width: '90%',
    maxWidth: 720,
    maxHeight: '85vh',
    overflow: 'auto',
    padding: 24,
    boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
  } as const,

  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  } as const,

  modalTitle: {
    fontSize: 18,
    fontWeight: 700,
    color: '#e0e0e0',
    margin: 0,
  } as const,

  // ── Tabs ──
  tabBar: {
    display: 'flex',
    gap: 2,
    borderBottom: '1px solid #0f3460',
    marginBottom: 16,
  } as const,

  tab: {
    padding: '8px 16px',
    fontSize: 12,
    fontWeight: 600,
    color: '#8899aa',
    border: 'none',
    background: 'none',
    cursor: 'pointer',
    borderBottom: '2px solid transparent',
    transition: 'all 0.15s',
  } as const,

  tabActive: {
    padding: '8px 16px',
    fontSize: 12,
    fontWeight: 600,
    color: '#4488ff',
    border: 'none',
    background: 'none',
    cursor: 'pointer',
    borderBottom: '2px solid #4488ff',
  } as const,

  // ── Progress bar ──
  progressBar: {
    height: 6,
    borderRadius: 3,
    background: '#0f3460',
    overflow: 'hidden',
    flex: 1,
  } as const,

  progressFill: {
    height: '100%',
    borderRadius: 3,
    transition: 'width 0.4s ease',
  } as const,

  // ── Slider ──
  slider: {
    width: '100%',
    appearance: 'none',
    height: 6,
    borderRadius: 3,
    background: '#0f3460',
    outline: 'none',
    cursor: 'pointer',
  } as const,

  // ── Info row ──
  infoRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 16,
    marginBottom: 12,
  } as const,

  infoItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
  } as const,

  infoLabel: {
    fontSize: 10,
    color: '#667788',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
  } as const,

  infoValue: {
    fontSize: 13,
    fontWeight: 600,
    color: '#e0e0e0',
  } as const,

  // ── Timeline ──
  timeline: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    paddingLeft: 16,
    borderLeft: '2px solid #0f3460',
    marginLeft: 8,
  } as const,

  timelineItem: {
    fontSize: 12,
    color: '#8899aa',
    position: 'relative',
    paddingLeft: 16,
  } as const,

  timelineDot: {
    position: 'absolute',
    left: -22,
    top: 4,
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: '#4488ff',
  } as const,

  // ── Empty state ──
  emptyState: {
    textAlign: 'center',
    padding: '40px 20px',
    color: '#667788',
    fontSize: 14,
  } as const,

  // ── Flex helpers ──
  flexRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  } as const,

  flexBetween: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  } as const,

  flexWrap: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
  } as const,

  gap8: { gap: 8 } as const,
  gap12: { gap: 12 } as const,
  gap16: { gap: 16 } as const,
  mb8: { marginBottom: 8 } as const,
  mb12: { marginBottom: 12 } as const,
  mb16: { marginBottom: 16 } as const,
  mt8: { marginTop: 8 } as const,
  mt12: { marginTop: 12 } as const,
  mt16: { marginTop: 16 } as const,
  flex1: { flex: 1 } as const,
} as const;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    idle: '#44cc44',
    busy: '#ffd700',
    offline: '#888888',
    executing: '#4488ff',
  };
  return colors[status] || '#888888';
}

function formatTime(iso: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const SwarmConsolePanel: React.FC<SwarmConsolePanelProps> = ({ onNavigate }) => {
  const toast = useToast();

  // ── Swarm state ──
  const [topic, setTopic] = useState('');
  const [selectedCapabilities, setSelectedCapabilities] = useState<string[]>([]);
  const [minMembers, setMinMembers] = useState(2);
  const [maxMembers, setMaxMembers] = useState(10);
  const [swarm, setSwarm] = useState<SwarmInfo | null>(null);
  const [isFormingSwarm, setIsFormingSwarm] = useState(false);

  // ── Metrics ──
  const [metrics, setMetrics] = useState<SwarmMetrics | null>(null);

  // ── Panel states ──
  const [activePanel, setActivePanel] = useState<ActivePanel>(null);
  const [selectedMember, setSelectedMember] = useState<SwarmMemberInfo | null>(null);

  // ── Consensus state ──
  const [consensusQuestion, setConsensusQuestion] = useState('');
  const [consensusOptions, setConsensusOptions] = useState<string[]>(['', '']);
  const [consensusMethod, setConsensusMethod] = useState<ConsensusMethod>('Majority');
  const [consensusResult, setConsensusResult] = useState<ConsensusResult | null>(null);
  const [isConsensusLoading, setIsConsensusLoading] = useState(false);

  // ── Task execution state ──
  const [taskDescription, setTaskDescription] = useState('');
  const [taskComplexity, setTaskComplexity] = useState('medium');
  const [taskPriority, setTaskPriority] = useState('medium');
  const [taskResult, setTaskResult] = useState<TaskExecutionResult | null>(null);
  const [isTaskLoading, setIsTaskLoading] = useState(false);

  // ── Explore state ──
  const [exploreTopic, setExploreTopic] = useState('');
  const [exploreResult, setExploreResult] = useState<string | null>(null);
  const [isExploreLoading, setIsExploreLoading] = useState(false);

  // ── Synthesize state ──
  const [synthesizeResult, setSynthesizeResult] = useState<SynthesizedResult | null>(null);
  const [isSynthesizeLoading, setIsSynthesizeLoading] = useState(false);

  // ── Results tab ──
  const [resultsTab, setResultsTab] = useState<ResultsTab>('Summary');

  // ── Fetch metrics on mount ──
  useEffect(() => {
    fetchMetrics();
  }, []);

  const fetchMetrics = async () => {
    try {
      const res = await fetch('/api/swarm-orchestrator/metrics');
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch {
      // Silently fail — metrics are non-critical
    }
  };

  // ── Toggle capability ──
  const toggleCapability = (cap: string) => {
    setSelectedCapabilities((prev) =>
      prev.includes(cap) ? prev.filter((c) => c !== cap) : [...prev, cap],
    );
  };

  // ── Form Swarm ──
  const handleFormSwarm = async () => {
    if (!topic.trim()) {
      toast.warning('Please enter a topic for the swarm.');
      return;
    }
    if (selectedCapabilities.length === 0) {
      toast.warning('Please select at least one capability.');
      return;
    }
    setIsFormingSwarm(true);
    try {
      const res = await fetch('/api/swarm-orchestrator/form', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic.trim(),
          required_capabilities: selectedCapabilities,
          min_members: minMembers,
          max_members: maxMembers,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed to form swarm' }));
        throw new Error(err.detail || 'Failed to form swarm');
      }
      const data: SwarmInfo = await res.json();
      setSwarm(data);
      setActivePanel(null);
      setConsensusResult(null);
      setTaskResult(null);
      setExploreResult(null);
      setSynthesizeResult(null);
      toast.success(`Swarm "${data.swarm_id}" formed with ${data.member_count} members.`);
      fetchMetrics();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to form swarm');
    } finally {
      setIsFormingSwarm(false);
    }
  };

  // ── Reach Consensus ──
  const handleReachConsensus = async () => {
    if (!consensusQuestion.trim() || consensusOptions.some((o) => !o.trim())) {
      toast.warning('Please fill in the question and all options.');
      return;
    }
    setIsConsensusLoading(true);
    try {
      const res = await fetch('/api/swarm-orchestrator/consensus', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          swarm_id: swarm?.swarm_id,
          question: consensusQuestion.trim(),
          options: consensusOptions.filter((o) => o.trim()),
          method: consensusMethod,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Consensus failed' }));
        throw new Error(err.detail || 'Consensus failed');
      }
      const data: ConsensusResult = await res.json();
      setConsensusResult(data);
      toast.success('Consensus reached successfully.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Consensus failed');
    } finally {
      setIsConsensusLoading(false);
    }
  };

  // ── Execute Task ──
  const handleExecuteTask = async () => {
    if (!taskDescription.trim()) {
      toast.warning('Please enter a task description.');
      return;
    }
    setIsTaskLoading(true);
    try {
      const res = await fetch('/api/swarm-orchestrator/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          swarm_id: swarm?.swarm_id,
          description: taskDescription.trim(),
          complexity: taskComplexity,
          priority: taskPriority,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Task execution failed' }));
        throw new Error(err.detail || 'Task execution failed');
      }
      const data: TaskExecutionResult = await res.json();
      setTaskResult(data);
      toast.success('Task executed successfully.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Task execution failed');
    } finally {
      setIsTaskLoading(false);
    }
  };

  // ── Parallel Explore ──
  const handleExplore = async () => {
    if (!exploreTopic.trim()) {
      toast.warning('Please enter an exploration topic.');
      return;
    }
    setIsExploreLoading(true);
    try {
      const res = await fetch('/api/swarm-orchestrator/explore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          swarm_id: swarm?.swarm_id,
          topic: exploreTopic.trim(),
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Exploration failed' }));
        throw new Error(err.detail || 'Exploration failed');
      }
      const data = await res.json();
      setExploreResult(data.result || JSON.stringify(data, null, 2));
      toast.success('Exploration completed.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Exploration failed');
    } finally {
      setIsExploreLoading(false);
    }
  };

  // ── Synthesize Results ──
  const handleSynthesize = async () => {
    if (!swarm) return;
    setIsSynthesizeLoading(true);
    try {
      const res = await fetch(`/api/swarm-orchestrator/${swarm.swarm_id}/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Synthesis failed' }));
        throw new Error(err.detail || 'Synthesis failed');
      }
      const data: SynthesizedResult = await res.json();
      setSynthesizeResult(data);
      toast.success('Results synthesized successfully.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Synthesis failed');
    } finally {
      setIsSynthesizeLoading(false);
    }
  };

  // ── Dissolve Swarm ──
  const handleDissolveSwarm = async () => {
    if (!swarm) return;
    try {
      const res = await fetch(`/api/swarm-orchestrator/${swarm.swarm_id}/dissolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Dissolve failed' }));
        throw new Error(err.detail || 'Dissolve failed');
      }
      toast.success(`Swarm "${swarm.swarm_id}" dissolved.`);
      setSwarm(null);
      setActivePanel(null);
      setConsensusResult(null);
      setTaskResult(null);
      setExploreResult(null);
      setSynthesizeResult(null);
      fetchMetrics();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Dissolve failed');
    }
  };

  // ── Export results ──
  const handleExportResults = () => {
    if (!synthesizeResult) return;
    const blob = new Blob([JSON.stringify(synthesizeResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `swarm-${swarm?.swarm_id || 'results'}-synthesis.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Results exported.');
  };

  // ── Add / remove consensus option ──
  const addConsensusOption = () => setConsensusOptions((prev) => [...prev, '']);
  const removeConsensusOption = (idx: number) =>
    setConsensusOptions((prev) => prev.filter((_, i) => i !== idx));
  const updateConsensusOption = (idx: number, value: string) =>
    setConsensusOptions((prev) => prev.map((o, i) => (i === idx ? value : o)));

  const closePanel = () => setActivePanel(null);

  // ── Render ──
  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h2 style={styles.headerTitle}>Swarm Orchestration Console</h2>
          <p style={styles.headerSubtitle}>
            Form intelligent agent swarms, reach consensus, and execute tasks in parallel
          </p>
        </div>
        {swarm && (
          <div style={{ ...styles.flexRow, gap: 8 }}>
            <span style={{ fontSize: 12, color: '#8899aa' }}>
              Swarm: <strong style={{ color: '#e0e0e0' }}>{swarm.swarm_id}</strong>
            </span>
            <span
              style={{
                ...styles.roleBadge,
                background: STATE_COLORS[swarm.state] + '22',
                color: STATE_COLORS[swarm.state],
                border: `1px solid ${STATE_COLORS[swarm.state]}44`,
              }}
            >
              {swarm.state}
            </span>
          </div>
        )}
      </div>

      {/* Main layout */}
      <div style={styles.mainLayout}>
        {/* Sidebar — Metrics */}
        <div style={styles.sidebar}>
          <div style={styles.sidebarTitle}>Swarm Metrics</div>

          {metrics ? (
            <>
              <div style={styles.metricCard}>
                <div style={styles.metricValue}>{metrics.total_swarms}</div>
                <div style={styles.metricLabel}>Total Swarms Formed</div>
              </div>
              <div style={styles.metricCard}>
                <div style={{ ...styles.metricValue, color: '#44cc44' }}>{metrics.active_swarms}</div>
                <div style={styles.metricLabel}>Active Swarms</div>
              </div>
              <div style={styles.metricCard}>
                <div style={styles.metricValue}>{metrics.average_consensus_rounds.toFixed(1)}</div>
                <div style={styles.metricLabel}>Avg Consensus Rounds</div>
              </div>
              <div style={styles.metricCard}>
                <div style={{ ...styles.metricValue, color: metrics.success_rate >= 80 ? '#44cc44' : '#ffd700' }}>
                  {metrics.success_rate.toFixed(1)}%
                </div>
                <div style={styles.metricLabel}>Success Rate</div>
              </div>
              <div style={styles.metricCard}>
                <div style={{ ...styles.metricValue, fontSize: 16 }}>
                  {metrics.optimal_swarm_sizes.join(' – ')}
                </div>
                <div style={styles.metricLabel}>Optimal Swarm Sizes</div>
              </div>
              <div style={styles.metricCard}>
                <div style={styles.metricValue}>{metrics.total_tasks_executed}</div>
                <div style={styles.metricLabel}>Total Tasks Executed</div>
              </div>
              <div style={styles.metricCard}>
                <div style={{ ...styles.metricValue, fontSize: 16 }}>
                  {(metrics.average_formation_time_ms / 1000).toFixed(1)}s
                </div>
                <div style={styles.metricLabel}>Avg Formation Time</div>
              </div>
            </>
          ) : (
            <div style={{ ...styles.emptyState, padding: '20px 0' }}>
              Loading metrics...
            </div>
          )}
        </div>

        {/* Content */}
        <div style={styles.content}>
          {/* ── Form Swarm Section ── */}
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>
              <span>⚡</span> Form Swarm
            </h3>

            <div style={{ ...styles.mb12 }}>
              <label style={styles.label}>Topic</label>
              <input
                style={styles.input}
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="What should the swarm work on? e.g. Design a new authentication system"
                disabled={!!swarm}
              />
            </div>

            <div style={{ ...styles.mb12 }}>
              <label style={styles.label}>Required Capabilities</label>
              <div style={styles.flexWrap}>
                {ALL_CAPABILITIES.map((cap) => (
                  <span
                    key={cap}
                    style={
                      selectedCapabilities.includes(cap)
                        ? styles.tagCapabilitySelected
                        : styles.tagCapability
                    }
                    onClick={() => !swarm && toggleCapability(cap)}
                  >
                    {cap}
                  </span>
                ))}
              </div>
            </div>

            <div style={{ ...styles.flexRow, gap: 24, ...styles.mb12 }}>
              <div style={{ flex: 1 }}>
                <label style={styles.label}>
                  Min Members: <strong style={{ color: '#e0e0e0' }}>{minMembers}</strong>
                </label>
                <input
                  type="range"
                  min={1}
                  max={20}
                  value={minMembers}
                  onChange={(e) => setMinMembers(Math.min(Number(e.target.value), maxMembers))}
                  disabled={!!swarm}
                  style={styles.slider}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={styles.label}>
                  Max Members: <strong style={{ color: '#e0e0e0' }}>{maxMembers}</strong>
                </label>
                <input
                  type="range"
                  min={1}
                  max={50}
                  value={maxMembers}
                  onChange={(e) => setMaxMembers(Math.max(Number(e.target.value), minMembers))}
                  disabled={!!swarm}
                  style={styles.slider}
                />
              </div>
            </div>

            <button
              style={isFormingSwarm || !!swarm ? styles.btnPrimaryDisabled : styles.btnPrimary}
              disabled={isFormingSwarm || !!swarm}
              onClick={handleFormSwarm}
            >
              {isFormingSwarm ? '⏳ Forming...' : '🚀 Form Swarm'}
            </button>

            {/* Current swarm info */}
            {swarm && (
              <div style={{ ...styles.mt16, ...styles.infoRow }}>
                <div style={styles.infoItem}>
                  <span style={styles.infoLabel}>Swarm ID</span>
                  <span style={styles.infoValue}>{swarm.swarm_id}</span>
                </div>
                <div style={styles.infoItem}>
                  <span style={styles.infoLabel}>Members</span>
                  <span style={styles.infoValue}>{swarm.member_count}</span>
                </div>
                <div style={styles.infoItem}>
                  <span style={styles.infoLabel}>State</span>
                  <span style={{ ...styles.infoValue, color: STATE_COLORS[swarm.state] }}>
                    {swarm.state}
                  </span>
                </div>
                <div style={styles.infoItem}>
                  <span style={styles.infoLabel}>Formed</span>
                  <span style={styles.infoValue}>{formatTime(swarm.formed_at)}</span>
                </div>
              </div>
            )}
          </div>

          {/* ── Swarm Members Grid ── */}
          {swarm && swarm.members.length > 0 && (
            <div style={styles.section}>
              <h3 style={styles.sectionTitle}>
                <span>👥</span> Swarm Members ({swarm.members.length})
              </h3>
              <div style={styles.memberGrid}>
                {swarm.members.map((member) => (
                  <div
                    key={member.agent_id}
                    style={styles.memberCard}
                    onClick={() => setSelectedMember(member)}
                  >
                    <div style={{ ...styles.flexRow, ...styles.mb8 }}>
                      <div
                        style={{
                          ...styles.memberAvatar,
                          background: ROLE_COLORS[member.role] || '#0f3460',
                          color: '#fff',
                        }}
                      >
                        {getInitials(member.agent_name)}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: '#e0e0e0' }}>
                          {member.agent_name}
                        </div>
                        <span
                          style={{
                            ...styles.roleBadge,
                            background: (ROLE_COLORS[member.role] || '#0f3460') + '22',
                            color: ROLE_COLORS[member.role] || '#8899aa',
                            border: `1px solid ${(ROLE_COLORS[member.role] || '#0f3460')}44`,
                          }}
                        >
                          {member.role}
                        </span>
                      </div>
                    </div>

                    <div style={{ ...styles.flexRow, ...styles.mb8 }}>
                      <span
                        style={{
                          ...styles.statusDot,
                          background: getStatusColor(member.status),
                        }}
                      />
                      <span style={{ fontSize: 11, color: '#8899aa' }}>{member.status}</span>
                    </div>

                    <div style={{ ...styles.flexRow, gap: 16, ...styles.mb8 }}>
                      <div style={{ fontSize: 11, color: '#667788' }}>
                        Tasks: <strong style={{ color: '#e0e0e0' }}>{member.task_count}</strong>
                      </div>
                      <div style={{ fontSize: 11, color: '#667788' }}>
                        Success:{' '}
                        <strong
                          style={{
                            color: member.success_rate >= 80 ? '#44cc44' : '#ffd700',
                          }}
                        >
                          {member.success_rate.toFixed(0)}%
                        </strong>
                      </div>
                    </div>

                    <div style={styles.flexWrap}>
                      {member.capabilities.slice(0, 4).map((cap) => (
                        <span key={cap} style={styles.tag}>
                          {cap}
                        </span>
                      ))}
                      {member.capabilities.length > 4 && (
                        <span style={styles.tag}>+{member.capabilities.length - 4}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Action Buttons ── */}
          {swarm && (
            <div style={styles.section}>
              <h3 style={styles.sectionTitle}>
                <span>🎯</span> Swarm Actions
              </h3>
              <div style={{ ...styles.flexWrap, gap: 10 }}>
                <button
                  style={styles.btnAction}
                  onClick={() => {
                    setActivePanel('consensus');
                    setConsensusResult(null);
                  }}
                >
                  🤝 Reach Consensus
                </button>
                <button
                  style={styles.btnAction}
                  onClick={() => {
                    setActivePanel('execute');
                    setTaskResult(null);
                  }}
                >
                  ⚡ Execute Task
                </button>
                <button
                  style={styles.btnAction}
                  onClick={() => {
                    setActivePanel('explore');
                    setExploreResult(null);
                  }}
                >
                  🔍 Parallel Explore
                </button>
                <button
                  style={styles.btnAction}
                  onClick={() => {
                    setActivePanel('synthesize');
                    handleSynthesize();
                  }}
                >
                  🧩 Synthesize Results
                </button>
                <button style={styles.btnDanger} onClick={handleDissolveSwarm}>
                  💥 Dissolve Swarm
                </button>
              </div>
            </div>
          )}

          {/* ── Synthesized Results ── */}
          {synthesizeResult && (
            <div style={styles.section}>
              <div style={styles.flexBetween}>
                <h3 style={{ ...styles.sectionTitle, marginBottom: 0 }}>
                  <span>📊</span> Results
                </h3>
                <button style={styles.btnSecondary} onClick={handleExportResults}>
                  📥 Export
                </button>
              </div>

              {/* Tabs */}
              <div style={{ ...styles.tabBar, ...styles.mt12 }}>
                {(['Summary', 'Per-Agent', 'Consensus History'] as ResultsTab[]).map((tab) => (
                  <button
                    key={tab}
                    style={resultsTab === tab ? styles.tabActive : styles.tab}
                    onClick={() => setResultsTab(tab)}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {/* Summary */}
              {resultsTab === 'Summary' && (
                <div>
                  <div
                    style={{
                      background: '#1a1a2e',
                      borderRadius: 8,
                      padding: 16,
                      border: '1px solid #0f3460',
                      fontSize: 13,
                      lineHeight: 1.6,
                      whiteSpace: 'pre-wrap',
                      color: '#e0e0e0',
                    }}
                  >
                    {synthesizeResult.summary}
                  </div>

                  {synthesizeResult.emergent_patterns.length > 0 && (
                    <div style={styles.mt16}>
                      <div style={{ ...styles.label, marginBottom: 8 }}>Emergent Patterns Detected</div>
                      <div style={styles.flexWrap}>
                        {synthesizeResult.emergent_patterns.map((pattern, i) => (
                          <span
                            key={i}
                            style={{
                              ...styles.tagCapabilitySelected,
                              cursor: 'default',
                              fontSize: 11,
                            }}
                          >
                            {pattern}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Per-Agent */}
              {resultsTab === 'Per-Agent' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {synthesizeResult.per_agent.map((agent) => (
                    <div
                      key={agent.agent_id}
                      style={{
                        background: '#1a1a2e',
                        borderRadius: 8,
                        padding: 14,
                        border: '1px solid #0f3460',
                      }}
                    >
                      <div style={{ ...styles.flexBetween, ...styles.mb8 }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: '#e0e0e0' }}>
                          {agent.agent_name}
                        </span>
                        <span style={{ fontSize: 11, color: '#8899aa' }}>
                          Score: {(agent.score * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: '#8899aa', lineHeight: 1.5 }}>
                        {agent.contribution}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Consensus History */}
              {resultsTab === 'Consensus History' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {synthesizeResult.consensus_history.length === 0 ? (
                    <div style={styles.emptyState}>No consensus rounds recorded.</div>
                  ) : (
                    synthesizeResult.consensus_history.map((cr, i) => (
                      <div
                        key={i}
                        style={{
                          background: '#1a1a2e',
                          borderRadius: 8,
                          padding: 14,
                          border: '1px solid #0f3460',
                        }}
                      >
                        <div style={{ ...styles.flexBetween, ...styles.mb8 }}>
                          <span style={{ fontSize: 13, fontWeight: 600, color: '#e0e0e0' }}>
                            Round {i + 1}: {cr.method}
                          </span>
                          <span style={{ fontSize: 12, color: '#44cc44' }}>
                            {cr.confidence.toFixed(1)}% confidence
                          </span>
                        </div>
                        <div style={{ fontSize: 12, color: '#8899aa', ...styles.mb8 }}>
                          Decision: <strong style={{ color: '#e0e0e0' }}>{cr.decision}</strong>
                        </div>
                        {cr.dissenting_opinions.length > 0 && (
                          <div style={{ fontSize: 11, color: '#ff8844' }}>
                            Dissenting: {cr.dissenting_opinions.join(', ')}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── Empty state ── */}
          {!swarm && !isFormingSwarm && (
            <div style={{ ...styles.emptyState, padding: '60px 20px' }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>🐝</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#8899aa', marginBottom: 8 }}>
                No Active Swarm
              </div>
              <div style={{ fontSize: 13, color: '#667788' }}>
                Fill in the Form Swarm section above to create your first agent swarm.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Member Detail Modal ── */}
      {selectedMember && (
        <div style={styles.overlay} onClick={() => setSelectedMember(null)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>Member Details</h3>
              <button
                style={{ ...styles.btnSecondary, padding: '6px 12px' }}
                onClick={() => setSelectedMember(null)}
              >
                ✕ Close
              </button>
            </div>

            <div style={{ ...styles.flexRow, gap: 16, ...styles.mb16 }}>
              <div
                style={{
                  ...styles.memberAvatar,
                  width: 56,
                  height: 56,
                  fontSize: 22,
                  background: ROLE_COLORS[selectedMember.role] || '#0f3460',
                  color: '#fff',
                }}
              >
                {getInitials(selectedMember.agent_name)}
              </div>
              <div>
                <div style={{ fontSize: 16, fontWeight: 700, color: '#e0e0e0' }}>
                  {selectedMember.agent_name}
                </div>
                <span
                  style={{
                    ...styles.roleBadge,
                    background: (ROLE_COLORS[selectedMember.role] || '#0f3460') + '22',
                    color: ROLE_COLORS[selectedMember.role] || '#8899aa',
                    border: `1px solid ${(ROLE_COLORS[selectedMember.role] || '#0f3460')}44`,
                  }}
                >
                  {selectedMember.role}
                </span>
              </div>
            </div>

            <div style={{ ...styles.infoRow, ...styles.mb16 }}>
              <div style={styles.infoItem}>
                <span style={styles.infoLabel}>Agent ID</span>
                <span style={styles.infoValue}>{selectedMember.agent_id}</span>
              </div>
              <div style={styles.infoItem}>
                <span style={styles.infoLabel}>Status</span>
                <span style={{ ...styles.infoValue, color: getStatusColor(selectedMember.status) }}>
                  {selectedMember.status}
                </span>
              </div>
              <div style={styles.infoItem}>
                <span style={styles.infoLabel}>Tasks</span>
                <span style={styles.infoValue}>{selectedMember.task_count}</span>
              </div>
              <div style={styles.infoItem}>
                <span style={styles.infoLabel}>Success Rate</span>
                <span style={styles.infoValue}>{selectedMember.success_rate.toFixed(0)}%</span>
              </div>
            </div>

            <div style={{ ...styles.mb16 }}>
              <div style={styles.label}>Capabilities</div>
              <div style={styles.flexWrap}>
                {selectedMember.capabilities.map((cap) => (
                  <span key={cap} style={styles.tagCapability}>
                    {cap}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Consensus Panel Modal ── */}
      {activePanel === 'consensus' && (
        <div style={styles.overlay} onClick={closePanel}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>🤝 Reach Consensus</h3>
              <button
                style={{ ...styles.btnSecondary, padding: '6px 12px' }}
                onClick={closePanel}
              >
                ✕ Close
              </button>
            </div>

            <div style={styles.mb12}>
              <label style={styles.label}>Question</label>
              <input
                style={styles.input}
                value={consensusQuestion}
                onChange={(e) => setConsensusQuestion(e.target.value)}
                placeholder="What should the swarm decide?"
              />
            </div>

            <div style={styles.mb12}>
              <div style={{ ...styles.flexBetween, ...styles.mb8 }}>
                <label style={{ ...styles.label, marginBottom: 0 }}>Options</label>
                <button style={styles.btnSecondary} onClick={addConsensusOption}>
                  + Add Option
                </button>
              </div>
              {consensusOptions.map((opt, idx) => (
                <div key={idx} style={{ ...styles.flexRow, ...styles.mb8 }}>
                  <input
                    style={styles.input}
                    value={opt}
                    onChange={(e) => updateConsensusOption(idx, e.target.value)}
                    placeholder={`Option ${idx + 1}`}
                  />
                  {consensusOptions.length > 2 && (
                    <button
                      style={{ ...styles.btnDanger, padding: '6px 10px', fontSize: 11 }}
                      onClick={() => removeConsensusOption(idx)}
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}
            </div>

            <div style={styles.mb16}>
              <label style={styles.label}>Method</label>
              <select
                style={styles.select}
                value={consensusMethod}
                onChange={(e) => setConsensusMethod(e.target.value as ConsensusMethod)}
              >
                {CONSENSUS_METHODS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>

            <button
              style={isConsensusLoading ? styles.btnPrimaryDisabled : styles.btnPrimary}
              disabled={isConsensusLoading}
              onClick={handleReachConsensus}
            >
              {isConsensusLoading ? '⏳ Reaching Consensus...' : '🤝 Reach Consensus'}
            </button>

            {/* Consensus result */}
            {consensusResult && (
              <div style={{ ...styles.mt16, background: '#1a1a2e', borderRadius: 10, padding: 16, border: '1px solid #0f3460' }}>
                <div style={{ ...styles.flexBetween, ...styles.mb12 }}>
                  <span style={{ fontSize: 14, fontWeight: 700, color: '#e0e0e0' }}>
                    Decision: {consensusResult.decision}
                  </span>
                  <span style={{ fontSize: 13, color: '#44cc44', fontWeight: 600 }}>
                    {consensusResult.confidence.toFixed(1)}% Confidence
                  </span>
                </div>

                <div style={{ ...styles.mb12 }}>
                  <div style={{ ...styles.label, marginBottom: 6 }}>
                    Votes Breakdown ({consensusResult.method} · {consensusResult.rounds} rounds)
                  </div>
                  {consensusResult.votes.map((v, i) => (
                    <div key={i} style={{ ...styles.mb8 }}>
                      <div style={{ ...styles.flexBetween, ...styles.mb8 }}>
                        <span style={{ fontSize: 12, color: '#8899aa' }}>{v.option}</span>
                        <span style={{ fontSize: 12, color: '#e0e0e0', fontWeight: 600 }}>
                          {v.count} votes ({v.percentage.toFixed(1)}%)
                        </span>
                      </div>
                      <div style={styles.progressBar}>
                        <div
                          style={{
                            ...styles.progressFill,
                            width: `${v.percentage}%`,
                            background: i === 0 ? '#4488ff' : '#0f3460',
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                {consensusResult.dissenting_opinions.length > 0 && (
                  <div>
                    <div style={{ ...styles.label, marginBottom: 6 }}>Dissenting Opinions</div>
                    {consensusResult.dissenting_opinions.map((op, i) => (
                      <div
                        key={i}
                        style={{
                          fontSize: 12,
                          color: '#ff8844',
                          padding: '4px 0',
                          borderBottom: i < consensusResult.dissenting_opinions.length - 1 ? '1px solid #0f3460' : 'none',
                        }}
                      >
                        {op}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Task Execution Panel Modal ── */}
      {activePanel === 'execute' && (
        <div style={styles.overlay} onClick={closePanel}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>⚡ Execute Task</h3>
              <button
                style={{ ...styles.btnSecondary, padding: '6px 12px' }}
                onClick={closePanel}
              >
                ✕ Close
              </button>
            </div>

            <div style={styles.mb12}>
              <label style={styles.label}>Task Description</label>
              <textarea
                style={{ ...styles.textarea, minHeight: 80 }}
                value={taskDescription}
                onChange={(e) => setTaskDescription(e.target.value)}
                placeholder="Describe the task the swarm should execute..."
              />
            </div>

            <div style={{ ...styles.flexRow, gap: 16, ...styles.mb16 }}>
              <div style={{ flex: 1 }}>
                <label style={styles.label}>Complexity</label>
                <select
                  style={styles.select}
                  value={taskComplexity}
                  onChange={(e) => setTaskComplexity(e.target.value)}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <div style={{ flex: 1 }}>
                <label style={styles.label}>Priority</label>
                <select
                  style={styles.select}
                  value={taskPriority}
                  onChange={(e) => setTaskPriority(e.target.value)}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>
            </div>

            <button
              style={isTaskLoading ? styles.btnPrimaryDisabled : styles.btnPrimary}
              disabled={isTaskLoading}
              onClick={handleExecuteTask}
            >
              {isTaskLoading ? '⏳ Executing...' : '⚡ Execute'}
            </button>

            {/* Task result */}
            {taskResult && (
              <div style={{ ...styles.mt16 }}>
                <div style={{ ...styles.flexBetween, ...styles.mb12 }}>
                  <span style={{ fontSize: 14, fontWeight: 700, color: '#e0e0e0' }}>
                    Task: {taskResult.task_id}
                  </span>
                  <span
                    style={{
                      ...styles.roleBadge,
                      background: taskResult.status === 'completed' ? '#44cc4422' : '#ffd70022',
                      color: taskResult.status === 'completed' ? '#44cc44' : '#ffd700',
                      border: `1px solid ${taskResult.status === 'completed' ? '#44cc4444' : '#ffd70044'}`,
                    }}
                  >
                    {taskResult.status}
                  </span>
                </div>

                <div style={{ ...styles.infoRow, ...styles.mb12 }}>
                  <div style={styles.infoItem}>
                    <span style={styles.infoLabel}>Complexity</span>
                    <span style={styles.infoValue}>{taskResult.complexity}</span>
                  </div>
                  <div style={styles.infoItem}>
                    <span style={styles.infoLabel}>Priority</span>
                    <span style={styles.infoValue}>{taskResult.priority}</span>
                  </div>
                </div>

                {/* Per-agent output */}
                <div style={{ ...styles.mb12 }}>
                  <div style={{ ...styles.label, ...styles.mb8 }}>Per-Agent Output</div>
                  {taskResult.agent_outputs.map((ao) => (
                    <div
                      key={ao.agent_id}
                      style={{
                        background: '#1a1a2e',
                        borderRadius: 8,
                        padding: 10,
                        border: '1px solid #0f3460',
                        ...styles.mb8,
                      }}
                    >
                      <div style={{ ...styles.flexBetween, ...styles.mb8 }}>
                        <span style={{ fontSize: 12, fontWeight: 600, color: '#e0e0e0' }}>
                          {ao.agent_name}
                        </span>
                        <span
                          style={{
                            fontSize: 10,
                            color: ao.status === 'completed' ? '#44cc44' : '#ffd700',
                          }}
                        >
                          {ao.status}
                        </span>
                      </div>
                      <div style={{ fontSize: 11, color: '#8899aa', whiteSpace: 'pre-wrap' }}>
                        {ao.output}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Status timeline */}
                <div>
                  <div style={{ ...styles.label, ...styles.mb8 }}>Timeline</div>
                  <div style={styles.timeline}>
                    {taskResult.timeline.map((evt, i) => (
                      <div key={i} style={styles.timelineItem}>
                        <div style={styles.timelineDot} />
                        <span style={{ fontSize: 10, color: '#667788' }}>
                          {formatTime(evt.timestamp)}
                        </span>
                        {' — '}
                        <span style={{ color: '#8899aa' }}>{evt.event}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Parallel Explore Panel Modal ── */}
      {activePanel === 'explore' && (
        <div style={styles.overlay} onClick={closePanel}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>🔍 Parallel Explore</h3>
              <button
                style={{ ...styles.btnSecondary, padding: '6px 12px' }}
                onClick={closePanel}
              >
                ✕ Close
              </button>
            </div>

            <div style={styles.mb12}>
              <label style={styles.label}>Exploration Topic</label>
              <input
                style={styles.input}
                value={exploreTopic}
                onChange={(e) => setExploreTopic(e.target.value)}
                placeholder="What topic should agents explore in parallel?"
              />
            </div>

            <button
              style={isExploreLoading ? styles.btnPrimaryDisabled : styles.btnPrimary}
              disabled={isExploreLoading}
              onClick={handleExplore}
            >
              {isExploreLoading ? '⏳ Exploring...' : '🔍 Explore'}
            </button>

            {exploreResult && (
              <div
                style={{
                  ...styles.mt16,
                  background: '#1a1a2e',
                  borderRadius: 10,
                  padding: 16,
                  border: '1px solid #0f3460',
                  fontSize: 13,
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                  color: '#e0e0e0',
                  maxHeight: 400,
                  overflow: 'auto',
                }}
              >
                {exploreResult}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Synthesize Panel Modal ── */}
      {activePanel === 'synthesize' && (
        <div style={styles.overlay} onClick={closePanel}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>🧩 Synthesize Results</h3>
              <button
                style={{ ...styles.btnSecondary, padding: '6px 12px' }}
                onClick={closePanel}
              >
                ✕ Close
              </button>
            </div>

            {isSynthesizeLoading ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: '#8899aa' }}>
                ⏳ Synthesizing results from all swarm members...
              </div>
            ) : synthesizeResult ? (
              <div>
                <div
                  style={{
                    background: '#1a1a2e',
                    borderRadius: 8,
                    padding: 16,
                    border: '1px solid #0f3460',
                    fontSize: 13,
                    lineHeight: 1.6,
                    whiteSpace: 'pre-wrap',
                    color: '#e0e0e0',
                    marginBottom: 16,
                  }}
                >
                  {synthesizeResult.summary}
                </div>

                {synthesizeResult.emergent_patterns.length > 0 && (
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ ...styles.label, marginBottom: 8 }}>Emergent Patterns</div>
                    <div style={styles.flexWrap}>
                      {synthesizeResult.emergent_patterns.map((p, i) => (
                        <span
                          key={i}
                          style={{ ...styles.tagCapabilitySelected, cursor: 'default', fontSize: 11 }}
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <button style={styles.btnPrimary} onClick={handleExportResults}>
                  📥 Export Results
                </button>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px 0', color: '#667788' }}>
                Click "Synthesize Results" from the actions panel to aggregate results.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export { SwarmConsolePanel };
export default SwarmConsolePanel;