import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';
import { api } from './api/client';
import type { Agent, Conversation, Message as MsgType } from './types';
import './App.css';

export default function App() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [selectedConv, setSelectedConv] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<MsgType[]>([]);
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
      const [agentList, convList] = await Promise.all([
        api.agents.list(),
        api.conversations.list(),
      ]);
      setAgents(agentList);
      setConversations(convList);
      if (agentList.length > 0 && !selectedAgent) {
        setSelectedAgent(agentList[0]);
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
      api.conversations.messages(selectedConv.id).then(setMessages).catch(console.error);
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
      if (selectedAgent?.id === agentId) {
        setSelectedAgent(agents.length > 1 ? agents.find((a) => a.id !== agentId) || null : null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete agent');
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

  if (loading) {
    return (
      <div className="app-loading">
        <div className="app-loading-logo">B</div>
        <div className="app-loading-text">Buddy</div>
      </div>
    );
  }

  return (
    <div className="app">
      <Sidebar
        agents={agents}
        conversations={conversations}
        selectedAgent={selectedAgent}
        selectedConv={selectedConv}
        onSelectAgent={(a) => { setSelectedAgent(a); setSelectedConv(null); }}
        onSelectConv={(c) => { setSelectedConv(c); }}
        onNewAgent={() => setShowNewAgent(true)}
        onNewConv={handleCreateConv}
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
          <ChatArea
            key={selectedAgent.id + (selectedConv?.id || '')}
            agent={selectedAgent}
            conversationId={selectedConv?.id || null}
            messages={messages}
            onMessagesUpdate={setMessages}
          />
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
  );
}