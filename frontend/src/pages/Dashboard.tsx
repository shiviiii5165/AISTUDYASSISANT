import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { Search, BookOpen, Loader2, ArrowRight, FileText, MessageSquare, Sparkles, TrendingUp } from 'lucide-react';
import { fetchPdfs } from '../lib/api';
import type { PDFDocument } from '../lib/api';
import { useAuthStore } from '../store/useAuthStore';
import GenieAvatar from '../components/GenieAvatar';

const SUBJECT_COLORS: Record<string, { bg: string; text: string }> = {
  Physics: { bg: 'bg-blue-50', text: 'text-blue-600' },
  Chemistry: { bg: 'bg-indigo-50', text: 'text-indigo-600' },
  Biology: { bg: 'bg-emerald-50', text: 'text-emerald-600' },
  Maths: { bg: 'bg-purple-50', text: 'text-purple-600' },
  English: { bg: 'bg-amber-50', text: 'text-amber-600' },
  History: { bg: 'bg-rose-50', text: 'text-rose-600' },
  'Computer Science': { bg: 'bg-cyan-50', text: 'text-cyan-600' },
  Economics: { bg: 'bg-orange-50', text: 'text-orange-600' },
  General: { bg: 'bg-gray-50', text: 'text-gray-600' },
};

