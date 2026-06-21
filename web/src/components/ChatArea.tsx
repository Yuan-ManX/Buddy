import React, { useState, useRef, useEffect, useCallback } from 'react';
import type { Agent, Message as MsgType, MessageBranch, QuickReply } from '../types';
import { MessageBubble } from './MessageBubble';
import { ToolCallCard } from './ToolCallCard';
import { StreamingMessage } from './StreamingMessage';
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
  const [showReasoning, setShowReasoning] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Message branching state
  const [messageBranches, setMessageBranches] = useState<MessageBranch[]>([]);
  const [showBranches, setShowBranches] = useState(false);

  // Quick reply state
  const [quickReplies, setQuickReplies] = useState<QuickReply[]>([]);
  const [showQuickReplies, setShowQuickReplies] = useState(false);

  const agentGradient = `linear-gradient(135deg, ${getRoleColor(agent.role)}, ${getRoleColorSecondary(agent.role)})`;

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
    setShowReasoning(false);

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
                setShowReasoning(true);
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

      if (newConvId && !currentConvId) {
        setCurrentConvId(newConvId);
        onConversationCreated(newConvId);
      }

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
      setShowReasoning(false);
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
      setShowReasoning(false);
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
    setLoading(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleRetry = async (msgContent: string) => {
    setInput(msgContent);
    inputRef.current?.focus();
  };

  const handleLoadBranches = async (messageId: string) => {
    try {
      const result = await api.chatBranches(messageId);
      setMessageBranches(result.branches);
      setShowBranches(true);
    } catch {}
  };

  const handleSwitchBranch = (branchId: string) => {
    const branch = messageBranches.find((b) => b.branch_id === branchId);
    if (branch && branch.messages.length > 0) {
      const lastMsg = branch.messages[branch.messages.length - 1];
      setInput(lastMsg.content);
      inputRef.current?.focus();
    }
    setShowBranches(false);
  };

  const handleLoadQuickReplies = async () => {
    try {
      const result = await api.chatQuickReplies(agent.id);
      setQuickReplies(result.replies);
      setShowQuickReplies(true);
    } catch {}
  };

  const suggestionPrompts: Record<string, string[]> = {
    strategy: ['Help me plan a product launch', 'Analyze the risks of this approach', 'Create a decision framework'],
    engineering: ['Review this code for improvements', 'Help me debug an issue', 'Explain how async works'],
    research: ['What are the latest trends in AI?', 'Summarize recent developments', 'Compare these two technologies'],
    companion: ['How can I improve my daily routine?', 'Give me some life advice', "What's a good habit to build?"],
  };

  const suggestions = suggestionPrompts[agent.role] || suggestionPrompts.companion || [];
  const isGenerating = loading;

  return (
    <div className="chat-area">
      {/* Header */}
      <div className="chat-header">
        <div className="chat-header-info">
          <div
            className="chat-header-avatar"
            style={{ background: agentGradient }}
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
            className="chat-mode-btn"
            onClick={handleLoadQuickReplies}
            title="Quick replies"
          >
            Quick
          </button>
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
              style={{ background: agentGradient }}
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

        {/* Tool calls display — using enhanced ToolCallCard */}
        {toolCalls.length > 0 && (
          <div className="tool-calls-container">
            <div className="tool-calls-header">
              <span className="tool-calls-count">{toolCalls.length} tool call{toolCalls.length > 1 ? 's' : ''}</span>
            </div>
            {toolCalls.map((tc) => (
              <ToolCallCard key={tc.id} toolCall={tc} />
            ))}
          </div>
        )}

        {/* Reasoning chain */}
        {reasoningChain.length > 0 && (
          <div className="reasoning-chain">
            <div className="reasoning-chain-header" onClick={() => setShowReasoning(!showReasoning)}>
              <span className="reasoning-icon">💭</span>
              <span>Reasoning</span>
              <span className="reasoning-step-count">{reasoningChain.length} steps</span>
              <span className={`reasoning-chevron ${showReasoning ? 'expanded' : ''}`}>▾</span>
            </div>
            {showReasoning && (
              <div className="reasoning-chain-body">
                {reasoningChain.map((step, i) => (
                  <div key={i} className="reasoning-step">
                    <span className="reasoning-step-num">{i + 1}</span>
                    <span className="reasoning-step-text">{step}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Streaming content — using enhanced StreamingMessage */}
        {streamingContent && (
          <StreamingMessage
            content={streamingContent}
            agentName={agent.name}
            agentColor={agentGradient}
          />
        )}

        {/* Typing indicator */}
        {loading && !streamingContent && (
          <div className="msg-row msg-assistant">
            <div
              className="msg-avatar"
              style={{ background: agentGradient }}
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

      {/* Message Branches */}
      {showBranches && messageBranches.length > 0 && (
        <div className="message-branches">
          <div className="branch-header">
            <span className="branch-label">Alternative responses</span>
            <button className="branch-close" onClick={() => setShowBranches(false)}>×</button>
          </div>
          <div className="branch-options">
            {messageBranches.map((branch) => (
              <div
                key={branch.branch_id}
                className="branch-option"
                onClick={() => handleSwitchBranch(branch.branch_id)}
              >
                <div className="branch-preview">
                  {branch.messages.length > 0 ? branch.messages[branch.messages.length - 1].content.slice(0, 100) + '...' : 'Empty branch'}
                </div>
                <div className="branch-meta">
                  <span className="branch-time">{new Date(branch.created_at).toLocaleTimeString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Replies */}
      {showQuickReplies && quickReplies.length > 0 && (
        <div className="quick-replies">
          <div className="quick-replies-header">
            <span className="quick-replies-label">Quick replies</span>
            <button className="quick-replies-close" onClick={() => setShowQuickReplies(false)}>×</button>
          </div>
          <div className="quick-replies-options">
            {quickReplies.map((qr) => (
              <button
                key={qr.id}
                className="quick-reply-btn"
                onClick={() => {
                  setInput(qr.text);
                  setShowQuickReplies(false);
                  inputRef.current?.focus();
                }}
              >
                <span className="qr-category">{qr.category}</span>
                <span className="qr-text">{qr.text}</span>
              </button>
            ))}
          </div>
        </div>
      )}

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