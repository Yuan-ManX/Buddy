import React, { useState, useRef, useEffect, useCallback } from 'react';
import type { Agent, Message as MsgType } from '../types';
import { MessageBubble } from './MessageBubble';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../api/client';
import { getRoleColor, getRoleColorSecondary } from '../utils/colors';

interface ChatAreaProps {
  agent: Agent;
  conversationId: string | null;
  messages: MsgType[];
  onMessagesUpdate: (msgs: MsgType[] | ((prev: MsgType[]) => MsgType[])) => void;
  onConversationCreated: (convId: string) => void;
}

interface ToolCallState {
  id: string;
  name: string;
  arguments: string;
  result: string | null;
  status: 'pending' | 'running' | 'done' | 'error';
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
  const [useStreaming, setUseStreaming] = useState(true);
  const [toolCalls, setToolCalls] = useState<ToolCallState[]>([]);
  const [reasoningChain, setReasoningChain] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const { connect, send, disconnect, streaming: wsStreaming } = useWebSocket(agent.id);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 200) + 'px';
    }
  }, [input]);

  useEffect(() => {
    setCurrentConvId(conversationId);
  }, [conversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent, toolCalls]);

  // SSE Streaming handler
  const handleSendSSE = useCallback(async () => {
    if (!input.trim() || loading) return;
    const content = input.trim();
    setInput('');
    setLoading(true);
    setStreamingContent('');
    setToolCalls([]);
    setReasoningChain([]);

    const userMsg: MsgType = {
      id: `u-${Date.now()}`,
      agent_id: agent.id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    onMessagesUpdate((prev) => [...prev, userMsg]);

    const abortController = new AbortController();
    abortRef.current = abortController;

    let fullContent = '';
    let newConvId: string | null = null;

    try {
      const response = await api.chatStream({
        agent_id: agent.id,
        content,
        conversation_id: currentConvId || undefined,
        enable_tools: true,
        enable_reasoning: true,
      });

      // Override fetch with abort signal
      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6).trim();
          if (data === '[DONE]') continue;

          try {
            const parsed = JSON.parse(data);

            switch (parsed.type) {
              case 'token':
                fullContent += parsed.content;
                setStreamingContent(fullContent);
                break;
              case 'tool_call':
                setToolCalls((prev) => [
                  ...prev,
                  {
                    id: parsed.id || `tc-${Date.now()}`,
                    name: parsed.name,
                    arguments: parsed.arguments || '',
                    result: null,
                    status: 'running',
                  },
                ]);
                break;
              case 'tool_result':
                setToolCalls((prev) =>
                  prev.map((tc) =>
                    tc.id === parsed.id || tc.name === parsed.name
                      ? { ...tc, result: parsed.result || parsed.content, status: parsed.error ? 'error' : 'done' }
                      : tc
                  )
                );
                break;
              case 'reasoning':
                setReasoningChain((prev) => [...prev, parsed.content]);
                break;
              case 'conversation':
                if (parsed.conversation_id) {
                  newConvId = parsed.conversation_id;
                }
                break;
              case 'error':
                throw new Error(parsed.content || 'Stream error');
            }
          } catch (e) {
            if (e instanceof SyntaxError) continue;
            throw e;
          }
        }
      }

      // Handle conversation creation
      if (newConvId && !currentConvId) {
        setCurrentConvId(newConvId);
        onConversationCreated(newConvId);
      }

      // Finalize assistant message
      if (fullContent) {
        const assistantMsg: MsgType = {
          id: `a-${Date.now()}`,
          agent_id: agent.id,
          role: 'assistant',
          content: fullContent,
          created_at: new Date().toISOString(),
        };
        onMessagesUpdate((prev) => [...prev, assistantMsg]);
      }
      setStreamingContent('');
      setToolCalls([]);
      setReasoningChain([]);
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      const errMsg: MsgType = {
        id: `e-${Date.now()}`,
        agent_id: agent.id,
        role: 'assistant',
        content: `Error: ${err instanceof Error ? err.message : 'Unknown error occurred'}`,
        created_at: new Date().toISOString(),
      };
      onMessagesUpdate((prev) => [...prev, errMsg]);
      setStreamingContent('');
      setToolCalls([]);
      setReasoningChain([]);
    } finally {
      setLoading(false);
      abortRef.current = null;
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [input, loading, agent, currentConvId, onMessagesUpdate, onConversationCreated]);

  // REST fallback
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

      if (res.tool_calls && res.tool_calls.length > 0) {
        setToolCalls(
          res.tool_calls.map((tc: any) => ({
            id: tc.id || `${tc.name}-${Date.now()}`,
            name: tc.name,
            arguments: JSON.stringify(tc.arguments || {}, null, 2),
            result: tc.result || null,
            status: (tc.result ? 'done' : 'error') as ToolCallState['status'],
          }))
        );
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

  // WebSocket streaming
  const handleSendWS = () => {
    if (!input.trim() || wsStreaming) return;
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

  const handleSend = () => {
    if (useStreaming) {
      handleSendSSE();
    } else {
      handleSendRest();
    }
  };

  const handleStopGeneration = () => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    if (wsStreaming) {
      disconnect();
    }
    setLoading(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    // Shift+Enter for new line
  };

  const handleRetry = async (msgContent: string) => {
    setInput(msgContent);
    inputRef.current?.focus();
  };

  const suggestionPrompts: Record<string, string[]> = {
    strategy: ['Help me plan a product launch', 'Analyze the risks of this approach', 'Create a decision framework'],
    engineering: ['Review this code for improvements', 'Help me debug an issue', 'Explain how async works'],
    research: ['What are the latest trends in AI?', 'Summarize recent developments', 'Compare these two technologies'],
    companion: ['How can I improve my daily routine?', 'Give me some life advice', "What's a good habit to build?"],
  };

  const suggestions = suggestionPrompts[agent.role] || suggestionPrompts.companion || [];
  const isGenerating = loading || wsStreaming;

  return (
    <div className="chat-area">
      {/* Header */}
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
          <button
            className={`chat-mode-btn ${useStreaming ? 'active' : ''}`}
            onClick={() => setUseStreaming(!useStreaming)}
            title={useStreaming ? 'Streaming mode (SSE)' : 'REST mode'}
          >
            {useStreaming ? 'SSE Stream' : 'REST'}
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {messages.length === 0 && !streamingContent && !isGenerating && (
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
          <MessageBubble
            key={msg.id}
            message={msg}
            agentName={agent.name}
            onRetry={handleRetry}
          />
        ))}

        {/* Tool calls display */}
        {toolCalls.length > 0 && (
          <div className="tool-calls-container">
            {toolCalls.map((tc) => (
              <div key={tc.id} className={`tool-call-card ${tc.status}`}>
                <div className="tool-call-header">
                  <span className={`tool-call-status-dot ${tc.status}`} />
                  <span className="tool-call-name">{tc.name}</span>
                  <span className="tool-call-status-text">{tc.status}</span>
                </div>
                {tc.arguments && (
                  <pre className="tool-call-args">{tc.arguments}</pre>
                )}
                {tc.result && (
                  <div className="tool-call-result">
                    <pre>{typeof tc.result === 'string' ? tc.result : JSON.stringify(tc.result, null, 2)}</pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Reasoning chain */}
        {reasoningChain.length > 0 && (
          <div className="reasoning-chain">
            <div className="reasoning-chain-header">
              <span className="reasoning-icon">💭</span>
              <span>Reasoning</span>
            </div>
            {reasoningChain.map((step, i) => (
              <div key={i} className="reasoning-step">{step}</div>
            ))}
          </div>
        )}

        {/* Streaming content */}
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

        {/* Typing indicator */}
        {loading && !streamingContent && (
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

      {/* Input area */}
      <div className="chat-input-area">
        <textarea
          ref={inputRef}
          className="chat-input"
          placeholder={`Message ${agent.name}... (Enter to send, Shift+Enter for new line)`}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={isGenerating}
        />
        {isGenerating ? (
          <button className="chat-stop-btn" onClick={handleStopGeneration} title="Stop generation">
            ■
          </button>
        ) : null}
        <button
          className="chat-send-btn"
          onClick={handleSend}
          disabled={!input.trim() || isGenerating}
        >
          {loading ? '...' : 'Send'}
        </button>
      </div>
    </div>
  );
};