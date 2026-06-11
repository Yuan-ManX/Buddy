import React, { useState, useMemo } from 'react';
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

// Tab categories with grouping
const GLOBAL_TABS: { id: TabView; label: string; icon: string }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: '📊' },
  { id: 'nexus', label: 'Nexus', icon: '🔗' },
  { id: 'forge', label: 'Forge', icon: '⚒️' },
  { id: 'guard', label: 'Guard', icon: '🛡️' },
  { id: 'pulse', label: 'Pulse', icon: '💓' },
  { id: 'gateway', label: 'Gateway', icon: '🌐' },
  { id: 'daemon', label: 'Daemon', icon: '👾' },
  { id: 'swarm', label: 'Swarm', icon: '🦾' },
  { id: 'runtime', label: 'Runtime', icon: '🖧' },
  { id: 'scheduler', label: 'Scheduler', icon: '⏰' },
  { id: 'studio', label: 'Studio', icon: '🎨' },
  { id: 'workflow', label: 'Workflow', icon: '📋' },
];

const AGENT_TABS: { id: TabView; label: string; icon: string }[] = [
  { id: 'chat', label: 'Chat', icon: '💬' },
  { id: 'tasks', label: 'Tasks', icon: '📋' },
  { id: 'skills', label: 'Skills', icon: '🧩' },
  { id: 'memory', label: 'Memory', icon: '🧠' },
  { id: 'identity', label: 'Identity', icon: '🪪' },
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
          <span className="sidebar-shortcut-hint">⌘K</span>
        </div>
      </div>
    </aside>
  );
};