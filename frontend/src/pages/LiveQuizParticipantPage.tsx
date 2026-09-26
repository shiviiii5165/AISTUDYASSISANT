import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Clock, CheckCircle2, XCircle, Sparkles, Loader2, Volume2, VolumeX,
  HelpCircle, Trophy, Zap, AlertCircle, ShieldAlert
} from 'lucide-react';
import SEO from '../components/SEO';
import {
  getParticipantState, submitParticipantResponse, recordActivitySignal,
  type StudentRoomState
} from '../lib/liveQuizApi';
import {
  recordPendingAnswer, markAnswerAcked, getPendingAnswers
} from '../lib/liveQuizJournal';
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
  const [isBanned, setIsBanned] = useState<boolean>(false);
  const [banReason, setBanReason] = useState<string>('Removed by teacher');

  const questionStartTimeRef = useRef<number>(Date.now());

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
      } catch (err: any) {
        if (err.response?.status === 403 && err.response?.data?.detail === 'ATTEMPT_REVOKED') {
          setIsBanned(true);
        }
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
        questionStartTimeRef.current = Date.now();
        soundFx.playJoinSound();
      })
      .on('broadcast', { event: 'question:revealed' }, () => {
        fetchState();
      })
      .on('broadcast', { event: 'participant:banned' }, (e: any) => {
        const payload = e.payload || {};
        if (state?.participant?.id && payload.participant_id === state.participant.id) {
          setIsBanned(true);
          setBanReason(payload.reason || 'Removed by teacher');
        }
      })
      .on('broadcast', { event: 'session:ended' }, () => {
        fetchState();
        soundFx.playSessionComplete();
      })
      .subscribe();

    // Polling fallback every 3 seconds for rock-solid sync
    const interval = setInterval(fetchState, 3000);

    return () => {
      supabase.removeChannel(channel);
      clearInterval(interval);
    };
  }, [sessionId, token]);

  // 3. Activity Tracking Listeners (Tab Hidden, Copy attempts)
  useEffect(() => {
    if (!sessionId || !token || isBanned) return;

    const handleVisibility = () => {
      if (document.hidden) {
        recordActivitySignal(sessionId, 'TAB_HIDDEN', token);
      } else {
        recordActivitySignal(sessionId, 'TAB_RETURNED', token);
      }
    };

    const handleCopy = () => {
      recordActivitySignal(sessionId, 'COPY_ATTEMPT', token);
    };

    document.addEventListener('visibilitychange', handleVisibility);
    document.addEventListener('copy', handleCopy);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibility);
      document.removeEventListener('copy', handleCopy);
    };
  }, [sessionId, token, isBanned]);

  // 4. Countdown timer tick
  useEffect(() => {
    if (timeLeft === null || timeLeft <= 0 || state?.is_revealed || isBanned) return;

    if (timeLeft <= 5 && timeLeft > 0) {
      soundFx.playTimerTick();
    }

    const timer = setInterval(() => {
      setTimeLeft((prev) => (prev !== null && prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft, state?.is_revealed, isBanned]);

  // Play sound when revealed
  useEffect(() => {
    if (state?.is_revealed && state.question && selectedOption) {
      const isCorrect = Array.isArray(state.question.correct_answer)
        ? state.question.correct_answer.includes(selectedOption)
        : state.question.correct_answer === selectedOption;

      if (isCorrect) {
        soundFx.playCorrectSound();
      } else {
        soundFx.playWrongSound();
      }
    }
  }, [state?.is_revealed]);

  // 5. Handle Option Selection with IndexedDB Durability Journal (§3)
  const handleSelectOption = async (option: string) => {
    if (!sessionId || !token || !state?.question || state.has_submitted || submitting || isBanned) return;

    const qid = state.question.id;
    const progToken = state.question.progression_token;
    const responseTimeMs = Math.max(0, Date.now() - questionStartTimeRef.current);

    setSelectedOption(option);
    setSubmitting(true);
    soundFx.playClick();

    // 1. Journal to IndexedDB FIRST (Durability guarantee)
    await recordPendingAnswer(sessionId, qid, option, responseTimeMs, progToken);

    try {
      // 2. Dispatch immediately to backend microbatch writer
      const res = await submitParticipantResponse(
        sessionId,
        qid,
        option,
        token,
        progToken,
        responseTimeMs
      );

      // 3. Mark ACKed in IndexedDB once server commits
      await markAnswerAcked(sessionId, qid);

      setState((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          has_submitted: true,
          selected_option_id: option,
          participant: {
            ...prev.participant,
            score: (prev.participant.score || 0) + (res.points_earned || 0),
          },
        };
      });
    } catch (err: any) {
      if (err.response?.status === 403 && err.response?.data?.detail === 'ATTEMPT_REVOKED') {
        setIsBanned(true);
      } else {
        console.warn('[ParticipantView] Network submission error; preserved in local journal for retry', err);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleSound = () => {
    const next = soundFx.toggleMute();
    setIsMuted(next);
  };

  if (loading) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center bg-[var(--bg-primary)]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-[var(--accent-royal)]" />
          <p className="font-semibold text-[var(--text-secondary)]">Connecting to room...</p>
        </div>
      </div>
    );
  }

  // Authoritative Ban Revocation Screen (§11)
  if (isBanned) {
    return (
      <div className="flex min-h-[100dvh] flex-col items-center justify-center bg-red-950/20 px-4 text-center">
        <SEO title="Access Revoked | TeachGenie" description="Participation revoked." />
        <div className="max-w-md rounded-3xl border border-red-500/40 bg-[var(--bg-card)] p-8 shadow-2xl">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-red-100 text-red-600">
            <ShieldAlert className="h-9 w-9" />
          </div>
          <h1 className="font-display text-2xl font-bold text-red-600">ATTEMPT REVOKED</h1>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">
            You have been removed from this live session by the teacher.
          </p>
          <div className="mt-4 rounded-xl bg-red-50 p-3 text-xs font-medium text-red-800">
            Reason: {banReason}
          </div>
          <button
            onClick={() => navigate('/join')}
            className="mt-6 w-full rounded-xl bg-[var(--accent-royal)] py-3 font-semibold text-white shadow-md hover:opacity-90"
          >
            Return to Join Screen
          </button>
        </div>
      </div>
    );
  }

  const isLobby = state?.status === 'LOBBY' || state?.status === 'CREATED';
  const isEnded = state?.status === 'COMPLETED' || state?.status === 'ENDED';
  const q = state?.question;

  return (
    <div className="flex min-h-[100dvh] flex-col bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <SEO title="Live Quiz Session | TeachGenie" description="Participating in live classroom quiz." />

      {/* Top Participant Status Header */}
      <header className="flex items-center justify-between border-b border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--accent-royal)]/15 text-lg font-bold">
            {state?.participant?.avatar_seed?.startsWith('avatar_') ? '🎓' : state?.participant?.avatar_seed || '🎓'}
          </div>
          <div>
            <div className="text-sm font-bold text-[var(--text-primary)]">
              {state?.participant?.display_name || 'Participant'}
            </div>
            <div className="flex items-center gap-2 text-xs font-semibold text-[var(--text-secondary)]">
              <span>{state?.participant?.score || 0} pts</span>
              {(state?.participant?.streak || 0) > 1 && (
                <span className="flex items-center gap-0.5 text-amber-500 font-bold">
                  <Zap className="h-3 w-3 fill-amber-500" /> {state?.participant?.streak} streak
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {timeLeft !== null && state?.status === 'LIVE' && !state?.is_revealed && (
            <div className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-bold shadow-sm ${
              timeLeft <= 5 ? 'bg-red-500 text-white animate-pulse' : 'bg-[var(--bg-hover)] text-[var(--text-primary)]'
            }`}>
              <Clock className="h-4 w-4" />
              <span>{timeLeft}s</span>
            </div>
          )}

          <button
            onClick={handleToggleSound}
            aria-label={isMuted ? 'Unmute' : 'Mute'}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
          >
            {isMuted ? <VolumeX className="h-4 w-4 text-red-500" /> : <Volume2 className="h-4 w-4 text-[var(--accent-green-text)]" />}
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex flex-1 flex-col items-center justify-center p-4 sm:p-6">
        <AnimatePresence mode="wait">
          {/* LOBBY STATE */}
          {isLobby && (
            <motion.div
              key="lobby"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              className="text-center max-w-sm"
            >
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[var(--accent-royal)]/15 text-[var(--accent-royal)]">
                <Clock className="h-8 w-8 animate-pulse" />
              </div>
              <h2 className="font-display text-2xl font-bold">You're in!</h2>
              <p className="mt-2 text-sm text-[var(--text-secondary)]">
                Waiting for the teacher to launch the first question...
              </p>
            </motion.div>
          )}

          {/* ACTIVE QUESTION STATE */}
          {!isLobby && !isEnded && q && (
            <motion.div
              key={q.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="w-full max-w-2xl space-y-6"
            >
              {/* Question Text */}
              <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-sm">
                <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
                  Question {(state?.current_question_index || 0) + 1} of {state?.total_questions}
                </div>
                <h2 className="mt-2 font-display text-xl font-bold sm:text-2xl text-[var(--text-primary)]">
                  {q.question_text}
                </h2>
              </div>

              {/* Answer Option Buttons */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4">
                {q.options?.map((opt, idx) => {
                  const isSelected = selectedOption === opt;
                  const isCorrect = Array.isArray(q.correct_answer)
                    ? q.correct_answer.includes(opt)
                    : q.correct_answer === opt;

                  let borderClass = 'border-[var(--border)] bg-[var(--bg-card)] hover:border-[var(--accent-royal)]';
                  if (isSelected && !state?.is_revealed) {
                    borderClass = 'border-[var(--accent-royal)] bg-[var(--accent-royal)]/10 ring-2 ring-[var(--accent-royal)]';
                  } else if (state?.is_revealed) {
                    if (isCorrect) {
                      borderClass = 'border-green-500 bg-green-500/15 ring-2 ring-green-500';
                    } else if (isSelected && !isCorrect) {
                      borderClass = 'border-red-500 bg-red-500/15 ring-2 ring-red-500';
                    } else {
                      borderClass = 'opacity-40 border-[var(--border)]';
                    }
                  }

                  return (
                    <motion.button
                      key={idx}
                      whileHover={!state.has_submitted ? { scale: 1.01 } : {}}
                      whileTap={!state.has_submitted ? { scale: 0.98 } : {}}
                      disabled={state.has_submitted || state.is_revealed || submitting}
                      onClick={() => handleSelectOption(opt)}
                      className={`flex items-center gap-3 rounded-2xl border-2 p-4 text-left transition-all shadow-sm ${borderClass}`}
                    >
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--bg-hover)] text-base font-bold">
                        {SHAPES[idx % SHAPES.length]}
                      </div>
                      <span className="font-semibold text-base flex-1">{opt}</span>
                    </motion.button>
                  );
                })}
              </div>

              {/* Revealed Feedback */}
              {state?.is_revealed && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-sm space-y-2"
                >
                  <div className="flex items-center gap-2 font-bold text-sm">
                    <Sparkles className="h-4 w-4 text-[var(--accent-royal)]" />
                    <span>Explanation</span>
                  </div>
                  <p className="text-sm text-[var(--text-secondary)]">
                    {q.explanation || 'Good effort! Pay attention to the teacher for key concepts.'}
                  </p>
                </motion.div>
              )}
            </motion.div>
          )}

          {/* COMPLETED STATE */}
          {isEnded && (
            <motion.div
              key="ended"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center max-w-sm rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-8 shadow-xl"
            >
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-500/15 text-amber-500">
                <Trophy className="h-8 w-8" />
              </div>
              <h2 className="font-display text-2xl font-bold">Quiz Complete!</h2>
              <p className="mt-1 text-sm text-[var(--text-secondary)]">Great job participating!</p>
              <div className="my-6 rounded-2xl bg-[var(--bg-hover)] p-4">
                <div className="text-xs uppercase font-bold tracking-wider text-[var(--text-muted)]">Final Score</div>
                <div className="text-4xl font-black text-[var(--accent-royal)] mt-1">
                  {state?.participant?.score || 0}
                </div>
              </div>
              <button
                onClick={() => navigate('/join')}
                className="w-full rounded-xl bg-[var(--accent-royal)] py-3 font-semibold text-white shadow-md hover:opacity-90"
              >
                Join Another Room
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
};

export default LiveQuizParticipantPage;
