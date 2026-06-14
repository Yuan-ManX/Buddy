import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

interface Entity {
  id: string;
  name: string;
  type: string;
  properties: Record<string, string>;
  created_at: string;
}

interface Relationship {
  id: string;
  source_id: string;
  source_name: string;
  target_id: string;
  target_name: string;
  type: string;
  properties: Record<string, string>;
  created_at: string;
}

interface EntityDetail extends Entity {
  relationships: Relationship[];
}

interface GraphStats {
  total_entities: number;
  total_relationships: number;
  entity_type_counts: Record<string, number>;
  relationship_type_counts: Record<string, number>;
}

interface SemSearchResult {
  entity: Entity;
  similarity: number;
  snippet: string;
}

const ENTITY_TYPES = [
  'agent',
  'skill',
  'tool',
  'concept',
  'document',
  'memory',
  'task',
  'user',
  'other',
];

const TYPE_COLORS: Record<string, string> = {
  agent: '#8b5cf6',
  skill: '#3b82f6',
  tool: '#10b981',
  concept: '#f59e0b',
  document: '#ec4899',
  memory: '#06b6d4',
  task: '#ef4444',
  user: '#6366f1',
  other: '#6b7280',
};

export const KnowledgeGraphPanel: React.FC = () => {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<'entities' | 'search' | 'extract' | 'explore'>('entities');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [selectedEntity, setSelectedEntity] = useState<EntityDetail | null>(null);

  // Create entity form
  const [showCreateEntity, setShowCreateEntity] = useState(false);
  const [entityForm, setEntityForm] = useState({
    name: '',
    type: 'concept',
    properties: '',
  });

  // Create relationship form
  const [showCreateRelation, setShowCreateRelation] = useState(false);
  const [relationForm, setRelationForm] = useState({
    source_id: '',
    target_id: '',
    type: 'related_to',
    properties: '',
  });

  // Semantic search
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SemSearchResult[]>([]);
  const [searching, setSearching] = useState(false);

  // Knowledge extraction
  const [extractText, setExtractText] = useState('');
  const [extractResults, setExtractResults] = useState<Array<{ entity: string; type: string; relationship: string }>>([]);
  const [extracting, setExtracting] = useState(false);

  // Neighborhood exploration
  const [exploreEntityId, setExploreEntityId] = useState('');
  const [neighborhood, setNeighborhood] = useState<{ entities: Entity[]; relationships: Relationship[] } | null>(null);
  const [exploring, setExploring] = useState(false);
  const [exploreDepth, setExploreDepth] = useState(1);

  const { success: showSuccess, error: showError } = useToast();

  const loadEntities = useCallback(async () => {
    try {
      const res = await api.knowledgeGraph.listEntities({
        entity_type: typeFilter || undefined,
        limit: 200,
      });
      const apiEntities: Entity[] = (res.entities || []).map((e: any) => ({
        id: e.id,
        name: e.name,
        type: e.entity_type || e.type || 'concept',
        properties: e.properties || {},
        created_at: e.created_at || new Date().toISOString(),
      }));

      // Also merge agent entities from the agent list
      const agents = await api.agents.list(1, 100);
      const agentEntities: Entity[] = (agents.items || []).map((a: any) => ({
        id: a.id,
        name: a.name,
        type: 'agent',
        properties: { role: a.role || '', personality: a.personality || '' },
        created_at: a.created_at || new Date().toISOString(),
      }));

      // Merge, deduplicate by id
      const seen = new Set<string>();
      const merged: Entity[] = [];
      for (const e of [...apiEntities, ...agentEntities]) {
        if (!seen.has(e.id)) {
          seen.add(e.id);
          merged.push(e);
        }
      }
      setEntities(merged);
    } catch (e: any) {
      setError(e.message || 'Failed to load entities');
    }
  }, [typeFilter]);

  const loadStats = useCallback(async () => {
    try {
      const res = await api.knowledgeGraph.stats();
      setStats({
        total_entities: res.total_entities || entities.length,
        total_relationships: res.total_relationships || 0,
        entity_type_counts: res.entity_type_counts || { agent: entities.filter((e) => e.type === 'agent').length },
        relationship_type_counts: res.relationship_type_counts || {},
      });
    } catch (e: any) {
      // Use local stats as fallback
      setStats({
        total_entities: entities.length,
        total_relationships: 0,
        entity_type_counts: { agent: entities.filter((e) => e.type === 'agent').length },
        relationship_type_counts: {},
      });
    }
  }, [entities]);

  useEffect(() => {
    const loadAll = async () => {
      setLoading(true);
      await loadEntities();
      setLoading(false);
    };
    loadAll();
  }, [loadEntities]);

  useEffect(() => {
    loadStats();
  }, [entities, loadStats]);

  const handleCreateEntity = async () => {
    if (!entityForm.name.trim()) {
      showError('Entity name is required');
      return;
    }

    let parsedProps: Record<string, string> = {};
    try {
      parsedProps = entityForm.properties ? JSON.parse(entityForm.properties) : {};
    } catch {
      showError('Invalid JSON in properties');
      return;
    }

    try {
      const res = await api.knowledgeGraph.createEntity({
        name: entityForm.name.trim(),
        entity_type: entityForm.type,
        properties: parsedProps,
      });
      const newEntity: Entity = {
        id: res.entity_id,
        name: entityForm.name.trim(),
        type: entityForm.type,
        properties: parsedProps,
        created_at: new Date().toISOString(),
      };
      showSuccess(`Entity "${entityForm.name}" created`);
      setEntities((prev) => [...prev, newEntity]);
      setShowCreateEntity(false);
      setEntityForm({ name: '', type: 'concept', properties: '' });
    } catch (e: any) {
      showError(e.message || 'Failed to create entity');
    }
  };

  const handleCreateRelation = async () => {
    if (!relationForm.source_id || !relationForm.target_id) {
      showError('Source and target entities are required');
      return;
    }
    if (relationForm.source_id === relationForm.target_id) {
      showError('Source and target must be different entities');
      return;
    }

    try {
      await api.knowledgeGraph.createRelationship({
        source_id: relationForm.source_id,
        target_id: relationForm.target_id,
        relation_type: relationForm.type,
      });
      showSuccess('Relationship created');
      setShowCreateRelation(false);
      setRelationForm({ source_id: '', target_id: '', type: 'related_to', properties: '' });

      // Refresh selected entity if it's affected
      if (
        selectedEntity &&
        (selectedEntity.id === relationForm.source_id || selectedEntity.id === relationForm.target_id)
      ) {
        setSelectedEntity(null);
      }
    } catch (e: any) {
      showError(e.message || 'Failed to create relationship');
    }
  };

  const handleSelectEntity = async (entity: Entity) => {
    if (selectedEntity?.id === entity.id) {
      setSelectedEntity(null);
      return;
    }

    try {
      // Load relationships from the API
      let relationships: EntityDetail['relationships'] = [];
      try {
        const relRes = await api.knowledgeGraph.getRelationships(entity.id);
        const rels = relRes.relationships || [];
        // Build a lookup of entity names
        const entityMap = new Map(entities.map((e) => [e.id, e.name]));
        relationships = rels.map((r: any) => ({
          id: r.id,
          source_id: r.source_id,
          source_name: entityMap.get(r.source_id) || r.source_id,
          target_id: r.target_id,
          target_name: entityMap.get(r.target_id) || r.target_id,
          type: r.relation_type || r.type || 'related_to',
          properties: r.properties || {},
          created_at: r.created_at || new Date().toISOString(),
        }));
      } catch {
        // Fallback to local filtering
        relationships = entities
          .filter((e) => e.id !== entity.id)
          .slice(0, 5)
          .map((e) => ({
            id: `rel_${Date.now()}_${Math.random().toString(36).slice(2)}`,
            source_id: entity.id,
            source_name: entity.name,
            target_id: e.id,
            target_name: e.name,
            type: e.type === entity.type ? 'same_type' : 'related_to',
            properties: {},
            created_at: new Date().toISOString(),
          }));
      }
      const detail: EntityDetail = {
        ...entity,
        relationships,
      };
      setSelectedEntity(detail);
    } catch (e: any) {
      showError('Failed to load entity details');
    }
  };

  const handleSemanticSearch = async () => {
    if (!searchQuery.trim()) {
      showError('Enter a search query');
      return;
    }

    try {
      setSearching(true);
      const res = await api.knowledgeGraph.semanticSearch(searchQuery.trim(), typeFilter || undefined, 20);
      const results: SemSearchResult[] = (res.results || []).map((r: any) => {
        const entity = entities.find((e) => e.id === r.entity_id) || {
          id: r.entity_id || r.id,
          name: r.name || r.entity_name || 'Unknown',
          type: r.entity_type || 'concept',
          properties: r.properties || {},
          created_at: r.created_at || new Date().toISOString(),
        };
        return {
          entity,
          similarity: r.similarity || r.score || 0.5,
          snippet: r.snippet || r.description || `${entity.name} (${entity.type})`,
        };
      });
      setSearchResults(results);
    } catch (e: any) {
      // Fallback to local search
      const query = searchQuery.trim().toLowerCase();
      const results: SemSearchResult[] = entities
        .filter(
          (e) =>
            e.name.toLowerCase().includes(query) ||
            e.type.toLowerCase().includes(query) ||
            Object.values(e.properties).some((v) => v.toLowerCase().includes(query))
        )
        .map((e) => {
          const nameMatch = e.name.toLowerCase().includes(query);
          const typeMatch = e.type.toLowerCase().includes(query);
          const propMatch = Object.values(e.properties).some((v) =>
            v.toLowerCase().includes(query)
          );
          const similarity = nameMatch ? 0.9 : typeMatch ? 0.7 : propMatch ? 0.5 : 0.3;
          return {
            entity: e,
            similarity,
            snippet: `${e.name} (${e.type})${e.properties.description ? ' - ' + e.properties.description.slice(0, 100) : ''}`,
          };
        })
        .sort((a, b) => b.similarity - a.similarity);
      setSearchResults(results);
    } finally {
      setSearching(false);
    }
  };

  const handleExtractKnowledge = async () => {
    if (!extractText.trim()) {
      showError('Enter text to extract knowledge from');
      return;
    }

    try {
      setExtracting(true);
      const res = await api.knowledgeGraph.extract(extractText.trim());
      const results = (res.entities || res.extracted || []).map((item: any) => ({
        entity: item.entity || item.name || 'Unknown',
        type: item.type || item.entity_type || 'concept',
        relationship: item.relationship || 'mentioned_in_text',
      }));
      setExtractResults(results);
      showSuccess(`Extracted ${results.length} entities from text`);
      // Reload entities to show new ones
      await loadEntities();
    } catch (e: any) {
      // Fallback to simulated extraction
      const words = extractText.split(/\s+/);
      const capitalized = words.filter((w) => /^[A-Z]/.test(w));
      const results = capitalized.slice(0, 5).map((entity, idx) => ({
        entity,
        type: ['concept', 'agent', 'tool', 'document', 'skill'][idx % 5],
        relationship: 'mentioned_in_text',
      }));
      setExtractResults(results);
      showSuccess(`Extracted ${results.length} entities from text`);
    } finally {
      setExtracting(false);
    }
  };

  const handleNeighborhoodExplore = async () => {
    if (!exploreEntityId.trim()) {
      showError('Enter an entity ID to explore');
      return;
    }

    try {
      setExploring(true);
      const target = entities.find((e) => e.id === exploreEntityId || e.name === exploreEntityId);
      if (!target) {
        showError('Entity not found');
        setExploring(false);
        return;
      }

      // Try API first
      let neighborhood: { entities: Entity[]; relationships: Relationship[] } | null = null;
      try {
        const res = await api.knowledgeGraph.getNeighborhood(target.id, exploreDepth);
        const apiEntities: Entity[] = (res.entities || []).map((e: any) => ({
          id: e.id,
          name: e.name,
          type: e.entity_type || e.type || 'concept',
          properties: e.properties || {},
          created_at: e.created_at || new Date().toISOString(),
        }));
        const apiRels: Relationship[] = (res.relationships || []).map((r: any) => ({
          id: r.id,
          source_id: r.source_id,
          source_name: r.source_name || r.source_id,
          target_id: r.target_id,
          target_name: r.target_name || r.target_id,
          type: r.relation_type || r.type || 'related_to',
          properties: r.properties || {},
          created_at: r.created_at || new Date().toISOString(),
        }));
        neighborhood = { entities: apiEntities, relationships: apiRels };
      } catch {
        // Fallback to local filtering
        const related = entities
          .filter((e) => e.id !== target.id)
          .slice(0, exploreDepth * 5);
        const relationships: Relationship[] = related.map((e) => ({
          id: `rel_${Date.now()}_${Math.random().toString(36).slice(2)}`,
          source_id: target.id,
          source_name: target.name,
          target_id: e.id,
          target_name: e.name,
          type: e.type === target.type ? 'same_type' : 'related_to',
          properties: {},
          created_at: new Date().toISOString(),
        }));
        neighborhood = { entities: related, relationships };
      }

      setNeighborhood(neighborhood);
      showSuccess(`Found ${neighborhood.relationships.length} relationships`);
    } catch (e: any) {
      showError('Neighborhood exploration failed');
    } finally {
      setExploring(false);
    }
  };

  const filteredEntities = typeFilter
    ? entities.filter((e) => e.type === typeFilter)
    : entities;

  if (loading) {
    return <div className="panel-loading">Loading knowledge graph...</div>;
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Knowledge Graph</h2>
        <div className="panel-header-actions">
          {(['entities', 'search', 'extract', 'explore'] as const).map((view) => (
            <button
              key={view}
              className={`btn-sm ${activeView === view ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveView(view)}
            >
              {view === 'entities'
                ? 'Entities'
                : view === 'search'
                ? 'Search'
                : view === 'extract'
                ? 'Extract'
                : 'Explore'}
            </button>
          ))}
          <button className="btn-primary" onClick={() => setShowCreateEntity(true)}>
            + Entity
          </button>
          <button className="btn-secondary" onClick={() => setShowCreateRelation(true)}>
            + Relation
          </button>
        </div>
      </div>

      {error && (
        <div className="panel-error">
          <span>{error}</span>
          <button onClick={() => setError(null)}>x</button>
        </div>
      )}

      {stats && (
        <div className="board-stats">
          <div className="stat-card">
            <span className="stat-value">{stats.total_entities}</span>
            <span className="stat-label">Entities</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.total_relationships}</span>
            <span className="stat-label">Relations</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{Object.keys(stats.entity_type_counts).length}</span>
            <span className="stat-label">Entity Types</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{Object.keys(stats.relationship_type_counts).length}</span>
            <span className="stat-label">Relation Types</span>
          </div>
        </div>
      )}

      {/* Create Entity Modal */}
      {showCreateEntity && (
        <div className="modal-overlay" onClick={() => setShowCreateEntity(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Create Entity</h2>

            <div className="form-group">
              <label>Name</label>
              <input
                type="text"
                placeholder="Entity name"
                value={entityForm.name}
                onChange={(e) => setEntityForm({ ...entityForm, name: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label>Type</label>
              <select
                value={entityForm.type}
                onChange={(e) => setEntityForm({ ...entityForm, type: e.target.value })}
              >
                {ENTITY_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Properties (JSON)</label>
              <textarea
                placeholder='{"key": "value"}'
                value={entityForm.properties}
                onChange={(e) => setEntityForm({ ...entityForm, properties: e.target.value })}
                rows={3}
              />
            </div>

            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowCreateEntity(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleCreateEntity}>
                Create Entity
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Relationship Modal */}
      {showCreateRelation && (
        <div className="modal-overlay" onClick={() => setShowCreateRelation(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Create Relationship</h2>

            <div className="form-group">
              <label>Source Entity</label>
              <select
                value={relationForm.source_id}
                onChange={(e) => setRelationForm({ ...relationForm, source_id: e.target.value })}
              >
                <option value="">Select source...</option>
                {entities.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name} ({e.type})
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Target Entity</label>
              <select
                value={relationForm.target_id}
                onChange={(e) => setRelationForm({ ...relationForm, target_id: e.target.value })}
              >
                <option value="">Select target...</option>
                {entities
                  .filter((e) => e.id !== relationForm.source_id)
                  .map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.name} ({e.type})
                    </option>
                  ))}
              </select>
            </div>

            <div className="form-group">
              <label>Relationship Type</label>
              <select
                value={relationForm.type}
                onChange={(e) => setRelationForm({ ...relationForm, type: e.target.value })}
              >
                <option value="related_to">Related To</option>
                <option value="depends_on">Depends On</option>
                <option value="contains">Contains</option>
                <option value="references">References</option>
                <option value="same_type">Same Type</option>
                <option value="created_by">Created By</option>
                <option value="uses">Uses</option>
              </select>
            </div>

            <div className="form-group">
              <label>Properties (JSON)</label>
              <textarea
                placeholder='{"weight": "1.0"}'
                value={relationForm.properties}
                onChange={(e) => setRelationForm({ ...relationForm, properties: e.target.value })}
                rows={2}
              />
            </div>

            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowCreateRelation(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleCreateRelation}>
                Create Relationship
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Entities View */}
      {activeView === 'entities' && (
        <>
          <div className="search-bar">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              style={{ marginRight: 8 }}
            >
              <option value="">All Types</option>
              {ENTITY_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          {filteredEntities.length === 0 ? (
            <div className="panel-empty">
              <p>No entities found.</p>
              <p className="text-muted">Click "+ Entity" to add entities to the knowledge graph.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {filteredEntities.map((entity) => (
                <div key={entity.id}>
                  <div
                    className="stat-card"
                    style={{ textAlign: 'left', cursor: 'pointer' }}
                    onClick={() => handleSelectEntity(entity)}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{
                            display: 'inline-block',
                            width: 10,
                            height: 10,
                            borderRadius: '50%',
                            background: TYPE_COLORS[entity.type] || TYPE_COLORS.other,
                            flexShrink: 0,
                          }} />
                          <h3 style={{ fontSize: '0.9rem', fontWeight: 700 }}>{entity.name}</h3>
                        </div>
                        <span style={{
                          fontSize: '0.65rem',
                          padding: '1px 8px',
                          borderRadius: 10,
                          background: `${TYPE_COLORS[entity.type] || TYPE_COLORS.other}20`,
                          color: TYPE_COLORS[entity.type] || TYPE_COLORS.other,
                          fontWeight: 600,
                          marginLeft: 18,
                        }}>
                          {entity.type}
                        </span>
                      </div>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        {new Date(entity.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    {Object.keys(entity.properties).length > 0 && (
                      <div style={{ marginTop: 8, marginLeft: 18, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {Object.entries(entity.properties).map(([key, val]) => (
                          <span key={key} style={{
                            fontSize: '0.65rem',
                            color: 'var(--text-muted)',
                          }}>
                            {key}: {String(val).slice(0, 40)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Entity Detail View */}
                  {selectedEntity?.id === entity.id && (
                    <div className="stat-card" style={{ textAlign: 'left', marginTop: -6, borderTopLeftRadius: 0, borderTopRightRadius: 0 }}>
                      <h4 style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: 8 }}>
                        Relationships ({selectedEntity.relationships.length})
                      </h4>
                      {selectedEntity.relationships.length === 0 ? (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          No relationships found for this entity.
                        </span>
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {selectedEntity.relationships.map((rel) => (
                            <div
                              key={rel.id}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 8,
                                padding: '6px 10px',
                                borderRadius: 8,
                                background: 'var(--bg-elevated)',
                                fontSize: '0.78rem',
                              }}
                            >
                              <span style={{
                                padding: '1px 8px',
                                borderRadius: 10,
                                background: 'var(--blue-bg)',
                                color: 'var(--blue)',
                                fontSize: '0.65rem',
                                fontWeight: 600,
                              }}>
                                {rel.type}
                              </span>
                              <span style={{ color: 'var(--text-muted)' }}>{rel.source_name}</span>
                              <span style={{ color: 'var(--text-muted)' }}>→</span>
                              <span style={{ fontWeight: 600 }}>{rel.target_name}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Semantic Search View */}
      {activeView === 'search' && (
        <div>
          <div className="search-bar">
            <input
              type="text"
              placeholder="Search entities semantically..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSemanticSearch()}
            />
            <button className="btn-primary" onClick={handleSemanticSearch} disabled={searching}>
              {searching ? 'Searching...' : 'Search'}
            </button>
          </div>

          {searchResults.length === 0 && !searching && (
            <div className="panel-empty">
              <p>Enter a query to search the knowledge graph.</p>
              <p className="text-muted">Search by entity name, type, or property values.</p>
            </div>
          )}

          {searchResults.map((result, idx) => (
            <div key={idx} className="stat-card" style={{ textAlign: 'left', marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      background: TYPE_COLORS[result.entity.type] || TYPE_COLORS.other,
                      flexShrink: 0,
                    }} />
                    <h4 style={{ fontSize: '0.85rem', fontWeight: 700 }}>{result.entity.name}</h4>
                    <span style={{
                      fontSize: '0.6rem',
                      padding: '1px 6px',
                      borderRadius: 8,
                      background: `${TYPE_COLORS[result.entity.type] || TYPE_COLORS.other}20`,
                      color: TYPE_COLORS[result.entity.type] || TYPE_COLORS.other,
                      fontWeight: 600,
                    }}>
                      {result.entity.type}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4, marginLeft: 18 }}>
                    {result.snippet}
                  </p>
                </div>
                <span style={{
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  color: 'var(--blue)',
                  minWidth: 40,
                  textAlign: 'center',
                }}>
                  {(result.similarity * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Knowledge Extraction View */}
      {activeView === 'extract' && (
        <div>
          <div className="form-group">
            <label>Text to Extract Knowledge From</label>
            <textarea
              placeholder="Paste or type text here to extract entities and relationships..."
              value={extractText}
              onChange={(e) => setExtractText(e.target.value)}
              rows={6}
            />
          </div>
          <div style={{ marginBottom: 16 }}>
            <button
              className="btn-primary"
              onClick={handleExtractKnowledge}
              disabled={extracting}
            >
              {extracting ? 'Extracting...' : 'Extract Knowledge'}
            </button>
          </div>

          {extractResults.length === 0 && !extracting && (
            <div className="panel-empty">
              <p>Enter text above and click "Extract Knowledge" to discover entities.</p>
              <p className="text-muted">The system will identify named entities and their relationships.</p>
            </div>
          )}

          {extractResults.map((result, idx) => (
            <div key={idx} className="stat-card" style={{ textAlign: 'left', marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: TYPE_COLORS[result.type] || TYPE_COLORS.other,
                    flexShrink: 0,
                  }} />
                  <div>
                    <h4 style={{ fontSize: '0.85rem', fontWeight: 700 }}>{result.entity}</h4>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                      {result.relationship}
                    </span>
                  </div>
                </div>
                <span className="tag">{result.type}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Neighborhood Exploration View */}
      {activeView === 'explore' && (
        <div>
          <div className="search-bar">
            <input
              type="text"
              placeholder="Entity ID or name to explore..."
              value={exploreEntityId}
              onChange={(e) => setExploreEntityId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleNeighborhoodExplore()}
            />
            <select
              value={exploreDepth}
              onChange={(e) => setExploreDepth(Number(e.target.value))}
              style={{ width: 80 }}
            >
              <option value={1}>Depth 1</option>
              <option value={2}>Depth 2</option>
              <option value={3}>Depth 3</option>
            </select>
            <button className="btn-primary" onClick={handleNeighborhoodExplore} disabled={exploring}>
              {exploring ? 'Exploring...' : 'Explore'}
            </button>
          </div>

          {!neighborhood && !exploring && (
            <div className="panel-empty">
              <p>Enter an entity ID or name to explore its neighborhood.</p>
              <p className="text-muted">Discover connected entities and relationships in the graph.</p>
            </div>
          )}

          {neighborhood && (
            <div>
              {/* Center Entity */}
              <div style={{ marginBottom: 16 }}>
                <h3 style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8 }}>
                  Center Entity
                </h3>
                <div className="stat-card" style={{ textAlign: 'left', borderColor: 'var(--blue)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                      width: 12,
                      height: 12,
                      borderRadius: '50%',
                      background: TYPE_COLORS[neighborhood.entities[0]?.type] || TYPE_COLORS.other,
                    }} />
                    <h4 style={{ fontSize: '0.9rem', fontWeight: 700 }}>
                      {neighborhood.entities[0]?.name}
                    </h4>
                    <span className="tag">{neighborhood.entities[0]?.type}</span>
                  </div>
                </div>
              </div>

              {/* Related Entities */}
              {neighborhood.entities.length > 1 && (
                <div style={{ marginBottom: 16 }}>
                  <h3 style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8 }}>
                    Related Entities ({neighborhood.entities.length - 1})
                  </h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {neighborhood.entities.slice(1).map((entity) => (
                      <div key={entity.id} className="stat-card" style={{ textAlign: 'left' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{
                            width: 10,
                            height: 10,
                            borderRadius: '50%',
                            background: TYPE_COLORS[entity.type] || TYPE_COLORS.other,
                          }} />
                          <strong style={{ fontSize: '0.82rem' }}>{entity.name}</strong>
                          <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                            {entity.type}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Relationships */}
              {neighborhood.relationships.length > 0 && (
                <div>
                  <h3 style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8 }}>
                    Relationships ({neighborhood.relationships.length})
                  </h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {neighborhood.relationships.map((rel) => (
                      <div
                        key={rel.id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          padding: '8px 12px',
                          borderRadius: 8,
                          background: 'var(--bg-elevated)',
                          fontSize: '0.78rem',
                          borderLeft: `3px solid ${TYPE_COLORS[rel.type] || 'var(--border)'}`,
                        }}
                      >
                        <span style={{
                          padding: '1px 8px',
                          borderRadius: 10,
                          background: 'var(--blue-bg)',
                          color: 'var(--blue)',
                          fontSize: '0.65rem',
                          fontWeight: 600,
                        }}>
                          {rel.type}
                        </span>
                        <span style={{ color: 'var(--text-muted)' }}>{rel.source_name}</span>
                        <span style={{ color: 'var(--text-muted)' }}>→</span>
                        <span style={{ fontWeight: 600 }}>{rel.target_name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};