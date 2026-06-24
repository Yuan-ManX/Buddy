import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// ── Props ──

interface SkillExplorerProps {
  onNavigate?: (tab: string) => void;
  onExecuteSkill?: (skillId: string) => void;
}

// ── Local Types ──

type SkillStatus = 'draft' | 'active' | 'deprecated' | 'archived';
type SkillCategory = 'Tool Chain' | 'Workflow' | 'Knowledge' | 'Interaction' | 'Automation';
type SortOption = 'popular' | 'newest' | 'rating' | 'name';

interface SkillExplorerItem {
  id: string;
  name: string;
  description: string;
  category: SkillCategory;
  rating: number;
  reviewCount: number;
  usageCount: number;
  version: string;
  status: SkillStatus;
  updatedAt: string;
  createdAt: string;
  author: string;
  dependencies: string[];
  parameters: Record<string, string>;
  tags: string[];
  successRate: number;
  avgLatency: number;
  usageExamples: string[];
}

interface SkillExplorerStats {
  totalSkills: number;
  activeSkills: number;
  mostPopularSkill: string;
  avgRating: number;
}

interface SkillFabricStatsResponse {
  forge: { total_skills: number; by_type: Record<string, number>; by_lifecycle: Record<string, number> };
  bundles: { total_bundles: number; avg_skills_per_bundle: number };
  market: { total_listed: number; featured: number; avg_rating: number; total_downloads: number };
  composer: { total_compositions: number; by_mode: Record<string, number> };
  analytics: Record<string, unknown>;
}

// ── Constants ──

const CATEGORIES: SkillCategory[] = ['Tool Chain', 'Workflow', 'Knowledge', 'Interaction', 'Automation'];

const CATEGORY_COLORS: Record<SkillCategory, string> = {
  'Tool Chain': '#818cf8',
  Workflow: '#34d399',
  Knowledge: '#fbbf24',
  Interaction: '#f472b6',
  Automation: '#fb923c',
};

const CATEGORY_ICONS: Record<SkillCategory, string> = {
  'Tool Chain': '🔗',
  Workflow: '⚡',
  Knowledge: '🧠',
  Interaction: '💬',
  Automation: '🤖',
};

const STATUS_COLORS: Record<SkillStatus, string> = {
  draft: '#fbbf24',
  active: '#34d399',
  deprecated: '#ef4444',
  archived: '#94a3b8',
};

const STATUS_LABELS: Record<SkillStatus, string> = {
  draft: 'Draft',
  active: 'Active',
  deprecated: 'Deprecated',
  archived: 'Archived',
};

const SORT_LABELS: Record<SortOption, string> = {
  popular: 'Popular',
  newest: 'Newest',
  rating: 'Rating',
  name: 'Name',
};

const ITEMS_PER_PAGE = 12;

// ── useDebounce Hook ──

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

// ── Helpers ──

function renderStars(rating: number): string {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5 ? 1 : 0;
  const empty = 5 - full - half;
  return '★'.repeat(full) + (half ? '☆' : '') + '☆'.repeat(empty);
}

