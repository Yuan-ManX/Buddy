import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';
import { TaskDashboard } from './components/TaskDashboard';
import { SkillPanel } from './components/SkillPanel';
import { MemoryViewer } from './components/MemoryViewer';
import { AutopilotPanel } from './components/AutopilotPanel';
import { SubAgentPanel } from './components/SubAgentPanel';
import { ToolPanel } from './components/ToolPanel';
import { PlanView } from './components/PlanView';
import { WorkspaceViewer } from './components/WorkspaceViewer';
import { DreamPanel } from './components/DreamPanel';
import { MCPServerPanel } from './components/MCPServerPanel';
import { CollaborationPanel } from './components/CollaborationPanel';
import { SystemOverview } from './components/SystemOverview';
import { AgentComparison } from './components/AgentComparison';
import ApprovalPanel from './components/ApprovalPanel';
import EventMonitor from './components/EventMonitor';
import Dashboard from './components/Dashboard';
import { NexusPanel } from './components/NexusPanel';
import { ForgePanel } from './components/ForgePanel';
import { IdentityPanel } from './components/IdentityPanel';
import { TrajectoryPanel } from './components/TrajectoryPanel';
import { SquadsPanel } from './components/SquadsPanel';
import { GuardPanel } from './components/GuardPanel';
import { PulsePanel } from './components/PulsePanel';
import { PersonaPanel } from './components/PersonaPanel';
import { LearningPanel } from './components/LearningPanel';
import { GatewayPanel } from './components/GatewayPanel';
import { DaemonPanel } from './components/DaemonPanel';
import { SwarmPanel } from './components/SwarmPanel';
import { KnowledgeBasePanel } from './components/KnowledgeBasePanel';
import { RuntimeHubPanel } from './components/RuntimeHubPanel';
import { SchedulerPanel } from './components/SchedulerPanel';
import { StudioPanel } from './components/StudioPanel';
import { WorkflowPanel } from './components/WorkflowPanel';
import { IssueBoardPanel } from './components/IssueBoardPanel';
import { CompoundingPanel } from './components/CompoundingPanel';
import { PipelinePanel } from './components/PipelinePanel';
import { CapabilityPanel } from './components/CapabilityPanel';
import { KnowledgeGraphPanel } from './components/KnowledgeGraphPanel';
import { MemorySyncPanel } from './components/MemorySyncPanel';
import { PlatformHubPanel } from './components/PlatformHubPanel';
import { CostAnalyticsPanel } from './components/CostAnalyticsPanel';
import { WorkspacePanel } from './components/WorkspacePanel';
import { AgentDashboard } from './components/AgentDashboard';
import { GovernancePanel } from './components/GovernancePanel';
import { SmartRouterPanel } from './components/SmartRouterPanel';
import { AgentMeshPanel } from './components/AgentMeshPanel';
import { LearningLoopPanel } from './components/LearningLoopPanel';
import { IdentityCorePanel } from './components/IdentityCorePanel';
import { ExperiencePanel } from './components/ExperiencePanel';
import { CollabSpacePanel } from './components/CollabSpacePanel';
import { ContextEnginePanel } from './components/ContextEnginePanel';
import { AutomationPanel } from './components/AutomationPanel';
import { SkillFabricPanel } from './components/SkillFabricPanel';
import { UserModelPanel } from './components/UserModelPanel';
import { EvolvingSkillsPanel } from './components/EvolvingSkillsPanel';
import { SubAgentMeshPanel } from './components/SubAgentMeshPanel';
import { ProtocolPanel } from './components/ProtocolPanel';
import { SandboxPanel } from './components/SandboxPanel';
import { ToolExecutorPanel } from './components/ToolExecutorPanel';
import { ModelOrchestratorPanel } from './components/ModelOrchestratorPanel';
import { DeploymentPanel } from './components/DeploymentPanel';
import { ProductComposerPanel } from './components/ProductComposerPanel';
import { AgentOrchestratorPanel } from './components/AgentOrchestratorPanel';
import { DreamModePanel } from './components/DreamModePanel';
import { WhiteMemoryPanel } from './components/WhiteMemoryPanel';
import { ReflectionPanel } from './components/ReflectionPanel';
import { IntentPanel } from './components/IntentPanel';
import { FleetPanel } from './components/FleetPanel';
import { KnowledgeNetworkPanel } from './components/KnowledgeNetworkPanel';
import { ProactiveDiscoveryPanel } from './components/ProactiveDiscoveryPanel';
import { MetaCognitionPanel } from './components/MetaCognitionPanel';
import { EvolutionPanel } from './components/EvolutionPanel';
import { AgentSelfPanel } from './components/AgentSelfPanel';
import { PluginSystemPanel } from './components/PluginSystemPanel';
import { IMHubPanel } from './components/IMHubPanel';
import { MarketplacePanel } from './components/MarketplacePanel';
import { TaskQueuePanel } from './components/TaskQueuePanel';
import { RuntimeBackendPanel } from './components/RuntimeBackendPanel';
import { KanbanBoard } from './components/KanbanBoard';
import { ActivityTimeline } from './components/ActivityTimeline';
import { RuntimeMonitor } from './components/RuntimeMonitor';
import { SkillManager } from './components/SkillManager';
import { StatusBar } from './components/StatusBar';
import { AgentCorePanel } from './components/AgentCorePanel';
import { SynthesisPanel } from './components/SynthesisPanel';
import { IntelligencePanel } from './components/IntelligencePanel';
import { RuntimePanel } from './components/RuntimePanel';
import { SkillCompilerPanel } from './components/SkillCompilerPanel';
import { ConversationSearchPanel } from './components/ConversationSearchPanel';
import { ReasoningPanel } from './components/ReasoningPanel';
import { ModelProxyPanel } from './components/ModelProxyPanel';
import { ToolComposerPanel } from './components/ToolComposerPanel';
import { ContextManagerPanel } from './components/ContextManagerPanel';
import { UnifiedConsole } from './components/UnifiedConsole';
import { ExperimentPanel } from './components/ExperimentPanel';
import { UnifiedBrainPanel } from './components/UnifiedBrainPanel';
import { PlatformCorePanel } from './components/PlatformCorePanel';

