import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts';
import {
  Sparkles, ArrowLeft, AlertCircle, ChevronRight,
  BarChart3, Tag, Briefcase, CheckCircle, XCircle,
  Brain, Zap, Filter, TrendingUp, Info
} from 'lucide-react';
import { getExplanations, getResume } from '../api/client';

// ── Types ────────────────────────────────────────────────────
interface XAIExp {
  rank: number; job_id: number; job_title?: string; title?: string;
  company: string; source: string; hybrid_score_pct: number;
  shap: {
    summary?: string; why_recommended?: string[];
    improvement_tips?: string[]; feature_values?: Record<string,number>;
    contributions?: Record<string,number>;
  };
  lime: {
    explanation?: string; top_keywords?: string[];
    job_keywords?: string[]; shared_keywords?: string[];
    keyword_matches?: number;
  };
  skill_gap: { matched?: string[]; missing?: string[]; };
}

const FEATURE_LABELS: Record<string,string> = {
  tfidf_score:'TF-IDF', skill_score:'Skill Match', word2vec_score:'Word2Vec',
  matched_count:'Matched Skills', missing_count:'Missing Skills',
  total_job_skills:'Job Skills Total', skill_coverage:'Skill Coverage',
  is_intern_level:'Intern Level', has_salary:'Has Salary',
};

const FEATURE_COLORS: Record<string,string> = {
  tfidf_score:'#60a5fa', word2vec_score:'#a78bfa', skill_score:'#34d399',
  matched_count:'#34d399', missing_count:'#f87171', skill_coverage:'#fbbf24',
  total_job_skills:'#22d3ee', is_intern_level:'#fb923c', has_salary:'#a3e635',
};

// ── Custom SHAP Tooltip ──────────────────────────────────────
function ShapTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="px-3 py-2 rounded-xl text-xs"
         style={{ background: 'rgba(10,15,30,0.95)', border: '1px solid rgba(255,255,255,0.1)', backdropFilter: 'blur(16px)' }}>
      <p className="font-semibold text-white mb-0.5">{d.label}</p>
      <p style={{ color: d.value >= 0 ? '#34d399' : '#f87171' }}>
        {d.value >= 0 ? '+' : ''}{(d.value * 100).toFixed(1)}% contribution
      </p>
    </div>
  );
}

