import React, { useState, useEffect, useCallback } from 'react';
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
import ApprovalPanel from './components/ApprovalPanel';
import EventMonitor from './components/EventMonitor';
import ErrorBoundary from './components/ErrorBoundary';
import { ToastProvider } from './components/Toast';
import { api } from './api/client';
import type { Agent, Conversation, Message as MsgType, Task } from './types';
import './App.css';

type TabView = 'chat' | 'tasks' | 'skills' | 'memory' | 'autopilot' | 'subagents' | 'tools' | 'plans' | 'workspace' | 'dream' | 'mcp' | 'collaboration' | 'approval' | 'events' | 'overview';

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
      setAgents((prev) => prev.filter((a) => a.id !== agentId));
      setConversations((prev) => prev.filter((c) => !c.agent_ids.includes(agentId)));
      if (selectedAgent?.id === agentId) {
        const remaining = agents.filter((a) => a.id !== agentId);
        setSelectedAgent(remaining.length > 0 ? remaining[0] : null);
        setSelectedConv(null);
        setMessages([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete agent');
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
        <div className="app">
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
        onDeleteConv={handleDeleteConv}
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

        {selectedAgent ? (
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
          </>
        ) : activeTab === 'overview' ? (
          <SystemOverview />
        ) : (
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