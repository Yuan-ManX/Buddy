import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#0891b2',
  secondary: '#22d3ee',
  bg: '#ecfeff',
  border: '#67e8f9',
  accent: '#cffafe',
  text: '#155e75',
};

export const VoiceInterfacePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'transcribe' | 'synthesize' | 'tone' | 'profiles'>('overview');

  const [transcribeForm, setTranscribeForm] = useState({ audio_text: '', language: '' });
  const [transcribeResult, setTranscribeResult] = useState<any>(null);

  const [synthesizeForm, setSynthesizeForm] = useState({
    text: '', voice_profile: '', language: '', speed: '1.0', pitch: '1.0', format: 'mp3',
  });
  const [synthesizeResult, setSynthesizeResult] = useState<any>(null);

  const [toneForm, setToneForm] = useState({ text: '', energy_level: '0.5', speaking_rate: '1.0' });
  const [toneResult, setToneResult] = useState<any>(null);

  const [profiles, setProfiles] = useState<any[] | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.voiceInterface.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load voice interface data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleTranscribe = async () => {
    if (!transcribeForm.audio_text.trim()) return;
    try {
      const result = await api.voiceInterface.transcribe({
        audio_text: transcribeForm.audio_text,
        language: transcribeForm.language || undefined,
      });
      setTranscribeResult(result);
      toast.success('Transcription completed');
      setTranscribeForm({ audio_text: '', language: '' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSynthesize = async () => {
    if (!synthesizeForm.text.trim()) return;
    try {
      const result = await api.voiceInterface.synthesize({
        text: synthesizeForm.text,
        voice_profile: synthesizeForm.voice_profile || undefined,
        language: synthesizeForm.language || undefined,
        speed: parseFloat(synthesizeForm.speed),
        pitch: parseFloat(synthesizeForm.pitch),
        format: synthesizeForm.format,
      });
      setSynthesizeResult(result);
      toast.success('Speech synthesized');
      setSynthesizeForm({ text: '', voice_profile: '', language: '', speed: '1.0', pitch: '1.0', format: 'mp3' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAnalyzeTone = async () => {
    if (!toneForm.text.trim()) return;
    try {
      const result = await api.voiceInterface.analyzeTone({
        text: toneForm.text,
        energy_level: parseFloat(toneForm.energy_level),
        speaking_rate: parseFloat(toneForm.speaking_rate),
      });
      setToneResult(result);
      toast.success('Tone analysis completed');
      setToneForm({ text: '', energy_level: '0.5', speaking_rate: '1.0' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleLoadProfiles = async () => {
    try {
      const p = await api.voiceInterface.profiles();
      setProfiles(p.profiles || p.items || p);
      toast.success('Voice profiles loaded');
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🎤 Voice Interface Engine</h2>
          <p className="panel-subtitle">Transcribe, synthesize, and analyze voice with tone intelligence</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading voice interface...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>🎤 Voice Interface Engine</h2>
        <p className="panel-subtitle">Transcribe, synthesize, and analyze voice with tone intelligence</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_sessions ?? stats.session_count ?? '-'}</span><span className="stat-label">Sessions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_transcriptions ?? stats.transcription_count ?? '-'}</span><span className="stat-label">Transcriptions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_syntheses ?? stats.synthesis_count ?? '-'}</span><span className="stat-label">Syntheses</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_analyses ?? stats.analysis_count ?? '-'}</span><span className="stat-label">Analyses</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'transcribe', 'synthesize', 'tone', 'profiles'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
            style={activeSection === s ? { background: themeColors.primary, borderColor: themeColors.primary } : {}}
          >
            {s === 'tone' ? 'Tone Analysis' : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
            {Object.entries(stats).filter(([k]) => !['by_language', 'by_voice_profile'].includes(k)).map(([key, value]: [string, any]) => (
              <div key={key} style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontSize: '0.85rem', color: '#6b7280', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>
                  {typeof value === 'number' ? value : typeof value === 'object' ? JSON.stringify(value).slice(0, 40) : String(value)}
                </div>
              </div>
            ))}
          </div>
          {stats.by_language && Object.keys(stats.by_language).length > 0 && (
            <div style={{ marginTop: 20 }}>
              <h4 style={{ color: themeColors.text }}>By Language</h4>
              {Object.entries(stats.by_language).map(([lang, count]: [string, any]) => (
                <div key={lang} className="dashboard-stat-row">
                  <span style={{ fontWeight: 500 }}>{lang}</span>
                  <strong style={{ color: themeColors.primary }}>{count}</strong>
                </div>
              ))}
            </div>
          )}
          {!stats.by_language && !stats.total_sessions && (
            <div className="panel-empty">No voice interface data yet. Start by transcribing or synthesizing.</div>
          )}
        </div>
      )}

      {/* Transcribe */}
      {activeSection === 'transcribe' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Speech-to-Text Transcription</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Audio Text / Description</label>
              <textarea
                rows={4}
                value={transcribeForm.audio_text}
                onChange={e => setTranscribeForm(f => ({ ...f, audio_text: e.target.value }))}
                placeholder="Enter audio description or text to transcribe..."
              />
            </div>
            <div className="form-group">
              <label>Language (optional)</label>
              <input type="text" value={transcribeForm.language}
                onChange={e => setTranscribeForm(f => ({ ...f, language: e.target.value }))}
                placeholder="en-US, zh-CN, etc." />
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleTranscribe}>Transcribe</button>
          </div>
          {transcribeResult && (
            <div style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Transcription Result</h4>
              <pre style={{ whiteSpace: 'pre-wrap', color: themeColors.text, background: '#fff', padding: 12, borderRadius: 6, marginTop: 8 }}>
                {typeof transcribeResult === 'string' ? transcribeResult : JSON.stringify(transcribeResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Synthesize */}
      {activeSection === 'synthesize' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Text-to-Speech Synthesis</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Text to Synthesize</label>
              <textarea
                rows={4}
                value={synthesizeForm.text}
                onChange={e => setSynthesizeForm(f => ({ ...f, text: e.target.value }))}
                placeholder="Enter text to convert to speech..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Voice Profile</label>
                <input type="text" value={synthesizeForm.voice_profile}
                  onChange={e => setSynthesizeForm(f => ({ ...f, voice_profile: e.target.value }))}
                  placeholder="e.g., default, female-1" />
              </div>
              <div className="form-group">
                <label>Language</label>
                <input type="text" value={synthesizeForm.language}
                  onChange={e => setSynthesizeForm(f => ({ ...f, language: e.target.value }))}
                  placeholder="en-US" />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Speed ({synthesizeForm.speed})</label>
                <input type="range" min="0.5" max="2.0" step="0.1" value={synthesizeForm.speed}
                  onChange={e => setSynthesizeForm(f => ({ ...f, speed: e.target.value }))} />
              </div>
              <div className="form-group">
                <label>Pitch ({synthesizeForm.pitch})</label>
                <input type="range" min="0.5" max="2.0" step="0.1" value={synthesizeForm.pitch}
                  onChange={e => setSynthesizeForm(f => ({ ...f, pitch: e.target.value }))} />
              </div>
              <div className="form-group">
                <label>Format</label>
                <select value={synthesizeForm.format} onChange={e => setSynthesizeForm(f => ({ ...f, format: e.target.value }))}>
                  {['mp3', 'wav', 'ogg', 'aac'].map(f => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleSynthesize}>Synthesize Speech</button>
          </div>
          {synthesizeResult && (
            <div style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Synthesis Result</h4>
              <pre style={{ whiteSpace: 'pre-wrap', color: themeColors.text, background: '#fff', padding: 12, borderRadius: 6, marginTop: 8 }}>
                {typeof synthesizeResult === 'string' ? synthesizeResult : JSON.stringify(synthesizeResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Tone Analysis */}
      {activeSection === 'tone' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Tone Analysis</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Text to Analyze</label>
              <textarea
                rows={4}
                value={toneForm.text}
                onChange={e => setToneForm(f => ({ ...f, text: e.target.value }))}
                placeholder="Enter text to analyze tone..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Energy Level ({toneForm.energy_level})</label>
                <input type="range" min="0" max="1" step="0.1" value={toneForm.energy_level}
                  onChange={e => setToneForm(f => ({ ...f, energy_level: e.target.value }))} />
              </div>
              <div className="form-group">
                <label>Speaking Rate ({toneForm.speaking_rate})</label>
                <input type="range" min="0.5" max="2.0" step="0.1" value={toneForm.speaking_rate}
                  onChange={e => setToneForm(f => ({ ...f, speaking_rate: e.target.value }))} />
              </div>
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleAnalyzeTone}>Analyze Tone</button>
          </div>
          {toneResult && (
            <div style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Tone Analysis Result</h4>
              <div style={{ marginTop: 8 }}>
                {Object.entries(toneResult).map(([key, value]: [string, any]) => (
                  <div key={key} className="dashboard-stat-row" style={{ padding: '8px 0' }}>
                    <span style={{ fontWeight: 500, textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</span>
                    <strong style={{ color: themeColors.primary }}>
                      {typeof value === 'number' ? value.toFixed(2) : String(value)}
                    </strong>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Profiles */}
      {activeSection === 'profiles' && (
        <div className="dashboard-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Voice Profiles</h3>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleLoadProfiles}>Load Profiles</button>
          </div>
          {profiles ? (
            profiles.length === 0 ? (
              <div className="panel-empty">No voice profiles available</div>
            ) : (
              <div className="forge-skill-list">
                {profiles.map((profile: any, idx: number) => (
                  <div key={profile.id || profile.name || idx} className="forge-skill-card" style={{ borderLeft: `4px solid ${themeColors.primary}` }}>
                    <div className="forge-skill-header">
                      <div className="forge-skill-name" style={{ color: themeColors.text }}>{profile.name || profile.voice_profile || `Profile ${idx + 1}`}</div>
                      <span className="dashboard-badge" style={{ background: themeColors.primary, color: '#fff' }}>
                        {profile.language || profile.lang || 'N/A'}
                      </span>
                    </div>
                    <div className="forge-skill-meta">
                      {Object.entries(profile).filter(([k]) => !['name', 'voice_profile', 'language', 'lang'].includes(k)).map(([key, value]: [string, any]) => (
                        <div key={key}>{key.replace(/_/g, ' ')}: {typeof value === 'object' ? JSON.stringify(value).slice(0, 50) : String(value)}</div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            <div className="panel-empty">Click "Load Profiles" to view available voice profiles</div>
          )}
        </div>
      )}
    </div>
  );
};

export default VoiceInterfacePanel;