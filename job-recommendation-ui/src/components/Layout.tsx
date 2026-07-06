import React, { useState } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Upload, Briefcase, Radio, Database, BarChart3, Bookmark,
  Brain, ChevronRight, ChevronLeft, Zap,
  Activity, Sparkles
} from 'lucide-react';

const NAV = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard',    color: 'blue'    },
  { to: '/upload',    icon: Upload,          label: 'Upload Resume', color: 'violet'  },
  { to: '/jobs',      icon: Briefcase,       label: 'Browse Jobs',   color: 'cyan'    },
  { to: '/scraping',  icon: Radio,           label: 'Job Scraping',  color: 'emerald' },
  { to: '/database',  icon: Database,        label: 'Database',      color: 'amber'   },
  { to: '/analytics', icon: BarChart3,       label: 'Analytics',     color: 'pink'    },
  { to: '/bookmarks', icon: Bookmark,        label: 'Saved Jobs',    color: 'yellow'  },
];

const colorMap: Record<string, string> = {
  blue:    '#60a5fa',
  violet:  '#a78bfa',
  cyan:    '#22d3ee',
  emerald: '#34d399',
  amber:   '#fbbf24',
  pink:    '#f472b6',
  yellow:  '#facc15',
};

function NavItem({ to, icon: Icon, label, color, collapsed }: {
  to: string; icon: any; label: string; color: string; collapsed: boolean;
}) {
  const c = colorMap[color];
  return (
    <NavLink to={to}>
      {({ isActive }) => (
        <div className={`
          group relative flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer
          transition-all duration-200 overflow-hidden mb-0.5
          ${isActive ? 'text-white' : 'text-slate-400 hover:text-white'}
        `}
        style={{
          background: isActive ? 'rgba(255,255,255,0.07)' : 'transparent',
          border: isActive ? '1px solid rgba(255,255,255,0.08)' : '1px solid transparent',
        }}
        onMouseEnter={e => {
          if (!isActive) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)';
        }}
        onMouseLeave={e => {
          if (!isActive) (e.currentTarget as HTMLElement).style.background = 'transparent';
        }}>

          {/* Left accent */}
          {isActive && (
            <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full"
                  style={{ background: c }} />
          )}

          <Icon size={16} className="shrink-0"
                style={{ color: isActive ? c : undefined }} />

          {!collapsed && (
            <>
              <span className="text-sm font-medium flex-1 truncate"
                    style={{ fontFamily: "'DM Sans', sans-serif" }}>
                {label}
              </span>
              {isActive && <ChevronRight size={12} style={{ color: c, opacity: 0.7 }} />}
            </>
          )}
        </div>
      )}
    </NavLink>
  );
}

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const currentPage = NAV.find(n => location.pathname.startsWith(n.to))?.label || 'Dashboard';

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#030712' }}>

      {/* Background glows */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden" style={{ zIndex: 0 }}>
        <div className="absolute -top-48 -left-24 w-96 h-96 rounded-full blur-3xl"
             style={{ background: 'rgba(59,130,246,0.06)' }} />
        <div className="absolute bottom-0 right-0 w-96 h-96 rounded-full blur-3xl"
             style={{ background: 'rgba(139,92,246,0.05)' }} />
      </div>

      {/* Sidebar */}
      <aside className="relative flex flex-col shrink-0 transition-all duration-300"
             style={{
               width: collapsed ? 64 : 232,
               background: 'rgba(3,7,18,0.85)',
               backdropFilter: 'blur(24px)',
               borderRight: '1px solid rgba(255,255,255,0.06)',
               zIndex: 10,
             }}>

        {/* Logo */}
        <div className="flex items-center h-16 px-4 shrink-0"
             style={{
               gap: collapsed ? 0 : 12,
               justifyContent: collapsed ? 'center' : 'flex-start',
               borderBottom: '1px solid rgba(255,255,255,0.05)',
             }}>
          <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
               style={{
                 background: 'linear-gradient(135deg, #3b82f6 0%, #7c3aed 100%)',
                 boxShadow: '0 0 20px rgba(59,130,246,0.35)',
               }}>
            <Brain size={16} className="text-white" />
          </div>

          {!collapsed && (
            <div className="flex-1 min-w-0 animate-fade-in">
              <p className="text-sm font-bold text-white truncate"
                 style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '-0.01em' }}>
                JobMatch AI
              </p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-xs" style={{ color: 'rgba(52,211,153,0.7)' }}>System online</span>
              </div>
            </div>
          )}
        </div>

        {/* Nav items */}
        <nav className="flex-1 py-4 px-2 overflow-y-auto">
          {!collapsed && (
            <p className="text-xs text-slate-600 uppercase tracking-widest px-3 mb-3"
               style={{ fontSize: '10px', letterSpacing: '0.08em' }}>
              Menu
            </p>
          )}
          {NAV.map(item => (
            <NavItem key={item.to} {...item} collapsed={collapsed} />
          ))}
        </nav>

        {/* ML Info + Collapse */}
        <div className="px-2 pb-4 shrink-0"
             style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 12 }}>
          {!collapsed && (
            <div className="px-3 py-2.5 rounded-xl mb-3 animate-fade-in"
                 style={{
                   background: 'rgba(59,130,246,0.06)',
                   border: '1px solid rgba(59,130,246,0.12)',
                 }}>
              <div className="flex items-center gap-2 mb-1">
                <Zap size={12} className="text-blue-400" />
                <span className="text-xs font-semibold text-white">ML Pipeline</span>
                <Sparkles size={11} style={{ color: 'rgba(147,197,253,0.5)', marginLeft: 'auto' }} />
              </div>
              <p className="text-xs" style={{ color: 'rgba(148,163,184,0.6)', lineHeight: 1.5 }}>
                TF-IDF · Word2Vec · Skill Gap · Random Forest
              </p>
            </div>
          )}

          <button
            onClick={() => setCollapsed(!collapsed)}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl
                       text-slate-600 hover:text-slate-300 transition-all duration-150"
            style={{ fontSize: 13 }}
            onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)'}
            onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = 'transparent'}
          >
            {collapsed ? <ChevronRight size={14} /> : <><ChevronLeft size={14} /><span style={{ fontSize: 12 }}>Collapse</span></>}
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden" style={{ zIndex: 1 }}>

        {/* Topbar */}
        <header className="shrink-0 h-16 flex items-center justify-between px-6"
                style={{
                  background: 'rgba(3,7,18,0.7)',
                  backdropFilter: 'blur(16px)',
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                }}>
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-600">JobMatch AI</span>
            <ChevronRight size={12} className="text-slate-700" />
            <span className="text-sm font-semibold text-white"
                  style={{ fontFamily: "'DM Sans', sans-serif" }}>
              {currentPage}
            </span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
               style={{
                 background: 'rgba(52,211,153,0.06)',
                 border: '1px solid rgba(52,211,153,0.12)',
               }}>
            <Activity size={12} className="text-emerald-400" />
            <span className="text-xs text-emerald-400/70">API Connected</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          </div>
        </header>

        <main className="flex-1 overflow-y-auto w-full">
          <Outlet />
        </main>
      </div>
    </div>
  );
}