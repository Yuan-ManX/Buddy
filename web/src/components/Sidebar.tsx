import React, { useState, useMemo } from 'react';
import type { Agent, Conversation, TabView } from '../types';
import { getRoleColor } from '../utils/colors';
import { useTheme } from '../hooks/useTheme';

interface SidebarProps {
  agents: Agent[];
  conversations: Conversation[];
  selectedAgent: Agent | null;
  selectedConv: Conversation | null;
  activeTab: TabView;
  onSelectAgent: (agent: Agent) => void;
  onSelectConv: (conv: Conversation) => void;
  onNewAgent: () => void;
  onNewConv: () => void;
  onDeleteAgent: (agentId: string) => void;
  onEditAgent?: (agent: Agent) => void;
  onDeleteConv: (convId: string) => void;
  onRenameConv?: (convId: string, title: string) => void;
  onSelectTab: (tab: TabView) => void;
}

// Tab categories with grouping
const GLOBAL_TABS: { id: TabView; label: string; icon: string }[] = [
  { id: 'commandCenter', label: 'Command Center', icon: '🏰' },
  { id: 'dashboard', label: 'Dashboard', icon: '📊' },
  { id: 'overview', label: 'Overview', icon: '🔍' },
  { id: 'agent-comparison', label: 'Compare', icon: '⚖️' },
  { id: 'phub', label: 'Hub', icon: '🏗️' },
  { id: 'nexus', label: 'Nexus', icon: '🔗' },
  { id: 'forge', label: 'Forge', icon: '⚒️' },
  { id: 'pipeline', label: 'Pipeline', icon: '🔀' },
  { id: 'capability', label: 'Capability', icon: '🎯' },
  { id: 'kgraph', label: 'K-Graph', icon: '🕸️' },
  { id: 'board', label: 'Board', icon: '📋' },
  { id: 'kanban', label: 'Kanban', icon: '📌' },
  { id: 'compounding', label: 'Compound', icon: '⚡' },
  { id: 'memorysync', label: 'M-Sync', icon: '🔄' },
  { id: 'plugins', label: 'Plugins', icon: '🔌' },
  { id: 'imhub', label: 'IM Hub', icon: '💬' },
  { id: 'marketplace', label: 'Market', icon: '🛒' },
  { id: 'taskqueue', label: 'Queue', icon: '⏳' },
  { id: 'runtimebackend', label: 'Backend', icon: '⚙️' },
  { id: 'guard', label: 'Guard', icon: '🛡️' },
  { id: 'pulse', label: 'Pulse', icon: '💓' },
  { id: 'gateway', label: 'Gateway', icon: '🌐' },
  { id: 'daemon', label: 'Daemon', icon: '👾' },
  { id: 'swarm', label: 'Swarm', icon: '🦾' },
  { id: 'runtime', label: 'Runtime', icon: '🖧' },
  { id: 'scheduler', label: 'Scheduler', icon: '⏰' },
  { id: 'studio', label: 'Studio', icon: '🎨' },
  { id: 'workflow', label: 'Workflow', icon: '📋' },
  { id: 'costs', label: 'Costs', icon: '💰' },
  { id: 'workspaces', label: 'Workspaces', icon: '🗂️' },
  { id: 'agentdashboard', label: 'A-Dash', icon: '📈' },
  { id: 'activity', label: 'Activity', icon: '📡' },
  { id: 'runtimemonitor', label: 'Runtime', icon: '🖥️' },
  { id: 'skillmanager', label: 'S-Manager', icon: '🎛️' },
  { id: 'agentcore', label: 'A-Core', icon: '🧬' },
  { id: 'synthesis', label: 'Synthesis', icon: '🔮' },
  { id: 'intelligence', label: 'Intel', icon: '💡' },
  { id: 'runtimepanel', label: 'Runtime', icon: '⚡' },
  { id: 'skillcompiler', label: 'Skills', icon: '🔧' },
  { id: 'conversationsearch', label: 'Search', icon: '🔍' },
  { id: 'governance', label: 'Governance', icon: '⚖️' },
  { id: 'smartrouter', label: 'Router', icon: '🧭' },
  { id: 'agentmesh', label: 'Mesh', icon: '🕸️' },
  { id: 'learningloop', label: 'Learn', icon: '🧠' },
  { id: 'experience', label: 'Experience', icon: '📊' },
  { id: 'collabspace', label: 'Collab', icon: '🤝' },
  { id: 'contextengine', label: 'Context', icon: '📝' },
  { id: 'automation', label: 'Automation', icon: '⚡' },
  { id: 'skillfabric', label: 'S-Fabric', icon: '🧵' },
  { id: 'usermodel', label: 'User Model', icon: '👤' },
  { id: 'evolvingskills', label: 'E-Skills', icon: '🧬' },
  { id: 'subagentmesh', label: 'S-Mesh', icon: '🕸️' },
  { id: 'protocol', label: 'Protocol', icon: '📡' },
  { id: 'sandbox', label: 'Sandbox', icon: '🏖️' },
  { id: 'toolexec', label: 'Tools', icon: '🔧' },
  { id: 'modelorch', label: 'Models', icon: '🧠' },
  { id: 'deployment', label: 'Deploy', icon: '🚀' },
  { id: 'productcomposer', label: 'Composer', icon: '🎨' },
  { id: 'agentorchestrator', label: 'Orchestrator', icon: '🎭' },
  { id: 'dreammode', label: 'Dream', icon: '🌙' },
  { id: 'whitememory', label: 'W-Memory', icon: '🧠' },
  { id: 'reflection', label: 'Reflection', icon: '🪞' },
  { id: 'intent', label: 'Intent', icon: '🎯' },
  { id: 'fleet', label: 'Fleet', icon: '🚀' },
  { id: 'knowledgenetwork', label: 'K-Network', icon: '🔗' },
  { id: 'reasoning', label: 'Reasoning', icon: '🧠' },
  { id: 'modelproxy', label: 'M-Proxy', icon: '🔀' },
  { id: 'toolcomposer', label: 'T-Compose', icon: '🔧' },
  { id: 'contextmanager', label: 'Context', icon: '📋' },
  { id: 'unifiedconsole', label: 'Console', icon: '🖥️' },
  { id: 'experiments', label: 'Experiments', icon: '🧪' },
  { id: 'goalDecomposer', label: 'Goals', icon: '🎯' },
  { id: 'selfReflection', label: 'Reflect', icon: '🪞' },
  { id: 'memoryConsolidator', label: 'MemConsol', icon: '🧠' },
  { id: 'contextCompressor', label: 'CtxComp', icon: '📦' },
  { id: 'unifiedSystem', label: 'Unified', icon: '🧬' },
  { id: 'knowledgeFabric', label: 'K-Fabric', icon: '🧵' },
  { id: 'collaborativeIntelligence', label: 'CollabAI', icon: '🤝' },
  { id: 'knowledgeGraphViz', label: 'KGraph', icon: '🔗' },
  { id: 'skillExplorer', label: 'Skills', icon: '🧰' },
  { id: 'codeReview', label: 'Review', icon: '🔍' },
  { id: 'swarmConsole', label: 'Swarm', icon: '🐝' },
  { id: 'platformConsole', label: 'Console', icon: '🖥️' },
  { id: 'teamArchitect', label: 'Team', icon: '🏗️' },
  { id: 'evolutionLoop', label: 'Evolve', icon: '🔄' },
  { id: 'proactiveEngine', label: 'Proactive', icon: '🎯' },
  { id: 'sentienceCore', label: 'Sentience', icon: '🧬' },
  { id: 'capabilityMesh', label: 'CapMesh', icon: '🕸️' },
  { id: 'presenceEngine', label: 'Presence', icon: '👁️' },
  { id: 'feedbackOrchestrator', label: 'Feedback', icon: '📡' },
  { id: 'sessionCommander', label: 'Sessions', icon: '📋' },
  { id: 'runtimeScheduler', label: 'Scheduler', icon: '⚡' },
  { id: 'workspaceNexus', label: 'Nexus', icon: '🔗' },
  { id: 'runtimeStore', label: 'R-Store', icon: '💾' },
  { id: 'conversationMemory', label: 'C-Memory', icon: '💭' },
  { id: 'streamingHub', label: 'Stream', icon: '📡' },
  { id: 'toolNetwork', label: 'T-Network', icon: '🌐' },
  { id: 'codeInterpreter', label: 'Code', icon: '💻' },
  { id: 'analyticsEngine', label: 'Analytics', icon: '📊' },
  { id: 'executionCompiler', label: 'E-Compiler', icon: '⚡' },
  { id: 'verificationPipeline', label: 'Verify', icon: '✅' },
  { id: 'modelConductor', label: 'M-Conductor', icon: '🎼' },
  { id: 'contextWeaver', label: 'C-Weaver', icon: '🧶' },
  { id: 'autonomyFramework', label: 'Autonomy', icon: '🛡️' },
  { id: 'intelligenceHub', label: 'IntelHub', icon: '🧿' },
  { id: 'adaptiveWorkflows', label: 'A-Workflow', icon: '🔄' },
  { id: 'crossConnector', label: 'X-Connect', icon: '🔗' },
  { id: 'chainOfThought', label: 'CoT', icon: '🧠' },
  { id: 'intentResolution', label: 'Intent', icon: '🎯' },
  { id: 'dynamicAdaptation', label: 'Adapt', icon: '🔄' },
  { id: 'uncertaintyQuantifier', label: 'Uncertain', icon: '❓' },
  { id: 'federatedKnowledge', label: 'F-Know', icon: '🌐' },
  { id: 'emergentBehavior', label: 'Emergent', icon: '🔮' },
  { id: 'performanceAutotuner', label: 'AutoTune', icon: '⚡' },
  { id: 'platformResilience', label: 'Resilient', icon: '🛡️' },
  { id: 'personalMemory', label: 'Memory', icon: '🧠' },
  { id: 'voiceInterface', label: 'Voice', icon: '🎤' },
  { id: 'documentIntelligence', label: 'Docs', icon: '📄' },
  { id: 'notificationHub', label: 'Alerts', icon: '🔔' },
  { id: 'promptStudio', label: 'Prompts', icon: '✍️' },
  { id: 'terminalInterface', label: 'Terminal', icon: '💻' },
  { id: 'reasoningNetwork', label: 'Reasoning', icon: '🧠' },
  { id: 'synthesisEngine', label: 'Synthesis', icon: '🔮' },
  { id: 'researchEngine', label: 'Research', icon: '🔬' },
  { id: 'learningLoop', label: 'Learn', icon: '📚' },
  { id: 'memoryGraph', label: 'M-Graph', icon: '🕸️' },
  { id: 'understandingEngine', label: 'Understand', icon: '🔍' },
  { id: 'hypothesisEngine', label: 'Hypothesis', icon: '🔬' },
  { id: 'negotiation', label: 'Negotiate', icon: '🤝' },
  { id: 'aiTwin', label: 'AI Twin', icon: '👥' },
  { id: 'codeSynthesis', label: 'CodeGen', icon: '💻' },
  { id: 'workflowComposer', label: 'W-Composer', icon: '🎼' },
  { id: 'skillForge', label: 'SkillForge', icon: '⚒️' },
  { id: 'policyGateway', label: 'Policy', icon: '🛡️' },
  { id: 'dreamConsolidator', label: 'Dream', icon: '💭' },
  { id: 'crossReview', label: 'X-Review', icon: '🔍' },
  { id: 'costOptimizer', label: 'Cost Opt', icon: '💰' },
  { id: 'lifecycleHooks', label: 'Hooks', icon: '🪝' },
  { id: 'sessionFork', label: 'Fork', icon: '🔀' },
  { id: 'alignmentEngine', label: 'Align', icon: '🎯' },
  { id: 'contextProvider', label: 'Provider', icon: '📡' },
  { id: 'interruptibleExec', label: 'Exec', icon: '🛑' },
  { id: 'actionSpace', label: 'Actions', icon: '⚡' },
  { id: 'goalManager', label: 'Goals', icon: '🎯' },
  { id: 'dialogueManager', label: 'Dialogue', icon: '💬' },
  { id: 'benchmarkEngine', label: 'Bench', icon: '📊' },
  { id: 'beliefEngine', label: 'Belief', icon: '🧠' },
  { id: 'tracingPipeline', label: 'Trace', icon: '🔍' },
  { id: 'quotaManager', label: 'Quota', icon: '🚦' },
  { id: 'causalEngine', label: 'Causal', icon: '🔗' },
  { id: 'temporalEngine', label: 'Temporal', icon: '📅' },
  { id: 'anomalyDetector', label: 'Anomaly', icon: '🚨' },
  { id: 'scenarioSimulator', label: 'Scenario', icon: '🎯' },
  { id: 'explanationSynthesizer', label: 'Explain', icon: '💡' },
  { id: 'knowledgeDistiller', label: 'Distill', icon: '🎓' },
  { id: 'attentionAllocator', label: 'Attention', icon: '🔬' },
  { id: 'ethicalDeliberation', label: 'Ethics', icon: '🛡' },
  { id: 'conceptFormation', label: 'Concept', icon: '🧩' },
  { id: 'analogyEngine', label: 'Analogy', icon: '🔄' },
  { id: 'curiosityEngine', label: 'Curiosity', icon: '🔍' },
  { id: 'mentalSimulation', label: 'Mental', icon: '🧠' },
  { id: 'narrativeEngine', label: 'Narrative', icon: '📖' },
  { id: 'cognitiveMapping', label: 'C-Map', icon: '🗺️' },
  { id: 'biasDetector', label: 'Bias', icon: '⚠️' },
  { id: 'cognitiveAffordance', label: 'Afford', icon: '🎯' },
  { id: 'cognitiveScaffolding', label: 'Scaffold', icon: '🏗️' },
  { id: 'affectiveEngine', label: 'Affect', icon: '💖' },
  { id: 'cognitiveStyleTransfer', label: 'Style', icon: '🎨' },
  { id: 'cognitivePrime', label: 'Prime', icon: '⚡' },
  { id: 'cognitivePhaseTransition', label: 'Phase', icon: '🔄' },
  { id: 'cognitiveGravity', label: 'Gravity', icon: '🪐' },
  { id: 'cognitiveResonance', label: 'Resonance', icon: '🌊' },
  { id: 'cognitiveWorkload', label: 'Workload', icon: '⚖️' },
  { id: 'cognitiveEntropy', label: 'Entropy', icon: '🔀' },
  { id: 'cognitiveHorizon', label: 'Horizon', icon: '🌅' },
  { id: 'cognitiveMomentum', label: 'Momentum', icon: '🚀' },
  { id: 'cognitiveFriction', label: 'Friction', icon: '🧱' },
  { id: 'cognitiveTension', label: 'Tension', icon: '⚡' },
  { id: 'cognitiveDepth', label: 'Depth', icon: '🌊' },
  { id: 'cognitiveCoherence', label: 'Coherence', icon: '🔗' },
  { id: 'cognitiveRhythm', label: 'Rhythm', icon: '🎵' },
  { id: 'cognitiveDiffusion', label: 'Diffusion', icon: '🌊' },
  { id: 'cognitiveSymbology', label: 'Symbology', icon: '🔣' },
  { id: 'cognitiveCatalyst', label: 'Catalyst', icon: '⚡' },
  { id: 'cognitiveRefraction', label: 'Refraction', icon: '🔎' },
  { id: 'cognitiveOsmosis', label: 'Osmosis', icon: '🧬' },
  { id: 'cognitiveBuoyancy', label: 'Buoyancy', icon: '🎈' },
  { id: 'cognitiveImmunity', label: 'Immunity', icon: '🛡️' },
  { id: 'cognitiveViscosity', label: 'Viscosity', icon: '🌊' },
  { id: 'cognitivePolarization', label: 'Polarization', icon: '🧭' },
  { id: 'cognitiveInertia', label: 'Inertia', icon: '⚖️' },
  { id: 'cognitiveTurbulence', label: 'Turbulence', icon: '🌪️' },
  { id: 'cognitiveCadence', label: 'Cadence', icon: '🎵' },
  { id: 'cognitiveDrift', label: 'Drift', icon: '🌊' },
  { id: 'cognitiveResilience', label: 'Resilience', icon: '🛡️' },
  { id: 'cognitiveLattice', label: 'Lattice', icon: '💎' },
  { id: 'cognitiveSingularity', label: 'Singularity', icon: '✨' },
  { id: 'cognitivePlasticity', label: 'Plasticity', icon: '🧶' },
  { id: 'cognitiveElasticity', label: 'Elasticity', icon: '🤸' },
  { id: 'cognitivePermeability', label: 'Permeability', icon: '🕳️' },
  { id: 'cognitiveFluidity', label: 'Fluidity', icon: '💧' },
  { id: 'cognitiveSolidity', label: 'Solidity', icon: '🪨' },
  { id: 'cognitiveEquilibrium', label: 'Equilibrium', icon: '⚖️' },
  { id: 'cognitiveCohesion', label: 'Cohesion', icon: '🔗' },
  { id: 'cognitiveSymmetry', label: 'Symmetry', icon: '🪞' },
  { id: 'cognitiveTexture', label: 'Texture', icon: '🎨' },
  { id: 'cognitiveGradient', label: 'Gradient', icon: '📉' },
];

