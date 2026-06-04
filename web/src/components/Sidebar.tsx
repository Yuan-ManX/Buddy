import React from 'react';
import type { Agent, Conversation } from '../types';

type TabView = 'chat' | 'tasks' | 'skills' | 'memory' | 'autopilot' | 'subagents' | 'tools' | 'plans' | 'workspace' | 'dream' | 'mcp' | 'collaboration' | 'approval' | 'events' | 'overview';

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
  onDeleteConv: (convId: string) => void;
  onSelectTab: (tab: TabView) => void;
}

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
  onDeleteConv,
  onSelectTab,
}) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <span className="sidebar-logo-icon">B</span>
          <span className="sidebar-logo-text">Buddy</span>
        </div>
      </div>

      {selectedAgent && (
        <div className="sidebar-tabs">
          <button
            className={`sidebar-tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => onSelectTab('chat')}
          >
            Chat
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'tasks' ? 'active' : ''}`}
            onClick={() => onSelectTab('tasks')}
          >
            Tasks
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'skills' ? 'active' : ''}`}
            onClick={() => onSelectTab('skills')}
          >
            Skills
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'memory' ? 'active' : ''}`}
            onClick={() => onSelectTab('memory')}
          >
            Memory
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'autopilot' ? 'active' : ''}`}
            onClick={() => onSelectTab('autopilot')}
          >
            Auto
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'subagents' ? 'active' : ''}`}
            onClick={() => onSelectTab('subagents')}
          >
            Workers
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'tools' ? 'active' : ''}`}
            onClick={() => onSelectTab('tools')}
          >
            Tools
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'plans' ? 'active' : ''}`}
            onClick={() => onSelectTab('plans')}
          >
            Plans
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'workspace' ? 'active' : ''}`}
            onClick={() => onSelectTab('workspace')}
          >
            Workspace
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'dream' ? 'active' : ''}`}
            onClick={() => onSelectTab('dream')}
          >
            Dream
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'mcp' ? 'active' : ''}`}
            onClick={() => onSelectTab('mcp')}
          >
            MCP
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'collaboration' ? 'active' : ''}`}
            onClick={() => onSelectTab('collaboration')}
          >
            Collab
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'approval' ? 'active' : ''}`}
            onClick={() => onSelectTab('approval')}
          >
            Approval
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'events' ? 'active' : ''}`}
            onClick={() => onSelectTab('events')}
          >
            Events
          </button>
        </div>
      )}

      <div className="sidebar-section">
        <div className="sidebar-section-header">
          <span className="sidebar-section-title">Agents</span>
          <button className="sidebar-add-btn" onClick={onNewAgent} title="Create Agent">
            +
          </button>
        </div>
        <div className="sidebar-list">
          {agents.map((agent) => (
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
                <div className="sidebar-item-role">{agent.role}</div>
              </div>
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

      <div className="sidebar-section">
        <div className="sidebar-section-header">
          <span className="sidebar-section-title">Conversations</span>
          <button className="sidebar-add-btn" onClick={onNewConv} title="New Conversation">
            +
          </button>
        </div>
        <div className="sidebar-list">
          {conversations.map((conv) => (
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

      <div className="sidebar-footer">
        <div className="sidebar-status">
          <span className="sidebar-status-dot" />
          <span>Backend Connected</span>
        </div>
      </div>
    </aside>
  );
};

function getRoleColor(role: string): string {
  const colors: Record<string, string> = {
    strategy: '#3b82f6',
    engineering: '#f59e0b',
    design: '#8b5cf6',
    research: '#06b6d4',
    writing: '#10b981',
    companion: '#ec4899',
    custom: '#6366f1',
  };
  return colors[role] || '#6366f1';
}