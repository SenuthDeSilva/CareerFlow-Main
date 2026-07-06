import React, { useEffect, useState, useCallback } from 'react';
import {
  Briefcase, Search, MapPin, DollarSign, ExternalLink,
  Filter, X, ChevronLeft, ChevronRight, Building2,
  Clock, AlertCircle, Calendar, Tag, Bookmark, BookmarkCheck
} from 'lucide-react';
import { getJobs, Job } from '../api/client';
import api from '../api/client';

const LIMIT = 21;

function JobModal({ job, onClose }: { job: Job; onClose: () => void }) {
  const isTopjobs = job.source?.toLowerCase() === 'topjobs';

  useEffect(() => {
    const fn = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', fn);
    return () => window.removeEventListener('keydown', fn);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
         style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}
         onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl animate-scale-in"
           style={{ background: 'rgba(10,15,30,0.97)', border: '1px solid rgba(255,255,255,0.1)',
                    boxShadow: '0 24px 64px rgba(0,0,0,0.6)' }}>

        {/* Modal header */}
        <div className="sticky top-0 flex items-start justify-between px-6 py-5 rounded-t-2xl"
             style={{ background: 'rgba(10,15,30,0.98)', borderBottom: '1px solid rgba(255,255,255,0.06)',
                      backdropFilter: 'blur(16px)' }}>
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                 style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
              <Briefcase size={18} className="text-blue-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                      style={isTopjobs
                        ? { background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.2)', color: '#93c5fd' }
                        : { background: 'rgba(167,139,250,0.1)', border: '1px solid rgba(167,139,250,0.2)', color: '#c4b5fd' }}>
                  {isTopjobs ? 'TopJobs.lk' : 'Rooster.jobs'}
                </span>
              </div>
              <h2 className="font-bold text-white leading-tight" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                {job.title}
              </h2>
              <p className="text-sm text-slate-400 mt-0.5">{job.company}</p>
            </div>
          </div>
          <button onClick={onClose}
            className="w-8 h-8 rounded-xl flex items-center justify-center text-slate-500
                       hover:text-white transition-all ml-3 shrink-0"
            style={{ background: 'rgba(255,255,255,0.05)' }}>
            <X size={14} />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* Meta chips */}
          <div className="flex flex-wrap gap-2">
            {[
              { icon: MapPin,    value: job.location, color: '#60a5fa' },
              { icon: DollarSign,value: job.salary,   color: '#34d399' },
              { icon: Building2, value: job.source,   color: '#a78bfa' },
              { icon: Clock,     value: job.job_type, color: '#fbbf24' },
            ].filter(m => m.value).map((m, i) => (
              <div key={i} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs"
                   style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
                            color: 'rgba(226,232,240,0.8)' }}>
                <m.icon size={12} style={{ color: m.color }} />
                {m.value}
              </div>
            ))}
          </div>

          {/* Description */}
          {job.description && (
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                Job Description
              </p>
              <div className="px-4 py-4 rounded-xl text-sm text-slate-300 leading-relaxed whitespace-pre-wrap"
                   style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
                            fontFamily: "'DM Sans', sans-serif", maxHeight: 300, overflowY: 'auto' }}>
                {job.description.length > 1200 ? job.description.slice(0, 1200) + '...' : job.description}
              </div>
            </div>
          )}

          {/* Apply button */}
          {job.job_url && (
            <a href={job.job_url} target="_blank" rel="noopener noreferrer"
               className="flex items-center justify-center gap-2 w-full py-3.5 rounded-2xl
                          font-semibold text-sm text-white transition-all active:scale-98"
               style={{ background: 'linear-gradient(135deg,#3b82f6,#2563eb)',
                        boxShadow: '0 4px 16px rgba(37,99,235,0.3)', fontFamily: "'DM Sans', sans-serif" }}>
              <ExternalLink size={16} />
              Apply for this Job
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

function JobCard({ job, onClick, onBookmark, bookmarkedIds }: { job: Job; onClick: () => void; onBookmark: (id: number, e: React.MouseEvent) => void; bookmarkedIds: Set<number> }) {
  const isTopjobs = job.source?.toLowerCase() === 'topjobs';

  return (
    <div onClick={onClick}
      className="rounded-2xl p-5 cursor-pointer transition-all duration-200 group animate-slide-up"
      style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}
      onMouseEnter={e => {
        const el = e.currentTarget as HTMLElement;
        el.style.background = 'rgba(255,255,255,0.04)';
        el.style.borderColor = 'rgba(255,255,255,0.12)';
        el.style.transform = 'translateY(-2px)';
        el.style.boxShadow = '0 8px 28px rgba(0,0,0,0.3)';
      }}
      onMouseLeave={e => {
        const el = e.currentTarget as HTMLElement;
        el.style.background = 'rgba(255,255,255,0.025)';
        el.style.borderColor = 'rgba(255,255,255,0.07)';
        el.style.transform = 'translateY(0)';
        el.style.boxShadow = 'none';
      }}>

      <div className="flex items-start gap-3 mb-3">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
             style={{ background: isTopjobs ? 'rgba(96,165,250,0.08)' : 'rgba(167,139,250,0.08)',
                      border: isTopjobs ? '1px solid rgba(96,165,250,0.18)' : '1px solid rgba(167,139,250,0.18)' }}>
          <Briefcase size={15} style={{ color: isTopjobs ? '#93c5fd' : '#c4b5fd' }} />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-white leading-tight line-clamp-2
                         group-hover:text-blue-300 transition-colors"
              style={{ fontFamily: "'DM Sans', sans-serif" }}>
            {job.title}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5 truncate">{job.company}</p>
        </div>
      </div>

      <div className="space-y-1.5 mb-4">
        {job.location && (
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <MapPin size={10} /><span className="truncate">{job.location}</span>
          </div>
        )}
        {job.salary && (
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <DollarSign size={10} /><span className="truncate">{job.salary}</span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between pt-3"
           style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <span className="text-xs px-2 py-0.5 rounded-full font-medium"
              style={isTopjobs
                ? { background: 'rgba(96,165,250,0.08)', border: '1px solid rgba(96,165,250,0.18)', color: '#93c5fd' }
                : { background: 'rgba(167,139,250,0.08)', border: '1px solid rgba(167,139,250,0.18)', color: '#c4b5fd' }}>
          {isTopjobs ? 'TopJobs' : 'Rooster'}
        </span>
        <span className="text-xs text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity
                         flex items-center gap-1">
          View <ChevronRight size={11} />
        </span>
      </div>
    </div>
  );
}

export default function Jobs() {
  const [jobs,     setJobs]     = useState<Job[]>([]);
  const [total,    setTotal]    = useState(0);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState('');
  const [search,   setSearch]   = useState('');
  const [source,   setSource]   = useState('');
  const [page,     setPage]     = useState(0);
  const [selected,     setSelected]     = useState<Job | null>(null);
  const [inputVal,     setInputVal]     = useState('');
  const [bookmarkedIds,setBookmarkedIds] = useState<Set<number>>(new Set());

  const totalPages = Math.ceil(total / LIMIT);

  const fetchJobs = useCallback(async (s: string, src: string, p: number) => {
    setLoading(true); setError('');
    try {
      const res = await getJobs({ search: s||undefined, source: src||undefined, limit: LIMIT, offset: p*LIMIT });
      setJobs(res.data.jobs || []);
      setTotal(res.data.total || 0);
    } catch { setError('Failed to load jobs.'); }
    finally  { setLoading(false); }
  }, []);

  useEffect(() => { fetchJobs(search, source, page); }, [search, source, page, fetchJobs]);

  // Load bookmark state
  useEffect(() => {
    api.get('/api/bookmarks/ids').then(r => {
      setBookmarkedIds(new Set(r.data.ids || []));
    }).catch(() => {});
  }, []);

  const toggleBookmark = async (jobId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    const isBookmarked = bookmarkedIds.has(jobId);
    try {
      if (isBookmarked) {
        await api.delete(`/api/bookmarks/${jobId}`);
        setBookmarkedIds(prev => { const s = new Set(prev); s.delete(jobId); return s; });
      } else {
        await api.post(`/api/bookmarks/${jobId}`);
        setBookmarkedIds(prev => new Set(Array.from(prev).concat(jobId)));
      }
    } catch {}
  };

  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); setSearch(inputVal); setPage(0); };
  const clearSearch  = () => { setInputVal(''); setSearch(''); setPage(0); };
  const setSourceFilter = (s: string) => { setSource(s); setPage(0); };

  return (
    <div className="px-10 py-7 w-full animate-fade-in">

      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1"
              style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '-0.02em' }}>
            Browse Jobs
          </h1>
          <p className="text-sm text-slate-400" style={{ fontFamily: "'DM Sans', sans-serif" }}>
            {total.toLocaleString()} jobs · Rooster.jobs &amp; TopJobs.lk
          </p>
        </div>
      </div>

      {/* Search + Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <form onSubmit={handleSearch} className="flex-1 relative">
          <Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
          <input type="text" value={inputVal} onChange={e => setInputVal(e.target.value)}
                 placeholder="Search by job title or company..."
                 className="w-full pl-11 pr-10 py-2.5 text-sm rounded-xl transition-all"
                 style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
                          color: 'white', fontFamily: "'DM Sans', sans-serif" }}
                 onFocus={e => { e.target.style.borderColor = 'rgba(59,130,246,0.5)'; e.target.style.boxShadow = '0 0 0 3px rgba(59,130,246,0.08)'; }}
                 onBlur={e => { e.target.style.borderColor = 'rgba(255,255,255,0.08)'; e.target.style.boxShadow = 'none'; }} />
          {inputVal && (
            <button type="button" onClick={clearSearch}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white">
              <X size={13} />
            </button>
          )}
        </form>

        <div className="flex items-center gap-2">
          <Filter size={13} className="text-slate-500 shrink-0" />
          {[
            { label: 'All',     value: '' },
            { label: 'TopJobs', value: 'topjobs' },
            { label: 'Rooster', value: 'rooster' },
          ].map(f => (
            <button key={f.value} onClick={() => setSourceFilter(f.value)}
              className="px-4 py-2.5 rounded-xl text-sm font-medium transition-all"
              style={source === f.value ? {
                background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(59,130,246,0.3)', color: '#93c5fd',
              } : {
                background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(148,163,184,0.7)',
              }}>
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Active search badge */}
      {search && (
        <div className="flex items-center gap-2 mb-5">
          <span className="text-xs text-slate-500">Results for:</span>
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
                style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)', color: '#93c5fd' }}>
            "{search}"
            <button onClick={clearSearch} className="hover:text-white"><X size={10} /></button>
          </span>
          <span className="text-xs text-slate-500">{total} found</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 px-5 py-4 rounded-2xl mb-6"
             style={{ background: 'rgba(244,63,94,0.07)', border: '1px solid rgba(244,63,94,0.18)' }}>
          <AlertCircle size={16} className="text-rose-400" />
          <p className="text-sm text-rose-300">{error}</p>
        </div>
      )}

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {[...Array(9)].map((_, i) => (
            <div key={i} className="h-40 rounded-2xl skeleton" style={{ animationDelay: `${i*50}ms` }} />
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div className="py-20 text-center">
          <div className="w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center"
               style={{ background: 'rgba(59,130,246,0.07)', border: '1px solid rgba(59,130,246,0.15)' }}>
            <Briefcase size={24} className="text-blue-400" />
          </div>
          <p className="text-slate-300 font-semibold mb-1">No jobs found</p>
          {search && (
            <button onClick={clearSearch}
              className="mt-3 px-4 py-2 rounded-xl text-sm text-slate-400 hover:text-white transition-colors"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
              Clear Search
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {jobs.map(job => (
            <JobCard key={job.id} job={job} onClick={() => setSelected(job)} onBookmark={toggleBookmark} bookmarkedIds={bookmarkedIds} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-between mt-8 pt-6"
             style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <p className="text-sm text-slate-500" style={{ fontFamily: "'DM Sans', sans-serif" }}>
            <span className="text-white font-medium">{page*LIMIT+1}–{Math.min((page+1)*LIMIT, total)}</span>
            {' '}of{' '}
            <span className="text-white font-medium">{total}</span> jobs
          </p>
          <div className="flex items-center gap-2">
            <button onClick={() => setPage(p => Math.max(0, p-1))} disabled={page === 0}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm transition-all disabled:opacity-30"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)', color: '#e2e8f0' }}>
              <ChevronLeft size={14} /> Prev
            </button>
            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const p = Math.max(0, Math.min(totalPages-5, page-2)) + i;
                return (
                  <button key={p} onClick={() => setPage(p)}
                    className="w-8 h-8 rounded-lg text-sm transition-all font-medium"
                    style={p === page ? {
                      background: 'rgba(59,130,246,0.2)', border: '1px solid rgba(59,130,246,0.35)', color: '#93c5fd',
                    } : {
                      background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', color: 'rgba(148,163,184,0.6)',
                    }}>
                    {p+1}
                  </button>
                );
              })}
            </div>
            <button onClick={() => setPage(p => Math.min(totalPages-1, p+1))} disabled={page >= totalPages-1}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm transition-all disabled:opacity-30"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)', color: '#e2e8f0' }}>
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {selected && <JobModal job={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}