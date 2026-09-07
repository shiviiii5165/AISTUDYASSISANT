import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Clock, CheckCircle2, XCircle, Sparkles, Loader2, Volume2, VolumeX,
  HelpCircle, Trophy, Zap, AlertCircle
} from 'lucide-react';
import SEO from '../components/SEO';
import {
  getParticipantState, submitParticipantResponse,
  type StudentRoomState
} from '../lib/liveQuizApi';
import { supabase } from '../lib/supabase';
import { soundFx } from '../lib/soundFx';

const SHAPES = ['●', '▲', '■', '◆'];
const COLORS = [
  'border-blue-500 hover:border-blue-600 bg-blue-50/50 hover:bg-blue-50',
  'border-purple-500 hover:border-purple-600 bg-purple-50/50 hover:bg-purple-50',
  'border-teal-500 hover:border-teal-600 bg-teal-50/50 hover:bg-teal-50',
  'border-amber-500 hover:border-amber-600 bg-amber-50/50 hover:bg-amber-50',
];

const LiveQuizParticipantPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [token, setToken] = useState<string | null>(null);
  const [state, setState] = useState<StudentRoomState | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState<boolean>(soundFx.isMuted());
  const [timeLeft, setTimeLeft] = useState<number | null>(null);

  // 1. Load Stored Participant JWT
  useEffect(() => {
    if (!sessionId) return;
    const stored = sessionStorage.getItem(`teachgenie_live_participant_${sessionId}`);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setToken(parsed.participant_token);
      } catch {
        navigate('/join');
      }
    } else {
      navigate('/join');
    }
  }, [sessionId]);

  // 2. Fetch Initial State & Subscribe to Broadcasts
  useEffect(() => {
    if (!sessionId || !token) return;

    const fetchState = async () => {
      try {
        const res = await getParticipantState(sessionId, token);
        setState(res);
        setTimeLeft(res.remaining_seconds);
        if (res.has_submitted) {
          setSelectedOption(res.selected_option_id || null);
        }
        if (res.status === 'COMPLETED' || res.status === 'ENDED') {
          soundFx.playSessionComplete();
        }
      } catch (err) {
        console.error('[ParticipantView] Failed to fetch state', err);
      } finally {
        setLoading(false);
      }
    };

    fetchState();

    // Supabase Realtime channel for room events
    const channel = supabase.channel(`session:${sessionId}`);
    channel
      .on('broadcast', { event: 'question:started' }, () => {
        fetchState();
        setSelectedOption(null);
        soundFx.playJoinSound();
      })
      .on('broadcast', { event: 'question:revealed' }, () => {
        fetchState();
      })
      .on('broadcast', { event: 'session:ended' }, () => {
        fetchState();
        soundFx.playSessionComplete();
      })
      .subscribe();

    // Polling fallback every 3 seconds
    const interval = setInterval(fetchState, 3000);

    return () => {
      supabase.removeChannel(channel);
      clearInterval(interval);
    };
  }, [sessionId, token]);

  // 3. Countdown timer tick
  useEffect(() => {
    if (timeLeft === null || timeLeft <= 0 || state?.is_revealed) return;

    if (timeLeft <= 5 && timeLeft > 0) {
      soundFx.playTimerTick();
    }

    const timer = setInterval(() => {
      setTimeLeft((prev) => (prev !== null && prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft, state?.is_revealed]);

  // Play sound when revealed
  useEffect(() => {
    if (state?.is_revealed && state.question && selectedOption) {
      const isCorrect = Array.isArray(state.question.correct_answer)
        ? state.question.correct_answer.includes(selectedOption)
        : state.question.correct_answer === selectedOption;

      if (isCorrect) {
        soundFx.playCorrectSound();
      } else {
        soundFx.playIncorrectSound();
      }
    }
  }, [state?.is_revealed]);

  const handleSelectOption = async (optionText: string) => {
    if (!sessionId || !token || !state?.question || state.has_submitted || state.is_revealed || submitting) return;

    setSelectedOption(optionText);
    setSubmitting(true);
    soundFx.playTimerTick();

    try {
      await submitParticipantResponse(sessionId, state.question.id, optionText, token);
      // Refresh state to confirm submission
      const refreshed = await getParticipantState(sessionId, token);
      setState(refreshed);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit response');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center bg-[var(--bg-primary)]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-[var(--accent-royal)]" />
          <p className="font-semibold text-[var(--text-secondary)]">Connecting to Classroom...</p>
        </div>
      </div>
    );
  }

  if (!state) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center bg-[var(--bg-primary)] p-4">
        <div className="w-full max-w-md rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
          <AlertCircle className="mx-auto h-8 w-8 text-red-600" />
          <h2 className="mt-2 text-lg font-bold text-red-900">Session Error</h2>
          <p className="mt-1 text-sm text-red-800">Cannot load session data. Please rejoin.</p>
        </div>
      </div>
    );
  }

  const isLobby = state.status === 'LOBBY' || state.status === 'CREATED';
  const isEnded = state.status === 'COMPLETED' || state.status === 'ENDED' || state.status === 'EXPIRED';
  const q = state.question;
  const isRevealed = state.is_revealed;
  const hasSubmitted = state.has_submitted || selectedOption !== null;

  return (
    <div className="flex min-h-[100dvh] flex-col bg-[var(--bg-primary)] px-4 py-6 sm:px-6">
      <SEO title="Live Quiz Session | TeachGenie" description="Live interactive classroom quiz." />

      {/* Top Participant Header */}
      <div className="mx-auto mb-6 flex w-full max-w-2xl items-center justify-between rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-3.5 shadow-sm">
        <div className="flex items-center gap-2.5">
          <span className="text-2xl">{state.participant?.avatar_seed || '👤'}</span>
          <div>
            <h3 className="text-sm font-bold text-[var(--text-primary)]">{state.participant?.display_name}</h3>
            <div className="flex items-center gap-2 font-mono text-xs text-[var(--text-muted)]">
              <span>{state.participant?.score || 0} pts</span>
              {(state.participant?.streak || 0) > 1 && (
                <span className="flex items-center gap-0.5 text-amber-600 font-bold">
                  <Zap className="h-3 w-3 fill-current" /> {state.participant?.streak} Streak
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {timeLeft !== null && !isLobby && !isEnded && (
            <div className={`flex items-center gap-1.5 rounded-xl px-3 py-1.5 font-mono text-sm font-bold tabular-nums ${timeLeft <= 5 ? 'animate-pulse bg-red-100 text-red-700' : 'bg-[var(--bg-secondary)] text-[var(--text-primary)]'}`}>
              <Clock className="h-4 w-4" />
              <span>{timeLeft}s</span>
            </div>
          )}
          <button
            onClick={() => setIsMuted(soundFx.toggleMute())}
            aria-label={isMuted ? 'Unmute sound' : 'Mute sound'}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
          >
            {isMuted ? <VolumeX className="h-4 w-4 text-red-500" /> : <Volume2 className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* ─── LOBBY WAITING SCREEN ────────────────────────────────────────── */}
      {isLobby && (
        <div className="mx-auto my-auto w-full max-w-md text-center">
          <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-8 shadow-xl">
            <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-[var(--accent-baby)]/30 text-4xl">
              {state.participant?.avatar_seed || '🚀'}
            </div>
            <h2 className="font-display text-2xl font-bold text-[var(--text-primary)]">You're in!</h2>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              Welcome, <strong className="text-[var(--accent-royal)]">{state.participant?.display_name}</strong>. Hang tight while your teacher gets everyone ready!
            </p>
            <div className="mt-8 flex items-center justify-center gap-2 text-xs font-semibold text-[var(--text-muted)]">
              <Loader2 className="h-4 w-4 animate-spin text-[var(--accent-royal)]" />
              <span>Waiting for teacher to start...</span>
            </div>
          </motion.div>
        </div>
      )}

      {/* ─── SESSION ENDED SCREEN ────────────────────────────────────────── */}
      {isEnded && (
        <div className="mx-auto my-auto w-full max-w-md text-center">
          <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-8 shadow-xl">
            <Trophy className="mx-auto mb-4 h-16 w-16 text-amber-500" />
            <h2 className="font-display text-3xl font-bold text-[var(--text-primary)]">Quiz Complete!</h2>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">Great effort! Here is your final summary:</p>
            
            <div className="my-6 rounded-2xl bg-[var(--bg-secondary)] p-6">
              <div className="font-display text-4xl font-bold text-[var(--accent-royal)]">
                {state.participant?.score || 0}
              </div>
              <div className="mt-1 text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
                Total Points Earned
              </div>
            </div>

            <p className="text-xs text-[var(--text-muted)]">
              Your teacher will review overall classroom concept mastery on their screen.
            </p>
          </motion.div>
        </div>
      )}

      {/* ─── ACTIVE QUESTION SCREEN ──────────────────────────────────────── */}
      {!isLobby && !isEnded && q && (
        <div className="mx-auto w-full max-w-2xl space-y-6">
          {/* Question Text */}
          <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-md sm:p-8">
            <div className="mb-3 flex items-center justify-between text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
              <span>Question {state.current_question_index + 1} of {state.total_questions}</span>
              {q.concept_id && <span>{q.concept_id}</span>}
            </div>

            <h2 className="font-display text-xl font-bold text-[var(--text-primary)] sm:text-2xl">
              {q.question_text}
            </h2>
          </div>

          {/* Option Selection Grid (Distinct Shapes & High Contrast) */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {q.options?.map((opt: string, idx: number) => {
              const isChosen = selectedOption === opt;
              const isCorrectAnswer = isRevealed && (Array.isArray(q.correct_answer) ? q.correct_answer.includes(opt) : q.correct_answer === opt);
              const isWrongChoice = isRevealed && isChosen && !isCorrectAnswer;

              let cardStyle = `${COLORS[idx % COLORS.length]} border-2`;
              if (isChosen && !isRevealed) {
                cardStyle = 'border-[var(--accent-royal)] bg-[var(--accent-baby)]/30 ring-2 ring-[var(--accent-royal)]';
              } else if (isRevealed) {
                if (isCorrectAnswer) {
                  cardStyle = 'border-emerald-600 bg-emerald-50 text-emerald-950 font-bold ring-2 ring-emerald-600';
                } else if (isWrongChoice) {
                  cardStyle = 'border-red-500 bg-red-50 text-red-950 font-medium opacity-80';
                } else {
                  cardStyle = 'border-gray-200 bg-gray-50 opacity-40';
                }
              }

              return (
                <button
                  key={idx}
                  onClick={() => handleSelectOption(opt)}
                  disabled={hasSubmitted || isRevealed}
                  className={`flex min-h-[72px] items-center justify-between rounded-2xl p-4 text-left shadow-sm transition-all active:scale-[0.98] disabled:cursor-default ${cardStyle}`}
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-base font-bold shadow-sm">
                      {SHAPES[idx % SHAPES.length]}
                    </span>
                    <span className="text-sm font-semibold text-[var(--text-primary)] sm:text-base">
                      {opt}
                    </span>
                  </div>

                  {isRevealed && isCorrectAnswer && (
                    <CheckCircle2 className="h-6 w-6 shrink-0 text-emerald-600" />
                  )}
                  {isRevealed && isWrongChoice && (
                    <XCircle className="h-6 w-6 shrink-0 text-red-600" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Submission Status & Feedback */}
          <AnimatePresence>
            {hasSubmitted && !isRevealed && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-center shadow-sm">
                <span className="flex items-center justify-center gap-2 text-sm font-bold text-[var(--accent-royal)]">
                  <CheckCircle2 className="h-5 w-5" /> Answer locked in! Waiting for others to finish...
                </span>
              </motion.div>
            )}

            {isRevealed && (
              <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-md">
                {(() => {
                  const isCorrect = Array.isArray(q.correct_answer)
                    ? q.correct_answer.includes(selectedOption || '')
                    : q.correct_answer === selectedOption;

                  return (
                    <div className="space-y-4">
                      <div className="flex items-center gap-3">
                        {isCorrect ? (
                          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                            <Sparkles className="h-6 w-6" />
                          </div>
                        ) : (
                          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-blue-700">
                            <HelpCircle className="h-6 w-6" />
                          </div>
                        )}
                        <div>
                          <h4 className="font-display text-lg font-bold text-[var(--text-primary)]">
                            {isCorrect ? 'Excellent job!' : "Not quite — let's learn together!"}
                          </h4>
                          <p className="text-xs text-[var(--text-secondary)]">
                            {isCorrect ? 'You answered correctly!' : 'Review the explanation below to master this concept.'}
                          </p>
                        </div>
                      </div>

                      {q.explanation && (
                        <div className="rounded-2xl bg-[var(--bg-secondary)] p-4 text-sm text-[var(--text-primary)]">
                          <strong className="block font-bold mb-1 text-[var(--text-primary)]">Explanation</strong>
                          {q.explanation}
                        </div>
                      )}
                    </div>
                  );
                })()}
              </motion.div>
            )}
          </AnimatePresence>

        </div>
      )}

    </div>
  );
};

export default LiveQuizParticipantPage;
