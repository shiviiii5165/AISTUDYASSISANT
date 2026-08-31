import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import {
  Search, BookOpen, ArrowRight, FileText, MessageSquare, Layers, CheckCircle2,
} from 'lucide-react';
import { fetchPdfs } from '../lib/api';
import type { PDFDocument } from '../lib/api';
import { subjectStyle } from '../lib/subjects';
import GreetingHeader from '../components/GreetingHeader';

const Dashboard: React.FC = () => {
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

  const readyPdfs = pdfs.filter(p => p.status === 'ready');
  const recentPdfs = pdfs.slice(0, 4);
  const totalPages = pdfs.reduce((sum, p) => sum + (p.page_count || 0), 0);
  const subjectCount = new Set(pdfs.map(p => p.subject).filter(Boolean)).size;

  const handleQuickAsk = () => {
    if (quickAsk.trim() && readyPdfs.length > 0) {
      navigate(`/chat?pdf=${readyPdfs[0].id}`);
    } else if (readyPdfs.length === 0) {
      navigate('/library');
    }
  };

  /* Every value here is derived from the /pdfs/list response already fetched
     above. The previous "Study Streak" tile was hardcoded to "1 day" with no
     backend behind it and has been replaced with a real count. */
  const STATS = [
    { label: 'Documents', value: pdfs.length, icon: FileText },
    { label: 'Total pages', value: totalPages, icon: BookOpen },
    { label: 'Ready to chat', value: readyPdfs.length, icon: CheckCircle2 },
    { label: 'Subjects', value: subjectCount, icon: Layers },
  ];

  return (
    <AppLayout title="Dashboard">
      <SEO
        title="Dashboard"
        description="View your learning progress, recent uploads, and AI study sessions on TeachGenie."
      />
      <div className="mx-auto max-w-5xl space-y-8 p-4 md:p-6 lg:p-8">

        <GreetingHeader
          avatarImageSrc="/scholar-genie-chibi.png"
          subtitle="Pick up where you left off, or ask a question about any document."
        />

        {/* Quick ask */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-2 shadow-[var(--shadow-sm)] focus-within:border-[var(--accent-green)]">
          <div className="flex items-center gap-2">
            <Search className="ml-3 h-5 w-5 shrink-0 text-[var(--text-muted)]" aria-hidden="true" />
            <label htmlFor="quick-ask" className="sr-only">
              Ask a question about your documents
            </label>
            <input
              id="quick-ask"
              type="text"
              value={quickAsk}
              onChange={(e) => setQuickAsk(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleQuickAsk()}
              placeholder={
                readyPdfs.length > 0
                  ? 'Ask a question about your documents'
                  : 'Upload a document first to start asking'
              }
              className="min-w-0 flex-1 border-none bg-transparent px-1 py-2.5 text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none"
              disabled={readyPdfs.length === 0}
            />
            <button
              type="button"
              onClick={handleQuickAsk}
              className="shrink-0 rounded-lg bg-[var(--accent-green)] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)] active:translate-y-px"
            >
              Ask
            </button>
          </div>
        </div>

        {/* Stats. Hairline-separated row rather than four bordered cards. */}
        <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--border)] lg:grid-cols-4">
          {STATS.map((stat) => (
            <div key={stat.label} className="bg-[var(--bg-card)] p-4">
              <dt className="flex items-center gap-2 text-xs font-medium text-[var(--text-secondary)]">
                <stat.icon className="h-4 w-4 text-[var(--accent-green-text)]" aria-hidden="true" />
                {stat.label}
              </dt>
              <dd className="mt-2 font-display text-3xl font-bold tabular-nums tracking-tight text-[var(--text-primary)]">
                {loadingPdfs ? (
                  <span
                    className="block h-8 w-12 animate-pulse rounded bg-[var(--bg-secondary)]"
                    aria-label="Loading"
                  />
                ) : (
                  stat.value
                )}
              </dd>
            </div>
          ))}
        </dl>

        {/* Recent documents */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-base font-semibold text-[var(--text-primary)]">
              Recent documents
            </h2>
            <button
              type="button"
              onClick={() => navigate('/library')}
              className="flex items-center gap-1 rounded text-xs font-semibold text-[var(--accent-green-text)] hover:underline"
            >
              View all
              <ArrowRight className="h-3 w-3" aria-hidden="true" />
            </button>
          </div>

          {loadingPdfs ? (
            /* Skeletons matching the card shape, not a spinner. */
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[0, 1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4"
                  aria-hidden="true"
                >
                  <div className="mb-4 h-24 animate-pulse rounded-lg bg-[var(--bg-secondary)]" />
                  <div className="mb-2 h-3 w-16 animate-pulse rounded bg-[var(--bg-secondary)]" />
                  <div className="h-4 w-full animate-pulse rounded bg-[var(--bg-secondary)]" />
                </div>
              ))}
              <span className="sr-only">Loading documents</span>
            </div>
          ) : recentPdfs.length === 0 ? (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-6 py-12 text-center">
              <BookOpen className="mx-auto mb-3 h-8 w-8 text-[var(--text-muted)]" aria-hidden="true" />
              <p className="font-display text-base font-semibold text-[var(--text-primary)]">
                Your library is empty
              </p>
              <p className="mx-auto mt-1 max-w-[40ch] text-sm text-[var(--text-secondary)]">
                Upload a PDF or a photo of your handwritten notes to start asking questions about it.
              </p>
              <button
                type="button"
                onClick={() => navigate('/library')}
                className="mt-5 rounded-lg bg-[var(--accent-green)] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)] active:translate-y-px"
              >
                Upload a document
              </button>
            </div>
          ) : (
            <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {recentPdfs.map((pdf) => {
                const colors = subjectStyle(pdf.subject);
                const isReady = pdf.status === 'ready';
                return (
                  <li key={pdf.id}>
                    {/* A real button, so the card is reachable by keyboard.
                        Previously a bare div with onClick. */}
                    <button
                      type="button"
                      disabled={!isReady}
                      onClick={() => navigate(`/chat?pdf=${pdf.id}`)}
                      className="group h-full w-full rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-left transition-colors enabled:hover:border-[var(--accent-green)] disabled:cursor-default disabled:opacity-70"
                    >
                      <div className="mb-3 flex h-24 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] transition-colors group-enabled:group-hover:bg-[var(--accent-green-light)]">
                        {pdf.status === 'processing' ? (
                          <span className="text-xs font-medium text-[var(--text-secondary)]">
                            Processing
                          </span>
                        ) : isReady ? (
                          <MessageSquare
                            className="h-6 w-6 text-[var(--text-muted)] transition-colors group-hover:text-[var(--accent-green-text)]"
                            aria-hidden="true"
                          />
                        ) : (
                          <span className="text-xs font-medium text-red-700">Failed</span>
                        )}
                      </div>
                      <div className="mb-1.5 flex items-center justify-between gap-2">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${colors.bg} ${colors.text}`}
                        >
                          {pdf.subject}
                        </span>
                        {pdf.page_count ? (
                          <span className="text-[10px] tabular-nums text-[var(--text-muted)]">
                            {pdf.page_count}p
                          </span>
                        ) : null}
                      </div>
                      <p
                        className="truncate text-sm font-semibold text-[var(--text-primary)]"
                        title={pdf.name}
                      >
                        {pdf.name}
                      </p>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>
    </AppLayout>
  );
};

export default Dashboard;
