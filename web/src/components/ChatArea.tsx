import React, { useState, useRef, useEffect } from 'react';
import type { Agent, Message as MsgType } from '../types';
import { MessageBubble } from './MessageBubble';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../api/client';

interface ChatAreaProps {
  agent: Agent;
  conversationId: string | null;
  messages: MsgType[];
  onMessagesUpdate: (msgs: MsgType[] | ((prev: MsgType[]) => MsgType[])) => void;
  onConversationCreated: (convId: string) => void;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  agent,
  conversationId,
  messages,
  onMessagesUpdate,
  onConversationCreated,
}) => {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [currentConvId, setCurrentConvId] = useState<string | null>(conversationId);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const { connect, send, disconnect, streaming } = useWebSocket(agent.id);

  useEffect(() => {
    setCurrentConvId(conversationId);
  }, [conversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const handleSendRest = async () => {
    if (!input.trim() || loading) return;
    const content = input.trim();
    setInput('');
    setLoading(true);

    const userMsg: MsgType = {
      id: `u-${Date.now()}`,
      agent_id: agent.id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };

    onMessagesUpdate((prev) => [...prev, userMsg]);

    try {
      const res = await api.chat({
        agent_id: agent.id,
        content,
        conversation_id: currentConvId || undefined,
      });

      if (res.conversation_id && !currentConvId) {
        setCurrentConvId(res.conversation_id);
        onConversationCreated(res.conversation_id);
      }

      const assistantMsg: MsgType = {
        id: `a-${Date.now()}`,
        agent_id: agent.id,
        role: 'assistant',
        content: res.content,
        created_at: new Date().toISOString(),
      };
      onMessagesUpdate((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errMsg: MsgType = {
        id: `e-${Date.now()}`,
        agent_id: agent.id,
        role: 'assistant',
        content: `Error: ${err instanceof Error ? err.message : 'Unknown error occurred'}`,
        created_at: new Date().toISOString(),
      };
      onMessagesUpdate((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleSendWS = () => {
    if (!input.trim() || streaming) return;
    const content = input.trim();
    setInput('');
    setStreamingContent('');

    const userMsg: MsgType = {
      id: `u-${Date.now()}`,
      agent_id: agent.id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };

    onMessagesUpdate((prev) => [...prev, userMsg]);

    let fullContent = '';

    connect(
      (token) => {
        fullContent += token;
        setStreamingContent(fullContent);
      },
      (full) => {
        if (!currentConvId) {
          const newConvId = `conv-${Date.now().toString(36)}`;
          setCurrentConvId(newConvId);
          onConversationCreated(newConvId);
        }

        const assistantMsg: MsgType = {
          id: `a-${Date.now()}`,
          agent_id: agent.id,
          role: 'assistant',
          content: full,
          created_at: new Date().toISOString(),
        };
        onMessagesUpdate((prev) => [...prev, assistantMsg]);
        setStreamingContent('');
        disconnect();
      },
      (err) => {
        const errMsg: MsgType = {
          id: `e-${Date.now()}`,
          agent_id: agent.id,
          role: 'assistant',
          content: `Error: ${err}`,
          created_at: new Date().toISOString(),
        };
        onMessagesUpdate((prev) => [...prev, errMsg]);
        setStreamingContent('');
        disconnect();
      }
    );

    send(content);
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendRest();
    }
  };

  const suggestionPrompts: Record<string, string[]> = {
    strategy: ['Help me plan a product launch', 'Analyze the risks of this approach', 'Create a decision framework'],
    engineering: ['Review this code for improvements', 'Help me debug an issue', 'Explain how async works'],
    research: ['What are the latest trends in AI?', 'Summarize recent developments', 'Compare these two technologies'],
    companion: ['How can I improve my daily routine?', 'Give me some life advice', "What's a good habit to build?"],
  };

  const suggestions = suggestionPrompts[agent.role] || suggestionPrompts.companion || [];

  return (
    <div className="chat-area">
      <div className="chat-header">
        <div className="chat-header-info">
          <div
            className="chat-header-avatar"
            style={{
              background: `linear-gradient(135deg, ${getRoleColor(agent.role)}, ${getRoleColorSecondary(agent.role)})`,
            }}
          >
            {agent.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="chat-header-name">{agent.name}</div>
            <div className="chat-header-role">
              {agent.role} · {agent.personality}
            </div>
          </div>
        </div>
        <div className="chat-header-actions">
          <button className="chat-mode-btn" onClick={handleSendWS} disabled={streaming}>
            {streaming ? 'Streaming...' : 'Live Stream'}
          </button>
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && !streamingContent && (
          <div className="chat-welcome">
            <div
              className="chat-welcome-icon"
              style={{
                background: `linear-gradient(135deg, ${getRoleColor(agent.role)}, ${getRoleColorSecondary(agent.role)})`,
              }}
            >
              {agent.name.charAt(0).toUpperCase()}
            </div>
            <h2>Start a conversation with {agent.name}</h2>
            <p>
              {agent.name} is a {agent.role} Agent. {agent.personality}
            </p>
            <div className="chat-suggestions">
              {suggestions.map((s) => (
                <button
                  key={s}
                  className="chat-suggestion"
                  onClick={() => {
                    setInput(s);
                    inputRef.current?.focus();
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} agentName={agent.name} />
        ))}
        {streamingContent && (
          <div className="msg-row msg-assistant">
            <div
              className="msg-avatar"
              style={{
                background: `linear-gradient(135deg, ${getRoleColor(agent.role)}, ${getRoleColorSecondary(agent.role)})`,
              }}
            >
              {agent.name.charAt(0).toUpperCase()}
            </div>
            <div className="msg-bubble bubble-assistant">
              <div className="msg-sender">{agent.name}</div>
              <div className="msg-content streaming">{streamingContent}</div>
            </div>
          </div>
        )}
        {loading && (
          <div className="msg-row msg-assistant">
            <div
              className="msg-avatar"
              style={{
                background: `linear-gradient(135deg, ${getRoleColor(agent.role)}, ${getRoleColorSecondary(agent.role)})`,
              }}
            >
              {agent.name.charAt(0).toUpperCase()}
            </div>
            <div className="msg-bubble bubble-assistant">
              <div className="typing-indicator">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <textarea
          ref={inputRef}
          className="chat-input"
          placeholder={`Message ${agent.name}...`}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={loading || streaming}
        />
        <button
          className="chat-send-btn"
          onClick={handleSendRest}
          disabled={!input.trim() || loading || streaming}
        >
          {loading ? '...' : 'Send'}
        </button>
      </div>
    </div>
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

function getRoleColorSecondary(role: string): string {
  const colors: Record<string, string> = {
    strategy: '#6366f1',
    engineering: '#f97316',
    design: '#a78bfa',
    research: '#0891b2',
    writing: '#059669',
    companion: '#f472b6',
    custom: '#818cf8',
  };
  return colors[role] || '#818cf8';
}