const Dashboard: React.FC = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [pdfs, setPdfs] = useState<PDFDocument[]>([]);
  const [loadingPdfs, setLoadingPdfs] = useState(true);
  const [quickAsk, setQuickAsk] = useState('');
  const [placeholderIndex, setPlaceholderIndex] = useState(0);

  const placeholders = [
    "Ask a doubt from any PDF...",
    "What is Newton's third law?",
    "Explain mitochondria simply...",
    "Generate 5 MCQs on this chapter..."
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setPlaceholderIndex((prev) => (prev + 1) % placeholders.length);
    }, 4000);
    return () => clearInterval(interval);
  }, [placeholders.length]);

  useEffect(() => {
    (async () => {
      try {
        const data = await fetchPdfs();
        setPdfs(data);
      } catch (err) {
        console.error('Error loading PDFs:', err);
      } finally {
        setLoadingPdfs(false);
      }
    })();
  }, []);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  const firstName = user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || 'Student';
  const readyPdfs = pdfs.filter(p => p.status === 'ready');
  const recentPdfs = pdfs.slice(0, 4);
  const totalPages = pdfs.reduce((sum, p) => sum + (p.page_count || 0), 0);

  const handleQuickAsk = () => {
    if (quickAsk.trim() && readyPdfs.length > 0) {
      navigate(`/chat?pdf=${readyPdfs[0].id}`);
    } else if (readyPdfs.length === 0) {
      navigate('/library');
    }
  };

  const STATS = [
    {
      label: 'PDFs Uploaded',
      value: pdfs.length,
      icon: <FileText className="w-4 h-4 text-[var(--accent-indigo)]" />,
      iconBg: 'bg-indigo-50',
    },
    {
      label: 'Total Pages',
      value: totalPages,
      icon: <BookOpen className="w-4 h-4 text-[var(--accent-green)]" />,
      iconBg: 'bg-green-50',
    },
    {
      label: 'Ready to Chat',
      value: readyPdfs.length,
      icon: <TrendingUp className="w-4 h-4 text-purple-600" />,
      iconBg: 'bg-purple-50',
    },
    {
      label: 'Study Streak',
      value: '1 day',
      icon: <span className="text-sm">🔥</span>,
      iconBg: 'bg-amber-50',
      isStreak: true,
    },
  ];

  return (
    <AppLayout title={<span className="font-semibold">Dashboard</span>}>
      <SEO 
        title="Dashboard" 
        description="View your learning progress, recent uploads, and AI study sessions on TeachGenie." 
      />
      <div className="p-4 md:p-6 lg:p-8 max-w-5xl mx-auto space-y-10">
        
        {/* Hero Section */}
        <div className="flex flex-col items-center justify-center text-center space-y-4 pt-4 pb-2">
          <GenieAvatar size="lg" />
          <h1 className="text-4xl md:text-5xl tracking-tight mt-2 animate-slideUp" style={{ animationDelay: '0.1s' }}>
            {getGreeting()}, <span className="text-gold-shimmer font-bold">{firstName}</span>.
          </h1>
          <p className="text-[var(--text-secondary)] text-lg animate-slideUp" style={{ animationDelay: '0.2s' }}>
            What would you like to teach today?
          </p>
        </div>

        {/* Quick Ask */}
        <div className="relative group animate-slideUp" style={{ animationDelay: '0.3s' }}>
          <div className="absolute -inset-0.5 bg-gradient-to-r from-[var(--accent-green)] to-[var(--accent-indigo)] rounded-2xl opacity-20 group-hover:opacity-40 group-focus-within:opacity-100 group-focus-within:animate-[borderGlow_3s_infinite] transition-all blur-sm" />
          <div className="relative card-storybook p-2 flex items-center gap-2 rounded-xl">
            <div className="pl-4">
              <Search className="w-5 h-5 text-[var(--accent-amber)]" />
            </div>
            <input
              type="text"
              value={quickAsk}
              onChange={(e) => setQuickAsk(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleQuickAsk()}
              placeholder={readyPdfs.length > 0 ? placeholders[placeholderIndex] : "Upload a PDF first to start asking..."}
              className="flex-1 bg-transparent border-none focus:outline-none text-[var(--text-primary)] py-3 px-2 placeholder:text-[var(--text-muted)] text-base min-w-0 transition-all"
              style={{ animation: readyPdfs.length > 0 && !quickAsk ? 'placeholderFade 4s infinite' : 'none' }}
              disabled={readyPdfs.length === 0}
            />
            <button
              onClick={handleQuickAsk}
              className="btn-gold px-6 py-3 rounded-lg flex items-center gap-2 text-sm shadow-sm shrink-0"
            >
              <Sparkles className="w-4 h-4" />
              <span className="hidden sm:inline">Ask Genie</span>
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-slideUp" style={{ animationDelay: '0.4s' }}>
          {STATS.map((stat, i) => (
            <div key={stat.label} className="card-storybook p-5 flex flex-col justify-between" style={{ animationDelay: `${0.4 + i*0.1}s` }}>
              <div className={`w-8 h-8 ${stat.iconBg} rounded-lg flex items-center justify-center mb-3`}>
                {stat.icon}
              </div>
              <p className="text-[var(--text-muted)] text-[11px] font-bold uppercase tracking-widest mb-1">{stat.label}</p>
              {loadingPdfs && !stat.isStreak ? (
                <Loader2 className="w-4 h-4 animate-spin text-[var(--text-muted)]" />
              ) : (
                <p className="text-3xl font-bold text-[var(--text-primary)] tracking-tight">{stat.value}</p>
              )}
            </div>
          ))}
        </div>
        
        {/* Recent PDFs */}
        <div className="animate-slideUp" style={{ animationDelay: '0.6s' }}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-base font-bold text-[var(--text-primary)]">Recent PDFs</h3>
            <button
              onClick={() => navigate('/library')}
              className="text-[var(--accent-indigo)] text-xs font-semibold hover:underline flex items-center gap-1"
            >
              View all <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {loadingPdfs ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="w-5 h-5 animate-spin text-[var(--accent-green)]" />
            </div>
          ) : recentPdfs.length === 0 ? (
            <div className="text-center py-12 card-storybook">
              <div className="w-14 h-14 bg-[var(--bg-secondary)] rounded-2xl flex items-center justify-center mx-auto mb-4 border border-[var(--border)] shadow-inner">
                <BookOpen className="w-6 h-6 text-[var(--accent-amber)]" />
              </div>
              <p className="text-[var(--text-primary)] font-bold text-lg mb-1">Your library is empty</p>
              <p className="text-[var(--text-secondary)] text-sm mb-6">Upload your first study material to get started</p>
              <button
                onClick={() => navigate('/library')}
                className="btn-gold px-6 py-2.5 rounded-lg text-sm transition-all"
              >
                Upload PDF
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
              {recentPdfs.map((pdf) => {
                const colors = SUBJECT_COLORS[pdf.subject] || SUBJECT_COLORS['General'];
                return (
                  <div
                    key={pdf.id}
                    onClick={() => {
                      if (pdf.status === 'ready') navigate(`/chat?pdf=${pdf.id}`);
                    }}
                    className={`card-storybook p-4 transition-all group ${
                      pdf.status === 'ready' ? 'cursor-pointer' : 'opacity-70'
                    }`}
                  >
                    <div className="h-28 bg-[var(--bg-secondary)] rounded-lg mb-4 flex items-center justify-center group-hover:bg-[var(--accent-green-light)] transition-colors relative overflow-hidden border border-[var(--border)]">
                      {pdf.status === 'processing' ? (
                        <Loader2 className="w-6 h-6 text-[var(--accent-amber)] animate-spin" />
                      ) : pdf.status === 'ready' ? (
                        <>
                          <BookOpen className="w-8 h-8 text-[var(--accent-amber)] opacity-40 group-hover:opacity-0 transition-all duration-300 transform group-hover:scale-110" />
                          <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300 transform scale-90 group-hover:scale-100">
                            <MessageSquare className="w-6 h-6 text-[var(--accent-green)] drop-shadow-md" />
                          </div>
                        </>
                      ) : (
                        <span className="text-red-400 text-xs font-medium">Error</span>
                      )}
                    </div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${colors.bg} ${colors.text}`}>
                        {pdf.subject}
                      </span>
                      {pdf.page_count ? (
                        <span className="text-[10px] text-[var(--text-muted)]">{pdf.page_count}p</span>
                      ) : null}
                    </div>
                    <h4 className="font-semibold text-[var(--text-primary)] text-sm truncate" title={pdf.name}>
                      {pdf.name}
                    </h4>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
};

export default Dashboard;
