import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// ── Types ──

interface CodeReviewFinding {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  dimension: string;
  line_start: number;
  line_end: number;
  title: string;
  description: string;
  suggestion: string;
}

interface CodeReviewResult {
  review_id: string;
  score: number;
  summary: string;
  commentary: string;
  findings: CodeReviewFinding[];
  severity_distribution: Record<string, number>;
  metrics: Record<string, number>;
}

interface CodeReviewStats {
  total_reviews: number;
  average_score: number;
  critical_issues_found: number;
  patterns_learned: number;
  recent_reviews: Array<{
    review_id: string;
    file_path: string;
    score: number;
    critical_count: number;
    timestamp: string;
  }>;
}

interface ReviewHistoryEntry {
  review_id: string;
  file_path: string;
  score: number;
  critical_count: number;
  timestamp: string;
}

interface BatchFile {
  id: string;
  code: string;
  language: string;
  file_path: string;
}

interface CodeReviewPanelProps {
  onNavigate?: (tab: string) => void;
}

// ── Constants ──

const LANGUAGES = [
  'Python', 'TypeScript', 'JavaScript', 'Go', 'Rust',
  'Java', 'C++', 'C#', 'Ruby', 'PHP', 'Swift', 'Kotlin',
  'Scala', 'Shell', 'SQL', 'HTML', 'CSS', 'YAML', 'JSON',
];

const DIMENSIONS = [
  'Security', 'Performance', 'Style', 'Architecture',
  'Maintainability', 'Reliability', 'Testing', 'Documentation',
  'Complexity', 'Best Practices',
];

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#f59e0b',
  low: '#22c55e',
  info: '#3b82f6',
};

const SEVERITY_LABELS: Record<string, string> = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  info: 'Info',
};

// ── Component ──

