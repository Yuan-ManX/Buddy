import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

// ─── Tab definitions ──────────────────────────────────────────────

type TabId = 'reasoning' | 'self-improvement' | 'sessions' | 'memory' | 'experience' | 'platform' | 'composer';

interface Tab {
  id: TabId;
  label: string;
  icon: string;
}

const TABS: Tab[] = [
  { id: 'reasoning', label: 'Deep Reasoning', icon: '🧠' },
  { id: 'self-improvement', label: 'Self-Improvement', icon: '📈' },
  { id: 'sessions', label: 'Session Management', icon: '🤝' },
  { id: 'memory', label: 'Memory', icon: '💾' },
  { id: 'experience', label: 'Experience', icon: '📊' },
  { id: 'platform', label: 'Platform', icon: '🏗️' },
  { id: 'composer', label: 'Agent Composer', icon: '🎯' },
];

// ─── Shared types ──────────────────────────────────────────────────

interface Agent {
  id: string;
  name: string;
  role: string;
}

interface Session {
  session_id: string;
  name: string;
  description: string;
  state: string;
  participant_count: number;
  created_at: string;
}

// ─── Helper: fetch wrapper ─────────────────────────────────────────

const BASE = '/api';

async function apiFetch<T = any>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try { message = JSON.parse(body).detail || body; } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ─── Section wrapper component ─────────────────────────────────────

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 mb-4">
    <h3 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wide">{title}</h3>
    {children}
  </div>
);

// ─── Inline components ─────────────────────────────────────────────

const Spinner: React.FC = () => (
  <div className="flex items-center justify-center py-4">
    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-400"></div>
  </div>
);

const ErrorMsg: React.FC<{ msg: string }> = ({ msg }) => (
  <div className="bg-red-900/30 border border-red-700/50 text-red-300 rounded-lg p-3 text-sm">{msg}</div>
);

const ResultBox: React.FC<{ data: any }> = ({ data }) => (
  <pre className="mt-2 bg-gray-900/80 border border-gray-700 rounded-lg p-3 text-xs text-green-300 overflow-x-auto max-h-64 overflow-y-auto">
    {typeof data === 'string' ? data : JSON.stringify(data, null, 2)}
  </pre>
);

// ─── Main Component ─────────────────────────────────────────────────

