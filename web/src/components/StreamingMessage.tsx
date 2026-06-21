import React, { useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';

interface StreamingMessageProps {
  content: string;
  agentName: string;
  agentColor?: string;
}

/** Inline code block for streaming markdown (no copy buttons needed during stream). */
const StreamingCodeBlock: React.FC<{ language: string; code: string }> = ({ language, code }) => (
  <div className="code-block-wrapper streaming-code">
    <div className="code-block-header">
      <span className="code-lang">{language}</span>
    </div>
    <pre className="code-block">
      <code className={language ? `language-${language}` : ''}>{code}</code>
    </pre>
  </div>
);

const streamingComponents: Components = {
  code({ className, children }) {
    const match = /language-(\w+)/.exec(className || '');
    const isInline = !match;
    const codeStr = String(children).replace(/\n$/, '');
    if (isInline) {
      return <code className="inline-code">{children}</code>;
    }
    return <StreamingCodeBlock language={match![1]} code={codeStr} />;
  },
  p({ children }) {
    return <p className="md-paragraph">{children}</p>;
  },
  ul({ children }) {
    return <ul className="md-list">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="md-list md-list-ordered">{children}</ol>;
  },
  li({ children }) {
    return <li className="md-list-item">{children}</li>;
  },
  a({ href, children }) {
    return <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">{children}</a>;
  },
  blockquote({ children }) {
    return <blockquote className="md-blockquote">{children}</blockquote>;
  },
  h1({ children }) {
    return <h1 className="md-heading md-h1">{children}</h1>;
  },
  h2({ children }) {
    return <h2 className="md-heading md-h2">{children}</h2>;
  },
  h3({ children }) {
    return <h3 className="md-heading md-h3">{children}</h3>;
  },
  table({ children }) {
    return <div className="md-table-wrapper"><table className="md-table">{children}</table></div>;
  },
  th({ children }) {
    return <th className="md-th">{children}</th>;
  },
  td({ children }) {
    return <td className="md-td">{children}</td>;
  },
};

export const StreamingMessage: React.FC<StreamingMessageProps> = ({
  content,
  agentName,
  agentColor,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom as content streams
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [content]);

  return (
    <div className="msg-row msg-assistant streaming-row">
      <div
        className="msg-avatar"
        style={agentColor ? { background: agentColor } : undefined}
      >
        {agentName.charAt(0).toUpperCase()}
      </div>
      <div className="msg-bubble bubble-assistant streaming-bubble">
        <div className="msg-header">
          <span className="msg-sender">{agentName}</span>
          <span className="streaming-badge">Streaming...</span>
        </div>
        <div className="msg-content" ref={containerRef}>
          <div className="markdown-body">
            <ReactMarkdown components={streamingComponents}>
              {content}
            </ReactMarkdown>
          </div>
          <span className="cursor-blink">|</span>
        </div>
      </div>
    </div>
  );
};