export const CodeReviewPanel: React.FC<CodeReviewPanelProps> = ({ onNavigate }) => {
  const toast = useToast();

  // Core state
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('Python');
  const [filePath, setFilePath] = useState('');
  const [mode, setMode] = useState<'single' | 'diff'>('single');
  const [diffInput, setDiffInput] = useState('');
  const [diffFilePaths, setDiffFilePaths] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CodeReviewResult | null>(null);
  const [stats, setStats] = useState<CodeReviewStats | null>(null);
  const [activeTab, setActiveTab] = useState<'findings' | 'summary' | 'details'>('findings');
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<Set<string>>(new Set());
  const [dimensionFilter, setDimensionFilter] = useState<Set<string>>(new Set());

  // Findings UI state
  const [expandedFindings, setExpandedFindings] = useState<Set<string>>(new Set());
  const [highlightedLines, setHighlightedLines] = useState<[number, number] | null>(null);

  // Batch mode
  const [batchMode, setBatchMode] = useState(false);
  const [batchFiles, setBatchFiles] = useState<BatchFile[]>([
    { id: '1', code: '', language: 'Python', file_path: '' },
  ]);
  const [batchResult, setBatchResult] = useState<CodeReviewResult | null>(null);

  // History
  const [reviewHistory, setReviewHistory] = useState<ReviewHistoryEntry[]>([]);

  const codeDisplayRef = useRef<HTMLDivElement>(null);

  // ── Data Loading ──

  const loadStats = useCallback(async () => {
    try {
      const s = await api.codeReview.stats();
      setStats(s);
      setReviewHistory(s.recent_reviews || []);
    } catch {
      // Stats are non-critical; silence errors
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // ── Review Handlers ──

  const handleReview = async () => {
    if (!code.trim()) {
      toast.warning('Please enter code to review');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    setHighlightedLines(null);
    try {
      const res = await api.codeReview.review({
        code,
        language,
        file_path: filePath || undefined,
      });
      setResult(res);
      addToHistory(res.review_id, filePath || 'untitled', res.score, res.severity_distribution.critical || 0);
      toast.success('Review completed successfully');
      loadStats();
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Review failed';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleDiffReview = async () => {
    if (!diffInput.trim()) {
      toast.warning('Please enter diff content');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    setHighlightedLines(null);
    try {
      const filePaths = diffFilePaths
        ? diffFilePaths.split(',').map((s) => s.trim()).filter(Boolean)
        : undefined;
      const res = await api.codeReview.diff({
        diff: diffInput,
        file_paths: filePaths,
      });
      setResult(res);
      addToHistory(res.review_id, 'diff review', res.score, res.severity_distribution.critical || 0);
      toast.success('Diff review completed successfully');
      loadStats();
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Diff review failed';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleBatchReview = async () => {
    const validFiles = batchFiles.filter((f) => f.code.trim());
    if (validFiles.length === 0) {
      toast.warning('Please enter code in at least one file');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.codeReview.batch({
        files: validFiles.map((f) => ({
          code: f.code,
          language: f.language,
          file_path: f.file_path || f.id,
        })),
      });
      // Use the first result or aggregate
      if (res.results.length > 0) {
        setResult(res.results[0].review);
      }
      toast.success(`Batch review completed for ${res.results.length} files`);
      loadStats();
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Batch review failed';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  // ── History ──

  const addToHistory = (reviewId: string, path: string, score: number, criticalCount: number) => {
    setReviewHistory((prev) => [
      {
        review_id: reviewId,
        file_path: path,
        score,
        critical_count: criticalCount,
        timestamp: new Date().toISOString(),
      },
      ...prev.slice(0, 19),
    ]);
  };

  // ── Batch File Management ──

  const addBatchFile = () => {
    setBatchFiles((prev) => [
      ...prev,
      { id: String(Date.now()), code: '', language: 'Python', file_path: '' },
    ]);
  };

  const removeBatchFile = (id: string) => {
    setBatchFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const updateBatchFile = (id: string, field: keyof BatchFile, value: string) => {
    setBatchFiles((prev) =>
      prev.map((f) => (f.id === id ? { ...f, [field]: value } : f))
    );
  };

  // ── Filter Toggles ──

  const toggleSeverityFilter = (s: string) => {
    setSeverityFilter((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  };

  const toggleDimensionFilter = (d: string) => {
    setDimensionFilter((prev) => {
      const next = new Set(prev);
      if (next.has(d)) next.delete(d);
      else next.add(d);
      return next;
    });
  };

  const toggleFindingExpanded = (id: string) => {
    setExpandedFindings((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // ── Highlight ──

  const highlightLines = (start: number, end: number) => {
    setHighlightedLines([start, end]);
    if (codeDisplayRef.current) {
      const lineEl = codeDisplayRef.current.querySelector(
        `[data-line="${start}"]`
      );
      if (lineEl) {
        lineEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  };

  // ── Filtered Findings ──

  const filteredFindings = (result?.findings || []).filter((f) => {
    if (severityFilter.size > 0 && !severityFilter.has(f.severity)) return false;
    if (dimensionFilter.size > 0 && !dimensionFilter.has(f.dimension)) return false;
    return true;
  });

  const groupedFindings = filteredFindings.reduce(
    (acc, f) => {
      const key = f.severity;
      if (!acc[key]) acc[key] = [];
      acc[key].push(f);
      return acc;
    },
    {} as Record<string, CodeReviewFinding[]>
  );

  const severityOrder = ['critical', 'high', 'medium', 'low', 'info'];

  // ── Score Gauge ──

  const getScoreColor = (score: number) => {
    if (score >= 80) return '#22c55e';
    if (score >= 60) return '#f59e0b';
    if (score >= 40) return '#f97316';
    return '#ef4444';
  };

  // ── Code Rendering (simple line-numbered view) ──

  const renderCodeLines = (source: string) => {
    const lines = source.split('\n');
    return lines.map((line, i) => {
      const lineNum = i + 1;
      const isHighlighted =
        highlightedLines &&
        lineNum >= highlightedLines[0] &&
        lineNum <= highlightedLines[1];
      return (
        <div
          key={i}
          data-line={lineNum}
          style={{
            ...styles.codeLine,
            background: isHighlighted ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
            borderLeft: isHighlighted ? '3px solid #3b82f6' : '3px solid transparent',
          }}
        >
          <span style={styles.lineNumber}>{lineNum}</span>
          <span style={styles.lineContent}>{line || ' '}</span>
        </div>
      );
    });
  };

  // ── Render ──

  return (
    <div style={styles.panel}>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={styles.headerTitle}>Code Review</h2>
        <div style={styles.headerActions}>
          {onNavigate && (
            <button
              style={styles.headerBtn}
              onClick={() => onNavigate('code-review')}
            >
              Navigate
            </button>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div style={styles.errorBanner}>
          <span>{error}</span>
          <button style={styles.errorClose} onClick={() => setError(null)}>
            ✕
          </button>
        </div>
      )}

      {/* Main Content: Two Columns */}
      <div style={styles.mainContent}>
        {/* Left Sidebar */}
        <div style={styles.sidebar}>
          {/* Mode Toggle */}
          <div style={styles.modeToggle}>
            <button
              style={{
                ...styles.modeBtn,
                background: mode === 'single' ? '#0f3460' : 'transparent',
                color: mode === 'single' ? '#e0e0e0' : '#888',
              }}
              onClick={() => setMode('single')}
            >
              Single File
            </button>
            <button
              style={{
                ...styles.modeBtn,
                background: mode === 'diff' ? '#0f3460' : 'transparent',
                color: mode === 'diff' ? '#e0e0e0' : '#888',
              }}
              onClick={() => setMode('diff')}
            >
              Diff Review
            </button>
          </div>

          {mode === 'single' && !batchMode && (
            <>
              {/* Language Selector */}
              <div style={styles.fieldGroup}>
                <label style={styles.fieldLabel}>Language</label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  style={styles.select}
                >
                  {LANGUAGES.map((lang) => (
                    <option key={lang} value={lang}>
                      {lang}
                    </option>
                  ))}
                </select>
              </div>

              {/* File Path */}
              <div style={styles.fieldGroup}>
                <label style={styles.fieldLabel}>File Path</label>
                <input
                  type="text"
                  value={filePath}
                  onChange={(e) => setFilePath(e.target.value)}
                  placeholder="src/main.py"
                  style={styles.input}
                />
              </div>

              {/* Code Textarea */}
              <div style={styles.fieldGroup}>
                <label style={styles.fieldLabel}>Code</label>
                <textarea
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="Paste your code here..."
                  rows={12}
                  style={styles.textarea}
                  spellCheck={false}
                />
              </div>

              {/* Review Button */}
              <button
                onClick={handleReview}
                disabled={loading || !code.trim()}
                style={{
                  ...styles.primaryBtn,
                  opacity: loading || !code.trim() ? 0.6 : 1,
                }}
              >
                {loading ? (
                  <>
                    <span style={styles.spinner} />
                    Reviewing...
                  </>
                ) : (
                  'Review Code'
                )}
              </button>
            </>
          )}

          {mode === 'diff' && (
            <>
              {/* Diff Input */}
              <div style={styles.fieldGroup}>
                <label style={styles.fieldLabel}>Diff Content (unified format)</label>
                <textarea
                  value={diffInput}
                  onChange={(e) => setDiffInput(e.target.value)}
                  placeholder="Paste unified diff here..."
                  rows={10}
                  style={styles.textarea}
                  spellCheck={false}
                />
              </div>

              {/* Diff File Paths */}
              <div style={styles.fieldGroup}>
                <label style={styles.fieldLabel}>File Paths (comma-separated)</label>
                <input
                  type="text"
                  value={diffFilePaths}
                  onChange={(e) => setDiffFilePaths(e.target.value)}
                  placeholder="src/main.py, src/utils.py"
                  style={styles.input}
                />
              </div>

              {/* Review Diff Button */}
              <button
                onClick={handleDiffReview}
                disabled={loading || !diffInput.trim()}
                style={{
                  ...styles.primaryBtn,
                  opacity: loading || !diffInput.trim() ? 0.6 : 1,
                }}
              >
                {loading ? (
                  <>
                    <span style={styles.spinner} />
                    Reviewing...
                  </>
                ) : (
                  'Review Diff'
                )}
              </button>
            </>
          )}

          {/* Batch Mode Toggle */}
          <div style={styles.batchToggle}>
            <label style={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={batchMode}
                onChange={(e) => setBatchMode(e.target.checked)}
                style={styles.checkbox}
              />
              Batch Review Mode
            </label>
          </div>

          {/* Batch Mode Files */}
          {batchMode && (
            <div style={styles.batchSection}>
              {batchFiles.map((file) => (
                <div key={file.id} style={styles.batchFile}>
                  <div style={styles.batchFileHeader}>
                    <input
                      type="text"
                      value={file.file_path}
                      onChange={(e) =>
                        updateBatchFile(file.id, 'file_path', e.target.value)
                      }
                      placeholder="File path"
                      style={styles.batchFilePathInput}
                    />
                    <select
                      value={file.language}
                      onChange={(e) =>
                        updateBatchFile(file.id, 'language', e.target.value)
                      }
                      style={styles.batchLangSelect}
                    >
                      {LANGUAGES.map((lang) => (
                        <option key={lang} value={lang}>
                          {lang}
                        </option>
                      ))}
                    </select>
                    {batchFiles.length > 1 && (
                      <button
                        style={styles.removeFileBtn}
                        onClick={() => removeBatchFile(file.id)}
                      >
                        ✕
                      </button>
                    )}
                  </div>
                  <textarea
                    value={file.code}
                    onChange={(e) =>
                      updateBatchFile(file.id, 'code', e.target.value)
                    }
                    placeholder="Paste code..."
                    rows={6}
                    style={styles.batchTextarea}
                    spellCheck={false}
                  />
                </div>
              ))}
              <div style={styles.batchActions}>
                <button style={styles.secondaryBtn} onClick={addBatchFile}>
                  + Add File
                </button>
                <button
                  onClick={handleBatchReview}
                  disabled={loading}
                  style={{
                    ...styles.primaryBtn,
                    opacity: loading ? 0.6 : 1,
                  }}
                >
                  {loading ? 'Reviewing...' : 'Review All Files'}
                </button>
              </div>
            </div>
          )}

          {/* Review History */}
          <div style={styles.historySection}>
            <h3 style={styles.sectionTitle}>Recent Reviews</h3>
            {reviewHistory.length === 0 && (
              <div style={styles.historyEmpty}>No reviews yet</div>
            )}
            {reviewHistory.map((entry) => (
              <div key={entry.review_id} style={styles.historyItem}>
                <div style={styles.historyItemTop}>
                  <span style={styles.historyFilePath} title={entry.file_path}>
                    {entry.file_path.length > 30
                      ? '...' + entry.file_path.slice(-27)
                      : entry.file_path}
                  </span>
                  <span
                    style={{
                      ...styles.severityBadge,
                      background: getScoreColor(entry.score),
                    }}
                  >
                    {entry.score}
                  </span>
                </div>
                <div style={styles.historyItemBottom}>
                  <span style={styles.historyTimestamp}>
                    {new Date(entry.timestamp).toLocaleDateString()}
                  </span>
                  {entry.critical_count > 0 && (
                    <span style={styles.historyCritical}>
                      {entry.critical_count} critical
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Main Area */}
        <div style={styles.mainArea}>
          {!result && !loading && (
            <div style={styles.emptyState}>
              <div style={styles.emptyIcon}>🔍</div>
              <div style={styles.emptyTitle}>Ready to Review</div>
              <div style={styles.emptySubtitle}>
                Paste your code in the sidebar and click "Review Code" to get started.
              </div>
            </div>
          )}

          {loading && (
            <div style={styles.loadingState}>
              <div style={styles.loadingSpinner} />
              <div style={styles.loadingText}>Analyzing code...</div>
            </div>
          )}

          {result && (
            <>
              {/* Score Gauge + Tab Bar */}
              <div style={styles.resultHeader}>
                <div style={styles.scoreSection}>
                  <div style={styles.scoreGauge}>
                    <svg width="100" height="100" viewBox="0 0 100 100">
                      <circle
                        cx="50"
                        cy="50"
                        r="42"
                        fill="none"
                        stroke="#1e2d4a"
                        strokeWidth="8"
                      />
                      <circle
                        cx="50"
                        cy="50"
                        r="42"
                        fill="none"
                        stroke={getScoreColor(result.score)}
                        strokeWidth="8"
                        strokeDasharray={`${(result.score / 100) * 264} 264`}
                        strokeLinecap="round"
                        transform="rotate(-90 50 50)"
                      />
                      <text
                        x="50"
                        y="50"
                        textAnchor="middle"
                        dominantBaseline="central"
                        fill={getScoreColor(result.score)}
                        fontSize="24"
                        fontWeight="700"
                      >
                        {result.score}
                      </text>
                    </svg>
                  </div>
                  <div style={styles.scoreLabel}>Overall Score</div>
                </div>

                <div style={styles.tabBar}>
                  {(['findings', 'summary', 'details'] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      style={{
                        ...styles.tabBtn,
                        background:
                          activeTab === tab ? '#0f3460' : 'transparent',
                        color: activeTab === tab ? '#e0e0e0' : '#888',
                        borderBottom:
                          activeTab === tab
                            ? '2px solid #3b82f6'
                            : '2px solid transparent',
                      }}
                    >
                      {tab === 'findings'
                        ? `Findings (${result.findings.length})`
                        : tab === 'summary'
                        ? 'Summary'
                        : 'Details'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Code Display */}
              <div style={styles.codeSection}>
                <div style={styles.codeSectionHeader}>
                  <span style={styles.codeSectionTitle}>
                    {filePath || 'Source Code'}
                  </span>
                  <span style={styles.codeSectionLang}>{language}</span>
                </div>
                <div ref={codeDisplayRef} style={styles.codeDisplay}>
                  {renderCodeLines(code)}
                </div>
              </div>

              {/* Tab Content */}
              <div style={styles.tabContent}>
                {activeTab === 'findings' && (
                  <div style={styles.findingsTab}>
                    {/* Filters */}
                    <div style={styles.filters}>
                      <div style={styles.filterGroup}>
                        <span style={styles.filterLabel}>Severity:</span>
                        {severityOrder.map((sev) => (
                          <button
                            key={sev}
                            onClick={() => toggleSeverityFilter(sev)}
                            style={{
                              ...styles.filterChip,
                              background: severityFilter.has(sev)
                                ? SEVERITY_COLORS[sev]
                                : 'transparent',
                              borderColor: SEVERITY_COLORS[sev],
                              color: severityFilter.has(sev)
                                ? '#fff'
                                : SEVERITY_COLORS[sev],
                            }}
                          >
                            {SEVERITY_LABELS[sev]}
                          </button>
                        ))}
                      </div>
                      <div style={styles.filterGroup}>
                        <span style={styles.filterLabel}>Dimension:</span>
                        {DIMENSIONS.slice(0, 6).map((dim) => (
                          <button
                            key={dim}
                            onClick={() => toggleDimensionFilter(dim)}
                            style={{
                              ...styles.filterChip,
                              background: dimensionFilter.has(dim)
                                ? '#3b82f6'
                                : 'transparent',
                              borderColor: '#3b82f6',
                              color: dimensionFilter.has(dim) ? '#fff' : '#aaa',
                            }}
                          >
                            {dim}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Grouped Findings */}
                    {severityOrder.map((sev) => {
                      const findings = groupedFindings[sev];
                      if (!findings || findings.length === 0) return null;
                      return (
                        <div key={sev} style={styles.findingGroup}>
                          <div style={styles.findingGroupHeader}>
                            <span
                              style={{
                                ...styles.severityIndicator,
                                background: SEVERITY_COLORS[sev],
                              }}
                            />
                            <span style={styles.findingGroupTitle}>
                              {SEVERITY_LABELS[sev]}
                            </span>
                            <span style={styles.findingGroupCount}>
                              {findings.length}
                            </span>
                          </div>
                          {findings.map((finding) => {
                            const isExpanded = expandedFindings.has(finding.id);
                            return (
                              <div
                                key={finding.id}
                                style={styles.findingCard}
                                onClick={() => highlightLines(finding.line_start, finding.line_end)}
                              >
                                <div
                                  style={styles.findingCardHeader}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    toggleFindingExpanded(finding.id);
                                  }}
                                >
                                  <div style={styles.findingCardLeft}>
                                    <span
                                      style={{
                                        ...styles.severityBadge,
                                        background: SEVERITY_COLORS[finding.severity],
                                      }}
                                    >
                                      {SEVERITY_LABELS[finding.severity]}
                                    </span>
                                    <span style={styles.dimensionBadge}>
                                      {finding.dimension}
                                    </span>
                                    <span style={styles.findingTitle}>
                                      {finding.title}
                                    </span>
                                  </div>
                                  <div style={styles.findingCardRight}>
                                    <span style={styles.lineRange}>
                                      L{finding.line_start}-L{finding.line_end}
                                    </span>
                                    <span style={styles.expandIcon}>
                                      {isExpanded ? '▼' : '▶'}
                                    </span>
                                  </div>
                                </div>
                                {isExpanded && (
                                  <div style={styles.findingCardBody}>
                                    <div style={styles.findingDescription}>
                                      {finding.description}
                                    </div>
                                    {finding.suggestion && (
                                      <div style={styles.findingSuggestion}>
                                        <strong>Suggestion:</strong>{' '}
                                        {finding.suggestion}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      );
                    })}

                    {filteredFindings.length === 0 && (
                      <div style={styles.noFindings}>
                        No findings match the current filters.
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'summary' && (
                  <div style={styles.summaryTab}>
                    {/* Summary Text */}
                    <div style={styles.summaryCard}>
                      <h3 style={styles.summaryCardTitle}>Summary</h3>
                      <p style={styles.summaryText}>{result.summary}</p>
                    </div>

                    {/* Severity Distribution */}
                    <div style={styles.summaryCard}>
                      <h3 style={styles.summaryCardTitle}>
                        Severity Distribution
                      </h3>
                      {severityOrder.map((sev) => {
                        const count = result.severity_distribution[sev] || 0;
                        const maxCount = Math.max(
                          ...Object.values(result.severity_distribution),
                          1
                        );
                        const barWidth = (count / maxCount) * 100;
                        return (
                          <div key={sev} style={styles.distributionRow}>
                            <span
                              style={{
                                ...styles.distributionLabel,
                                color: SEVERITY_COLORS[sev],
                              }}
                            >
                              {SEVERITY_LABELS[sev]}
                            </span>
                            <div style={styles.distributionBar}>
                              <div
                                style={{
                                  ...styles.distributionBarFill,
                                  width: `${barWidth}%`,
                                  background: SEVERITY_COLORS[sev],
                                }}
                              />
                            </div>
                            <span style={styles.distributionCount}>
                              {count}
                            </span>
                          </div>
                        );
                      })}
                    </div>

                    {/* Key Metrics */}
                    {Object.keys(result.metrics).length > 0 && (
                      <div style={styles.summaryCard}>
                        <h3 style={styles.summaryCardTitle}>Key Metrics</h3>
                        <div style={styles.metricsGrid}>
                          {Object.entries(result.metrics).map(([key, val]) => (
                            <div key={key} style={styles.metricItem}>
                              <div style={styles.metricValue}>
                                {typeof val === 'number'
                                  ? val % 1 === 0
                                    ? val
                                    : val.toFixed(2)
                                  : String(val)}
                              </div>
                              <div style={styles.metricLabel}>
                                {key.replace(/_/g, ' ')}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Score Progress */}
                    <div style={styles.summaryCard}>
                      <h3 style={styles.summaryCardTitle}>Score</h3>
                      <div style={styles.scoreProgressBar}>
                        <div
                          style={{
                            ...styles.scoreProgressFill,
                            width: `${result.score}%`,
                            background: getScoreColor(result.score),
                          }}
                        />
                      </div>
                      <div style={styles.scoreProgressLabel}>
                        {result.score}/100
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === 'details' && (
                  <div style={styles.detailsTab}>
                    <div style={styles.commentaryCard}>
                      <h3 style={styles.summaryCardTitle}>Full Commentary</h3>
                      <div style={styles.commentaryText}>
                        {result.commentary.split('\n').map((line, i) => {
                          // Simple markdown-like rendering
                          if (line.startsWith('### ')) {
                            return (
                              <h4 key={i} style={styles.commentaryH3}>
                                {line.slice(4)}
                              </h4>
                            );
                          }
                          if (line.startsWith('## ')) {
                            return (
                              <h3 key={i} style={styles.commentaryH2}>
                                {line.slice(3)}
                              </h3>
                            );
                          }
                          if (line.startsWith('# ')) {
                            return (
                              <h2 key={i} style={styles.commentaryH1}>
                                {line.slice(2)}
                              </h2>
                            );
                          }
                          if (line.startsWith('- ')) {
                            return (
                              <div key={i} style={styles.commentaryListItem}>
                                • {line.slice(2)}
                              </div>
                            );
                          }
                          if (line.startsWith('**') && line.endsWith('**')) {
                            return (
                              <div key={i} style={styles.commentaryBold}>
                                {line.slice(2, -2)}
                              </div>
                            );
                          }
                          return (
                            <p key={i} style={styles.commentaryParagraph}>
                              {line || '\u00A0'}
                            </p>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Diff View (side-by-side) */}
              {mode === 'diff' && diffInput && (
                <div style={styles.diffSection}>
                  <div style={styles.codeSectionHeader}>
                    <span style={styles.codeSectionTitle}>Diff View</span>
                  </div>
                  <div style={styles.diffView}>
                    {diffInput.split('\n').map((line, i) => {
                      let lineStyle: React.CSSProperties = {
                        ...styles.diffLine,
                      };
                      let prefix = ' ';
                      if (line.startsWith('+')) {
                        lineStyle = {
                          ...lineStyle,
                          background: 'rgba(34, 197, 94, 0.1)',
                          color: '#22c55e',
                        };
                        prefix = '+';
                      } else if (line.startsWith('-')) {
                        lineStyle = {
                          ...lineStyle,
                          background: 'rgba(239, 68, 68, 0.1)',
                          color: '#ef4444',
                        };
                        prefix = '-';
                      } else if (line.startsWith('@@')) {
                        lineStyle = {
                          ...lineStyle,
                          background: 'rgba(59, 130, 246, 0.1)',
                          color: '#3b82f6',
                          fontWeight: 600,
                        };
                        prefix = '';
                      }
                      return (
                        <div key={i} style={lineStyle}>
                          <span style={styles.diffLineNum}>{i + 1}</span>
                          <span style={styles.diffLinePrefix}>{prefix}</span>
                          <span>{line}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Stats Bar */}
      <div style={styles.statsBar}>
        <div style={styles.statItem}>
          <span style={styles.statValue}>
            {stats?.total_reviews ?? 0}
          </span>
          <span style={styles.statLabel}>Total Reviews</span>
        </div>
        <div style={styles.statDivider} />
        <div style={styles.statItem}>
          <span style={styles.statValue}>
            {stats?.average_score != null
              ? stats.average_score.toFixed(1)
              : '--'}
          </span>
          <span style={styles.statLabel}>Avg Score</span>
        </div>
        <div style={styles.statDivider} />
        <div style={styles.statItem}>
          <span style={{ ...styles.statValue, color: '#ef4444' }}>
            {stats?.critical_issues_found ?? 0}
          </span>
          <span style={styles.statLabel}>Critical Issues</span>
        </div>
        <div style={styles.statDivider} />
        <div style={styles.statItem}>
          <span style={{ ...styles.statValue, color: '#3b82f6' }}>
            {stats?.patterns_learned ?? 0}
          </span>
          <span style={styles.statLabel}>Patterns Learned</span>
        </div>
      </div>
    </div>
  );
};

// ── Styles ──

const styles = {
  panel: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    background: '#1a1a2e',
    color: '#e0e0e0',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontSize: '13px',
    overflow: 'hidden',
  } as React.CSSProperties,

  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 20px',
    background: '#16213e',
    borderBottom: '1px solid #0f3460',
    flexShrink: 0,
  } as React.CSSProperties,

  headerTitle: {
    margin: 0,
    fontSize: '16px',
    fontWeight: 600,
    color: '#e0e0e0',
  } as React.CSSProperties,

  headerActions: {
    display: 'flex',
    gap: '8px',
  } as React.CSSProperties,

  headerBtn: {
    padding: '6px 14px',
    background: '#0f3460',
    color: '#e0e0e0',
    border: 'none',
    borderRadius: '6px',
    fontSize: '12px',
    cursor: 'pointer',
    fontWeight: 500,
  } as React.CSSProperties,

  errorBanner: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 16px',
    margin: '8px 16px 0',
    background: 'rgba(239, 68, 68, 0.15)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    borderRadius: '8px',
    color: '#fca5a5',
    fontSize: '13px',
    flexShrink: 0,
  } as React.CSSProperties,

  errorClose: {
    background: 'none',
    border: 'none',
    color: '#fca5a5',
    cursor: 'pointer',
    fontSize: '14px',
    padding: '2px 6px',
  } as React.CSSProperties,

  mainContent: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  } as React.CSSProperties,

  // ── Sidebar ──

  sidebar: {
    width: '340px',
    minWidth: '340px',
    background: '#16213e',
    borderRight: '1px solid #0f3460',
    display: 'flex',
    flexDirection: 'column',
    overflowY: 'auto',
    padding: '16px',
    gap: '12px',
    flexShrink: 0,
  } as React.CSSProperties,

  modeToggle: {
    display: 'flex',
    background: '#1a1a2e',
    borderRadius: '8px',
    padding: '3px',
    gap: '3px',
  } as React.CSSProperties,

  modeBtn: {
    flex: 1,
    padding: '8px 12px',
    border: 'none',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background 0.2s',
  } as React.CSSProperties,

  fieldGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  } as React.CSSProperties,

  fieldLabel: {
    fontSize: '11px',
    fontWeight: 600,
    color: '#888',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  } as React.CSSProperties,

  input: {
    width: '100%',
    padding: '8px 12px',
    background: '#1a1a2e',
    border: '1px solid #0f3460',
    borderRadius: '6px',
    color: '#e0e0e0',
    fontSize: '13px',
    fontFamily: 'inherit',
    boxSizing: 'border-box',
    outline: 'none',
  } as React.CSSProperties,

  select: {
    width: '100%',
    padding: '8px 12px',
    background: '#1a1a2e',
    border: '1px solid #0f3460',
    borderRadius: '6px',
    color: '#e0e0e0',
    fontSize: '13px',
    fontFamily: 'inherit',
    boxSizing: 'border-box',
    outline: 'none',
    cursor: 'pointer',
  } as React.CSSProperties,

  textarea: {
    width: '100%',
    padding: '10px 12px',
    background: '#1a1a2e',
    border: '1px solid #0f3460',
    borderRadius: '6px',
    color: '#e0e0e0',
    fontSize: '12px',
    fontFamily: "'Fira Code', 'Cascadia Code', 'JetBrains Mono', monospace",
    resize: 'vertical',
    boxSizing: 'border-box',
    outline: 'none',
    lineHeight: '1.5',
  } as React.CSSProperties,

  primaryBtn: {
    width: '100%',
    padding: '10px 16px',
    background: '#0f3460',
    color: '#e0e0e0',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    transition: 'background 0.2s',
  } as React.CSSProperties,

  secondaryBtn: {
    padding: '8px 14px',
    background: 'transparent',
    color: '#aaa',
    border: '1px solid #0f3460',
    borderRadius: '6px',
    fontSize: '12px',
    cursor: 'pointer',
    fontWeight: 500,
  } as React.CSSProperties,

  spinner: {
    width: '16px',
    height: '16px',
    border: '2px solid rgba(255,255,255,0.3)',
    borderTopColor: '#fff',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
    display: 'inline-block',
  } as React.CSSProperties,

  // ── Batch Mode ──

  batchToggle: {
    padding: '8px 0',
    borderTop: '1px solid #0f3460',
  } as React.CSSProperties,

  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '12px',
    color: '#aaa',
    cursor: 'pointer',
  } as React.CSSProperties,

  checkbox: {
    accentColor: '#3b82f6',
  } as React.CSSProperties,

  batchSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    padding: '8px',
    background: '#1a1a2e',
    borderRadius: '8px',
    border: '1px solid #0f3460',
  } as React.CSSProperties,

  batchFile: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    padding: '8px',
    background: '#16213e',
    borderRadius: '6px',
  } as React.CSSProperties,

  batchFileHeader: {
    display: 'flex',
    gap: '6px',
    alignItems: 'center',
  } as React.CSSProperties,

  batchFilePathInput: {
    flex: 1,
    padding: '5px 8px',
    background: '#1a1a2e',
    border: '1px solid #0f3460',
    borderRadius: '4px',
    color: '#e0e0e0',
    fontSize: '11px',
    fontFamily: 'inherit',
    outline: 'none',
  } as React.CSSProperties,

  batchLangSelect: {
    padding: '5px 6px',
    background: '#1a1a2e',
    border: '1px solid #0f3460',
    borderRadius: '4px',
    color: '#e0e0e0',
    fontSize: '11px',
    fontFamily: 'inherit',
    outline: 'none',
    cursor: 'pointer',
  } as React.CSSProperties,

  removeFileBtn: {
    padding: '3px 8px',
    background: 'none',
    border: 'none',
    color: '#ef4444',
    cursor: 'pointer',
    fontSize: '14px',
  } as React.CSSProperties,

  batchTextarea: {
    width: '100%',
    padding: '6px 8px',
    background: '#1a1a2e',
    border: '1px solid #0f3460',
    borderRadius: '4px',
    color: '#e0e0e0',
    fontSize: '11px',
    fontFamily: "'Fira Code', 'Cascadia Code', 'JetBrains Mono', monospace",
    resize: 'vertical',
    boxSizing: 'border-box',
    outline: 'none',
    lineHeight: '1.4',
  } as React.CSSProperties,

  batchActions: {
    display: 'flex',
    gap: '8px',
    justifyContent: 'space-between',
  } as React.CSSProperties,

  // ── History ──

  historySection: {
    borderTop: '1px solid #0f3460',
    paddingTop: '12px',
    flex: 1,
    minHeight: 0,
    overflowY: 'auto',
  } as React.CSSProperties,

  sectionTitle: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#888',
    margin: '0 0 8px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  } as React.CSSProperties,

  historyEmpty: {
    fontSize: '12px',
    color: '#555',
    textAlign: 'center',
    padding: '16px',
  } as React.CSSProperties,

  historyItem: {
    padding: '8px 10px',
    background: '#1a1a2e',
    borderRadius: '6px',
    marginBottom: '6px',
    cursor: 'pointer',
    border: '1px solid transparent',
    transition: 'border-color 0.2s',
  } as React.CSSProperties,

  historyItemTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '4px',
  } as React.CSSProperties,

  historyFilePath: {
    fontSize: '12px',
    color: '#ccc',
    fontFamily: 'monospace',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  } as React.CSSProperties,

  historyItemBottom: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  } as React.CSSProperties,

  historyTimestamp: {
    fontSize: '10px',
    color: '#555',
  } as React.CSSProperties,

  historyCritical: {
    fontSize: '10px',
    color: '#ef4444',
    fontWeight: 600,
  } as React.CSSProperties,

  // ── Main Area ──

  mainArea: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    background: '#1a1a2e',
  } as React.CSSProperties,

  emptyState: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '12px',
    padding: '40px',
  } as React.CSSProperties,

  emptyIcon: {
    fontSize: '48px',
  } as React.CSSProperties,

  emptyTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: '#888',
  } as React.CSSProperties,

  emptySubtitle: {
    fontSize: '13px',
    color: '#555',
    textAlign: 'center',
    maxWidth: '400px',
    lineHeight: '1.5',
  } as React.CSSProperties,

  loadingState: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '16px',
  } as React.CSSProperties,

  loadingSpinner: {
    width: '40px',
    height: '40px',
    border: '3px solid rgba(59, 130, 246, 0.2)',
    borderTopColor: '#3b82f6',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  } as React.CSSProperties,

  loadingText: {
    fontSize: '14px',
    color: '#888',
  } as React.CSSProperties,

  // ── Result Header ──

  resultHeader: {
    display: 'flex',
    alignItems: 'center',
    padding: '16px 20px',
    gap: '24px',
    borderBottom: '1px solid #0f3460',
    flexShrink: 0,
  } as React.CSSProperties,

  scoreSection: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '6px',
    flexShrink: 0,
  } as React.CSSProperties,

  scoreGauge: {
    width: '100px',
    height: '100px',
  } as React.CSSProperties,

  scoreLabel: {
    fontSize: '11px',
    color: '#888',
    fontWeight: 500,
  } as React.CSSProperties,

  tabBar: {
    display: 'flex',
    gap: '4px',
    flex: 1,
    flexWrap: 'wrap',
  } as React.CSSProperties,

  tabBtn: {
    padding: '8px 16px',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
  } as React.CSSProperties,

  // ── Code Display ──

  codeSection: {
    borderBottom: '1px solid #0f3460',
    flexShrink: 0,
  } as React.CSSProperties,

  codeSectionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 16px',
    background: '#16213e',
    borderBottom: '1px solid #0f3460',
  } as React.CSSProperties,

  codeSectionTitle: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#aaa',
    fontFamily: 'monospace',
  } as React.CSSProperties,

  codeSectionLang: {
    fontSize: '10px',
    color: '#555',
    padding: '2px 8px',
    background: '#1a1a2e',
    borderRadius: '4px',
    fontWeight: 500,
  } as React.CSSProperties,

  codeDisplay: {
    maxHeight: '200px',
    overflowY: 'auto',
    background: '#0d1117',
    fontFamily: "'Fira Code', 'Cascadia Code', 'JetBrains Mono', monospace",
    fontSize: '12px',
    lineHeight: '1.6',
  } as React.CSSProperties,

  codeLine: {
    display: 'flex',
    padding: '0 16px',
    minHeight: '20px',
    transition: 'background 0.15s',
  } as React.CSSProperties,

  lineNumber: {
    width: '44px',
    minWidth: '44px',
    textAlign: 'right',
    paddingRight: '12px',
    color: '#484f58',
    userSelect: 'none',
    fontSize: '11px',
  } as React.CSSProperties,

  lineContent: {
    whiteSpace: 'pre',
    color: '#c9d1d9',
  } as React.CSSProperties,

  // ── Tab Content ──

  tabContent: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px',
  } as React.CSSProperties,

  // ── Findings Tab ──

  findingsTab: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  } as React.CSSProperties,

  filters: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    padding: '10px',
    background: '#16213e',
    borderRadius: '8px',
    border: '1px solid #0f3460',
  } as React.CSSProperties,

  filterGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    flexWrap: 'wrap',
  } as React.CSSProperties,

  filterLabel: {
    fontSize: '11px',
    fontWeight: 600,
    color: '#666',
    marginRight: '4px',
  } as React.CSSProperties,

  filterChip: {
    padding: '3px 10px',
    borderRadius: '12px',
    border: '1px solid',
    fontSize: '11px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.15s',
  } as React.CSSProperties,

  findingGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  } as React.CSSProperties,

  findingGroupHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '4px 0',
  } as React.CSSProperties,

  severityIndicator: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
  } as React.CSSProperties,

  findingGroupTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#e0e0e0',
  } as React.CSSProperties,

  findingGroupCount: {
    fontSize: '11px',
    color: '#888',
    padding: '1px 8px',
    background: '#1a1a2e',
    borderRadius: '10px',
  } as React.CSSProperties,

  findingCard: {
    background: '#16213e',
    borderRadius: '8px',
    border: '1px solid #0f3460',
    cursor: 'pointer',
    transition: 'border-color 0.2s',
    overflow: 'hidden',
  } as React.CSSProperties,

  findingCardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 14px',
  } as React.CSSProperties,

  findingCardLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flex: 1,
    minWidth: 0,
  } as React.CSSProperties,

  findingCardRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    flexShrink: 0,
  } as React.CSSProperties,

  severityBadge: {
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '10px',
    fontWeight: 700,
    color: '#fff',
    textTransform: 'uppercase',
    whiteSpace: 'nowrap',
  } as React.CSSProperties,

  dimensionBadge: {
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '10px',
    fontWeight: 600,
    color: '#3b82f6',
    background: 'rgba(59, 130, 246, 0.15)',
    whiteSpace: 'nowrap',
  } as React.CSSProperties,

  findingTitle: {
    fontSize: '13px',
    color: '#e0e0e0',
    fontWeight: 500,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  } as React.CSSProperties,

  lineRange: {
    fontSize: '11px',
    color: '#888',
    fontFamily: 'monospace',
  } as React.CSSProperties,

  expandIcon: {
    fontSize: '10px',
    color: '#666',
  } as React.CSSProperties,

  findingCardBody: {
    padding: '0 14px 14px',
    borderTop: '1px solid #0f3460',
    paddingTop: '10px',
  } as React.CSSProperties,

  findingDescription: {
    fontSize: '12px',
    color: '#ccc',
    lineHeight: '1.6',
    marginBottom: '8px',
  } as React.CSSProperties,

  findingSuggestion: {
    fontSize: '12px',
    color: '#22c55e',
    lineHeight: '1.6',
    padding: '8px 10px',
    background: 'rgba(34, 197, 94, 0.08)',
    borderRadius: '6px',
    border: '1px solid rgba(34, 197, 94, 0.15)',
    fontFamily: "'Fira Code', 'Cascadia Code', 'JetBrains Mono', monospace",
  } as React.CSSProperties,

  noFindings: {
    textAlign: 'center',
    padding: '40px',
    color: '#555',
    fontSize: '14px',
  } as React.CSSProperties,

  // ── Summary Tab ──

  summaryTab: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  } as React.CSSProperties,

  summaryCard: {
    padding: '16px',
    background: '#16213e',
    borderRadius: '10px',
    border: '1px solid #0f3460',
  } as React.CSSProperties,

  summaryCardTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#e0e0e0',
    margin: '0 0 12px',
  } as React.CSSProperties,

  summaryText: {
    fontSize: '13px',
    color: '#ccc',
    lineHeight: '1.7',
    margin: 0,
  } as React.CSSProperties,

  distributionRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '8px',
  } as React.CSSProperties,

  distributionLabel: {
    width: '60px',
    fontSize: '11px',
    fontWeight: 600,
    textAlign: 'right',
  } as React.CSSProperties,

  distributionBar: {
    flex: 1,
    height: '10px',
    background: '#1a1a2e',
    borderRadius: '5px',
    overflow: 'hidden',
  } as React.CSSProperties,

  distributionBarFill: {
    height: '100%',
    borderRadius: '5px',
    transition: 'width 0.5s ease',
  } as React.CSSProperties,

  distributionCount: {
    width: '30px',
    fontSize: '12px',
    color: '#888',
    fontWeight: 600,
    textAlign: 'right',
  } as React.CSSProperties,

  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
    gap: '10px',
  } as React.CSSProperties,

  metricItem: {
    padding: '12px',
    background: '#1a1a2e',
    borderRadius: '8px',
    textAlign: 'center',
  } as React.CSSProperties,

  metricValue: {
    fontSize: '20px',
    fontWeight: 700,
    color: '#3b82f6',
    marginBottom: '4px',
  } as React.CSSProperties,

  metricLabel: {
    fontSize: '10px',
    color: '#888',
    textTransform: 'capitalize',
  } as React.CSSProperties,

  scoreProgressBar: {
    height: '12px',
    background: '#1a1a2e',
    borderRadius: '6px',
    overflow: 'hidden',
    marginBottom: '8px',
  } as React.CSSProperties,

  scoreProgressFill: {
    height: '100%',
    borderRadius: '6px',
    transition: 'width 0.5s ease',
  } as React.CSSProperties,

  scoreProgressLabel: {
    fontSize: '12px',
    color: '#888',
    fontWeight: 600,
  } as React.CSSProperties,

  // ── Details Tab ──

  detailsTab: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  } as React.CSSProperties,

  commentaryCard: {
    padding: '20px',
    background: '#16213e',
    borderRadius: '10px',
    border: '1px solid #0f3460',
  } as React.CSSProperties,

  commentaryText: {
    lineHeight: '1.8',
  } as React.CSSProperties,

  commentaryH1: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#e0e0e0',
    margin: '16px 0 8px',
    paddingBottom: '8px',
    borderBottom: '1px solid #0f3460',
  } as React.CSSProperties,

  commentaryH2: {
    fontSize: '15px',
    fontWeight: 600,
    color: '#e0e0e0',
    margin: '14px 0 6px',
  } as React.CSSProperties,

  commentaryH3: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#ccc',
    margin: '10px 0 4px',
  } as React.CSSProperties,

  commentaryParagraph: {
    fontSize: '13px',
    color: '#ccc',
    margin: '6px 0',
  } as React.CSSProperties,

  commentaryListItem: {
    fontSize: '13px',
    color: '#ccc',
    margin: '3px 0',
    paddingLeft: '16px',
  } as React.CSSProperties,

  commentaryBold: {
    fontSize: '13px',
    fontWeight: 700,
    color: '#e0e0e0',
    margin: '8px 0',
  } as React.CSSProperties,

  // ── Diff View ──

  diffSection: {
    borderTop: '1px solid #0f3460',
    flexShrink: 0,
  } as React.CSSProperties,

  diffView: {
    maxHeight: '200px',
    overflowY: 'auto',
    background: '#0d1117',
    fontFamily: "'Fira Code', 'Cascadia Code', 'JetBrains Mono', monospace",
    fontSize: '12px',
    lineHeight: '1.6',
  } as React.CSSProperties,

  diffLine: {
    display: 'flex',
    padding: '0 12px',
    minHeight: '20px',
    alignItems: 'center',
  } as React.CSSProperties,

  diffLineNum: {
    width: '36px',
    minWidth: '36px',
    textAlign: 'right',
    paddingRight: '10px',
    color: '#484f58',
    fontSize: '11px',
    userSelect: 'none',
  } as React.CSSProperties,

  diffLinePrefix: {
    width: '14px',
    minWidth: '14px',
    fontWeight: 700,
    fontSize: '11px',
  } as React.CSSProperties,

  // ── Stats Bar ──

  statsBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '10px 20px',
    background: '#16213e',
    borderTop: '1px solid #0f3460',
    gap: '0',
    flexShrink: 0,
  } as React.CSSProperties,

  statItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '0 24px',
  } as React.CSSProperties,

  statValue: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#e0e0e0',
  } as React.CSSProperties,

  statLabel: {
    fontSize: '10px',
    color: '#888',
    fontWeight: 500,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginTop: '2px',
  } as React.CSSProperties,

  statDivider: {
    width: '1px',
    height: '32px',
    background: '#0f3460',
  } as React.CSSProperties,
} as const;

export default CodeReviewPanel;