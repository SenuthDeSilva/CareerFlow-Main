import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, RadialBarChart,
  RadialBar, Legend
} from 'recharts';
import {
  Briefcase, FileText, Users, TrendingUp, Upload,
  ChevronRight, RefreshCw, Database, Activity,
  Clock, Zap, Brain, Sparkles, ArrowUpRight,
  Target, BarChart3
} from 'lucide-react';
import { getStats, getResumes, Stats, Resume } from '../api/client';

// ── Animated counter ────────────────────────────────────────
function Counter({ value, duration = 1400 }: { value: number; duration?: number }) {
  const [n, setN] = useState(0);
  const raf = useRef<number | null>(null);
  useEffect(() => {
    const t0 = performance.now();
    const run = (now: number) => {
      const p    = Math.min((now - t0) / duration, 1);
      const ease = 1 - Math.pow(1 - p, 4);
      setN(Math.round(ease * value));
      if (p < 1) raf.current = requestAnimationFrame(run);
    };
    raf.current = requestAnimationFrame(run);
    return () => { if (raf.current !== null) cancelAnimationFrame(raf.current); };
  }, [value, duration]);
  return <>{n.toLocaleString()}</>;
}

// ── Glassmorphism tooltip ───────────────────────────────────
function GlassTooltip({ active, payload, label, formatter }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(3,7,18,0.92)', backdropFilter: 'blur(16px)',
      border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12,
      padding: '10px 14px', fontSize: 12,
    }}>
      {label && <p style={{ color: 'rgba(148,163,184,0.7)', marginBottom: 6, fontFamily: "'DM Sans', sans-serif" }}>{label}</p>}
      {payload.map((p: any, i: number) => (
        <p key={i} style={{ color: p.color || '#fff', fontFamily: "'JetBrains Mono', monospace" }}>
          {formatter ? formatter(p.value, p.name) : `${p.name}: ${p.value}`}
        </p>
      ))}
    </div>
  );
}

// ── Stat card ───────────────────────────────────────────────
function StatCard({ icon: Icon, label, value, sub, color, glow, delay = 0 }: {
  icon: any; label: string; value: number | string; sub?: string;
  color: string; glow: string; delay?: number;
}) {
  const [vis, setVis] = useState(false);
  useEffect(() => { const t = setTimeout(() => setVis(true), delay); return () => clearTimeout(t); }, [delay]);
  return (
    <div className={`relative overflow-hidden rounded-2xl p-5 transition-all duration-600
      ${vis ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-5'}`}
      style={{
        background: `linear-gradient(135deg, ${color}0f 0%, rgba(255,255,255,0.02) 100%)`,
        border: `1px solid ${color}28`,
        boxShadow: `0 4px 24px rgba(0,0,0,0.3), 0 0 48px ${glow}`,
      }}>
      <div className="absolute inset-0 bg-gradient-to-br from-white/4 to-transparent pointer-events-none" />
      <div className="relative flex items-start justify-between">
        <div>
          <p className="uppercase tracking-widest mb-3 font-medium"
             style={{ color: 'rgba(148,163,184,0.6)', fontSize: 10, letterSpacing: '0.1em', fontFamily: "'DM Sans', sans-serif" }}>
            {label}
          </p>
          <p className="text-3xl font-bold text-white"
             style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '-0.025em' }}>
            {typeof value === 'number' ? <Counter value={value} /> : value}
          </p>
          {sub && <p className="text-xs mt-1" style={{ color: 'rgba(148,163,184,0.45)' }}>{sub}</p>}
        </div>
        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
             style={{ background: `${color}18`, border: `1px solid ${color}30` }}>
          <Icon size={18} style={{ color }} />
        </div>
      </div>
      <div className="absolute bottom-0 left-6 right-6 h-px"
           style={{ background: `linear-gradient(90deg, transparent, ${color}50, transparent)` }} />
    </div>
  );
}

