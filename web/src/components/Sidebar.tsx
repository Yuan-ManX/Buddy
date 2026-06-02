import React from 'react';
import type { Agent, Conversation } from '../types';

interface SidebarProps {
  agents: Agent[];
  conversations: Conversation[];
  selectedAgent: Agent | null;
  selectedConv: Conversation | null;
  onSelectAgent: (agent: Agent) => void;
  onSelectConv: (conv: Conversation) => void;
  onNewAgent: () => void;
  onNewConv: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  agents,
  conversations,
  selectedAgent,
  selectedConv,
  onSelectAgent,
  onSelectConv,
  onNewAgent,
  onNewConv,
}) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <span className="sidebar-logo-icon">B</span>
          <span className="sidebar-logo-text">Buddy</span>
        </div>
      </div>

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
              className={`sidebar-item ${selectedAgent?.id === agent.id ? 'active' : ''}`}
              onClick={() => onSelectAgent(agent)}
            >
              <div className="sidebar-avatar" style={{ background: getRoleColor(agent.role) }}>
                {agent.name.charAt(0).toUpperCase()}
              </div>
              <div className="sidebar-item-info">
                <div className="sidebar-item-name">{agent.name}</div>
                <div className="sidebar-item-role">{agent.role}</div>
              </div>
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