import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  BookOpen,
  LogOut,
  Sparkles,
  HelpCircle,
  Lightbulb,
  Check
} from 'lucide-react';
import { transferApi } from '../lib/transferApi';
import type {
  TransferSession,
  StudentTransferItemView,
  TransferFeedback,
  TransferSummary
} from '../types/transfer';
import { Card, Button, Badge } from '../components/ui';
import { pageTransition, cardHover, buttonPress } from '../lib/motion';

export const TransferCheckPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const skillIdParam = searchParams.get('skill_id') || 'MATH_LIN_EQ';
  const subjectParam = searchParams.get('subject') || 'Mathematics';

  const [session, setSession] = useState<TransferSession | null>(null);
  const [currentItem, setCurrentItem] = useState<StudentTransferItemView | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<string>('');
  const [feedback, setFeedback] = useState<TransferFeedback | null>(null);
  const [summary, setSummary] = useState<TransferSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [startTime] = useState<number>(Date.now());

  // Start or resume session on mount
  useEffect(() => {
    let isMounted = true;

    async function initTransfer() {
      setLoading(true);
      setErrorMsg(null);
      try {
        const sess = await transferApi.startSession({
          skill_id: skillIdParam,
          subject: subjectParam,
          source_trigger: 'STUDENT_REQUEST'
        });

        if (!isMounted) return;
        setSession(sess);

        const item = await transferApi.getItem(sess.id);
        if (isMounted) {
          setCurrentItem(item);
        }
      } catch (err: any) {
        if (!isMounted) return;
        const msg = err.response?.data?.detail || 'Unable to start independent check at this time.';
        setErrorMsg(msg);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    initTransfer();

    return () => {
      isMounted = false;
    };
  }, [skillIdParam, subjectParam]);

  const handleSubmit = async () => {
    if (!session || !currentItem || !selectedAnswer.trim()) return;

    setSubmitting(true);
    setErrorMsg(null);
    try {
      const responseTime = Date.now() - startTime;
      const fb = await transferApi.submitResponse(session.id, {
        item_id: currentItem.item_id,
        student_response: selectedAnswer.trim(),
        response_time_ms: responseTime,
        question_index: session.question_index
      });
      setFeedback(fb);

      // Fetch summary
      const sum = await transferApi.getSummary(session.id);
      setSummary(sum);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Error submitting response. Please try again.';
      setErrorMsg(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleAbort = async () => {
    if (session) {
      try {
        await transferApi.abortSession(session.id, 'STUDENT_EXITED');
      } catch {
        // Safe exit
      }
    }
    navigate('/practice');
  };

  return (
    <motion.div
      variants={pageTransition}
      initial="initial"
      animate="animate"
      exit="exit"
      className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] flex flex-col font-sans"
    >
      {/* Header — Dignified, clean, pressure-free white bar with soft depth */}
      <header className="border-b border-[var(--border)] bg-white/95 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-30 shadow-[var(--shadow-xs)]">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-[var(--brand-light)] border border-[var(--brand-soft)] flex items-center justify-center text-[var(--brand-primary)] shadow-sm">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-[var(--text-primary)] tracking-tight">
              {currentItem?.transfer_badge_text || 'Independent Transfer Check'}
            </h1>
            <p className="text-xs text-[var(--text-muted)] flex items-center gap-1.5 mt-0.5">
              <span>{subjectParam}</span>
              <span>•</span>
              <span className="font-medium text-[var(--accent-sky-text)]">AI Assistance Disabled for Verification</span>
            </p>
          </div>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={handleAbort}
          className="flex items-center space-x-1.5"
          title="Leave and continue learning anytime"
        >
          <LogOut className="w-3.5 h-3.5 text-[var(--text-muted)]" />
          <span>Exit Check</span>
        </Button>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-2xl w-full mx-auto p-6 sm:p-8 flex flex-col justify-center">
        {loading && (
          <div className="text-center py-16">
            <div className="w-10 h-10 border-3 border-[var(--brand-primary)] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-sm font-medium text-[var(--text-secondary)]">Preparing your independent question...</p>
            <p className="text-xs text-[var(--text-muted)] mt-1">Calibrating item difficulty to verify standalone mastery</p>
          </div>
        )}

        {errorMsg && !feedback && (
          <div className="p-4 rounded-xl bg-[var(--accent-yellow-light)] border border-[#FCE6BD] text-[var(--accent-yellow-text)] text-sm flex items-start space-x-3 mb-6 shadow-sm">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-sm">Notice</p>
              <p className="text-xs mt-1 leading-relaxed">{errorMsg}</p>
              <Button
                variant="secondary"
                size="xs"
                onClick={() => navigate('/practice')}
                className="mt-3"
              >
                Return to Practice
              </Button>
            </div>
          </div>
        )}

        {!loading && currentItem && !feedback && (
          <Card variant="elevated" className="card-3d p-6 sm:p-8">
            {/* Why am I seeing this note */}
            {currentItem.why_explanation && (
              <div className="mb-6 px-4 py-3 bg-[var(--accent-sky-light)] border border-[#D1EBF9] rounded-xl flex items-start space-x-3 shadow-xs">
                <Sparkles className="w-4 h-4 text-[var(--accent-sky-text)] mt-0.5 flex-shrink-0" />
                <p className="text-xs text-[var(--accent-sky-text)] leading-relaxed font-medium">
                  {currentItem.why_explanation}
                </p>
              </div>
            )}

            {/* Question Prompt */}
            <div className="mb-6">
              <div className="flex items-center gap-2 mb-2">
                <Badge tone="sky" dot>Standalone Transfer Probe</Badge>
                <span className="text-xs text-[var(--text-muted)] font-mono">No Tutor Prompts</span>
              </div>
              <h2 className="text-lg sm:text-xl font-semibold text-[var(--text-primary)] leading-relaxed">
                {currentItem.prompt}
              </h2>
            </div>

            {/* Options or Input */}
            {currentItem.options && currentItem.options.length > 0 ? (
              <div className="space-y-3 mb-8">
                {currentItem.options.map((opt, idx) => {
                  const isSelected = selectedAnswer === opt;
                  return (
                    <motion.button
                      key={idx}
                      variants={cardHover}
                      whileHover="hover"
                      whileTap="tap"
                      onClick={() => setSelectedAnswer(opt)}
                      className={`w-full text-left p-4 rounded-xl border text-sm transition-all flex items-center justify-between shadow-xs ${
                        isSelected
                          ? 'border-[var(--brand-primary)] bg-[var(--brand-light)] text-[var(--brand-primary)] font-semibold ring-2 ring-[var(--brand-soft)] shadow-sm'
                          : 'border-[var(--border)] bg-white hover:border-[var(--brand-primary)]/50 hover:bg-[var(--bg-hover)] text-[var(--text-primary)]'
                      }`}
                    >
                      <span className="pr-4">{opt}</span>
                      <div
                        className={`w-5 h-5 rounded-full border flex items-center justify-center shrink-0 transition-colors ${
                          isSelected
                            ? 'border-[var(--brand-primary)] bg-[var(--brand-primary)] text-white'
                            : 'border-[var(--border-strong)] bg-white'
                        }`}
                      >
                        {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                      </div>
                    </motion.button>
                  );
                })}
              </div>
            ) : (
              <div className="mb-8">
                <input
                  type="text"
                  value={selectedAnswer}
                  onChange={(e) => setSelectedAnswer(e.target.value)}
                  placeholder="Enter your final answer here"
                  className="w-full bg-white border border-[var(--border)] rounded-xl px-4 py-3 text-[var(--text-primary)] placeholder-[var(--text-disabled)] text-sm focus:outline-none focus:border-[var(--brand-primary)] focus:ring-2 focus:ring-[var(--brand-soft)] transition shadow-xs"
                />
              </div>
            )}

            {/* AI-Disabled Notice & Action Footer */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-5 border-t border-[var(--border)]">
              <div className="flex items-center space-x-2 text-xs text-[var(--text-muted)]">
                <HelpCircle className="w-4 h-4 text-[var(--text-muted)]" />
                <span>Hints and Tutor assistance are disabled for this check.</span>
              </div>

              <div className="flex items-center space-x-3">
                <Button
                  variant="primary"
                  size="md"
                  onClick={handleSubmit}
                  disabled={!selectedAnswer.trim() || submitting}
                  className="w-full sm:w-auto"
                >
                  {submitting ? 'Verifying...' : 'Submit Answer'}
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Feedback / Outcome Screen */}
        {feedback && (
          <Card variant="elevated" className="card-3d p-6 sm:p-8 space-y-6">
            <div className="flex items-center space-x-4">
              {feedback.outcome === 'PASSED' ? (
                <div className="w-14 h-14 rounded-2xl bg-[var(--accent-green-light)] border border-[var(--accent-green-soft)] flex items-center justify-center text-[var(--accent-green)] shadow-sm">
                  <CheckCircle2 className="w-7 h-7" />
                </div>
              ) : (
                <div className="w-14 h-14 rounded-2xl bg-[var(--accent-yellow-light)] border border-[var(--accent-yellow-soft)] flex items-center justify-center text-[var(--accent-yellow-text)] shadow-sm">
                  <BookOpen className="w-7 h-7" />
                </div>
              )}
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Badge tone={feedback.outcome === 'PASSED' ? 'green' : 'yellow'}>
                    {feedback.outcome === 'PASSED' ? 'Mastery Verified' : 'Practice Needed'}
                  </Badge>
                  <span className="text-xs text-[var(--text-muted)]">Transfer Assessment</span>
                </div>
                <h2 className="text-xl font-bold text-[var(--text-primary)]">
                  {feedback.feedback_headline}
                </h2>
              </div>
            </div>

            {feedback.educational_explanation && (
              <div className="p-4 rounded-xl bg-[var(--bg-subtle)] border border-[var(--border)] text-sm text-[var(--text-secondary)] leading-relaxed">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-[var(--text-primary)] mb-1.5">
                  <Lightbulb className="w-3.5 h-3.5 text-[var(--accent-yellow-text)]" />
                  <span>Concept Insight</span>
                </div>
                <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                  {feedback.educational_explanation}
                </p>
              </div>
            )}

            {summary && (
              <div className="p-4 rounded-xl bg-[var(--brand-light)] border border-[var(--brand-soft)] text-xs text-[var(--brand-primary)]">
                <p className="font-semibold mb-1">Recommended Next Step:</p>
                <p className="text-[var(--text-secondary)] leading-relaxed">{summary.next_step}</p>
              </div>
            )}

            <div className="flex flex-col sm:flex-row items-center justify-end gap-3 pt-5 border-t border-[var(--border)]">
              <Button
                variant="secondary"
                size="md"
                onClick={() => navigate('/practice')}
                className="w-full sm:w-auto"
              >
                Return to Practice
              </Button>
              <Button
                variant="primary"
                size="md"
                onClick={() => navigate(`/tutor?topic=${encodeURIComponent(subjectParam)}`)}
                className="w-full sm:w-auto flex items-center justify-center space-x-1.5"
              >
                <span>Continue Learning</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </Card>
        )}
      </main>
    </motion.div>
  );
};