export const UnifiedAgentPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('reasoning');

  // Shared state
  const [agents, setAgents] = useState<Agent[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedAgent, setSelectedAgent] = useState('buddy-coder');
  const [selectedSession, setSelectedSession] = useState('');

  // Load agents
  useEffect(() => {
    api.agents.list(1, 100).then((res) => {
      setAgents(res.items.map((a) => ({ id: a.id, name: a.name, role: a.role })));
    }).catch(() => {});
  }, []);

  // Load sessions
  useEffect(() => {
    apiFetch('/sessions').then((data: any) => {
      setSessions(data.sessions || []);
      if (data.sessions?.length > 0) setSelectedSession(data.sessions[0].session_id);
    }).catch(() => {});
  }, []);

  // ─── Agent Selector ──────────────────────────────────────────────

  const AgentSelector = ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
    >
      {agents.map((a) => (
        <option key={a.id} value={a.id}>{a.name} ({a.role})</option>
      ))}
      {agents.length === 0 && <option value="buddy-coder">buddy-coder</option>}
    </select>
  );

  const SessionSelector = ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
    >
      {sessions.map((s) => (
        <option key={s.session_id} value={s.session_id}>{s.name} ({s.state})</option>
      ))}
      {sessions.length === 0 && <option value="">No sessions</option>}
    </select>
  );

  return (
    <div className="flex flex-col h-full bg-gray-900 text-gray-200">
      {/* Header */}
      <div className="border-b border-gray-700/50 px-4 py-3 flex items-center justify-between">
        <h2 className="text-lg font-bold text-white">Unified Agent Panel</h2>
        <div className="flex items-center gap-4">
          <span className="text-xs text-gray-400">Agent:</span>
          <AgentSelector value={selectedAgent} onChange={setSelectedAgent} />
        </div>
      </div>

      {/* Tab Bar */}
      <div className="flex border-b border-gray-700/50 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-blue-400 text-blue-400 bg-blue-900/20'
                : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-600'
            }`}
          >
            <span className="mr-1.5">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'reasoning' && <ReasoningTab agentId={selectedAgent} />}
        {activeTab === 'self-improvement' && <SelfImprovementTab agentId={selectedAgent} />}
        {activeTab === 'sessions' && (
          <SessionsTab agentId={selectedAgent} sessionId={selectedSession} sessions={sessions} />
        )}
        {activeTab === 'memory' && <MemoryTab agentId={selectedAgent} />}
        {activeTab === 'experience' && <ExperienceTab agentId={selectedAgent} />}
        {activeTab === 'platform' && <PlatformTab agentId={selectedAgent} />}
        {activeTab === 'composer' && <ComposerTab agentId={selectedAgent} />}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
// 1. Deep Reasoning Tab
// ═══════════════════════════════════════════════════════════════════

const ReasoningTab: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [subTab, setSubTab] = useState<'adversarial' | 'causal' | 'analogical' | 'synthesize' | 'recommend' | 'calibrate'>('adversarial');

  return (
    <div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {(['adversarial', 'causal', 'analogical', 'synthesize', 'recommend', 'calibrate'] as const).map((st) => (
          <button
            key={st}
            onClick={() => setSubTab(st)}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              subTab === st
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {st === 'adversarial' && 'Adversarial'}
            {st === 'causal' && 'Causal'}
            {st === 'analogical' && 'Analogical'}
            {st === 'synthesize' && 'Chain Synthesis'}
            {st === 'recommend' && 'Strategy Recommendation'}
            {st === 'calibrate' && 'Confidence Calibration'}
          </button>
        ))}
      </div>

      {subTab === 'adversarial' && <AdversarialReasoning agentId={agentId} />}
      {subTab === 'causal' && <CausalReasoning agentId={agentId} />}
      {subTab === 'analogical' && <AnalogicalReasoning agentId={agentId} />}
      {subTab === 'synthesize' && <ChainSynthesis agentId={agentId} />}
      {subTab === 'recommend' && <StrategyRecommendation agentId={agentId} />}
      {subTab === 'calibrate' && <ConfidenceCalibration agentId={agentId} />}
    </div>
  );
};

const AdversarialReasoning: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [prompt, setPrompt] = useState('');
  const [numCounterArgs, setNumCounterArgs] = useState(3);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/reasoning/adversarial`, {
        method: 'POST',
        body: JSON.stringify({ prompt, num_counter_args: numCounterArgs }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Adversarial Reasoning">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Prompt</label>
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={3}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Enter the problem or statement to analyze adversarially..." />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Number of Counter-Arguments: {numCounterArgs}</label>
          <input type="range" min={1} max={10} value={numCounterArgs} onChange={(e) => setNumCounterArgs(Number(e.target.value))}
            className="w-full" />
        </div>
        <button onClick={run} disabled={loading || !prompt.trim()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Running...' : 'Run Adversarial Reasoning'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const CausalReasoning: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [prompt, setPrompt] = useState('');
  const [maxChainDepth, setMaxChainDepth] = useState(3);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/reasoning/causal`, {
        method: 'POST',
        body: JSON.stringify({ prompt, max_chain_depth: maxChainDepth }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Causal Reasoning">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Prompt</label>
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={3}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Enter the problem to analyze causally..." />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Max Chain Depth: {maxChainDepth}</label>
          <input type="range" min={1} max={10} value={maxChainDepth} onChange={(e) => setMaxChainDepth(Number(e.target.value))}
            className="w-full" />
        </div>
        <button onClick={run} disabled={loading || !prompt.trim()}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Running...' : 'Run Causal Reasoning'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const AnalogicalReasoning: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [prompt, setPrompt] = useState('');
  const [domains, setDomains] = useState<string[]>(['biology', 'physics']);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const allDomains = ['biology', 'physics', 'economics', 'history', 'technology'];

  const toggleDomain = (d: string) => {
    setDomains((prev) => prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]);
  };

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/reasoning/analogical`, {
        method: 'POST',
        body: JSON.stringify({ prompt, domains }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Analogical Reasoning">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Prompt</label>
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={3}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Enter the problem to find analogies for..." />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Domains</label>
          <div className="flex flex-wrap gap-2">
            {allDomains.map((d) => (
              <label key={d} className="flex items-center gap-1.5 text-xs text-gray-300 cursor-pointer">
                <input type="checkbox" checked={domains.includes(d)} onChange={() => toggleDomain(d)}
                  className="rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500" />
                {d.charAt(0).toUpperCase() + d.slice(1)}
              </label>
            ))}
          </div>
        </div>
        <button onClick={run} disabled={loading || !prompt.trim() || domains.length === 0}
          className="px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Running...' : 'Run Analogical Reasoning'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const ChainSynthesis: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [prompt, setPrompt] = useState('');
  const [strategies, setStrategies] = useState<string[]>(['adversarial', 'causal']);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const allStrategies = ['adversarial', 'causal', 'analogical', 'chain_of_thought', 'tree_of_thought', 'self_consistency', 'iterative_refinement', 'multi_perspective'];

  const toggleStrategy = (s: string) => {
    setStrategies((prev) => prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]);
  };

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/reasoning/synthesize`, {
        method: 'POST',
        body: JSON.stringify({ prompt, strategies }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Chain Synthesis">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Prompt</label>
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={3}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Enter the problem to synthesize reasoning chains for..." />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Strategies</label>
          <div className="flex flex-wrap gap-2">
            {allStrategies.map((s) => (
              <label key={s} className="flex items-center gap-1.5 text-xs text-gray-300 cursor-pointer">
                <input type="checkbox" checked={strategies.includes(s)} onChange={() => toggleStrategy(s)}
                  className="rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500" />
                {s.replace(/_/g, ' ')}
              </label>
            ))}
          </div>
        </div>
        <button onClick={run} disabled={loading || !prompt.trim() || strategies.length === 0}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Running...' : 'Synthesize Chains'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const StrategyRecommendation: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/reasoning/recommend`, {
        method: 'POST',
        body: JSON.stringify({ prompt }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Strategy Recommendation">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Prompt</label>
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={3}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Enter a query to get recommended reasoning strategy..." />
        </div>
        <button onClick={run} disabled={loading || !prompt.trim()}
          className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Analyzing...' : 'Get Recommendation'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const ConfidenceCalibration: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [answer, setAnswer] = useState('');
  const [confidence, setConfidence] = useState(0.5);
  const [pastAccuracy, setPastAccuracy] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      let accuracyHistory = undefined;
      if (pastAccuracy.trim()) {
        try { accuracyHistory = JSON.parse(pastAccuracy); } catch { accuracyHistory = pastAccuracy.split(',').map(Number); }
      }
      const data = await apiFetch(`/agents/${agentId}/reasoning/calibrate`, {
        method: 'POST',
        body: JSON.stringify({ answer, confidence, past_accuracy_history: accuracyHistory }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Confidence Calibration">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Result / Answer Text</label>
          <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} rows={2}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="The conclusion or answer to calibrate..." />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Confidence: {confidence.toFixed(2)}</label>
          <input type="range" min={0} max={1} step={0.01} value={confidence} onChange={(e) => setConfidence(Number(e.target.value))}
            className="w-full" />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Past Accuracy History (JSON array or comma-separated)</label>
          <input type="text" value={pastAccuracy} onChange={(e) => setPastAccuracy(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="e.g. [0.8, 0.6, 0.9] or 0.8,0.6,0.9" />
        </div>
        <button onClick={run} disabled={loading || !answer.trim()}
          className="px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Calibrating...' : 'Calibrate Confidence'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

// ═══════════════════════════════════════════════════════════════════
// 2. Self-Improvement Tab
// ═══════════════════════════════════════════════════════════════════

const SelfImprovementTab: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [subTab, setSubTab] = useState<'compound' | 'cross-skill' | 'benchmark' | 'recommend' | 'tune' | 'trends'>('compound');

  const subTabs = [
    { id: 'compound' as const, label: 'Skill Compounding' },
    { id: 'cross-skill' as const, label: 'Cross-Skill Synthesis' },
    { id: 'benchmark' as const, label: 'Benchmark Skills' },
    { id: 'recommend' as const, label: 'Recommend Skill' },
    { id: 'tune' as const, label: 'Tune Thresholds' },
    { id: 'trends' as const, label: 'Improvement Trends' },
  ];

  return (
    <div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {subTabs.map((st) => (
          <button key={st.id} onClick={() => setSubTab(st.id)}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              subTab === st.id ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}>
            {st.label}
          </button>
        ))}
      </div>

      {subTab === 'compound' && <SkillCompounding agentId={agentId} />}
      {subTab === 'cross-skill' && <CrossSkillSynthesis agentId={agentId} />}
      {subTab === 'benchmark' && <BenchmarkSkills agentId={agentId} />}
      {subTab === 'recommend' && <RecommendSkill agentId={agentId} />}
      {subTab === 'tune' && <TuneThresholds agentId={agentId} />}
      {subTab === 'trends' && <ImprovementTrends agentId={agentId} />}
    </div>
  );
};

const SkillCompounding: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [skillIds, setSkillIds] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/improve/compound-skills`, {
        method: 'POST',
        body: JSON.stringify({
          skill_ids: skillIds.split(',').map((s) => s.trim()).filter(Boolean),
          name, description,
        }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Skill Compounding">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Skill IDs (comma-separated)</label>
          <input type="text" value={skillIds} onChange={(e) => setSkillIds(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="skill-id-1, skill-id-2, ..." />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">New Skill Name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Description</label>
            <input type="text" value={description} onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
          </div>
        </div>
        <button onClick={run} disabled={loading || !skillIds.trim() || !name.trim()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Compounding...' : 'Compound Skills'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const CrossSkillSynthesis: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [category1, setCategory1] = useState('');
  const [category2, setCategory2] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/improve/cross-skill-synthesize`, {
        method: 'POST',
        body: JSON.stringify({ category1, category2 }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Cross-Skill Synthesis">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Category 1</label>
            <input type="text" value={category1} onChange={(e) => setCategory1(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              placeholder="e.g. coding" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Category 2</label>
            <input type="text" value={category2} onChange={(e) => setCategory2(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              placeholder="e.g. analysis" />
          </div>
        </div>
        <button onClick={run} disabled={loading || !category1.trim() || !category2.trim()}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Synthesizing...' : 'Synthesize Cross-Skill'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const BenchmarkSkills: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch('/improve/skills/benchmark', { method: 'POST' });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Benchmark Skills">
      <p className="text-xs text-gray-400 mb-3">Run benchmarks on all skills to measure performance and quality metrics.</p>
      <button onClick={run} disabled={loading}
        className="px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
        {loading ? 'Running Benchmarks...' : 'Run Benchmark'}
      </button>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const RecommendSkill: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [taskDescription, setTaskDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch('/improve/skills/recommend', {
        method: 'POST',
        body: JSON.stringify({ task_description: taskDescription }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Recommend Skill">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Task Description</label>
          <textarea value={taskDescription} onChange={(e) => setTaskDescription(e.target.value)} rows={3}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Describe the task you need a skill for..." />
        </div>
        <button onClick={run} disabled={loading || !taskDescription.trim()}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Searching...' : 'Get Recommendation'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const TuneThresholds: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/improve/tune-thresholds`, { method: 'POST' });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Tune Thresholds">
      <p className="text-xs text-gray-400 mb-3">Auto-tune synthesis thresholds for optimal skill quality and performance.</p>
      <button onClick={run} disabled={loading}
        className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
        {loading ? 'Tuning...' : 'Auto-Tune Thresholds'}
      </button>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const ImprovementTrends: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch('/improve/trends');
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Improvement Trends">
      <p className="text-xs text-gray-400 mb-3">Analyze improvement trends over time including skill evolution and pattern discovery.</p>
      <button onClick={run} disabled={loading}
        className="px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
        {loading ? 'Analyzing...' : 'Analyze Trends'}
      </button>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

// ═══════════════════════════════════════════════════════════════════
// 3. Session Management Tab
// ═══════════════════════════════════════════════════════════════════

const SessionsTab: React.FC<{ agentId: string; sessionId: string; sessions: Session[] }> = ({ agentId, sessionId, sessions }) => {
  const [subTab, setSubTab] = useState<'delegate' | 'vote' | 'templates' | 'summary' | 'handoff' | 'health'>('delegate');
  const [localSession, setLocalSession] = useState(sessionId);

  useEffect(() => { setLocalSession(sessionId); }, [sessionId]);

  const subTabs = [
    { id: 'delegate' as const, label: 'Task Delegation' },
    { id: 'vote' as const, label: 'Collaborative Voting' },
    { id: 'templates' as const, label: 'Session Templates' },
    { id: 'summary' as const, label: 'Session Summary' },
    { id: 'handoff' as const, label: 'Handoff' },
    { id: 'health' as const, label: 'Health Check' },
  ];

  return (
    <div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {subTabs.map((st) => (
          <button key={st.id} onClick={() => setSubTab(st.id)}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              subTab === st.id ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}>
            {st.label}
          </button>
        ))}
      </div>

      {/* Session selector for session-dependent operations */}
      {subTab !== 'templates' && (
        <div className="flex items-center gap-3 mb-4">
          <span className="text-xs text-gray-400">Session:</span>
          <select value={localSession} onChange={(e) => setLocalSession(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500">
            {sessions.map((s) => (
              <option key={s.session_id} value={s.session_id}>{s.name} ({s.state})</option>
            ))}
            {sessions.length === 0 && <option value="">No sessions available</option>}
          </select>
        </div>
      )}

      {subTab === 'delegate' && <TaskDelegation sessionId={localSession} agentId={agentId} />}
      {subTab === 'vote' && <CollaborativeVoting sessionId={localSession} />}
      {subTab === 'templates' && <SessionTemplates agentId={agentId} />}
      {subTab === 'summary' && <SessionSummary sessionId={localSession} />}
      {subTab === 'handoff' && <SessionHandoff sessionId={localSession} agentId={agentId} />}
      {subTab === 'health' && <SessionHealth sessionId={localSession} />}
    </div>
  );
};

const TaskDelegation: React.FC<{ sessionId: string; agentId: string }> = ({ sessionId, agentId }) => {
  const [description, setDescription] = useState('');
  const [targetRole, setTargetRole] = useState('worker');
  const [targetAgentId, setTargetAgentId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/sessions/${sessionId}/delegate`, {
        method: 'POST',
        body: JSON.stringify({
          delegator_id: agentId,
          description,
          target_role: targetRole,
          target_agent_id: targetAgentId || undefined,
        }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Task Delegation">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Task Description</label>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Describe the task to delegate..." />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Target Role</label>
            <select value={targetRole} onChange={(e) => setTargetRole(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500">
              <option value="worker">Worker</option>
              <option value="reviewer">Reviewer</option>
              <option value="observer">Observer</option>
              <option value="leader">Leader</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Target Agent ID (optional)</label>
            <input type="text" value={targetAgentId} onChange={(e) => setTargetAgentId(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
          </div>
        </div>
        <button onClick={run} disabled={loading || !description.trim()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Delegating...' : 'Delegate Task'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const CollaborativeVoting: React.FC<{ sessionId: string }> = ({ sessionId }) => {
  const [action, setAction] = useState<'start' | 'cast' | 'result' | 'close'>('start');
  const [topic, setTopic] = useState('');
  const [options, setOptions] = useState('');
  const [initiatorId, setInitiatorId] = useState('');
  const [voteId, setVoteId] = useState('');
  const [voterId, setVoterId] = useState('');
  const [choice, setChoice] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const body: any = { action };
      if (action === 'start') {
        body.topic = topic;
        body.options = options.split(',').map((s) => s.trim()).filter(Boolean);
        body.initiator_id = initiatorId;
      } else if (action === 'cast') {
        body.vote_id = voteId;
        body.voter_id = voterId;
        body.choice = choice;
      } else if (action === 'result' || action === 'close') {
        body.vote_id = voteId;
      }
      const data = await apiFetch(`/sessions/${sessionId}/vote`, {
        method: 'POST',
        body: JSON.stringify(body),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Collaborative Voting">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Action</label>
          <select value={action} onChange={(e) => setAction(e.target.value as any)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500">
            <option value="start">Start Vote</option>
            <option value="cast">Cast Vote</option>
            <option value="result">Get Result</option>
            <option value="close">Close Vote</option>
          </select>
        </div>

        {action === 'start' && (
          <>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Topic</label>
              <input type="text" value={topic} onChange={(e) => setTopic(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Options (comma-separated)</label>
              <input type="text" value={options} onChange={(e) => setOptions(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
                placeholder="Option A, Option B, Option C" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Initiator ID</label>
              <input type="text" value={initiatorId} onChange={(e) => setInitiatorId(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
            </div>
          </>
        )}

        {action === 'cast' && (
          <>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Vote ID</label>
              <input type="text" value={voteId} onChange={(e) => setVoteId(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Voter ID</label>
              <input type="text" value={voterId} onChange={(e) => setVoterId(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Choice</label>
              <input type="text" value={choice} onChange={(e) => setChoice(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
            </div>
          </>
        )}

        {(action === 'result' || action === 'close') && (
          <div>
            <label className="block text-xs text-gray-400 mb-1">Vote ID</label>
            <input type="text" value={voteId} onChange={(e) => setVoteId(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
          </div>
        )}

        <button onClick={run} disabled={loading}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Processing...' : 'Submit'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const SessionTemplates: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [name, setName] = useState('');
  const [createResult, setCreateResult] = useState<any>(null);
  const [createLoading, setCreateLoading] = useState(false);

  const fetchTemplates = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const data = await apiFetch('/sessions/templates');
      setTemplates(data.templates || []);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  }, []);

  useEffect(() => { fetchTemplates(); }, [fetchTemplates]);

  const createFromTemplate = async () => {
    setCreateLoading(true); setCreateResult(null);
    try {
      const data = await apiFetch('/sessions/from-template', {
        method: 'POST',
        body: JSON.stringify({ template_id: selectedTemplate, name, orchestrator_id: agentId }),
      });
      setCreateResult(data);
    } catch (e: any) { setError(e.message); }
    setCreateLoading(false);
  };

  return (
    <Section title="Session Templates">
      <div className="space-y-4">
        <div>
          <h4 className="text-xs font-semibold text-gray-300 mb-2">Available Templates</h4>
          {loading && <Spinner />}
          {error && <ErrorMsg msg={error} />}
          {!loading && templates.length === 0 && (
            <p className="text-xs text-gray-500">No templates available.</p>
          )}
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {templates.map((t: any) => (
              <div key={t.template_id || t.id} className="bg-gray-700/50 border border-gray-600/50 rounded p-2 text-xs">
                <div className="font-medium text-gray-200">{t.name}</div>
                <div className="text-gray-400">{t.description}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="border-t border-gray-700 pt-3">
          <h4 className="text-xs font-semibold text-gray-300 mb-2">Create from Template</h4>
          <div className="space-y-2">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Template</label>
              <select value={selectedTemplate} onChange={(e) => setSelectedTemplate(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500">
                <option value="">Select a template...</option>
                {templates.map((t: any) => (
                  <option key={t.template_id || t.id} value={t.template_id || t.id}>{t.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Session Name</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
            </div>
            <button onClick={createFromTemplate} disabled={createLoading || !selectedTemplate}
              className="px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
              {createLoading ? 'Creating...' : 'Create Session from Template'}
            </button>
          </div>
          {createResult && <ResultBox data={createResult} />}
        </div>
      </div>
    </Section>
  );
};

const SessionSummary: React.FC<{ sessionId: string }> = ({ sessionId }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/sessions/${sessionId}/summary`);
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Session Summary">
      <p className="text-xs text-gray-400 mb-3">View a comprehensive summary of the session including metadata, participants, tasks, and voting outcomes.</p>
      <button onClick={run} disabled={loading}
        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
        {loading ? 'Loading...' : 'View Summary'}
      </button>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const SessionHandoff: React.FC<{ sessionId: string; agentId: string }> = ({ sessionId, agentId }) => {
  const [toAgentId, setToAgentId] = useState('');
  const [contextNotes, setContextNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/sessions/${sessionId}/handoff`, {
        method: 'POST',
        body: JSON.stringify({
          from_agent_id: agentId,
          to_agent_id: toAgentId,
          context_notes: contextNotes,
        }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Handoff">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">From Agent</label>
          <input type="text" value={agentId} disabled
            className="w-full bg-gray-600 border border-gray-500 rounded px-3 py-2 text-sm text-gray-300" />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">To Agent</label>
          <input type="text" value={toAgentId} onChange={(e) => setToAgentId(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Target agent ID" />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Context Notes</label>
          <textarea value={contextNotes} onChange={(e) => setContextNotes(e.target.value)} rows={3}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Notes about the handoff context..." />
        </div>
        <button onClick={run} disabled={loading || !toAgentId.trim()}
          className="px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Handing off...' : 'Handoff Session'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const SessionHealth: React.FC<{ sessionId: string }> = ({ sessionId }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/sessions/${sessionId}/health`);
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Health Check">
      <p className="text-xs text-gray-400 mb-3">Check session health including participant activity, timeouts, and overall health score.</p>
      <button onClick={run} disabled={loading}
        className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
        {loading ? 'Checking...' : 'Check Health'}
      </button>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

// ═══════════════════════════════════════════════════════════════════
// 4. Memory Tab (White Memory)
// ═══════════════════════════════════════════════════════════════════

const MemoryTab: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [localAgent, setLocalAgent] = useState(agentId);

  useEffect(() => { setLocalAgent(agentId); }, [agentId]);

  const [subTab, setSubTab] = useState<'search' | 'conflicts' | 'consolidate' | 'decay' | 'graph' | 'recall'>('search');

  const subTabs = [
    { id: 'search' as const, label: 'Semantic Search' },
    { id: 'conflicts' as const, label: 'Conflict Detection' },
    { id: 'consolidate' as const, label: 'Memory Consolidation' },
    { id: 'decay' as const, label: 'Importance Decay' },
    { id: 'graph' as const, label: 'Memory Graph' },
    { id: 'recall' as const, label: 'Contextual Recall' },
  ];

  return (
    <div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {subTabs.map((st) => (
          <button key={st.id} onClick={() => setSubTab(st.id)}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              subTab === st.id ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}>
            {st.label}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-3 mb-4">
        <span className="text-xs text-gray-400">Agent:</span>
        <input type="text" value={localAgent} onChange={(e) => setLocalAgent(e.target.value)}
          className="bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500 w-48" />
      </div>

      {subTab === 'search' && <SemanticSearch agentId={localAgent} />}
      {subTab === 'conflicts' && <ConflictDetection agentId={localAgent} />}
      {subTab === 'consolidate' && <MemoryConsolidation agentId={localAgent} />}
      {subTab === 'decay' && <ImportanceDecay agentId={localAgent} />}
      {subTab === 'graph' && <MemoryGraph agentId={localAgent} />}
      {subTab === 'recall' && <ContextualRecall agentId={localAgent} />}
    </div>
  );
};

const SemanticSearch: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [query, setQuery] = useState('');
  const [threshold, setThreshold] = useState(0.3);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/memory/semantic-search`, {
        method: 'POST',
        body: JSON.stringify({ query, similarity_threshold: threshold }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Semantic Search">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Query</label>
          <input type="text" value={query} onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Search query..." />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Similarity Threshold: {threshold.toFixed(2)}</label>
          <input type="range" min={0} max={1} step={0.01} value={threshold} onChange={(e) => setThreshold(Number(e.target.value))}
            className="w-full" />
        </div>
        <button onClick={run} disabled={loading || !query.trim()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const ConflictDetection: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/memory/detect-conflicts`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Conflict Detection">
      <p className="text-xs text-gray-400 mb-3">Detect contradictory memories and flag them for resolution.</p>
      <button onClick={run} disabled={loading}
        className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
        {loading ? 'Detecting...' : 'Detect Conflicts'}
      </button>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const MemoryConsolidation: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [threshold, setThreshold] = useState(0.5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/memory/consolidate`, {
        method: 'POST',
        body: JSON.stringify({ similarity_threshold: threshold }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Memory Consolidation">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Similarity Threshold: {threshold.toFixed(2)}</label>
          <input type="range" min={0.1} max={1} step={0.05} value={threshold} onChange={(e) => setThreshold(Number(e.target.value))}
            className="w-full" />
        </div>
        <button onClick={run} disabled={loading}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Consolidating...' : 'Consolidate Memories'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const ImportanceDecay: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [halfLifeDays, setHalfLifeDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/memory/decay`, {
        method: 'POST',
        body: JSON.stringify({ half_life_days: halfLifeDays }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Importance Decay">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Half-Life Days: {halfLifeDays}</label>
          <input type="range" min={1} max={365} value={halfLifeDays} onChange={(e) => setHalfLifeDays(Number(e.target.value))}
            className="w-full" />
        </div>
        <button onClick={run} disabled={loading}
          className="px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Applying Decay...' : 'Apply Decay'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const MemoryGraph: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/memory/graph`);
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Memory Graph">
      <p className="text-xs text-gray-400 mb-3">Export the memory graph structure for visualization.</p>
      <button onClick={run} disabled={loading}
        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
        {loading ? 'Loading...' : 'View Graph'}
      </button>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const ContextualRecall: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [context, setContext] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/memory/contextual-recall`, {
        method: 'POST',
        body: JSON.stringify({ context }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Contextual Recall">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Context</label>
          <textarea value={context} onChange={(e) => setContext(e.target.value)} rows={3}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Enter context to recall relevant memories..." />
        </div>
        <button onClick={run} disabled={loading || !context.trim()}
          className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Recalling...' : 'Recall'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

// ═══════════════════════════════════════════════════════════════════
// 5. Experience Tab
// ═══════════════════════════════════════════════════════════════════

const ExperienceTab: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [localAgent, setLocalAgent] = useState(agentId);

  useEffect(() => { setLocalAgent(agentId); }, [agentId]);

  const [subTab, setSubTab] = useState<'trends' | 'predict' | 'recommend' | 'cross-domain' | 'cluster'>('trends');

  const subTabs = [
    { id: 'trends' as const, label: 'Trend Analysis' },
    { id: 'predict' as const, label: 'Predict Outcome' },
    { id: 'recommend' as const, label: 'Recommend Experiences' },
    { id: 'cross-domain' as const, label: 'Cross-Domain Transfer' },
    { id: 'cluster' as const, label: 'Cluster Summary' },
  ];

  return (
    <div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {subTabs.map((st) => (
          <button key={st.id} onClick={() => setSubTab(st.id)}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              subTab === st.id ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}>
            {st.label}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-3 mb-4">
        <span className="text-xs text-gray-400">Agent:</span>
        <input type="text" value={localAgent} onChange={(e) => setLocalAgent(e.target.value)}
          className="bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500 w-48" />
      </div>

      {subTab === 'trends' && <TrendAnalysis agentId={localAgent} />}
      {subTab === 'predict' && <PredictOutcome agentId={localAgent} />}
      {subTab === 'recommend' && <RecommendExperiences agentId={localAgent} />}
      {subTab === 'cross-domain' && <CrossDomainTransfer agentId={localAgent} />}
      {subTab === 'cluster' && <ClusterSummary />}
    </div>
  );
};

const TrendAnalysis: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/experiences/trends?days=${days}`);
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Trend Analysis">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Days Range: {days}</label>
          <input type="range" min={1} max={365} value={days} onChange={(e) => setDays(Number(e.target.value))}
            className="w-full" />
        </div>
        <button onClick={run} disabled={loading}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Analyzing...' : 'Analyze Trends'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const PredictOutcome: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [description, setDescription] = useState('');
  const [expType, setExpType] = useState('');
  const [tools, setTools] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/experiences/predict`, {
        method: 'POST',
        body: JSON.stringify({
          description,
          experience_type: expType || undefined,
          tools_used: tools ? tools.split(',').map((s) => s.trim()) : undefined,
        }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Predict Outcome">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Task Description</label>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Describe the task..." />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Experience Type</label>
            <input type="text" value={expType} onChange={(e) => setExpType(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              placeholder="e.g. coding, analysis" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Tools (comma-separated)</label>
            <input type="text" value={tools} onChange={(e) => setTools(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              placeholder="tool1, tool2" />
          </div>
        </div>
        <button onClick={run} disabled={loading || !description.trim()}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Predicting...' : 'Predict Outcome'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const RecommendExperiences: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [description, setDescription] = useState('');
  const [expType, setExpType] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agents/${agentId}/experiences/recommend`, {
        method: 'POST',
        body: JSON.stringify({
          description,
          experience_type: expType || undefined,
        }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Recommend Experiences">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Task Description</label>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Describe the task to find relevant experiences..." />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Experience Type</label>
          <input type="text" value={expType} onChange={(e) => setExpType(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="e.g. coding, analysis" />
        </div>
        <button onClick={run} disabled={loading || !description.trim()}
          className="px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Searching...' : 'Get Recommendations'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const CrossDomainTransfer: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [sourceType, setSourceType] = useState('');
  const [targetType, setTargetType] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(
        `/agents/${agentId}/experiences/cross-domain?source_type=${encodeURIComponent(sourceType)}&target_type=${encodeURIComponent(targetType)}`
      );
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Cross-Domain Transfer">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Source Type</label>
            <input type="text" value={sourceType} onChange={(e) => setSourceType(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              placeholder="e.g. coding" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Target Type</label>
            <input type="text" value={targetType} onChange={(e) => setTargetType(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              placeholder="e.g. analysis" />
          </div>
        </div>
        <button onClick={run} disabled={loading || !sourceType.trim() || !targetType.trim()}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Transferring...' : 'Find Transferable Experiences'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const ClusterSummary: React.FC = () => {
  const [clusterId, setClusterId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/experiences/clusters/${clusterId}/summary`);
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Cluster Summary">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Cluster ID</label>
          <input type="text" value={clusterId} onChange={(e) => setClusterId(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Enter cluster ID..." />
        </div>
        <button onClick={run} disabled={loading || !clusterId.trim()}
          className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Loading...' : 'View Summary'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

// ═══════════════════════════════════════════════════════════════════
// 6. Platform Tab
// ═══════════════════════════════════════════════════════════════════

const PlatformTab: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [subTab, setSubTab] = useState<'fleet' | 'sync' | 'health-dashboard' | 'auto-scale' | 'quotas' | 'broadcast'>('fleet');

  const subTabs = [
    { id: 'fleet' as const, label: 'Fleet Orchestration' },
    { id: 'sync' as const, label: 'Knowledge Sync' },
    { id: 'health-dashboard' as const, label: 'Health Dashboard' },
    { id: 'auto-scale' as const, label: 'Auto-Scale' },
    { id: 'quotas' as const, label: 'Resource Quotas' },
    { id: 'broadcast' as const, label: 'Event Broadcast' },
  ];

  return (
    <div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {subTabs.map((st) => (
          <button key={st.id} onClick={() => setSubTab(st.id)}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              subTab === st.id ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}>
            {st.label}
          </button>
        ))}
      </div>

      {subTab === 'fleet' && <FleetOrchestration agentId={agentId} />}
      {subTab === 'sync' && <KnowledgeSync agentId={agentId} />}
      {subTab === 'health-dashboard' && <HealthDashboard />}
      {subTab === 'auto-scale' && <AutoScale />}
      {subTab === 'quotas' && <ResourceQuotas agentId={agentId} />}
      {subTab === 'broadcast' && <EventBroadcast />}
    </div>
  );
};

const FleetOrchestration: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [fleetName, setFleetName] = useState('');
  const [agentIds, setAgentIds] = useState('');
  const [deploymentStrategy, setDeploymentStrategy] = useState('rolling');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch('/platform/fleet/orchestrate', {
        method: 'POST',
        body: JSON.stringify({
          fleet_name: fleetName,
          agent_ids: agentIds.split(',').map((s) => s.trim()).filter(Boolean),
          deployment_strategy: deploymentStrategy,
        }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Fleet Orchestration">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Fleet Name</label>
          <input type="text" value={fleetName} onChange={(e) => setFleetName(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="My Fleet" />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Agent IDs (comma-separated)</label>
          <input type="text" value={agentIds} onChange={(e) => setAgentIds(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="agent-1, agent-2, ..." />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Deployment Strategy</label>
          <select value={deploymentStrategy} onChange={(e) => setDeploymentStrategy(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500">
            <option value="rolling">Rolling</option>
            <option value="blue_green">Blue/Green</option>
            <option value="canary">Canary</option>
          </select>
        </div>
        <button onClick={run} disabled={loading || !fleetName.trim() || !agentIds.trim()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Deploying...' : 'Create & Deploy Fleet'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const KnowledgeSync: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [fleetId, setFleetId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch('/platform/fleet/sync-knowledge', {
        method: 'POST',
        body: JSON.stringify({ fleet_id: fleetId }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Knowledge Sync">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Fleet ID</label>
          <input type="text" value={fleetId} onChange={(e) => setFleetId(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Fleet ID to sync..." />
        </div>
        <button onClick={run} disabled={loading || !fleetId.trim()}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Syncing...' : 'Sync Knowledge'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const HealthDashboard: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch('/platform/health-dashboard');
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Health Dashboard">
      <p className="text-xs text-gray-400 mb-3">View comprehensive platform health including agent status, component health, and resource utilization.</p>
      <button onClick={run} disabled={loading}
        className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
        {loading ? 'Loading...' : 'View Dashboard'}
      </button>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const AutoScale: React.FC = () => {
  const [fleetId, setFleetId] = useState('');
  const [targetCount, setTargetCount] = useState(3);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch('/platform/auto-scale', {
        method: 'POST',
        body: JSON.stringify({ fleet_id: fleetId, target_count: targetCount }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Auto-Scale">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Fleet ID</label>
          <input type="text" value={fleetId} onChange={(e) => setFleetId(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Fleet ID to scale..." />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Target Count: {targetCount}</label>
          <input type="range" min={1} max={20} value={targetCount} onChange={(e) => setTargetCount(Number(e.target.value))}
            className="w-full" />
        </div>
        <button onClick={run} disabled={loading || !fleetId.trim()}
          className="px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Scaling...' : 'Auto-Scale'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const ResourceQuotas: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch('/platform/quotas');
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Resource Quotas">
      <p className="text-xs text-gray-400 mb-3">View resource quotas and usage status for all agents.</p>
      <button onClick={run} disabled={loading}
        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
        {loading ? 'Loading...' : 'View Quotas'}
      </button>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const EventBroadcast: React.FC = () => {
  const [message, setMessage] = useState('');
  const [category, setCategory] = useState('platform.broadcast');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch('/platform/events/broadcast', {
        method: 'POST',
        body: JSON.stringify({
          event_type: category,
          source: 'api',
          data: { message, category },
        }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Event Broadcast">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Message</label>
          <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Event message to broadcast..." />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Category</label>
          <select value={category} onChange={(e) => setCategory(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500">
            <option value="platform.broadcast">Platform Broadcast</option>
            <option value="platform.alert">Alert</option>
            <option value="platform.notification">Notification</option>
            <option value="platform.deployment">Deployment</option>
            <option value="platform.config">Configuration</option>
          </select>
        </div>
        <button onClick={run} disabled={loading || !message.trim()}
          className="px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Broadcasting...' : 'Broadcast Event'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

// ═══════════════════════════════════════════════════════════════════
// 7. Agent Composer Tab
// ═══════════════════════════════════════════════════════════════════

const ComposerTab: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [subTab, setSubTab] = useState<'execute' | 'history' | 'distribution'>('execute');

  const subTabs = [
    { id: 'execute' as const, label: 'Execute' },
    { id: 'history' as const, label: 'Execution History' },
    { id: 'distribution' as const, label: 'Strategy Distribution' },
  ];

  return (
    <div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {subTabs.map((st) => (
          <button key={st.id} onClick={() => setSubTab(st.id)}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              subTab === st.id ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}>
            {st.label}
          </button>
        ))}
      </div>

      {subTab === 'execute' && <ComposerExecute agentId={agentId} />}
      {subTab === 'history' && <ComposerHistory agentId={agentId} />}
      {subTab === 'distribution' && <ComposerDistribution agentId={agentId} />}
    </div>
  );
};

const ComposerExecute: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [message, setMessage] = useState('');
  const [localAgent, setLocalAgent] = useState(agentId);
  const [mode, setMode] = useState('reactive');
  const [strategy, setStrategy] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => { setLocalAgent(agentId); }, [agentId]);

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch('/agents/compose/execute', {
        method: 'POST',
        body: JSON.stringify({
          message,
          agent_id: localAgent,
          mode,
          strategy: strategy || undefined,
        }),
      });
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Execute with Strategy">
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Message</label>
          <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Enter your message to execute through the agent composer..." />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Agent ID</label>
            <input type="text" value={localAgent} onChange={(e) => setLocalAgent(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Mode</label>
            <select value={mode} onChange={(e) => setMode(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500">
              <option value="reactive">Reactive</option>
              <option value="proactive">Proactive</option>
              <option value="reflective">Reflective</option>
              <option value="creative">Creative</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Strategy</label>
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500">
              <option value="">Auto-detect</option>
              <option value="chain_of_thought">Chain of Thought</option>
              <option value="tree_of_thought">Tree of Thought</option>
              <option value="self_consistency">Self Consistency</option>
              <option value="adversarial">Adversarial</option>
              <option value="causal">Causal</option>
              <option value="analogical">Analogical</option>
            </select>
          </div>
        </div>
        <button onClick={run} disabled={loading || !message.trim()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
          {loading ? 'Executing...' : 'Execute'}
        </button>
      </div>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const ComposerHistory: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agent-core/traces?agent_id=${agentId}&limit=20`);
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Execution History">
      <p className="text-xs text-gray-400 mb-3">View recent execution traces and their strategies used.</p>
      <button onClick={run} disabled={loading}
        className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
        {loading ? 'Loading...' : 'View History'}
      </button>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

const ComposerDistribution: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiFetch(`/agent-core/stats?agent_id=${agentId}`);
      setResult(data);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <Section title="Strategy Distribution">
      <p className="text-xs text-gray-400 mb-3">View strategy distribution statistics and effectiveness metrics.</p>
      <button onClick={run} disabled={loading}
        className="px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 rounded text-sm font-medium text-white transition-colors">
        {loading ? 'Loading...' : 'View Stats'}
      </button>
      {loading && <Spinner />}
      {error && <ErrorMsg msg={error} />}
      {result && <ResultBox data={result} />}
    </Section>
  );
};

export default UnifiedAgentPanel;