import { UnifiedAgentPanel } from './components/UnifiedAgentPanel';
import { AgentFlowPanel } from './components/AgentFlowPanel';
import { ProfilePanel } from './components/ProfilePanel';
import { MCPToolsPanel } from './components/MCPToolsPanel';
import { GoalDecomposerPanel } from './components/GoalDecomposerPanel';
import { SelfReflectionPanel } from './components/SelfReflectionPanel';
import { MemoryConsolidatorPanel } from './components/MemoryConsolidatorPanel';
import { ContextCompressorPanel } from './components/ContextCompressorPanel';
import { AgentCommandCenter } from './components/AgentCommandCenter';
import { UnifiedSystemPanel } from './components/UnifiedSystemPanel';
import { KnowledgeFabricPanel } from './components/KnowledgeFabricPanel';
import { CollaborativeIntelligencePanel } from './components/CollaborativeIntelligencePanel';
import { KnowledgeGraphViz } from './components/KnowledgeGraphViz';
import { SkillExplorer } from './components/SkillExplorer';
import { CodeReviewPanel } from './components/CodeReviewPanel';
import { SwarmConsolePanel } from './components/SwarmConsolePanel';
import { PlatformConsolePanel } from './components/PlatformConsolePanel';
import { TeamArchitectPanel } from './components/TeamArchitectPanel';
import { EvolutionLoopPanel } from './components/EvolutionLoopPanel';
import { ProactiveEnginePanel } from './components/ProactiveEnginePanel';
import { SentienceCorePanel } from './components/SentienceCorePanel';
import { CapabilityMeshPanel } from './components/CapabilityMeshPanel';
import { PresenceEnginePanel } from './components/PresenceEnginePanel';
import { FeedbackOrchestratorPanel } from './components/FeedbackOrchestratorPanel';
import { SessionCommanderPanel } from './components/SessionCommanderPanel';
import { RuntimeSchedulerPanel } from './components/RuntimeSchedulerPanel';
import { WorkspaceNexusPanel } from './components/WorkspaceNexusPanel';
import { ExecutionCompilerPanel } from './components/ExecutionCompilerPanel';
import { VerificationPipelinePanel } from './components/VerificationPipelinePanel';
import { ModelConductorPanel } from './components/ModelConductorPanel';
import { ContextWeaverPanel } from './components/ContextWeaverPanel';
import { AutonomyFrameworkPanel } from './components/AutonomyFrameworkPanel';
import { IntelligenceHubPanel } from './components/IntelligenceHubPanel';
import { AdaptiveWorkflowsPanel } from './components/AdaptiveWorkflowsPanel';
import { CrossConnectorPanel } from './components/CrossConnectorPanel';
import { ChainOfThoughtPanel } from './components/ChainOfThoughtPanel';
import { IntentResolutionPanel } from './components/IntentResolutionPanel';
import { DynamicAdaptationPanel } from './components/DynamicAdaptationPanel';
import { UncertaintyQuantifierPanel } from './components/UncertaintyQuantifierPanel';
import { FederatedKnowledgePanel } from './components/FederatedKnowledgePanel';
import { EmergentBehaviorPanel } from './components/EmergentBehaviorPanel';
import { PerformanceAutotunerPanel } from './components/PerformanceAutotunerPanel';
import { PlatformResiliencePanel } from './components/PlatformResiliencePanel';
import ErrorBoundary from './components/ErrorBoundary';
import { ToastProvider } from './components/Toast';
import { CommandPalette } from './components/CommandPalette';

