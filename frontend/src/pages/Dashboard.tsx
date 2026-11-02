import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import {
  Search, BookOpen, ArrowRight, FileText, MessageSquare, Layers, CheckCircle2,
  Flame, Award, Sparkles, RefreshCw, ChevronRight, Check, Target, Compass, Zap
} from 'lucide-react';
import { fetchPdfs } from '../lib/api';
import type { PDFDocument } from '../lib/api';
import { fetchLearnerContext } from '../lib/learnerApi';
import type { LearnerContext } from '../types/learner';
import { fetchGamificationSummary, checkInStreak } from '../lib/gamificationApi';
import type { GamificationSummary } from '../lib/gamificationApi';
import { fetchReviewQueue, submitCardReview } from '../lib/spacedRepetitionApi';
import type { SpacedCard } from '../lib/spacedRepetitionApi';
import { fetchDailyPersonalizedRoadmap } from '../lib/portalsApi';
import type { DailyPersonalizedRoadmap } from '../lib/portalsApi';
import { subjectStyle } from '../lib/subjects';
import GreetingHeader from '../components/GreetingHeader';
import { ILLUSTRATIONS, GENIE } from '../lib/assets';
import { fadeUp, staggerContainer, cardHover, viewport } from '../lib/motion';
import DynamicText from '../components/DynamicText';
import { HoverCard } from '../components/MotionUtils';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const prefersReducedMotion = useReducedMotion();
  const [pdfs, setPdfs] = useState<PDFDocument[]>([]);
  const [loadingPdfs, setLoadingPdfs] = useState(true);
  const [quickAsk, setQuickAsk] = useState('');
  const [learnerContext, setLearnerContext] = useState<LearnerContext | null>(null);

  // Gamification & Spaced Repetition State
  const [gamification, setGamification] = useState<GamificationSummary | null>(null);
  const [reviewCards, setReviewCards] = useState<SpacedCard[]>([]);
  const [dailyRoadmap, setDailyRoadmap] = useState<DailyPersonalizedRoadmap | null>(null);
  const [activeCardIndex, setActiveCardIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [submittingReview, setSubmittingReview] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [pdfRes, ctxRes, gamRes, cardsRes, roadRes] = await Promise.allSettled([
          fetchPdfs(),
          fetchLearnerContext(),
          fetchGamificationSummary(),
          fetchReviewQueue(5),
          fetchDailyPersonalizedRoadmap(),
        ]);
        if (pdfRes.status === 'fulfilled') setPdfs(pdfRes.value);
        if (ctxRes.status === 'fulfilled') setLearnerContext(ctxRes.value);
        if (gamRes.status === 'fulfilled') setGamification(gamRes.value);
        if (cardsRes.status === 'fulfilled') setReviewCards(cardsRes.value);
        if (roadRes.status === 'fulfilled') setDailyRoadmap(roadRes.value);

        // Auto check-in streak
        checkInStreak().catch(() => {});
      } catch (err) {
        console.error('Error loading dashboard data:', err);
      } finally {
        setLoadingPdfs(false);
      }
    })();
  }, []);

  const handleReviewCard = async (rating: number) => {
    if (reviewCards.length === 0 || submittingReview) return;
    const card = reviewCards[activeCardIndex];
    try {
      setSubmittingReview(true);
      await submitCardReview({
        card_id: card.id,
        rating,
        response_time_ms: 2500,
      });

      // Update local card queue
      const nextIndex = activeCardIndex + 1;
      setIsFlipped(false);
      if (nextIndex < reviewCards.length) {
        setActiveCardIndex(nextIndex);
      } else {
        setReviewCards([]);
        setActiveCardIndex(0);
      }

      // Refresh XP
      const updated = await fetchGamificationSummary();
      setGamification(updated);
    } catch (err) {
      console.error('Error reviewing card:', err);
    } finally {
      setSubmittingReview(false);
    }
  };

  const readyPdfs = pdfs.filter((p) => p.status === 'ready');
  const recentPdfs = pdfs.slice(0, 4);
  const totalPages = pdfs.reduce((sum, p) => sum + (p.page_count || 0), 0);
  const subjectCount = new Set(pdfs.map((p) => p.subject).filter(Boolean)).size;

  const handleQuickAsk = () => {
    if (quickAsk.trim() && readyPdfs.length > 0) {
      navigate(`/chat?pdf=${readyPdfs[0].id}`);
    } else if (readyPdfs.length === 0) {
      navigate('/library');
    }
  };

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
        description="View your learning progress, recent uploads, and AI study sessions on LearnByGenie."
      />
      <div className="mx-auto max-w-5xl space-y-6 p-4 md:p-6 lg:p-8">
        <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
          <GreetingHeader
            avatarImageSrc={GENIE.welcome}
            subtitle="Pick up where you left off, or ask a question about any document."
          />
          <DynamicText />
        </div>

        {/* Gamification & Daily Streak Bar */}
        {gamification && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Level & XP Progress Card */}
            <div className="md:col-span-2 p-4 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] shadow-bento flex flex-col justify-between space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                    <Award className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-[var(--text-primary)]">
                      Level {gamification.current_level} Scholar
                    </h3>
                    <span className="text-xs text-[var(--text-secondary)]">
                      {gamification.total_xp.toLocaleString()} Total XP earned
                    </span>
                  </div>
                </div>
                <span className="text-xs font-semibold text-amber-400">
                  {gamification.progress_to_next_level}% to Level {gamification.current_level + 1}
                </span>
              </div>

              {/* Progress bar */}
              <div className="space-y-1">
                <div className="w-full h-2 rounded-full bg-[var(--border)] overflow-hidden">
                  <div
                    style={{ width: `${gamification.progress_to_next_level}%` }}
                    className="h-full bg-gradient-to-r from-amber-400 to-[var(--accent-royal)] rounded-full transition-all duration-500"
                  />
                </div>
                <div className="flex justify-between text-[11px] text-[var(--text-secondary)]">
                  <span>{gamification.current_level_xp} XP in this tier</span>
                  <span>{gamification.next_level_xp} XP needed</span>
                </div>
              </div>
            </div>

            {/* Streak & Badges Card */}
            <div className="p-4 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] shadow-bento flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-500">
                  <Flame className="w-6 h-6 animate-pulse" />
                </div>
                <div>
                  <div className="text-xl font-bold font-display text-[var(--text-primary)]">
                    {gamification.streak.current_streak_days} Days
                  </div>
                  <div className="text-xs text-[var(--text-secondary)]">
                    Daily Study Streak
                  </div>
                </div>
              </div>
              <div className="text-right">
                <span className="text-xs font-semibold text-blue-400 block">
                  {gamification.streak.freeze_credits} Freezes
                </span>
                <span className="text-[11px] text-[var(--text-secondary)]">
                  Longest: {gamification.streak.longest_streak_days}d
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Spaced Repetition (SM-2) Flashcard Due Widget */}
        {reviewCards.length > 0 && (
          <div className="p-5 rounded-2xl border border-[var(--accent-royal)]/30 bg-gradient-to-r from-[var(--accent-royal)]/5 via-[var(--bg-card)] to-purple-500/5 shadow-bento space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-[var(--accent-royal)]" />
                <h3 className="text-sm font-bold text-[var(--text-primary)]">
                  Spaced Repetition Review Due ({reviewCards.length - activeCardIndex} remaining)
                </h3>
              </div>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-[var(--accent-royal)]/10 text-[var(--accent-royal)] font-semibold border border-[var(--accent-royal)]/20">
                SM-2 Engine
              </span>
            </div>

            {activeCardIndex < reviewCards.length && (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] p-4 space-y-3">
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>Topic: <strong className="text-[var(--text-primary)]">{reviewCards[activeCardIndex].skill_id}</strong></span>
                  <span>Interval: {reviewCards[activeCardIndex].interval_days}d</span>
                </div>

                <div className="text-sm font-medium text-[var(--text-primary)] min-h-[48px] flex items-center">
                  {reviewCards[activeCardIndex].front_prompt}
                </div>

                {isFlipped ? (
                  <div className="p-3 rounded-lg bg-[var(--bg-hover)] border border-[var(--border)] text-xs text-emerald-400 space-y-1">
                    <strong className="block text-xs text-emerald-300">Solution:</strong>
                    {reviewCards[activeCardIndex].back_solution}
                    {reviewCards[activeCardIndex].explanation && (
                      <p className="text-[11px] text-[var(--text-secondary)] pt-1">
                        {reviewCards[activeCardIndex].explanation}
                      </p>
                    )}
                  </div>
                ) : (
                  <button
                    onClick={() => setIsFlipped(true)}
                    className="w-full py-2 rounded-lg bg-[var(--bg-hover)] text-xs font-semibold text-[var(--accent-royal)] hover:bg-[var(--accent-royal)] hover:text-white transition"
                  >
                    Reveal Solution
                  </button>
                )}

                {isFlipped && (
                  <div className="flex items-center justify-between gap-2 pt-2 border-t border-[var(--border)]">
                    <button
                      onClick={() => handleReviewCard(1)}
                      disabled={submittingReview}
                      className="flex-1 py-1.5 rounded-lg bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 text-xs font-semibold transition"
                    >
                      Again (1)
                    </button>
                    <button
                      onClick={() => handleReviewCard(3)}
                      disabled={submittingReview}
                      className="flex-1 py-1.5 rounded-lg bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 text-xs font-semibold transition"
                    >
                      Hard (3)
                    </button>
                    <button
                      onClick={() => handleReviewCard(4)}
                      disabled={submittingReview}
                      className="flex-1 py-1.5 rounded-lg bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 text-xs font-semibold transition"
                    >
                      Good (4)
                    </button>
                    <button
                      onClick={() => handleReviewCard(5)}
                      disabled={submittingReview}
                      className="flex-1 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 text-xs font-semibold transition"
                    >
                      Easy (5)
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Canonical Learner Context Contextual Bar */}
        {learnerContext && (
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-5 py-3 shadow-bento transition-all hover:border-[var(--accent-royal)]/30">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="font-bold text-[var(--text-primary)]">
                {learnerContext.education.level} · {learnerContext.goals.primary || learnerContext.education.board}
              </span>
              {learnerContext.subjects.length > 0 && (
                <>
                  <span className="text-[var(--text-muted)]">·</span>
                  <span className="text-[var(--text-secondary)]">
                    {learnerContext.subjects.slice(0, 4).join(' · ')}
                  </span>
                </>
              )}
            </div>
            <Link
              to="/profile"
              className="text-xs font-semibold text-[var(--accent-royal)] hover:underline inline-flex items-center gap-1 shrink-0"
            >
              {learnerContext.profile_completeness.is_complete ? 'Learning Profile' : 'Complete Profile'}
              <ArrowRight className="w-3 h-3 inline" />
            </Link>
          </div>
        )}

        {/* Stage 8: Daily Personalized Learning Roadmap (30/50/20) */}
        {dailyRoadmap && dailyRoadmap.tasks.length > 0 && (
          <div className="p-6 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] shadow-bento space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[var(--border)] pb-3">
              <div className="flex items-center gap-2">
                <Target className="w-5 h-5 text-indigo-500" />
                <div>
                  <h2 className="text-base font-bold font-display text-[var(--text-primary)]">
                    Today's Priority Learning Roadmap
                  </h2>
                  <p className="text-xs text-[var(--text-secondary)]">
                    Algorithmic 30/50/20 balance: 30% Spaced Repair · 50% Core Progression · 20% Interleaved Transfer
                  </p>
                </div>
              </div>
              <span className="text-xs px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 font-semibold border border-indigo-500/20 self-start sm:self-auto">
                {dailyRoadmap.target_exam} · {dailyRoadmap.daily_goal_minutes}m Budget
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
              {dailyRoadmap.tasks.map((task) => {
                const isRepair = task.category === 'SPACED_ERROR_REPAIR';
                const isProg = task.category === 'CORE_PROGRESSION';
                const badgeColor = isRepair
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                  : isProg
                  ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                  : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';

                return (
                  <div
                    key={task.task_id}
                    className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] flex flex-col justify-between space-y-3 hover:border-indigo-500/40 transition shadow-sm"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${badgeColor}`}>
                          {task.weight_percentage}% Daily Weight
                        </span>
                        <span className="text-[11px] text-[var(--text-secondary)]">
                          ~{task.expected_duration_minutes} mins
                        </span>
                      </div>

                      <h3 className="text-sm font-bold text-[var(--text-primary)] line-clamp-1">
                        {task.title}
                      </h3>

                      <p className="text-xs text-[var(--text-secondary)] line-clamp-2 leading-relaxed">
                        {task.why_recommended}
                      </p>

                      <div className="text-[11px] text-indigo-400/90 bg-indigo-500/5 p-2 rounded-lg border border-indigo-500/10">
                        <strong className="block text-[10px] uppercase tracking-wider text-indigo-300">Unlocks Next:</strong>
                        {task.unlocks_next}
                      </div>
                    </div>

                    <button
                      onClick={() => navigate(task.action_route)}
                      className="w-full py-2 rounded-lg bg-[var(--bg-hover)] text-xs font-semibold text-[var(--accent-royal)] hover:bg-[var(--accent-royal)] hover:text-white transition flex items-center justify-center gap-1.5"
                    >
                      Start This Task
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

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

        {/* Stats */}
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

        {/* Subtle section separator */}
        <div className="relative my-2 overflow-hidden rounded-2xl" aria-hidden="true">
          <div className="h-1.5 w-full bg-gradient-to-r from-[#ABD2FA]/40 via-[#1B2CC1]/15 to-[#7692FF]/30 rounded-full" />
        </div>

        {/* Recent documents */}
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
                onError={(e) => {
                  (e.currentTarget as HTMLImageElement).style.display = 'none';
                }}
                alt=""
                aria-hidden="true"
                className="mx-auto mb-6 h-32 w-32 rounded-xl object-cover shadow-sm"
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
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

        <div className="h-8" aria-hidden="true" />
      </div>
    </AppLayout>
  );
};

export default Dashboard;
