import React, { useState, useEffect } from 'react';

interface SkillInfo {
  skill_id: string;
  name: string;
  description: string;
  status: string;
  version: number;
  params_count: number;
  steps_count: number;
  success_rate: number;
  tags: string[];
}

interface CompileResult {
  compilation_id: string;
  success: boolean;
  skill_id: string | null;
  suggested_name: string;
  errors: string[];
  warnings: string[];
  params_count: number;
  steps_count: number;
  compilation_time_ms: number;
}

export const SkillCompilerPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [showCompile, setShowCompile] = useState(false);
  const [compileResult, setCompileResult] = useState<CompileResult | null>(null);
  const [formData, setFormData] = useState({ description: '', name: '', tags: '' });
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchStats(); }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/skill-compiler/stats');
      const data = await res.json();
      setStats(data);
      setSkills(data.skills || []);
    } catch (e) { console.error('Failed to fetch skill stats:', e); }
  };

  const compileSkill = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/skill-compiler/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...formData,
          tags: formData.tags.split(',').map(s => s.trim()).filter(Boolean),
        }),
      });
      const result = await res.json();
      setCompileResult(result);
      setShowCompile(false);
      fetchStats();
    } catch (e) { console.error('Compile failed:', e); }
    setLoading(false);
  };

  const verifySkill = async (skillId: string) => {
    await fetch('/api/skill-compiler/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ skill_id: skillId }),
    });
    fetchStats();
  };

  const activateSkill = async (skillId: string) => {
    await fetch('/api/skill-compiler/activate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ skill_id: skillId }),
    });
    fetchStats();
  };

  const statusColor = (s: string) => {
    const map: Record<string, string> = { active: '#16a34a', verified: '#3b82f6', tested: '#8b5cf6', compiled: '#f59e0b', draft: '#6b7280', deprecated: '#ef4444', failed: '#dc2626' };
    return map[s] || '#6b7280';
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Skill Compiler</h2>
          <p style={{ color: '#666', margin: '4px 0 0' }}>Compile natural language descriptions into executable skill definitions</p>
        </div>
        <button onClick={() => setShowCompile(true)} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
          + Compile Skill
        </button>
      </div>

      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <div style={{ flex: 1, background: '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a' }}>{stats.total_skills}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Skills</div>
          </div>
          <div style={{ flex: 1, background: '#eff6ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_compilations}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Compilations</div>
          </div>
          <div style={{ flex: 1, background: '#faf5ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#7c3aed' }}>{stats.active_skills || 0}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Active</div>
          </div>
          <div style={{ flex: 1, background: '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a' }}>{stats.verified_skills || 0}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Verified</div>
          </div>
        </div>
      )}

      {/* Compile Result Toast */}
      {compileResult && (
        <div style={{ position: 'fixed', bottom: 24, right: 24, background: compileResult.success ? '#f0fdf4' : '#fef2f2', borderRadius: 12, padding: 16, boxShadow: '0 4px 20px rgba(0,0,0,0.15)', maxWidth: 400, zIndex: 900, border: `2px solid ${compileResult.success ? '#16a34a' : '#ef4444'}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontWeight: 600, color: compileResult.success ? '#16a34a' : '#ef4444' }}>{compileResult.success ? 'Compiled' : 'Failed'}</span>
            <button onClick={() => setCompileResult(null)} style={{ border: 'none', background: 'none', cursor: 'pointer' }}>x</button>
          </div>
          <div style={{ fontSize: 12, color: '#666' }}>
            <div>Name: <strong>{compileResult.suggested_name}</strong></div>
            <div>Params: {compileResult.params_count} | Steps: {compileResult.steps_count}</div>
            <div>Time: {compileResult.compilation_time_ms.toFixed(1)}ms</div>
            {compileResult.errors.map((e, i) => <div key={i} style={{ color: '#ef4444' }}>{e}</div>)}
            {compileResult.warnings.map((w, i) => <div key={i} style={{ color: '#f59e0b' }}>{w}</div>)}
          </div>
        </div>
      )}

      {/* Skills Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
        {skills.map(skill => (
          <div key={skill.skill_id} style={{ background: '#fff', borderRadius: 12, padding: 16, border: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{skill.name}</div>
              <span style={{ background: statusColor(skill.status), color: '#fff', padding: '2px 8px', borderRadius: 6, fontSize: 11 }}>{skill.status}</span>
            </div>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>{skill.description}</div>
            <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#888', marginBottom: 8 }}>
              <span>v{skill.version}</span>
              <span>{skill.params_count} params</span>
              <span>{skill.steps_count} steps</span>
              <span>{(skill.success_rate * 100).toFixed(0)}% success</span>
            </div>
            {skill.tags.length > 0 && (
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
                {skill.tags.map(tag => (
                  <span key={tag} style={{ background: '#f3f4f6', padding: '2px 8px', borderRadius: 6, fontSize: 11 }}>{tag}</span>
                ))}
              </div>
            )}
            <div style={{ display: 'flex', gap: 8 }}>
              {skill.status === 'compiled' && (
                <button onClick={() => verifySkill(skill.skill_id)} style={{ padding: '4px 12px', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 6, cursor: 'pointer', fontSize: 12, color: '#2563eb' }}>Verify</button>
              )}
              {(skill.status === 'tested' || skill.status === 'verified') && (
                <button onClick={() => activateSkill(skill.skill_id)} style={{ padding: '4px 12px', background: '#f0fdf4', border: '1px solid #86efac', borderRadius: 6, cursor: 'pointer', fontSize: 12, color: '#16a34a' }}>Activate</button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Compile Modal */}
      {showCompile && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: '#fff', borderRadius: 16, padding: 24, width: 500 }}>
            <h3 style={{ marginBottom: 16 }}>Compile Skill from Description</h3>
            <div style={{ display: 'grid', gap: 10 }}>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Description</label><textarea value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} rows={4} placeholder="Describe what the skill should do..." style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', resize: 'vertical' }} /></div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Name (optional)</label><input value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} placeholder="Auto-generated if empty" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Tags (comma-separated)</label><input value={formData.tags} onChange={e => setFormData({ ...formData, tags: e.target.value })} placeholder="code, data, automation" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
              <button onClick={() => setShowCompile(false)} style={{ padding: '8px 16px', background: '#e5e7eb', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
              <button onClick={compileSkill} disabled={loading} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>{loading ? 'Compiling...' : 'Compile'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};