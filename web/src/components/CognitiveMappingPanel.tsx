import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: teal for cognitive mapping
const themeColors = {
  primary: '#0d9488',
  secondary: '#14b8a6',
  bg: '#f0fdfa',
  border: '#99f6e4',
  accent: '#ccfbf1',
  text: '#134e4a',
};

// Enum values must match backend EnvironmentType / MapStatus / SpatialRelation / AnchorType / DeltaType exactly (uppercase).
const ENVIRONMENT_TYPES = ['FILESYSTEM', 'WORKSPACE', 'UI_TREE', 'SEMANTIC_GRAPH', 'NETWORK', 'KNOWLEDGE_BASE'];
const MAP_STATUS = ['DRAFT', 'ACTIVE', 'ARCHIVED', 'STALE'];
const SPATIAL_RELATIONS = ['CONTAINS', 'ADJACENT', 'NESTED_IN', 'REACHABLE_FROM', 'OVERLAPS', 'PART_OF'];
const ANCHOR_TYPES = ['LANDMARK', 'REGION', 'BOUNDARY', 'PORTAL', 'NODE'];
const DELTA_TYPES = ['ADD', 'UPDATE', 'REMOVE', 'MERGE'];

// Map a status value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  DRAFT: '#9ca3af',
  ACTIVE: '#0d9488',
  ARCHIVED: '#6366f1',
  STALE: '#dc2626',
};

