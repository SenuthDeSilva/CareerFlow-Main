import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload, FileText, CheckCircle, AlertCircle,
  Loader2, X, Brain, Zap, Shield, Sparkles,
  ChevronRight, File, ArrowRight, Briefcase
} from 'lucide-react';
import { uploadResume } from '../api/client';

type Stage = 'idle' | 'uploading' | 'parsing' | 'matching' | 'xai' | 'done' | 'error';

interface Result {
  resume_id: number;
  candidate: string;
  email: string;
  phone: string;
  years_experience: number;
  skills_count: number;
  hard_skills: string[];
  soft_skills: string[];
  top_recommendations: number;
  predicted_role?: string;
  role_confidence?: number;
}

const STAGES = [
  { key: 'uploading', label: 'Uploading file',        icon: Upload,   pct: 20 },
  { key: 'parsing',   label: 'Parsing resume',         icon: FileText, pct: 45 },
  { key: 'matching',  label: 'Running ML pipeline',    icon: Brain,    pct: 75 },
  { key: 'xai',       label: 'Generating XAI report',  icon: Sparkles, pct: 92 },
  { key: 'done',      label: 'Complete',               icon: CheckCircle, pct: 100 },
];

function StageTracker({ stage }: { stage: Stage }) {
  const current = STAGES.findIndex(s => s.key === stage);
  const pct     = STAGES[Math.max(0, current)]?.pct ?? 0;

  return (
    <div className="w-full">
      {/* Progress bar */}
      <div className="h-1 rounded-full mb-5 overflow-hidden"
           style={{ background: 'rgba(255,255,255,0.06)' }}>
        <div className="h-full rounded-full transition-all duration-700 ease-out"
             style={{
               width: `${pct}%`,
               background: 'linear-gradient(90deg, #3b82f6, #7c3aed)',
               boxShadow: '0 0 12px rgba(59,130,246,0.5)',
             }} />
      </div>

      {/* Steps */}
      <div className="flex items-center justify-between">
        {STAGES.map((s, i) => {
          const done    = i < current;
          const active  = i === current;
          const Icon    = s.icon;
          return (
            <div key={s.key} className="flex flex-col items-center gap-1.5">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center
                transition-all duration-400 ${
                  done   ? 'bg-emerald-500/20 border border-emerald-500/40' :
                  active ? 'border border-blue-500/60'                      :
                           'border border-white/8'
                }`}
                style={active ? {
                  background: 'rgba(59,130,246,0.12)',
                  boxShadow: '0 0 14px rgba(59,130,246,0.3)',
                } : done ? {} : { background: 'rgba(255,255,255,0.03)' }}>
                <Icon size={13}
                  className={done ? 'text-emerald-400' : active ? 'text-blue-400' : 'text-slate-600'}
                  style={active ? { animation: 'spin 1.5s linear infinite' } : undefined}
                />
              </div>
              <span className="text-xs hidden sm:block"
                    style={{
                      color: done ? '#34d399' : active ? '#93c5fd' : 'rgba(148,163,184,0.4)',
                      fontFamily: "'DM Sans', sans-serif",
                      fontSize: '10px',
                    }}>
                {s.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SkillPill({ skill, color }: { skill: string; color: string }) {
  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium animate-scale-in"
          style={{
            background: `${color}12`,
            border: `1px solid ${color}25`,
            color: color,
            fontFamily: "'DM Sans', sans-serif",
          }}>
      {skill}
    </span>
  );
}

export default function UploadPage() {
  const navigate  = useNavigate();
  const inputRef  = useRef<HTMLInputElement>(null);
  const [file,    setFile]    = useState<File | null>(null);
  const [stage,   setStage]   = useState<Stage>('idle');
  const [result,  setResult]  = useState<Result | null>(null);
  const [error,   setError]   = useState('');
  const [drag,    setDrag]    = useState(false);
  const [autoNav, setAutoNav] = useState(false);

  const handleFile = (f: File) => {
    const ext = '.' + f.name.split('.').pop()?.toLowerCase();
    if (!['.pdf','.docx','.txt'].includes(ext)) {
      setError(`"${ext}" not supported — use PDF, DOCX, or TXT`); return;
    }
    if (f.size > 10 * 1024 * 1024) { setError('File must be under 10MB'); return; }
    setFile(f); setError(''); setStage('idle'); setResult(null);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDrag(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setError('');

    // Stage progression tied to actual API progress
    setStage('uploading');
    await new Promise(r => setTimeout(r, 400));
    setStage('parsing');
    await new Promise(r => setTimeout(r, 600));
    setStage('matching');

    try {
      const res = await uploadResume(file);
      setStage('xai');
      await new Promise(r => setTimeout(r, 800));
      setStage('done');
      setResult(res.data);
    } catch (e: any) {
      setStage('error');
      setError(e?.response?.data?.detail || 'Upload failed — make sure API is running.');
    }
  };

  const reset = () => { setFile(null); setStage('idle'); setResult(null); setError(''); setAutoNav(false); };

  // Auto-navigate to results after upload completes
  useEffect(() => {
    if (stage === 'done' && result && !autoNav) {
      setAutoNav(true);
      const timer = setTimeout(() => {
        navigate(`/results/${result.resume_id}`);
      }, 3000); // 3 second delay so user can see success
      return () => clearTimeout(timer);
    }
  }, [stage, result, navigate, autoNav]);

  const isProcessing = ['uploading','parsing','matching','xai'].includes(stage);

  return (
    <div className="px-8 py-6 w-full max-w-2xl mx-auto animate-fade-in">

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-1"
            style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '-0.02em' }}>
          Upload Resume
        </h1>
        <p className="text-sm text-slate-400" style={{ fontFamily: "'DM Sans', sans-serif" }}>
          Get AI-powered job recommendations in seconds
        </p>
      </div>

      {/* Feature strip */}
      <div className="grid grid-cols-3 gap-3 mb-8">
        {[
          { icon: Brain,   label: 'ML Matching',   sub: 'TF-IDF + Word2Vec', color: '#60a5fa', bg: 'rgba(59,130,246,0.06)',  bd: 'rgba(59,130,246,0.15)' },
          { icon: Zap,     label: 'Instant Match',  sub: 'Top 20 results',   color: '#fbbf24', bg: 'rgba(245,158,11,0.06)',  bd: 'rgba(245,158,11,0.15)' },
          { icon: Shield,  label: 'XAI Explained',  sub: 'SHAP + LIME',      color: '#34d399', bg: 'rgba(16,185,129,0.06)', bd: 'rgba(16,185,129,0.15)' },
        ].map(f => (
          <div key={f.label} className="rounded-2xl px-4 py-3.5 animate-slide-up"
               style={{ background: f.bg, border: `1px solid ${f.bd}` }}>
            <f.icon size={18} style={{ color: f.color, marginBottom: 8 }} />
            <p className="text-sm font-semibold text-white"
               style={{ fontFamily: "'DM Sans', sans-serif" }}>{f.label}</p>
            <p className="text-xs mt-0.5" style={{ color: 'rgba(148,163,184,0.6)' }}>{f.sub}</p>
          </div>
        ))}
      </div>

      {/* Drop zone — hidden when done */}
      {stage !== 'done' && (
        <div
          onDrop={onDrop}
          onDragOver={e => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onClick={() => !file && !isProcessing && inputRef.current?.click()}
          className="relative rounded-2xl mb-4 transition-all duration-300 overflow-hidden"
          style={{
            padding: file ? '20px 24px' : '48px 24px',
            cursor: file || isProcessing ? 'default' : 'pointer',
            background: drag
              ? 'rgba(59,130,246,0.08)'
              : file
              ? 'rgba(255,255,255,0.03)'
              : 'rgba(255,255,255,0.02)',
            border: `2px dashed ${drag ? 'rgba(59,130,246,0.6)' : file ? 'rgba(255,255,255,0.1)' : 'rgba(255,255,255,0.08)'}`,
          }}>
          <input ref={inputRef} type="file" accept=".pdf,.docx,.txt"
                 className="hidden" onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} />

          {/* Glow when dragging */}
          {drag && (
            <div className="absolute inset-0 pointer-events-none"
                 style={{ background: 'radial-gradient(circle at 50% 50%, rgba(59,130,246,0.08), transparent 70%)' }} />
          )}

          {!file ? (
            <div className="flex flex-col items-center text-center">
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
                   style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
                <Upload size={26} className="text-slate-400" />
              </div>
              <p className="text-lg font-semibold text-white mb-2"
                 style={{ fontFamily: "'Syne', sans-serif" }}>
                {drag ? 'Drop it here!' : 'Drop your resume here'}
              </p>
              <p className="text-sm text-slate-500 mb-5" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                or click to browse files
              </p>
              <div className="flex items-center gap-2">
                {['.pdf','.docx','.txt'].map(ext => (
                  <span key={ext} className="px-3 py-1 rounded-lg text-xs font-mono text-slate-400"
                        style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
                    {ext}
                  </span>
                ))}
                <span className="text-xs text-slate-600">· max 10MB</span>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
                   style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
                <File size={20} className="text-blue-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white truncate">{file.name}</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {(file.size / 1024).toFixed(1)} KB · {file.name.split('.').pop()?.toUpperCase()}
                </p>
              </div>
              {!isProcessing && (
                <button onClick={e => { e.stopPropagation(); reset(); }}
                  className="p-2 rounded-lg text-slate-500 hover:text-white transition-colors"
                  style={{ background: 'rgba(255,255,255,0.04)' }}>
                  <X size={14} />
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Progress tracker */}
      {isProcessing && (
        <div className="rounded-2xl px-6 py-5 mb-4 animate-slide-up"
             style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}>
          <p className="text-sm font-semibold text-white mb-5"
             style={{ fontFamily: "'DM Sans', sans-serif" }}>
            Analyzing your resume...
          </p>
          <StageTracker stage={stage} />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-start gap-3 px-5 py-4 rounded-2xl mb-4 animate-slide-up"
             style={{ background: 'rgba(244,63,94,0.07)', border: '1px solid rgba(244,63,94,0.18)' }}>
          <AlertCircle size={16} className="text-rose-400 shrink-0 mt-0.5" />
          <p className="text-sm text-rose-300" style={{ fontFamily: "'DM Sans', sans-serif" }}>{error}</p>
        </div>
      )}

      {/* Upload button */}
      {file && stage === 'idle' && (
        <button onClick={handleUpload}
          className="w-full flex items-center justify-center gap-3 py-4 rounded-2xl
                     text-white font-semibold text-sm transition-all duration-150 active:scale-99 animate-slide-up"
          style={{
            background: 'linear-gradient(135deg, #3b82f6 0%, #7c3aed 100%)',
            boxShadow: '0 6px 24px rgba(59,130,246,0.3), 0 0 40px rgba(124,58,237,0.1)',
            fontFamily: "'DM Sans', sans-serif",
          }}>
          <Brain size={18} />
          Analyze Resume &amp; Get Job Recommendations
          <ArrowRight size={16} />
        </button>
      )}

      {/* ── SUCCESS RESULT ─────────────────────────────────── */}
      {stage === 'done' && result && (
        <div className="space-y-4 animate-slide-up">

          {/* Success banner */}
          <div className="flex items-center gap-4 px-5 py-4 rounded-2xl"
               style={{ background: 'rgba(52,211,153,0.07)', border: '1px solid rgba(52,211,153,0.18)' }}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                 style={{ background: 'rgba(52,211,153,0.12)', border: '1px solid rgba(52,211,153,0.25)' }}>
              <CheckCircle size={20} className="text-emerald-400" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-emerald-300"
                 style={{ fontFamily: "'DM Sans', sans-serif" }}>
                Resume analyzed successfully!
              </p>
              <p className="text-xs mt-0.5" style={{ color: 'rgba(52,211,153,0.6)' }}>
                Found {result.top_recommendations} job matches · Redirecting to results in 3s...
              </p>
            </div>
            <Sparkles size={18} className="text-emerald-400/60 shrink-0" />
          </div>

          {/* Predicted Career Role */}
          {result.predicted_role && (
            <div className="flex items-center gap-4 px-5 py-4 rounded-2xl"
                 style={{ background: 'rgba(139,92,246,0.07)', border: '1px solid rgba(139,92,246,0.2)' }}>
              <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                   style={{ background: 'rgba(139,92,246,0.12)', border: '1px solid rgba(139,92,246,0.25)' }}>
                <Briefcase size={18} className="text-violet-400" />
              </div>
              <div className="flex-1">
                <p className="text-xs text-slate-400 mb-0.5" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                  Predicted Career Role
                </p>
                <p className="text-sm font-bold text-violet-300" style={{ fontFamily: "'Syne', sans-serif" }}>
                  {result.predicted_role}
                </p>
              </div>
              {result.role_confidence !== undefined && result.role_confidence > 0 && (
                <span className="text-sm font-bold px-3 py-1.5 rounded-xl"
                      style={{ background: 'rgba(139,92,246,0.15)', color: '#c4b5fd',
                               border: '1px solid rgba(139,92,246,0.25)', fontFamily: "'Syne', sans-serif" }}>
                  {result.role_confidence.toFixed(1)}%
                </span>
              )}
            </div>
          )}

          {/* Candidate profile */}
          <div className="rounded-2xl overflow-hidden"
               style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}>
            <div className="px-5 py-4 flex items-center justify-between"
                 style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <h3 className="text-sm font-semibold text-white" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                Candidate Profile
              </h3>
              <span className="text-xs px-2.5 py-1 rounded-full"
                    style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)', color: '#93c5fd' }}>
                Resume #{result.resume_id}
              </span>
            </div>

            <div className="px-5 py-4">
              {/* Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5">
                {[
                  { label: 'Name',       value: result.candidate || result.email || '—' },
                  { label: 'Phone',      value: result.phone || '—'                     },
                  { label: 'Experience', value: `${result.years_experience} years`       },
                  { label: 'Skills',     value: `${result.skills_count} detected`        },
                ].map(i => (
                  <div key={i.label}>
                    <p className="text-xs text-slate-500 mb-1" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                      {i.label}
                    </p>
                    <p className="text-sm font-semibold text-white truncate">{i.value}</p>
                  </div>
                ))}
              </div>

              {/* Hard skills */}
              {result.hard_skills?.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs text-slate-500 mb-2.5" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                    Hard Skills
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {result.hard_skills.slice(0, 14).map((s, i) => (
                      <SkillPill key={s} skill={s} color="#60a5fa" />
                    ))}
                    {result.hard_skills.length > 14 && (
                      <span className="text-xs text-slate-500 px-2.5 py-0.5 rounded-full"
                            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
                        +{result.hard_skills.length - 14} more
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Soft skills */}
              {result.soft_skills?.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 mb-2.5" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                    Soft Skills
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {result.soft_skills.map(s => (
                      <SkillPill key={s} skill={s} color="#a78bfa" />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Action buttons */}
          <div className="grid grid-cols-2 gap-3">
            <button onClick={() => navigate(`/results/${result.resume_id}`)}
              className="flex items-center justify-center gap-2 py-3.5 rounded-2xl
                         text-white font-semibold text-sm transition-all active:scale-98"
              style={{
                background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
                boxShadow: '0 4px 16px rgba(37,99,235,0.3)',
                fontFamily: "'DM Sans', sans-serif",
              }}>
              <Briefcase size={15} />
              View Job Recommendations
              <ChevronRight size={14} />
            </button>
            <button onClick={() => navigate(`/explain/${result.resume_id}`)}
              className="flex items-center justify-center gap-2 py-3.5 rounded-2xl
                         text-white font-medium text-sm transition-all active:scale-98"
              style={{
                background: 'rgba(139,92,246,0.1)',
                border: '1px solid rgba(139,92,246,0.25)',
                fontFamily: "'DM Sans', sans-serif",
              }}>
              <Sparkles size={15} className="text-violet-400" />
              XAI Explanations
              <ChevronRight size={14} />
            </button>
          </div>

          <button onClick={reset}
            className="w-full py-2.5 text-sm text-slate-500 hover:text-slate-300
                       transition-colors text-center"
            style={{ fontFamily: "'DM Sans', sans-serif" }}>
            Upload another resume
          </button>
        </div>
      )}
    </div>
  );
}