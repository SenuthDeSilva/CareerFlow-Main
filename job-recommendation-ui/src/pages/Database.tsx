import React, { useEffect, useState, useCallback } from 'react';
import {
  Database, Trash2, RefreshCw, AlertTriangle,
  CheckCircle, XCircle, Server, FileText, Briefcase,
  Users, BarChart3, Shield, ChevronRight, AlertCircle,
  HardDrive, Clock, Zap, ArrowUpRight
} from 'lucide-react';
import api from '../api/client';

// ── Types ─────────────────────────────────────────────────
interface DBOverview {
  jobs:            { total: number; rooster: number; topjobs: number; last_scraped: string|null };
  resumes:         { total: number; last_uploaded: string|null };
  recommendations: { total: number; last_created: string|null };
  database:        { size: string; name: string };
}

interface Resume { id: number; candidate_name: string; email: string; skills_count: number; years_experience: number; uploaded_at: string; }
type Tab = 'overview' | 'jobs' | 'resumes' | 'recommendations' | 'danger';

// ── Confirm Dialog ──────────────────────────────────────
function ConfirmDialog({ message, onConfirm, onCancel, dangerous = false }: {
  message: string; onConfirm: () => void; onCancel: () => void; dangerous?: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
         style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)' }}>
      <div className="w-full max-w-md rounded-2xl p-6 animate-scale-in"
           style={{ background: 'rgba(10,15,30,0.98)', border: '1px solid rgba(255,255,255,0.1)' }}>
        <div className="flex items-start gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
               style={{ background: dangerous ? 'rgba(244,63,94,0.1)' : 'rgba(245,158,11,0.1)',
                        border: dangerous ? '1px solid rgba(244,63,94,0.25)' : '1px solid rgba(245,158,11,0.25)' }}>
            <AlertTriangle size={18} style={{ color: dangerous ? '#f87171' : '#fbbf24' }} />
          </div>
          <div>
            <h3 className="font-semibold text-white mb-1" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              Confirm Action
            </h3>
            <p className="text-sm text-slate-400" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              {message}
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <button onClick={onCancel}
            className="flex-1 py-2.5 rounded-xl text-sm font-medium text-slate-400 transition-all"
            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
            Cancel
          </button>
          <button onClick={onConfirm}
            className="flex-1 py-2.5 rounded-xl text-sm font-semibold text-white transition-all active:scale-95"
            style={{ background: dangerous ? 'linear-gradient(135deg,#dc2626,#b91c1c)' : 'linear-gradient(135deg,#d97706,#b45309)',
                     boxShadow: dangerous ? '0 4px 16px rgba(220,38,38,0.3)' : '0 4px 16px rgba(217,119,6,0.3)' }}>
            {dangerous ? 'Yes, Delete' : 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Toast ──────────────────────────────────────────────
function Toast({ msg, type }: { msg: string; type: 'success'|'error' }) {
  return (
    <div className="fixed bottom-6 right-6 z-50 animate-slide-up flex items-center gap-3 px-5 py-3.5 rounded-2xl"
         style={type === 'success'
           ? { background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.25)', boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }
           : { background: 'rgba(244,63,94,0.1)',  border: '1px solid rgba(244,63,94,0.25)',  boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }}>
      {type === 'success'
        ? <CheckCircle size={16} className="text-emerald-400 shrink-0" />
        : <XCircle    size={16} className="text-rose-400 shrink-0" />}
      <p className="text-sm font-medium" style={{ color: type === 'success' ? '#6ee7b7' : '#fda4af', fontFamily: "'DM Sans', sans-serif" }}>
        {msg}
      </p>
    </div>
  );
}

// ── Stat Card ──────────────────────────────────────────
function DBStatCard({ icon: Icon, label, value, sub, color, bg, border }: {
  icon: any; label: string; value: string|number; sub?: string;
  color: string; bg: string; border: string;
}) {
  return (
    <div className="rounded-2xl p-5" style={{ background: bg, border: `1px solid ${border}` }}>
      <div className="flex items-center gap-2 mb-3">
        <Icon size={15} style={{ color }} />
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider"
              style={{ fontSize: 10, fontFamily: "'DM Sans', sans-serif" }}>{label}</span>
      </div>
      <p className="text-3xl font-bold text-white" style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '-0.02em' }}>
        {value}
      </p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  );
}

