import React from 'react';
import type { Agent, Conversation, TabView } from '../types';
import { getRoleColor } from '../utils/colors';

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
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <span className="sidebar-logo-icon">B</span>
          <span className="sidebar-logo-text">Buddy</span>
        </div>
        <button
          className={`sidebar-tab dashboard-nav ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => onSelectTab('dashboard')}
          title="System Dashboard"
        >
          📊
        </button>
      </div>

      {/* Global tabs */}
      <div className="sidebar-tabs">
        <button
          className={`sidebar-tab ${activeTab === 'nexus' ? 'active' : ''}`}
          onClick={() => onSelectTab('nexus')}
        >
          Nexus
        </button>
        <button
          className={`sidebar-tab ${activeTab === 'forge' ? 'active' : ''}`}
          onClick={() => onSelectTab('forge')}
        >
          Forge
        </button>
        <button
          className={`sidebar-tab ${activeTab === 'guard' ? 'active' : ''}`}
          onClick={() => onSelectTab('guard')}
        >
          Guard
        </button>
        <button
          className={`sidebar-tab ${activeTab === 'pulse' ? 'active' : ''}`}
          onClick={() => onSelectTab('pulse')}
        >
          Pulse
        </button>
      </div>

      {/* Agent-specific tabs */}
      {selectedAgent ? (
        <div>
          <div className="sidebar-tabs-divider" />
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
              className={`sidebar-tab ${activeTab === 'identity' ? 'active' : ''}`}
              onClick={() => onSelectTab('identity')}
            >
              Identity
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
              className={`sidebar-tab ${activeTab === 'squads' ? 'active' : ''}`}
              onClick={() => onSelectTab('squads')}
            >
              Squads
            </button>
            <button
              className={`sidebar-tab ${activeTab === 'trajectory' ? 'active' : ''}`}
              onClick={() => onSelectTab('trajectory')}
            >
              Trace
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
        </div>
      ) : null}

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

      <div className="sidebar-footer">
        <div className="sidebar-status">
          <span className="sidebar-status-dot" />
          <span>Backend Connected</span>
        </div>
      </div>
    </aside>
  );
};