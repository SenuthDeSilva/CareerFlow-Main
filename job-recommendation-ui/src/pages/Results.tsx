import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Briefcase, MapPin, DollarSign, ExternalLink,
  ChevronRight, RefreshCw, Brain, Target,
  CheckCircle, XCircle, AlertCircle,
  ArrowLeft, Sparkles, Filter, TrendingUp,
  Building2, Bookmark, BookmarkCheck
} from 'lucide-react';
import { getRecommendations, getResume, Recommendation } from '../api/client';
import api from '../api/client';

// ── Score Ring ───────────────────────────────────────────────
function ScoreRing({ value, color, label, size = 48 }: {
  value: number; color: string; label: string; size?: number;
}) {
  const [animated, setAnimated] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setAnimated(value), 100);
    return () => clearTimeout(t);
  }, [value]);

  const r    = size / 2 - 4;
  const circ = 2 * Math.PI * r;
  const fill = (animated / 100) * circ;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
          <circle cx={size/2} cy={size/2} r={r} fill="none"
                  stroke="rgba(255,255,255,0.06)" strokeWidth="3" />
          <circle cx={size/2} cy={size/2} r={r} fill="none"
                  stroke={color} strokeWidth="3"
                  strokeDasharray={`${fill} ${circ}`}
                  strokeLinecap="round"
                  style={{ transition: 'stroke-dasharray 0.8s cubic-bezier(0.16,1,0.3,1)' }} />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-bold text-white" style={{ fontSize: size > 44 ? 12 : 10,
            fontFamily: "'JetBrains Mono', monospace" }}>
            {value}%
          </span>
        </div>
      </div>
      <span className="text-slate-500" style={{ fontSize: 10, fontFamily: "'DM Sans', sans-serif" }}>
        {label}
      </span>
    </div>
  );
}

// ── Score Badge ──────────────────────────────────────────────
function ScoreBadge({ pct }: { pct: number }) {
  const cfg = pct >= 55
    ? { bg: 'rgba(52,211,153,0.1)',  border: 'rgba(52,211,153,0.25)',  color: '#34d399', label: 'Strong' }
    : pct >= 35
    ? { bg: 'rgba(251,191,36,0.1)',  border: 'rgba(251,191,36,0.25)',  color: '#fbbf24', label: 'Good'   }
    : { bg: 'rgba(96,165,250,0.1)',  border: 'rgba(96,165,250,0.25)',  color: '#60a5fa', label: 'Fair'   };

  return (
    <div className="flex flex-col items-center px-4 py-2.5 rounded-xl"
         style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}>
      <span className="text-2xl font-bold" style={{ color: cfg.color, fontFamily: "'Syne', sans-serif" }}>
        {pct}%
      </span>
      <span className="text-xs font-medium mt-0.5" style={{ color: cfg.color, opacity: 0.8 }}>
        {cfg.label}
      </span>
    </div>
  );
}