export const CognitiveMappingPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'map' | 'place'>('overview');

  // Maps / places / anchors / edges / deltas
  const [maps, setMaps] = useState<any[]>([]);
  const [places, setPlaces] = useState<any[]>([]);
  const [selectedMap, setSelectedMap] = useState<string>('');
  const [pathResult, setPathResult] = useState<any>(null);
  const [localizeResult, setLocalizeResult] = useState<any>(null);

  // Map form
  const [mapForm, setMapForm] = useState({
    agent_id: '',
    name: '',
    environment_type: 'WORKSPACE',
    description: '',
  });

  // Place form
  const [placeForm, setPlaceForm] = useState({
    name: '',
    place_type: '',
    coordinates: '',
    properties: '',
  });

  // Anchor form
  const [anchorForm, setAnchorForm] = useState({
    place_id: '',
    anchor_type: 'LANDMARK',
    label: '',
    salience: '0.5',
  });

  // Edge form
  const [edgeForm, setEdgeForm] = useState({
    source_place_id: '',
    target_place_id: '',
    relation: 'CONTAINS',
    weight: '1.0',
  });

  // Path form
  const [pathForm, setPathForm] = useState({
    source_place_id: '',
    target_place_id: '',
  });

  // Localize form
  const [localizeForm, setLocalizeForm] = useState({
    anchor_label: '',
    coordinates: '',
  });

  // Delta form
  const [deltaForm, setDeltaForm] = useState({
    delta_type: 'ADD',
    place_id: '',
    place_data: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveMapping.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive mapping stats');
    } finally {
      setLoading(false);
    }
  };

  const loadMaps = async () => {
    try {
      const result = await api.cognitiveMapping.listMaps();
      const list = Array.isArray(result) ? result : (result?.maps ?? []);
      setMaps(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load maps');
    }
  };

  const loadPlaces = async () => {
    if (!selectedMap) { setPlaces([]); return; }
    try {
      const result = await api.cognitiveMapping.listPlaces(selectedMap);
      const list = Array.isArray(result) ? result : (result?.places ?? []);
      setPlaces(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load places');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadMaps();
    }
  }, [activeSection]);

  // Reload places when selected map changes
  useEffect(() => { loadPlaces(); }, [selectedMap]);

  const handleCreateMap = async () => {
    if (!mapForm.agent_id.trim() || !mapForm.name.trim()) {
      toast.error('Agent ID and Name are required');
      return;
    }
    const payload: any = {
      agent_id: mapForm.agent_id.trim(),
      name: mapForm.name.trim(),
      environment_type: mapForm.environment_type,
    };
    if (mapForm.description.trim()) payload.description = mapForm.description.trim();
    try {
      await api.cognitiveMapping.createMap(payload);
      toast.success('Map created');
      setMapForm({ agent_id: '', name: '', environment_type: 'WORKSPACE', description: '' });
      await loadMaps();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddPlace = async () => {
    if (!selectedMap || !placeForm.name.trim()) {
      toast.error('Select a map and provide a place name');
      return;
    }
    const payload: any = { name: placeForm.name.trim() };
    if (placeForm.place_type.trim()) payload.place_type = placeForm.place_type.trim();
    if (placeForm.coordinates.trim()) {
      try { payload.coordinates = JSON.parse(placeForm.coordinates); }
      catch { toast.error('Coordinates must be valid JSON'); return; }
    }
    if (placeForm.properties.trim()) {
      try { payload.properties = JSON.parse(placeForm.properties); }
      catch { toast.error('Properties must be valid JSON'); return; }
    }
    try {
      await api.cognitiveMapping.addPlace(selectedMap, payload);
      toast.success('Place added');
      setPlaceForm({ name: '', place_type: '', coordinates: '', properties: '' });
      await loadPlaces();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddAnchor = async () => {
    if (!selectedMap || !anchorForm.place_id.trim() || !anchorForm.label.trim()) {
      toast.error('Map, place ID, and label are required');
      return;
    }
    const payload: any = {
      anchor_type: anchorForm.anchor_type,
      label: anchorForm.label.trim(),
    };
    if (anchorForm.salience.trim() !== '') payload.salience = Number(anchorForm.salience);
    try {
      await api.cognitiveMapping.addAnchor(selectedMap, anchorForm.place_id.trim(), payload);
      toast.success('Anchor added');
      setAnchorForm({ place_id: '', anchor_type: 'LANDMARK', label: '', salience: '0.5' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddEdge = async () => {
    if (!selectedMap || !edgeForm.source_place_id.trim() || !edgeForm.target_place_id.trim()) {
      toast.error('Map, source place, and target place are required');
      return;
    }
    const payload: any = {
      source_place_id: edgeForm.source_place_id.trim(),
      target_place_id: edgeForm.target_place_id.trim(),
      relation: edgeForm.relation,
    };
    if (edgeForm.weight.trim() !== '') payload.weight = Number(edgeForm.weight);
    try {
      await api.cognitiveMapping.addEdge(selectedMap, payload);
      toast.success('Edge added');
      setEdgeForm({ source_place_id: '', target_place_id: '', relation: 'CONTAINS', weight: '1.0' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleFindPath = async () => {
    if (!selectedMap || !pathForm.source_place_id.trim() || !pathForm.target_place_id.trim()) {
      toast.error('Map, source place, and target place are required');
      return;
    }
    try {
      const result = await api.cognitiveMapping.findPath(selectedMap, pathForm.source_place_id.trim(), pathForm.target_place_id.trim());
      setPathResult(result);
      toast.success('Path computed');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleLocalize = async () => {
    if (!selectedMap) { toast.error('Select a map first'); return; }
    if (!localizeForm.anchor_label.trim() && !localizeForm.coordinates.trim()) {
      toast.error('Provide an anchor label or coordinates');
      return;
    }
    const payload: any = {};
    if (localizeForm.anchor_label.trim()) payload.anchor_label = localizeForm.anchor_label.trim();
    if (localizeForm.coordinates.trim()) {
      try { payload.coordinates = JSON.parse(localizeForm.coordinates); }
      catch { toast.error('Coordinates must be valid JSON'); return; }
    }
    try {
      const result = await api.cognitiveMapping.localize(selectedMap, payload);
      setLocalizeResult(result);
      toast.success('Localization computed');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleApplyDelta = async () => {
    if (!selectedMap || !deltaForm.delta_type) {
      toast.error('Select a map and delta type');
      return;
    }
    const payload: any = { delta_type: deltaForm.delta_type };
    if (deltaForm.place_id.trim()) payload.place_id = deltaForm.place_id.trim();
    if (deltaForm.place_data.trim()) {
      try { payload.place_data = JSON.parse(deltaForm.place_data); }
      catch { toast.error('Place data must be valid JSON'); return; }
    }
    try {
      await api.cognitiveMapping.applyDelta(selectedMap, payload);
      toast.success('Delta applied');
      setDeltaForm({ delta_type: 'ADD', place_id: '', place_data: '' });
      await loadPlaces();
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

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🗺️ Cognitive Mapping</h2>
          <p className="panel-subtitle">Build spatial maps, places, anchors, and edges for agent navigation</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive mapping...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🗺️ Cognitive Mapping</h2>
        <p className="panel-subtitle">Build spatial maps, places, anchors, and edges for agent navigation</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_maps ?? '-'}</span><span className="stat-label">Maps</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_places ?? '-'}</span><span className="stat-label">Places</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_edges ?? '-'}</span><span className="stat-label">Edges</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_anchors ?? '-'}</span><span className="stat-label">Anchors</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_deltas ?? '-'}</span><span className="stat-label">Deltas</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'map', 'place'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Cognitive Mapping Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Maps</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_maps ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Places</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_places ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Edges</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_edges ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Anchors</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_anchors ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Deltas</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_deltas ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Maps</h3>
            <button onClick={() => loadMaps()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {maps.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No maps recorded. Create one in the Map section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {maps.slice(0, 10).map((m: any, i: number) => {
                  const id = m.map_id ?? m.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{m.name ?? 'unnamed'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{m.description ?? ''} · {id}</div>
                        </div>
                        <div>
                          {m.environment_type && renderBadge(m.environment_type, themeColors.secondary)}
                          {m.status && renderBadge(m.status, statusColor(m.status))}
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

      {/* Map Section */}
      {activeSection === 'map' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Create Map</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={mapForm.agent_id} onChange={e => setMapForm({ ...mapForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Name *</label>
                <input value={mapForm.name} onChange={e => setMapForm({ ...mapForm, name: e.target.value })} placeholder="e.g. workspace_layout" />
              </div>
              <div className="form-group">
                <label>Environment Type</label>
                <select value={mapForm.environment_type} onChange={e => setMapForm({ ...mapForm, environment_type: e.target.value })}>
                  {ENVIRONMENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={mapForm.description} onChange={e => setMapForm({ ...mapForm, description: e.target.value })} placeholder="Optional description" />
              </div>
            </div>
            <button onClick={handleCreateMap} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Map</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Maps ({maps.length})</h3>
            <button onClick={() => loadMaps()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {maps.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No maps recorded. Create one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {maps.slice(0, 30).map((m: any, i: number) => {
                  const id = m.map_id ?? m.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{m.name ?? 'unnamed'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>agent: {m.agent_id ?? '-'} · {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {m.environment_type && renderBadge(m.environment_type, themeColors.secondary)}
                          {m.status && renderBadge(m.status, statusColor(m.status))}
                          <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff', marginLeft: 4 }} onClick={() => setSelectedMap(id)}>Select</button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            {selectedMap && (
              <div style={{ marginTop: 12, padding: 8, background: themeColors.accent, borderRadius: 6, color: themeColors.text, fontSize: 13 }}>
                Selected map: <strong>{selectedMap}</strong>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Place Section */}
      {activeSection === 'place' && (
        <div className="dashboard-section">
          <div style={{ padding: 12, background: themeColors.accent, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16, color: themeColors.text }}>
            Working on map: <strong>{selectedMap || 'none selected'}</strong> — choose a map in the Map section first.
          </div>

          {/* Add Place */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Add Place</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Name *</label>
                <input value={placeForm.name} onChange={e => setPlaceForm({ ...placeForm, name: e.target.value })} placeholder="e.g. project_root" />
              </div>
              <div className="form-group">
                <label>Place Type</label>
                <input value={placeForm.place_type} onChange={e => setPlaceForm({ ...placeForm, place_type: e.target.value })} placeholder="e.g. directory" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Coordinates (JSON)</label>
                <input value={placeForm.coordinates} onChange={e => setPlaceForm({ ...placeForm, coordinates: e.target.value })} placeholder='{"x": 0, "y": 0}' />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Properties (JSON)</label>
                <input value={placeForm.properties} onChange={e => setPlaceForm({ ...placeForm, properties: e.target.value })} placeholder='{"visited": true}' />
              </div>
            </div>
            <button onClick={handleAddPlace} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Place</button>
          </div>

          {/* Add Anchor */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Add Anchor</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Place ID *</label>
                <input value={anchorForm.place_id} onChange={e => setAnchorForm({ ...anchorForm, place_id: e.target.value })} placeholder="place id" />
              </div>
              <div className="form-group">
                <label>Anchor Type</label>
                <select value={anchorForm.anchor_type} onChange={e => setAnchorForm({ ...anchorForm, anchor_type: e.target.value })}>
                  {ANCHOR_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Label *</label>
                <input value={anchorForm.label} onChange={e => setAnchorForm({ ...anchorForm, label: e.target.value })} placeholder="e.g. main_entrance" />
              </div>
              <div className="form-group">
                <label>Salience</label>
                <input value={anchorForm.salience} onChange={e => setAnchorForm({ ...anchorForm, salience: e.target.value })} type="number" min="0" max="1" step="0.1" />
              </div>
            </div>
            <button onClick={handleAddAnchor} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Anchor</button>
          </div>

          {/* Add Edge */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Add Edge</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Source Place ID *</label>
                <input value={edgeForm.source_place_id} onChange={e => setEdgeForm({ ...edgeForm, source_place_id: e.target.value })} placeholder="source place id" />
              </div>
              <div className="form-group">
                <label>Target Place ID *</label>
                <input value={edgeForm.target_place_id} onChange={e => setEdgeForm({ ...edgeForm, target_place_id: e.target.value })} placeholder="target place id" />
              </div>
              <div className="form-group">
                <label>Relation</label>
                <select value={edgeForm.relation} onChange={e => setEdgeForm({ ...edgeForm, relation: e.target.value })}>
                  {SPATIAL_RELATIONS.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Weight</label>
                <input value={edgeForm.weight} onChange={e => setEdgeForm({ ...edgeForm, weight: e.target.value })} type="number" min="0" step="0.1" />
              </div>
            </div>
            <button onClick={handleAddEdge} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Edge</button>
          </div>

          {/* Find Path */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Find Path</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Source Place ID *</label>
                <input value={pathForm.source_place_id} onChange={e => setPathForm({ ...pathForm, source_place_id: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Target Place ID *</label>
                <input value={pathForm.target_place_id} onChange={e => setPathForm({ ...pathForm, target_place_id: e.target.value })} />
              </div>
            </div>
            <button onClick={handleFindPath} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Find Path</button>
            {pathResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(pathResult, null, 2)}</pre>
            )}
          </div>

          {/* Localize */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Localize</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Anchor Label</label>
                <input value={localizeForm.anchor_label} onChange={e => setLocalizeForm({ ...localizeForm, anchor_label: e.target.value })} placeholder="e.g. main_entrance" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Coordinates (JSON)</label>
                <input value={localizeForm.coordinates} onChange={e => setLocalizeForm({ ...localizeForm, coordinates: e.target.value })} placeholder='{"x": 3, "y": 2}' />
              </div>
            </div>
            <button onClick={handleLocalize} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Localize</button>
            {localizeResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(localizeResult, null, 2)}</pre>
            )}
          </div>

          {/* Apply Delta */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Apply Delta</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Delta Type</label>
                <select value={deltaForm.delta_type} onChange={e => setDeltaForm({ ...deltaForm, delta_type: e.target.value })}>
                  {DELTA_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Place ID</label>
                <input value={deltaForm.place_id} onChange={e => setDeltaForm({ ...deltaForm, place_id: e.target.value })} placeholder="optional place id" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Place Data (JSON)</label>
                <input value={deltaForm.place_data} onChange={e => setDeltaForm({ ...deltaForm, place_data: e.target.value })} placeholder='{"name": "new_place"}' />
              </div>
            </div>
            <button onClick={handleApplyDelta} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Apply Delta</button>
          </div>

          {/* Places List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Places ({places.length})</h3>
            <button onClick={() => loadPlaces()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {places.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No places recorded for the selected map.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {places.slice(0, 30).map((p: any, i: number) => {
                  const id = p.place_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{p.name ?? 'unnamed'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{p.place_type ?? 'no_type'}]</span></div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                      {p.coordinates && (
                        <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 6, overflow: 'auto', maxHeight: 80, fontSize: 11 }}>{JSON.stringify(p.coordinates, null, 2)}</pre>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CognitiveMappingPanel;
