import React from 'react';
import type { Message as MsgType } from '../types';
import MarkdownMessage from './MarkdownMessage';

interface MessageBubbleProps {
  message: MsgType;
  agentName: string;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, agentName }) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  if (isSystem) return null;

  return (
    <div className={`msg-row ${isUser ? 'msg-user' : 'msg-assistant'}`}>
      {!isUser && (
        <div className="msg-avatar">
          {agentName.charAt(0).toUpperCase()}
        </div>
      )}
      <div className={`msg-bubble ${isUser ? 'bubble-user' : 'bubble-assistant'}`}>
        <div className="msg-sender">{isUser ? 'You' : agentName}</div>
        <div className="msg-content">
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <MarkdownMessage content={message.content} />
          )}
        </div>
      </div>
      {isUser && (
        <div className="msg-avatar msg-avatar-user">
          U
        </div>
      )}
    </div>
  );
};