// ── Action Button ──────────────────────────────────────
function ActionBtn({ icon: Icon, label, sub, onClick, variant = 'default' }: {
  icon: any; label: string; sub?: string; onClick: () => void;
  variant?: 'default'|'danger'|'warning'|'success';
}) {
  const styles = {
    default: { bg: 'rgba(255,255,255,0.04)', bd: 'rgba(255,255,255,0.08)', color: '#e2e8f0' },
    danger:  { bg: 'rgba(244,63,94,0.07)',   bd: 'rgba(244,63,94,0.2)',    color: '#fda4af' },
    warning: { bg: 'rgba(245,158,11,0.07)',  bd: 'rgba(245,158,11,0.2)',   color: '#fcd34d' },
    success: { bg: 'rgba(52,211,153,0.07)',  bd: 'rgba(52,211,153,0.2)',   color: '#6ee7b7' },
  };
  const s = styles[variant];
  return (
    <button onClick={onClick}
      className="w-full flex items-center justify-between px-4 py-3.5 rounded-xl transition-all active:scale-98 group"
      style={{ background: s.bg, border: `1px solid ${s.bd}` }}
      onMouseEnter={e => (e.currentTarget as HTMLElement).style.opacity = '0.85'}
      onMouseLeave={e => (e.currentTarget as HTMLElement).style.opacity = '1'}>
      <div className="flex items-center gap-3">
        <Icon size={16} style={{ color: s.color }} />
        <div className="text-left">
          <p className="text-sm font-medium text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>{label}</p>
          {sub && <p className="text-xs mt-0.5" style={{ color: 'rgba(148,163,184,0.5)' }}>{sub}</p>}
        </div>
      </div>
      <ChevronRight size={14} style={{ color: s.color, opacity: 0.6 }} />
    </button>
  );
}

