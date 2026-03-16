import React, { useState, useEffect, useRef, useCallback } from 'react';

const API = 'http://localhost:8000';

const CATEGORIES = [
  { value: '', label: 'All categories' },
  { value: 'basic_navigation', label: 'Basic Navigation' },
  { value: 'cast_and_crew', label: 'Cast & Crew' },
  { value: 'movie_details', label: 'Movie Details' },
  { value: 'tv_shows_episodes', label: 'TV Shows & Episodes' },
  { value: 'charts_rankings', label: 'Charts & Rankings' },
  { value: 'advanced_search', label: 'Advanced Search' },
  { value: 'user_features', label: 'User Features' },
  { value: 'complex_tasks', label: 'Complex Tasks' },
];

const DIFFICULTIES = [
  { value: '', label: 'All difficulties' },
  { value: 'basic', label: 'Basic' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
  { value: 'expert', label: 'Expert' },
];

function fmt(val, suffix = '') {
  if (val == null) return '—';
  return `${val}${suffix}`;
}

function ScoreBadge({ score }) {
  if (score == null) return <span style={s.badge.none}>—</span>;
  const color = score >= 7 ? '#22c55e' : score >= 5 ? '#f5c518' : '#ef4444';
  return (
    <span style={{ ...s.badge.base, color, borderColor: color }}>
      {score.toFixed(1)}
    </span>
  );
}

function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const yyyy = d.getFullYear();
  const hh = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${dd}/${mm}/${yyyy} ${hh}:${min}`;
}

function RunCard({ run, onSelect, onDelete, active }) {
  const date = fmtDate(run.generated_at) || run.run_id;
  return (
    <div style={{ ...s.runCard, ...(active ? s.runCardActive : {}), position: 'relative' }}>
      <button
        onClick={e => onDelete(run.run_id, e)}
        title="Delete run"
        style={{ position:'absolute', top:8, right:8, background:'transparent', border:'1px solid #444', borderRadius:4, color:'#ef4444', fontSize:12, padding:'1px 7px', cursor:'pointer' }}
      >✕</button>
      <div style={{ cursor: 'pointer' }} onClick={() => onSelect(run.run_id)}>
        <div style={s.runCardId}>{run.run_id}</div>
        <div style={s.runCardDate}>{date}</div>
        <div style={s.runCardStats}>
          <span>{run.questions ?? '?'} questions</span>
          {run.pass_rate_pct != null && (
            <span style={{ color: '#22c55e' }}>{run.pass_rate_pct}% pass</span>
          )}
          {run.avg_score != null && (
            <ScoreBadge score={run.avg_score} />
          )}
        </div>
      </div>
    </div>
  );
}

function SummaryPanel({ summary }) {
  const t = summary.totals || {};
  const sc = summary.scores || {};
  const dims = sc.dimensions || {};

  return (
    <div style={s.summaryWrap}>
      <div style={s.summaryTitle}>
        Run: <code style={s.code}>{summary.run_id}</code>
      </div>

      {/* Key numbers */}
      <div style={s.metaGrid}>
        <Metric label="Questions" value={t.questions} />
        <Metric label="Errors" value={t.errors} warn={t.errors > 0} />
        <Metric label="Pass rate" value={fmt(t.pass_rate_pct, '%')} highlight />
        <Metric label="Avg score" value={fmt(sc.average_overall)} highlight />
        <Metric label="Graph hits" value={fmt(t.graph_hit_rate_pct, '%')} />
        <Metric label="Videos" value={t.videos_recorded} />
      </div>

      {/* Dimension scores */}
      {Object.keys(dims).length > 0 && (
        <div style={s.section}>
          <div style={s.sectionTitle}>Judge Dimensions</div>
          <div style={s.dimGrid}>
            {Object.entries(dims).map(([k, v]) => (
              <div key={k} style={s.dimItem}>
                <div style={s.dimLabel}>{k.replace(/_/g, ' ')}</div>
                <ScoreBadge score={v} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* By category */}
      {summary.by_category && (
        <div style={s.section}>
          <div style={s.sectionTitle}>By Category</div>
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>Category</th>
                <th style={s.th}>Total</th>
                <th style={s.th}>Pass</th>
                <th style={s.th}>Avg</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(summary.by_category).map(([cat, info]) => (
                <tr key={cat}>
                  <td style={s.td}>{cat.replace(/_/g, ' ')}</td>
                  <td style={s.tdNum}>{info.total}</td>
                  <td style={s.tdNum}>{fmt(info.pass_rate_pct, '%')}</td>
                  <td style={s.tdNum}><ScoreBadge score={info.avg_score} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Top failures */}
      {summary.top_failures && summary.top_failures.length > 0 && (
        <div style={s.section}>
          <div style={s.sectionTitle}>Lowest scoring questions</div>
          {summary.top_failures.slice(0, 10).map(f => (
            <div key={f.id} style={s.failItem}>
              <div style={s.failHeader}>
                <span style={s.failId}>#{f.id}</span>
                <span style={s.failCat}>{f.category}</span>
                <ScoreBadge score={f.overall_score} />
              </div>
              <div style={s.failQ}>{f.question}</div>
              {f.reasoning && (
                <div style={s.failReason}>{f.reasoning}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, highlight, warn }) {
  return (
    <div style={s.metric}>
      <div style={s.metricLabel}>{label}</div>
      <div style={{
        ...s.metricValue,
        color: warn ? '#ef4444' : highlight ? '#f5c518' : '#e0e4f0',
      }}>
        {value ?? '—'}
      </div>
    </div>
  );
}

function LiveLog({ recent }) {
  if (!recent || recent.length === 0) return null;
  return (
    <div style={s.liveLog}>
      <div style={s.liveLogTitle}>Last completed</div>
      {[...recent].reverse().map((r, i) => {
        const icon = r.error ? '❌' : r.passed === true ? '✅' : r.passed === false ? '⚠️' : '⏳';
        const scoreColor = r.overall >= 7 ? '#22c55e' : r.overall >= 5 ? '#f5c518' : r.overall != null ? '#ef4444' : '#8b92a5';
        return (
          <div key={i} style={{ ...s.logRow, opacity: i === 0 ? 1 : 0.65 }}>
            <span style={s.logIcon}>{icon}</span>
            <div style={s.logBody}>
              <div style={s.logQ}>{r.question}{r.question.length >= 80 ? '…' : ''}</div>
              <div style={s.logMeta}>
                <span style={s.logCat}>{r.category?.replace(/_/g, ' ')}</span>
                <span style={s.logDiff}>{r.difficulty}</span>
                {r.graph_miss ? <span style={s.logMiss}>graph miss</span> : <span style={s.logHit}>graph hit</span>}
                {r.video ? <span style={s.logVideo}>🎬</span> : null}
                {r.error ? <span style={s.logErrBadge}>error</span> : null}
              </div>
            </div>
            <div style={{ ...s.logScore, color: scoreColor }}>
              {r.overall != null ? r.overall.toFixed(1) : '—'}
            </div>
          </div>
        );
      })}
    </div>
  );
}

const ACTIVE_RUN_KEY = 'imdb_active_run_id';

export default function TestRunner() {
  const [category, setCategory] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [limit, setLimit] = useState('');
  const [ids, setIds] = useState('');
  const [noJudge, setNoJudge] = useState(false);
  const [noVideo, setNoVideo] = useState(false);

  const [running, setRunning] = useState(false);
  const [currentRun, setCurrentRun] = useState(null);
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [selectedSummary, setSelectedSummary] = useState(null);

  const pollRef = useRef(null);

  const loadRuns = useCallback(async () => {
    try {
      const res = await fetch(`${API}/tests/runs`);
      if (res.ok) setRuns(await res.json());
    } catch (_) {}
  }, []);

  const startPolling = useCallback((runId) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API}/tests/status/${runId}`);
        if (!res.ok) return;
        const data = await res.json();
        setCurrentRun(prev => ({ ...prev, ...data }));
        if (data.status === 'done' || data.status === 'error' || data.status === 'stopped') {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setRunning(false);
          localStorage.removeItem(ACTIVE_RUN_KEY);
          loadRuns();
          if (data.status === 'done') selectRun(runId);
        }
      } catch (_) {}
    }, 1500);
  }, [loadRuns]);

  // On mount: restore any in-progress run from localStorage so closing/reopening
  // the browser tab doesn't lose the live progress view.
  useEffect(() => {
    loadRuns();
    const savedRunId = localStorage.getItem(ACTIVE_RUN_KEY);
    if (!savedRunId) return;
    fetch(`${API}/tests/status/${savedRunId}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data) { localStorage.removeItem(ACTIVE_RUN_KEY); return; }
        setCurrentRun(data);
        if (data.status === 'running') {
          setRunning(true);
          startPolling(savedRunId);
        } else {
          localStorage.removeItem(ACTIVE_RUN_KEY);
        }
      })
      .catch(() => localStorage.removeItem(ACTIVE_RUN_KEY));
  }, []);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const startRun = async () => {
    setRunning(true);
    setSelectedSummary(null);
    setSelectedRunId(null);
    try {
      const body = {};
      if (category) body.category = category;
      if (difficulty) body.difficulty = difficulty;
      if (ids.trim()) body.ids = ids.trim();
      if (limit) body.limit = parseInt(limit, 10);
      body.no_judge = noJudge;
      body.no_video = noVideo;

      const res = await fetch(`${API}/tests/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(`Error starting run: ${err.detail || res.statusText}`);
        setRunning(false);
        return;
      }
      const { run_id, total } = await res.json();
      setCurrentRun({ run_id, total, completed: 0, status: 'running', recent: [] });
      localStorage.setItem(ACTIVE_RUN_KEY, run_id);
      startPolling(run_id);
    } catch (e) {
      alert(`Failed to start run: ${e.message}`);
      setRunning(false);
    }
  };

  const stopRun = async () => {
    if (!currentRun) return;
    try {
      await fetch(`${API}/tests/stop/${currentRun.run_id}`, { method: 'POST' });
      setRunning(false);
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
      localStorage.removeItem(ACTIVE_RUN_KEY);
      setCurrentRun(prev => ({ ...prev, status: 'stopped' }));
      loadRuns();
    } catch (e) {
      alert(`Failed to stop run: ${e.message}`);
    }
  };

  const selectRun = async (runId) => {
    setSelectedRunId(runId);
    setSelectedSummary(null);
    try {
      const res = await fetch(`${API}/tests/runs/${runId}`);
      if (res.ok) setSelectedSummary(await res.json());
    } catch (_) {}
  };

  const deleteRun = async (runId, e) => {
    e.stopPropagation();
    if (!window.confirm(`Delete run "${runId}" and its videos? This cannot be undone.`)) return;
    try {
      const res = await fetch(`${API}/tests/runs/${runId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(await res.text());
      setRuns(prev => prev.filter(r => r.run_id !== runId));
      if (selectedRunId === runId) { setSelectedRunId(null); setSelectedSummary(null); }
    } catch (err) { alert('Delete failed: ' + err.message); }
  };

  const progress = currentRun
    ? Math.min(100, Math.round((currentRun.completed / (currentRun.total || 1)) * 100))
    : 0;

  const isActive = running || (currentRun && currentRun.status === 'running');
  const statusIcon = !currentRun ? null
    : currentRun.status === 'done' ? '✅'
    : currentRun.status === 'stopped' ? '⛔'
    : currentRun.status === 'error' ? '❌'
    : '🔄';

  return (
    <div style={s.root}>
      {/* ── Config panel ──────────────────────────────────────── */}
      <div style={s.configPanel}>
        <div style={s.panelTitle}>Run Tests</div>

        <label style={s.label}>Category</label>
        <select style={s.select} value={category} onChange={e => setCategory(e.target.value)} disabled={isActive}>
          {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>

        <label style={s.label}>Difficulty</label>
        <select style={s.select} value={difficulty} onChange={e => setDifficulty(e.target.value)} disabled={isActive}>
          {DIFFICULTIES.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
        </select>

        <label style={s.label}>Limit (max questions)</label>
        <input style={s.input} type="number" min={1} max={200} placeholder="all"
          value={limit} onChange={e => setLimit(e.target.value)} disabled={isActive} />

        <label style={s.label}>Specific IDs (e.g. 1,5,12)</label>
        <input style={s.input} type="text" placeholder="leave blank for all"
          value={ids} onChange={e => setIds(e.target.value)} disabled={isActive} />

        <div style={s.toggleRow}>
          <label style={s.toggleLabel}>
            <input type="checkbox" checked={noJudge} onChange={e => setNoJudge(e.target.checked)} disabled={isActive} />
            &nbsp;Skip AI Judge
          </label>
        </div>

        <div style={s.toggleRow}>
          <label style={s.toggleLabel}>
            <input type="checkbox" checked={noVideo} onChange={e => setNoVideo(e.target.checked)} disabled={isActive} />
            &nbsp;Skip video recording
          </label>
        </div>

        {/* Start / Stop buttons */}
        <div style={s.btnRow}>
          <button
            style={{ ...s.runBtn, ...(isActive ? s.runBtnDisabled : {}) }}
            onClick={startRun}
            disabled={isActive}
          >
            {isActive ? '▶ Running…' : '▶ Start Test Run'}
          </button>
          {isActive && (
            <button style={s.stopBtn} onClick={stopRun}>⛔ Stop</button>
          )}
        </div>

        {/* ── Big progress block ── */}
        {currentRun && (
          <div style={s.progressWrap}>
            {/* Percentage — large */}
            <div style={s.progressPct}>{progress}%</div>

            {/* Count */}
            <div style={s.progressCountRow}>
              <span style={s.progressStatus}>{statusIcon} {currentRun.status}</span>
              <span style={s.progressCount}>{currentRun.completed} / {currentRun.total}</span>
            </div>

            {/* Bar */}
            <div style={s.progressTrack}>
              <div style={{
                ...s.progressBar,
                width: `${progress}%`,
                background: currentRun.status === 'stopped' ? '#ef4444'
                  : currentRun.status === 'error' ? '#ef4444'
                  : currentRun.status === 'done' ? '#22c55e'
                  : '#f5c518',
              }} />
            </div>

            <div style={s.progressRunId}><code style={s.code}>{currentRun.run_id}</code></div>

            {/* Live log */}
            <LiveLog recent={currentRun.recent} />
          </div>
        )}
      </div>

      {/* ── Results panel ─────────────────────────────────────── */}
      <div style={s.resultsPanel}>
        {selectedSummary ? (
          <>
            <button style={s.backBtn} onClick={() => { setSelectedSummary(null); setSelectedRunId(null); }}>
              ← Back to runs
            </button>
            <SummaryPanel summary={selectedSummary} />
          </>
        ) : (
          <>
            <div style={s.panelTitle}>Past Runs</div>
            {runs.length === 0 ? (
              <div style={s.empty}>No completed runs yet. Start a test run to see results here.</div>
            ) : (
              <div style={s.runsList}>
                {runs.map(run => (
                  <RunCard
                    key={run.run_id}
                    run={run}
                    onSelect={selectRun}
                    onDelete={deleteRun}
                    active={run.run_id === selectedRunId}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

const s = {
  root: {
    display: 'flex',
    gap: '28px',
    height: '100%',
    overflow: 'hidden',
  },
  configPanel: {
    width: '300px',
    flexShrink: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    overflowY: 'auto',
    paddingRight: '12px',
    paddingBottom: '20px',
  },
  resultsPanel: {
    flex: 1,
    overflowY: 'auto',
    minWidth: 0,
    paddingBottom: '20px',
  },
  panelTitle: {
    fontSize: '16px',
    fontWeight: '700',
    color: '#f5c518',
    textTransform: 'uppercase',
    letterSpacing: '.6px',
    marginBottom: '6px',
  },
  label: {
    fontSize: '13px',
    color: '#8b92a5',
    marginTop: '6px',
  },
  select: {
    width: '100%',
    background: '#131620',
    border: '1px solid #2a2e42',
    borderRadius: '6px',
    color: '#e0e4f0',
    padding: '8px 10px',
    fontSize: '14px',
  },
  input: {
    width: '100%',
    background: '#131620',
    border: '1px solid #2a2e42',
    borderRadius: '6px',
    color: '#e0e4f0',
    padding: '8px 10px',
    fontSize: '14px',
    boxSizing: 'border-box',
  },
  toggleRow: {
    marginTop: '6px',
  },
  toggleLabel: {
    display: 'flex',
    alignItems: 'center',
    fontSize: '14px',
    color: '#e0e4f0',
    cursor: 'pointer',
    gap: '6px',
  },
  runBtn: {
    flex: 1,
    background: '#f5c518',
    color: '#0d0d0d',
    border: 'none',
    borderRadius: '8px',
    padding: '13px 0',
    fontWeight: '700',
    fontSize: '15px',
    cursor: 'pointer',
    width: '100%',
  },
  btnRow: {
    display: 'flex',
    gap: '8px',
    marginTop: '16px',
  },
  stopBtn: {
    background: '#2a1010',
    color: '#ef4444',
    border: '1px solid #ef4444',
    borderRadius: '8px',
    padding: '13px 14px',
    fontWeight: '700',
    fontSize: '14px',
    cursor: 'pointer',
    flexShrink: 0,
  },
  runBtnDisabled: {
    background: '#2a2e42',
    color: '#8b92a5',
    cursor: 'not-allowed',
  },
  progressWrap: {
    marginTop: '16px',
    background: '#131620',
    border: '1px solid #2a2e42',
    borderRadius: '10px',
    padding: '16px 16px 12px',
  },
  progressPct: {
    fontSize: '52px',
    fontWeight: '900',
    color: '#f5c518',
    lineHeight: '1',
    marginBottom: '6px',
    letterSpacing: '-2px',
  },
  progressCountRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px',
  },
  progressStatus: {
    fontSize: '13px',
    color: '#e0e4f0',
    textTransform: 'capitalize',
  },
  progressCount: {
    fontSize: '16px',
    fontWeight: '700',
    color: '#e0e4f0',
  },
  progressTrack: {
    height: '10px',
    background: '#2a2e42',
    borderRadius: '5px',
    overflow: 'hidden',
    marginBottom: '8px',
  },
  progressBar: {
    height: '100%',
    borderRadius: '5px',
    transition: 'width .4s',
  },
  progressRunId: {
    fontSize: '11px',
    color: '#8b92a5',
    marginBottom: '12px',
  },
  liveLog: {
    borderTop: '1px solid #2a2e42',
    paddingTop: '10px',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  liveLogTitle: {
    fontSize: '10px',
    color: '#8b92a5',
    textTransform: 'uppercase',
    letterSpacing: '.6px',
    marginBottom: '4px',
  },
  logRow: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '8px',
    background: '#0d1017',
    borderRadius: '6px',
    padding: '7px 10px',
  },
  logIcon: {
    fontSize: '14px',
    flexShrink: 0,
    marginTop: '1px',
  },
  logBody: {
    flex: 1,
    minWidth: 0,
  },
  logQ: {
    fontSize: '12px',
    color: '#e0e4f0',
    marginBottom: '3px',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  logMeta: {
    display: 'flex',
    gap: '5px',
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  logCat: {
    fontSize: '10px',
    color: '#8b92a5',
    background: '#1e2235',
    padding: '1px 5px',
    borderRadius: '3px',
    textTransform: 'capitalize',
  },
  logDiff: {
    fontSize: '10px',
    color: '#8b92a5',
    background: '#1e2235',
    padding: '1px 5px',
    borderRadius: '3px',
  },
  logHit: {
    fontSize: '10px',
    color: '#22c55e',
    background: '#0f2e1a',
    padding: '1px 5px',
    borderRadius: '3px',
  },
  logMiss: {
    fontSize: '10px',
    color: '#f5c518',
    background: '#2e2a10',
    padding: '1px 5px',
    borderRadius: '3px',
  },
  logVideo: {
    fontSize: '11px',
  },
  logErrBadge: {
    fontSize: '10px',
    color: '#ef4444',
    background: '#2e1010',
    padding: '1px 5px',
    borderRadius: '3px',
  },
  logScore: {
    fontSize: '16px',
    fontWeight: '800',
    flexShrink: 0,
    alignSelf: 'center',
  },
  backBtn: {
    background: 'transparent',
    border: '1px solid #2a2e42',
    borderRadius: '6px',
    color: '#8b92a5',
    fontSize: '14px',
    padding: '7px 14px',
    cursor: 'pointer',
    marginBottom: '20px',
  },
  runsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  runCard: {
    background: '#131620',
    border: '1px solid #2a2e42',
    borderRadius: '8px',
    padding: '14px 16px',
    cursor: 'pointer',
  },
  runCardActive: {
    borderColor: '#f5c518',
  },
  runCardId: {
    fontFamily: 'monospace',
    fontSize: '14px',
    color: '#f5c518',
    marginBottom: '3px',
  },
  runCardDate: {
    fontSize: '13px',
    color: '#8b92a5',
    marginBottom: '8px',
  },
  runCardStats: {
    display: 'flex',
    gap: '14px',
    fontSize: '14px',
    color: '#e0e4f0',
    alignItems: 'center',
  },
  empty: {
    color: '#8b92a5',
    fontSize: '15px',
    paddingTop: '20px',
  },
  summaryWrap: {
    display: 'flex',
    flexDirection: 'column',
    gap: '22px',
  },
  summaryTitle: {
    fontSize: '16px',
    color: '#e0e4f0',
    fontWeight: '600',
  },
  metaGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '12px',
  },
  metric: {
    background: '#131620',
    border: '1px solid #2a2e42',
    borderRadius: '8px',
    padding: '12px 14px',
  },
  metricLabel: {
    fontSize: '11px',
    color: '#8b92a5',
    textTransform: 'uppercase',
    letterSpacing: '.4px',
    marginBottom: '5px',
  },
  metricValue: {
    fontSize: '24px',
    fontWeight: '700',
  },
  section: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  sectionTitle: {
    fontSize: '13px',
    color: '#f5c518',
    textTransform: 'uppercase',
    letterSpacing: '.6px',
    fontWeight: '700',
  },
  dimGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '8px',
  },
  dimItem: {
    background: '#131620',
    border: '1px solid #2a2e42',
    borderRadius: '6px',
    padding: '8px 10px',
  },
  dimLabel: {
    fontSize: '12px',
    color: '#8b92a5',
    textTransform: 'capitalize',
    marginBottom: '5px',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '14px',
  },
  th: {
    textAlign: 'left',
    padding: '8px 10px',
    color: '#8b92a5',
    fontSize: '11px',
    textTransform: 'uppercase',
    letterSpacing: '.4px',
    borderBottom: '1px solid #2a2e42',
  },
  td: {
    padding: '9px 10px',
    color: '#e0e4f0',
    borderBottom: '1px solid #1a1e2e',
    textTransform: 'capitalize',
  },
  tdNum: {
    padding: '9px 10px',
    color: '#e0e4f0',
    borderBottom: '1px solid #1a1e2e',
    textAlign: 'right',
  },
  failItem: {
    background: '#131620',
    border: '1px solid #2a2e42',
    borderRadius: '6px',
    padding: '12px 14px',
    marginBottom: '8px',
  },
  failHeader: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    marginBottom: '6px',
  },
  failId: {
    fontSize: '13px',
    color: '#8b92a5',
  },
  failCat: {
    fontSize: '12px',
    color: '#8b92a5',
    background: '#1e2235',
    padding: '2px 8px',
    borderRadius: '4px',
    textTransform: 'capitalize',
  },
  failQ: {
    fontSize: '14px',
    color: '#e0e4f0',
    marginBottom: '5px',
  },
  failReason: {
    fontSize: '13px',
    color: '#8b92a5',
    fontStyle: 'italic',
  },
  badge: {
    base: {
      display: 'inline-block',
      fontSize: '12px',
      fontWeight: '700',
      padding: '2px 7px',
      borderRadius: '4px',
      border: '1px solid',
    },
    none: {
      display: 'inline-block',
      fontSize: '12px',
      color: '#8b92a5',
    },
  },
  code: {
    background: '#0a0c14',
    padding: '1px 6px',
    borderRadius: '4px',
    color: '#f5c518',
    fontSize: '11px',
    fontFamily: 'monospace',
  },
};
