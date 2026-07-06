import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  RefreshCw, Play, CheckCircle, XCircle, Clock,
  Database, Briefcase, AlertCircle, Activity,
  TrendingUp, Zap, Globe, BarChart3, Terminal,
  Trash2, ArrowUpRight, Calendar, Timer, ToggleLeft, ToggleRight, ChevronDown
} from 'lucide-react';
import api from '../api/client';

interface SourceStatus {
  running: boolean; last_run: string|null; jobs_before: number;
  jobs_after: number; new_jobs: number; error: string|null;
  total_jobs: number; last_scraped: string|null;
}
interface ScrapingStatus { rooster: SourceStatus; topjobs: SourceStatus; }

const DEFAULT: SourceStatus = {
  running: false, last_run: null, jobs_before: 0,
  jobs_after: 0, new_jobs: 0, error: null, total_jobs: 0, last_scraped: null,
};

const fmt = (dt: string|null) => {
  if (!dt) return 'Never';
  try { return new Date(dt).toLocaleString('en-US', { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit', second:'2-digit' }); }
  catch { return dt; }
};

const ago = (dt: string|null) => {
  if (!dt) return 'Never';
  try {
    const s = Math.floor((Date.now() - new Date(dt).getTime()) / 1000);
    if (s < 60) return `${s}s ago`;
    if (s < 3600) return `${Math.floor(s/60)}m ago`;
    if (s < 86400) return `${Math.floor(s/3600)}h ago`;
    return `${Math.floor(s/86400)}d ago`;
  } catch { return ''; }
};

// ── Live Terminal ────────────────────────────────────────────
function Terminal_({ source, running }: { source: string; running: boolean }) {
  const [logs, setLogs] = useState<string[]>([]);
  const bottomRef       = useRef<HTMLDivElement>(null);

  const fetchLogs = useCallback(async () => {
    try { const r = await api.get(`/api/scrape/logs/${source}`); setLogs(r.data.logs || []); } catch {}
  }, [source]);

  const clear = async () => {
    try { await api.delete(`/api/scrape/logs/${source}`); setLogs([]); } catch {}
  };

  useEffect(() => {
    fetchLogs();
    const id = setInterval(fetchLogs, running ? 1500 : 8000);
    return () => clearInterval(id);
  }, [fetchLogs, running]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [logs]);

  const lineColor = (l: string) => {
    if (l.includes('ERROR') || l.includes('[ERR]')) return '#f87171';
    if (l.includes('TIMEOUT'))                        return '#fb923c';
    if (l.includes('WARN'))                           return '#fbbf24';
    if (l.includes('Done') || l.includes('complete') || l.includes('Pipeline done')) return '#34d399';
    if (l.includes('started'))                        return '#60a5fa';
    if (l.includes('new jobs') || l.includes('inserted')) return '#a78bfa';
    return 'rgba(226,232,240,0.7)';
  };

  return (
    <div className="rounded-xl overflow-hidden"
         style={{ border: '1px solid rgba(255,255,255,0.07)' }}>
      {/* Terminal header */}
      <div className="flex items-center justify-between px-4 py-2.5"
           style={{ background: 'rgba(255,255,255,0.04)', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500/60" />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
          </div>
          <span className="text-xs text-slate-400 ml-1"
                style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            {source}.log
          </span>
          {running && (
            <span className="flex items-center gap-1 text-xs"
                  style={{ color: '#34d399' }}>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              live
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-600" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            {logs.length} lines
          </span>
          <button onClick={clear}
            className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors">
            <Trash2 size={10} /> clear
          </button>
        </div>
      </div>

      {/* Terminal body */}
      <div className="h-44 overflow-y-auto p-3 space-y-0.5"
           style={{ background: '#00010a', fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>
        {logs.length === 0 ? (
          <p className="text-slate-700 italic" style={{ fontSize: 11 }}>
            {running ? '▌ Waiting for output...' : '// No logs yet. Click Scrape Now to start.'}
          </p>
        ) : (
          <>
            {logs.map((line, i) => (
              <p key={i} style={{ color: lineColor(line), lineHeight: 1.6 }}>{line}</p>
            ))}
            <div ref={bottomRef} />
          </>
        )}
      </div>
    </div>
  );
}

// ── Scraper Card ─────────────────────────────────────────────
function ScraperCard({ source, status, onScrape, cfg }: {
  source: 'rooster'|'topjobs'; status: SourceStatus;
  onScrape: () => void;
  cfg: { name: string; url: string; color: string; bg: string; border: string; };
}) {
  return (
    <div className="rounded-2xl overflow-hidden transition-all duration-300"
         style={{
           background: 'rgba(255,255,255,0.025)',
           border: status.running ? `1px solid rgba(59,130,246,0.4)` : '1px solid rgba(255,255,255,0.07)',
           boxShadow: status.running ? '0 0 32px rgba(59,130,246,0.08)' : 'none',
         }}>

      {/* Header */}
      <div className="px-6 py-5 flex items-start justify-between"
           style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center"
               style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}>
            <Globe size={22} style={{ color: cfg.color }} />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-0.5">
              <h3 className="font-bold text-white text-lg" style={{ fontFamily: "'Syne', sans-serif" }}>
                {cfg.name}
              </h3>
              {status.running && (
                <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs"
                      style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.25)', color: '#93c5fd' }}>
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                  Scraping...
                </span>
              )}
              {!status.running && status.last_run && !status.error && (
                <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs"
                      style={{ background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.2)', color: '#34d399' }}>
                  <CheckCircle size={9} /> Done
                </span>
              )}
              {status.error && (
                <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs"
                      style={{ background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.2)', color: '#f87171' }}>
                  <XCircle size={9} /> Error
                </span>
              )}
            </div>
            <p className="text-sm text-slate-500" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              {cfg.url}
            </p>
          </div>
        </div>

        <button onClick={onScrape} disabled={status.running}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm
                     transition-all active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
          style={status.running ? {
            background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(148,163,184,0.5)',
          } : {
            background: 'linear-gradient(135deg,#3b82f6,#2563eb)',
            boxShadow: '0 4px 16px rgba(37,99,235,0.3)',
            color: 'white',
          }}>
          {status.running
            ? <><RefreshCw size={14} className="animate-spin" /> Running...</>
            : <><Play size={14} /> Scrape Now</>}
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3"
           style={{ borderTop: '1px solid rgba(255,255,255,0.05)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        {[
          { label: 'Total Jobs',   value: status.total_jobs.toLocaleString(), icon: Database,  color: '#60a5fa', last: false },
          { label: 'New This Run', value: status.running ? '—' : (status.new_jobs > 0 ? `+${status.new_jobs}` : (status.last_run ? '0' : '—')),
            icon: TrendingUp, color: status.new_jobs > 0 ? '#34d399' : 'rgba(148,163,184,0.4)', last: false },
          { label: 'Last Scraped', value: ago(status.last_scraped), icon: Clock, color: '#fbbf24', last: true },
        ].map((s, i) => (
          <div key={i} className="px-5 py-4"
               style={{ borderRight: s.last ? 'none' : '1px solid rgba(255,255,255,0.05)' }}>
            <div className="flex items-center gap-1.5 mb-1.5">
              <s.icon size={12} style={{ color: s.color }} />
              <span className="text-xs text-slate-500 uppercase tracking-wider"
                    style={{ fontSize: '10px', fontFamily: "'DM Sans', sans-serif" }}>{s.label}</span>
            </div>
            <p className="text-xl font-bold" style={{ color: s.color, fontFamily: "'Syne', sans-serif" }}>
              {s.value}
            </p>
          </div>
        ))}
      </div>

      {/* Timeline + Terminal */}
      <div className="px-6 py-4 space-y-3">
        {/* Timeline rows */}
        {[
          { label: 'Last DB record',  value: fmt(status.last_scraped), dot: 'bg-slate-600' },
          ...(status.last_run ? [
            { label: 'Last session run', value: fmt(status.last_run), dot: status.error ? 'bg-rose-400' : 'bg-emerald-400' },
          ] : []),
          ...(status.last_run ? [
            { label: `${status.jobs_before} → ${status.jobs_after} jobs`, value: status.new_jobs > 0 ? `+${status.new_jobs} new` : '0 new', dot: 'bg-blue-400', highlight: status.new_jobs > 0 },
          ] : []),
        ].map((row, i) => (
          <div key={i} className="flex items-center justify-between px-3 py-2.5 rounded-xl"
               style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div className="flex items-center gap-2.5">
              <span className={`w-1.5 h-1.5 rounded-full ${row.dot}`} />
              <span className="text-xs text-slate-400" style={{ fontFamily: "'DM Sans', sans-serif" }}>{row.label}</span>
            </div>
            <span className="text-xs font-mono"
                  style={{ color: (row as any).highlight ? '#34d399' : 'rgba(226,232,240,0.7)',
                           fontFamily: "'JetBrains Mono', monospace" }}>
              {row.value}
            </span>
          </div>
        ))}

        {/* Error */}
        {status.error && (
          <div className="flex items-start gap-2.5 px-3 py-3 rounded-xl"
               style={{ background: 'rgba(244,63,94,0.06)', border: '1px solid rgba(244,63,94,0.15)' }}>
            <AlertCircle size={13} className="text-rose-400 shrink-0 mt-0.5" />
            <p className="text-xs text-rose-300" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              {status.error}
            </p>
          </div>
        )}

        {/* Progress */}
        {status.running && (
          <div className="px-3 py-3 rounded-xl"
               style={{ background: 'rgba(59,130,246,0.05)', border: '1px solid rgba(59,130,246,0.15)' }}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-blue-400 flex items-center gap-1.5">
                <Activity size={11} /> Scraping in progress...
              </span>
            </div>
            <div className="h-1 rounded-full overflow-hidden"
                 style={{ background: 'rgba(255,255,255,0.06)' }}>
              <div className="h-full rounded-full animate-pulse"
                   style={{ width: '75%', background: 'linear-gradient(90deg,#3b82f6,#7c3aed)' }} />
            </div>
          </div>
        )}

        {/* Live terminal */}
        <Terminal_ source={source} running={status.running} />
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────
export default function Scraping() {
  const [status,    setStatus]    = useState<ScrapingStatus|null>(null);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState('');
  const [lastFetch,  setLastFetch]  = useState(new Date());
  const [scheduler,  setScheduler]  = useState<any>(null);
  const [schedHrs,   setSchedHrs]   = useState(24);
  const [schedLoading, setSchedLoading] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const r = await api.get('/api/scrape/status');
      setStatus(r.data); setLastFetch(new Date()); setError('');
    } catch { setError('Cannot connect to API.'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    fetchStatus();
    const id = setInterval(fetchStatus, 3000);
    return () => clearInterval(id);
  }, [fetchStatus]);

  const fetchScheduler = useCallback(async () => {
    try { const r = await api.get('/api/scheduler/status'); setScheduler(r.data); } catch {}
  }, []);

  useEffect(() => {
    fetchScheduler();
    const id = setInterval(fetchScheduler, 10000);
    return () => clearInterval(id);
  }, [fetchScheduler]);

  const toggleScheduler = async () => {
    setSchedLoading(true);
    try {
      if (scheduler?.enabled) {
        await api.post('/api/scheduler/stop');
      } else {
        await api.post(`/api/scheduler/start?interval_hrs=${schedHrs}`);
      }
      await fetchScheduler();
    } catch {}
    setSchedLoading(false);
  };

  const scrape = async (source: 'rooster'|'topjobs') => {
    setError('');
    try { await api.post(`/api/scrape/${source}`); setTimeout(fetchStatus, 400); }
    catch (e: any) { setError(e?.response?.data?.detail || `Failed to start ${source}`); }
  };

  const scrapeAll = async () => {
    setError('');
    try {
      await api.post('/api/scrape/rooster');
      await new Promise(r => setTimeout(r, 300));
      await api.post('/api/scrape/topjobs');
      setTimeout(fetchStatus, 400);
    } catch (e: any) { setError(e?.response?.data?.detail || 'Failed to start scrapers'); }
  };

  const rooster    = status?.rooster || DEFAULT;
  const topjobs    = status?.topjobs || DEFAULT;
  const anyRunning = rooster.running || topjobs.running;
  const totalJobs  = rooster.total_jobs + topjobs.total_jobs;
  const totalNew   = rooster.new_jobs + topjobs.new_jobs;

  return (
    <div className="px-10 py-7 w-full animate-fade-in">

      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1"
              style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '-0.02em' }}>
            Job Scraping
          </h1>
          <p className="text-sm text-slate-400" style={{ fontFamily: "'DM Sans', sans-serif" }}>
            Live scraping · Selenium + BeautifulSoup · auto-refresh 3s
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              {lastFetch.toLocaleTimeString()}
            </span>
          </div>
          <button onClick={scrapeAll} disabled={anyRunning}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm
                       text-white transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            style={anyRunning ? {
              background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
            } : {
              background: 'linear-gradient(135deg,#3b82f6 0%,#7c3aed 100%)',
              boxShadow: '0 4px 20px rgba(59,130,246,0.25)',
            }}>
            {anyRunning ? <><RefreshCw size={14} className="animate-spin" /> Scraping...</>
              : <><Zap size={14} /> Scrape All Sources</>}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 px-5 py-4 rounded-2xl mb-6"
             style={{ background: 'rgba(244,63,94,0.07)', border: '1px solid rgba(244,63,94,0.18)' }}>
          <AlertCircle size={16} className="text-rose-400 shrink-0" />
          <p className="text-sm text-rose-300">{error}</p>
        </div>
      )}

      {/* Summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-5 mb-8">
        <div className="rounded-2xl px-4 py-4 animate-slide-up"
             style={{ background: 'rgba(59,130,246,0.06)', border: '1px solid rgba(59,130,246,0.14)' }}>
          <div className="flex items-center gap-2 mb-2">
            <Briefcase size={14} style={{ color: '#60a5fa' }} />
            <span className="text-xs text-slate-500" style={{ fontFamily: "'DM Sans', sans-serif" }}>Total Jobs</span>
          </div>
          <p className="text-2xl font-bold" style={{ color: '#60a5fa', fontFamily: "'Syne', sans-serif" }}>
            {loading ? '—' : totalJobs.toLocaleString()}
          </p>
        </div>
        <div className="rounded-2xl px-4 py-4 animate-slide-up"
             style={{ background: 'rgba(139,92,246,0.06)', border: '1px solid rgba(139,92,246,0.14)' }}>
          <div className="flex items-center gap-2 mb-2">
            <Database size={14} style={{ color: '#a78bfa' }} />
            <span className="text-xs text-slate-500" style={{ fontFamily: "'DM Sans', sans-serif" }}>Rooster Jobs</span>
          </div>
          <p className="text-2xl font-bold" style={{ color: '#a78bfa', fontFamily: "'Syne', sans-serif" }}>
            {loading ? '—' : rooster.total_jobs.toLocaleString()}
          </p>
        </div>
        <div className="rounded-2xl px-4 py-4 animate-slide-up"
             style={{ background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.14)' }}>
          <div className="flex items-center gap-2 mb-2">
            <Database size={14} style={{ color: '#34d399' }} />
            <span className="text-xs text-slate-500" style={{ fontFamily: "'DM Sans', sans-serif" }}>TopJobs</span>
          </div>
          <p className="text-2xl font-bold" style={{ color: '#34d399', fontFamily: "'Syne', sans-serif" }}>
            {loading ? '—' : topjobs.total_jobs.toLocaleString()}
          </p>
        </div>
        <div className="rounded-2xl px-4 py-4 animate-slide-up"
             style={{ background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.14)' }}>
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={14} style={{ color: totalNew > 0 ? '#fbbf24' : 'rgba(148,163,184,0.3)' }} />
            <span className="text-xs text-slate-500" style={{ fontFamily: "'DM Sans', sans-serif" }}>New This Session</span>
          </div>
          <p className="text-2xl font-bold" style={{ color: totalNew > 0 ? '#fbbf24' : 'rgba(148,163,184,0.3)', fontFamily: "'Syne', sans-serif" }}>
            {loading ? '—' : (totalNew > 0 ? `+${totalNew}` : '0')}
          </p>
        </div>
      </div>

      {/* Scraper cards */}
      {loading ? (
        <div className="space-y-4">
          {[...Array(2)].map((_, i) => <div key={i} className="h-64 rounded-2xl skeleton" />)}
        </div>
      ) : (
        <div className="space-y-5">
          <ScraperCard source="rooster" status={rooster} onScrape={() => scrape('rooster')}
            cfg={{ name:'Rooster.jobs', url:'rooster.jobs', color:'#a78bfa', bg:'rgba(139,92,246,0.08)', border:'rgba(139,92,246,0.2)' }} />
          <ScraperCard source="topjobs" status={topjobs} onScrape={() => scrape('topjobs')}
            cfg={{ name:'TopJobs.lk', url:'topjobs.lk', color:'#60a5fa', bg:'rgba(59,130,246,0.08)', border:'rgba(59,130,246,0.2)' }} />
        </div>
      )}

      {/* Auto-Scrape Scheduler */}
      <div className="mt-5 rounded-2xl overflow-hidden"
           style={{ background: 'rgba(255,255,255,0.025)', border: `1px solid ${scheduler?.enabled ? 'rgba(52,211,153,0.3)' : 'rgba(255,255,255,0.07)'}` }}>

        <div className="px-6 py-4 flex items-center justify-between"
             style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
                 style={{ background: scheduler?.enabled ? 'rgba(52,211,153,0.1)' : 'rgba(255,255,255,0.04)',
                          border: scheduler?.enabled ? '1px solid rgba(52,211,153,0.25)' : '1px solid rgba(255,255,255,0.08)' }}>
              <Calendar size={16} style={{ color: scheduler?.enabled ? '#34d399' : '#64748b' }} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                  Auto-Scrape Scheduler
                </h3>
                {scheduler?.enabled && (
                  <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full"
                        style={{ background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.2)', color: '#34d399' }}>
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Active
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-0.5" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                Automatically scrape both sources on a schedule
              </p>
            </div>
          </div>

          <button onClick={toggleScheduler} disabled={schedLoading}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm
                       transition-all active:scale-95 disabled:opacity-50"
            style={scheduler?.enabled ? {
              background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.2)', color: '#fda4af',
            } : {
              background: 'linear-gradient(135deg,#059669,#047857)',
              boxShadow: '0 4px 16px rgba(5,150,105,0.25)', color: 'white',
            }}>
            {schedLoading ? <RefreshCw size={14} className="animate-spin" /> :
             scheduler?.enabled ? <><XCircle size={14} /> Stop</> : <><Play size={14} /> Start</>}
          </button>
        </div>

        <div className="px-6 py-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            {[
              { label: 'Status',      value: scheduler?.enabled ? 'Running' : 'Stopped',
                color: scheduler?.enabled ? '#34d399' : 'rgba(148,163,184,0.4)' },
              { label: 'Interval',    value: `Every ${scheduler?.interval_hrs || schedHrs}h`,  color: '#60a5fa' },
              { label: 'Last Run',    value: scheduler?.last_run
                ? new Date(scheduler.last_run).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
                : 'Never',  color: '#fbbf24' },
              { label: 'Total Runs',  value: String(scheduler?.runs_total || 0),   color: '#a78bfa' },
            ].map(s => (
              <div key={s.label} className="rounded-xl px-4 py-3"
                   style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                <p className="text-xs text-slate-500 mb-1" style={{ fontSize: 10, fontFamily: "'DM Sans'", textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  {s.label}
                </p>
                <p className="text-sm font-bold" style={{ color: s.color, fontFamily: "'Syne', sans-serif" }}>
                  {s.value}
                </p>
              </div>
            ))}
          </div>

          {/* Interval selector */}
          <div className="flex items-center gap-4">
            <p className="text-xs text-slate-500 shrink-0" style={{ fontFamily: "'DM Sans'" }}>
              Scrape interval:
            </p>
            <div className="flex gap-2 flex-wrap">
              {[6, 12, 24, 48, 72].map(h => (
                <button key={h} onClick={() => setSchedHrs(h)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
                  style={schedHrs === h ? {
                    background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(59,130,246,0.3)', color: '#93c5fd',
                  } : {
                    background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(148,163,184,0.6)',
                  }}>
                  {h}h
                </button>
              ))}
            </div>
            {scheduler?.next_run && scheduler?.enabled && (
              <p className="text-xs text-slate-600 ml-auto" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                Next: {new Date(scheduler.next_run).toLocaleString('en-US', { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' })}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Info */}
      <div className="mt-6 flex items-start gap-3 px-5 py-4 rounded-2xl"
           style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
        <Activity size={14} className="text-blue-400 shrink-0 mt-0.5" />
        <p className="text-xs text-slate-500 leading-relaxed" style={{ fontFamily: "'DM Sans', sans-serif" }}>
          Scrapers use <span className="text-slate-300">Selenium + BeautifulSoup</span> inside the venv Python environment.
          New jobs are inserted into PostgreSQL after each run. Page auto-refreshes every 3 seconds.
          Average scrape time: 2–5 minutes per source.
        </p>
      </div>
    </div>
  );
}