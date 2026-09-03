import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import {
  Search, BookOpen, ArrowRight, FileText, MessageSquare, Layers, CheckCircle2,
} from 'lucide-react';
import { fetchPdfs } from '../lib/api';
import type { PDFDocument } from '../lib/api';
import { subjectStyle } from '../lib/subjects';
import GreetingHeader from '../components/GreetingHeader';
import { ILLUSTRATIONS } from '../lib/assets';
import { fadeUp, staggerContainer, cardHover, viewport } from '../lib/motion';
import DynamicText from '../components/DynamicText';
import { HoverCard } from '../components/MotionUtils';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const prefersReducedMotion = useReducedMotion();
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

        <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
          <GreetingHeader
            avatarImageSrc="/images/tutor_avatar.jpg"
            subtitle="Pick up where you left off, or ask a question about any document."
          />
          <DynamicText />
        </div>

        {/* Quick ask */}
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-2 shadow-bento focus-within:border-[var(--accent-royal)] transition-colors duration-300">
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
              className="btn-gold shrink-0 px-6 py-2.5 text-sm"
            >
              Ask
            </button>
          </div>
        </div>

        {/* Stats. Clean bento-style cards inspired by Teak. */}
        <motion.dl
          className="grid grid-cols-2 gap-4 lg:grid-cols-4"
          variants={prefersReducedMotion ? undefined : staggerContainer}
          initial="hidden"
          whileInView="show"
          viewport={viewport}
        >
          {STATS.map((stat) => (
            <HoverCard key={stat.label}>
              <div className="card-storybook h-full p-6 dark:bg-[var(--bg-navy)] flex flex-col justify-between">
                <dt className="flex items-center gap-3 text-sm font-medium text-[var(--text-secondary)]">
                  <div className="rounded-md bg-[var(--accent-baby)]/20 p-2">
                    <stat.icon className="h-5 w-5 text-[var(--accent-royal)]" aria-hidden="true" />
                  </div>
                  {stat.label}
                </dt>
                <dd className="mt-6 font-display text-5xl font-bold tracking-tight text-[var(--text-primary)]">
                  {loadingPdfs ? (
                    <span
                      className="block h-12 w-16 animate-pulse rounded-lg bg-[var(--bg-secondary)]"
                      aria-label="Loading"
                    />
                  ) : (
                    stat.value
                  )}
                </dd>
              </div>
            </HoverCard>
          ))}
        </motion.dl>

        {/* Subtle section separator — gentle gradient band matching Landing's wave pattern */}
        <div className="relative my-2 overflow-hidden rounded-2xl" aria-hidden="true">
          <div className="h-1.5 w-full bg-gradient-to-r from-[#ABD2FA]/40 via-[#1B2CC1]/15 to-[#7692FF]/30 rounded-full" />
        </div>

        {/* Recent documents — wrapped in a section card for visual weight */}
        <section className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-bento">
          <div className="mb-4 flex items-center justify-between">
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
                  className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4"
                  aria-hidden="true"
                >
                  <div className="mb-4 h-24 animate-pulse rounded-lg bg-[var(--bg-hover)]" />
                  <div className="mb-2 h-3 w-16 animate-pulse rounded bg-[var(--bg-hover)]" />
                  <div className="h-4 w-full animate-pulse rounded bg-[var(--bg-hover)]" />
                </div>
              ))}
              <span className="sr-only">Loading documents</span>
            </div>
          ) : recentPdfs.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-[var(--border)] bg-[var(--bg-secondary)] px-6 py-16 text-center">
              <motion.img
                src={ILLUSTRATIONS.emptyLibrary}
                onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                alt=""
                aria-hidden="true"
                className="mx-auto mb-6 h-32 w-32 rounded-xl object-cover shadow-sm"
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              />
              <p className="font-display text-lg font-bold text-[var(--text-primary)]">
                Your library is empty
              </p>
              <p className="mx-auto mt-2 max-w-[40ch] text-sm text-[var(--text-secondary)]">
                Upload a PDF or a photo of your handwritten notes to start asking questions about it.
              </p>
              <button
                type="button"
                onClick={() => navigate('/library')}
                className="btn-gold mt-6 px-6 py-3"
              >
                Upload a document
              </button>
            </div>
          ) : (
            <motion.ul
              className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4"
              variants={prefersReducedMotion ? undefined : staggerContainer}
              initial="hidden"
              whileInView="show"
              viewport={viewport}
            >
              {recentPdfs.map((pdf) => {
                const colors = subjectStyle(pdf.subject);
                const isReady = pdf.status === 'ready';
                return (
                  <motion.li
                    key={pdf.id}
                    variants={prefersReducedMotion ? undefined : fadeUp}
                    {...(prefersReducedMotion || !isReady ? {} : cardHover)}
                  >
                    <HoverCard className="h-full">
                      <button
                        type="button"
                        disabled={!isReady}
                        onClick={() => navigate(`/chat?pdf=${pdf.id}`)}
                        className="card-storybook group h-full w-full p-5 text-left disabled:cursor-default disabled:opacity-70"
                      >
                        <div className="mb-4 flex h-24 items-center justify-center rounded-xl bg-[var(--bg-secondary)] transition-colors group-enabled:group-hover:bg-[var(--accent-baby)]/30">
                          {pdf.status === 'processing' ? (
                            <span className="text-xs font-medium text-[var(--text-secondary)]">
                              Processing
                            </span>
                          ) : isReady ? (
                            <MessageSquare
                              className="h-6 w-6 text-[var(--text-muted)] transition-colors group-hover:text-[var(--accent-royal)]"
                              aria-hidden="true"
                            />
                          ) : (
                            <span className="text-xs font-medium text-red-700">Failed</span>
                          )}
                        </div>
                        <div className="mb-2 flex items-center justify-between gap-2">
                          <span
                            className={`rounded px-2 py-0.5 text-xs font-semibold ${colors.bg} ${colors.text}`}
                          >
                            {pdf.subject}
                          </span>
                          {pdf.page_count ? (
                            <span className="text-xs tabular-nums text-[var(--text-muted)]">
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
                    </HoverCard>
                  </motion.li>
                );
              })}
            </motion.ul>
          )}
        </section>

        {/* Bottom spacer for visual breathing room */}
        <div className="h-8" aria-hidden="true" />
      </div>
    </AppLayout>
  );
};

export default Dashboard;
