import React, { useState, useCallback } from 'react';
import type { Message as MsgType } from '../types';
import MarkdownMessage from './MarkdownMessage';

interface MessageBubbleProps {
  message: MsgType;
  agentName: string;
  onRetry?: (content: string) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, agentName, onRetry }) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const [copied, setCopied] = useState(false);
  const [showActions, setShowActions] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
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

  if (isSystem) return null;

  return (
    <div
      className={`msg-row ${isUser ? 'msg-user' : 'msg-assistant'}`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
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
            <span className="msg-time">
              {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
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
        {/* Message actions */}
        {showActions && !isUser && (
          <div className="msg-actions">
            <button className="msg-action-btn" onClick={handleCopy} title="Copy message">
              {copied ? '✓ Copied' : '📋 Copy'}
            </button>
            {onRetry && (
              <button className="msg-action-btn" onClick={() => onRetry(message.content)} title="Retry with this prompt">
                🔄 Retry
              </button>
            )}
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