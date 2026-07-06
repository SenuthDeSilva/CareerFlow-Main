import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bookmark, BookmarkX, ExternalLink, MapPin,
  DollarSign, Building2, Trash2, Search,
  AlertCircle, ChevronRight, Filter, X, Briefcase
} from 'lucide-react';
import api from '../api/client';

interface Job {
  id: number; title: string; company: string; location: string;
  salary: string; source: string; job_url: string;
  description: string; bookmarked_at: string;
}

function JobCard({ job, onRemove }: { job: Job; onRemove: () => void }) {
  const isTopjobs = job.source?.toLowerCase() === 'topjobs';
  const [removing, setRemoving] = useState(false);

  const handleRemove = async () => {
    setRemoving(true);
    await onRemove();
  };

  return (
    <div className={`rounded-2xl overflow-hidden transition-all duration-300 ${removing ? 'opacity-0 scale-95' : 'opacity-100'}`}
         style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}
         onMouseEnter={e => {
           (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.12)';
           (e.currentTarget as HTMLElement).style.boxShadow  = '0 8px 28px rgba(0,0,0,0.3)';
         }}
         onMouseLeave={e => {
           (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.07)';
           (e.currentTarget as HTMLElement).style.boxShadow  = 'none';
         }}>

      <div className="p-5">
        {/* Header */}
        <div className="flex items-start gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
               style={{ background: isTopjobs ? 'rgba(96,165,250,0.08)' : 'rgba(167,139,250,0.08)',
                        border:     isTopjobs ? '1px solid rgba(96,165,250,0.18)' : '1px solid rgba(167,139,250,0.18)' }}>
            <Briefcase size={16} style={{ color: isTopjobs ? '#93c5fd' : '#c4b5fd' }} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                    style={isTopjobs
                      ? { background: 'rgba(96,165,250,0.08)', border: '1px solid rgba(96,165,250,0.18)', color: '#93c5fd' }
                      : { background: 'rgba(167,139,250,0.08)', border: '1px solid rgba(167,139,250,0.18)', color: '#c4b5fd' }}>
                {isTopjobs ? 'TopJobs.lk' : 'Rooster.jobs'}
              </span>
            </div>
            <h3 className="font-semibold text-white leading-tight"
                style={{ fontFamily: "'DM Sans', sans-serif" }}>
              {job.title}
            </h3>
            <p className="text-sm text-slate-400 flex items-center gap-1.5 mt-0.5">
              <Building2 size={11} />{job.company}
            </p>
          </div>
          <button onClick={handleRemove}
            className="p-2 rounded-xl text-slate-500 hover:text-rose-400 transition-all shrink-0"
            style={{ background: 'rgba(244,63,94,0.06)', border: '1px solid rgba(244,63,94,0.12)' }}
            title="Remove bookmark">
            <BookmarkX size={15} />
          </button>
        </div>

        {/* Meta */}
        <div className="flex flex-wrap gap-3 mb-4">
          {job.location && (
            <span className="flex items-center gap-1 text-xs text-slate-500">
              <MapPin size={10} />{job.location}
            </span>
          )}
          {job.salary && (
            <span className="flex items-center gap-1 text-xs text-slate-500">
              <DollarSign size={10} />{job.salary}
            </span>
          )}
          <span className="text-xs text-slate-600">
            Saved {new Date(job.bookmarked_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          </span>
        </div>

        {/* Description preview */}
        {job.description && (
          <p className="text-xs text-slate-500 leading-relaxed mb-4 line-clamp-2"
             style={{ fontFamily: "'DM Sans', sans-serif" }}>
            {job.description.slice(0, 140)}...
          </p>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-3" style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          {job.job_url && (
            <a href={job.job_url} target="_blank" rel="noopener noreferrer"
               className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold
                          text-white transition-all active:scale-95"
               style={{ background: 'linear-gradient(135deg,#3b82f6,#2563eb)', boxShadow: '0 4px 12px rgba(37,99,235,0.25)' }}>
              <ExternalLink size={13} /> Apply Now
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Bookmarks() {
  const navigate = useNavigate();
  const [bookmarks, setBookmarks] = useState<Job[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState('');
  const [search,    setSearch]    = useState('');
  const [source,    setSource]    = useState('');
  const [toast,     setToast]     = useState('');

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  const fetchBookmarks = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const r = await api.get('/api/bookmarks');
      setBookmarks(r.data.bookmarks || []);
    } catch { setError('Cannot connect to API.'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchBookmarks(); }, [fetchBookmarks]);

  const removeBookmark = async (jobId: number) => {
    try {
      await api.delete(`/api/bookmarks/${jobId}`);
      setBookmarks(prev => prev.filter(b => b.id !== jobId));
      showToast('Bookmark removed');
    } catch { showToast('Failed to remove bookmark'); }
  };

  const clearAll = async () => {
    try {
      await api.delete('/api/bookmarks');
      setBookmarks([]);
      showToast('All bookmarks cleared');
    } catch { showToast('Failed to clear bookmarks'); }
  };

  const filtered = bookmarks
    .filter(b => !source || b.source?.toLowerCase() === source)
    .filter(b => !search || b.title?.toLowerCase().includes(search.toLowerCase()) ||
                             b.company?.toLowerCase().includes(search.toLowerCase()));

  const roosterCount = bookmarks.filter(b => b.source?.toLowerCase() === 'rooster').length;
  const topjobsCount = bookmarks.filter(b => b.source?.toLowerCase() === 'topjobs').length;

  return (
    <div className="px-10 py-7 w-full animate-fade-in">

      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1"
              style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '-0.025em' }}>
            Saved Jobs
          </h1>
          <p className="text-sm text-slate-400" style={{ fontFamily: "'DM Sans', sans-serif" }}>
            {bookmarks.length} bookmarked · apply whenever you're ready
          </p>
        </div>
        {bookmarks.length > 0 && (
          <button onClick={clearAll}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all active:scale-95"
            style={{ background: 'rgba(244,63,94,0.07)', border: '1px solid rgba(244,63,94,0.18)', color: '#fda4af' }}>
            <Trash2 size={13} /> Clear All
          </button>
        )}
      </div>

      {/* Stats */}
      {!loading && bookmarks.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          {[
            { label: 'Total Saved',  value: bookmarks.length,  color: '#60a5fa', bg: 'rgba(59,130,246,0.06)',  bd: 'rgba(59,130,246,0.15)'  },
            { label: 'Rooster',      value: roosterCount,       color: '#a78bfa', bg: 'rgba(139,92,246,0.06)', bd: 'rgba(139,92,246,0.15)'  },
            { label: 'TopJobs',      value: topjobsCount,       color: '#34d399', bg: 'rgba(16,185,129,0.06)', bd: 'rgba(16,185,129,0.15)'  },
          ].map(s => (
            <div key={s.label} className="rounded-2xl px-5 py-4 animate-slide-up"
                 style={{ background: s.bg, border: `1px solid ${s.bd}` }}>
              <p className="text-xs text-slate-500 mb-1 uppercase tracking-wider"
                 style={{ fontSize: 10, fontFamily: "'DM Sans'" }}>{s.label}</p>
              <p className="text-3xl font-bold" style={{ color: s.color, fontFamily: "'Syne', sans-serif" }}>
                {s.value}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Search + Filter */}
      {bookmarks.length > 0 && (
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="flex-1 relative">
            <Search size={14} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
            <input type="text" value={search} onChange={e => setSearch(e.target.value)}
                   placeholder="Search saved jobs..."
                   className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl"
                   style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
                            color: 'white', fontFamily: "'DM Sans', sans-serif", outline: 'none' }}
                   onFocus={e => { e.target.style.borderColor = 'rgba(59,130,246,0.5)'; }}
                   onBlur={e  => { e.target.style.borderColor = 'rgba(255,255,255,0.08)'; }} />
            {search && (
              <button onClick={() => setSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white">
                <X size={13} />
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Filter size={13} className="text-slate-500 shrink-0" />
            {[
              { label: 'All',     value: '' },
              { label: 'TopJobs', value: 'topjobs' },
              { label: 'Rooster', value: 'rooster' },
            ].map(f => (
              <button key={f.value} onClick={() => setSource(f.value)}
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
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-48 rounded-2xl skeleton" style={{ animationDelay: `${i*60}ms` }} />
          ))}
        </div>
      )}

      {/* Empty */}
      {!loading && bookmarks.length === 0 && (
        <div className="py-24 text-center">
          <div className="w-16 h-16 rounded-2xl mx-auto mb-5 flex items-center justify-center"
               style={{ background: 'rgba(59,130,246,0.07)', border: '1px solid rgba(59,130,246,0.15)' }}>
            <Bookmark size={28} className="text-blue-400" />
          </div>
          <p className="text-lg font-semibold text-white mb-2" style={{ fontFamily: "'Syne', sans-serif" }}>
            No saved jobs yet
          </p>
          <p className="text-sm text-slate-400 mb-6" style={{ fontFamily: "'DM Sans', sans-serif" }}>
            Browse jobs and click the bookmark icon to save them for later
          </p>
          <button onClick={() => navigate('/jobs')}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold
                       text-white transition-all active:scale-95"
            style={{ background: 'linear-gradient(135deg,#3b82f6,#2563eb)', boxShadow: '0 4px 16px rgba(37,99,235,0.28)' }}>
            Browse Jobs <ChevronRight size={15} />
          </button>
        </div>
      )}

      {/* No results after filter */}
      {!loading && bookmarks.length > 0 && filtered.length === 0 && (
        <div className="py-16 text-center">
          <p className="text-slate-400 text-sm mb-3">No bookmarks match your search</p>
          <button onClick={() => { setSearch(''); setSource(''); }}
            className="px-4 py-2 rounded-xl text-sm text-slate-400 hover:text-white transition-colors"
            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
            Clear Filters
          </button>
        </div>
      )}

      {/* Grid */}
      {!loading && filtered.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((job, i) => (
            <div key={job.id} className="animate-slide-up" style={{ animationDelay: `${i * 40}ms` }}>
              <JobCard job={job} onRemove={() => removeBookmark(job.id)} />
            </div>
          ))}
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 animate-slide-up px-5 py-3 rounded-2xl"
             style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.25)',
                      boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }}>
          <p className="text-sm font-medium text-emerald-300" style={{ fontFamily: "'DM Sans', sans-serif" }}>
            {toast}
          </p>
        </div>
      )}
    </div>
  );
}
