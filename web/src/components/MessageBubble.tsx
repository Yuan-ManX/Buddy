import React, { useState, useCallback } from 'react';
import type { Message as MsgType } from '../types';
import MarkdownMessage from './MarkdownMessage';

interface MessageBubbleProps {
  message: MsgType;
  agentName: string;
  onRetry?: (content: string) => void;
  onReact?: (messageId: string, emoji: string) => void;
}

const COMMON_REACTIONS = ['👍', '👎', '❤️', '😂', '🤔', '🎯', '💡', '🔥', '👏', '✅'];

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, agentName, onRetry, onReact }) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const [copied, setCopied] = useState(false);
  const [showActions, setShowActions] = useState(false);
  const [showReactions, setShowReactions] = useState(false);
  const [localReactions, setLocalReactions] = useState<Record<string, number>>({});

  const messageDate = new Date(message.created_at);
  const timeStr = messageDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const fullDateTime = messageDate.toLocaleString([], {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = message.content;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [message.content]);

  const handleReaction = useCallback((emoji: string) => {
    setLocalReactions((prev) => ({
      ...prev,
      [emoji]: (prev[emoji] || 0) + 1,
    }));
    setShowReactions(false);
    onReact?.(message.id, emoji);
  }, [message.id, onReact]);

  const handleRegenerate = useCallback(() => {
    onRetry?.(message.content);
  }, [message.content, onRetry]);

  if (isSystem) return null;

  return (
    <div
      className={`msg-row ${isUser ? 'msg-user' : 'msg-assistant'}`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => {
        setShowActions(false);
        setShowReactions(false);
      }}
    >
      {!isUser && (
        <div className="msg-avatar">
          {agentName.charAt(0).toUpperCase()}
        </div>
      )}
      <div className={`msg-bubble ${isUser ? 'bubble-user' : 'bubble-assistant'}`}>
        <div className="msg-header">
          <span className="msg-sender">{isUser ? 'You' : agentName}</span>
          {!isUser && (
            <span className="msg-time" title={fullDateTime}>
              {timeStr}
              <span className="msg-time-tooltip">{fullDateTime}</span>
            </span>
          )}
        </div>
        <div className="msg-content">
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <MarkdownMessage content={message.content} />
          )}
        </div>

        {/* Inline reactions display */}
        {Object.keys(localReactions).length > 0 && (
          <div className="msg-reactions">
            {Object.entries(localReactions).map(([emoji, count]) => (
              <button
                key={emoji}
                className="msg-reaction-chip"
                onClick={() => handleReaction(emoji)}
                title={`React with ${emoji}`}
              >
                {emoji} {count > 1 && <span className="msg-reaction-count">{count}</span>}
              </button>
            ))}
          </div>
        )}

        {/* Message actions */}
        {showActions && !isUser && (
          <div className="msg-actions">
            <button className="msg-action-btn" onClick={handleCopy} title="Copy message">
              {copied ? '✓ Copied' : '📋 Copy'}
            </button>
            {onRetry && (
              <button className="msg-action-btn" onClick={handleRegenerate} title="Regenerate response">
                🔄 Regenerate
              </button>
            )}
            <div className="msg-reactions-wrapper">
              <button
                className="msg-action-btn"
                onClick={() => setShowReactions(!showReactions)}
                title="Add reaction"
              >
                😀 React
              </button>
              {showReactions && (
                <div className="msg-reactions-picker">
                  {COMMON_REACTIONS.map((emoji) => (
                    <button
                      key={emoji}
                      className="msg-reaction-picker-btn"
                      onClick={() => handleReaction(emoji)}
                      title={emoji}
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      {isUser && (
        <div className="msg-avatar msg-avatar-user">
          U
        </div>
      )}
    </div>
  );
};