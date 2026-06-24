import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// ── Types ──

interface KnowledgeFabricStats {
  total_nodes: number;
  total_edges: number;
  total_clusters: number;
  total_queries: number;
  nodes_by_domain: Record<string, number>;
  nodes_by_type: Record<string, number>;
  total_tags: number;
  avg_confidence: number;
}

interface KnowledgeNode {
  node_id: string;
  title: string;
  summary: string;
  content?: string;
  domain: string;
  knowledge_type: string;
  confidence: number;
  importance?: number;
  tags: string[];
  source?: string;
  created_at?: string;
}

interface QueryResult {
  query_id: string;
  total_matches: number;
  query_time_ms: number;
  nodes: KnowledgeNode[];
  suggested_related: string[];
}

interface GraphNode {
  id: string;
  title: string;
  domain: string;
  type: string;
  confidence: number;
  importance: number;
  tags: string[];
  summary: string;
  content?: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  color: string;
  relatedIds: string[];
}

interface GraphEdge {
  id: string;
  sourceId: string;
  targetId: string;
  strength: number;
  type: string;
}

interface KnowledgeGraphVizProps {
  onNavigate?: (tab: string) => void;
  onSelectNode?: (nodeId: string) => void;
}

// ── Constants ──

const DOMAIN_COLORS: Record<string, string> = {
  ai_ml: '#4f6ef7',
  software_engineering: '#22c55e',
  data_science: '#f59e0b',
  security: '#ef4444',
  design: '#a855f7',
  general: '#6b7280',
};

const DEFAULT_DOMAIN_COLOR = '#6b7280';

const NODE_MIN_RADIUS = 14;
const NODE_MAX_RADIUS = 36;
const EDGE_MIN_WIDTH = 0.5;
const EDGE_MAX_WIDTH = 3;

type LayoutMode = 'force-directed' | 'radial' | 'grid';

const ALL_DOMAINS = [
  'ai_ml',
  'software_engineering',
  'data_science',
  'security',
  'design',
  'general',
];

function getDomainColor(domain: string): string {
  return DOMAIN_COLORS[domain] || DEFAULT_DOMAIN_COLOR;
}

function getNodeRadius(confidence: number, importance: number): number {
  const avg = (confidence + importance) / 2;
  return NODE_MIN_RADIUS + avg * (NODE_MAX_RADIUS - NODE_MIN_RADIUS);
}

function getEdgeWidth(strength: number): number {
  return EDGE_MIN_WIDTH + strength * (EDGE_MAX_WIDTH - EDGE_MIN_WIDTH);
}

// ── Force-directed layout ──

function applyForceLayout(
  nodes: GraphNode[],
  edges: GraphEdge[],
  width: number,
  height: number
): void {
  const repulsion = 8000;
  const attraction = 0.002;
  const damping = 0.85;
  const centerX = width / 2;
  const centerY = height / 2;
  const centerGravity = 0.001;

  const nodeMap = new Map<string, GraphNode>();
  for (const n of nodes) nodeMap.set(n.id, n);

  for (const node of nodes) {
    let fx = 0;
    let fy = 0;

    // Repulsion between all node pairs
    for (const other of nodes) {
      if (other.id === node.id) continue;
      let dx = node.x - other.x;
      let dy = node.y - other.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = repulsion / (dist * dist);
      fx += (dx / dist) * force;
      fy += (dy / dist) * force;
    }

    // Attraction along edges
    for (const edge of edges) {
      let otherId: string | null = null;
      if (edge.sourceId === node.id) otherId = edge.targetId;
      if (edge.targetId === node.id) otherId = edge.sourceId;
      if (!otherId) continue;
      const other = nodeMap.get(otherId);
      if (!other) continue;
      let dx = other.x - node.x;
      let dy = other.y - node.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = dist * attraction * edge.strength;
      fx += dx * force;
      fy += dy * force;
    }

    // Center gravity
    fx += (centerX - node.x) * centerGravity;
    fy += (centerY - node.y) * centerGravity;

    // Apply velocity with damping
    node.vx = (node.vx + fx) * damping;
    node.vy = (node.vy + fy) * damping;

    node.x += node.vx;
    node.y += node.vy;

    // Clamp to bounds
    node.x = Math.max(node.radius, Math.min(width - node.radius, node.x));
    node.y = Math.max(node.radius, Math.min(height - node.radius, node.y));
  }
}

// ── Radial layout ──

function applyRadialLayout(nodes: GraphNode[], width: number, height: number): void {
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) * 0.38;
  const count = nodes.length;

  nodes.forEach((node, i) => {
    if (i === 0) {
      node.x = centerX;
      node.y = centerY;
    } else {
      const angle = (2 * Math.PI * (i - 1)) / (count - 1);
      node.x = centerX + radius * Math.cos(angle);
      node.y = centerY + radius * Math.sin(angle);
    }
    node.vx = 0;
    node.vy = 0;
  });
}