function formatDate(iso: string): string {
  if (!iso) return 'Unknown';
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function truncateText(text: string, maxLen: number): string {
  if (!text) return '';
  return text.length > maxLen ? text.slice(0, maxLen).trimEnd() + '...' : text;
}

// ── Mock / fallback data generator for demo when API returns limited fields ──

function enrichSkill(item: { name: string; description: string; category: string; parameters: Record<string, string> }, index: number): SkillExplorerItem {
  const opts: SkillCategory[] = ['Tool Chain', 'Workflow', 'Knowledge', 'Interaction', 'Automation'];
  const statuses: SkillStatus[] = ['active', 'active', 'active', 'draft', 'deprecated', 'archived'];
  const category = opts.includes(item.category as SkillCategory) ? (item.category as SkillCategory) : opts[index % opts.length];
  const status = statuses[index % statuses.length];
  const now = Date.now();
  const createdAgo = now - (index * 3 + 7) * 86400000;
  const updatedAgo = now - (index * 2 + 1) * 86400000;

  return {
    id: `skill-${index + 1}`,
    name: item.name,
    description: item.description || 'A powerful skill that extends your agent capabilities with advanced processing.',
    category,
    rating: Math.min(5, 3.5 + (index % 3) * 0.5 + (index % 5) * 0.1),
    reviewCount: 5 + (index * 7) % 120,
    usageCount: 42 + (index * 13) % 2500,
    version: `1.${Math.floor(index / 3)}.${index % 10}`,
    status,
    updatedAt: new Date(updatedAgo).toISOString(),
    createdAt: new Date(createdAgo).toISOString(),
    author: item.parameters?.author || 'Buddy Team',
    dependencies: index % 2 === 0 ? ['core-runtime', 'memory-bridge'] : ['core-runtime'],
    parameters: item.parameters || {},
    tags: item.category ? [item.category.replace(/_/g, '-'), 'skill'] : ['general'],
    successRate: 0.85 + (index % 15) * 0.01,
    avgLatency: 120 + (index % 20) * 15,
    usageExamples: [
      `Execute ${item.name} with default parameters`,
      `Chain ${item.name} after data preprocessing`,
      `Combine ${item.name} with other skills for complex workflows`,
    ],
  };
}

// ── Component ──

export const SkillExplorer: React.FC<SkillExplorerProps> = ({ onNavigate, onExecuteSkill }) => {
  const toast = useToast();

  // ── State ──
  const [skills, setSkills] = useState<SkillExplorerItem[]>([]);
  const [stats, setStats] = useState<SkillExplorerStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearch = useDebounce(searchQuery, 300);
  const [activeCategory, setActiveCategory] = useState<SkillCategory | 'All'>('All');
  const [sortBy, setSortBy] = useState<SortOption>('popular');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);

  // Detail Modal
  const [selectedSkill, setSelectedSkill] = useState<SkillExplorerItem | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // ── Data Fetching ──

  const loadSkills = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const rawSkills = await api.skills.list();
      const enriched = rawSkills.map((s, i) => enrichSkill(s, i));
      setSkills(enriched);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load skills';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const loadStats = useCallback(async () => {
    try {
      const res = await fetch('/api/skill-fabric/stats');
      if (!res.ok) throw new Error('Failed to fetch stats');
      const data: SkillFabricStatsResponse = await res.json();

      const marketStats = data.market || {};
      const forgeStats = data.forge || {};

      const activeCount = forgeStats.by_lifecycle
        ? Object.entries(forgeStats.by_lifecycle)
            .filter(([k]) => k === 'active' || k === 'production')
            .reduce((sum, [, v]) => sum + Number(v), 0)
        : 0;

      setStats({
        totalSkills: forgeStats.total_skills || 0,
        activeSkills: activeCount || marketStats.total_listed || 0,
        mostPopularSkill: 'N/A',
        avgRating: marketStats.avg_rating || 0,
      });
    } catch (err) {
      console.error('Failed to load skill fabric stats:', err);
    }
  }, []);

  useEffect(() => {
    loadSkills();
    loadStats();
  }, [loadSkills, loadStats]);

  // ── Filtered & Sorted Skills ──

  const filteredSkills = useMemo(() => {
    let result = [...skills];

    // Category filter
    if (activeCategory !== 'All') {
      result = result.filter((s) => s.category === activeCategory);
    }

    // Search filter
    if (debouncedSearch.trim()) {
      const q = debouncedSearch.toLowerCase();
      result = result.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.description.toLowerCase().includes(q) ||
          s.tags.some((t) => t.toLowerCase().includes(q)) ||
          s.author.toLowerCase().includes(q)
      );
    }

    // Sort
    switch (sortBy) {
      case 'popular':
        result.sort((a, b) => b.usageCount - a.usageCount);
        break;
      case 'newest':
        result.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
        break;
      case 'rating':
        result.sort((a, b) => b.rating - a.rating);
        break;
      case 'name':
        result.sort((a, b) => a.name.localeCompare(b.name));
        break;
    }

    return result;
  }, [skills, activeCategory, debouncedSearch, sortBy]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [activeCategory, debouncedSearch, sortBy]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(filteredSkills.length / ITEMS_PER_PAGE));
  const paginatedSkills = filteredSkills.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const activeFilterCount = [activeCategory !== 'All' ? 1 : 0, debouncedSearch.trim() ? 1 : 0].reduce(
    (a, b) => a + b,
    0
  );

  // ── Handlers ──

  const handleCardClick = (skill: SkillExplorerItem) => {
    setSelectedSkill(skill);
  };

  const handleCloseDetail = () => {
    setSelectedSkill(null);
  };

  const handleInstall = async (skillId: string) => {
    try {
      await api.marketplace.download(skillId);
      toast.success(`Skill "${skillId}" installed successfully`);
    } catch (err) {
      toast.error('Failed to install skill');
    }
  };

  const handleExecute = (skillId: string) => {
    if (onExecuteSkill) {
      onExecuteSkill(skillId);
    } else {
      toast.info(`Skill "${skillId}" execution triggered`);
    }
  };

  const handleCreateSkill = () => {
    if (onNavigate) {
      onNavigate('skill-fabric');
    } else {
      toast.info('Navigate to Skill Fabric to create a new skill');
    }
  };

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  // ── Compute Most Popular ──
  const mostPopular = useMemo(() => {
    if (skills.length === 0) return 'N/A';
    return skills.reduce((a, b) => (a.usageCount > b.usageCount ? a : b)).name;
  }, [skills]);

  const avgRating = useMemo(() => {
    if (skills.length === 0) return 0;
    return skills.reduce((sum, s) => sum + s.rating, 0) / skills.length;
  }, [skills]);

  // ── Styles ──

  const styles = {
    container: {
      fontFamily: 'inherit',
      color: '#e4e6ed',
      width: '100%',
    },
    // Top bar
    topBar: {
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'center',
      gap: '12px',
      marginBottom: '20px',
    },
    searchWrapper: {
      position: 'relative',
      flex: '1 1 260px',
      minWidth: '200px',
    },
    searchIcon: {
      position: 'absolute',
      left: '12px',
      top: '50%',
      transform: 'translateY(-50%)',
      fontSize: '0.85rem',
      color: '#6b7280',
      pointerEvents: 'none',
    },
    searchInput: {
      width: '100%',
      padding: '10px 14px 10px 36px',
      borderRadius: '8px',
      border: '1px solid #2a2d3a',
      background: '#1c1f2e',
      color: '#e4e6ed',
      fontSize: '0.85rem',
      outline: 'none',
      boxSizing: 'border-box',
      transition: 'border-color 0.2s',
    },
    createBtn: {
      padding: '10px 20px',
      borderRadius: '8px',
      border: 'none',
      background: 'linear-gradient(135deg, #818cf8, #6366f1)',
      color: '#fff',
      fontSize: '0.85rem',
      fontWeight: 600,
      cursor: 'pointer',
      whiteSpace: 'nowrap',
      transition: 'opacity 0.2s',
    },
    // Category tabs
    tabsRow: {
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'center',
      gap: '8px',
      marginBottom: '12px',
    },
    categoryTab: (isActive: boolean): React.CSSProperties => ({
      padding: '7px 16px',
      borderRadius: '20px',
      border: isActive ? '1px solid #818cf8' : '1px solid #2a2d3a',
      background: isActive ? 'rgba(129, 140, 248, 0.12)' : 'transparent',
      color: isActive ? '#818cf8' : '#9ca3b8',
      fontSize: '0.78rem',
      fontWeight: isActive ? 600 : 400,
      cursor: 'pointer',
      whiteSpace: 'nowrap',
      transition: 'all 0.2s',
    }),
    filterCountBadge: {
      padding: '2px 8px',
      borderRadius: '10px',
      background: 'rgba(129, 140, 248, 0.15)',
      color: '#818cf8',
      fontSize: '0.7rem',
      fontWeight: 700,
      marginLeft: '4px',
    },
    // Sort
    sortRow: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: '16px',
      flexWrap: 'wrap',
      gap: '8px',
    },
    sortLabel: {
      fontSize: '0.78rem',
      color: '#6b7280',
      marginRight: '6px',
    },
    sortSelect: {
      padding: '6px 12px',
      borderRadius: '6px',
      border: '1px solid #2a2d3a',
      background: '#1c1f2e',
      color: '#e4e6ed',
      fontSize: '0.78rem',
      outline: 'none',
      cursor: 'pointer',
    },
    resultCount: {
      fontSize: '0.75rem',
      color: '#6b7280',
    },
    // Grid
    grid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
      gap: '16px',
      marginBottom: '24px',
    },
    card: {
      background: '#1c1f2e',
      border: '1px solid #2a2d3a',
      borderRadius: '12px',
      padding: '20px',
      cursor: 'pointer',
      transition: 'transform 0.2s, box-shadow 0.2s, border-color 0.2s',
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
      position: 'relative',
      overflow: 'hidden',
    },
    cardHeader: {
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      gap: '8px',
    },
    cardIcon: {
      fontSize: '1.6rem',
      lineHeight: 1,
      flexShrink: 0,
    },
    cardName: {
      flex: 1,
      fontSize: '0.95rem',
      fontWeight: 700,
      color: '#e4e6ed',
      lineHeight: 1.3,
      wordBreak: 'break-word',
    },
    cardDescription: {
      fontSize: '0.78rem',
      color: '#9ca3b8',
      lineHeight: 1.4,
      display: '-webkit-box',
      WebkitLineClamp: 2,
      WebkitBoxOrient: 'vertical',
      overflow: 'hidden',
      minHeight: '2.2em',
    },
    cardMeta: {
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'center',
      gap: '8px',
      fontSize: '0.72rem',
      color: '#6b7280',
    },
    categoryBadge: (color: string): React.CSSProperties => ({
      padding: '2px 10px',
      borderRadius: '100px',
      background: `${color}1a`,
      color,
      fontSize: '0.68rem',
      fontWeight: 600,
      whiteSpace: 'nowrap',
    }),
    statusBadge: (color: string): React.CSSProperties => ({
      padding: '2px 8px',
      borderRadius: '100px',
      background: `${color}1a`,
      color,
      fontSize: '0.65rem',
      fontWeight: 700,
      textTransform: 'uppercase',
      whiteSpace: 'nowrap',
    }),
    ratingRow: {
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      fontSize: '0.75rem',
    },
    stars: {
      color: '#fbbf24',
      fontSize: '0.8rem',
      letterSpacing: '1px',
    },
    ratingCount: {
      color: '#6b7280',
      fontSize: '0.7rem',
    },
    cardFooter: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginTop: 'auto',
      fontSize: '0.7rem',
      color: '#6b7280',
    },
    // Loading & Empty
    loadingContainer: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 20px',
      color: '#6b7280',
      gap: '12px',
    },
    spinner: {
      width: '32px',
      height: '32px',
      border: '3px solid #2a2d3a',
      borderTopColor: '#818cf8',
      borderRadius: '50%',
      animation: 'spin 0.8s linear infinite',
    },
    emptyContainer: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 20px',
      color: '#6b7280',
      gap: '8px',
    },
    emptyIcon: {
      fontSize: '2.5rem',
      marginBottom: '8px',
    },
    errorContainer: {
      padding: '16px',
      background: 'rgba(239, 68, 68, 0.08)',
      border: '1px solid rgba(239, 68, 68, 0.2)',
      borderRadius: '8px',
      color: '#ef4444',
      fontSize: '0.85rem',
      marginBottom: '16px',
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
    },
    retryBtn: {
      padding: '4px 12px',
      borderRadius: '6px',
      border: '1px solid rgba(239, 68, 68, 0.3)',
      background: 'transparent',
      color: '#ef4444',
      fontSize: '0.75rem',
      cursor: 'pointer',
      marginLeft: 'auto',
    },
    // Pagination
    pagination: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '6px',
      marginBottom: '24px',
    },
    pageBtn: (isActive: boolean): React.CSSProperties => ({
      width: '34px',
      height: '34px',
      borderRadius: '8px',
      border: isActive ? '1px solid #818cf8' : '1px solid #2a2d3a',
      background: isActive ? 'rgba(129, 140, 248, 0.12)' : 'transparent',
      color: isActive ? '#818cf8' : '#9ca3b8',
      fontSize: '0.8rem',
      fontWeight: isActive ? 600 : 400,
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      transition: 'all 0.15s',
    }),
    pageEllipsis: {
      color: '#6b7280',
      fontSize: '0.8rem',
      padding: '0 4px',
    },
    // Stats Bar
    statsBar: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
      gap: '12px',
      padding: '16px',
      background: '#1c1f2e',
      border: '1px solid #2a2d3a',
      borderRadius: '12px',
    },
    statItem: {
      textAlign: 'center',
    },
    statValue: {
      fontSize: '1.2rem',
      fontWeight: 800,
      color: '#818cf8',
    },
    statLabel: {
      fontSize: '0.68rem',
      color: '#6b7280',
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
      marginTop: '4px',
    },
    // Modal Overlay
    overlay: {
      position: 'fixed',
      inset: 0,
      background: 'rgba(0, 0, 0, 0.7)',
      backdropFilter: 'blur(4px)',
      zIndex: 1000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
    },
    modal: {
      background: '#1c1f2e',
      border: '1px solid #2a2d3a',
      borderRadius: '16px',
      width: '100%',
      maxWidth: '700px',
      maxHeight: '85vh',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      boxShadow: '0 24px 80px rgba(0, 0, 0, 0.5)',
    },
    modalHeader: {
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      padding: '24px 24px 16px',
      borderBottom: '1px solid #2a2d3a',
      gap: '12px',
    },
    modalTitle: {
      fontSize: '1.15rem',
      fontWeight: 700,
      color: '#e4e6ed',
      flex: 1,
    },
    modalCloseBtn: {
      width: '32px',
      height: '32px',
      borderRadius: '8px',
      border: '1px solid #2a2d3a',
      background: 'transparent',
      color: '#9ca3b8',
      fontSize: '1rem',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
      transition: 'all 0.15s',
    },
    modalBody: {
      padding: '24px',
      overflowY: 'auto',
      flex: 1,
    },
    modalSection: {
      marginBottom: '20px',
    },
    modalSectionTitle: {
      fontSize: '0.8rem',
      fontWeight: 700,
      color: '#6b7280',
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
      marginBottom: '8px',
    },
    modalDescription: {
      fontSize: '0.88rem',
      color: '#9ca3b8',
      lineHeight: 1.6,
      marginBottom: '8px',
    },
    modalMetaRow: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: '16px',
      marginBottom: '12px',
      fontSize: '0.8rem',
      color: '#9ca3b8',
    },
    modalMetaItem: {
      display: 'flex',
      alignItems: 'center',
      gap: '5px',
    },
    modalMetaLabel: {
      color: '#6b7280',
    },
    metricsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
      gap: '10px',
    },
    metricCard: {
      background: '#161822',
      border: '1px solid #2a2d3a',
      borderRadius: '8px',
      padding: '12px',
      textAlign: 'center',
    },
    metricValue: {
      fontSize: '1.1rem',
      fontWeight: 700,
      color: '#818cf8',
    },
    metricLabel: {
      fontSize: '0.68rem',
      color: '#6b7280',
      marginTop: '2px',
    },
    tag: {
      display: 'inline-block',
      padding: '3px 10px',
      borderRadius: '6px',
      background: 'rgba(129, 140, 248, 0.08)',
      color: '#818cf8',
      fontSize: '0.72rem',
      margin: '0 6px 6px 0',
    },
    codeBlock: {
      background: '#161822',
      border: '1px solid #2a2d3a',
      borderRadius: '8px',
      padding: '12px 16px',
      fontFamily: "'SF Mono', 'Fira Code', monospace",
      fontSize: '0.78rem',
      color: '#9ca3b8',
      lineHeight: 1.5,
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-word',
    },
    versionItem: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '8px 0',
      borderBottom: '1px solid #2a2d3a',
      fontSize: '0.8rem',
      color: '#9ca3b8',
    },
    versionCurrent: {
      padding: '1px 8px',
      borderRadius: '4px',
      background: 'rgba(52, 211, 153, 0.1)',
      color: '#34d399',
      fontSize: '0.65rem',
      fontWeight: 600,
    },
    dependencyItem: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      padding: '6px 0',
      fontSize: '0.8rem',
      color: '#9ca3b8',
    },
    depDot: {
      width: '6px',
      height: '6px',
      borderRadius: '50%',
      background: '#818cf8',
      flexShrink: 0,
    },
    modalFooter: {
      display: 'flex',
      gap: '10px',
      padding: '16px 24px',
      borderTop: '1px solid #2a2d3a',
    },
    actionBtn: (isPrimary: boolean): React.CSSProperties => ({
      flex: 1,
      padding: '10px 20px',
      borderRadius: '8px',
      border: isPrimary ? 'none' : '1px solid #2a2d3a',
      background: isPrimary
        ? 'linear-gradient(135deg, #818cf8, #6366f1)'
        : 'transparent',
      color: isPrimary ? '#fff' : '#e4e6ed',
      fontSize: '0.85rem',
      fontWeight: 600,
      cursor: 'pointer',
      transition: 'opacity 0.2s',
    }),
  } as const;

  // ── Render ──

  return (
    <div style={styles.container}>
      {/* ── Top Bar: Search + Create ── */}
      <div style={styles.topBar}>
        <div style={styles.searchWrapper}>
          <span style={styles.searchIcon}>🔍</span>
          <input
            style={styles.searchInput}
            type="text"
            placeholder="Search skills by name, description, tags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <button
          style={styles.createBtn}
          onClick={handleCreateSkill}
          onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.85')}
          onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
        >
          + Create Skill
        </button>
      </div>

      {/* ── Category Tabs ── */}
      <div style={styles.tabsRow}>
        <button
          style={styles.categoryTab(activeCategory === 'All')}
          onClick={() => setActiveCategory('All')}
        >
          All
        </button>
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            style={styles.categoryTab(activeCategory === cat)}
            onClick={() => setActiveCategory(cat)}
          >
            {CATEGORY_ICONS[cat]} {cat}
          </button>
        ))}
        {activeFilterCount > 0 && (
          <span style={styles.filterCountBadge}>{activeFilterCount}</span>
        )}
      </div>

      {/* ── Sort + Results Count ── */}
      <div style={styles.sortRow}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <span style={styles.sortLabel}>Sort by:</span>
          <select
            style={styles.sortSelect}
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
          >
            {(Object.entries(SORT_LABELS) as [SortOption, string][]).map(([val, label]) => (
              <option key={val} value={val}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <span style={styles.resultCount}>
          {filteredSkills.length} skill{filteredSkills.length !== 1 ? 's' : ''} found
        </span>
      </div>

      {/* ── Error ── */}
      {error && (
        <div style={styles.errorContainer}>
          <span>⚠️</span>
          <span>{error}</span>
          <button style={styles.retryBtn} onClick={loadSkills}>
            Retry
          </button>
        </div>
      )}

      {/* ── Loading ── */}
      {loading && (
        <div style={styles.loadingContainer}>
          <div style={styles.spinner} />
          <span>Loading skills...</span>
        </div>
      )}

      {/* ── Empty State ── */}
      {!loading && !error && filteredSkills.length === 0 && (
        <div style={styles.emptyContainer}>
          <div style={styles.emptyIcon}>📦</div>
          <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#9ca3b8' }}>
            No skills found
          </div>
          <div style={{ fontSize: '0.8rem' }}>
            Try adjusting your search or filters
          </div>
        </div>
      )}

      {/* ── Skill Cards Grid ── */}
      {!loading && paginatedSkills.length > 0 && (
        <div style={styles.grid}>
          {paginatedSkills.map((skill) => (
            <div
              key={skill.id}
              style={styles.card}
              onClick={() => handleCardClick(skill)}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                e.currentTarget.style.boxShadow = '0 8px 30px rgba(0, 0, 0, 0.3)';
                e.currentTarget.style.borderColor = '#818cf8';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0) scale(1)';
                e.currentTarget.style.boxShadow = 'none';
                e.currentTarget.style.borderColor = '#2a2d3a';
              }}
            >
              {/* Header: Icon + Name + Status */}
              <div style={styles.cardHeader}>
                <span style={styles.cardIcon}>{CATEGORY_ICONS[skill.category]}</span>
                <div style={styles.cardName}>{skill.name}</div>
                <span style={styles.statusBadge(STATUS_COLORS[skill.status])}>
                  {STATUS_LABELS[skill.status]}
                </span>
              </div>

              {/* Description */}
              <div style={styles.cardDescription}>
                {truncateText(skill.description, 120)}
              </div>

              {/* Category Badge */}
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                <span style={styles.categoryBadge(CATEGORY_COLORS[skill.category])}>
                  {skill.category}
                </span>
              </div>

              {/* Rating Stars */}
              <div style={styles.ratingRow}>
                <span style={styles.stars}>{renderStars(skill.rating)}</span>
                <span style={{ color: '#e4e6ed', fontWeight: 600, fontSize: '0.8rem' }}>
                  {skill.rating.toFixed(1)}
                </span>
                <span style={styles.ratingCount}>({skill.reviewCount})</span>
              </div>

              {/* Meta: Usage, Version */}
              <div style={styles.cardMeta}>
                <span>📥 {skill.usageCount.toLocaleString()} uses</span>
                <span>•</span>
                <span>v{skill.version}</span>
              </div>

              {/* Footer: Updated */}
              <div style={styles.cardFooter}>
                <span>Updated {formatDate(skill.updatedAt)}</span>
                <span>{skill.author}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Pagination ── */}
      {totalPages > 1 && !loading && (
        <div style={styles.pagination}>
          <button
            style={styles.pageBtn(false)}
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
          >
            ‹
          </button>
          {Array.from({ length: totalPages }, (_, i) => i + 1)
            .filter((p) => {
              if (totalPages <= 7) return true;
              if (p === 1 || p === totalPages) return true;
              if (Math.abs(p - currentPage) <= 1) return true;
              return false;
            })
            .reduce<(number | 'ellipsis')[]>((acc, p, idx, arr) => {
              if (idx > 0) {
                const prev = arr[idx - 1];
                if (p - prev > 1) acc.push('ellipsis');
              }
              acc.push(p);
              return acc;
            }, [])
            .map((item, i) =>
              item === 'ellipsis' ? (
                <span key={`e-${i}`} style={styles.pageEllipsis}>
                  ...
                </span>
              ) : (
                <button
                  key={item}
                  style={styles.pageBtn(currentPage === item)}
                  onClick={() => handlePageChange(item as number)}
                >
                  {item}
                </button>
              )
            )}
          <button
            style={styles.pageBtn(false)}
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
          >
            ›
          </button>
        </div>
      )}

      {/* ── Stats Bar ── */}
      <div style={styles.statsBar}>
        <div style={styles.statItem}>
          <div style={styles.statValue}>{stats?.totalSkills ?? skills.length}</div>
          <div style={styles.statLabel}>Total Skills</div>
        </div>
        <div style={styles.statItem}>
          <div style={styles.statValue}>{stats?.activeSkills ?? skills.filter((s) => s.status === 'active').length}</div>
          <div style={styles.statLabel}>Active Skills</div>
        </div>
        <div style={styles.statItem}>
          <div style={styles.statValue}>{mostPopular}</div>
          <div style={styles.statLabel}>Most Popular</div>
        </div>
        <div style={styles.statItem}>
          <div style={styles.statValue}>{avgRating.toFixed(1)}</div>
          <div style={styles.statLabel}>Avg Rating</div>
        </div>
      </div>

      {/* ── Skill Detail Modal ── */}
      {selectedSkill && (
        <div style={styles.overlay} onClick={handleCloseDetail}>
          <div
            style={styles.modal}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={styles.modalHeader}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1 }}>
                <span style={{ fontSize: '1.6rem' }}>
                  {CATEGORY_ICONS[selectedSkill.category]}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={styles.modalTitle}>{selectedSkill.name}</div>
                  <div style={{ fontSize: '0.78rem', color: '#6b7280', marginTop: '2px' }}>
                    v{selectedSkill.version} • by {selectedSkill.author}
                  </div>
                </div>
              </div>
              <button
                style={styles.modalCloseBtn}
                onClick={handleCloseDetail}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#2a2d3a';
                  e.currentTarget.style.color = '#e4e6ed';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = '#9ca3b8';
                }}
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div style={styles.modalBody}>
              {/* Description */}
              <div style={styles.modalSection}>
                <div style={styles.modalSectionTitle}>Description</div>
                <div style={styles.modalDescription}>
                  {selectedSkill.description}
                </div>
              </div>

              {/* Meta */}
              <div style={styles.modalSection}>
                <div style={styles.modalSectionTitle}>Details</div>
                <div style={styles.modalMetaRow}>
                  <div style={styles.modalMetaItem}>
                    <span style={styles.modalMetaLabel}>Category:</span>
                    <span style={styles.categoryBadge(CATEGORY_COLORS[selectedSkill.category])}>
                      {selectedSkill.category}
                    </span>
                  </div>
                  <div style={styles.modalMetaItem}>
                    <span style={styles.modalMetaLabel}>Status:</span>
                    <span style={styles.statusBadge(STATUS_COLORS[selectedSkill.status])}>
                      {STATUS_LABELS[selectedSkill.status]}
                    </span>
                  </div>
                  <div style={styles.modalMetaItem}>
                    <span style={styles.modalMetaLabel}>Rating:</span>
                    <span style={styles.stars}>{renderStars(selectedSkill.rating)}</span>
                    <span style={{ color: '#e4e6ed' }}>{selectedSkill.rating.toFixed(1)}</span>
                  </div>
                  <div style={styles.modalMetaItem}>
                    <span style={styles.modalMetaLabel}>Uses:</span>
                    <span>{selectedSkill.usageCount.toLocaleString()}</span>
                  </div>
                  <div style={styles.modalMetaItem}>
                    <span style={styles.modalMetaLabel}>Updated:</span>
                    <span>{formatDate(selectedSkill.updatedAt)}</span>
                  </div>
                </div>
              </div>

              {/* Performance Metrics */}
              <div style={styles.modalSection}>
                <div style={styles.modalSectionTitle}>Performance</div>
                <div style={styles.metricsGrid}>
                  <div style={styles.metricCard}>
                    <div style={styles.metricValue}>
                      {(selectedSkill.successRate * 100).toFixed(1)}%
                    </div>
                    <div style={styles.metricLabel}>Success Rate</div>
                  </div>
                  <div style={styles.metricCard}>
                    <div style={styles.metricValue}>
                      {selectedSkill.avgLatency}ms
                    </div>
                    <div style={styles.metricLabel}>Avg Latency</div>
                  </div>
                  <div style={styles.metricCard}>
                    <div style={styles.metricValue}>
                      {selectedSkill.usageCount.toLocaleString()}
                    </div>
                    <div style={styles.metricLabel}>Total Executions</div>
                  </div>
                  <div style={styles.metricCard}>
                    <div style={styles.metricValue}>
                      {selectedSkill.reviewCount}
                    </div>
                    <div style={styles.metricLabel}>Reviews</div>
                  </div>
                </div>
              </div>

              {/* Version History */}
              <div style={styles.modalSection}>
                <div style={styles.modalSectionTitle}>Version History</div>
                <div style={styles.versionItem}>
                  <span>v{selectedSkill.version}</span>
                  <span style={styles.versionCurrent}>Current</span>
                </div>
                {(() => {
                  const [major, minor, patch] = selectedSkill.version.split('.').map(Number);
                  const versions = [];
                  if (patch > 0) versions.push(`v${major}.${minor}.${patch - 1}`);
                  if (minor > 0) versions.push(`v${major}.${minor - 1}.0`);
                  if (major > 0) versions.push(`v${major - 1}.0.0`);
                  return versions.map((v, i) => (
                    <div key={i} style={styles.versionItem}>
                      <span>{v}</span>
                      <span style={{ color: '#6b7280', fontSize: '0.7rem' }}>Previous</span>
                    </div>
                  ));
                })()}
              </div>

              {/* Parameters */}
              {Object.keys(selectedSkill.parameters).length > 0 && (
                <div style={styles.modalSection}>
                  <div style={styles.modalSectionTitle}>Parameters</div>
                  <div style={styles.codeBlock}>
                    {JSON.stringify(selectedSkill.parameters, null, 2)}
                  </div>
                </div>
              )}

              {/* Usage Examples */}
              {selectedSkill.usageExamples.length > 0 && (
                <div style={styles.modalSection}>
                  <div style={styles.modalSectionTitle}>Usage Examples</div>
                  {selectedSkill.usageExamples.map((ex, i) => (
                    <div key={i} style={{ ...styles.codeBlock, marginBottom: '8px' }}>
                      {ex}
                    </div>
                  ))}
                </div>
              )}

              {/* Dependencies */}
              {selectedSkill.dependencies.length > 0 && (
                <div style={styles.modalSection}>
                  <div style={styles.modalSectionTitle}>Dependencies</div>
                  {selectedSkill.dependencies.map((dep) => (
                    <div key={dep} style={styles.dependencyItem}>
                      <span style={styles.depDot} />
                      <span>{dep}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Tags */}
              {selectedSkill.tags.length > 0 && (
                <div style={styles.modalSection}>
                  <div style={styles.modalSectionTitle}>Tags</div>
                  <div>
                    {selectedSkill.tags.map((tag) => (
                      <span key={tag} style={styles.tag}>
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer Actions */}
            <div style={styles.modalFooter}>
              <button
                style={styles.actionBtn(false)}
                onClick={() => handleInstall(selectedSkill.id)}
                onMouseEnter={(e) => (e.currentTarget.style.background = '#2a2d3a')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                📥 Install
              </button>
              <button
                style={styles.actionBtn(true)}
                onClick={() => handleExecute(selectedSkill.id)}
                onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.85')}
                onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
              >
                ⚡ Execute
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Inject keyframes for spinner */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default SkillExplorer;