// ── Job Card ─────────────────────────────────────────────────
function JobCard({ rec, onExplain, index, bookmarkedIds, onBookmark }: {
  rec: Recommendation; onExplain: () => void; index: number;
  bookmarkedIds: Set<number>; onBookmark: (id: number, e: React.MouseEvent) => void;
}) {
  const isBookmarked = bookmarkedIds.has(rec.job_id);
  const [expanded, setExpanded] = useState(false);
  const isTopjobs = (rec.source || '').toLowerCase() === 'topjobs';

  return (
    <div className="rounded-2xl overflow-hidden transition-all duration-300 animate-slide-up group"
         style={{
           animationDelay: `${index * 40}ms`,
           background: 'rgba(255,255,255,0.025)',
           border: '1px solid rgba(255,255,255,0.07)',
           boxShadow: '0 4px 24px rgba(0,0,0,0.2)',
         }}
         onMouseEnter={e => {
           (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.12)';
           (e.currentTarget as HTMLElement).style.boxShadow = '0 8px 32px rgba(0,0,0,0.3)';
         }}
         onMouseLeave={e => {
           (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.07)';
           (e.currentTarget as HTMLElement).style.boxShadow = '0 4px 24px rgba(0,0,0,0.2)';
         }}>

      {/* Card body */}
      <div className="p-5">
        <div className="flex items-start gap-4">

          {/* Rank badge */}
          <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 mt-0.5"
               style={{
                 background: rec.rank <= 3 ? 'rgba(251,191,36,0.1)' : 'rgba(255,255,255,0.04)',
                 border: rec.rank <= 3 ? '1px solid rgba(251,191,36,0.2)' : '1px solid rgba(255,255,255,0.07)',
               }}>
            <span className="text-xs font-bold" style={{
              color: rec.rank <= 3 ? '#fbbf24' : 'rgba(148,163,184,0.6)',
              fontFamily: "'Syne', sans-serif",
            }}>#{rec.rank}</span>
          </div>

          {/* Job info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                    style={isTopjobs
                      ? { background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.2)', color: '#93c5fd' }
                      : { background: 'rgba(167,139,250,0.1)', border: '1px solid rgba(167,139,250,0.2)', color: '#c4b5fd' }}>
                {isTopjobs ? 'TopJobs.lk' : 'Rooster.jobs'}
              </span>
            </div>
            <h3 className="font-semibold text-white leading-tight mb-1"
                style={{ fontFamily: "'DM Sans', sans-serif" }}>
              {rec.title}
            </h3>
            <p className="text-sm text-slate-400 flex items-center gap-1.5">
              <Building2 size={11} />
              {rec.company}
            </p>

            {/* Meta */}
            <div className="flex flex-wrap gap-3 mt-2.5">
              {rec.location && (
                <span className="flex items-center gap-1 text-xs text-slate-500">
                  <MapPin size={11} />{rec.location}
                </span>
              )}
              {rec.salary && (
                <span className="flex items-center gap-1 text-xs text-slate-500">
                  <DollarSign size={11} />{rec.salary}
                </span>
              )}
            </div>
          </div>

          {/* Score */}
          <ScoreBadge pct={rec.hybrid_score_pct} />
        </div>

        {/* Score rings row */}
        <div className="flex items-center gap-5 mt-5 pt-4"
             style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <ScoreRing value={rec.tfidf_score_pct}                          color="#60a5fa" label="TF-IDF" />
          <ScoreRing value={Math.round((rec.word2vec_score || 0) * 100)}  color="#a78bfa" label="W2V"    />
          <ScoreRing value={rec.skill_score_pct}                          color="#34d399" label="Skill"  />
          <ScoreRing value={Math.round((rec.ml_score || 0) * 100)}        color="#fbbf24" label="ML"     />

          <div className="ml-auto flex items-center gap-2">
            <button onClick={(e) => onBookmark(rec.job_id, e)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium
                         transition-all duration-150 active:scale-95"
              style={isBookmarked
                ? { background: 'rgba(251,191,36,0.12)', border: '1px solid rgba(251,191,36,0.25)', color: '#fbbf24' }
                : { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#64748b' }}
              title={isBookmarked ? 'Remove bookmark' : 'Save job'}>
              {isBookmarked ? <BookmarkCheck size={11} /> : <Bookmark size={11} />}
            </button>
            <button onClick={onExplain}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium
                         transition-all duration-150 active:scale-95"
              style={{ background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.2)', color: '#c4b5fd' }}>
              <Sparkles size={11} />
              Explain
            </button>

            {rec.job_url && (
              <a href={rec.job_url} target="_blank" rel="noopener noreferrer"
                 className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium
                            transition-all duration-150 active:scale-95"
                 style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)', color: '#93c5fd' }}>
                <ExternalLink size={11} />
                Apply
              </a>
            )}

            <button onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium
                         text-slate-400 hover:text-white transition-all duration-150"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
              {expanded ? 'Less' : 'Skills'}
              <ChevronRight size={11} className={`transition-transform ${expanded ? 'rotate-90' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {/* Expanded skills */}
      {expanded && (
        <div className="px-5 pb-5 grid grid-cols-2 gap-4 animate-fade-in"
             style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 16 }}>
          {rec.matched_skills?.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2.5">
                <CheckCircle size={12} className="text-emerald-400" />
                <span className="text-xs font-medium text-emerald-400">
                  Matched ({rec.matched_skills.length})
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {rec.matched_skills.map(s => (
                  <span key={s} className="text-xs px-2 py-0.5 rounded-full"
                        style={{ background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.18)', color: '#6ee7b7' }}>
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
          {rec.missing_skills?.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2.5">
                <XCircle size={12} className="text-rose-400" />
                <span className="text-xs font-medium text-rose-400">
                  Missing ({rec.missing_skills.length})
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {rec.missing_skills.map(s => (
                  <span key={s} className="text-xs px-2 py-0.5 rounded-full"
                        style={{ background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.18)', color: '#fda4af' }}>
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main ─────────────────────────────────────────────────────
export default function Results() {
  const { resumeId } = useParams();
  const navigate     = useNavigate();
  const [recs,       setRecs]        = useState<Recommendation[]>([]);
  const [resume,     setResume]      = useState<any>(null);
  const [loading,    setLoading]     = useState(true);
  const [error,      setError]       = useState('');
  const [refreshing, setRefreshing]  = useState(false);
  const [filter,       setFilter]      = useState('all');
  const [bookmarkedIds,setBookmarkedIds] = useState<Set<number>>(new Set());

  const fetchData = React.useCallback(async (refresh = false) => {
    if (!resumeId) return;
    refresh ? setRefreshing(true) : setLoading(true);
    setError('');
    try {
      const [rr, rs] = await Promise.all([
        getRecommendations(parseInt(resumeId), refresh),
        getResume(parseInt(resumeId)),
      ]);
      setRecs(rr.data.recommendations || []);
      setResume(rs.data.resume);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load recommendations.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [resumeId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    api.get('/api/bookmarks/ids').then(r => {
      setBookmarkedIds(new Set(r.data.ids || []));
    }).catch(() => {});
  }, []);

  const toggleBookmark = async (jobId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      if (bookmarkedIds.has(jobId)) {
        await api.delete(`/api/bookmarks/${jobId}`);
        setBookmarkedIds(prev => { const s = new Set(Array.from(prev)); s.delete(jobId); return s; });
      } else {
        await api.post(`/api/bookmarks/${jobId}`);
        setBookmarkedIds(prev => new Set(Array.from(prev).concat(jobId)));
      }
    } catch {}
  };

  const filtered = filter === 'all' ? recs
    : recs.filter(r => (r.source || '').toLowerCase() === filter);

  const stats = recs.length > 0 ? {
    best: recs[0]?.hybrid_score_pct,
    avg:  Math.round(recs.reduce((a, r) => a + r.hybrid_score_pct, 0) / recs.length),
    avgSkills: Math.round(recs.reduce((a, r) => a + (r.matched_skills?.length || 0), 0) / recs.length),
    topjobs: recs.filter(r => (r.source||'').toLowerCase() === 'topjobs').length,
    rooster: recs.filter(r => (r.source||'').toLowerCase() === 'rooster').length,
  } : null;

  return (
    <div className="px-10 py-7 w-full animate-fade-in">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)}
            className="w-9 h-9 rounded-xl flex items-center justify-center text-slate-400
                       hover:text-white transition-all duration-150"
            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
            <ArrowLeft size={16} />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-white"
                style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '-0.02em' }}>
              Job Recommendations
            </h1>
            {resume && (
              <p className="text-sm text-slate-400 mt-0.5" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                {resume.candidate_name || resume.email} · {resume.skills_count} skills detected
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => navigate(`/explain/${resumeId}`)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium
                       transition-all duration-150 active:scale-95"
            style={{ background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.2)', color: '#c4b5fd' }}>
            <Sparkles size={14} />
            XAI Explain
          </button>
          <button onClick={() => fetchData(true)} disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold
                       text-white transition-all duration-150 active:scale-95 disabled:opacity-50"
            style={{ background: 'linear-gradient(135deg, #3b82f6, #2563eb)', boxShadow: '0 4px 16px rgba(37,99,235,0.25)' }}>
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stat pills */}
      {!loading && stats && (
        <div className="flex flex-wrap gap-3 mb-6 animate-slide-up">
          {[
            { icon: TrendingUp, label: 'Best Match',   value: `${stats.best}%`,     color: '#34d399' },
            { icon: Target,     label: 'Avg Match',    value: `${stats.avg}%`,      color: '#fbbf24' },
            { icon: CheckCircle,label: 'Avg Skills',   value: `${stats.avgSkills}`, color: '#60a5fa' },
            { icon: Briefcase,  label: 'Total Matches',value: `${recs.length}`,     color: '#a78bfa' },
          ].map(s => (
            <div key={s.label} className="flex items-center gap-2 px-4 py-2.5 rounded-xl"
                 style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}>
              <s.icon size={14} style={{ color: s.color }} />
              <span className="text-xs text-slate-400" style={{ fontFamily: "'DM Sans', sans-serif" }}>{s.label}</span>
              <span className="text-sm font-bold text-white" style={{ fontFamily: "'Syne', sans-serif" }}>{s.value}</span>
            </div>
          ))}
        </div>
      )}

      {/* Predicted Career Role banner */}
      {!loading && resume?.predicted_role && (
        <div className="flex items-center gap-4 px-5 py-3.5 rounded-xl mb-4 animate-slide-up"
             style={{ background: 'rgba(139,92,246,0.07)', border: '1px solid rgba(139,92,246,0.18)' }}>
          <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
               style={{ background: 'rgba(139,92,246,0.12)', border: '1px solid rgba(139,92,246,0.22)' }}>
            <Sparkles size={14} className="text-violet-400" />
          </div>
          <div className="flex-1">
            <p className="text-xs text-slate-400" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              Predicted Career Role
            </p>
            <p className="text-sm font-bold text-violet-300 mt-0.5" style={{ fontFamily: "'Syne', sans-serif" }}>
              {resume.predicted_role}
            </p>
          </div>
          {resume.role_confidence > 0 && (
            <span className="text-xs font-bold px-3 py-1.5 rounded-xl"
                  style={{ background: 'rgba(139,92,246,0.12)', color: '#c4b5fd',
                           border: '1px solid rgba(139,92,246,0.22)', fontFamily: "'Syne', sans-serif" }}>
              {Number(resume.role_confidence).toFixed(1)}% confidence
            </span>
          )}
        </div>
      )}

      {/* Pipeline info */}
      <div className="flex items-center gap-3 mb-4 px-4 py-3 rounded-xl animate-slide-up"
           style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
        <Brain size={13} className="text-blue-400 shrink-0" />
        <p className="text-xs text-slate-500" style={{ fontFamily: "'DM Sans', sans-serif" }}>
          Pipeline:{' '}
          {['TF-IDF Similarity', 'Word2Vec Semantics', 'Skill Gap Analysis', 'Career Role Prediction'].map((step, i, arr) => (
            <span key={step}>
              <span className="text-slate-300">{step}</span>
              {i < arr.length - 1 && <span className="mx-1 text-slate-700">→</span>}
            </span>
          ))}
          <span className="ml-2 font-mono" style={{ color: '#34d399', fontSize: 10 }}>→ Top 20</span>
        </p>
      </div>

      {/* Source filter */}
      {!loading && recs.length > 0 && (
        <div className="flex items-center gap-2 mb-6 animate-slide-up">
          <Filter size={12} className="text-slate-500 shrink-0" />
          <span className="text-xs text-slate-500 mr-1">Filter:</span>
          {[
            { label: 'All Sources',  value: 'all',     count: recs.length },
            { label: 'TopJobs.lk',   value: 'topjobs', count: stats?.topjobs || 0 },
            { label: 'Rooster.jobs', value: 'rooster', count: stats?.rooster || 0 },
          ].filter(f => f.count > 0).map(f => (
            <button key={f.value} onClick={() => setFilter(f.value)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all duration-150"
              style={filter === f.value ? {
                background: 'rgba(59,130,246,0.15)',
                border: '1px solid rgba(59,130,246,0.3)',
                color: '#93c5fd',
              } : {
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.07)',
                color: 'rgba(148,163,184,0.7)',
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
        <div className="flex items-center gap-3 px-5 py-4 rounded-2xl mb-6"
             style={{ background: 'rgba(244,63,94,0.07)', border: '1px solid rgba(244,63,94,0.18)' }}>
          <AlertCircle size={16} className="text-rose-400 shrink-0" />
          <p className="text-sm text-rose-300" style={{ fontFamily: "'DM Sans', sans-serif" }}>{error}</p>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-36 rounded-2xl skeleton" style={{ animationDelay: `${i*80}ms` }} />
          ))}
        </div>
      )}

      {/* Results */}
      {!loading && filtered.length > 0 && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {filtered.map((rec, i) => (
            <JobCard key={rec.job_id} rec={rec} index={i}
              onExplain={() => navigate(`/explain/${resumeId}`)}
              bookmarkedIds={bookmarkedIds} onBookmark={toggleBookmark} />
          ))}
        </div>
      )}

      {/* Empty */}
      {!loading && filtered.length === 0 && !error && (
        <div className="py-20 text-center">
          <div className="w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center"
               style={{ background: 'rgba(59,130,246,0.07)', border: '1px solid rgba(59,130,246,0.15)' }}>
            <Target size={24} className="text-blue-400" />
          </div>
          <p className="text-slate-300 font-semibold mb-1" style={{ fontFamily: "'DM Sans', sans-serif" }}>
            No recommendations found
          </p>
          <p className="text-sm text-slate-500 mb-5">Run ML matching to get job recommendations</p>
          <button onClick={() => fetchData(true)}
            className="px-6 py-2.5 rounded-xl text-sm font-semibold text-white transition-all active:scale-95"
            style={{ background: 'linear-gradient(135deg, #3b82f6, #2563eb)', boxShadow: '0 4px 16px rgba(37,99,235,0.25)' }}>
            Run ML Matching
          </button>
        </div>
      )}
    </div>
  );
}