// ── Grid layout ──

function applyGridLayout(nodes: GraphNode[], width: number, height: number): void {
  const cols = Math.ceil(Math.sqrt(nodes.length));
  const cellW = width / (cols + 1);
  const cellH = height / (Math.ceil(nodes.length / cols) + 1);

  nodes.forEach((node, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    node.x = (col + 1) * cellW;
    node.y = (row + 1) * cellH;
    node.vx = 0;
    node.vy = 0;
  });
}

// ── Build edges from related data ──

function buildEdges(nodes: GraphNode[], relatedMap: Map<string, string[]>): GraphEdge[] {
  const edges: GraphEdge[] = [];
  const seen = new Set<string>();

  for (const node of nodes) {
    const related = relatedMap.get(node.id) || [];
    for (const relatedId of related) {
      const pairKey = [node.id, relatedId].sort().join('::');
      if (seen.has(pairKey)) continue;
      seen.add(pairKey);

      const target = nodes.find((n) => n.id === relatedId);
      let strength = 0.5;
      if (target && target.domain === node.domain) strength = 0.8;
      if (target && target.type === node.type) strength += 0.1;

      edges.push({
        id: `edge_${node.id}_${relatedId}`,
        sourceId: node.id,
        targetId: relatedId,
        strength: Math.min(strength, 1),
        type: 'related',
      });
    }
  }

  return edges;
}

// ── Arrow drawing helper ──

function drawArrow(
  ctx: CanvasRenderingContext2D,
  fromX: number,
  fromY: number,
  toX: number,
  toY: number,
  color: string,
  width: number,
  alpha: number
): void {
  const headLen = 8;
  const angle = Math.atan2(toY - fromY, toX - fromX);

  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.globalAlpha = alpha;
  ctx.beginPath();
  ctx.moveTo(fromX, fromY);
  ctx.lineTo(toX, toY);
  ctx.stroke();

  // Arrow head
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(toX, toY);
  ctx.lineTo(
    toX - headLen * Math.cos(angle - Math.PI / 6),
    toY - headLen * Math.sin(angle - Math.PI / 6)
  );
  ctx.lineTo(
    toX - headLen * Math.cos(angle + Math.PI / 6),
    toY - headLen * Math.sin(angle + Math.PI / 6)
  );
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

// ── Styles ──

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'relative',
    width: '100%',
    height: '100%',
    minHeight: 600,
    background: '#1a1a2e',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    borderRadius: 12,
    border: '1px solid rgba(255,255,255,0.06)',
  },
  controlBar: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '10px 14px',
    background: '#16213e',
    borderBottom: '1px solid rgba(255,255,255,0.08)',
    flexWrap: 'wrap',
    minHeight: 48,
    zIndex: 10,
  },
  searchInput: {
    padding: '6px 12px',
    borderRadius: 8,
    border: '1px solid rgba(255,255,255,0.12)',
    background: '#1a1a2e',
    color: '#e0e0e0',
    fontSize: '0.8rem',
    outline: 'none',
    width: 180,
    flexShrink: 0,
  },
  domainFilter: {
    position: 'relative' as const,
    flexShrink: 0,
  },
  domainFilterBtn: {
    padding: '6px 12px',
    borderRadius: 8,
    border: '1px solid rgba(255,255,255,0.12)',
    background: '#1a1a2e',
    color: '#e0e0e0',
    fontSize: '0.78rem',
    cursor: 'pointer',
    whiteSpace: 'nowrap' as const,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  domainDropdown: {
    position: 'absolute' as const,
    top: '100%',
    left: 0,
    marginTop: 4,
    background: '#16213e',
    border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 8,
    padding: '6px 0',
    zIndex: 100,
    minWidth: 200,
    boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
  },
  domainOption: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '6px 14px',
    cursor: 'pointer',
    fontSize: '0.78rem',
    color: '#ccc',
    transition: 'background 0.15s',
  },
  layoutBtns: {
    display: 'flex',
    gap: 2,
    flexShrink: 0,
  },
  zoomBtn: {
    padding: '5px 10px',
    borderRadius: 6,
    border: '1px solid rgba(255,255,255,0.08)',
    background: 'transparent',
    color: '#ccc',
    fontSize: '0.78rem',
    cursor: 'pointer',
    minWidth: 28,
    textAlign: 'center' as const,
  },
  statsBar: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
    marginLeft: 'auto',
    flexShrink: 0,
  },
  statItem: {
    fontSize: '0.7rem',
    color: '#888',
    whiteSpace: 'nowrap' as const,
  },
  statValue: {
    color: '#ccc',
    fontWeight: 600,
  },
  canvasWrapper: {
    flex: 1,
    position: 'relative' as const,
    overflow: 'hidden',
    cursor: 'grab',
  },
  canvas: {
    display: 'block',
    width: '100%',
    height: '100%',
  },
  detailPanel: {
    position: 'absolute' as const,
    top: 12,
    right: 12,
    width: 300,
    maxHeight: 'calc(100% - 24px)',
    background: '#16213e',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 12,
    padding: 16,
    zIndex: 20,
    overflowY: 'auto' as const,
    boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
    animation: 'slideIn 0.2s ease-out',
  },
  detailTitle: {
    fontSize: '0.95rem',
    fontWeight: 700,
    color: '#fff',
    marginBottom: 4,
    wordBreak: 'break-word' as const,
  },
  detailDomain: {
    fontSize: '0.7rem',
    padding: '2px 8px',
    borderRadius: 10,
    display: 'inline-block',
    fontWeight: 600,
    marginBottom: 10,
  },
  detailType: {
    fontSize: '0.7rem',
    padding: '2px 8px',
    borderRadius: 10,
    display: 'inline-block',
    fontWeight: 600,
    marginLeft: 6,
    marginBottom: 10,
    background: 'rgba(255,255,255,0.06)',
    color: '#aaa',
  },
  confidenceBar: {
    marginBottom: 12,
  },
  confidenceLabel: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.7rem',
    color: '#999',
    marginBottom: 4,
  },
  confidenceTrack: {
    height: 4,
    borderRadius: 2,
    background: 'rgba(255,255,255,0.08)',
    overflow: 'hidden',
  },
  tagsRow: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: 4,
    marginBottom: 12,
  },
  tagChip: {
    fontSize: '0.65rem',
    padding: '2px 8px',
    borderRadius: 10,
    background: 'rgba(255,255,255,0.06)',
    color: '#aaa',
  },
  detailSummary: {
    fontSize: '0.75rem',
    color: '#aaa',
    lineHeight: 1.5,
    marginBottom: 12,
    maxHeight: 80,
    overflow: 'hidden',
  },
  relatedList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 4,
    marginBottom: 12,
  },
  relatedItem: {
    fontSize: '0.72rem',
    color: '#bbb',
    padding: '6px 10px',
    borderRadius: 6,
    background: 'rgba(255,255,255,0.04)',
    cursor: 'pointer',
    border: '1px solid transparent',
    transition: 'border-color 0.15s',
  },
  viewDetailsBtn: {
    width: '100%',
    padding: '8px 0',
    borderRadius: 8,
    border: 'none',
    background: '#0f3460',
    color: '#fff',
    fontSize: '0.78rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background 0.2s',
  },
  emptyState: {
    position: 'absolute' as const,
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    textAlign: 'center' as const,
    color: '#666',
    fontSize: '0.9rem',
    pointerEvents: 'none' as const,
  },
  loadingOverlay: {
    position: 'absolute' as const,
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    color: '#888',
    fontSize: '0.85rem',
  },
};

