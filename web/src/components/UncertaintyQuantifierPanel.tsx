import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface UncertaintyStats {
  total_assessments: number;
  avg_confidence: number;
  high_uncertainty_rate: number;
  calibration_effectiveness: number;
}

interface UncertaintySource {
  type: string;
  description: string;
  severity: 'low' | 'medium' | 'high';
}

interface SegmentConfidence {
  segment: string;
  confidence: number;
}

interface AssessmentResult {
  assessment_id: string;
  overall_confidence: number;
  uncertainty_sources: UncertaintySource[];
  segments: SegmentConfidence[];
  factuality_score: number;
  precision_score: number;
  hedging_phrases: string[];
  suggested_caveats: string[];
}

interface Alternative {
  id: string;
  text: string;
  confidence: number;
  probability: number;
  rationale: string;
}

interface AlternativesResult {
  assessment_id: string;
  alternatives: Alternative[];
}

interface RiskFactor {
  factor: string;
  severity: 'low' | 'medium' | 'high';
  description: string;
}

interface RiskProfile {
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  risk_factors: RiskFactor[];
  mitigation_suggestions: string[];
  content_warnings: string[];
  ethical_concerns: string[];
  bias_indicators: string[];
}

// ── Request helper ──

const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try {
      const parsed = JSON.parse(body);
      message = parsed.detail || parsed.error || body;
    } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Component ──

