import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { MarketplaceSkillInfo, MarketplaceStats, SkillReview } from '../types';

export const MarketplacePanel: React.FC = () => {
  const [skills, setSkills] = useState<MarketplaceSkillInfo[]>([]);
  const [stats, setStats] = useState<MarketplaceStats | null>(null);
  const [featured, setFeatured] = useState<MarketplaceSkillInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [sortBy, setSortBy] = useState('rating');
  const [selectedSkill, setSelectedSkill] = useState<MarketplaceSkillInfo | null>(null);
  const [reviews, setReviews] = useState<SkillReview[]>([]);
  const [showPublish, setShowPublish] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [reviewForm, setReviewForm] = useState({ reviewer_name: 'Anonymous', rating: 5, title: '', content: '' });
  const [publishForm, setPublishForm] = useState({
    name: '', description: '', category: 'utility', version: '1.0.0', author: '', tags: '', prompt_template: '',
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [sRes, st, f] = await Promise.all([
        api.marketplace.search(searchQuery, categoryFilter, undefined, undefined, sortBy),
        api.marketplace.stats(),
        api.marketplace.featured(),
      ]);
      setSkills(sRes.skills);
      setStats(st);
      setFeatured(f.skills);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load marketplace');
    } finally {
      setLoading(false);
    }
  }, [searchQuery, categoryFilter, sortBy]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleSelectSkill = async (skill: MarketplaceSkillInfo) => {
    setSelectedSkill(skill);
    try {
      const r = await api.marketplace.reviews(skill.id);
      setReviews(r.reviews);
    } catch {
      setReviews([]);
    }
  };

  const handleDownload = async (skillId: string) => {
    try {
      await api.marketplace.download(skillId);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record download');
    }
  };

  const handlePublish = async () => {
    if (!publishForm.name) return;
    try {
      await api.marketplace.publish({
        name: publishForm.name,
        description: publishForm.description,
        category: publishForm.category,
        version: publishForm.version,
        author: publishForm.author,
        tags: publishForm.tags ? publishForm.tags.split(',').map(s => s.trim()) : [],
        prompt_template: publishForm.prompt_template,
      });
      setShowPublish(false);
      setPublishForm({ name: '', description: '', category: 'utility', version: '1.0.0', author: '', tags: '', prompt_template: '' });
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to publish skill');
    }
  };

  const handleReview = async () => {
    if (!selectedSkill || !reviewForm.content) return;
    try {
      await api.marketplace.review(selectedSkill.id, {
        reviewer_name: reviewForm.reviewer_name,
        rating: reviewForm.rating,
        title: reviewForm.title,
        content: reviewForm.content,
      });
      setShowReview(false);
      setReviewForm({ reviewer_name: 'Anonymous', rating: 5, title: '', content: '' });
      handleSelectSkill(selectedSkill);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit review');
    }
  };

  if (loading) return <div className="panel-loading">Loading marketplace...</div>;

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Skills Marketplace</h2>
        <div className="panel-header-actions">
          <button className="btn-primary" onClick={() => setShowPublish(true)}>Publish Skill</button>
          <button className="btn-secondary" onClick={loadData}>Refresh</button>
        </div>
      </div>

      {error && <div className="panel-error">{error}</div>}

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.total_skills}</div>
            <div className="stat-label">Total Skills</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.total_publishers}</div>
            <div className="stat-label">Publishers</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.avg_rating.toFixed(1)}</div>
            <div className="stat-label">Avg Rating</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.total_downloads}</div>
            <div className="stat-label">Downloads</div>
          </div>
        </div>
      )}

      {featured.length > 0 && (
        <div className="panel-section">
          <h3>Featured Skills</h3>
          <div className="card-grid">
            {featured.map((skill) => (
              <div key={skill.id} className="card card-clickable" onClick={() => handleSelectSkill(skill)}>
                <div className="card-header">
                  <span className="item-name">{skill.name}</span>
                  <span className={`badge ${skill.verified ? 'badge-green' : 'badge-blue'}`}>
                    {skill.verified ? 'Verified' : skill.version}
                  </span>
                </div>
                <div className="card-body">{skill.description}</div>
                <div className="card-footer">
                  <span>by {skill.author}</span>
                  <span>{(skill.rating || 0).toFixed(1)} ({skill.review_count})</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="panel-section">
        <h3>Browse Skills</h3>
        <div className="form-row">
          <input
            type="text"
            placeholder="Search skills..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
          <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="form-select">
            <option value="">All Categories</option>
            <option value="productivity">Productivity</option>
            <option value="development">Development</option>
            <option value="design">Design</option>
            <option value="research">Research</option>
            <option value="writing">Writing</option>
            <option value="utility">Utility</option>
          </select>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="form-select">
            <option value="rating">Top Rated</option>
            <option value="downloads">Most Downloads</option>
            <option value="newest">Newest</option>
          </select>
        </div>
      </div>

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Skill</th>
              <th>Author</th>
              <th>Rating</th>
              <th>Downloads</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {skills.map((skill) => (
              <tr key={skill.id} className={selectedSkill?.id === skill.id ? 'row-selected' : ''}>
                <td>
                  <div className="item-name clickable" onClick={() => handleSelectSkill(skill)}>{skill.name}</div>
                  <div className="item-desc">{skill.description.slice(0, 80)}</div>
                  {skill.tags.slice(0, 3).map(t => <span key={t} className="badge badge-sm">{t}</span>)}
                </td>
                <td>{skill.author}</td>
                <td>{(skill.rating || 0).toFixed(1)} ({skill.review_count})</td>
                <td>{skill.download_count}</td>
                <td>
                  <button className="btn-sm btn-blue" onClick={() => handleDownload(skill.id)}>Download</button>
                </td>
              </tr>
            ))}
            {skills.length === 0 && (
              <tr><td colSpan={5} className="empty-cell">No skills found.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showPublish && (
        <div className="modal-overlay" onClick={() => setShowPublish(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Publish Skill</h2>
            <div className="form-group">
              <label>Name (required)</label>
              <input type="text" value={publishForm.name} onChange={e => setPublishForm({...publishForm, name: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea rows={3} value={publishForm.description} onChange={e => setPublishForm({...publishForm, description: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Category</label>
              <select value={publishForm.category} onChange={e => setPublishForm({...publishForm, category: e.target.value})}>
                <option value="utility">Utility</option>
                <option value="productivity">Productivity</option>
                <option value="development">Development</option>
                <option value="design">Design</option>
                <option value="research">Research</option>
                <option value="writing">Writing</option>
              </select>
            </div>
            <div className="form-group">
              <label>Prompt Template</label>
              <textarea rows={4} value={publishForm.prompt_template} onChange={e => setPublishForm({...publishForm, prompt_template: e.target.value})} placeholder="Skill prompt template..." />
            </div>
            <div className="form-group">
              <label>Tags (comma separated)</label>
              <input type="text" value={publishForm.tags} onChange={e => setPublishForm({...publishForm, tags: e.target.value})} />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowPublish(false)}>Cancel</button>
              <button className="btn-primary" onClick={handlePublish}>Publish</button>
            </div>
          </div>
        </div>
      )}

      {selectedSkill && (
        <div className="panel-section panel-section-highlight">
          <h3>Skill Details: {selectedSkill.name}</h3>
          <p>{selectedSkill.description}</p>
          <div className="detail-meta">
            <span>Version: {selectedSkill.version}</span>
            <span>Author: {selectedSkill.author}</span>
            <span>Rating: {(selectedSkill.rating || 0).toFixed(1)}</span>
            <span>Downloads: {selectedSkill.download_count}</span>
          </div>
          <button className="btn-primary" onClick={() => setShowReview(true)}>Write Review</button>
          <button className="btn-secondary" onClick={() => setSelectedSkill(null)}>Close</button>

          {reviews.length > 0 && (
            <div className="reviews-section">
              <h4>Reviews ({reviews.length})</h4>
              {reviews.map((r) => (
                <div key={r.id} className="review-card">
                  <div className="review-header">
                    <span>{r.reviewer_name}</span>
                    <span>{'★'.repeat(Math.round(r.rating))}{'☆'.repeat(5 - Math.round(r.rating))}</span>
                  </div>
                  {r.title && <div className="review-title">{r.title}</div>}
                  <div className="review-content">{r.content}</div>
                </div>
              ))}
            </div>
          )}

          {showReview && (
            <div className="modal-overlay" onClick={() => setShowReview(false)}>
              <div className="modal" onClick={(e) => e.stopPropagation()}>
                <h3>Write Review</h3>
                <div className="form-group">
                  <label>Name</label>
                  <input type="text" value={reviewForm.reviewer_name} onChange={e => setReviewForm({...reviewForm, reviewer_name: e.target.value})} />
                </div>
                <div className="form-group">
                  <label>Rating: {reviewForm.rating}</label>
                  <input type="range" min="1" max="5" value={reviewForm.rating} onChange={e => setReviewForm({...reviewForm, rating: Number(e.target.value)})} />
                </div>
                <div className="form-group">
                  <label>Title</label>
                  <input type="text" value={reviewForm.title} onChange={e => setReviewForm({...reviewForm, title: e.target.value})} />
                </div>
                <div className="form-group">
                  <label>Content</label>
                  <textarea rows={3} value={reviewForm.content} onChange={e => setReviewForm({...reviewForm, content: e.target.value})} />
                </div>
                <div className="modal-actions">
                  <button className="btn-secondary" onClick={() => setShowReview(false)}>Cancel</button>
                  <button className="btn-primary" onClick={handleReview}>Submit</button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};