// ── Dynamic style helpers ──

function domainDotStyle(color: string): React.CSSProperties {
  return {
    width: 10,
    height: 10,
    borderRadius: '50%',
    background: color,
    flexShrink: 0,
  };
}

function layoutBtnStyle(active: boolean): React.CSSProperties {
  return {
    padding: '5px 10px',
    borderRadius: 6,
    border: '1px solid rgba(255,255,255,0.08)',
    background: active ? '#0f3460' : 'transparent',
    color: active ? '#fff' : '#999',
    fontSize: '0.72rem',
    cursor: 'pointer',
    fontWeight: active ? 600 : 400,
  };
}

function confidenceFillStyle(pct: number, color: string): React.CSSProperties {
  return {
    height: '100%',
    width: `${pct}%`,
    background: color,
    borderRadius: 2,
    transition: 'width 0.3s ease',
  };
}

// ── Component ──

export const KnowledgeGraphViz: React.FC<KnowledgeGraphVizProps> = ({
  onNavigate,
  onSelectNode,
}) => {
  const { error: showError } = useToast();

  // Data state
  const [stats, setStats] = useState<KnowledgeFabricStats | null>(null);
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [graphEdges, setGraphEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(true);

  // UI state
  const [searchQuery, setSearchQuery] = useState('');
  const [domainFilters, setDomainFilters] = useState<Set<string>>(new Set(ALL_DOMAINS));
  const [showDomainDropdown, setShowDomainDropdown] = useState(false);
  const [layoutMode, setLayoutMode] = useState<LayoutMode>('force-directed');
  const [zoom, setZoom] = useState(1);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<Set<string>>(new Set());

  // Canvas & interaction refs
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const animFrameRef = useRef<number>(0);
  const nodesRef = useRef<GraphNode[]>([]);
  const edgesRef = useRef<GraphEdge[]>([]);
  const zoomRef = useRef(1);
  const panRef = useRef({ x: 0, y: 0 });
  const dragRef = useRef<{
    type: 'node' | 'canvas';
    nodeId?: string;
    startX: number;
    startY: number;
    nodeStartX?: number;
    nodeStartY?: number;
  } | null>(null);
  const doubleClickTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep refs in sync
  useEffect(() => {
    nodesRef.current = graphNodes;
  }, [graphNodes]);

  useEffect(() => {
    edgesRef.current = graphEdges;
  }, [graphEdges]);

  useEffect(() => {
    zoomRef.current = zoom;
  }, [zoom]);

  // ── Data fetching ──

  const fetchData = useCallback(async () => {
    try {
      // Fetch stats
      try {
        const statsRes = await api.knowledgeGraph.stats();
        setStats({
          total_nodes: statsRes.total_entities || statsRes.total_nodes || 0,
          total_edges: statsRes.total_relationships || statsRes.total_edges || 0,
          total_clusters: statsRes.total_clusters || 0,
          total_queries: statsRes.total_queries || 0,
          nodes_by_domain: statsRes.entity_type_counts || statsRes.nodes_by_domain || {},
          nodes_by_type: statsRes.relationship_type_counts || statsRes.nodes_by_type || {},
          total_tags: statsRes.total_tags || 0,
          avg_confidence: statsRes.avg_confidence || 0.5,
        });
      } catch {
        // Stats endpoint may not exist; use defaults
        setStats({
          total_nodes: 0,
          total_edges: 0,
          total_clusters: 0,
          total_queries: 0,
          nodes_by_domain: {},
          nodes_by_type: {},
          total_tags: 0,
          avg_confidence: 0.5,
        });
      }

      // Fetch nodes from knowledge-fabric
      let nodes: KnowledgeNode[] = [];
      try {
        const queryRes = await fetch('/api/knowledge-fabric/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: '*',
            filters: { limit: 200 },
          }),
        });
        if (queryRes.ok) {
          const data: QueryResult = await queryRes.json();
          nodes = data.nodes || [];
        }
      } catch {
        // knowledge-fabric/query may not be available yet
      }

      // Also try kg entities as fallback
      if (nodes.length === 0) {
        try {
          const kgRes = await api.knowledgeGraph.listEntities({ limit: 200 });
          const entities = kgRes.entities || [];
          nodes = entities.map((e: any) => ({
            node_id: e.id,
            title: e.name,
            summary: e.properties?.description || '',
            content: e.properties?.content || '',
            domain: e.properties?.domain || e.entity_type || 'general',
            knowledge_type: e.entity_type || 'concept',
            confidence: e.properties?.confidence || e.confidence || 0.5,
            importance: e.properties?.importance || 0.5,
            tags: e.properties?.tags ? (Array.isArray(e.properties.tags) ? e.properties.tags : [e.properties.tags]) : [],
            source: e.properties?.source || '',
            created_at: e.created_at,
          }));
        } catch {
          // No fallback available
        }
      }

      // Build related map from entities
      const relatedMap = new Map<string, string[]>();
      for (const node of nodes) {
        try {
          const relRes = await api.knowledgeGraph.getRelationships(node.node_id);
          const related = (relRes.relationships || []).map((r: any) =>
            r.source_id === node.node_id ? r.target_id : r.source_id
          );
          relatedMap.set(node.node_id, related.slice(0, 10));
        } catch {
          relatedMap.set(node.node_id, []);
        }
      }

      // Convert to graph nodes
      const gNodes: GraphNode[] = nodes.map((n) => ({
        id: n.node_id,
        title: n.title,
        domain: n.domain || 'general',
        type: n.knowledge_type || 'fact',
        confidence: n.confidence || 0.5,
        importance: n.importance || 0.5,
        tags: n.tags || [],
        summary: n.summary || '',
        content: n.content,
        x: Math.random() * 800,
        y: Math.random() * 500,
        vx: 0,
        vy: 0,
        radius: getNodeRadius(n.confidence || 0.5, n.importance || 0.5),
        color: getDomainColor(n.domain || 'general'),
        relatedIds: relatedMap.get(n.node_id) || [],
      }));

      const gEdges = buildEdges(gNodes, relatedMap);

      setGraphNodes(gNodes);
      setGraphEdges(gEdges);

      // Update stats
      setStats((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          total_nodes: gNodes.length,
          total_edges: gEdges.length,
        };
      });
    } catch (e: any) {
      showError(e.message || 'Failed to load knowledge graph data');
    } finally {
      setLoading(false);
    }
  }, [showError]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh polling
  useEffect(() => {
    const interval = setInterval(() => {
      fetchData();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // ── Filtered nodes ──

  const filteredNodes = useMemo(() => {
    let nodes = graphNodes.filter((n) => domainFilters.has(n.domain));
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      nodes = nodes.filter(
        (n) =>
          n.title.toLowerCase().includes(q) ||
          n.tags.some((t) => t.toLowerCase().includes(q)) ||
          n.summary.toLowerCase().includes(q)
      );
    }
    return nodes;
  }, [graphNodes, domainFilters, searchQuery]);

  // ── Layout application ──

  const applyLayout = useCallback(
    (nodes: GraphNode[], mode: LayoutMode, width: number, height: number) => {
      const copy = nodes.map((n) => ({ ...n }));
      if (mode === 'radial') {
        applyRadialLayout(copy, width, height);
      } else if (mode === 'grid') {
        applyGridLayout(copy, width, height);
      } else {
        // Force-directed: random initial positions
        copy.forEach((n) => {
          n.x = 50 + Math.random() * (width - 100);
          n.y = 50 + Math.random() * (height - 100);
          n.vx = 0;
          n.vy = 0;
        });
      }
      return copy;
    },
    []
  );

  // Re-layout when mode changes
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const width = canvas.width || 800;
    const height = canvas.height || 600;
    const laidOut = applyLayout(filteredNodes, layoutMode, width, height);
    setGraphNodes((prev) => {
      const map = new Map(laidOut.map((n) => [n.id, n]));
      return prev.map((n) => {
        const updated = map.get(n.id);
        if (updated) {
          return { ...n, x: updated.x, y: updated.y, vx: 0, vy: 0 };
        }
        return n;
      });
    });
  }, [layoutMode]);

  // ── Canvas rendering & animation loop ──

  const render = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const rect = container.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;
    const dpr = window.devicePixelRatio || 1;

    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const z = zoomRef.current;
    const panX = panRef.current.x;
    const panY = panRef.current.y;

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Background
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, w, h);

    const nodes = nodesRef.current;
    const edges = edgesRef.current;
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));

    // Apply force simulation per frame
    if (layoutMode === 'force-directed') {
      applyForceLayout(nodes, edges, w, h);
    }

    // Transform
    ctx.save();
    ctx.translate(panX, panY);
    ctx.scale(z, z);

    // Draw edges
    for (const edge of edges) {
      const source = nodeMap.get(edge.sourceId);
      const target = nodeMap.get(edge.targetId);
      if (!source || !target) continue;

      let alpha = 0.25;
      let color = 'rgba(255,255,255,0.25)';
      let width = getEdgeWidth(edge.strength);

      if (hoveredNodeId) {
        if (edge.sourceId === hoveredNodeId || edge.targetId === hoveredNodeId) {
          alpha = 0.8;
          color = source.color || target.color;
          width = Math.max(width, 1.5);
        } else {
          alpha = 0.05;
        }
      }

      drawArrow(ctx, source.x, source.y, target.x, target.y, color, width, alpha);
    }

    // Draw nodes
    for (const node of nodes) {
      const isSelected = node.id === selectedNodeId;
      const isHovered = node.id === hoveredNodeId;
      const isHighlighted = highlightedNodeIds.has(node.id);
      let alpha = hoveredNodeId && !isHovered && !isHighlighted ? 0.2 : 1;

      ctx.save();
      ctx.globalAlpha = alpha;

      // Glow ring for selected
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius + 6, 0, Math.PI * 2);
        ctx.fillStyle = node.color + '30';
        ctx.fill();
      }

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
      ctx.fillStyle = node.color;
      ctx.fill();

      // Border
      ctx.strokeStyle = isHovered || isSelected ? '#fff' : 'rgba(255,255,255,0.2)';
      ctx.lineWidth = isHovered || isSelected ? 2 : 1;
      ctx.stroke();

      // Label
      const fontSize = Math.max(8, Math.min(node.radius * 0.65, 12));
      ctx.font = `${fontSize}px "Inter", -apple-system, sans-serif`;
      ctx.fillStyle = '#fff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const label = node.title.length > 14 ? node.title.slice(0, 12) + '..' : node.title;
      ctx.fillText(label, node.x, node.y);

      ctx.restore();
    }

    ctx.restore();

    // Draw zoom indicator
    ctx.fillStyle = 'rgba(255,255,255,0.4)';
    ctx.font = '10px monospace';
    ctx.textAlign = 'right';
    ctx.fillText(`${Math.round(z * 100)}%`, w - 12, h - 12);
  }, [layoutMode, hoveredNodeId, selectedNodeId, highlightedNodeIds]);

  // Animation loop
  useEffect(() => {
    let running = true;
    const loop = () => {
      if (!running) return;
      render();
      animFrameRef.current = requestAnimationFrame(loop);
    };
    loop();
    return () => {
      running = false;
      cancelAnimationFrame(animFrameRef.current);
    };
  }, [render]);

  // ── Mouse interactions ──

  const getCanvasCoords = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement> | MouseEvent): { x: number; y: number } => {
      const canvas = canvasRef.current;
      if (!canvas) return { x: 0, y: 0 };
      const rect = canvas.getBoundingClientRect();
      return {
        x: (e.clientX - rect.left) / zoomRef.current - panRef.current.x / zoomRef.current,
        y: (e.clientY - rect.top) / zoomRef.current - panRef.current.y / zoomRef.current,
      };
    },
    []
  );

  const findNodeAt = useCallback(
    (x: number, y: number): GraphNode | null => {
      for (let i = nodesRef.current.length - 1; i >= 0; i--) {
        const node = nodesRef.current[i];
        const dx = x - node.x;
        const dy = y - node.y;
        if (dx * dx + dy * dy <= (node.radius + 4) ** 2) {
          return node;
        }
      }
      return null;
    },
    []
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const coords = getCanvasCoords(e);
      const node = findNodeAt(coords.x, coords.y);

      if (node) {
        dragRef.current = {
          type: 'node',
          nodeId: node.id,
          startX: e.clientX,
          startY: e.clientY,
          nodeStartX: node.x,
          nodeStartY: node.y,
        };
      } else {
        dragRef.current = {
          type: 'canvas',
          startX: e.clientX,
          startY: e.clientY,
        };
      }
    },
    [getCanvasCoords, findNodeAt]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const coords = getCanvasCoords(e);

      // Handle dragging
      if (dragRef.current) {
        if (dragRef.current.type === 'node') {
          const node = nodesRef.current.find((n) => n.id === dragRef.current!.nodeId);
          if (node) {
            const dx = (e.clientX - dragRef.current.startX) / zoomRef.current;
            const dy = (e.clientY - dragRef.current.startY) / zoomRef.current;
            node.x = (dragRef.current.nodeStartX || 0) + dx;
            node.y = (dragRef.current.nodeStartY || 0) + dy;
          }
        } else if (dragRef.current.type === 'canvas') {
          const dx = e.clientX - dragRef.current.startX;
          const dy = e.clientY - dragRef.current.startY;
          panRef.current.x += dx;
          panRef.current.y += dy;
          dragRef.current.startX = e.clientX;
          dragRef.current.startY = e.clientY;
        }
        return;
      }

      // Hover detection
      const node = findNodeAt(coords.x, coords.y);
      const newHoveredId = node ? node.id : null;
      setHoveredNodeId((prev) => {
        if (prev !== newHoveredId) {
          if (newHoveredId) {
            // Highlight connected nodes
            const connected = new Set<string>();
            connected.add(newHoveredId);
            for (const edge of edgesRef.current) {
              if (edge.sourceId === newHoveredId) connected.add(edge.targetId);
              if (edge.targetId === newHoveredId) connected.add(edge.sourceId);
            }
            setHighlightedNodeIds(connected);
          } else {
            setHighlightedNodeIds(new Set());
          }
          return newHoveredId;
        }
        return prev;
      });
    },
    [getCanvasCoords, findNodeAt]
  );

  const handleMouseUp = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      dragRef.current = null;
    },
    []
  );

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const coords = getCanvasCoords(e);
      const node = findNodeAt(coords.x, coords.y);

      if (node) {
        // Single click: select
        if (doubleClickTimerRef.current) {
          clearTimeout(doubleClickTimerRef.current);
          doubleClickTimerRef.current = null;
          return;
        }

        doubleClickTimerRef.current = setTimeout(() => {
          doubleClickTimerRef.current = null;
          setSelectedNodeId((prev) => (prev === node.id ? null : node.id));
          onSelectNode?.(node.id);
        }, 250);
      } else {
        setSelectedNodeId(null);
      }
    },
    [getCanvasCoords, findNodeAt, onSelectNode]
  );

  const handleDoubleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (doubleClickTimerRef.current) {
        clearTimeout(doubleClickTimerRef.current);
        doubleClickTimerRef.current = null;
      }

      const coords = getCanvasCoords(e);
      const node = findNodeAt(coords.x, coords.y);

      if (node) {
        // Expand: fetch related nodes and add them
        setSelectedNodeId(node.id);
        onSelectNode?.(node.id);

        // Try to fetch related entities
        const fetchRelated = async () => {
          try {
            const relRes = await api.knowledgeGraph.getRelationships(node.id);
            const relatedIds = new Set<string>();
            for (const r of relRes.relationships || []) {
              const rid = r.source_id === node.id ? r.target_id : r.source_id;
              relatedIds.add(rid);
            }

            // Fetch entity details for new nodes
            const newNodes: GraphNode[] = [];
            for (const rid of relatedIds) {
              if (nodesRef.current.some((n) => n.id === rid)) continue;
              try {
                const ent = await api.knowledgeGraph.getEntity(rid);
                newNodes.push({
                  id: rid,
                  title: ent.name || rid,
                  domain: ent.entity_type || 'general',
                  type: ent.entity_type || 'concept',
                  confidence: ent.confidence || 0.5,
                  importance: ent.importance || 0.5,
                  tags: ent.tags || [],
                  summary: ent.properties?.description || '',
                  content: ent.properties?.content,
                  x: node.x + (Math.random() - 0.5) * 200,
                  y: node.y + (Math.random() - 0.5) * 200,
                  vx: 0,
                  vy: 0,
                  radius: getNodeRadius(ent.confidence || 0.5, ent.importance || 0.5),
                  color: getDomainColor(ent.entity_type || 'general'),
                  relatedIds: [],
                });
              } catch {
                // Skip if entity not found
              }
            }

            if (newNodes.length > 0) {
              const newEdges: GraphEdge[] = newNodes.map((n) => ({
                id: `edge_${node.id}_${n.id}`,
                sourceId: node.id,
                targetId: n.id,
                strength: 0.6,
                type: 'related',
              }));

              setGraphNodes((prev) => [...prev, ...newNodes]);
              setGraphEdges((prev) => [...prev, ...newEdges]);
            }
          } catch {
            // Silently fail
          }
        };
        fetchRelated();
      }
    },
    [getCanvasCoords, findNodeAt, onSelectNode]
  );

  const handleWheel = useCallback(
    (e: React.WheelEvent<HTMLCanvasElement>) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.08 : 0.08;
      setZoom((prev) => Math.max(0.2, Math.min(3, prev + delta)));
    },
    []
  );

  // ── Zoom controls ──

  const zoomIn = () => setZoom((z) => Math.min(3, z + 0.15));
  const zoomOut = () => setZoom((z) => Math.max(0.2, z - 0.15));
  const zoomReset = () => {
    setZoom(1);
    panRef.current = { x: 0, y: 0 };
  };

  // ── Domain filter toggle ──

  const toggleDomain = (domain: string) => {
    setDomainFilters((prev) => {
      const next = new Set(prev);
      if (next.has(domain)) {
        if (next.size > 1) next.delete(domain);
      } else {
        next.add(domain);
      }
      return next;
    });
  };

  // ── Selected node detail ──

  const selectedNode = useMemo(
    () => graphNodes.find((n) => n.id === selectedNodeId) || null,
    [graphNodes, selectedNodeId]
  );

  const selectedNodeRelated = useMemo(() => {
    if (!selectedNode) return [];
    const relatedIds = new Set<string>();
    for (const edge of graphEdges) {
      if (edge.sourceId === selectedNode.id) relatedIds.add(edge.targetId);
      if (edge.targetId === selectedNode.id) relatedIds.add(edge.sourceId);
    }
    return graphNodes.filter((n) => relatedIds.has(n.id)).slice(0, 8);
  }, [selectedNode, graphEdges, graphNodes]);

  // ── Render ──

  return (
    <div style={styles.container}>
      {/* Control Bar */}
      <div style={styles.controlBar}>
        {/* Search */}
        <input
          type="text"
          placeholder="Search nodes..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={styles.searchInput}
        />

        {/* Domain Filter */}
        <div style={styles.domainFilter}>
          <button
            style={styles.domainFilterBtn}
            onClick={() => setShowDomainDropdown((v) => !v)}
            onBlur={() => setTimeout(() => setShowDomainDropdown(false), 200)}
          >
            <span>Domains ({domainFilters.size})</span>
            <span style={{ fontSize: '0.6rem' }}>▼</span>
          </button>
          {showDomainDropdown && (
            <div style={styles.domainDropdown}>
              {ALL_DOMAINS.map((domain) => (
                <div
                  key={domain}
                  style={styles.domainOption}
                  onClick={() => toggleDomain(domain)}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.06)';
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.background = 'transparent';
                  }}
                >
                  <span style={domainDotStyle(getDomainColor(domain))} />
                  <span style={{ flex: 1 }}>{domain.replace(/_/g, ' ')}</span>
                  {domainFilters.has(domain) && <span style={{ color: '#4f6ef7' }}>✓</span>}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Layout Toggle */}
        <div style={styles.layoutBtns}>
          {(['force-directed', 'radial', 'grid'] as const).map((mode) => (
            <button
              key={mode}
              style={layoutBtnStyle(layoutMode === mode)}
              onClick={() => setLayoutMode(mode)}
            >
              {mode === 'force-directed' ? 'Force' : mode === 'radial' ? 'Radial' : 'Grid'}
            </button>
          ))}
        </div>

        {/* Zoom Controls */}
        <button style={styles.zoomBtn} onClick={zoomOut} title="Zoom out">
          −
        </button>
        <button style={styles.zoomBtn} onClick={zoomReset} title="Reset zoom">
          {Math.round(zoom * 100)}%
        </button>
        <button style={styles.zoomBtn} onClick={zoomIn} title="Zoom in">
          +
        </button>

        {/* Stats */}
        <div style={styles.statsBar}>
          <span style={styles.statItem}>
            Nodes: <span style={styles.statValue}>{filteredNodes.length}</span>
          </span>
          <span style={styles.statItem}>
            Edges: <span style={styles.statValue}>{graphEdges.length}</span>
          </span>
          {stats && (
            <span style={styles.statItem}>
              Clusters:{' '}
              <span style={styles.statValue}>
                {stats.total_clusters || Object.keys(stats.nodes_by_domain || {}).length}
              </span>
            </span>
          )}
        </div>
      </div>

      {/* Canvas */}
      <div
        ref={containerRef}
        style={styles.canvasWrapper}
        onMouseDown={(e) => {
          // Only handle canvas mouse down on the wrapper
          if ((e.target as HTMLElement).tagName === 'CANVAS') {
            handleMouseDown(e as any);
          }
        }}
      >
        <canvas
          ref={canvasRef}
          style={{
            ...styles.canvas,
            cursor: dragRef.current?.type === 'node' ? 'grabbing' : 'grab',
          }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onClick={handleClick}
          onDoubleClick={handleDoubleClick}
          onWheel={handleWheel}
        />

        {/* Loading */}
        {loading && <div style={styles.loadingOverlay}>Loading graph data...</div>}

        {/* Empty state */}
        {!loading && filteredNodes.length === 0 && (
          <div style={styles.emptyState}>
            <div style={{ fontSize: '2rem', marginBottom: 8 }}>⊘</div>
            <div>No nodes to display</div>
            <div style={{ fontSize: '0.75rem', marginTop: 4 }}>
              {searchQuery
                ? 'Try a different search query'
                : 'Add knowledge nodes to populate the graph'}
            </div>
          </div>
        )}

        {/* Detail Panel */}
        {selectedNode && (
          <div style={styles.detailPanel}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
              <div style={{ flex: 1 }}>
                <div style={styles.detailTitle}>{selectedNode.title}</div>
              </div>
              <button
                onClick={() => setSelectedNodeId(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#888',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  padding: 0,
                  lineHeight: 1,
                }}
              >
                ✕
              </button>
            </div>

            <div>
              <span style={{ ...styles.detailDomain, background: selectedNode.color + '25', color: selectedNode.color }}>
                {selectedNode.domain.replace(/_/g, ' ')}
              </span>
              <span style={styles.detailType}>{selectedNode.type}</span>
            </div>

            {/* Confidence */}
            <div style={styles.confidenceBar}>
              <div style={styles.confidenceLabel}>
                <span>Confidence</span>
                <span>{(selectedNode.confidence * 100).toFixed(0)}%</span>
              </div>
              <div style={styles.confidenceTrack}>
                <div style={confidenceFillStyle(selectedNode.confidence * 100, selectedNode.color)} />
              </div>
            </div>

            {/* Tags */}
            {selectedNode.tags.length > 0 && (
              <div style={styles.tagsRow}>
                {selectedNode.tags.map((tag) => (
                  <span key={tag} style={styles.tagChip}>
                    {tag}
                  </span>
                ))}
              </div>
            )}

            {/* Summary */}
            {selectedNode.summary && (
              <div style={styles.detailSummary}>
                {selectedNode.summary.length > 200
                  ? selectedNode.summary.slice(0, 200) + '...'
                  : selectedNode.summary}
              </div>
            )}

            {/* Related Nodes */}
            {selectedNodeRelated.length > 0 && (
              <div>
                <div
                  style={{
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    color: '#ccc',
                    marginBottom: 6,
                  }}
                >
                  Related Nodes ({selectedNodeRelated.length})
                </div>
                <div style={styles.relatedList}>
                  {selectedNodeRelated.map((rn) => (
                    <div
                      key={rn.id}
                      style={styles.relatedItem}
                      onClick={() => setSelectedNodeId(rn.id)}
                      onMouseEnter={(e) => {
                        (e.currentTarget as HTMLElement).style.borderColor = rn.color;
                      }}
                      onMouseLeave={(e) => {
                        (e.currentTarget as HTMLElement).style.borderColor = 'transparent';
                      }}
                    >
                      <span
                        style={{
                          display: 'inline-block',
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          background: rn.color,
                          marginRight: 8,
                        }}
                      />
                      {rn.title}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* View Details Button */}
            <button
              style={styles.viewDetailsBtn}
              onClick={() => {
                if (onNavigate) {
                  onNavigate('knowledgeFabric');
                }
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.background = '#1a4a8a';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.background = '#0f3460';
              }}
            >
              View Details
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default KnowledgeGraphViz;