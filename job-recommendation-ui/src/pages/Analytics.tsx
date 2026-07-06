import React, { useEffect, useState, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line,
  CartesianGrid, Legend, ReferenceLine
} from 'recharts';
import {
  BarChart3, TrendingUp, MapPin, Building2, Brain,
  Target, RefreshCw, Zap, AlertCircle, Clock,
  ChevronUp, ChevronDown, Minus, Sparkles, Shield
} from 'lucide-react';
import api from '../api/client';
import { getResumes, getModelReport } from '../api/client';

// ── Glassmorphism Tooltip ──────────────────────────────────
function GlassTip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(3,7,18,0.95)', backdropFilter: 'blur(16px)',
      border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: '10px 14px'
    }}>
      {label && <p style={{ color: 'rgba(148,163,184,0.7)', fontSize: 11, marginBottom: 5, fontFamily: "'DM Sans'" }}>{label}</p>}
      {payload.map((p: any, i: number) => (
        <p key={i} style={{ color: p.color || p.fill || '#fff', fontSize: 12, fontFamily: "'JetBrains Mono'" }}>
          {p.name}: <strong>{p.value}{p.unit || ''}</strong>
        </p>
      ))}
    </div>
  );
}

// ── Section Card wrapper ──────────────────────────────────
function Card({ title, icon: Icon, color, children, delay = 0 }: {
  title: string; icon: any; color: string; children: React.ReactNode; delay?: number;
}) {
  return (
    <div className="rounded-2xl p-5 animate-slide-up"
         style={{ animationDelay: `${delay}ms`, background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}>
      <div className="flex items-center gap-2 mb-5">
        <Icon size={15} style={{ color }} />
        <h2 className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>{title}</h2>
      </div>
      {children}
    </div>
  );
}

// ── Metric Pill ───────────────────────────────────────────
function MetricPill({ label, value, color, sub }: { label: string; value: string|number; color: string; sub?: string }) {
  return (
    <div className="rounded-xl p-4" style={{ background: `${color}0f`, border: `1px solid ${color}25` }}>
      <p className="text-xs text-slate-500 mb-1 uppercase tracking-wider"
         style={{ fontSize: 10, fontFamily: "'DM Sans'" }}>{label}</p>
      <p className="text-2xl font-bold" style={{ color, fontFamily: "'Syne', sans-serif" }}>{value}</p>
      {sub && <p className="text-xs text-slate-600 mt-0.5">{sub}</p>}
    </div>
  );
}

// ── Counterfactual Card ───────────────────────────────────
function CounterfactualCard({ cf }: { cf: any }) {
  const impactColor = cf.impact === 'High' ? '#34d399' : cf.impact === 'Medium' ? '#fbbf24' : '#60a5fa';
  return (
    <div className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs px-2 py-0.5 rounded-full"
                  style={{ background: `${impactColor}15`, border: `1px solid ${impactColor}30`, color: impactColor }}>
              {cf.impact} Impact
            </span>
          </div>
          <p className="text-sm font-semibold text-white truncate" style={{ fontFamily: "'DM Sans'" }}>{cf.job_title}</p>
          <p className="text-xs text-slate-500">{cf.company}</p>
        </div>
        <div className="text-right shrink-0">
          <div className="flex items-center gap-1.5 justify-end">
            <span className="text-lg font-bold text-slate-400" style={{ fontFamily: "'Syne'" }}>{cf.current_score}%</span>
            <ChevronUp size={16} className="text-emerald-400" />
            <span className="text-lg font-bold text-emerald-400" style={{ fontFamily: "'Syne'" }}>{cf.new_score_est}%</span>
          </div>
          <p className="text-xs text-emerald-400">{cf.skill_gain} gain</p>
        </div>
      </div>
      <div>
        <p className="text-xs text-slate-500 mb-1.5" style={{ fontFamily: "'DM Sans'" }}>
          Add these skills to boost your match:
        </p>
        <div className="flex flex-wrap gap-1.5">
          {cf.add_skills.map((s: string) => (
            <span key={s} className="text-xs px-2 py-0.5 rounded-full"
                  style={{ background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.2)', color: '#6ee7b7' }}>
              + {s}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Skeleton ─────────────────────────────────────────────
function Skel({ h = 48 }: { h?: number }) {
  return <div className="skeleton rounded-xl w-full" style={{ height: h }} />;
}

// ── Main Analytics Page ───────────────────────────────────
export default function Analytics() {
  const [skills,       setSkills]       = useState<any[]>([]);
  const [categories,   setCategories]   = useState<any[]>([]);
  const [companies,    setCompanies]    = useState<any[]>([]);
  const [locations,    setLocations]    = useState<any[]>([]);
  const [timeline,     setTimeline]     = useState<any[]>([]);
  const [xaiEval,      setXaiEval]      = useState<any>(null);
  const [resumes,      setResumes]      = useState<any[]>([]);
  const [selResume,    setSelResume]    = useState<number|null>(null);
  const [modelReport,  setModelReport]  = useState<any>(null);
  const [loading,      setLoading]      = useState(true);
  const [xaiLoading,   setXaiLoading]   = useState(false);
  const [error,        setError]        = useState('');

  const fetchAll = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [sk, cat, comp, loc, tl, res, mr] = await Promise.all([
        api.get('/api/analytics/skills-demand'),
        api.get('/api/analytics/job-categories'),
        api.get('/api/analytics/companies'),
        api.get('/api/analytics/locations'),
        api.get('/api/analytics/timeline'),
        getResumes(),
        getModelReport().catch(() => null),
      ]);
      setSkills(sk.data.skills || []);
      setCategories(cat.data.categories || []);
      setCompanies(comp.data.companies || []);
      setLocations(loc.data.locations || []);

      // Process timeline — group by date
      const tData: Record<string, any> = {};
      for (const t of (tl.data.timeline || [])) {
        if (!tData[t.date]) tData[t.date] = { date: t.date, rooster: 0, topjobs: 0 };
        tData[t.date][t.source] = t.count;
      }
      setTimeline(Object.values(tData).sort((a: any, b: any) => a.date.localeCompare(b.date)));

      const resumeList = res.data.resumes || [];
      setResumes(resumeList);
      if (resumeList.length > 0) setSelResume(resumeList[0].id);

      if (mr?.data) setModelReport(mr.data);
    } catch { setError('Cannot connect to API.'); }
    finally { setLoading(false); }
  }, []);

  const fetchXAI = useCallback(async (resumeId: number) => {
    setXaiLoading(true);
    try {
      const r = await api.get(`/api/analytics/xai/evaluation/${resumeId}`);
      setXaiEval(r.data);
    } catch {}
    finally { setXaiLoading(false); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);
  useEffect(() => { if (selResume) fetchXAI(selResume); }, [selResume, fetchXAI]);

  const PIE_COLORS = ['#60a5fa','#a78bfa','#34d399','#fbbf24','#f472b6','#22d3ee','#fb923c','#a3e635','#818cf8','#e879f9'];

  return (
    <div className="px-10 py-7 w-full animate-fade-in">

      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1"
              style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '-0.025em' }}>
            Job Market Analytics
          </h1>
          <p className="text-sm text-slate-400" style={{ fontFamily: "'DM Sans', sans-serif" }}>
            Real-time insights from {skills.length > 0 ? `${categories.reduce((a,c)=>a+c.total,0)}` : '—'} scraped jobs
          </p>
        </div>
        <button onClick={fetchAll}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-white transition-all active:scale-95"
          style={{ background: 'rgba(59,130,246,0.12)', border: '1px solid rgba(59,130,246,0.2)' }}>
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-3 px-5 py-4 rounded-2xl mb-6"
             style={{ background: 'rgba(244,63,94,0.07)', border: '1px solid rgba(244,63,94,0.18)' }}>
          <AlertCircle size={16} className="text-rose-400" />
          <p className="text-sm text-rose-300">{error}</p>
        </div>
      )}

      {/* ── Row 1: Skills Demand + Radar ───────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 mb-5">

        {/* Top Skills Bar — spans 2 cols */}
        <div className="xl:col-span-2">
          <Card title="Top Skills in Demand" icon={Zap} color="#60a5fa" delay={0}>
            {loading ? <Skel h={260} /> : (
              <>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={skills.slice(0, 15)} layout="vertical"
                            margin={{ left: 8, right: 32, top: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="skillBar" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.9} />
                        <stop offset="100%" stopColor="#7c3aed" stopOpacity={0.8} />
                      </linearGradient>
                    </defs>
                    <XAxis type="number" tick={{ fill: 'rgba(148,163,184,0.5)', fontSize: 10 }}
                           axisLine={false} tickLine={false} />
                    <YAxis type="category" dataKey="skill" width={82}
                           tick={{ fill: 'rgba(148,163,184,0.7)', fontSize: 10, fontFamily: "'DM Sans'" }}
                           axisLine={false} tickLine={false} />
                    <Tooltip content={<GlassTip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                    <Bar dataKey="count" name="Jobs" fill="url(#skillBar)" radius={[0,6,6,0]} maxBarSize={12} />
                  </BarChart>
                </ResponsiveContainer>
                <div className="flex items-center gap-4 mt-3 pt-3"
                     style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                  <span className="text-xs text-slate-500">Top skill:</span>
                  <span className="text-xs font-semibold text-blue-400">{skills[0]?.skill} ({skills[0]?.pct}% of jobs)</span>
                </div>
              </>
            )}
          </Card>
        </div>

        {/* Radar */}
        <Card title="Skills Radar" icon={Target} color="#a78bfa" delay={80}>
          {loading ? <Skel h={260} /> : (
            <>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={skills.slice(0, 8)} layout="vertical"
                          margin={{ left: 8, right: 32, top: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="radarBar" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#a78bfa" stopOpacity={0.9} />
                      <stop offset="100%" stopColor="#7c3aed" stopOpacity={0.7} />
                    </linearGradient>
                  </defs>
                  <XAxis type="number" tick={{ fill: 'rgba(148,163,184,0.5)', fontSize: 10 }}
                         axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} />
                  <YAxis type="category" dataKey="skill" width={72}
                         tick={{ fill: 'rgba(148,163,184,0.7)', fontSize: 10, fontFamily: "'DM Sans'" }}
                         axisLine={false} tickLine={false} />
                  <Tooltip content={<GlassTip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                  <Bar dataKey="pct" name="Demand %" fill="url(#radarBar)" radius={[0,6,6,0]} maxBarSize={14} />
                </BarChart>
              </ResponsiveContainer>
              <p className="text-xs text-slate-600 mt-2 text-center">% of jobs requiring this skill</p>
            </>
          )}
        </Card>
      </div>

      {/* ── Row 2: Categories Pie + Companies Bar ──────── */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 mb-5">

        {/* Job Categories Pie */}
        <Card title="Job Categories Distribution" icon={BarChart3} color="#34d399" delay={120}>
          {loading ? <Skel h={260} /> : (
            <div className="flex items-center gap-4">
              <div className="shrink-0">
                <ResponsiveContainer width={180} height={180}>
                  <PieChart>
                    <Pie data={categories.slice(0,8)} cx={85} cy={85}
                         innerRadius={48} outerRadius={78} paddingAngle={3}
                         dataKey="total" strokeWidth={0}>
                      {categories.slice(0,8).map((_: any, i: number) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} opacity={0.85} />
                      ))}
                    </Pie>
                    <Tooltip content={<GlassTip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex-1 space-y-2 overflow-hidden">
                {categories.slice(0, 8).map((c: any, i: number) => (
                  <div key={c.category} className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full shrink-0"
                          style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                    <span className="text-xs text-slate-400 flex-1 truncate"
                          style={{ fontFamily: "'DM Sans'" }}>{c.category}</span>
                    <span className="text-xs font-bold text-white shrink-0"
                          style={{ fontFamily: "'JetBrains Mono'" }}>{c.total}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>

        {/* Top Companies */}
        <Card title="Top Hiring Companies" icon={Building2} color="#fbbf24" delay={160}>
          {loading ? <Skel h={260} /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={companies.slice(0, 10)} layout="vertical"
                        margin={{ left: 8, right: 24, top: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="compBar" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.9} />
                    <stop offset="100%" stopColor="#d97706" stopOpacity={0.7} />
                  </linearGradient>
                </defs>
                <XAxis type="number" tick={{ fill: 'rgba(148,163,184,0.5)', fontSize: 10 }}
                       axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="company" width={110}
                       tick={{ fill: 'rgba(148,163,184,0.7)', fontSize: 9, fontFamily: "'DM Sans'" }}
                       axisLine={false} tickLine={false} />
                <Tooltip content={<GlassTip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                <Bar dataKey="count" name="Jobs" fill="url(#compBar)" radius={[0,6,6,0]} maxBarSize={12} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      {/* ── Row 3: Timeline + Locations ────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 mb-5">

        {/* Timeline */}
        <div className="xl:col-span-2">
          <Card title="Scraping Timeline" icon={Clock} color="#22d3ee" delay={200}>
            {loading ? <Skel h={180} /> : timeline.length === 0 ? (
              <div className="flex items-center justify-center h-44 text-slate-600 text-sm">No timeline data</div>
            ) : (
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={timeline} margin={{ left: -12, right: 8, top: 4, bottom: 0 }}>
                  <defs>
                    <linearGradient id="lineRooster" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#a78bfa" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#a78bfa" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="lineTopjobs" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#60a5fa" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#60a5fa" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="4 4" />
                  <XAxis dataKey="date" tick={{ fill: 'rgba(148,163,184,0.5)', fontSize: 10 }}
                         axisLine={false} tickLine={false}
                         tickFormatter={d => d.slice(5)} />
                  <YAxis tick={{ fill: 'rgba(148,163,184,0.4)', fontSize: 10 }}
                         axisLine={false} tickLine={false} />
                  <Tooltip content={<GlassTip />} />
                  <Legend wrapperStyle={{ fontSize: 11, color: 'rgba(148,163,184,0.6)' }} />
                  <Line type="monotone" dataKey="rooster" name="Rooster" stroke="#a78bfa" strokeWidth={2}
                        dot={{ r: 3, fill: '#a78bfa' }} activeDot={{ r: 5 }} />
                  <Line type="monotone" dataKey="topjobs" name="TopJobs" stroke="#60a5fa" strokeWidth={2}
                        dot={{ r: 3, fill: '#60a5fa' }} activeDot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </Card>
        </div>

        {/* Locations */}
        <Card title="Job Locations" icon={MapPin} color="#f472b6" delay={240}>
          {loading ? <Skel h={180} /> : (
            <div className="space-y-2 max-h-44 overflow-y-auto pr-1">
              {locations.slice(0, 12).map((l: any, i: number) => {
                const maxCount = locations[0]?.count || 1;
                const pct = Math.round((l.count / maxCount) * 100);
                return (
                  <div key={l.location}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-slate-400 truncate flex-1"
                            style={{ fontFamily: "'DM Sans'" }}>{l.location}</span>
                      <span className="text-xs font-bold text-white ml-2 shrink-0"
                            style={{ fontFamily: "'JetBrains Mono'" }}>{l.count}</span>
                    </div>
                    <div className="h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.05)' }}>
                      <div className="h-full rounded-full transition-all duration-700"
                           style={{ width: `${pct}%`, background: `${PIE_COLORS[i % PIE_COLORS.length]}`,
                                    boxShadow: `0 0 6px ${PIE_COLORS[i%PIE_COLORS.length]}50` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>

      {/* ── XAI Evaluation Section ─────────────────────── */}
      <div className="rounded-2xl p-5 animate-slide-up" style={{ animationDelay: '300ms',
        background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}>
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <Brain size={15} className="text-violet-400" />
            <h2 className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              XAI Research Evaluation
            </h2>
            <span className="text-xs px-2 py-0.5 rounded-full"
                  style={{ background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.2)', color: '#c4b5fd' }}>
              Precision@K · NDCG · Counterfactuals
            </span>
          </div>

          {/* Resume selector */}
          {resumes.length > 0 && (
            <select value={selResume || ''} onChange={e => setSelResume(Number(e.target.value))}
              className="text-sm rounded-xl px-3 py-2 transition-all"
              style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
                       color: 'white', fontFamily: "'DM Sans', sans-serif", outline: 'none' }}>
              {resumes.map((r: any) => (
                <option key={r.id} value={r.id} style={{ background: '#0a0f1e' }}>
                  {r.candidate_name || r.email || `Resume #${r.id}`}
                </option>
              ))}
            </select>
          )}
        </div>

        {resumes.length === 0 ? (
          <div className="py-10 text-center">
            <Brain size={28} className="text-slate-700 mx-auto mb-3" />
            <p className="text-slate-500 text-sm">Upload a resume first to see XAI evaluation metrics</p>
          </div>
        ) : xaiLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => <Skel key={i} h={88} />)}
          </div>
        ) : xaiEval ? (
          <div className="space-y-6">
            {/* Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricPill label="Avg Match Score"   value={`${xaiEval.metrics.avg_match_score}%`}  color="#60a5fa" sub="across top 20" />
              <MetricPill label="Precision @ 5"     value={`${xaiEval.metrics.precision_at_5}%`}   color="#34d399" sub="top 5 relevant" />
              <MetricPill label="NDCG @ 10"         value={`${xaiEval.metrics.ndcg_at_10}%`}       color="#a78bfa" sub="ranking quality" />
              <MetricPill label="Score Spread"      value={`${xaiEval.metrics.score_spread}%`}     color="#fbbf24" sub="best - worst" />
            </div>

            {/* Score Distribution + Bias */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

              {/* Score distribution line */}
              <div className="xl:col-span-2">
                <p className="text-xs text-slate-500 mb-3" style={{ fontFamily: "'DM Sans'" }}>
                  Match Score Distribution (Rank 1 → 20)
                </p>
                <ResponsiveContainer width="100%" height={140}>
                  <LineChart data={xaiEval.score_distribution}
                             margin={{ left: -12, right: 8, top: 4, bottom: 0 }}>
                    <defs>
                      <linearGradient id="scoreLine" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#60a5fa" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#60a5fa" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="4 4" />
                    <XAxis dataKey="rank" tick={{ fill: 'rgba(148,163,184,0.5)', fontSize: 10 }}
                           axisLine={false} tickLine={false} label={{ value: 'Rank', position: 'insideBottom', fill: 'rgba(148,163,184,0.4)', fontSize: 10 }} />
                    <YAxis tick={{ fill: 'rgba(148,163,184,0.4)', fontSize: 10 }}
                           axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} />
                    <Tooltip content={<GlassTip />} />
                    <Line type="monotone" dataKey="score" name="Score" stroke="#60a5fa" strokeWidth={2}
                          dot={{ r: 2, fill: '#60a5fa' }} activeDot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Bias check */}
              <div className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                <div className="flex items-center gap-2 mb-3">
                  <Shield size={13} className="text-emerald-400" />
                  <p className="text-xs font-semibold text-white" style={{ fontFamily: "'DM Sans'" }}>
                    Source Bias Check
                  </p>
                </div>
                {xaiEval.bias_check && (
                  <div className="space-y-3">
                    {[
                      { label: 'Top 5', data: xaiEval.bias_check.top5  },
                      { label: 'Top 20',data: xaiEval.bias_check.top20 },
                    ].map(b => (
                      <div key={b.label}>
                        <p className="text-xs text-slate-500 mb-1.5">{b.label}</p>
                        <div className="grid grid-cols-2 gap-2">
                          {[['Rooster','#a78bfa'],['TopJobs','#60a5fa']].map(([src, col]) => (
                            <div key={src} className="text-center px-2 py-2 rounded-lg"
                                 style={{ background: `${col}10`, border: `1px solid ${col}20` }}>
                              <p className="text-xs font-bold" style={{ color: col as string, fontFamily: "'Syne'" }}>
                                {src === 'Rooster' ? b.data.rooster : b.data.topjobs}
                              </p>
                              <p className="text-xs text-slate-600">{src}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                    <div className="flex items-center gap-2 pt-2"
                         style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                      {xaiEval.bias_check.balanced
                        ? <><span className="w-2 h-2 rounded-full bg-emerald-400" /><span className="text-xs text-emerald-400">Balanced sources</span></>
                        : <><span className="w-2 h-2 rounded-full bg-amber-400" /><span className="text-xs text-amber-400">Source imbalance detected</span></>}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Counterfactuals */}
            {xaiEval.counterfactuals?.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles size={13} className="text-amber-400" />
                  <p className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans'" }}>
                    Counterfactual Analysis
                  </p>
                  <span className="text-xs text-slate-500">
                    — "What if you had these skills?"
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {xaiEval.counterfactuals.map((cf: any, i: number) => (
                    <CounterfactualCard key={i} cf={cf} />
                  ))}
                </div>
              </div>
            )}

            {/* Precision@K table */}
            <div>
              <p className="text-xs text-slate-500 mb-3 flex items-center gap-2">
                <Target size={11} className="text-blue-400" />
                Evaluation Metrics Summary
              </p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: 'Precision@5',  value: `${xaiEval.metrics.precision_at_5}%`,  color: '#60a5fa' },
                  { label: 'Precision@10', value: `${xaiEval.metrics.precision_at_10}%`, color: '#34d399' },
                  { label: 'NDCG@5',       value: `${xaiEval.metrics.ndcg_at_5}%`,       color: '#a78bfa' },
                  { label: 'NDCG@10',      value: `${xaiEval.metrics.ndcg_at_10}%`,      color: '#fbbf24' },
                ].map(m => (
                  <div key={m.label} className="px-4 py-3 rounded-xl text-center"
                       style={{ background: `${m.color}08`, border: `1px solid ${m.color}18` }}>
                    <p className="text-xs text-slate-500 mb-1" style={{ fontFamily: "'DM Sans'" }}>{m.label}</p>
                    <p className="text-xl font-bold" style={{ color: m.color, fontFamily: "'Syne'" }}>{m.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* ── ML Model Performance Section ──────────────────── */}
      <div className="rounded-2xl p-5 mt-5 animate-slide-up"
           style={{ animationDelay: '350ms', background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}>
        <div className="flex items-center gap-2 mb-5">
          <Brain size={15} className="text-emerald-400" />
          <h2 className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
            ML Model Performance
          </h2>
          <span className="text-xs px-2 py-0.5 rounded-full"
                style={{ background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.18)', color: '#6ee7b7' }}>
            7 Classifiers · Phase 2 GridSearchCV
          </span>
        </div>

        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => <Skel key={i} h={88} />)}
          </div>
        ) : !modelReport ? (
          <div className="py-10 text-center">
            <Brain size={28} className="text-slate-700 mx-auto mb-3" />
            <p className="text-slate-500 text-sm">Training report not found.</p>
            <p className="text-slate-600 text-xs mt-1">Run <code className="text-emerald-500">python ml_model/train_role_classifier.py</code> to generate it.</p>
          </div>
        ) : (
          <div className="space-y-5">

            {/* Summary pills */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <MetricPill label="Best Model"      value={modelReport.best_model?.replace('Linear SVM Tuned','SVM Tuned') ?? '—'} color="#34d399" />
              <MetricPill label="Weighted F1"     value={`${modelReport.best_f1 ?? '—'}%`}          color="#60a5fa" sub="majority-class biased" />
              <MetricPill label="Macro F1"        value={`${modelReport.best_macro_f1 ?? '—'}%`}     color="#f472b6" sub="honest per-class avg" />
              <MetricPill label="Best Accuracy"   value={`${modelReport.best_accuracy ?? '—'}%`}     color="#a78bfa" sub="test set" />
              <MetricPill label="Career Roles"    value={modelReport.n_roles ?? '—'}                 color="#fbbf24" sub={`${modelReport.total_samples ?? '—'} samples`} />
            </div>
            {/* Data fixes badge row */}
            <div className="flex flex-wrap gap-2">
              {[
                { label: `SE Cap: ${modelReport.se_cap ?? 800}`, tip: 'Software Engineer undersampled' },
                { label: `SMOTE: ${modelReport.smote_enabled ? 'ON' : 'OFF'}`, tip: 'Minority class oversampling' },
                { label: 'class_weight=balanced', tip: 'Penalises minority-class errors more' },
                { label: 'Skills 3× weighted', tip: 'Skills field repeated 3x in TF-IDF' },
                { label: 'Synonym normalised', tip: 'ml→machine learning, js→javascript …' },
              ].map(b => (
                <span key={b.label} title={b.tip} className="text-xs px-3 py-1 rounded-full cursor-help"
                      style={{ background: 'rgba(244,114,182,0.08)', border: '1px solid rgba(244,114,182,0.2)', color: '#f9a8d4', fontFamily: "'JetBrains Mono'" }}>
                  {b.label}
                </span>
              ))}
            </div>

            {/* Phase 2 tuned detail */}
            {modelReport.tuned && (
              <div className="rounded-xl px-4 py-3 flex flex-wrap items-center gap-4"
                   style={{ background: 'rgba(52,211,153,0.05)', border: '1px solid rgba(52,211,153,0.15)' }}>
                <span className="text-xs font-semibold text-emerald-400" style={{ fontFamily: "'DM Sans'" }}>
                  Phase 2 GridSearchCV — Best C = {modelReport.tuned.best_C}
                </span>
                {[
                  { l: 'F1',        v: modelReport.tuned.f1 },
                  { l: 'Accuracy',  v: modelReport.tuned.accuracy },
                  { l: 'Precision', v: modelReport.tuned.precision },
                  { l: 'Recall',    v: modelReport.tuned.recall },
                ].map(m => (
                  <span key={m.l} className="text-xs px-3 py-1 rounded-full"
                        style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.2)', color: '#6ee7b7', fontFamily: "'JetBrains Mono'" }}>
                    {m.l}: <strong>{m.v}%</strong>
                  </span>
                ))}
              </div>
            )}

            {/* 7-model comparison table */}
            {modelReport.evaluation && (
              <div>
                <p className="text-xs text-slate-500 mb-3 flex items-center gap-2" style={{ fontFamily: "'DM Sans'" }}>
                  <Target size={11} className="text-blue-400" /> Classifier Comparison (5-fold Cross-Validation)
                </p>
                <div className="overflow-x-auto rounded-xl" style={{ border: '1px solid rgba(255,255,255,0.07)' }}>
                  <table className="w-full text-xs" style={{ borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ background: 'rgba(255,255,255,0.04)', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                        {['Model', 'Accuracy', 'Precision', 'Recall', 'W-F1', 'Macro F1'].map(h => (
                          <th key={h} className="text-left px-4 py-3 font-semibold text-slate-400"
                              style={{ fontFamily: "'DM Sans'", fontSize: 11, whiteSpace: 'nowrap',
                                       color: h === 'Macro F1' ? '#f472b6' : undefined }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(modelReport.evaluation as Record<string, any>).map(([name, m]: [string, any], i) => {
                        const isBest = name === modelReport.best_model;
                        const isTuned = name.includes('Tuned');
                        return (
                          <tr key={name}
                              style={{ background: isBest ? 'rgba(52,211,153,0.06)' : i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                                       borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                            <td className="px-4 py-3" style={{ fontFamily: "'DM Sans'" }}>
                              <div className="flex items-center gap-2">
                                <span className={isBest ? 'text-emerald-400 font-semibold' : 'text-slate-300'}>{name}</span>
                                {isBest && <span className="text-xs px-1.5 py-0.5 rounded-full"
                                                 style={{ background: 'rgba(52,211,153,0.12)', border: '1px solid rgba(52,211,153,0.25)', color: '#6ee7b7', fontSize: 9 }}>BEST</span>}
                                {isTuned && !isBest && <span className="text-xs px-1.5 py-0.5 rounded-full"
                                                             style={{ background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.2)', color: '#93c5fd', fontSize: 9 }}>TUNED</span>}
                              </div>
                            </td>
                            {['accuracy', 'precision', 'recall', 'f1_score'].map(key => (
                              <td key={key} className="px-4 py-3"
                                  style={{ fontFamily: "'JetBrains Mono'", color: isBest ? '#34d399' : '#94a3b8' }}>
                                {m[key] != null ? `${m[key]}%` : '—'}
                              </td>
                            ))}
                            <td className="px-4 py-3" style={{ fontFamily: "'JetBrains Mono'", color: isBest ? '#f472b6' : '#d8b4fe' }}>
                              {m.macro_f1 != null ? `${m.macro_f1}%` : '—'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* F1-Score bar chart with 90% target reference */}
            {modelReport.evaluation && Object.keys(modelReport.evaluation).length > 0 && (
              <div>
                <p className="text-xs text-slate-500 mb-3 flex items-center gap-2" style={{ fontFamily: "'DM Sans'" }}>
                  <TrendingUp size={11} className="text-emerald-400" />
                  F1-Score Comparison
                  <span className="text-slate-600">— dashed line = 90% target (document expected)</span>
                </p>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart
                    data={Object.entries(modelReport.evaluation as Record<string, any>).map(([name, m]: [string, any]) => ({
                      name: name.replace('Linear SVM (Calibrated)', 'LinearSVC')
                               .replace('Linear SVM Tuned', 'SVM Tuned')
                               .replace('Logistic Regression', 'Log. Reg.')
                               .replace('k-NN (cosine)', 'k-NN')
                               .replace('Multinomial NB', 'Naive Bayes')
                               .replace('Gradient Boosting', 'Grad. Boost')
                               .replace('Random Forest', 'Rand. Forest'),
                      f1: m.f1_score ?? 0,
                      isBest: name === modelReport.best_model,
                    }))}
                    margin={{ left: 0, right: 16, top: 8, bottom: 40 }}>
                    <defs>
                      <linearGradient id="f1Bar" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#34d399" stopOpacity={0.9} />
                        <stop offset="100%" stopColor="#34d399" stopOpacity={0.4} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" tick={{ fill: 'rgba(148,163,184,0.6)', fontSize: 9, fontFamily: "'DM Sans'" }}
                           axisLine={false} tickLine={false} angle={-30} textAnchor="end" interval={0} />
                    <YAxis tick={{ fill: 'rgba(148,163,184,0.4)', fontSize: 10 }}
                           axisLine={false} tickLine={false}
                           domain={[0, 100]} tickFormatter={v => `${v}%`} />
                    <Tooltip content={<GlassTip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                    <Bar dataKey="f1" name="F1-Score" unit="%" radius={[4,4,0,0]}>
                      {Object.entries(modelReport.evaluation as Record<string, any>).map(([name, _]: [string, any], i) => (
                        <Cell key={i} fill={name === modelReport.best_model ? '#34d399' : 'url(#f1Bar)'} fillOpacity={name === modelReport.best_model ? 1 : 0.65} />
                      ))}
                    </Bar>
                    <ReferenceLine y={90} stroke="#fbbf24" strokeDasharray="4 4" strokeWidth={1}
                                   label={{ value: '90% target', position: 'right', fill: '#fbbf24', fontSize: 9 }} />
                  </BarChart>
                </ResponsiveContainer>
                <p className="text-xs text-amber-600 mt-1" style={{ fontFamily: "'DM Sans'" }}>
                  Target: 90% F1-Score (document expected range: 90–94%)
                </p>
              </div>
            )}

            {/* Per-class metrics table */}
            {modelReport.per_class && Object.keys(modelReport.per_class).length > 0 && (
              <div>
                <p className="text-xs text-slate-500 mb-3 flex items-center gap-2" style={{ fontFamily: "'DM Sans'" }}>
                  <Target size={11} className="text-pink-400" />
                  Per-Class Metrics — Best Model (test set)
                  <span className="text-slate-600">· Macro F1 = honest average across all roles</span>
                </p>
                <div className="overflow-x-auto rounded-xl" style={{ border: '1px solid rgba(255,255,255,0.07)' }}>
                  <table className="w-full text-xs" style={{ borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ background: 'rgba(255,255,255,0.04)', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                        {['Role', 'Precision', 'Recall', 'F1-Score', 'Support'].map(h => (
                          <th key={h} className="text-left px-4 py-2.5 font-semibold text-slate-400"
                              style={{ fontFamily: "'DM Sans'", fontSize: 10 }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(modelReport.per_class as Record<string, any>)
                        .sort(([, a]: any, [, b]: any) => b.f1_score - a.f1_score)
                        .map(([role, m]: [string, any], i) => {
                          const f1Color = m.f1_score >= 85 ? '#34d399' : m.f1_score >= 70 ? '#60a5fa' : m.f1_score >= 50 ? '#fbbf24' : '#f87171';
                          return (
                            <tr key={role} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)',
                                                    background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.012)' }}>
                              <td className="px-4 py-2.5 text-slate-300" style={{ fontFamily: "'DM Sans'" }}>{role}</td>
                              <td className="px-4 py-2.5" style={{ fontFamily: "'JetBrains Mono'", color: '#94a3b8' }}>{m.precision}%</td>
                              <td className="px-4 py-2.5" style={{ fontFamily: "'JetBrains Mono'", color: '#94a3b8' }}>{m.recall}%</td>
                              <td className="px-4 py-2.5">
                                <div className="flex items-center gap-2">
                                  <span style={{ fontFamily: "'JetBrains Mono'", color: f1Color, fontWeight: 600 }}>{m.f1_score}%</span>
                                  <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)', maxWidth: 60 }}>
                                    <div style={{ width: `${m.f1_score}%`, height: '100%', background: f1Color, borderRadius: 4 }} />
                                  </div>
                                </div>
                              </td>
                              <td className="px-4 py-2.5 text-slate-500" style={{ fontFamily: "'JetBrains Mono'" }}>{m.support}</td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Confusion Matrix */}
            {modelReport.confusion_matrix?.matrix && modelReport.confusion_matrix?.labels && (
              <div>
                <p className="text-xs text-slate-500 mb-3 flex items-center gap-2" style={{ fontFamily: "'DM Sans'" }}>
                  <Target size={11} className="text-amber-400" />
                  Confusion Matrix — Best Model (test set)
                  <span className="text-slate-600">· darker = more predictions in that cell</span>
                </p>
                <div className="overflow-auto rounded-xl" style={{ border: '1px solid rgba(255,255,255,0.07)', maxHeight: 420 }}>
                  {(() => {
                    const labels: string[] = modelReport.confusion_matrix.labels;
                    const matrix: number[][] = modelReport.confusion_matrix.matrix;
                    const maxVal = Math.max(...matrix.flat());
                    const short = (r: string) => r.replace(' Developer','Dev').replace(' Engineer','Eng')
                                                   .replace('Full Stack','FullStack').replace('Business','Biz')
                                                   .replace('Administrator','Admin').replace('System','Sys');
                    return (
                      <table style={{ borderCollapse: 'collapse', fontSize: 9 }}>
                        <thead>
                          <tr>
                            <th style={{ padding: '4px 6px', color: 'rgba(148,163,184,0.5)', fontFamily: "'DM Sans'", fontWeight: 400, textAlign: 'right', minWidth: 72 }}>Actual ↓ Pred →</th>
                            {labels.map(l => (
                              <th key={l} style={{ padding: '4px 5px', color: 'rgba(148,163,184,0.6)', fontFamily: "'DM Sans'", fontWeight: 500,
                                                   writingMode: 'vertical-rl', transform: 'rotate(180deg)', height: 80, verticalAlign: 'bottom', whiteSpace: 'nowrap' }}>
                                {short(l)}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {matrix.map((row, ri) => (
                            <tr key={ri}>
                              <td style={{ padding: '3px 6px', color: 'rgba(148,163,184,0.7)', fontFamily: "'DM Sans'", whiteSpace: 'nowrap', fontSize: 9 }}>
                                {short(labels[ri])}
                              </td>
                              {row.map((val, ci) => {
                                const isDiag  = ri === ci;
                                const opacity = maxVal > 0 ? val / maxVal : 0;
                                const bg      = isDiag
                                  ? `rgba(52,211,153,${Math.max(0.08, opacity * 0.85)})`
                                  : val > 0 ? `rgba(248,113,113,${Math.min(0.8, opacity * 0.9)})` : 'transparent';
                                return (
                                  <td key={ci} title={`${labels[ri]} → ${labels[ci]}: ${val}`}
                                      style={{ padding: '3px 5px', textAlign: 'center', background: bg,
                                               color: val === 0 ? 'rgba(148,163,184,0.2)' : isDiag ? '#6ee7b7' : '#fca5a5',
                                               fontFamily: "'JetBrains Mono'", fontWeight: isDiag ? 700 : 400,
                                               minWidth: 28, border: '1px solid rgba(255,255,255,0.03)' }}>
                                    {val}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    );
                  })()}
                </div>
                <p className="text-xs text-slate-600 mt-1.5" style={{ fontFamily: "'DM Sans'" }}>
                  Green diagonal = correct predictions · Red off-diagonal = confusion between roles
                </p>
              </div>
            )}

            {/* Roles list */}
            {modelReport.roles?.length > 0 && (
              <div>
                <p className="text-xs text-slate-500 mb-2" style={{ fontFamily: "'DM Sans'" }}>
                  Trained Career Roles ({modelReport.roles.length})
                </p>
                <div className="flex flex-wrap gap-2">
                  {modelReport.roles.map((role: string) => (
                    <span key={role} className="text-xs px-3 py-1 rounded-full"
                          style={{ background: 'rgba(167,139,250,0.08)', border: '1px solid rgba(167,139,250,0.2)', color: '#c4b5fd', fontFamily: "'DM Sans'" }}>
                      {role}
                    </span>
                  ))}
                </div>
              </div>
            )}

          </div>
        )}
      </div>

    </div>
  );
}