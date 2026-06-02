import React, { useState, useRef, useEffect } from 'react';
import type { Agent, Message as MsgType } from '../types';
import { MessageBubble } from './MessageBubble';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../api/client';

interface ChatAreaProps {
  agent: Agent;
  conversationId: string | null;
  messages: MsgType[];
  onMessagesUpdate: (msgs: MsgType[]) => void;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  agent,
  conversationId,
  messages,
  onMessagesUpdate,
}) => {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { connect, send, disconnect, streaming } = useWebSocket(agent.id);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  useEffect(() => {
    if (streamingContent) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [streamingContent]);

  const handleSendRest = async () => {
    if (!input.trim() || loading) return;
    const content = input.trim();
    setInput('');
    setLoading(true);

    const userMsg: MsgType = {
      id: Date.now().toString(),
      agent_id: agent.id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    onMessagesUpdate([...messages, userMsg]);

    try {
      const res = await api.chat({
        agent_id: agent.id,
        content,
        conversation_id: conversationId || undefined,
      });

      const assistantMsg: MsgType = {
        id: (Date.now() + 1).toString(),
        agent_id: agent.id,
        role: 'assistant',
        content: res.content,
        created_at: new Date().toISOString(),
      };
      onMessagesUpdate([...messages, userMsg, assistantMsg]);
    } catch (err) {
      const errMsg: MsgType = {
        id: (Date.now() + 1).toString(),
        agent_id: agent.id,
        role: 'assistant',
        content: `Error: ${err instanceof Error ? err.message : 'Unknown error'}`,
        created_at: new Date().toISOString(),
      };
      onMessagesUpdate([...messages, userMsg, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleSendWS = () => {
    if (!input.trim() || streaming) return;
    const content = input.trim();
    setInput('');
    setStreamingContent('');

    const userMsg: MsgType = {
      id: Date.now().toString(),
      agent_id: agent.id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };

    let fullContent = '';

    connect(
      (token) => {
        fullContent += token;
        setStreamingContent(fullContent);
      },
      (full) => {
        const assistantMsg: MsgType = {
          id: (Date.now() + 1).toString(),
          agent_id: agent.id,
          role: 'assistant',
          content: full,
          created_at: new Date().toISOString(),
        };
        onMessagesUpdate([...messages, userMsg, assistantMsg]);
        setStreamingContent('');
        disconnect();
      },
      (err) => {
        const errMsg: MsgType = {
          id: (Date.now() + 1).toString(),
          agent_id: agent.id,
          role: 'assistant',
          content: `Error: ${err}`,
          created_at: new Date().toISOString(),
        };
        onMessagesUpdate([...messages, userMsg, errMsg]);
        setStreamingContent('');
        disconnect();
      }
    );

    send(content);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendRest();
    }
  };

  return (
    <div className="chat-area">
      <div className="chat-header">
        <div className="chat-header-info">
          <div className="chat-header-avatar" style={{ background: '#3b82f6' }}>
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
            {streaming ? 'Streaming...' : 'Live Mode'}
          </button>
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && !streamingContent && (
          <div className="chat-welcome">
            <div className="chat-welcome-icon">B</div>
            <h2>Start a conversation with {agent.name}</h2>
            <p>
              {agent.name} is a {agent.role} Agent. {agent.personality}
            </p>
            <div className="chat-suggestions">
              {['What can you help me with?', 'Tell me about yourself.', 'Let\'s brainstorm some ideas.'].map((s) => (
                <button key={s} className="chat-suggestion" onClick={() => { setInput(s); }}>
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
            <div className="msg-avatar">{agent.name.charAt(0).toUpperCase()}</div>
            <div className="msg-bubble bubble-assistant">
              <div className="msg-sender">{agent.name}</div>
              <div className="msg-content streaming">{streamingContent}</div>
            </div>
          </div>
        )}
        {loading && (
          <div className="msg-row msg-assistant">
            <div className="msg-avatar">{agent.name.charAt(0).toUpperCase()}</div>
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
          Send
        </button>
      </div>
    </div>
  );
};