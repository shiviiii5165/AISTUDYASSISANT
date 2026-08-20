import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { Search, BookOpen, Loader2, ArrowRight, FileText, MessageSquare, Sparkles, TrendingUp } from 'lucide-react';
import { fetchPdfs } from '../lib/api';
import type { PDFDocument } from '../lib/api';
import { useAuthStore } from '../store/useAuthStore';

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
    <AppLayout title={
      <div className="flex items-center gap-3">
        <span>{getGreeting()}, {firstName}</span>
        {user?.plan === 'pro' ? (
          <span className="hidden sm:flex items-center gap-1 bg-indigo-50 text-[var(--accent-indigo)] text-xs font-bold px-2.5 py-1 rounded-md border border-indigo-100">
            <Sparkles className="w-3 h-3" /> Pro Plan
          </span>
        ) : (
          <div className="hidden sm:flex items-center gap-2">
            <span className="bg-gray-100 text-gray-600 text-xs font-bold px-2.5 py-1 rounded-md border border-gray-200">
              Free Plan
            </span>
            <button 
              onClick={() => navigate('/pricing')}
              className="text-xs font-bold text-white bg-[var(--text-primary)] px-3 py-1 rounded-md hover:bg-gray-800 transition-colors shadow-sm"
            >
              Upgrade
            </button>
          </div>
        )}
      </div>
    }>
      <SEO 
        title="Dashboard" 
        description="View your learning progress, recent uploads, and AI study sessions on TeachGenie." 
      />
      <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto space-y-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
          {STATS.map((stat) => (
            <div key={stat.label} className="bg-white p-4 rounded-xl border border-[var(--border)] shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] transition-shadow">
              <div className={`w-8 h-8 ${stat.iconBg} rounded-lg flex items-center justify-center mb-3`}>
                {stat.icon}
              </div>
              <p className="text-[var(--text-muted)] text-[11px] font-semibold uppercase tracking-wider mb-0.5">{stat.label}</p>
              {loadingPdfs && !stat.isStreak ? (
                <Loader2 className="w-4 h-4 animate-spin text-[var(--text-muted)]" />
              ) : (
                <p className="text-2xl font-bold text-[var(--text-primary)] tracking-tight">{stat.value}</p>
              )}
            </div>
          ))}
        </div>

        {/* Quick Ask */}
        <div className="bg-white p-1.5 rounded-xl border border-[var(--border)] shadow-[var(--shadow-sm)] flex items-center gap-2">
          <div className="pl-3">
            <Search className="w-4 h-4 text-[var(--text-muted)]" />
          </div>
          <input
            type="text"
            value={quickAsk}
            onChange={(e) => setQuickAsk(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleQuickAsk()}
            placeholder={readyPdfs.length > 0 ? "Ask a doubt from any PDF..." : "Upload a PDF first to start asking..."}
            className="flex-1 bg-transparent border-none focus:outline-none text-[var(--text-primary)] py-2.5 placeholder:text-[var(--text-muted)] text-sm min-w-0"
            disabled={readyPdfs.length === 0}
          />
          <button
            onClick={handleQuickAsk}
            className="bg-[var(--accent-green)] text-white px-4 py-2 rounded-lg font-medium hover:bg-green-700 transition-colors flex items-center gap-1.5 text-sm shadow-sm shrink-0"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Ask</span>
          </button>
        </div>

        {/* Recent PDFs */}
        <div>
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
            <div className="text-center py-10 bg-white rounded-xl border border-[var(--border)] shadow-[var(--shadow-sm)]">
              <div className="w-12 h-12 bg-[var(--bg-secondary)] rounded-xl flex items-center justify-center mx-auto mb-3">
                <BookOpen className="w-6 h-6 text-[var(--text-muted)]" />
              </div>
              <p className="text-[var(--text-secondary)] font-medium text-sm mb-1">No PDFs yet</p>
              <p className="text-[var(--text-muted)] text-xs mb-4">Upload your first study material to get started</p>
              <button
                onClick={() => navigate('/library')}
                className="bg-[var(--accent-green)] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
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
                    className={`bg-white p-4 rounded-xl border border-[var(--border)] shadow-[var(--shadow-sm)] transition-all group ${
                      pdf.status === 'ready' ? 'hover:shadow-[var(--shadow-md)] hover:border-[var(--accent-green)]/40 cursor-pointer' : 'opacity-70'
                    }`}
                  >
                    <div className="h-24 bg-[var(--bg-secondary)] rounded-lg mb-3 flex items-center justify-center group-hover:bg-green-50/50 transition-colors relative overflow-hidden">
                      {pdf.status === 'processing' ? (
                        <Loader2 className="w-6 h-6 text-[var(--accent-amber)] animate-spin" />
                      ) : pdf.status === 'ready' ? (
                        <>
                          <BookOpen className="w-6 h-6 text-[var(--text-muted)] opacity-30 group-hover:opacity-0 transition-opacity" />
                          <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                            <MessageSquare className="w-5 h-5 text-[var(--accent-green)]" />
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