export const UncertaintyQuantifierPanel: React.FC = () => {
  const toast = useToast();

  const [stats, setStats] = useState<UncertaintyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'assess' | 'alternatives' | 'risk'>('overview');

  // Assess form
  const [assessForm, setAssessForm] = useState({ text: '', context: '' });
  const [assessing, setAssessing] = useState(false);
  const [assessmentResult, setAssessmentResult] = useState<AssessmentResult | null>(null);

  // Alternatives form
  const [alternativesId, setAlternativesId] = useState('');
  const [loadingAlternatives, setLoadingAlternatives] = useState(false);
  const [alternativesResult, setAlternativesResult] = useState<AlternativesResult | null>(null);

  // Risk form
  const [riskQuery, setRiskQuery] = useState('');
  const [loadingRisk, setLoadingRisk] = useState(false);
  const [riskProfile, setRiskProfile] = useState<RiskProfile | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await request<UncertaintyStats>('/uncertainty-quantifier/stats').catch(() => null);
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load uncertainty quantifier data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleAssess = async () => {
    if (!assessForm.text.trim()) return;
    try {
      setAssessing(true);
      const result = await request<AssessmentResult>('/uncertainty-quantifier/assess', {
        method: 'POST',
        body: JSON.stringify({
          text: assessForm.text,
          context: assessForm.context || undefined,
        }),
      });
      setAssessmentResult(result);
      toast.success('Assessment completed successfully');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setAssessing(false);
    }
  };

  const handleLoadAlternatives = async () => {
    if (!alternativesId.trim()) return;
    try {
      setLoadingAlternatives(true);
      const result = await request<AlternativesResult>(`/uncertainty-quantifier/alternatives/${alternativesId}`);
      setAlternativesResult(result);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoadingAlternatives(false);
    }
  };

  const handleRiskProfile = async () => {
    if (!riskQuery.trim()) return;
    try {
      setLoadingRisk(true);
      const result = await request<RiskProfile>('/uncertainty-quantifier/risk-profile', {
        method: 'POST',
        body: JSON.stringify({ query: riskQuery }),
      });
      setRiskProfile(result);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoadingRisk(false);
    }
  };

  const severityColors: Record<string, string> = {
    low: '#22c55e',
    medium: '#f59e0b',
    high: '#ef4444',
    critical: '#7f1d1d',
  };

  const confidenceColor = (val: number): string => {
    if (val >= 0.8) return '#22c55e';
    if (val >= 0.5) return '#f59e0b';
    return '#ef4444';
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Uncertainty Quantifier</h2>
          <p className="panel-subtitle">Quantify and manage uncertainty in AI-generated content</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading uncertainty quantifier data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Uncertainty Quantifier</h2>
        <p className="panel-subtitle">Assess, quantify, and mitigate uncertainty in AI-generated outputs</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_assessments}</span>
              <span className="stat-label">Total Assessments</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: confidenceColor(stats.avg_confidence) }}>
                {(stats.avg_confidence * 100).toFixed(1)}%
              </span>
              <span className="stat-label">Avg Confidence</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: stats.high_uncertainty_rate <= 0.3 ? '#22c55e' : '#f59e0b' }}>
                {(stats.high_uncertainty_rate * 100).toFixed(1)}%
              </span>
              <span className="stat-label">High Uncertainty Rate</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#8b5cf6' }}>
                {(stats.calibration_effectiveness * 100).toFixed(1)}%
              </span>
              <span className="stat-label">Calibration Effectiveness</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'assess', 'alternatives', 'risk'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Overview Section ── */}
      {activeSection === 'overview' && (
        <div className="dashboard-section">
          {stats && (
            <>
              <h3>Quantifier Overview</h3>
              <div className="dashboard-stat-row">
                <span>Total Assessments</span>
                <strong>{stats.total_assessments}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Average Confidence</span>
                <strong style={{ color: confidenceColor(stats.avg_confidence) }}>
                  {(stats.avg_confidence * 100).toFixed(1)}%
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>High Uncertainty Rate</span>
                <strong style={{ color: stats.high_uncertainty_rate <= 0.3 ? '#22c55e' : '#f59e0b' }}>
                  {(stats.high_uncertainty_rate * 100).toFixed(1)}%
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Calibration Effectiveness</span>
                <strong style={{ color: '#8b5cf6' }}>
                  {(stats.calibration_effectiveness * 100).toFixed(1)}%
                </strong>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Assess Section ── */}
      {activeSection === 'assess' && (
        <div className="dashboard-section">
          <h3>Assess Uncertainty</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Text to Assess</label>
              <textarea
                rows={8}
                value={assessForm.text}
                onChange={e => setAssessForm(f => ({ ...f, text: e.target.value }))}
                placeholder="Enter the content you want to assess for uncertainty..."
              />
            </div>
            <div className="form-group">
              <label>Context (Optional)</label>
              <textarea
                rows={3}
                value={assessForm.context}
                onChange={e => setAssessForm(f => ({ ...f, context: e.target.value }))}
                placeholder="Provide additional context for the assessment..."
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleAssess}
              disabled={assessing || !assessForm.text.trim()}
            >
              {assessing ? 'Assessing...' : 'Assess Uncertainty'}
            </button>
          </div>

          {assessmentResult && (
            <div className="dashboard-section" style={{ marginTop: 16 }}>
              <h3>Assessment Result</h3>

              {/* Overall Confidence Progress Bar */}
              <div className="dashboard-stat-row">
                <span>Overall Confidence</span>
                <strong style={{ color: confidenceColor(assessmentResult.overall_confidence) }}>
                  {(assessmentResult.overall_confidence * 100).toFixed(1)}%
                </strong>
              </div>
              <div style={{
                background: 'var(--border-color, #333)',
                borderRadius: 8,
                height: 12,
                marginBottom: 16,
                overflow: 'hidden',
              }}>
                <div style={{
                  width: `${assessmentResult.overall_confidence * 100}%`,
                  height: '100%',
                  background: confidenceColor(assessmentResult.overall_confidence),
                  borderRadius: 8,
                  transition: 'width 0.3s ease',
                }} />
              </div>

              {/* Factuality & Precision Scores */}
              <div className="dashboard-stat-row">
                <span>Factuality Score</span>
                <strong style={{ color: confidenceColor(assessmentResult.factuality_score) }}>
                  {(assessmentResult.factuality_score * 100).toFixed(1)}%
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Precision Score</span>
                <strong style={{ color: confidenceColor(assessmentResult.precision_score) }}>
                  {(assessmentResult.precision_score * 100).toFixed(1)}%
                </strong>
              </div>

              {/* Uncertainty Sources */}
              {assessmentResult.uncertainty_sources.length > 0 && (
                <>
                  <h4 style={{ marginTop: 16 }}>Uncertainty Sources</h4>
                  <div className="forge-skill-list">
                    {assessmentResult.uncertainty_sources.map((source, i) => (
                      <div key={i} className="forge-skill-card">
                        <div className="forge-skill-header">
                          <div className="forge-skill-name">{source.type}</div>
                          <span className="dashboard-badge" style={{
                            background: severityColors[source.severity] || '#9ca3af',
                            color: '#fff',
                          }}>
                            {source.severity}
                          </span>
                        </div>
                        <div className="forge-skill-meta">
                          <div>{source.description}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* Segment Confidence */}
              {assessmentResult.segments.length > 0 && (
                <>
                  <h4 style={{ marginTop: 16 }}>Per-Segment Confidence</h4>
                  <div className="forge-skill-list">
                    {assessmentResult.segments.map((seg, i) => (
                      <div key={i} className="forge-skill-card">
                        <div className="forge-skill-header">
                          <div className="forge-skill-name" style={{ fontSize: 13, flex: 1 }}>
                            {seg.segment}
                          </div>
                          <span className="dashboard-badge" style={{
                            background: confidenceColor(seg.confidence),
                            color: '#fff',
                          }}>
                            {(seg.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* Hedging Phrases */}
              {assessmentResult.hedging_phrases.length > 0 && (
                <>
                  <h4 style={{ marginTop: 16 }}>Hedging Phrases Detected</h4>
                  <div className="forge-skill-list">
                    {assessmentResult.hedging_phrases.map((phrase, i) => (
                      <div key={i} className="forge-skill-card">
                        <div className="forge-skill-meta">
                          <div>{phrase}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* Suggested Caveats */}
              {assessmentResult.suggested_caveats.length > 0 && (
                <>
                  <h4 style={{ marginTop: 16 }}>Suggested Caveats</h4>
                  <div className="forge-skill-list">
                    {assessmentResult.suggested_caveats.map((caveat, i) => (
                      <div key={i} className="forge-skill-card">
                        <div className="forge-skill-meta">
                          <div>{caveat}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Alternatives Section ── */}
      {activeSection === 'alternatives' && (
        <div className="dashboard-section">
          <h3>View Alternatives</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Assessment ID</label>
              <input
                type="text"
                value={alternativesId}
                onChange={e => setAlternativesId(e.target.value)}
                placeholder="Enter assessment ID..."
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleLoadAlternatives}
              disabled={loadingAlternatives || !alternativesId.trim()}
            >
              {loadingAlternatives ? 'Loading...' : 'Load Alternatives'}
            </button>
          </div>

          {alternativesResult && (
            <div className="dashboard-section" style={{ marginTop: 16 }}>
              <h3>Alternatives for Assessment {alternativesResult.assessment_id}</h3>
              {alternativesResult.alternatives.length === 0 ? (
                <div className="panel-empty">No alternatives found</div>
              ) : (
                <div className="forge-skill-list">
                  {alternativesResult.alternatives.map(alt => (
                    <div key={alt.id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name" style={{ fontSize: 13, flex: 1 }}>
                          {alt.text}
                        </div>
                      </div>
                      <div className="forge-skill-meta">
                        <div style={{ display: 'flex', gap: 16, marginBottom: 4 }}>
                          <span>Confidence: <strong style={{ color: confidenceColor(alt.confidence) }}>
                            {(alt.confidence * 100).toFixed(1)}%
                          </strong></span>
                          <span>Probability: <strong style={{ color: '#3b82f6' }}>
                            {(alt.probability * 100).toFixed(1)}%
                          </strong></span>
                        </div>
                        <div>{alt.rationale}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Risk Section ── */}
      {activeSection === 'risk' && (
        <div className="dashboard-section">
          <h3>Risk Profile</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Content Query</label>
              <textarea
                rows={4}
                value={riskQuery}
                onChange={e => setRiskQuery(e.target.value)}
                placeholder="Enter the content or query to analyze for risk..."
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleRiskProfile}
              disabled={loadingRisk || !riskQuery.trim()}
            >
              {loadingRisk ? 'Analyzing...' : 'Analyze Risk'}
            </button>
          </div>

          {riskProfile && (
            <div className="dashboard-section" style={{ marginTop: 16 }}>
              <h3>Risk Analysis Result</h3>

              <div className="dashboard-stat-row">
                <span>Risk Level</span>
                <strong style={{ color: severityColors[riskProfile.risk_level] || '#9ca3af' }}>
                  {riskProfile.risk_level.toUpperCase()}
                </strong>
              </div>

              {/* Risk Factors */}
              {riskProfile.risk_factors.length > 0 && (
                <>
                  <h4 style={{ marginTop: 16 }}>Risk Factors</h4>
                  <div className="forge-skill-list">
                    {riskProfile.risk_factors.map((rf, i) => (
                      <div key={i} className="forge-skill-card">
                        <div className="forge-skill-header">
                          <div className="forge-skill-name">{rf.factor}</div>
                          <span className="dashboard-badge" style={{
                            background: severityColors[rf.severity] || '#9ca3af',
                            color: '#fff',
                          }}>
                            {rf.severity}
                          </span>
                        </div>
                        <div className="forge-skill-meta">
                          <div>{rf.description}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* Mitigation Suggestions */}
              {riskProfile.mitigation_suggestions.length > 0 && (
                <>
                  <h4 style={{ marginTop: 16 }}>Mitigation Suggestions</h4>
                  <div className="forge-skill-list">
                    {riskProfile.mitigation_suggestions.map((s, i) => (
                      <div key={i} className="forge-skill-card">
                        <div className="forge-skill-meta">
                          <div>{s}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* Content Warnings */}
              {riskProfile.content_warnings.length > 0 && (
                <>
                  <h4 style={{ marginTop: 16 }}>Content Warnings</h4>
                  <div className="forge-skill-list">
                    {riskProfile.content_warnings.map((w, i) => (
                      <div key={i} className="forge-skill-card">
                        <div className="forge-skill-meta">
                          <div style={{ color: '#f59e0b' }}>{w}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* Ethical Concerns */}
              {riskProfile.ethical_concerns.length > 0 && (
                <>
                  <h4 style={{ marginTop: 16 }}>Ethical Concerns</h4>
                  <div className="forge-skill-list">
                    {riskProfile.ethical_concerns.map((c, i) => (
                      <div key={i} className="forge-skill-card">
                        <div className="forge-skill-meta">
                          <div style={{ color: '#ef4444' }}>{c}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* Bias Indicators */}
              {riskProfile.bias_indicators.length > 0 && (
                <>
                  <h4 style={{ marginTop: 16 }}>Bias Indicators</h4>
                  <div className="forge-skill-list">
                    {riskProfile.bias_indicators.map((b, i) => (
                      <div key={i} className="forge-skill-card">
                        <div className="forge-skill-meta">
                          <div style={{ color: '#ef4444' }}>{b}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default UncertaintyQuantifierPanel;