// ── Sparkline mini chart ────────────────────────────────────
function Sparkline({ data, color }: { data: number[]; color: string }) {
  const pts = data.map((v, i) => ({ v, i }));
  return (
    <ResponsiveContainer width="100%" height={36}>
      <AreaChart data={pts} margin={{ top: 2, bottom: 2, left: 0, right: 0 }}>
        <defs>
          <linearGradient id={`sg-${color.replace('#','')}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="v" stroke={color} strokeWidth={1.5}
              fill={`url(#sg-${color.replace('#','')})`} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ── Source donut ────────────────────────────────────────────
function SourceDonut({ rooster, topjobs }: { rooster: number; topjobs: number }) {
  const total = rooster + topjobs;
  const data  = [
    { name: 'TopJobs.lk',  value: topjobs, color: '#60a5fa' },
    { name: 'Rooster.jobs',value: rooster,  color: '#a78bfa' },
  ];
  return (
    <div className="flex items-center gap-5">
      <div className="relative shrink-0">
        <ResponsiveContainer width={120} height={160}>
          <PieChart>
            <Pie data={data} cx={65} cy={65} innerRadius={44} outerRadius={62}
                 paddingAngle={4} dataKey="value" strokeWidth={0}>
              {data.map((d, i) => <Cell key={i} fill={d.color} opacity={0.9} />)}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <p className="text-xl font-bold text-white" style={{ fontFamily: "'Syne', sans-serif" }}>
            <Counter value={total} />
          </p>
          <p className="text-xs text-slate-600">total</p>
        </div>
      </div>
      <div className="flex-1 space-y-3">
        {data.map(d => {
          const pct = total > 0 ? Math.round((d.value / total) * 100) : 0;
          return (
            <div key={d.name}>
              <div className="flex justify-between text-xs mb-1.5">
                <span className="flex items-center gap-1.5 text-slate-400">
                  <span className="w-2 h-2 rounded-full" style={{ background: d.color }} />
                  {d.name}
                </span>
                <span style={{ color: d.color, fontFamily: "'JetBrains Mono', monospace" }}>
                  {d.value} · {pct}%
                </span>
              </div>
              <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.05)' }}>
                <div className="h-full rounded-full transition-all duration-1000"
                     style={{ width: `${pct}%`, background: d.color, boxShadow: `0 0 8px ${d.color}60` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Radial pipeline chart ───────────────────────────────────
function PipelineRadial() {
  const data = [
    { name: 'TF-IDF',      value: 40, fill: '#60a5fa' },
    { name: 'Skill Gap',   value: 35, fill: '#34d399' },
    { name: 'Word2Vec',    value: 20, fill: '#a78bfa' },
    { name: 'RandomForest',value: 5,  fill: '#fbbf24' },
  ];
  return (
    <div className="flex items-center gap-4">
      <div className="shrink-0">
        <ResponsiveContainer width={130} height={150}>
          <RadialBarChart cx={65} cy={65} innerRadius={22} outerRadius={60}
                          data={data} startAngle={90} endAngle={-270}>
            <RadialBar dataKey="value" cornerRadius={4} background={{ fill: 'rgba(255,255,255,0.03)' }} />
          </RadialBarChart>
        </ResponsiveContainer>
      </div>
      <div className="flex-1 space-y-2">
        {data.map(d => (
          <div key={d.name} className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ background: d.fill }} />
            <span className="text-xs text-slate-400 flex-1" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              {d.name}
            </span>
            <span className="text-xs font-bold" style={{ color: d.fill, fontFamily: "'JetBrains Mono', monospace" }}>
              {d.value}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Skills bar chart ────────────────────────────────────────
function SkillsBarChart({ resumes }: { resumes: Resume[] }) {
  if (!resumes.length) return (
    <div className="flex items-center justify-center h-32 text-slate-700 text-sm">
      No resume data yet
    </div>
  );
  const data = resumes.slice(0, 5).map(r => ({
    name: (r.candidate_name || r.email || 'Unknown').split('@')[0].slice(0, 10),
    skills: r.skills_count,
    exp: r.years_experience,
  }));
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="bar-skills" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#60a5fa" stopOpacity={0.9} />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.6} />
          </linearGradient>
          <linearGradient id="bar-exp" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#a78bfa" stopOpacity={0.9} />
            <stop offset="100%" stopColor="#7c3aed" stopOpacity={0.6} />
          </linearGradient>
        </defs>
        <XAxis dataKey="name" tick={{ fill: 'rgba(148,163,184,0.5)', fontSize: 10, fontFamily: "'DM Sans', sans-serif" }}
               axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: 'rgba(148,163,184,0.4)', fontSize: 10 }} axisLine={false} tickLine={false} />
        <Tooltip content={<GlassTooltip formatter={(v: number, n: string) => `${n}: ${v}`} />}
                 cursor={{ fill: 'rgba(255,255,255,0.03)', radius: 6 }} />
        <Bar dataKey="skills" name="Skills"     fill="url(#bar-skills)" radius={[4,4,0,0]} maxBarSize={20} />
        <Bar dataKey="exp"    name="Experience" fill="url(#bar-exp)"    radius={[4,4,0,0]} maxBarSize={20} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── Match rate area chart ───────────────────────────────────
function MatchAreaChart({ matched, total }: { matched: number; total: number }) {
  // Simulated trend data based on actual stats
  const base = total > 0 ? Math.round((matched / total) * 100) : 0;
  const data = [
    { day: 'Mon', rate: Math.max(0, base - 15) },
    { day: 'Tue', rate: Math.max(0, base - 8)  },
    { day: 'Wed', rate: Math.max(0, base - 12) },
    { day: 'Thu', rate: Math.max(0, base - 4)  },
    { day: 'Fri', rate: Math.max(0, base - 6)  },
    { day: 'Sat', rate: Math.max(0, base - 2)  },
    { day: 'Now', rate: base                    },
  ];
  return (
    <ResponsiveContainer width="100%" height={160}>
      <AreaChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
        <defs>
          <linearGradient id="area-match" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#34d399" stopOpacity={0.3} />
            <stop offset="100%" stopColor="#34d399" stopOpacity={0}   />
          </linearGradient>
        </defs>
        <XAxis dataKey="day" tick={{ fill: 'rgba(148,163,184,0.5)', fontSize: 10, fontFamily: "'DM Sans', sans-serif" }}
               axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: 'rgba(148,163,184,0.4)', fontSize: 10 }} axisLine={false} tickLine={false}
               domain={[0, 100]} tickFormatter={v => `${v}%`} />
        <Tooltip content={<GlassTooltip formatter={(v: number) => `${v}% match rate`} />}
                 cursor={{ stroke: 'rgba(52,211,153,0.2)', strokeWidth: 1 }} />
        <Area type="monotone" dataKey="rate" stroke="#34d399" strokeWidth={2}
              fill="url(#area-match)" dot={false}
              activeDot={{ r: 4, fill: '#34d399', strokeWidth: 0 }} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ── Resume row ──────────────────────────────────────────────
function ResumeRow({ resume, index, onClick }: { resume: Resume; index: number; onClick: () => void }) {
  const colors = ['#60a5fa','#a78bfa','#34d399','#fbbf24','#f472b6'];
  const c = colors[index % colors.length];
  const sparkData = [20, 35, 28, 45, 38, 52, resume.skills_count];
  return (
    <div onClick={onClick}
      className="flex items-center gap-4 px-5 py-3.5 cursor-pointer group transition-all"
      style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
      onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)'}
      onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = 'transparent'}>
      <div className="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold shrink-0"
           style={{ background: `${c}18`, border: `1px solid ${c}30`, color: c, fontFamily: "'Syne', sans-serif" }}>
        {(resume.candidate_name || resume.email || '?')[0].toUpperCase()}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white truncate" style={{ fontFamily: "'DM Sans', sans-serif" }}>
          {resume.candidate_name || resume.email || 'Unknown'}
        </p>
        <p className="text-xs text-slate-500">{resume.skills_count} skills · {resume.years_experience}yr</p>
      </div>
      <div className="w-20 shrink-0">
        <Sparkline data={sparkData} color={c} />
      </div>
      <div className="text-right shrink-0">
        <p className="text-xs text-slate-500">
          {new Date(resume.uploaded_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
        </p>
        <p className="text-xs flex items-center justify-end gap-0.5 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
           style={{ color: '#60a5fa' }}>
          View <ChevronRight size={10} />
        </p>
      </div>
    </div>
  );
}

// ── Main Dashboard ───────────────────────────────────────────
export default function Dashboard() {
  const navigate   = useNavigate();
  const [stats,   setStats]   = useState<Stats | null>(null);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');
  const [ts,      setTs]      = useState(new Date());

  const fetch = async () => {
    setLoading(true); setError('');
    try {
      const [s, r] = await Promise.all([getStats(), getResumes()]);
      setStats(s.data.stats);
      setResumes(r.data.resumes?.slice(0, 5) || []);
      setTs(new Date());
    } catch { setError('Cannot connect to API — make sure python main.py is running.'); }
    finally  { setLoading(false); }
  };
  useEffect(() => { fetch(); }, []);

  const cards = stats ? [
    { icon: Briefcase,  label: 'Total Jobs',      value: stats.total_jobs,      sub: 'Across all sources',  color: '#3b82f6', glow: 'rgba(59,130,246,0.06)',  delay: 0   },
    { icon: FileText,   label: 'Resumes Uploaded', value: stats.total_resumes,  sub: 'Parsed & analyzed',   color: '#7c3aed', glow: 'rgba(124,58,237,0.06)', delay: 80  },
    { icon: Users,      label: 'Matched Resumes', value: stats.resumes_matched, sub: 'ML matched',          color: '#059669', glow: 'rgba(5,150,105,0.06)',  delay: 160 },
    { icon: TrendingUp, label: 'Match Rate',
      value: stats.total_resumes > 0 ? `${Math.round((stats.resumes_matched / stats.total_resumes) * 100)}%` : '0%',
      sub: 'Overall accuracy', color: '#d97706', glow: 'rgba(217,119,6,0.06)', delay: 240 },
  ] : [];

  return (
    <div className="px-10 py-7 w-full animate-fade-in">

      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1"
              style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '-0.025em' }}>
            Dashboard
          </h1>
          <p className="text-sm text-slate-400" style={{ fontFamily: "'DM Sans', sans-serif" }}>
            ML-powered job matching · SHAP + LIME explainability
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-600 flex items-center gap-1.5"
                style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            <Clock size={11} />{ts.toLocaleTimeString()}
          </span>
          <button onClick={fetch}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-white
                       transition-all active:scale-95"
            style={{ background: 'rgba(59,130,246,0.12)', border: '1px solid rgba(59,130,246,0.2)' }}>
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button onClick={() => navigate('/upload')}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white
                       transition-all active:scale-95"
            style={{ background: 'linear-gradient(135deg,#3b82f6,#2563eb)', boxShadow: '0 4px 16px rgba(37,99,235,0.28)' }}>
            <Upload size={13} /> Upload Resume
          </button>
        </div>
      </div>

      {/* Error / API status */}
      {error ? (
        <div className="flex items-center gap-3 px-5 py-3.5 rounded-2xl mb-6"
             style={{ background: 'rgba(244,63,94,0.07)', border: '1px solid rgba(244,63,94,0.2)' }}>
          <Activity size={14} className="text-rose-400 shrink-0" />
          <p className="text-sm text-rose-300" style={{ fontFamily: "'DM Sans', sans-serif" }}>{error}</p>
        </div>
      ) : (
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs mb-6"
             style={{ background: 'rgba(52,211,153,0.06)', border: '1px solid rgba(52,211,153,0.15)', color: '#34d399' }}>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          API Connected — localhost:8000
        </div>
      )}

      {/* Stat cards */}
      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-5 mb-6">
          {[...Array(4)].map((_, i) => <div key={i} className="h-28 rounded-2xl skeleton" />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-5 mb-6">
          {cards.map(c => <StatCard key={c.label} {...c} />)}
        </div>
      )}

      {/* Row 1: Source donut + Match rate area + Pipeline radial */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-5">

        {/* Source distribution */}
        <div className="rounded-2xl p-5 animate-slide-up" style={{ animationDelay: '80ms',
          background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}>
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <Database size={14} className="text-blue-400" />
              <h2 className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                Job Sources
              </h2>
            </div>
            <span className="text-xs text-slate-600">{stats?.total_jobs || 0} total</span>
          </div>
          {loading ? <div className="h-32 skeleton rounded-xl" /> : stats ? (
            <SourceDonut rooster={stats.rooster_jobs} topjobs={stats.topjobs_jobs} />
          ) : null}
        </div>

        {/* Match rate trend */}
        <div className="rounded-2xl p-5 animate-slide-up" style={{ animationDelay: '140ms',
          background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <TrendingUp size={14} className="text-emerald-400" />
              <h2 className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                Match Rate Trend
              </h2>
            </div>
            <span className="text-xs font-bold text-emerald-400"
                  style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              {stats && stats.total_resumes > 0
                ? `${Math.round((stats.resumes_matched / stats.total_resumes) * 100)}%`
                : '—'}
            </span>
          </div>
          <p className="text-xs text-slate-600 mb-4" style={{ fontFamily: "'DM Sans', sans-serif" }}>
            Simulated weekly view
          </p>
          {loading ? <div className="h-28 skeleton rounded-xl" /> : stats ? (
            <MatchAreaChart matched={stats.resumes_matched} total={stats.total_resumes} />
          ) : null}
        </div>

        {/* ML Pipeline radial */}
        <div className="rounded-2xl p-5 animate-slide-up" style={{ animationDelay: '200ms',
          background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}>
          <div className="flex items-center gap-2 mb-5">
            <Brain size={14} className="text-violet-400" />
            <h2 className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              ML Signal Weights
            </h2>
            <span className="ml-auto text-xs px-2 py-0.5 rounded-full"
                  style={{ background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.18)', color: '#34d399' }}>
              Active
            </span>
          </div>
          <PipelineRadial />
          <div className="mt-4 pt-3 flex items-center gap-2"
               style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
            <Sparkles size={11} className="text-blue-400" />
            <span className="text-xs text-slate-500">XAI: SHAP + LIME</span>
          </div>
        </div>
      </div>

      {/* Row 2: Skills bar + Quick actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-5">

        {/* Resume skills comparison */}
        <div className="md:col-span-2 rounded-2xl p-5 animate-slide-up" style={{ animationDelay: '260ms',
          background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <BarChart3 size={14} className="text-amber-400" />
              <h2 className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                Resume Comparison
              </h2>
            </div>
            <div className="flex items-center gap-3">
              {[['#60a5fa','Skills'],['#a78bfa','Experience']].map(([c, l]) => (
                <span key={l} className="flex items-center gap-1.5 text-xs text-slate-500">
                  <span className="w-2 h-2 rounded-sm" style={{ background: c as string }} />{l}
                </span>
              ))}
            </div>
          </div>
          <p className="text-xs text-slate-600 mb-4" style={{ fontFamily: "'DM Sans', sans-serif" }}>
            Skills count vs experience years per candidate
          </p>
          {loading ? <div className="h-36 skeleton rounded-xl" /> : (
            <SkillsBarChart resumes={resumes} />
          )}
        </div>

        {/* Quick actions */}
        <div className="rounded-2xl p-5 animate-slide-up" style={{ animationDelay: '320ms',
          background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}>
          <div className="flex items-center gap-2 mb-5">
            <Zap size={14} className="text-amber-400" />
            <h2 className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              Quick Actions
            </h2>
          </div>
          <div className="space-y-2.5">
            {[
              { label:'Upload Resume',  sub:'PDF · DOCX · TXT',   to:'/upload',   color:'#3b82f6', bg:'rgba(59,130,246,0.08)',  bd:'rgba(59,130,246,0.18)' },
              { label:'Browse Jobs',    sub:`${stats?.total_jobs||0} available`, to:'/jobs', color:'#a78bfa', bg:'rgba(139,92,246,0.06)', bd:'rgba(139,92,246,0.15)' },
              { label:'Scrape New Jobs',sub:'Refresh live data',  to:'/scraping', color:'#34d399', bg:'rgba(16,185,129,0.06)', bd:'rgba(16,185,129,0.15)' },
            ].map(a => (
              <button key={a.to} onClick={() => navigate(a.to)}
                className="w-full flex items-center justify-between px-4 py-3 rounded-xl
                           transition-all duration-150 active:scale-98 group"
                style={{ background: a.bg, border: `1px solid ${a.bd}` }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.transform = 'translateX(3px)'}
                onMouseLeave={e => (e.currentTarget as HTMLElement).style.transform = 'translateX(0)'}>
                <div className="text-left">
                  <p className="text-sm font-medium text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                    {a.label}
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: 'rgba(148,163,184,0.5)' }}>{a.sub}</p>
                </div>
                <ArrowUpRight size={14} style={{ color: a.color }} />
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Resumes */}
      <div className="rounded-2xl overflow-hidden animate-slide-up" style={{ animationDelay: '380ms',
        background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}>
        <div className="flex items-center justify-between px-5 py-4"
             style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <div className="flex items-center gap-2">
            <FileText size={14} className="text-violet-400" />
            <h2 className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              Recent Resumes
            </h2>
            {resumes.length > 0 && (
              <span className="text-xs px-2 py-0.5 rounded-full"
                    style={{ background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.2)', color: '#c4b5fd' }}>
                {resumes.length}
              </span>
            )}
          </div>
          <button onClick={() => navigate('/upload')}
            className="text-xs flex items-center gap-1 transition-colors"
            style={{ color: 'rgba(96,165,250,0.7)' }}
            onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = '#60a5fa'}
            onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = 'rgba(96,165,250,0.7)'}>
            Upload new <ChevronRight size={11} />
          </button>
        </div>

        {loading ? (
          <div className="p-5 space-y-3">
            {[...Array(3)].map((_, i) => <div key={i} className="h-12 skeleton rounded-xl" />)}
          </div>
        ) : resumes.length === 0 ? (
          <div className="py-14 text-center">
            <div className="w-12 h-12 rounded-2xl mx-auto mb-4 flex items-center justify-center"
                 style={{ background: 'rgba(139,92,246,0.07)', border: '1px solid rgba(139,92,246,0.14)' }}>
              <FileText size={20} className="text-violet-400" />
            </div>
            <p className="text-sm text-slate-400 mb-4" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              No resumes uploaded yet
            </p>
            <button onClick={() => navigate('/upload')}
              className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all active:scale-95"
              style={{ background: 'linear-gradient(135deg,#3b82f6,#2563eb)', boxShadow: '0 4px 16px rgba(37,99,235,0.28)' }}>
              Upload First Resume
            </button>
          </div>
        ) : (
          resumes.map((r, i) => (
            <ResumeRow key={r.id} resume={r} index={i} onClick={() => navigate(`/results/${r.id}`)} />
          ))
        )}
      </div>
    </div>
  );
}