// ── Resume Table Row ───────────────────────────────────
function ResumeRow({ resume, onDelete, onClearRecs }: {
  resume: Resume; onDelete: () => void; onClearRecs: () => void;
}) {
  const initials = (resume.candidate_name || resume.email || '?')[0].toUpperCase();
  return (
    <div className="flex items-center gap-4 px-5 py-3.5 transition-all"
         style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
         onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)'}
         onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = 'transparent'}>
      <div className="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold shrink-0"
           style={{ background: 'rgba(139,92,246,0.12)', border: '1px solid rgba(139,92,246,0.2)', color: '#c4b5fd',
                    fontFamily: "'Syne', sans-serif" }}>
        {initials}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white truncate"
           style={{ fontFamily: "'DM Sans', sans-serif" }}>
          {resume.candidate_name || resume.email || 'Unknown'}
        </p>
        <p className="text-xs text-slate-500">
          {resume.skills_count} skills · {resume.years_experience}yr ·{' '}
          {new Date(resume.uploaded_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <button onClick={onClearRecs}
          className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
          style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.18)', color: '#fcd34d' }}>
          Clear Recs
        </button>
        <button onClick={onDelete}
          className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 transition-colors"
          style={{ background: 'rgba(244,63,94,0.06)', border: '1px solid rgba(244,63,94,0.12)' }}>
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────
export default function DatabasePage() {
  const [tab,       setTab]       = useState<Tab>('overview');
  const [overview,  setOverview]  = useState<DBOverview|null>(null);
  const [resumes,   setResumes]   = useState<Resume[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [confirm,   setConfirm]   = useState<{ msg: string; fn: () => void; dangerous?: boolean }|null>(null);
  const [toast,     setToast]     = useState<{ msg: string; type: 'success'|'error' }|null>(null);
  const [resLoading,setResLoading]= useState(false);

  const showToast = (msg: string, type: 'success'|'error' = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const ask = (msg: string, fn: () => void, dangerous = false) =>
    setConfirm({ msg, fn, dangerous });

  const run = async (fn: () => Promise<any>, successMsg?: string) => {
    try {
      const r = await fn();
      showToast(successMsg || r.data?.message || 'Done!', 'success');
      fetchOverview();
      if (tab === 'resumes') fetchResumes();
    } catch (e: any) {
      showToast(e?.response?.data?.detail || 'Operation failed', 'error');
    }
  };

  const fetchOverview = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get('/api/db/overview');
      setOverview(r.data.overview);
    } catch { showToast('Cannot connect to API', 'error'); }
    finally { setLoading(false); }
  }, []);

  const fetchResumes = async () => {
    setResLoading(true);
    try {
      const r = await api.get('/api/resumes');
      setResumes(r.data.resumes || []);
    } catch {}
    finally { setResLoading(false); }
  };

  useEffect(() => { fetchOverview(); }, [fetchOverview]);
  useEffect(() => { if (tab === 'resumes') fetchResumes(); }, [tab]);

  const fmt = (dt: string|null) => {
    if (!dt) return 'Never';
    try { return new Date(dt).toLocaleString('en-US', { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' }); }
    catch { return dt; }
  };

  const TABS: { key: Tab; label: string; icon: any; color: string }[] = [
    { key: 'overview',        label: 'Overview',         icon: BarChart3,    color: '#60a5fa' },
    { key: 'jobs',            label: 'Jobs',             icon: Briefcase,    color: '#a78bfa' },
    { key: 'resumes',         label: 'Resumes',          icon: FileText,     color: '#34d399' },
    { key: 'recommendations', label: 'Recommendations',  icon: Users,        color: '#fbbf24' },
    { key: 'danger',          label: 'Danger Zone',      icon: AlertTriangle,color: '#f87171' },
  ];

  return (
    <div className="px-10 py-7 w-full animate-fade-in">

      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1"
              style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '-0.025em' }}>
            Database Manager
          </h1>
          <p className="text-sm text-slate-400" style={{ fontFamily: "'DM Sans', sans-serif" }}>
            Manage jobs, resumes, recommendations · PostgreSQL
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={fetchOverview}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-white transition-all active:scale-95"
            style={{ background: 'rgba(59,130,246,0.12)', border: '1px solid rgba(59,130,246,0.2)' }}>
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-8 p-1 rounded-2xl w-fit"
           style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all"
            style={tab === t.key ? {
              background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.1)',
              color: t.color,
            } : { color: 'rgba(148,163,184,0.6)', border: '1px solid transparent' }}>
            <t.icon size={14} />
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Overview ─────────────────────────────────── */}
      {tab === 'overview' && (
        <div className="space-y-6">
          {loading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
              {[...Array(4)].map((_, i) => <div key={i} className="h-28 rounded-2xl skeleton" />)}
            </div>
          ) : overview ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
                <DBStatCard icon={Briefcase}  label="Total Jobs"      value={overview.jobs.total}            sub={`Last: ${fmt(overview.jobs.last_scraped)}`}              color="#60a5fa" bg="rgba(59,130,246,0.06)"   border="rgba(59,130,246,0.15)"  />
                <DBStatCard icon={FileText}   label="Resumes"         value={overview.resumes.total}         sub={`Last: ${fmt(overview.resumes.last_uploaded)}`}          color="#a78bfa" bg="rgba(139,92,246,0.06)"  border="rgba(139,92,246,0.15)"  />
                <DBStatCard icon={Users}      label="Recommendations" value={overview.recommendations.total} sub={`Last: ${fmt(overview.recommendations.last_created)}`}   color="#34d399" bg="rgba(16,185,129,0.06)"  border="rgba(16,185,129,0.15)"  />
                <DBStatCard icon={HardDrive}  label="DB Size"         value={overview.database.size}         sub={overview.database.name}                                  color="#fbbf24" bg="rgba(245,158,11,0.06)"  border="rgba(245,158,11,0.15)"  />
              </div>

              {/* Source breakdown */}
              <div className="rounded-2xl p-5"
                   style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}>
                <div className="flex items-center gap-2 mb-5">
                  <Server size={14} className="text-blue-400" />
                  <h2 className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                    Source Breakdown
                  </h2>
                </div>
                <div className="grid grid-cols-2 gap-5">
                  {[
                    { label: 'Rooster.jobs', value: overview.jobs.rooster, total: overview.jobs.total, color: '#a78bfa' },
                    { label: 'TopJobs.lk',   value: overview.jobs.topjobs, total: overview.jobs.total, color: '#60a5fa' },
                  ].map(s => {
                    const pct = s.total > 0 ? Math.round((s.value / s.total) * 100) : 0;
                    return (
                      <div key={s.label}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="flex items-center gap-2 text-sm text-slate-300">
                            <span className="w-2 h-2 rounded-full" style={{ background: s.color }} />
                            {s.label}
                          </span>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-white"
                                  style={{ fontFamily: "'Syne', sans-serif" }}>{s.value}</span>
                            <span className="text-xs text-slate-500">{pct}%</span>
                          </div>
                        </div>
                        <div className="h-2 rounded-full overflow-hidden"
                             style={{ background: 'rgba(255,255,255,0.05)' }}>
                          <div className="h-full rounded-full transition-all duration-700"
                               style={{ width: `${pct}%`, background: s.color, boxShadow: `0 0 8px ${s.color}50` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>


            </>
          ) : null}
        </div>
      )}

      {/* ── Jobs ─────────────────────────────────────── */}
      {tab === 'jobs' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="rounded-2xl p-5"
               style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}>
            <div className="flex items-center gap-2 mb-4">
              <Briefcase size={14} className="text-blue-400" />
              <h2 className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                Jobs Management
              </h2>
            </div>
            <div className="space-y-2.5">
              <ActionBtn icon={Trash2} label="Delete Rooster Jobs" sub={`${overview?.jobs.rooster || 0} jobs`}
                variant="warning"
                onClick={() => ask(`Delete all ${overview?.jobs.rooster || 0} Rooster.jobs entries?`,
                  () => run(() => api.delete('/api/db/jobs/source/rooster')))} />
              <ActionBtn icon={Trash2} label="Delete TopJobs" sub={`${overview?.jobs.topjobs || 0} jobs`}
                variant="warning"
                onClick={() => ask(`Delete all ${overview?.jobs.topjobs || 0} TopJobs.lk entries?`,
                  () => run(() => api.delete('/api/db/jobs/source/topjobs')))} />
              <ActionBtn icon={Zap} label="Remove Duplicate Jobs" sub="Keep latest per URL"
                variant="default"
                onClick={() => ask('Remove all duplicate jobs (keeping latest per URL)?',
                  () => run(() => api.delete('/api/db/jobs/duplicates')))} />
              <ActionBtn icon={Trash2} label="Delete ALL Jobs" sub={`${overview?.jobs.total || 0} total jobs`}
                variant="danger"
                onClick={() => ask(`Delete ALL ${overview?.jobs.total || 0} jobs? This cannot be undone.`,
                  () => run(() => api.delete('/api/db/jobs/all')), true)} />
            </div>
          </div>


        </div>
      )}

      {/* ── Resumes ───────────────────────────────────── */}
      {tab === 'resumes' && (
        <div className="space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-sm text-slate-400" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                {resumes.length} resumes in database
              </span>
            </div>
            <div className="flex gap-2">

              <button onClick={() => ask(`Delete ALL ${resumes.length} resumes and their recommendations?`,
                () => run(() => api.delete('/api/db/resumes/all')), true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm transition-all active:scale-95"
                style={{ background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.18)', color: '#fda4af' }}>
                <Trash2 size={13} /> Delete All
              </button>
            </div>
          </div>

          <div className="rounded-2xl overflow-hidden"
               style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}>
            {resLoading ? (
              <div className="p-5 space-y-3">
                {[...Array(3)].map((_, i) => <div key={i} className="h-14 rounded-xl skeleton" />)}
              </div>
            ) : resumes.length === 0 ? (
              <div className="py-14 text-center">
                <FileText size={28} className="text-slate-700 mx-auto mb-3" />
                <p className="text-slate-500 text-sm">No resumes in database</p>
              </div>
            ) : resumes.map(r => (
              <ResumeRow key={r.id} resume={r}
                onDelete={() => ask(`Delete resume for ${r.candidate_name || r.email}?`,
                  () => run(() => api.delete(`/api/db/resume/${r.id}`)), true)}
                onClearRecs={() => ask(`Clear all recommendations for ${r.candidate_name || r.email}?`,
                  () => run(() => api.delete(`/api/db/recommendations/resume/${r.id}`)))}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── Recommendations ───────────────────────────── */}
      {tab === 'recommendations' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="rounded-2xl p-5"
               style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}>
            <div className="flex items-center gap-2 mb-1">
              <Users size={14} className="text-amber-400" />
              <h2 className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                Recommendations
              </h2>
            </div>
            <p className="text-xs text-slate-500 mb-5" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              {overview?.recommendations.total || 0} total · last: {fmt(overview?.recommendations.last_created || null)}
            </p>
            <div className="space-y-2.5">
              <ActionBtn icon={Trash2} label="Clear All Recommendations" sub="Keeps resumes and jobs intact"
                variant="warning"
                onClick={() => ask(`Delete all ${overview?.recommendations.total || 0} recommendations? Jobs and resumes are preserved.`,
                  () => run(() => api.delete('/api/db/recommendations/all')))} />
            </div>
          </div>

          <div className="rounded-2xl p-5"
               style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}>
            <div className="flex items-center gap-2 mb-4">
              <AlertCircle size={14} className="text-blue-400" />
              <h2 className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                About Recommendations
              </h2>
            </div>
            <div className="space-y-3 text-xs text-slate-400" style={{ fontFamily: "'DM Sans', sans-serif", lineHeight: 1.7 }}>
              <p>Recommendations are generated by the ML pipeline when a resume is uploaded.</p>
              <p>Clearing recommendations does <span className="text-white">not</span> delete resumes or jobs — you can re-run ML matching by uploading the resume again.</p>
              <p>Each resume gets <span className="text-amber-300">top 20 recommendations</span> (10 Rooster + 10 TopJobs).</p>
            </div>
          </div>
        </div>
      )}

      {/* ── Danger Zone ───────────────────────────────── */}
      {tab === 'danger' && (
        <div className="max-w-2xl space-y-5">
          <div className="flex items-start gap-3 px-5 py-4 rounded-2xl"
               style={{ background: 'rgba(244,63,94,0.06)', border: '1px solid rgba(244,63,94,0.2)' }}>
            <AlertTriangle size={16} className="text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-300" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              Actions in this zone are <strong>irreversible</strong>. All data will be permanently deleted.
              Make sure to export any data you need before proceeding.
            </p>
          </div>

          <div className="rounded-2xl p-5"
               style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(244,63,94,0.15)' }}>
            <div className="flex items-center gap-2 mb-5">
              <Shield size={14} className="text-rose-400" />
              <h2 className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                Destructive Actions
              </h2>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between px-4 py-4 rounded-xl"
                   style={{ background: 'rgba(244,63,94,0.06)', border: '1px solid rgba(244,63,94,0.15)' }}>
                <div>
                  <p className="text-sm font-medium text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                    Reset Entire Database
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Deletes ALL jobs ({overview?.jobs.total || 0}), resumes ({overview?.resumes.total || 0}), and recommendations ({overview?.recommendations.total || 0})
                  </p>
                </div>
                <button
                  onClick={() => ask(
                    `RESET ENTIRE DATABASE? This will permanently delete ALL ${overview?.jobs.total || 0} jobs, ${overview?.resumes.total || 0} resumes, and all recommendations. This CANNOT be undone.`,
                    () => run(() => api.delete('/api/db/reset')),
                    true
                  )}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white
                             transition-all active:scale-95 shrink-0 ml-4"
                  style={{ background: 'linear-gradient(135deg,#dc2626,#b91c1c)', boxShadow: '0 4px 16px rgba(220,38,38,0.3)' }}>
                  <Trash2 size={14} /> Reset DB
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Confirm dialog */}
      {confirm && (
        <ConfirmDialog
          message={confirm.msg}
          dangerous={confirm.dangerous}
          onConfirm={() => { confirm.fn(); setConfirm(null); }}
          onCancel={() => setConfirm(null)}
        />
      )}

      {/* Toast */}
      {toast && <Toast msg={toast.msg} type={toast.type} />}
    </div>
  );
}
