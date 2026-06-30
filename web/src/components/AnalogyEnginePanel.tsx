import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: orange for analogy engine
const themeColors = {
  primary: '#ea580c',
  secondary: '#f97316',
  bg: '#fff7ed',
  border: '#fed7aa',
  accent: '#ffedd5',
  text: '#7c2d12',
};

// Enum values must match backend DomainType / MappingType / AnalogyStatus exactly (lowercase).
const DOMAIN_TYPES = ['concrete', 'abstract', 'procedural', 'conceptual', 'hybrid'];
const MAPPING_TYPES = ['structural', 'functional', 'relational', 'attribute', 'causal'];
const ANALOGY_STATUS = ['draft', 'proposed', 'validated', 'rejected', 'refined', 'archived'];
const CONFIDENCE_LEVELS = ['low', 'medium', 'high', 'very_high'];
const TRANSFER_STATUS = ['pending', 'transferred', 'failed', 'partial'];

// Status -> badge color mapping for quick visual scanning.
const STATUS_COLORS: Record<string, string> = {
  draft: '#9ca3af',
  proposed: '#2563eb',
  validated: '#059669',
  rejected: '#dc2626',
  refined: '#7c3aed',
  archived: '#6b7280',
};

const CONFIDENCE_COLORS: Record<string, string> = {
  low: '#dc2626',
  medium: '#d97706',
  high: '#059669',
  very_high: '#047857',
};

