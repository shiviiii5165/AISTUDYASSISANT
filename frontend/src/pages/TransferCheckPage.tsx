import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  BookOpen,
  LogOut,
  Sparkles,
  HelpCircle
} from 'lucide-react';
import { transferApi } from '../lib/transferApi';
import type {
  TransferSession,
  StudentTransferItemView,
  TransferFeedback,
  TransferSummary
} from '../types/transfer';

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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Header — Dignified, clean, pressure-free */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white tracking-tight">
              {currentItem?.transfer_badge_text || 'Independent Check'}
            </h1>
            <p className="text-xs text-slate-400">
              {subjectParam} • AI Assistance is Disabled
            </p>
          </div>
        </div>

        <button
          onClick={handleAbort}
          className="flex items-center space-x-1.5 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 rounded-lg transition-colors"
          title="Leave and continue learning anytime"
        >
          <LogOut className="w-4 h-4" />
          <span>Exit Check</span>
        </button>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-3xl w-full mx-auto p-6 flex flex-col justify-center">
        {loading && (
          <div className="text-center py-12">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-sm text-slate-400">Preparing your independent question...</p>
          </div>
        )}

        {errorMsg && !feedback && (
          <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/40 text-amber-200 text-sm flex items-start space-x-3 mb-6">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Notice</p>
              <p className="text-xs text-amber-300/90 mt-1">{errorMsg}</p>
              <button
                onClick={() => navigate('/practice')}
                className="mt-3 px-3 py-1 bg-amber-800/40 hover:bg-amber-800/60 text-xs text-amber-100 rounded-md transition-colors"
              >
                Return to Practice
              </button>
            </div>
          </div>
        )}

        {!loading && currentItem && !feedback && (
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl">
            {/* Why am I seeing this note */}
            {currentItem.why_explanation && (
              <div className="mb-6 px-4 py-3 bg-indigo-950/30 border border-indigo-800/30 rounded-xl flex items-start space-x-2.5">
                <Sparkles className="w-4 h-4 text-indigo-400 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-indigo-200 leading-relaxed">
                  {currentItem.why_explanation}
                </p>
              </div>
            )}

            {/* Question Prompt */}
            <div className="mb-6">
              <span className="text-xs font-semibold tracking-wider text-indigo-400 uppercase">
                Challenge
              </span>
              <h2 className="text-lg sm:text-xl font-medium text-slate-100 mt-1.5 leading-relaxed">
                {currentItem.prompt}
              </h2>
            </div>

            {/* Options or Input */}
            {currentItem.options && currentItem.options.length > 0 ? (
              <div className="space-y-3 mb-8">
                {currentItem.options.map((opt, idx) => {
                  const isSelected = selectedAnswer === opt;
                  return (
                    <button
                      key={idx}
                      onClick={() => setSelectedAnswer(opt)}
                      className={`w-full text-left p-4 rounded-xl border text-sm transition-all flex items-center justify-between ${
                        isSelected
                          ? 'border-indigo-500 bg-indigo-950/40 text-white font-medium shadow-sm'
                          : 'border-slate-800 bg-slate-900 hover:border-slate-700 hover:bg-slate-800/40 text-slate-300'
                      }`}
                    >
                      <span>{opt}</span>
                      <div
                        className={`w-5 h-5 rounded-full border flex items-center justify-center ${
                          isSelected
                            ? 'border-indigo-500 bg-indigo-500 text-white'
                            : 'border-slate-700'
                        }`}
                      >
                        {isSelected && <div className="w-2 h-2 rounded-full bg-white" />}
                      </div>
                    </button>
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
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}

            {/* AI-Disabled Notice & Action Footer */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-4 border-t border-slate-800/80">
              <div className="flex items-center space-x-2 text-xs text-slate-500">
                <HelpCircle className="w-4 h-4 text-slate-500" />
                <span>Hints and Tutor assistance are disabled for this check.</span>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={handleSubmit}
                  disabled={!selectedAnswer.trim() || submitting}
                  className="w-full sm:w-auto px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl transition-colors shadow-lg shadow-indigo-600/20"
                >
                  {submitting ? 'Verifying...' : 'Submit Answer'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Feedback / Outcome Screen */}
        {feedback && (
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl">
            <div className="flex items-center space-x-3 mb-6">
              {feedback.outcome === 'PASSED' ? (
                <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
              ) : (
                <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                  <BookOpen className="w-6 h-6" />
                </div>
              )}
              <div>
                <h2 className="text-xl font-semibold text-slate-100">
                  {feedback.feedback_headline}
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Independent Verification Outcome
                </p>
              </div>
            </div>

            {feedback.educational_explanation && (
              <div className="mb-6 p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-sm text-slate-300 leading-relaxed">
                <p className="text-xs font-semibold text-slate-400 mb-1">Concept Insight:</p>
                {feedback.educational_explanation}
              </div>
            )}

            {summary && (
              <div className="mb-8 p-4 rounded-xl bg-slate-800/40 border border-slate-700/40 text-xs text-slate-300">
                <p className="font-semibold text-slate-200 mb-1">Recommended Next Step:</p>
                <p>{summary.next_step}</p>
              </div>
            )}

            <div className="flex flex-col sm:flex-row items-center justify-end gap-3 pt-4 border-t border-slate-800">
              <button
                onClick={() => navigate('/practice')}
                className="w-full sm:w-auto px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-xl transition-colors"
              >
                Return to Practice
              </button>
              <button
                onClick={() => navigate(`/tutor?topic=${encodeURIComponent(subjectParam)}`)}
                className="w-full sm:w-auto px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl transition-colors flex items-center justify-center space-x-1.5"
              >
                <span>Continue Learning</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
