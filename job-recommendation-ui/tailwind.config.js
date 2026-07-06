/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        dark: {
          950: '#00010a',
          900: '#030712',
          800: '#0a0f1e',
          700: '#0f172a',
          600: '#1e293b',
          500: '#334155',
        },
        brand: {
          50:  '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        glow: {
          blue:   'rgba(59,130,246,0.5)',
          violet: 'rgba(139,92,246,0.5)',
          cyan:   'rgba(34,211,238,0.5)',
          green:  'rgba(16,185,129,0.5)',
        }
      },
      fontFamily: {
        sans:    ['"Syne"', 'system-ui', 'sans-serif'],
        body:    ['"DM Sans"', 'system-ui', 'sans-serif'],
        mono:    ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'glass':         '0 4px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06)',
        'glass-hover':   '0 8px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.1)',
        'glow-blue':     '0 0 24px rgba(59,130,246,0.25), 0 0 48px rgba(59,130,246,0.1)',
        'glow-violet':   '0 0 24px rgba(139,92,246,0.25)',
        'glow-emerald':  '0 0 24px rgba(16,185,129,0.25)',
        'inner-glow':    'inset 0 1px 0 rgba(255,255,255,0.08)',
      },
      backgroundImage: {
        'mesh':          'radial-gradient(at 40% 20%, rgba(59,130,246,0.08) 0px, transparent 60%), radial-gradient(at 90% 80%, rgba(139,92,246,0.06) 0px, transparent 50%), radial-gradient(at 10% 90%, rgba(34,211,238,0.05) 0px, transparent 50%)',
        'glass-gradient':'linear-gradient(135deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%)',
        'card-shine':    'linear-gradient(135deg, rgba(255,255,255,0.05) 0%, transparent 60%)',
        'shimmer':       'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.05) 50%, transparent 100%)',
      },
      animation: {
        'fade-in':       'fadeIn 0.4s ease-out both',
        'slide-up':      'slideUp 0.5s cubic-bezier(0.16,1,0.3,1) both',
        'slide-in-left': 'slideInLeft 0.4s cubic-bezier(0.16,1,0.3,1) both',
        'scale-in':      'scaleIn 0.3s cubic-bezier(0.16,1,0.3,1) both',
        'shimmer':       'shimmer 2.5s linear infinite',
        'pulse-glow':    'pulseGlow 3s ease-in-out infinite',
        'float':         'float 6s ease-in-out infinite',
        'spin-slow':     'spin 8s linear infinite',
      },
      keyframes: {
        fadeIn:      { from: { opacity: '0' },                              to: { opacity: '1' } },
        slideUp:     { from: { opacity: '0', transform: 'translateY(20px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        slideInLeft: { from: { opacity: '0', transform: 'translateX(-20px)' }, to: { opacity: '1', transform: 'translateX(0)' } },
        scaleIn:     { from: { opacity: '0', transform: 'scale(0.95)' },    to: { opacity: '1', transform: 'scale(1)' } },
        shimmer:     { from: { backgroundPosition: '-200% 0' },             to: { backgroundPosition: '200% 0' } },
        pulseGlow:   { '0%,100%': { opacity: '0.6' },                       '50%': { opacity: '1' } },
        float:       { '0%,100%': { transform: 'translateY(0)' },           '50%': { transform: 'translateY(-8px)' } },
      },
    },
  },
  plugins: [],
}