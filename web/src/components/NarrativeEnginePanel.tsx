import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: pink for narrative engine
const themeColors = {
  primary: '#db2777',
  secondary: '#ec4899',
  bg: '#fdf2f8',
  border: '#fbcfe8',
  accent: '#fce7f3',
  text: '#831843',
};

// Enum values must match backend NarrativeType / NarrativeStatus / PlotArc / NarrativeTense / PerspectiveType exactly (lowercase).
const NARRATIVE_TYPES = ['personal', 'procedural', 'explanatory', 'persuasive', 'descriptive', 'reflective'];
const NARRATIVE_STATUS = ['draft', 'structured', 'refined', 'published', 'archived'];
const PLOT_ARCS = ['setup', 'rising_action', 'climax', 'falling_action', 'resolution'];
const NARRATIVE_TENSES = ['past', 'present', 'future', 'conditional'];
const PERSPECTIVE_TYPES = ['first_person', 'second_person', 'third_person', 'omniscient'];

// Significance drives badge color for events (not a backend enum).
const SIGNIFICANCE_LEVELS = ['low', 'medium', 'high', 'pivotal'];

const STATUS_COLORS: Record<string, string> = {
  draft: '#9ca3af',
  structured: '#2563eb',
  refined: '#7c3aed',
  published: '#059669',
  archived: '#6b7280',
};

const SIGNIFICANCE_COLORS: Record<string, string> = {
  low: '#9ca3af',
  medium: '#d97706',
  high: '#ea580c',
  pivotal: '#dc2626',
};