// ── SHAP Chart ───────────────────────────────────────────────
function ShapChart({ contributions }: { contributions: Record<string,number> }) {
  const data = Object.entries(contributions)
    .map(([k, v]) => ({ key: k, label: FEATURE_LABELS[k] || k, value: Number(v), color: FEATURE_COLORS[k] || '#60a5fa' }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, 8);

  if (!data.length) return (
    <div className="py-8 text-center text-slate-600 text-sm">No SHAP data available</div>
  );

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
        <XAxis type="number" tick={{ fill: 'rgba(148,163,184,0.5)', fontSize: 10,
          fontFamily: "'JetBrains Mono', monospace" }}
          axisLine={false} tickLine={false}
          tickFormatter={v => `${(v*100).toFixed(0)}%`} />
        <YAxis type="category" dataKey="label" width={88}
          tick={{ fill: 'rgba(148,163,184,0.7)', fontSize: 10, fontFamily: "'DM Sans', sans-serif" }}
          axisLine={false} tickLine={false} />
        <Tooltip content={<ShapTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={14}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.value >= 0 ? (d.color || '#60a5fa') : '#f87171'} opacity={0.85} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── Keyword Cloud ────────────────────────────────────────────
function KeywordCloud({ keywords, shared, jobKeywords }: {
  keywords: string[]; shared: string[]; jobKeywords: string[];
}) {
  if (!keywords.length && !shared.length) return (
    <div className="py-8 text-center text-slate-600 text-sm">No keyword data available</div>
  );

  return (
    <div className="space-y-4">
      {shared.length > 0 && (
        <div>
          <p className="text-xs font-medium mb-2.5 flex items-center gap-1.5"
             style={{ color: '#34d399', fontFamily: "'DM Sans', sans-serif" }}>
            <CheckCircle size={11} /> Shared keywords ({shared.length} matched)
          </p>
          <div className="flex flex-wrap gap-1.5">
            {shared.map(kw => (
              <span key={kw} className="px-2.5 py-1 rounded-full text-xs font-medium"
                    style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.25)', color: '#6ee7b7' }}>
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}
      {keywords.length > 0 && (
        <div>
          <p className="text-xs font-medium mb-2.5 flex items-center gap-1.5"
             style={{ color: '#93c5fd', fontFamily: "'DM Sans', sans-serif" }}>
            <Tag size={11} /> Resume keywords
          </p>
          <div className="flex flex-wrap gap-1.5">
            {keywords.map(kw => (
              <span key={kw} className="px-2.5 py-1 rounded-full text-xs"
                    style={{ background: shared.includes(kw) ? 'rgba(52,211,153,0.08)' : 'rgba(96,165,250,0.08)',
                             border: shared.includes(kw) ? '1px solid rgba(52,211,153,0.2)' : '1px solid rgba(96,165,250,0.2)',
                             color: shared.includes(kw) ? '#6ee7b7' : '#93c5fd' }}>
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}
      {jobKeywords.length > 0 && (
        <div>
          <p className="text-xs font-medium mb-2.5 flex items-center gap-1.5"
             style={{ color: 'rgba(148,163,184,0.6)', fontFamily: "'DM Sans', sans-serif" }}>
            <Briefcase size={11} /> Job requires
          </p>
          <div className="flex flex-wrap gap-1.5">
            {jobKeywords.slice(0,12).map(kw => (
              <span key={kw} className="px-2.5 py-1 rounded-full text-xs text-slate-500"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}>
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Explain Card ─────────────────────────────────────────────
function ExplainCard({ exp, index }: { exp: XAIExp; index: number }) {
  const [tab, setTab] = useState<'shap'|'lime'|'skills'>('shap');

  const title       = exp.job_title || exp.title || 'Unknown Job';
  const shap        = exp.shap || {};
  const lime        = exp.lime || {};
  const gap         = exp.skill_gap || {};
  const contribs    = (shap.contributions || {}) as Record<string,number>;
  const topKeywords = (lime.top_keywords   || []) as string[];
  const sharedKw    = (lime.shared_keywords || []) as string[];
  const jobKw       = (lime.job_keywords   || []) as string[];
  const whyList     = (shap.why_recommended || []) as string[];
  const tips        = (shap.improvement_tips || []) as string[];
  const isTopjobs   = (exp.source || '').toLowerCase() === 'topjobs';

  const scoreCfg = exp.hybrid_score_pct >= 55
    ? { color: '#34d399', bg: 'rgba(52,211,153,0.1)',  border: 'rgba(52,211,153,0.25)',  label: 'Strong Match'  }
    : exp.hybrid_score_pct >= 35
    ? { color: '#fbbf24', bg: 'rgba(251,191,36,0.1)',  border: 'rgba(251,191,36,0.25)',  label: 'Good Match'    }
    : { color: '#60a5fa', bg: 'rgba(96,165,250,0.1)',  border: 'rgba(96,165,250,0.25)',  label: 'Fair Match'    };

  const TABS = [
    { key: 'shap',   label: 'SHAP Features', icon: BarChart3 },
    { key: 'lime',   label: 'LIME Keywords',  icon: Tag       },
    { key: 'skills', label: 'Skill Gap',      icon: Zap       },
  ];

  return (
    <div className="rounded-2xl overflow-hidden animate-slide-up"
         style={{
           animationDelay: `${index * 60}ms`,
           background: 'rgba(255,255,255,0.025)',
           border: '1px solid rgba(255,255,255,0.07)',
           boxShadow: '0 4px 24px rgba(0,0,0,0.2)',
         }}>

      {/* Header */}
      <div className="px-5 py-4 flex items-start justify-between gap-4"
           style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
               style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.15)' }}>
            <span className="text-xs font-bold text-blue-400" style={{ fontFamily: "'Syne', sans-serif" }}>
              #{index + 1}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs px-2 py-0.5 rounded-full"
                    style={isTopjobs
                      ? { background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.2)', color: '#93c5fd' }
                      : { background: 'rgba(167,139,250,0.1)', border: '1px solid rgba(167,139,250,0.2)', color: '#c4b5fd' }}>
                {isTopjobs ? 'TopJobs.lk' : 'Rooster.jobs'}
              </span>
            </div>
            <h3 className="font-semibold text-white leading-tight" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              {title}
            </h3>
            <p className="text-sm text-slate-400">{exp.company}</p>
          </div>
        </div>
        <div className="shrink-0 px-4 py-2.5 rounded-xl text-center"
             style={{ background: scoreCfg.bg, border: `1px solid ${scoreCfg.border}` }}>
          <p className="text-xl font-bold" style={{ color: scoreCfg.color, fontFamily: "'Syne', sans-serif" }}>
            {exp.hybrid_score_pct}%
          </p>
          <p className="text-xs mt-0.5" style={{ color: scoreCfg.color, opacity: 0.7 }}>{scoreCfg.label}</p>
        </div>
      </div>

      {/* Why recommended */}
      {(whyList.length > 0 || tips.length > 0) && (
        <div className="px-5 py-3 space-y-1.5"
             style={{ background: 'rgba(255,255,255,0.015)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          {whyList.slice(0, 2).map((w, i) => (
            <div key={i} className="flex items-start gap-2">
              <CheckCircle size={11} className="text-emerald-400 shrink-0 mt-0.5" />
              <p className="text-xs text-slate-300" style={{ fontFamily: "'DM Sans', sans-serif" }}>{w}</p>
            </div>
          ))}
          {tips.slice(0, 1).map((t, i) => (
            <div key={i} className="flex items-start gap-2">
              <Info size={11} className="text-amber-400 shrink-0 mt-0.5" />
              <p className="text-xs text-slate-400" style={{ fontFamily: "'DM Sans', sans-serif" }}>{t}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key as any)}
            className="flex items-center gap-2 px-5 py-3 text-xs font-medium transition-all duration-150"
            style={{
              color: tab === t.key ? '#93c5fd' : 'rgba(148,163,184,0.5)',
              borderBottom: tab === t.key ? '2px solid #3b82f6' : '2px solid transparent',
              fontFamily: "'DM Sans', sans-serif",
              marginBottom: -1,
            }}>
            <t.icon size={13} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="p-5">

        {/* SHAP */}
        {tab === 'shap' && (
          <div className="animate-fade-in">
            <p className="text-xs text-slate-500 mb-4" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              Feature contributions to match score — positive increases, negative decreases
            </p>
            <ShapChart contributions={contribs} />
            {Object.keys(shap.feature_values || {}).length > 0 && (
              <div className="mt-4 pt-4 grid grid-cols-3 gap-2"
                   style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                {Object.entries(shap.feature_values || {}).slice(0, 6).map(([k, v]) => (
                  <div key={k} className="px-3 py-2 rounded-xl"
                       style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <p className="text-xs text-slate-500 truncate" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                      {FEATURE_LABELS[k] || k}
                    </p>
                    <p className="text-sm font-semibold text-white mt-0.5"
                       style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                      {typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : String(v)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* LIME */}
        {tab === 'lime' && (
          <div className="animate-fade-in">
            {lime.explanation && (
              <div className="px-4 py-3 rounded-xl mb-4 text-xs text-slate-300 leading-relaxed"
                   style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
                            fontFamily: "'DM Sans', sans-serif" }}>
                {lime.explanation}
              </div>
            )}
            <KeywordCloud keywords={topKeywords} shared={sharedKw} jobKeywords={jobKw} />
            <div className="mt-4 pt-4 flex items-center gap-3"
                 style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
              <span className="text-xs text-slate-500">Keyword matches:</span>
              <span className="text-sm font-bold text-blue-400"
                    style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                {lime.keyword_matches || 0}
              </span>
            </div>
          </div>
        )}

        {/* Skills */}
        {tab === 'skills' && (
          <div className="grid grid-cols-2 gap-5 animate-fade-in">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle size={13} className="text-emerald-400" />
                <span className="text-xs font-semibold text-emerald-400">
                  Matched ({gap.matched?.length || 0})
                </span>
              </div>
              {(gap.matched || []).length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {(gap.matched || []).map((s: string) => (
                    <span key={s} className="text-xs px-2.5 py-1 rounded-full"
                          style={{ background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.18)', color: '#6ee7b7' }}>
                      {s}
                    </span>
                  ))}
                </div>
              ) : <p className="text-xs text-slate-600">No matched skills</p>}
            </div>
            <div>
              <div className="flex items-center gap-2 mb-3">
                <XCircle size={13} className="text-rose-400" />
                <span className="text-xs font-semibold text-rose-400">
                  Missing ({gap.missing?.length || 0})
                </span>
              </div>
              {(gap.missing || []).length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {(gap.missing || []).map((s: string) => (
                    <span key={s} className="text-xs px-2.5 py-1 rounded-full"
                          style={{ background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.18)', color: '#fda4af' }}>
                      {s}
                    </span>
                  ))}
                </div>
              ) : <p className="text-xs text-slate-600">No missing skills</p>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────
export default function Explain() {
  const { resumeId } = useParams();
  const navigate     = useNavigate();
  const [exps,    setExps]    = useState<XAIExp[]>([]);
  const [resume,  setResume]  = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');
  const [filter,  setFilter]  = useState('all');

  useEffect(() => {
    if (!resumeId) return;
    (async () => {
      setLoading(true); setError('');
      try {
        const [e, r] = await Promise.all([
          getExplanations(parseInt(resumeId)),
          getResume(parseInt(resumeId)),
        ]);
        setExps(e.data.explanations || []);
        setResume(r.data.resume);
      } catch (err: any) {
        setError(err?.response?.status === 404
          ? 'No recommendations found. Go to Results page first.'
          : err?.response?.data?.detail || 'Failed to load explanations.');
      } finally { setLoading(false); }
    })();
  }, [resumeId]);

  const filtered = filter === 'all' ? exps
    : exps.filter(e => (e.source || '').toLowerCase() === filter);

  return (
    <div className="px-10 py-7 w-full animate-fade-in">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)}
            className="w-9 h-9 rounded-xl flex items-center justify-center text-slate-400
                       hover:text-white transition-all"
            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
            <ArrowLeft size={16} />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-white"
                style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '-0.02em' }}>
              XAI Explanations
            </h1>
            {resume && (
              <p className="text-sm text-slate-400 mt-0.5" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                {resume.candidate_name || resume.email}
              </p>
            )}
          </div>
        </div>
        <button onClick={() => navigate(`/results/${resumeId}`)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium
                     transition-all active:scale-95"
          style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)', color: '#93c5fd' }}>
          <Briefcase size={14} />
          View Jobs
          <ChevronRight size={14} />
        </button>
      </div>

      {/* Method cards */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {[
          { icon: BarChart3, title: 'SHAP Analysis',   sub: 'Feature contributions — what drives each recommendation',   color: '#60a5fa', bg: 'rgba(59,130,246,0.06)',  bd: 'rgba(59,130,246,0.14)' },
          { icon: Tag,       title: 'LIME Keywords',   sub: 'Word-level importance — which keywords matched',             color: '#a78bfa', bg: 'rgba(139,92,246,0.06)', bd: 'rgba(139,92,246,0.14)' },
        ].map(m => (
          <div key={m.title} className="flex items-start gap-3 px-4 py-4 rounded-2xl animate-slide-up"
               style={{ background: m.bg, border: `1px solid ${m.bd}` }}>
            <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
                 style={{ background: `${m.color}18`, border: `1px solid ${m.color}25` }}>
              <m.icon size={16} style={{ color: m.color }} />
            </div>
            <div>
              <p className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                {m.title}
              </p>
              <p className="text-xs mt-0.5 text-slate-400">{m.sub}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Source filter */}
      {!loading && exps.length > 0 && (
        <div className="flex items-center gap-2 mb-6 animate-slide-up">
          <Filter size={12} className="text-slate-500 shrink-0" />
          <span className="text-xs text-slate-500 mr-1">Filter:</span>
          {[
            { label: 'All Sources',  value: 'all',     count: exps.length },
            { label: 'TopJobs.lk',   value: 'topjobs', count: exps.filter(e => (e.source||'').toLowerCase() === 'topjobs').length },
            { label: 'Rooster.jobs', value: 'rooster', count: exps.filter(e => (e.source||'').toLowerCase() === 'rooster').length },
          ].filter(f => f.count > 0).map(f => (
            <button key={f.value} onClick={() => setFilter(f.value)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all"
              style={filter === f.value ? {
                background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(59,130,246,0.3)', color: '#93c5fd',
              } : {
                background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', color: 'rgba(148,163,184,0.6)',
              }}>
              {f.label}
              <span className="px-1.5 py-0.5 rounded-full text-xs"
                    style={{ background: filter === f.value ? 'rgba(59,130,246,0.25)' : 'rgba(255,255,255,0.07)' }}>
                {f.count}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-start gap-3 px-5 py-4 rounded-2xl mb-6"
             style={{ background: 'rgba(244,63,94,0.07)', border: '1px solid rgba(244,63,94,0.18)' }}>
          <AlertCircle size={16} className="text-rose-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-rose-300" style={{ fontFamily: "'DM Sans', sans-serif" }}>{error}</p>
            {error.includes('Results') && (
              <button onClick={() => navigate(`/results/${resumeId}`)}
                className="mt-2 flex items-center gap-1 text-xs text-rose-400 hover:text-rose-300">
                Go to Results <ChevronRight size={11} />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-64 rounded-2xl skeleton" style={{ animationDelay: `${i*100}ms` }} />
          ))}
        </div>
      )}

      {/* Cards */}
      {!loading && filtered.length > 0 && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 items-start">
          {filtered.map((exp, i) => (
            <ExplainCard key={exp.job_id || i} exp={exp} index={i} />
          ))}
        </div>
      )}

      {/* Empty */}
      {!loading && filtered.length === 0 && !error && (
        <div className="py-20 text-center">
          <div className="w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center"
               style={{ background: 'rgba(139,92,246,0.07)', border: '1px solid rgba(139,92,246,0.15)' }}>
            <Sparkles size={24} className="text-violet-400" />
          </div>
          <p className="text-slate-300 font-semibold mb-1" style={{ fontFamily: "'DM Sans', sans-serif" }}>
            No explanations available
          </p>
          <button onClick={() => navigate(`/results/${resumeId}`)}
            className="mt-4 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold
                       text-white transition-all active:scale-95"
            style={{ background: 'linear-gradient(135deg,#3b82f6,#2563eb)', boxShadow: '0 4px 16px rgba(37,99,235,0.25)' }}>
            Run Recommendations First <ChevronRight size={14} />
          </button>
        </div>
      )}
    </div>
  );
}