const AGENT_TABS: { id: TabView; label: string; icon: string }[] = [
  { id: 'chat', label: 'Chat', icon: '💬' },
  { id: 'tasks', label: 'Tasks', icon: '📋' },
  { id: 'skills', label: 'Skills', icon: '🧩' },
  { id: 'memory', label: 'Memory', icon: '🧠' },
  { id: 'identity', label: 'Identity', icon: '🪪' },
  { id: 'agentself', label: 'Self', icon: '🪞' },
  { id: 'autopilot', label: 'Auto', icon: '🤖' },
  { id: 'subagents', label: 'Workers', icon: '👥' },
  { id: 'tools', label: 'Tools', icon: '🔧' },
  { id: 'plans', label: 'Plans', icon: '📐' },
  { id: 'workspace', label: 'Workspace', icon: '📁' },
  { id: 'dream', label: 'Dream', icon: '🌙' },
  { id: 'mcp', label: 'MCP', icon: '🔌' },
  { id: 'collaboration', label: 'Collab', icon: '🤝' },
  { id: 'squads', label: 'Squads', icon: '⚔️' },
  { id: 'trajectory', label: 'Trace', icon: '📍' },
  { id: 'approval', label: 'Approval', icon: '✅' },
  { id: 'events', label: 'Events', icon: '📡' },
  { id: 'persona', label: 'Persona', icon: '🎭' },
  { id: 'learning', label: 'Learn', icon: '📚' },
  { id: 'knowledge', label: 'Knowledge', icon: '📖' },
  { id: 'proactive', label: 'Proactive', icon: '🎯' },
  { id: 'metacognition', label: 'Meta', icon: '🧠' },
  { id: 'evolution', label: 'Evolution', icon: '🧬' },
  { id: 'identitycore', label: 'ID-Core', icon: '🧬' },
];

