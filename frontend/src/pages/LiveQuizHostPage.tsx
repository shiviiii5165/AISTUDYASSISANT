import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users, Play, CheckCircle2, AlertTriangle, Clock,
  ArrowRight, Eye, Pause, RotateCcw, X, Volume2, VolumeX,
  Share2, Check, Sparkles, Lightbulb, BarChart3, HelpCircle, Layers
} from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import {
  startLiveSession, getLiveSessionHostView, advanceNextQuestion,
  revealCurrentQuestion, pauseLiveSession, resumeLiveSession,
  endLiveSession, triggerIntervention, type LiveQuizSession, type LiveParticipant, type InterventionResult
} from '../lib/liveQuizApi';
import { supabase } from '../lib/supabase';
import { soundFx } from '../lib/soundFx';

const LiveQuizHostPage: React.FC = () => {
  const { quizId } = useParams<{ quizId: string }>();
  const navigate = useNavigate();

  const [session, setSession] = useState<LiveQuizSession | null>(null);
  const [participants, setParticipants] = useState<LiveParticipant[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState<any>(null);
  const [responseCount, setResponseCount] = useState<number>(0);
  const [optionDistribution, setOptionDistribution] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Controls
  const [copiedCode, setCopiedCode] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState<boolean>(soundFx.isMuted());
  const [showEndModal, setShowEndModal] = useState<boolean>(false);

  // Real-time timer
  const [timeLeft, setTimeLeft] = useState<number | null>(null);

  // Intervention
  const [interventionResult, setInterventionResult] = useState<InterventionResult | null>(null);
  const [interventionLoading, setInterventionLoading] = useState<boolean>(false);

  const prevParticipantCount = useRef<number>(0);

  // 1. Initialize or Load Live Session
  useEffect(() => {
    if (!quizId) return;

    const init = async () => {
      try {
        setLoading(true);
        // Start or recover session for this quiz
        const data = await startLiveSession(quizId, {
          mode: 'teacher_led',
          timer_seconds: 30,
          speed_bonus: false,
        });
        setSession(data);
        await refreshHostView(data.id);
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message || 'Failed to initialize live session');
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [quizId]);

  const refreshHostView = async (sessionId: string) => {
    try {
      const data = await getLiveSessionHostView(sessionId);
      setSession(data.session);
      setParticipants(data.participants || []);
      setCurrentQuestion(data.current_question);
      setResponseCount(data.current_response_count || 0);
      setOptionDistribution(data.option_distribution || {});

      // Sound trigger on new participant
      if ((data.participants?.length || 0) > prevParticipantCount.current) {
        soundFx.playJoinSound();
        prevParticipantCount.current = data.participants.length;
      }

      // Calculate timer if active
      if (data.session.current_question_deadline && data.session.status === 'LIVE') {
        const deadline = new Date(data.session.current_question_deadline).getTime();
        const diff = Math.max(0, Math.floor((deadline - Date.now()) / 1000));
        setTimeLeft(diff);
      }
    } catch (e) {
      console.error('[HostView] Refresh failed', e);
    }
  };

  // 2. Realtime Subscription & Polling Backup
  useEffect(() => {
    if (!session?.id) return;
    const sid = session.id;

    // Realtime channel listener for room events
    const channel = supabase.channel(`session:${sid}`);
    channel
      .on('broadcast', { event: 'participant:joined' }, () => {
        refreshHostView(sid);
      })
      .on('broadcast', { event: 'response:submitted' }, () => {
        refreshHostView(sid);
      })
      .subscribe();

    // Polling fallback every 3 seconds for rock-solid sync
    const interval = setInterval(() => {
      refreshHostView(sid);
    }, 3000);

    return () => {
      supabase.removeChannel(channel);
      clearInterval(interval);
    };
  }, [session?.id]);

  // 3. Countdown timer tick
  useEffect(() => {
    if (timeLeft === null || timeLeft <= 0 || session?.status !== 'LIVE') return;

    if (timeLeft <= 5 && timeLeft > 0) {
      soundFx.playTimerTick();
    }

    const timer = setInterval(() => {
      setTimeLeft((prev) => (prev !== null && prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft, session?.status]);

  // Actions
  const handleNext = async () => {
    if (!session) return;
    try {
      setActionLoading('next');
      const updated = await advanceNextQuestion(session.id);
      setSession(updated);
      await refreshHostView(session.id);

      if (updated.status === 'COMPLETED') {
        soundFx.playSessionComplete();
        navigate(`/live/${session.id}/report`);
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to advance question');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReveal = async () => {
    if (!session) return;
    try {
      setActionLoading('reveal');
      const updated = await revealCurrentQuestion(session.id);
      setSession(updated);
      await refreshHostView(session.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to reveal question');
    } finally {
      setActionLoading(null);
    }
  };

  const handlePauseToggle = async () => {
    if (!session) return;
    try {
      setActionLoading('pause');
      if (session.status === 'PAUSED') {
        const updated = await resumeLiveSession(session.id);
        setSession(updated);
      } else {
        const updated = await pauseLiveSession(session.id);
        setSession(updated);
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to toggle pause');
    } finally {
      setActionLoading(null);
    }
  };

  const handleEnd = async () => {
    if (!session) return;
    try {
      setActionLoading('end');
      await endLiveSession(session.id);
      soundFx.playSessionComplete();
      navigate(`/live/${session.id}/report`);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to end session');
    } finally {
      setActionLoading(null);
      setShowEndModal(false);
    }
  };

  const handleTriggerIntervention = async (type: 'explain' | 'visual' | 'example' | 'followup') => {
    if (!session) return;
    try {
      setInterventionLoading(true);
      const res = await triggerIntervention(session.id, type, currentQuestion?.id);
      setInterventionResult(res);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Intervention call failed');
    } finally {
      setInterventionLoading(false);
    }
  };

  const copyJoinLink = () => {
    if (!session) return;
    const url = `${window.location.origin}/join?code=${session.join_code}`;
    navigator.clipboard.writeText(url);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  if (loading) {
    return (
      <AppLayout title="Live Classroom">
        <div className="flex h-[80vh] items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="h-10 w-10 animate-spin rounded-full border-3 border-[var(--accent-royal)] border-t-transparent" />
            <p className="font-semibold text-[var(--text-secondary)]">Initializing Live Room...</p>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (error || !session) {
    return (
      <AppLayout title="Live Classroom">
        <div className="mx-auto mt-12 max-w-lg rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
          <AlertTriangle className="mx-auto h-8 w-8 text-red-600" />
          <h2 className="mt-2 text-lg font-bold text-red-900">Live Session Error</h2>
          <p className="mt-1 text-sm text-red-800">{error || 'Session could not be reached'}</p>
        </div>
      </AppLayout>
    );
  }

  const isLobby = session.status === 'LOBBY';
  const isRevealed = session.settings?.question_revealed;
  const totalQuestions = session.total_questions || 1;
  const currentQIndex = session.current_question_index || 0;
  const responsePct = participants.length > 0 ? Math.round((responseCount / participants.length) * 100) : 0;

  // Check if class struggled on current question (accuracy < 50% upon reveal)
  const isClassStruggling = isRevealed && optionDistribution && currentQuestion && (
    (() => {
      const correctOpt = currentQuestion.correct_answer;
      const correctCount = optionDistribution[correctOpt] || 0;
      return responseCount > 0 && (correctCount / responseCount) < 0.50;
    })()
  );

  return (
    <AppLayout title="Live Classroom Host">
      <SEO title="Live Room Host | TeachGenie" description="Host a real-time interactive quiz session." />

      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
        
        {/* Top Navigation & Status Bar */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className={`inline-block h-3 w-3 rounded-full ${session.status === 'LIVE' ? 'animate-pulse bg-emerald-500' : session.status === 'PAUSED' ? 'bg-amber-500' : 'bg-[var(--accent-royal)]'}`} />
              <span className="font-mono text-sm font-bold uppercase tracking-wider text-[var(--text-primary)]">
                {session.status}
              </span>
            </div>
            <div className="hidden h-5 w-px bg-[var(--border)] sm:block" />
            <div className="flex items-center gap-2 font-mono text-sm">
              <span className="text-[var(--text-muted)]">Code:</span>
              <span className="rounded bg-[var(--accent-baby)]/30 px-2.5 py-1 font-bold tracking-widest text-[var(--accent-royal)]">
                {session.join_code}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsMuted(soundFx.toggleMute())}
              aria-label={isMuted ? 'Unmute' : 'Mute'}
              className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
            >
              {isMuted ? <VolumeX className="h-4 w-4 text-red-500" /> : <Volume2 className="h-4 w-4" />}
            </button>
            <button
              onClick={copyJoinLink}
              className="flex items-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-xs font-semibold text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
            >
              {copiedCode ? <Check className="h-4 w-4 text-emerald-600" /> : <Share2 className="h-4 w-4" />}
              <span>{copiedCode ? 'Copied' : 'Share Link'}</span>
            </button>
            <button
              onClick={() => setShowEndModal(true)}
              className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-100"
            >
              End Session
            </button>
          </div>
        </div>

        {/* ─── VIEW 1: LOBBY SCREEN ────────────────────────────────────────── */}
        {isLobby && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
            <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-8 text-center shadow-lg sm:p-12">
              <span className="mb-2 inline-block rounded-full bg-[var(--accent-baby)]/40 px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-[var(--accent-royal)]">
                Classroom Room Ready
              </span>
              <h1 className="font-display text-4xl font-bold tracking-tight text-[var(--text-primary)] sm:text-6xl">
                {session.join_code}
              </h1>
              <p className="mt-3 text-base text-[var(--text-secondary)]">
                Students go to <strong className="text-[var(--accent-royal)]">{window.location.host}/join</strong> and enter this code
              </p>

              <div className="mt-8 flex justify-center">
                <button
                  onClick={handleNext}
                  disabled={actionLoading === 'next'}
                  className="flex items-center gap-3 rounded-full bg-[var(--accent-royal)] px-10 py-4 text-base font-bold text-white shadow-xl shadow-[var(--accent-royal)]/30 transition-all hover:bg-[var(--accent-green-deep)] active:scale-95 disabled:opacity-50"
                >
                  <Play className="h-5 w-5 fill-current" />
                  <span>Start Live Session ({participants.length} Joined)</span>
                </button>
              </div>
            </div>

            {/* Live Participant Roster */}
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-[var(--accent-royal)]" />
                  <h3 className="text-base font-bold text-[var(--text-primary)]">
                    Joined Students ({participants.length})
                  </h3>
                </div>
                <span className="text-xs font-semibold text-[var(--text-muted)]">
                  Live presence synced
                </span>
              </div>

              {participants.length === 0 ? (
                <div className="rounded-xl border border-dashed border-[var(--border)] p-8 text-center text-sm text-[var(--text-muted)]">
                  Waiting for students to join with code <strong className="text-[var(--text-primary)]">{session.join_code}</strong>...
                </div>
              ) : (
                <div className="flex flex-wrap gap-2.5">
                  {participants.map((p) => (
                    <motion.div
                      key={p.id}
                      initial={{ scale: 0.8, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      className="flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--bg-secondary)] px-4 py-2 text-sm font-semibold text-[var(--text-primary)] shadow-sm"
                    >
                      <span className="text-lg">{p.avatar_seed || '👤'}</span>
                      <span>{p.display_name}</span>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* ─── VIEW 2: ACTIVE QUESTION SCREEN ──────────────────────────────── */}
        {!isLobby && currentQuestion && (
          <div className="space-y-6">
            
            {/* Header / Progress / Timer */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="flex flex-col justify-center rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-sm">
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">Progress</span>
                <span className="font-display text-xl font-bold text-[var(--text-primary)]">
                  Question {currentQIndex + 1} of {totalQuestions}
                </span>
              </div>

              <div className="flex flex-col justify-center rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-sm">
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">Responses</span>
                <div className="flex items-center justify-between">
                  <span className="font-display text-xl font-bold text-[var(--text-primary)]">
                    {responseCount} / {participants.length}
                  </span>
                  <span className="rounded bg-[var(--accent-baby)]/30 px-2 py-0.5 text-xs font-bold text-[var(--accent-royal)]">
                    {responsePct}%
                  </span>
                </div>
                <div className="mt-2 h-1.5 w-full rounded-full bg-[var(--bg-secondary)]">
                  <div className="h-1.5 rounded-full bg-[var(--accent-royal)] transition-all duration-300" style={{ width: `${responsePct}%` }} />
                </div>
              </div>

              <div className="flex items-center justify-between rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-sm">
                <div>
                  <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">Time Left</span>
                  <div className="font-mono text-2xl font-bold text-[var(--text-primary)]">
                    {timeLeft !== null ? `${timeLeft}s` : 'Untimed'}
                  </div>
                </div>
                <Clock className={`h-8 w-8 ${timeLeft !== null && timeLeft <= 5 ? 'animate-bounce text-red-600' : 'text-[var(--accent-royal)]'}`} />
              </div>
            </div>

            {/* Main Question Card */}
            <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-md md:p-8">
              <div className="mb-4 flex items-center justify-between">
                <span className="rounded-full bg-[var(--bg-secondary)] px-3 py-1 text-xs font-bold uppercase text-[var(--text-secondary)]">
                  {currentQuestion.type || 'MCQ'} • {currentQuestion.concept_id || 'General'}
                </span>
                {isRevealed && (
                  <span className="flex items-center gap-1 text-xs font-bold text-emerald-600">
                    <CheckCircle2 className="h-4 w-4" /> Answer Revealed
                  </span>
                )}
              </div>

              <h2 className="font-display text-2xl font-bold text-[var(--text-primary)] sm:text-3xl">
                {currentQuestion.question_text}
              </h2>

              {/* Real-time Response Distribution Bars */}
              <div className="mt-8 space-y-3">
                {currentQuestion.options?.map((opt: string, idx: number) => {
                  const count = optionDistribution[opt] || 0;
                  const isCorrect = isRevealed && (Array.isArray(currentQuestion.correct_answer) ? currentQuestion.correct_answer.includes(opt) : currentQuestion.correct_answer === opt);
                  const pct = responseCount > 0 ? Math.round((count / responseCount) * 100) : 0;

                  return (
                    <div key={idx} className={`relative overflow-hidden rounded-xl border p-4 transition-all ${isCorrect ? 'border-emerald-500 bg-emerald-50/70 ring-2 ring-emerald-500' : 'border-[var(--border)] bg-[var(--bg-card)]'}`}>
                      {/* Background fill based on response count */}
                      <div
                        className={`absolute inset-y-0 left-0 transition-all duration-500 ${isCorrect ? 'bg-emerald-200/40' : 'bg-[var(--accent-baby)]/25'}`}
                        style={{ width: `${pct}%` }}
                      />

                      <div className="relative flex items-center justify-between gap-4">
                        <div className="flex items-center gap-3">
                          <span className={`flex h-7 w-7 items-center justify-center rounded-lg font-bold text-xs ${isCorrect ? 'bg-emerald-600 text-white' : 'bg-[var(--bg-secondary)] text-[var(--text-primary)]'}`}>
                            {String.fromCharCode(65 + idx)}
                          </span>
                          <span className={`text-base font-semibold ${isCorrect ? 'text-emerald-900 font-bold' : 'text-[var(--text-primary)]'}`}>
                            {opt}
                          </span>
                        </div>

                        <div className="flex items-center gap-3 font-mono">
                          <span className="text-sm font-bold text-[var(--text-secondary)]">
                            {count} votes ({pct}%)
                          </span>
                          {isCorrect && <CheckCircle2 className="h-5 w-5 text-emerald-600" />}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Explanation upon reveal */}
              {isRevealed && currentQuestion.explanation && (
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-6 rounded-2xl bg-[var(--bg-secondary)] p-4 text-sm">
                  <strong className="block font-bold text-[var(--text-primary)]">Explanation:</strong>
                  <p className="mt-1 text-[var(--text-secondary)]">{currentQuestion.explanation}</p>
                </motion.div>
              )}
            </div>

            {/* AI Learning Intelligence Banner (Triggers if class accuracy < 50%) */}
            {isClassStruggling && (
              <motion.div
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="rounded-2xl border border-amber-300 bg-amber-50 p-6 shadow-sm"
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="mt-0.5 h-6 w-6 text-amber-700 shrink-0" />
                    <div>
                      <h4 className="font-bold text-amber-950">
                        Class Misconception Detected ({currentQuestion.concept_id || 'Concept'})
                      </h4>
                      <p className="text-xs text-amber-800">
                        Less than 50% answered correctly. Trigger a targeted remediation right now before moving forward.
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => handleTriggerIntervention('explain')}
                      disabled={interventionLoading}
                      className="flex items-center gap-1.5 rounded-xl bg-amber-700 px-3.5 py-2 text-xs font-bold text-white shadow hover:bg-amber-800 disabled:opacity-50"
                    >
                      <Lightbulb className="h-3.5 w-3.5" /> Explain Now
                    </button>
                    <button
                      onClick={() => handleTriggerIntervention('visual')}
                      disabled={interventionLoading}
                      className="flex items-center gap-1.5 rounded-xl bg-blue-700 px-3.5 py-2 text-xs font-bold text-white shadow hover:bg-blue-800 disabled:opacity-50"
                    >
                      <Layers className="h-3.5 w-3.5" /> Show Visual
                    </button>
                    <button
                      onClick={() => handleTriggerIntervention('example')}
                      disabled={interventionLoading}
                      className="flex items-center gap-1.5 rounded-xl bg-purple-700 px-3.5 py-2 text-xs font-bold text-white shadow hover:bg-purple-800 disabled:opacity-50"
                    >
                      <Sparkles className="h-3.5 w-3.5" /> Give Example
                    </button>
                    <button
                      onClick={() => handleTriggerIntervention('followup')}
                      disabled={interventionLoading}
                      className="flex items-center gap-1.5 rounded-xl bg-teal-700 px-3.5 py-2 text-xs font-bold text-white shadow hover:bg-teal-800 disabled:opacity-50"
                    >
                      <HelpCircle className="h-3.5 w-3.5" /> Ask Follow-up
                    </button>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Host Control Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-sm">
              <div className="flex items-center gap-2">
                <button
                  onClick={handlePauseToggle}
                  className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-4 py-2.5 text-sm font-bold text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
                >
                  <Pause className="h-4 w-4" />
                  <span>{session.status === 'PAUSED' ? 'Resume Session' : 'Pause Room'}</span>
                </button>
              </div>

              <div className="flex items-center gap-3">
                {!isRevealed ? (
                  <button
                    onClick={handleReveal}
                    disabled={actionLoading === 'reveal'}
                    className="flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-3 text-sm font-bold text-white shadow-md hover:bg-emerald-700 active:scale-95 disabled:opacity-50"
                  >
                    <Eye className="h-4 w-4" />
                    <span>Reveal Answer</span>
                  </button>
                ) : (
                  <button
                    onClick={handleNext}
                    disabled={actionLoading === 'next'}
                    className="flex items-center gap-2 rounded-xl bg-[var(--accent-royal)] px-8 py-3 text-sm font-bold text-white shadow-lg shadow-[var(--accent-royal)]/25 hover:bg-[var(--accent-green-deep)] active:scale-95 disabled:opacity-50"
                  >
                    <span>{currentQIndex === totalQuestions - 1 ? 'Finish Session' : 'Next Question'}</span>
                    <ArrowRight className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>

          </div>
        )}

      </div>

      {/* ─── MODAL: AI Intervention Output ──────────────────────────────── */}
      <AnimatePresence>
        {interventionResult && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="w-full max-w-2xl rounded-3xl bg-white p-6 shadow-2xl">
              <div className="flex items-center justify-between border-b pb-3">
                <h3 className="font-display text-lg font-bold text-[var(--text-primary)]">
                  Classroom Remediation: {interventionResult.concept}
                </h3>
                <button onClick={() => setInterventionResult(null)} className="rounded-lg p-1 text-[var(--text-muted)] hover:bg-[var(--bg-hover)]">
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="mt-4 max-h-[60vh] overflow-y-auto space-y-4">
                {interventionResult.type === 'visual' && (
                  <div className="space-y-4">
                    {interventionResult.svg && (
                      <div className="rounded-2xl border p-4 bg-slate-50 flex justify-center" dangerouslySetInnerHTML={{ __html: interventionResult.svg }} />
                    )}
                    {interventionResult.comparison && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                          <h4 className="font-bold text-emerald-900 text-sm">{interventionResult.comparison.correct_concept.heading}</h4>
                          <p className="mt-1 text-xs text-emerald-800 font-semibold">{interventionResult.comparison.correct_concept.text}</p>
                          <p className="mt-2 text-xs text-emerald-700">{interventionResult.comparison.correct_concept.reason}</p>
                        </div>
                        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
                          <h4 className="font-bold text-red-900 text-sm">{interventionResult.comparison.common_misconception.heading}</h4>
                          <p className="mt-1 text-xs text-red-800 font-semibold">{interventionResult.comparison.common_misconception.text}</p>
                          <p className="mt-2 text-xs text-red-700">{interventionResult.comparison.common_misconception.pitfall}</p>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {interventionResult.type !== 'visual' && (
                  <div className="rounded-2xl bg-[var(--bg-secondary)] p-5 text-sm text-[var(--text-primary)] leading-relaxed whitespace-pre-wrap">
                    {interventionResult.content || interventionResult.raw_content}
                  </div>
                )}
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setInterventionResult(null)}
                  className="rounded-xl bg-[var(--accent-royal)] px-6 py-2.5 text-sm font-bold text-white hover:bg-[var(--accent-green-deep)]"
                >
                  Continue Teaching
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ─── MODAL: Confirm End Session ─────────────────────────────────── */}
      <AnimatePresence>
        {showEndModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }} className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
              <h3 className="font-display text-lg font-bold text-[var(--text-primary)]">End live session for all students?</h3>
              <p className="mt-2 text-sm text-[var(--text-secondary)]">
                This will conclude the quiz, compute mastery rollups, and transition everyone to the results screen.
              </p>
              <div className="mt-6 flex justify-end gap-3">
                <button onClick={() => setShowEndModal(false)} className="rounded-xl px-4 py-2 text-sm font-semibold text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]">
                  Cancel
                </button>
                <button
                  onClick={handleEnd}
                  disabled={actionLoading === 'end'}
                  className="rounded-xl bg-red-600 px-5 py-2 text-sm font-bold text-white hover:bg-red-700"
                >
                  End Session
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </AppLayout>
  );
};

export default LiveQuizHostPage;
