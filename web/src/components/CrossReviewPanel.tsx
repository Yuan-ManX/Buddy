import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#e11d48',
  secondary: '#fda4af',
  bg: '#fff1f2',
  border: '#fecdd3',
  accent: '#ffe4e6',
  text: '#881337',
};

const REVIEW_STRATEGIES = ['thorough', 'quick', 'adversarial', 'constructive', 'security_focused'];
const VERDICTS = ['approved', 'rejected', 'needs_revision', 'passed', 'failed'];

export const CrossReviewPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'reviewer' | 'review' | 'report'>('overview');

  // Reviewer form
  const [reviewerForm, setReviewerForm] = useState({
    name: '', specialties: '',
  });

  // Review form
  const [reviewForm, setReviewForm] = useState({
    reviewer_id: '', reviewee_id: '', artifact_type: '', artifact_content: '', strategy: 'thorough',
  });

  // Report form
  const [reportForm, setReportForm] = useState({
    review_id: '', verdict: 'approved', summary: '', score: '', confidence: '',
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.crossReview.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cross review data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleRegisterReviewer = async () => {
    if (!reviewerForm.name.trim()) return;
    try {
      await api.crossReview.registerReviewer({
        name: reviewerForm.name.trim(),
        specialties: reviewerForm.specialties.split(',').map(s => s.trim()).filter(Boolean),
      });
      toast.success(`Reviewer "${reviewerForm.name}" registered`);
      setReviewerForm({ name: '', specialties: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreateReview = async () => {
    if (!reviewForm.reviewer_id.trim() || !reviewForm.reviewee_id.trim() || !reviewForm.artifact_type.trim() || !reviewForm.artifact_content.trim()) return;
    try {
      await api.crossReview.createReview({
        reviewer_id: reviewForm.reviewer_id.trim(),
        reviewee_id: reviewForm.reviewee_id.trim(),
        artifact_type: reviewForm.artifact_type.trim(),
        artifact_content: reviewForm.artifact_content.trim(),
        strategy: reviewForm.strategy,
      });
      toast.success('Review created');
      setReviewForm({ reviewer_id: '', reviewee_id: '', artifact_type: '', artifact_content: '', strategy: 'thorough' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSubmitReport = async () => {
    if (!reportForm.review_id.trim() || !reportForm.summary.trim()) return;
    try {
      await api.crossReview.submitReport({
        review_id: reportForm.review_id.trim(),
        verdict: reportForm.verdict,
        summary: reportForm.summary.trim(),
        score: reportForm.score ? Number(reportForm.score) : undefined,
        confidence: reportForm.confidence ? Number(reportForm.confidence) : undefined,
      });
      toast.success('Review report submitted');
      setReportForm({ review_id: '', verdict: 'approved', summary: '', score: '', confidence: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🔍 Cross Review</h2>
          <p className="panel-subtitle">Peer review, critique, and quality assessment between agents</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cross review...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🔍 Cross Review</h2>
        <p className="panel-subtitle">Peer review, critique, and quality assessment between agents</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_reviewers ?? '-'}</span><span className="stat-label">Reviewers</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_reviews ?? '-'}</span><span className="stat-label">Reviews</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_reports ?? '-'}</span><span className="stat-label">Reports</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.pending_reviews ?? '-'}</span><span className="stat-label">Pending</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'reviewer', 'review', 'report'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
            style={activeSection === s ? { background: themeColors.primary, borderColor: themeColors.primary } : {}}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Cross Review Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Reviewers</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_reviewers ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Reviews</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_reviews ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Reports Submitted</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_reports ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Pending Reviews</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.pending_reviews ?? 0}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reviewer */}
      {activeSection === 'reviewer' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Register Reviewer</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Name *</label>
              <input
                type="text"
                value={reviewerForm.name}
                onChange={e => setReviewerForm(f => ({ ...f, name: e.target.value }))}
                placeholder="Reviewer name..."
              />
            </div>
            <div className="form-group">
              <label>Specialties (comma-separated)</label>
              <input
                type="text"
                value={reviewerForm.specialties}
                onChange={e => setReviewerForm(f => ({ ...f, specialties: e.target.value }))}
                placeholder="code, security, documentation"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleRegisterReviewer}
              disabled={!reviewerForm.name.trim()}
            >
              Register Reviewer
            </button>
          </div>
        </div>
      )}

      {/* Review */}
      {activeSection === 'review' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create Review</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Reviewer ID *</label>
                <input
                  type="text"
                  value={reviewForm.reviewer_id}
                  onChange={e => setReviewForm(f => ({ ...f, reviewer_id: e.target.value }))}
                  placeholder="Reviewer ID"
                />
              </div>
              <div className="form-group">
                <label>Reviewee ID *</label>
                <input
                  type="text"
                  value={reviewForm.reviewee_id}
                  onChange={e => setReviewForm(f => ({ ...f, reviewee_id: e.target.value }))}
                  placeholder="Reviewee ID"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Artifact Type *</label>
                <input
                  type="text"
                  value={reviewForm.artifact_type}
                  onChange={e => setReviewForm(f => ({ ...f, artifact_type: e.target.value }))}
                  placeholder="e.g. code, document, plan"
                />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={reviewForm.strategy} onChange={e => setReviewForm(f => ({ ...f, strategy: e.target.value }))}>
                  {REVIEW_STRATEGIES.map(s => (
                    <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Artifact Content *</label>
              <textarea
                rows={5}
                value={reviewForm.artifact_content}
                onChange={e => setReviewForm(f => ({ ...f, artifact_content: e.target.value }))}
                placeholder="Content to be reviewed..."
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleCreateReview}
              disabled={!reviewForm.reviewer_id.trim() || !reviewForm.reviewee_id.trim() || !reviewForm.artifact_type.trim() || !reviewForm.artifact_content.trim()}
            >
              Create Review
            </button>
          </div>
        </div>
      )}

      {/* Report */}
      {activeSection === 'report' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Submit Report</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Review ID *</label>
                <input
                  type="text"
                  value={reportForm.review_id}
                  onChange={e => setReportForm(f => ({ ...f, review_id: e.target.value }))}
                  placeholder="Review ID"
                />
              </div>
              <div className="form-group">
                <label>Verdict</label>
                <select value={reportForm.verdict} onChange={e => setReportForm(f => ({ ...f, verdict: e.target.value }))}>
                  {VERDICTS.map(v => (
                    <option key={v} value={v}>{v.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Summary *</label>
              <textarea
                rows={4}
                value={reportForm.summary}
                onChange={e => setReportForm(f => ({ ...f, summary: e.target.value }))}
                placeholder="Review summary and findings..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Score (0-100)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={reportForm.score}
                  onChange={e => setReportForm(f => ({ ...f, score: e.target.value }))}
                  placeholder="Quality score"
                />
              </div>
              <div className="form-group">
                <label>Confidence (0-1)</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={reportForm.confidence}
                  onChange={e => setReportForm(f => ({ ...f, confidence: e.target.value }))}
                  placeholder="0.0 - 1.0"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleSubmitReport}
              disabled={!reportForm.review_id.trim() || !reportForm.summary.trim()}
            >
              Submit Report
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CrossReviewPanel;