export const NarrativeEnginePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'narrative' | 'event'>('overview');

  // Narratives / events / characters / themes
  const [narratives, setNarratives] = useState<any[]>([]);
  const [selectedNarrativeId, setSelectedNarrativeId] = useState<string>('');
  const [events, setEvents] = useState<any[]>([]);
  const [characters, setCharacters] = useState<any[]>([]);
  const [themes, setThemes] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);

  // Narrative form
  const [narrativeForm, setNarrativeForm] = useState({
    title: '',
    narrative_type: 'personal',
    tense: 'past',
    perspective: 'first_person',
    description: '',
  });

  // Event form
  const [eventForm, setEventForm] = useState({
    title: '',
    plot_arc: 'setup',
    significance: 'medium',
    sequence: '',
    description: '',
  });

  // Character form
  const [characterForm, setCharacterForm] = useState({
    name: '',
    role: '',
    description: '',
  });

  // Theme form
  const [themeForm, setThemeForm] = useState({
    name: '',
    description: '',
    weight: '1.0',
  });

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.narrativeEngine.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load narrative engine stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadNarratives = useCallback(async () => {
    try {
      const result = await api.narrativeEngine.listNarratives();
      const list = Array.isArray(result) ? result : (result?.narratives ?? []);
      setNarratives(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load narratives');
    }
  }, [toast]);

  const loadNarrativeDetail = useCallback(async (narrativeId: string) => {
    if (!narrativeId) return;
    try {
      const [ev, ch, th] = await Promise.all([
        api.narrativeEngine.listEvents(narrativeId).catch(() => []),
        api.narrativeEngine.listCharacters(narrativeId).catch(() => []),
        api.narrativeEngine.listThemes(narrativeId).catch(() => []),
      ]);
      setEvents(Array.isArray(ev) ? ev : (ev?.events ?? []));
      setCharacters(Array.isArray(ch) ? ch : (ch?.characters ?? []));
      setThemes(Array.isArray(th) ? th : (th?.themes ?? []));
    } catch {
      setEvents([]);
      setCharacters([]);
      setThemes([]);
    }
  }, []);

  // Initial load
  useEffect(() => { loadStats(); }, [loadStats]);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadNarratives();
    }
  }, [activeSection, loadStats, loadNarratives]);

  // When the active narrative changes, refresh its events, characters, and themes
  useEffect(() => {
    if (selectedNarrativeId) {
      loadNarrativeDetail(selectedNarrativeId);
      setSummary(null);
    }
  }, [selectedNarrativeId, loadNarrativeDetail]);

  // Auto-select first narrative when entering the event section
  useEffect(() => {
    if (activeSection === 'event' && !selectedNarrativeId && narratives.length > 0) {
      setSelectedNarrativeId(narratives[0].narrative_id ?? narratives[0].id);
    }
  }, [activeSection, selectedNarrativeId, narratives]);

  const handleCreateNarrative = async () => {
    if (!narrativeForm.title.trim()) {
      toast.error('Title is required');
      return;
    }
    try {
      const payload: any = {
        title: narrativeForm.title.trim(),
        narrative_type: narrativeForm.narrative_type,
        tense: narrativeForm.tense,
        perspective: narrativeForm.perspective,
      };
      if (narrativeForm.description.trim()) payload.description = narrativeForm.description.trim();
      const result = await api.narrativeEngine.createNarrative(payload);
      toast.success('Narrative created');
      setNarrativeForm({ title: '', narrative_type: 'personal', tense: 'past', perspective: 'first_person', description: '' });
      await loadNarratives();
      const newId = result?.narrative_id ?? result?.id;
      if (newId) setSelectedNarrativeId(newId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDeleteNarrative = async (narrativeId: string) => {
    try {
      await api.narrativeEngine.deleteNarrative(narrativeId);
      toast.success('Narrative deleted');
      await loadNarratives();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddEvent = async () => {
    if (!selectedNarrativeId || !eventForm.title.trim()) {
      toast.error('Narrative and event title are required');
      return;
    }
    try {
      const payload: any = {
        title: eventForm.title.trim(),
        plot_arc: eventForm.plot_arc,
        significance: eventForm.significance,
      };
      if (eventForm.description.trim()) payload.description = eventForm.description.trim();
      if (eventForm.sequence.trim() !== '') payload.sequence = Number(eventForm.sequence);
      await api.narrativeEngine.addEvent(selectedNarrativeId, payload);
      toast.success('Event added');
      setEventForm({ title: '', plot_arc: 'setup', significance: 'medium', sequence: '', description: '' });
      loadNarrativeDetail(selectedNarrativeId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddCharacter = async () => {
    if (!selectedNarrativeId || !characterForm.name.trim()) {
      toast.error('Narrative and character name are required');
      return;
    }
    try {
      const payload: any = { name: characterForm.name.trim() };
      if (characterForm.role.trim()) payload.role = characterForm.role.trim();
      if (characterForm.description.trim()) payload.description = characterForm.description.trim();
      await api.narrativeEngine.addCharacter(selectedNarrativeId, payload);
      toast.success('Character added');
      setCharacterForm({ name: '', role: '', description: '' });
      loadNarrativeDetail(selectedNarrativeId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddTheme = async () => {
    if (!selectedNarrativeId || !themeForm.name.trim()) {
      toast.error('Narrative and theme name are required');
      return;
    }
    try {
      const payload: any = { name: themeForm.name.trim() };
      if (themeForm.description.trim()) payload.description = themeForm.description.trim();
      if (themeForm.weight.trim() !== '') payload.weight = Number(themeForm.weight);
      await api.narrativeEngine.addTheme(selectedNarrativeId, payload);
      toast.success('Theme added');
      setThemeForm({ name: '', description: '', weight: '1.0' });
      loadNarrativeDetail(selectedNarrativeId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleGenerateSummary = async () => {
    if (!selectedNarrativeId) return;
    try {
      const result = await api.narrativeEngine.generateSummary(selectedNarrativeId);
      setSummary(result);
      toast.success('Summary generated');
    } catch (e: any) { toast.error(e.message); }
  };

  const renderBadge = (value: string, color: string) => (
    <span style={{
      display: 'inline-block',
      padding: '2px 8px',
      borderRadius: 10,
      fontSize: 11,
      fontWeight: 600,
      color: '#fff',
      background: color,
      marginRight: 4,
    }}>{value}</span>
  );

  const statusColor = (s: string) => STATUS_COLORS[s] ?? themeColors.primary;
  const significanceColor = (s: string) => SIGNIFICANCE_COLORS[s] ?? themeColors.primary;

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>📖 Narrative Engine</h2>
          <p className="panel-subtitle">Create narratives, add events, characters, and themes</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading narrative engine...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>📖 Narrative Engine</h2>
        <p className="panel-subtitle">Create narratives, add events, characters, and themes</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_narratives ?? '-'}</span><span className="stat-label">Narratives</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_events ?? '-'}</span><span className="stat-label">Events</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_characters ?? '-'}</span><span className="stat-label">Characters</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_themes ?? '-'}</span><span className="stat-label">Themes</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.published_count ?? '-'}</span><span className="stat-label">Published</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'narrative', 'event'] as const).map(s => (
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

      {/* Overview Section */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Narrative Engine Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Narratives</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_narratives ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Events</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_events ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Characters</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_characters ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Themes</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_themes ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Published</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.published_count ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Narratives</h3>
            <button onClick={() => loadNarratives()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {narratives.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No narratives recorded. Create one in the Narrative section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {narratives.slice(0, 10).map((n: any, i: number) => {
                  const id = n.narrative_id ?? n.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{n.title ?? 'untitled'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{n.description ?? ''} · {id}</div>
                        </div>
                        <div>
                          {n.narrative_type && renderBadge(n.narrative_type, themeColors.secondary)}
                          {n.status && renderBadge(n.status, statusColor(n.status))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Narrative Section */}
      {activeSection === 'narrative' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Create Narrative</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Title *</label>
                <input value={narrativeForm.title} onChange={e => setNarrativeForm({ ...narrativeForm, title: e.target.value })} placeholder="e.g. first_contact" />
              </div>
              <div className="form-group">
                <label>Narrative Type</label>
                <select value={narrativeForm.narrative_type} onChange={e => setNarrativeForm({ ...narrativeForm, narrative_type: e.target.value })}>
                  {NARRATIVE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Tense</label>
                <select value={narrativeForm.tense} onChange={e => setNarrativeForm({ ...narrativeForm, tense: e.target.value })}>
                  {NARRATIVE_TENSES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Perspective</label>
                <select value={narrativeForm.perspective} onChange={e => setNarrativeForm({ ...narrativeForm, perspective: e.target.value })}>
                  {PERSPECTIVE_TYPES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={narrativeForm.description} onChange={e => setNarrativeForm({ ...narrativeForm, description: e.target.value })} />
              </div>
            </div>
            <button onClick={handleCreateNarrative} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Narrative</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Narratives ({narratives.length})</h3>
            <button onClick={() => loadNarratives()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {narratives.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No narratives recorded. Create one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {narratives.slice(0, 30).map((n: any, i: number) => {
                  const id = n.narrative_id ?? n.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{n.title ?? 'untitled'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{n.description ?? ''} · {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {n.narrative_type && renderBadge(n.narrative_type, themeColors.secondary)}
                          {n.tense && renderBadge(n.tense, '#6366f1')}
                          {n.status && renderBadge(n.status, statusColor(n.status))}
                          <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff', marginLeft: 4 }} onClick={() => { setActiveSection('event'); setSelectedNarrativeId(id); }}>Open</button>
                          <button className="btn-sm" style={{ background: '#dc2626', color: '#fff', marginLeft: 4 }} onClick={() => handleDeleteNarrative(id)}>Delete</button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Event Section */}
      {activeSection === 'event' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Active Narrative</h3>
            <div className="form-group" style={{ marginTop: 8 }}>
              <label>Narrative</label>
              <select
                value={selectedNarrativeId}
                onChange={e => { setSelectedNarrativeId(e.target.value); setEvents([]); setCharacters([]); setThemes([]); setSummary(null); }}
              >
                <option value="">— Select a narrative —</option>
                {narratives.map((n: any) => {
                  const id = n.narrative_id ?? n.id;
                  return <option key={id} value={id}>{n.title ?? id}</option>;
                })}
              </select>
            </div>
          </div>

          {selectedNarrativeId && (
            <>
              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Add Event</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label>Title *</label>
                    <input value={eventForm.title} onChange={e => setEventForm({ ...eventForm, title: e.target.value })} placeholder="e.g. discovery" />
                  </div>
                  <div className="form-group">
                    <label>Plot Arc</label>
                    <select value={eventForm.plot_arc} onChange={e => setEventForm({ ...eventForm, plot_arc: e.target.value })}>
                      {PLOT_ARCS.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Significance</label>
                    <select value={eventForm.significance} onChange={e => setEventForm({ ...eventForm, significance: e.target.value })}>
                      {SIGNIFICANCE_LEVELS.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Sequence</label>
                    <input value={eventForm.sequence} onChange={e => setEventForm({ ...eventForm, sequence: e.target.value })} type="number" />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Description</label>
                    <input value={eventForm.description} onChange={e => setEventForm({ ...eventForm, description: e.target.value })} />
                  </div>
                </div>
                <button onClick={handleAddEvent} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Event</button>
              </div>

              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Add Character</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label>Name *</label>
                    <input value={characterForm.name} onChange={e => setCharacterForm({ ...characterForm, name: e.target.value })} placeholder="e.g. explorer" />
                  </div>
                  <div className="form-group">
                    <label>Role</label>
                    <input value={characterForm.role} onChange={e => setCharacterForm({ ...characterForm, role: e.target.value })} placeholder="e.g. protagonist" />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Description</label>
                    <input value={characterForm.description} onChange={e => setCharacterForm({ ...characterForm, description: e.target.value })} />
                  </div>
                </div>
                <button onClick={handleAddCharacter} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Character</button>
              </div>

              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Add Theme</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label>Name *</label>
                    <input value={themeForm.name} onChange={e => setThemeForm({ ...themeForm, name: e.target.value })} placeholder="e.g. redemption" />
                  </div>
                  <div className="form-group">
                    <label>Weight</label>
                    <input value={themeForm.weight} onChange={e => setThemeForm({ ...themeForm, weight: e.target.value })} type="number" min="0" step="0.1" />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Description</label>
                    <input value={themeForm.description} onChange={e => setThemeForm({ ...themeForm, description: e.target.value })} />
                  </div>
                </div>
                <button onClick={handleAddTheme} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Theme</button>
              </div>

              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Events ({events.length})</h3>
                <button onClick={() => loadNarrativeDetail(selectedNarrativeId)} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
                {events.length === 0 ? (
                  <div style={{ color: themeColors.text, opacity: 0.7 }}>No events recorded. Add one above.</div>
                ) : (
                  <div style={{ display: 'grid', gap: 8 }}>
                    {events.slice(0, 30).map((ev: any, i: number) => {
                      const id = ev.event_id ?? ev.id ?? i;
                      return (
                        <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                            <div>
                              <div style={{ fontWeight: 600, color: themeColors.text }}>{ev.title ?? 'untitled event'}</div>
                              <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{ev.description ?? ''} · {id}</div>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                              {ev.plot_arc && renderBadge(ev.plot_arc, themeColors.secondary)}
                              {ev.significance && renderBadge(ev.significance, significanceColor(ev.significance))}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Characters ({characters.length})</h3>
                <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(characters, null, 2)}</pre>
                <h3 style={{ color: themeColors.text, marginTop: 12 }}>Themes ({themes.length})</h3>
                <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(themes, null, 2)}</pre>
              </div>

              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                <h3 style={{ color: themeColors.text }}>Summary</h3>
                <button onClick={handleGenerateSummary} className="btn-primary" style={{ marginTop: 8, background: themeColors.primary, color: '#fff' }}>Generate Summary</button>
                {summary && (
                  <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 300, border: `1px solid ${themeColors.border}`, fontSize: 12, marginTop: 12 }}>{JSON.stringify(summary, null, 2)}</pre>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default NarrativeEnginePanel;