export const AnalogyEnginePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'domain' | 'analogy'>('overview');

  // Domains / entities / relations / analogies
  const [domains, setDomains] = useState<any[]>([]);
  const [selectedDomainId, setSelectedDomainId] = useState<string>('');
  const [entities, setEntities] = useState<any[]>([]);
  const [relations, setRelations] = useState<any[]>([]);
  const [analogies, setAnalogies] = useState<any[]>([]);

  // Domain form
  const [domainForm, setDomainForm] = useState({
    name: '',
    domain_type: 'concrete',
    description: '',
  });

  // Entity form
  const [entityForm, setEntityForm] = useState({
    name: '',
    attributes: '',
    description: '',
  });

  // Relation form
  const [relationForm, setRelationForm] = useState({
    source_entity: '',
    target_entity: '',
    relation_type: 'causal',
    weight: '1.0',
  });

  // Analogy form
  const [analogyForm, setAnalogyForm] = useState({
    source_domain: '',
    target_domain: '',
    mapping_type: 'structural',
    description: '',
  });

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.analogyEngine.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load analogy engine stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDomains = useCallback(async () => {
    try {
      const result = await api.analogyEngine.listDomains();
      const list = Array.isArray(result) ? result : (result?.domains ?? []);
      setDomains(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load domains');
    }
  }, [toast]);

  const loadDomainDetail = useCallback(async (domainId: string) => {
    if (!domainId) return;
    try {
      const [ents, rels] = await Promise.all([
        api.analogyEngine.listEntities(domainId).catch(() => []),
        api.analogyEngine.listRelations(domainId).catch(() => []),
      ]);
      setEntities(Array.isArray(ents) ? ents : (ents?.entities ?? []));
      setRelations(Array.isArray(rels) ? rels : (rels?.relations ?? []));
    } catch {
      setEntities([]);
      setRelations([]);
    }
  }, []);

  const loadAnalogies = useCallback(async () => {
    try {
      const result = await api.analogyEngine.listAnalogies();
      const list = Array.isArray(result) ? result : (result?.analogies ?? []);
      setAnalogies(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load analogies');
    }
  }, [toast]);

  // Initial load
  useEffect(() => { loadStats(); }, [loadStats]);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadDomains();
      loadAnalogies();
    }
  }, [activeSection, loadStats, loadDomains, loadAnalogies]);

  // When the active domain changes, refresh its entities and relations
  useEffect(() => {
    if (selectedDomainId) loadDomainDetail(selectedDomainId);
  }, [selectedDomainId, loadDomainDetail]);

  // Auto-select first domain when entering the domain section
  useEffect(() => {
    if (activeSection === 'domain' && !selectedDomainId && domains.length > 0) {
      setSelectedDomainId(domains[0].domain_id ?? domains[0].id);
    }
  }, [activeSection, selectedDomainId, domains]);

  const handleRegisterDomain = async () => {
    if (!domainForm.name.trim()) {
      toast.error('Domain name is required');
      return;
    }
    try {
      const payload: any = {
        name: domainForm.name.trim(),
        domain_type: domainForm.domain_type,
      };
      if (domainForm.description.trim()) payload.description = domainForm.description.trim();
      await api.analogyEngine.registerDomain(payload);
      toast.success('Domain registered');
      setDomainForm({ name: '', domain_type: 'concrete', description: '' });
      await loadDomains();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddEntity = async () => {
    if (!selectedDomainId || !entityForm.name.trim()) {
      toast.error('Domain and entity name are required');
      return;
    }
    let attributes: any = {};
    if (entityForm.attributes.trim() !== '') {
      try { attributes = JSON.parse(entityForm.attributes); }
      catch { toast.error('Attributes must be valid JSON'); return; }
    }
    try {
      const payload: any = { name: entityForm.name.trim(), attributes };
      if (entityForm.description.trim()) payload.description = entityForm.description.trim();
      await api.analogyEngine.addEntity(selectedDomainId, payload);
      toast.success('Entity added');
      setEntityForm({ name: '', attributes: '', description: '' });
      loadDomainDetail(selectedDomainId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddRelation = async () => {
    if (!selectedDomainId || !relationForm.source_entity.trim() || !relationForm.target_entity.trim()) {
      toast.error('Domain and both entities are required');
      return;
    }
    try {
      const payload: any = {
        source_entity: relationForm.source_entity.trim(),
        target_entity: relationForm.target_entity.trim(),
        relation_type: relationForm.relation_type,
      };
      if (relationForm.weight.trim() !== '') payload.weight = Number(relationForm.weight);
      await api.analogyEngine.addRelation(selectedDomainId, payload);
      toast.success('Relation added');
      setRelationForm({ source_entity: '', target_entity: '', relation_type: 'causal', weight: '1.0' });
      loadDomainDetail(selectedDomainId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreateAnalogy = async () => {
    if (!analogyForm.source_domain.trim() || !analogyForm.target_domain.trim()) {
      toast.error('Source and target domains are required');
      return;
    }
    try {
      const payload: any = {
        source_domain: analogyForm.source_domain.trim(),
        target_domain: analogyForm.target_domain.trim(),
        mapping_type: analogyForm.mapping_type,
      };
      if (analogyForm.description.trim()) payload.description = analogyForm.description.trim();
      await api.analogyEngine.createAnalogy(payload);
      toast.success('Analogy created');
      setAnalogyForm({ source_domain: '', target_domain: '', mapping_type: 'structural', description: '' });
      await loadAnalogies();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleValidateAnalogy = async (analogyId: string) => {
    try {
      await api.analogyEngine.validateAnalogy(analogyId, { structural: 0.8, functional: 0.7 });
      toast.success('Analogy validated');
      await loadAnalogies();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRefineAnalogy = async (analogyId: string) => {
    try {
      await api.analogyEngine.refineAnalogy(analogyId, {});
      toast.success('Analogy refined');
      await loadAnalogies();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTransferKnowledge = async (analogyId: string) => {
    try {
      await api.analogyEngine.transferKnowledge(analogyId, []);
      toast.success('Knowledge transfer initiated');
      await loadAnalogies();
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
  const confidenceColor = (c: string) => CONFIDENCE_COLORS[c] ?? themeColors.primary;

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🔄 Analogy Engine</h2>
          <p className="panel-subtitle">Register domains, build analogies, and transfer knowledge across domains</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading analogy engine...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🔄 Analogy Engine</h2>
        <p className="panel-subtitle">Register domains, build analogies, and transfer knowledge across domains</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_domains ?? '-'}</span><span className="stat-label">Domains</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_entities ?? '-'}</span><span className="stat-label">Entities</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_relations ?? '-'}</span><span className="stat-label">Relations</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_analogies ?? '-'}</span><span className="stat-label">Analogies</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.validated_count ?? '-'}</span><span className="stat-label">Validated</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'domain', 'analogy'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Analogy Engine Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Domains</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_domains ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Entities</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_entities ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Relations</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_relations ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Analogies</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_analogies ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Validated</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.validated_count ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Analogies</h3>
            <button onClick={() => loadAnalogies()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {analogies.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No analogies recorded. Create one in the Analogy section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {analogies.slice(0, 10).map((a: any, i: number) => {
                  const id = a.analogy_id ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{a.source_domain ?? '?'} → {a.target_domain ?? '?'}</div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Domain Section */}
      {activeSection === 'domain' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Domain</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Name *</label>
                <input value={domainForm.name} onChange={e => setDomainForm({ ...domainForm, name: e.target.value })} placeholder="e.g. solar_system" />
              </div>
              <div className="form-group">
                <label>Domain Type</label>
                <select value={domainForm.domain_type} onChange={e => setDomainForm({ ...domainForm, domain_type: e.target.value })}>
                  {DOMAIN_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={domainForm.description} onChange={e => setDomainForm({ ...domainForm, description: e.target.value })} />
              </div>
            </div>
            <button onClick={handleRegisterDomain} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Domain</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Domains ({domains.length})</h3>
            <button onClick={() => loadDomains()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            <div className="form-group" style={{ marginBottom: 12 }}>
              <label>Active Domain</label>
              <select value={selectedDomainId} onChange={e => setSelectedDomainId(e.target.value)}>
                <option value="">— Select a domain —</option>
                {domains.map((d: any) => {
                  const id = d.domain_id ?? d.id;
                  return <option key={id} value={id}>{d.name ?? id}</option>;
                })}
              </select>
            </div>
            {domains.length === 0 && (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No domains recorded. Register one above.</div>
            )}
          </div>

          {selectedDomainId && (
            <>
              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Add Entity</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label>Name *</label>
                    <input value={entityForm.name} onChange={e => setEntityForm({ ...entityForm, name: e.target.value })} placeholder="e.g. sun" />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Attributes (JSON)</label>
                    <input value={entityForm.attributes} onChange={e => setEntityForm({ ...entityForm, attributes: e.target.value })} placeholder='{"mass": 1.989, "role": "center"}' />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Description</label>
                    <input value={entityForm.description} onChange={e => setEntityForm({ ...entityForm, description: e.target.value })} />
                  </div>
                </div>
                <button onClick={handleAddEntity} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Entity</button>
              </div>

              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Add Relation</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label>Source Entity *</label>
                    <input value={relationForm.source_entity} onChange={e => setRelationForm({ ...relationForm, source_entity: e.target.value })} placeholder="entity id or name" />
                  </div>
                  <div className="form-group">
                    <label>Target Entity *</label>
                    <input value={relationForm.target_entity} onChange={e => setRelationForm({ ...relationForm, target_entity: e.target.value })} placeholder="entity id or name" />
                  </div>
                  <div className="form-group">
                    <label>Relation Type</label>
                    <select value={relationForm.relation_type} onChange={e => setRelationForm({ ...relationForm, relation_type: e.target.value })}>
                      {MAPPING_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Weight</label>
                    <input value={relationForm.weight} onChange={e => setRelationForm({ ...relationForm, weight: e.target.value })} type="number" min="0" step="0.1" />
                  </div>
                </div>
                <button onClick={handleAddRelation} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Relation</button>
              </div>

              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                <h3 style={{ color: themeColors.text }}>Domain: {selectedDomainId}</h3>
                <h4 style={{ color: themeColors.text, marginTop: 12 }}>Entities ({entities.length})</h4>
                <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(entities, null, 2)}</pre>
                <h4 style={{ color: themeColors.text, marginTop: 12 }}>Relations ({relations.length})</h4>
                <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(relations, null, 2)}</pre>
              </div>
            </>
          )}
        </div>
      )}

      {/* Analogy Section */}
      {activeSection === 'analogy' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Create Analogy</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Source Domain *</label>
                <select value={analogyForm.source_domain} onChange={e => setAnalogyForm({ ...analogyForm, source_domain: e.target.value })}>
                  <option value="">— Select source —</option>
                  {domains.map((d: any) => {
                    const id = d.domain_id ?? d.id;
                    return <option key={id} value={id}>{d.name ?? id}</option>;
                  })}
                </select>
              </div>
              <div className="form-group">
                <label>Target Domain *</label>
                <select value={analogyForm.target_domain} onChange={e => setAnalogyForm({ ...analogyForm, target_domain: e.target.value })}>
                  <option value="">— Select target —</option>
                  {domains.map((d: any) => {
                    const id = d.domain_id ?? d.id;
                    return <option key={id} value={id}>{d.name ?? id}</option>;
                  })}
                </select>
              </div>
              <div className="form-group">
                <label>Mapping Type</label>
                <select value={analogyForm.mapping_type} onChange={e => setAnalogyForm({ ...analogyForm, mapping_type: e.target.value })}>
                  {MAPPING_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={analogyForm.description} onChange={e => setAnalogyForm({ ...analogyForm, description: e.target.value })} />
              </div>
            </div>
            <button onClick={handleCreateAnalogy} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Analogy</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Analogies ({analogies.length})</h3>
            <button onClick={() => loadAnalogies()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {analogies.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No analogies recorded. Create one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {analogies.slice(0, 30).map((a: any, i: number) => {
                  const id = a.analogy_id ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{a.source_domain ?? '?'} → {a.target_domain ?? '?'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{a.description ?? ''} · {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {a.mapping_type && renderBadge(a.mapping_type, themeColors.secondary)}
                          {a.status && renderBadge(a.status, statusColor(a.status))}
                          {a.confidence && renderBadge(a.confidence, confidenceColor(a.confidence))}
                          <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff', marginLeft: 4 }} onClick={() => handleValidateAnalogy(id)}>Validate</button>
                          <button className="btn-sm" style={{ background: themeColors.secondary, color: '#fff', marginLeft: 4 }} onClick={() => handleRefineAnalogy(id)}>Refine</button>
                          <button className="btn-sm" style={{ background: '#059669', color: '#fff', marginLeft: 4 }} onClick={() => handleTransferKnowledge(id)}>Transfer</button>
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
    </div>
  );
};

export default AnalogyEnginePanel;
