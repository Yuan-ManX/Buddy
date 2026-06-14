import React, { useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';

interface MarkdownMessageProps {
  content: string;
}

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = code;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [code]);

  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        <span className="code-lang">{language}</span>
        <button className="code-copy-btn" onClick={handleCopy} title="Copy code">
          {copied ? '✓ Copied' : '📋 Copy'}
        </button>
      </div>
      <pre className="code-block">
        <code className={language ? `language-${language}` : ''}>
          {code}
        </code>
      </pre>
    </div>
  );
}

/** Custom components for rendering markdown in chat messages. */
const markdownComponents: Components = {
  code({ className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || '');
    const isInline = !match;
    const codeStr = String(children).replace(/\n$/, '');

    if (isInline) {
      return (
        <code className="inline-code" {...props}>
          {children}
        </code>
      );
    }

    return <CodeBlock language={match![1]} code={codeStr} />;
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
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">
        {children}
      </a>
    );
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

export default function MarkdownMessage({ content }: MarkdownMessageProps) {
  return (
    <div className="markdown-body">
      <ReactMarkdown components={markdownComponents}>
        {content}
      </ReactMarkdown>
    </div>
  );
}