export const Sidebar: React.FC<SidebarProps> = ({
  agents,
  conversations,
  selectedAgent,
  selectedConv,
  activeTab,
  onSelectAgent,
  onSelectConv,
  onNewAgent,
  onNewConv,
  onDeleteAgent,
  onEditAgent,
  onDeleteConv,
  onRenameConv,
  onSelectTab,
}) => {
  const { mode, toggle: toggleTheme, isDark } = useTheme();
  const [agentSearch, setAgentSearch] = useState('');
  const [convSearch, setConvSearch] = useState('');
  const [tabsExpanded, setTabsExpanded] = useState(true);
  const [agentTabsExpanded, setAgentTabsExpanded] = useState(true);

  const filteredAgents = useMemo(
    () =>
      agentSearch.trim()
        ? agents.filter(
            (a) =>
              a.name.toLowerCase().includes(agentSearch.toLowerCase()) ||
              a.role.toLowerCase().includes(agentSearch.toLowerCase())
          )
        : agents,
    [agents, agentSearch]
  );

  const filteredConvs = useMemo(
    () =>
      convSearch.trim()
        ? conversations.filter((c) =>
            c.title.toLowerCase().includes(convSearch.toLowerCase())
          )
        : conversations,
    [conversations, convSearch]
  );

  return (
    <aside className="sidebar">
      {/* Header */}
      <div className="sidebar-header">
        <div className="sidebar-logo" onClick={() => onSelectTab('dashboard')} style={{ cursor: 'pointer' }}>
          <span className="sidebar-logo-icon">B</span>
          <span className="sidebar-logo-text">Buddy</span>
        </div>
      </div>

      {/* Global Tabs */}
      <div className="sidebar-section">
        <button
          className="sidebar-collapse-header"
          onClick={() => setTabsExpanded(!tabsExpanded)}
        >
          <span className={`sidebar-collapse-arrow ${tabsExpanded ? 'expanded' : ''}`}>▾</span>
          <span className="sidebar-section-title">System</span>
        </button>
        {tabsExpanded && (
          <div className="sidebar-tabs-grid">
            {GLOBAL_TABS.map((tab) => (
              <button
                key={tab.id}
                className={`sidebar-tab-icon ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => onSelectTab(tab.id)}
                title={tab.label}
              >
                <span className="sidebar-tab-emoji">{tab.icon}</span>
                <span className="sidebar-tab-label">{tab.label}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Agent-specific tabs */}
      {selectedAgent && (
        <div className="sidebar-section">
          <button
            className="sidebar-collapse-header"
            onClick={() => setAgentTabsExpanded(!agentTabsExpanded)}
          >
            <span className={`sidebar-collapse-arrow ${agentTabsExpanded ? 'expanded' : ''}`}>▾</span>
            <span className="sidebar-section-title">Agent Tools</span>
          </button>
          {agentTabsExpanded && (
            <div className="sidebar-tabs-grid">
              {AGENT_TABS.map((tab) => (
                <button
                  key={tab.id}
                  className={`sidebar-tab-icon ${activeTab === tab.id ? 'active' : ''}`}
                  onClick={() => onSelectTab(tab.id)}
                  title={tab.label}
                >
                  <span className="sidebar-tab-emoji">{tab.icon}</span>
                  <span className="sidebar-tab-label">{tab.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Agents section */}
      <div className="sidebar-section">
        <div className="sidebar-section-header">
          <span className="sidebar-section-title">Agents</span>
          <button className="sidebar-add-btn" onClick={onNewAgent} title="Create Agent">
            +
          </button>
        </div>
        <div className="sidebar-search-wrapper">
          <input
            className="sidebar-search-input"
            type="text"
            placeholder="Search agents..."
            value={agentSearch}
            onChange={(e) => setAgentSearch(e.target.value)}
          />
        </div>
        <div className="sidebar-list">
          {filteredAgents.map((agent) => (
            <div
              key={agent.id}
              className={`sidebar-item ${selectedAgent?.id === agent.id && !selectedConv ? 'active' : ''}`}
              onClick={() => onSelectAgent(agent)}
            >
              <div className="sidebar-avatar" style={{ background: getRoleColor(agent.role) }}>
                {agent.name.charAt(0).toUpperCase()}
              </div>
              <div className="sidebar-item-info">
                <div className="sidebar-item-name">{agent.name}</div>
                <div className="sidebar-item-role">
                  <span className={`agent-status-dot ${agent.is_active ? 'active' : 'inactive'}`} />
                  {agent.role}
                </div>
              </div>
              {onEditAgent && (
                <button
                  className="sidebar-item-edit"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEditAgent(agent);
                  }}
                  title="Edit Agent"
                >
                  &#9998;
                </button>
              )}
              <button
                className="sidebar-item-delete"
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm(`Delete agent "${agent.name}"?`)) {
                    onDeleteAgent(agent.id);
                  }
                }}
                title="Delete Agent"
              >
                ×
              </button>
            </div>
          ))}
          {agents.length === 0 && (
            <div className="sidebar-empty">No agents yet. Create one to get started.</div>
          )}
        </div>
      </div>

      <div className="sidebar-divider" />

      {/* Conversations section */}
      <div className="sidebar-section sidebar-convs">
        <div className="sidebar-section-header">
          <span className="sidebar-section-title">Conversations</span>
          <button className="sidebar-add-btn" onClick={onNewConv} title="New Conversation">
            +
          </button>
        </div>
        <div className="sidebar-search-wrapper">
          <input
            className="sidebar-search-input"
            type="text"
            placeholder="Search conversations..."
            value={convSearch}
            onChange={(e) => setConvSearch(e.target.value)}
          />
        </div>
        <div className="sidebar-list sidebar-conv-list">
          {filteredConvs.map((conv) => (
            <div
              key={conv.id}
              className={`sidebar-item ${selectedConv?.id === conv.id ? 'active' : ''}`}
              onClick={() => onSelectConv(conv)}
            >
              <div className="sidebar-item-info">
                <div className="sidebar-item-name">{conv.title}</div>
                <div className="sidebar-item-role">
                  {new Date(conv.updated_at).toLocaleDateString()}
                </div>
              </div>
              {onRenameConv && (
                <button
                  className="sidebar-item-edit"
                  onClick={(e) => {
                    e.stopPropagation();
                    const newTitle = prompt('Rename conversation:', conv.title);
                    if (newTitle && newTitle.trim()) {
                      onRenameConv(conv.id, newTitle.trim());
                    }
                  }}
                  title="Rename"
                >
                  &#9998;
                </button>
              )}
              <button
                className="sidebar-item-delete"
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm('Delete this conversation?')) {
                    onDeleteConv(conv.id);
                  }
                }}
                title="Delete Conversation"
              >
                ×
              </button>
            </div>
          ))}
          {conversations.length === 0 && (
            <div className="sidebar-empty">No conversations yet.</div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-status">
          <span className="sidebar-status-dot" />
          <span>System Online</span>
          <button
            className="sidebar-theme-toggle"
            onClick={toggleTheme}
            title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
          >
            {isDark ? '☀️' : '🌙'}
          </button>
          <span className="sidebar-shortcut-hint">⌘K</span>
        </div>
      </div>
    </aside>
  );
};