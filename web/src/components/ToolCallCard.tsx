import React, { useState, useCallback } from 'react';

interface ToolCallState {
  id: string;
  name: string;
  arguments: string;
  result: string | null;
  status: 'pending' | 'running' | 'done' | 'error';
}

interface ToolCallCardProps {
  toolCall: ToolCallState;
}

const STATUS_ICONS: Record<string, string> = {
  pending: '○',
  running: '◌',
  done: '✓',
  error: '✗',
};

const STATUS_LABELS: Record<string, string> = {
  pending: 'Waiting',
  running: 'Running',
  done: 'Complete',
  error: 'Failed',
};

export const ToolCallCard: React.FC<ToolCallCardProps> = ({ toolCall }) => {
  const [expanded, setExpanded] = useState(false);
  const [argsCopied, setArgsCopied] = useState(false);
  const [resultCopied, setResultCopied] = useState(false);

  const handleCopyArgs = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(toolCall.arguments);
      setArgsCopied(true);
      setTimeout(() => setArgsCopied(false), 2000);
    } catch {}
  }, [toolCall.arguments]);

  const handleCopyResult = useCallback(async () => {
    if (!toolCall.result) return;
    try {
      await navigator.clipboard.writeText(toolCall.result);
      setResultCopied(true);
      setTimeout(() => setResultCopied(false), 2000);
    } catch {}
  }, [toolCall.result]);

  const formatJSON = (raw: string): string => {
    try {
      return JSON.stringify(JSON.parse(raw), null, 2);
    } catch {
      return raw;
    }
  };

  const truncateResult = (result: string, maxLen = 500): string => {
    if (result.length <= maxLen) return result;
    return result.slice(0, maxLen) + '...';
  };

  return (
    <div className={`tool-call-card ${toolCall.status}`}>
      <div className="tool-call-header" onClick={() => setExpanded(!expanded)}>
        <div className="tool-call-left">
          <span className={`tool-call-status-icon ${toolCall.status}`}>
            {toolCall.status === 'running' && <span className="tool-call-spinner" />}
            {toolCall.status !== 'running' && STATUS_ICONS[toolCall.status]}
          </span>
          <span className="tool-call-name">{toolCall.name}</span>
        </div>
        <div className="tool-call-right">
          <span className="tool-call-status-text">{STATUS_LABELS[toolCall.status]}</span>
          <span className={`tool-call-chevron ${expanded ? 'expanded' : ''}`}>▾</span>
        </div>
      </div>

      {expanded && (
        <div className="tool-call-body">
          <div className="tool-call-section">
            <div className="tool-call-section-header">
              <span className="tool-call-section-label">Arguments</span>
              <button className="tool-call-copy-btn" onClick={handleCopyArgs}>
                {argsCopied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <pre className="tool-call-code">{formatJSON(toolCall.arguments)}</pre>
          </div>

          {toolCall.result && (
            <div className="tool-call-section">
              <div className="tool-call-section-header">
                <span className="tool-call-section-label">Result</span>
                <button className="tool-call-copy-btn" onClick={handleCopyResult}>
                  {resultCopied ? 'Copied' : 'Copy'}
                </button>
              </div>
              <pre className="tool-call-code">{truncateResult(toolCall.result)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};