import { api } from './api/client';
import type { Agent, Conversation, Message as MsgType, Task, TabView } from './types';
import './App.css';

export default function App() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [selectedConv, setSelectedConv] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<MsgType[]>([]);
  const [activeTab, setActiveTab] = useState<TabView>('chat');
  const [showNewAgent, setShowNewAgent] = useState(false);
  const [newAgentForm, setNewAgentForm] = useState({
    name: '',
    role: 'custom' as string,
    personality: 'friendly and helpful',
    instructions: '',
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [editForm, setEditForm] = useState({ name: '', role: '', personality: '', instructions: '' });
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [agentRes, convRes, taskRes] = await Promise.all([
        api.agents.list(),
        api.conversations.list(),
        api.tasks.list({ page_size: 50 }),
      ]);
      setAgents(agentRes.items);
      setConversations(convRes.items);
      setTasks(taskRes.items);
      if (agentRes.items.length > 0 && !selectedAgent) {
        setSelectedAgent(agentRes.items[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
      if (e.key === 'Escape') {
        setCommandPaletteOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (selectedConv) {
      api.conversations.messages(selectedConv.id).then((res) => setMessages(res.items)).catch(console.error);
    } else if (selectedAgent) {
      setMessages([]);
    }
  }, [selectedConv, selectedAgent]);

  const handleCreateAgent = async () => {
    if (!newAgentForm.name.trim()) return;
    try {
      const agent = await api.agents.create(newAgentForm);
      setAgents((prev) => [agent, ...prev]);
      setSelectedAgent(agent);
      setSelectedConv(null);
      setShowNewAgent(false);
      setNewAgentForm({ name: '', role: 'custom', personality: 'friendly and helpful', instructions: '' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create agent');
    }
  };

  const handleDeleteAgent = async (agentId: string) => {
    try {
      await api.agents.delete(agentId);
      setAgents((prev) => {
        const filtered = prev.filter((a) => a.id !== agentId);
        if (selectedAgent?.id === agentId) {
          setSelectedAgent(filtered.length > 0 ? filtered[0] : null);
          setSelectedConv(null);
          setMessages([]);
        }
        return filtered;
      });
      setConversations((prev) => prev.filter((c) => !c.agent_ids.includes(agentId)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete agent');
    }
  };

  const handleOpenEdit = useCallback((agent: Agent) => {
    setEditingAgent(agent);
    setEditForm({
      name: agent.name,
      role: agent.role,
      personality: agent.personality,
      instructions: agent.instructions,
    });
    setShowEditModal(true);
  }, []);

  const handleUpdateAgent = async () => {
    if (!editingAgent || !editForm.name.trim()) return;
    try {
      const updated = await api.agents.update(editingAgent.id, {
        name: editForm.name,
        role: editForm.role,
        personality: editForm.personality,
        instructions: editForm.instructions,
      });
      setAgents((prev) => prev.map((a) => (a.id === updated.id ? { ...a, ...updated } : a)));
      if (selectedAgent?.id === updated.id) {
        setSelectedAgent((prev) => prev ? { ...prev, ...updated } : null);
      }
      setShowEditModal(false);
      setEditingAgent(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update agent');
    }
  };

  const handleRenameConv = async (convId: string, title: string) => {
    try {
      await api.conversations.update(convId, { title });
      setConversations((prev) => prev.map((c) => (c.id === convId ? { ...c, title } : c)));
      if (selectedConv?.id === convId) {
        setSelectedConv((prev) => prev ? { ...prev, title } : null);
      }
    } catch {
      // silently fail
    }
  };

  const handleDeleteConv = async (convId: string) => {
    try {
      await api.conversations.delete(convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (selectedConv?.id === convId) {
        setSelectedConv(null);
        setMessages([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete conversation');
    }
  };

  const handleCreateConv = async () => {
    try {
      const conv = await api.conversations.create({
        title: `Chat ${new Date().toLocaleTimeString()}`,
        agent_ids: selectedAgent ? [selectedAgent.id] : [],
      });
      setConversations((prev) => [conv, ...prev]);
      setSelectedConv(conv);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create conversation');
    }
  };

  // Command palette actions
  const commandActions = useMemo(() => [
    { id: 'new-agent', label: 'Create Agent', description: 'Create a new AI agent', category: 'Agents', action: () => setShowNewAgent(true) },
    { id: 'new-conv', label: 'New Conversation', description: 'Start a new chat conversation', category: 'Chat', action: handleCreateConv },
    { id: 'go-chat', label: 'Go to Chat', description: 'Open the chat view', category: 'Navigation', action: () => setActiveTab('chat') },
    { id: 'go-dashboard', label: 'Go to Dashboard', description: 'View system dashboard', category: 'Navigation', action: () => setActiveTab('dashboard') },
    { id: 'go-tasks', label: 'Go to Tasks', description: 'View task dashboard', category: 'Navigation', action: () => setActiveTab('tasks') },
    { id: 'go-memory', label: 'Go to Memory', description: 'View agent memory', category: 'Navigation', action: () => setActiveTab('memory') },
    { id: 'go-skills', label: 'Go to Skills', description: 'Manage agent skills', category: 'Navigation', action: () => setActiveTab('skills') },
    { id: 'go-tools', label: 'Go to Tools', description: 'Browse available tools', category: 'Navigation', action: () => setActiveTab('tools') },
    { id: 'go-squads', label: 'Go to Squads', description: 'Manage agent squads', category: 'Navigation', action: () => setActiveTab('squads') },
    { id: 'go-forge', label: 'Go to Forge', description: 'Skill creation forge', category: 'Navigation', action: () => setActiveTab('forge') },
    { id: 'go-guard', label: 'Go to Guard', description: 'Safety & monitoring', category: 'Navigation', action: () => setActiveTab('guard') },
    { id: 'go-swarm', label: 'Go to Swarm', description: 'Agent swarm engine', category: 'Navigation', action: () => setActiveTab('swarm') },
    { id: 'go-knowledge', label: 'Go to Knowledge Base', description: 'RAG knowledge management', category: 'Navigation', action: () => setActiveTab('knowledge') },
    { id: 'go-nexus', label: 'Go to Nexus', description: 'Coordination hub', category: 'Navigation', action: () => setActiveTab('nexus') },
    { id: 'go-goals', label: 'Go to Goals', description: 'Goal decomposition engine', category: 'Navigation', action: () => setActiveTab('goalDecomposer') },
    { id: 'go-reflect', label: 'Go to Self-Reflection', description: 'Agent self-reflection', category: 'Navigation', action: () => setActiveTab('selfReflection') },
    { id: 'go-memconsol', label: 'Go to Memory Consolidator', description: 'Memory consolidation', category: 'Navigation', action: () => setActiveTab('memoryConsolidator') },
    { id: 'go-ctxcomp', label: 'Go to Context Compressor', description: 'Context compression', category: 'Navigation', action: () => setActiveTab('contextCompressor') },
    { id: 'refresh', label: 'Refresh Data', description: 'Reload all data from server', category: 'System', action: () => { loadData(); } },
  ], [handleCreateConv, loadData]);

  const handleConversationCreated = useCallback(async (convId: string) => {
    try {
      const convList = await api.conversations.list();
      setConversations(convList.items);
      const newConv = convList.items.find((c) => c.id === convId);
      if (newConv) {
        setSelectedConv(newConv);
      }
    } catch {
      // silently fail
    }
  }, []);

  const handleTaskCreated = useCallback(async () => {
    try {
      const taskRes = await api.tasks.list({ page_size: 50 });
      setTasks(taskRes.items);
    } catch {}
  }, []);

  const handleSelectAgent = useCallback((agent: Agent) => {
    setSelectedAgent(agent);
    setSelectedConv(null);
    setMessages([]);
    setActiveTab('chat');
  }, []);

  if (loading) {
    return (
      <div className="app-loading">
        <div className="app-loading-logo">B</div>
        <div className="app-loading-text">Buddy</div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <ToastProvider>
        <CommandPalette
          isOpen={commandPaletteOpen}
          onClose={() => setCommandPaletteOpen(false)}
          actions={commandActions}
        />
        <div className="app">
      <StatusBar />
      <Sidebar
        agents={agents}
        conversations={conversations}
        selectedAgent={selectedAgent}
        selectedConv={selectedConv}
        activeTab={activeTab}
        onSelectAgent={handleSelectAgent}
        onSelectConv={(c) => { setSelectedConv(c); setActiveTab('chat'); }}
        onNewAgent={() => setShowNewAgent(true)}
        onNewConv={handleCreateConv}
        onDeleteAgent={handleDeleteAgent}
        onEditAgent={handleOpenEdit}
        onDeleteConv={handleDeleteConv}
        onRenameConv={handleRenameConv}
        onSelectTab={setActiveTab}
      />

      <main className="main">
        {error && (
          <div className="app-error">
            <span>{error}</span>
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        {showNewAgent && (
          <div className="modal-overlay" onClick={() => setShowNewAgent(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <h2>Create New Agent</h2>
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  placeholder="Agent name"
                  value={newAgentForm.name}
                  onChange={(e) => setNewAgentForm({ ...newAgentForm, name: e.target.value })}
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select
                  value={newAgentForm.role}
                  onChange={(e) => setNewAgentForm({ ...newAgentForm, role: e.target.value })}
                >
                  <option value="strategy">Strategy</option>
                  <option value="engineering">Engineering</option>
                  <option value="design">Design</option>
                  <option value="research">Research</option>
                  <option value="writing">Writing</option>
                  <option value="companion">Companion</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
              <div className="form-group">
                <label>Personality</label>
                <input
                  type="text"
                  placeholder="e.g., friendly and helpful"
                  value={newAgentForm.personality}
                  onChange={(e) => setNewAgentForm({ ...newAgentForm, personality: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Instructions</label>
                <textarea
                  placeholder="Special instructions for this agent..."
                  value={newAgentForm.instructions}
                  onChange={(e) => setNewAgentForm({ ...newAgentForm, instructions: e.target.value })}
                  rows={3}
                />
              </div>
              <div className="modal-actions">
                <button className="btn-secondary" onClick={() => setShowNewAgent(false)}>
                  Cancel
                </button>
                <button className="btn-primary" onClick={handleCreateAgent}>
                  Create Agent
                </button>
              </div>
            </div>
          </div>
        )}

        {showEditModal && editingAgent && (
          <div className="modal-overlay" onClick={() => { setShowEditModal(false); setEditingAgent(null); }}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <h2>Edit Agent</h2>
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  placeholder="Agent name"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select
                  value={editForm.role}
                  onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                >
                  <option value="strategy">Strategy</option>
                  <option value="engineering">Engineering</option>
                  <option value="design">Design</option>
                  <option value="research">Research</option>
                  <option value="writing">Writing</option>
                  <option value="companion">Companion</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
              <div className="form-group">
                <label>Personality</label>
                <input
                  type="text"
                  placeholder="e.g., friendly and helpful"
                  value={editForm.personality}
                  onChange={(e) => setEditForm({ ...editForm, personality: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Instructions</label>
                <textarea
                  placeholder="Special instructions for this agent..."
                  value={editForm.instructions}
                  onChange={(e) => setEditForm({ ...editForm, instructions: e.target.value })}
                  rows={3}
                />
              </div>
              <div className="modal-actions">
                <button className="btn-secondary" onClick={() => { setShowEditModal(false); setEditingAgent(null); }}>
                  Cancel
                </button>
                <button className="btn-primary" onClick={handleUpdateAgent}>
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'commandCenter' && <AgentCommandCenter onNavigate={(tab: string) => setActiveTab(tab as TabView)} />}

        {/* Global panels — no agent required */}
          {activeTab === 'overview' && <SystemOverview onNavigate={setActiveTab} />}
          {activeTab === 'dashboard' && <Dashboard />}
          {activeTab === 'agent-comparison' && <AgentComparison agents={agents} />}
          {activeTab === 'nexus' && <NexusPanel />}
          {activeTab === 'forge' && <ForgePanel />}
          {activeTab === 'guard' && <GuardPanel />}
          {activeTab === 'pulse' && <PulsePanel />}
          {activeTab === 'gateway' && <GatewayPanel />}
          {activeTab === 'daemon' && <DaemonPanel />}
        {activeTab === 'swarm' && <SwarmPanel agents={agents} />}
        {activeTab === 'runtime' && <RuntimeHubPanel />}
        {activeTab === 'scheduler' && <SchedulerPanel />}
        {activeTab === 'studio' && <StudioPanel />}
        {activeTab === 'workflow' && <WorkflowPanel />}
        {activeTab === 'board' && <IssueBoardPanel />}
        {activeTab === 'kanban' && <KanbanBoard />}
        {activeTab === 'compounding' && <CompoundingPanel />}
        {activeTab === 'pipeline' && <PipelinePanel />}
        {activeTab === 'capability' && <CapabilityPanel />}
        {activeTab === 'kgraph' && <KnowledgeGraphPanel />}
        {activeTab === 'memorysync' && <MemorySyncPanel />}
        {activeTab === 'phub' && <PlatformHubPanel />}
        {activeTab === 'costs' && <CostAnalyticsPanel />}
        {activeTab === 'workspaces' && <WorkspacePanel />}
        {activeTab === 'agentdashboard' && <AgentDashboard />}
        {activeTab === 'governance' && <GovernancePanel />}
        {activeTab === 'smartrouter' && <SmartRouterPanel />}
{activeTab === 'agentmesh' && <AgentMeshPanel />}
{activeTab === 'learningloop' && <LearningLoopPanel />}
{activeTab === 'experience' && <ExperiencePanel />}
{activeTab === 'collabspace' && <CollabSpacePanel />}
{activeTab === 'contextengine' && <ContextEnginePanel />}
{activeTab === 'automation' && <AutomationPanel />}
{activeTab === 'skillfabric' && <SkillFabricPanel />}
              {activeTab === 'usermodel' && <UserModelPanel />}
              {activeTab === 'evolvingskills' && <EvolvingSkillsPanel />}
              {activeTab === 'subagentmesh' && <SubAgentMeshPanel />}
              {activeTab === 'protocol' && <ProtocolPanel />}
              {activeTab === 'sandbox' && <SandboxPanel />}
              {activeTab === 'toolexec' && <ToolExecutorPanel />}
              {activeTab === 'modelorch' && <ModelOrchestratorPanel />}
              {activeTab === 'deployment' && <DeploymentPanel />}
              {activeTab === 'productcomposer' && <ProductComposerPanel />}
              {activeTab === 'agentorchestrator' && <AgentOrchestratorPanel />}
              {activeTab === 'dreammode' && <DreamModePanel />}
              {activeTab === 'whitememory' && <WhiteMemoryPanel />}
              {activeTab === 'reflection' && <ReflectionPanel />}
              {activeTab === 'intent' && <IntentPanel />}
              {activeTab === 'fleet' && <FleetPanel />}
              {activeTab === 'knowledgenetwork' && <KnowledgeNetworkPanel />}
        {activeTab === 'proactive' && selectedAgent && <ProactiveDiscoveryPanel agent={selectedAgent} />}
        {activeTab === 'metacognition' && selectedAgent && <MetaCognitionPanel agent={selectedAgent} />}
        {activeTab === 'evolution' && selectedAgent && <EvolutionPanel agent={selectedAgent} />}
        {activeTab === 'agentself' && selectedAgent && <AgentSelfPanel agent={selectedAgent} />}
        {activeTab === 'activity' && <ActivityTimeline />}
        {activeTab === 'runtimemonitor' && <RuntimeMonitor />}
        {activeTab === 'skillmanager' && <SkillManager />}
        {activeTab === 'plugins' && <PluginSystemPanel />}
        {activeTab === 'imhub' && <IMHubPanel />}
        {activeTab === 'marketplace' && <MarketplacePanel />}
        {activeTab === 'taskqueue' && <TaskQueuePanel />}
        {activeTab === 'runtimebackend' && <RuntimeBackendPanel agent={selectedAgent} />}
        {activeTab === 'agentcore' && <AgentCorePanel />}
        {activeTab === 'synthesis' && <SynthesisPanel />}
        {activeTab === 'intelligence' && <IntelligencePanel />}
        {activeTab === 'runtimepanel' && <RuntimePanel />}
        {activeTab === 'skillcompiler' && <SkillCompilerPanel />}
        {activeTab === 'conversationsearch' && <ConversationSearchPanel />}
        {activeTab === 'reasoning' && <ReasoningPanel />}
        {activeTab === 'modelproxy' && <ModelProxyPanel />}
        {activeTab === 'toolcomposer' && <ToolComposerPanel />}
        {activeTab === 'contextmanager' && <ContextManagerPanel />}
        {activeTab === 'unifiedconsole' && <UnifiedConsole />}
        {activeTab === 'experiments' && <ExperimentPanel />}
        {activeTab === 'unifiedbrain' && <UnifiedBrainPanel />}
        {activeTab === 'platformcore' && <PlatformCorePanel />}
        {activeTab === 'unifiedagent' && <UnifiedAgentPanel />}
        {activeTab === 'agentflow' && <AgentFlowPanel />}
        {activeTab === 'profile' && <ProfilePanel />}
        {activeTab === 'mcptools' && <MCPToolsPanel />}
{activeTab === 'goalDecomposer' && <GoalDecomposerPanel />}
{activeTab === 'selfReflection' && <SelfReflectionPanel />}
{activeTab === 'memoryConsolidator' && <MemoryConsolidatorPanel />}
{activeTab === 'contextCompressor' && <ContextCompressorPanel />}
{activeTab === 'unifiedSystem' && <UnifiedSystemPanel />}
{activeTab === 'knowledgeFabric' && <KnowledgeFabricPanel />}
{activeTab === 'collaborativeIntelligence' && <CollaborativeIntelligencePanel />}
{activeTab === 'knowledgeGraphViz' && <KnowledgeGraphViz onNavigate={(tab: string) => setActiveTab(tab as TabView)} />}
{activeTab === 'skillExplorer' && <SkillExplorer onNavigate={(tab: string) => setActiveTab(tab as TabView)} />}
{activeTab === 'codeReview' && <CodeReviewPanel onNavigate={(tab: string) => setActiveTab(tab as TabView)} />}
{activeTab === 'swarmConsole' && <SwarmConsolePanel onNavigate={(tab: string) => setActiveTab(tab as TabView)} />}
{activeTab === 'platformConsole' && <PlatformConsolePanel onNavigate={(tab: string) => setActiveTab(tab as TabView)} />}
{activeTab === 'teamArchitect' && <TeamArchitectPanel />}
{activeTab === 'evolutionLoop' && <EvolutionLoopPanel />}
{activeTab === 'proactiveEngine' && <ProactiveEnginePanel />}
{activeTab === 'sentienceCore' && <SentienceCorePanel />}
{activeTab === 'capabilityMesh' && <CapabilityMeshPanel />}
{activeTab === 'presenceEngine' && <PresenceEnginePanel />}
{activeTab === 'feedbackOrchestrator' && <FeedbackOrchestratorPanel />}
{activeTab === 'sessionCommander' && <SessionCommanderPanel />}
{activeTab === 'runtimeScheduler' && <RuntimeSchedulerPanel />}
{activeTab === 'workspaceNexus' && <WorkspaceNexusPanel />}
{activeTab === 'executionCompiler' && <ExecutionCompilerPanel />}
{activeTab === 'verificationPipeline' && <VerificationPipelinePanel />}
{activeTab === 'modelConductor' && <ModelConductorPanel />}
{activeTab === 'contextWeaver' && <ContextWeaverPanel />}
{activeTab === 'autonomyFramework' && <AutonomyFrameworkPanel />}
{activeTab === 'intelligenceHub' && <IntelligenceHubPanel />}
{activeTab === 'adaptiveWorkflows' && <AdaptiveWorkflowsPanel />}
{activeTab === 'crossConnector' && <CrossConnectorPanel />}
{activeTab === 'chainOfThought' && <ChainOfThoughtPanel />}
{activeTab === 'intentResolution' && <IntentResolutionPanel />}
{activeTab === 'dynamicAdaptation' && <DynamicAdaptationPanel />}
{activeTab === 'uncertaintyQuantifier' && <UncertaintyQuantifierPanel />}
{activeTab === 'federatedKnowledge' && <FederatedKnowledgePanel />}
{activeTab === 'emergentBehavior' && <EmergentBehaviorPanel />}
{activeTab === 'performanceAutotuner' && <PerformanceAutotunerPanel />}
{activeTab === 'platformResilience' && <PlatformResiliencePanel />}

        {/* Agent-specific panels */}
        {selectedAgent && (
          <>
            {activeTab === 'chat' && (
              <ChatArea
                key={`${selectedAgent.id}-${selectedConv?.id || 'new'}`}
                agent={selectedAgent}
                conversationId={selectedConv?.id || null}
                messages={messages}
                onMessagesUpdate={setMessages}
                onConversationCreated={handleConversationCreated}
              />
            )}
            {activeTab === 'tasks' && (
              <TaskDashboard
                agent={selectedAgent}
                tasks={tasks.filter((t) => t.agent_id === selectedAgent.id)}
                onTaskCreated={handleTaskCreated}
              />
            )}
            {activeTab === 'skills' && (
              <SkillPanel agent={selectedAgent} />
            )}
            {activeTab === 'memory' && (
              <MemoryViewer agent={selectedAgent} />
            )}
            {activeTab === 'autopilot' && (
              <AutopilotPanel agent={selectedAgent} />
            )}
            {activeTab === 'subagents' && (
              <SubAgentPanel agent={selectedAgent} />
            )}
            {activeTab === 'tools' && (
              <ToolPanel />
            )}
            {activeTab === 'plans' && (
              <PlanView />
            )}
            {activeTab === 'workspace' && (
              <WorkspaceViewer />
            )}
            {activeTab === 'dream' && (
              <DreamPanel />
            )}
            {activeTab === 'mcp' && (
              <MCPServerPanel />
            )}
            {activeTab === 'collaboration' && (
              <CollaborationPanel />
            )}
            {activeTab === 'approval' && (
              <ApprovalPanel />
            )}
            {activeTab === 'events' && (
              <EventMonitor />
            )}
            {activeTab === 'identity' && (
              <IdentityPanel agent={selectedAgent} />
            )}
            {activeTab === 'trajectory' && (
              <TrajectoryPanel agent={selectedAgent} />
            )}
            {activeTab === 'squads' && (
                <SquadsPanel agent={selectedAgent} />
              )}
              {activeTab === 'persona' && (
                <PersonaPanel agent={selectedAgent} />
              )}
              {activeTab === 'learning' && (
            <LearningPanel agent={selectedAgent} />
          )}
          {activeTab === 'knowledge' && (
            <KnowledgeBasePanel agent={selectedAgent} />
          )}
          {activeTab === 'identitycore' && (
            <IdentityCorePanel agent={selectedAgent} />
          )}
      </>
    )}

        {/* Empty state — no agent and no global panel selected */}
        {!selectedAgent && !['commandCenter', 'overview', 'dashboard', 'agent-comparison', 'nexus', 'forge', 'board', 'kanban', 'compounding', 'whitememory', 'pipeline', 'capability', 'kgraph', 'memorysync', 'phub', 'guard', 'pulse', 'gateway', 'daemon', 'swarm', 'runtime', 'scheduler', 'studio', 'workflow', 'costs', 'workspaces', 'agentdashboard', 'activity', 'runtimemonitor', 'skillmanager', 'plugins', 'imhub', 'marketplace', 'taskqueue', 'runtimebackend', 'agentcore', 'synthesis', 'intelligence', 'runtimepanel', 'skillcompiler', 'conversationsearch', 'governance', 'smartrouter', 'agentmesh', 'learningloop', 'experience', 'collabspace', 'contextengine', 'automation', 'skillfabric', 'usermodel', 'evolvingskills', 'subagentmesh', 'protocol', 'sandbox', 'toolexec', 'modelorch', 'deployment', 'productcomposer', 'agentorchestrator', 'dreammode', 'reflection', 'intent', 'fleet', 'knowledgenetwork', 'reasoning', 'modelproxy', 'toolcomposer', 'contextmanager', 'unifiedconsole', 'experiments', 'unifiedbrain', 'platformcore', 'unifiedagent', 'agentflow', 'profile', 'mcptools', 'goalDecomposer', 'selfReflection', 'memoryConsolidator', 'contextCompressor', 'teamArchitect', 'evolutionLoop', 'proactiveEngine', 'executionCompiler', 'verificationPipeline', 'modelConductor', 'contextWeaver', 'autonomyFramework', 'intelligenceHub', 'adaptiveWorkflows', 'crossConnector'].includes(activeTab) && (
          <div className="main-empty">
            <div className="main-empty-icon">B</div>
            <h2>Welcome to Buddy</h2>
            <p>Select an Agent from the sidebar or create a new one to get started.</p>
            <button className="btn-primary" onClick={() => setShowNewAgent(true)}>
              Create Your First Agent
            </button>
          </div>
        )}
      </main>
    </div>
      </ToastProvider>
    </ErrorBoundary>
  );
}