import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users, Play, CheckCircle2, AlertTriangle, Clock,
  ArrowRight, Eye, Pause, RotateCcw, X, Volume2, VolumeX,
  Share2, Check, Sparkles, Lightbulb, BarChart3, HelpCircle, Layers,
  ShieldAlert, ShieldCheck, Search, Filter, ChevronRight, Activity, Ban
} from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import {
  startLiveSession, getLiveSessionHostView, getMonitoringSummary,
  getPaginatedParticipants, getParticipantDetail, banParticipant, unbanParticipant,
  advanceNextQuestion, revealCurrentQuestion, pauseLiveSession, resumeLiveSession,
  endLiveSession, triggerIntervention,
  type LiveQuizSession, type LiveParticipant, type MonitoringSummary, type InterventionResult
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

  // Monitoring summary state
  const [summary, setSummary] = useState<MonitoringSummary | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [bannedFilter, setBannedFilter] = useState<boolean>(false);
  const [cursor, setCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState<boolean>(false);

  // Student Detail Drawer
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);
  const [studentDetail, setStudentDetail] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);

  // Ban Modal
  const [banModalStudent, setBanModalStudent] = useState<LiveParticipant | null>(null);
  const [banReasonInput, setBanReasonInput] = useState<string>('Suspicious tab activity / unauthorized actions');
  const [banLoading, setBanLoading] = useState<boolean>(false);

  // Controls
  const [copiedCode, setCopiedCode] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState<boolean>(soundFx.isMuted());
  const [showEndModal, setShowEndModal] = useState<boolean>(false);
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
      const [hostData, summaryData, paginatedData] = await Promise.all([
        getLiveSessionHostView(sessionId),
        getMonitoringSummary(sessionId).catch(() => null),
        getPaginatedParticipants(sessionId, {
          limit: 100,
          search: searchQuery || undefined,
          risk: riskFilter !== 'all' ? riskFilter : undefined,
          banned_only: bannedFilter || undefined,
        }).catch(() => null),
      ]);

      setSession(hostData.session);
      setCurrentQuestion(hostData.current_question);
      setResponseCount(hostData.current_response_count || 0);
      setOptionDistribution(hostData.option_distribution || {});

      if (summaryData) setSummary(summaryData);
      if (paginatedData) {
        setParticipants(paginatedData.items);
        setHasMore(paginatedData.has_more);
        setCursor(paginatedData.next_cursor);
      } else {
        setParticipants(hostData.participants || []);
      }

      // Sound trigger on new participant
      const totalP = summaryData?.total_participants || hostData.participants?.length || 0;
      if (totalP > prevParticipantCount.current) {
        soundFx.playJoinSound();
        prevParticipantCount.current = totalP;
      }

      // Calculate timer if active
      if (hostData.session.current_question_deadline && hostData.session.status === 'LIVE') {
        const deadline = new Date(hostData.session.current_question_deadline).getTime();
        const diff = Math.max(0, Math.floor((deadline - Date.now()) / 1000));
        setTimeLeft(diff);
      }
    } catch (e) {
      console.error('[HostView] Refresh failed', e);
    }
  };

  // 2. Realtime Subscriptions with Aggregated Updates (§5)
  useEffect(() => {
    if (!session?.id) return;
    const sid = session.id;

    const channel = supabase.channel(`session:${sid}`);
    channel
      .on('broadcast', { event: 'participant:joined' }, () => {
        refreshHostView(sid);
      })
      .on('broadcast', { event: 'session:aggregated_update' }, (e: any) => {
        const payload = e.payload || {};
        if (payload.option_counts) {
          setOptionDistribution(prev => ({ ...prev, ...payload.option_counts }));
        }
        if (payload.answered_count_delta) {
          setResponseCount(prev => prev + payload.answered_count_delta);
        }
      })
      .on('broadcast', { event: 'participant:banned' }, () => {
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
  }, [session?.id, searchQuery, riskFilter, bannedFilter]);

  // 3. Countdown timer tick
  useEffect(() => {
    if (timeLeft === null || timeLeft <= 0 || session?.status !== 'LIVE') return;

    const timer = setInterval(() => {
      setTimeLeft(prev => (prev !== null && prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft, session?.status]);

  // 4. Open Student Detail Drawer
  const handleOpenStudentDetail = async (studentId: string) => {
    if (!session?.id) return;
    setSelectedStudentId(studentId);
    setDetailLoading(true);
    try {
      const data = await getParticipantDetail(session.id, studentId);
      setStudentDetail(data);
    } catch (err) {
      console.error('Failed to load student detail', err);
    } finally {
      setDetailLoading(false);
    }
  };

  // 5. Authoritative Ban & Unban Actions
  const handleConfirmBan = async () => {
    if (!session?.id || !banModalStudent) return;
    setBanLoading(true);
    try {
      await banParticipant(session.id, banModalStudent.id, banReasonInput);
      setBanModalStudent(null);
      await refreshHostView(session.id);
    } catch (err) {
      alert('Failed to ban participant');
    } finally {
      setBanLoading(false);
    }
  };

  const handleUnban = async (participantId: string) => {
    if (!session?.id) return;
    try {
      await unbanParticipant(session.id, participantId);
      await refreshHostView(session.id);
    } catch (err) {
      alert('Failed to unban participant');
    }
  };

  // Host Action Handlers
  const handleNextQuestion = async () => {
    if (!session?.id) return;
    setActionLoading('next');
    try {
      const res = await advanceNextQuestion(session.id);
      setSession(res);
      setInterventionResult(null);
      await refreshHostView(session.id);
      soundFx.playJoinSound();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to advance question');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReveal = async () => {
    if (!session?.id) return;
    setActionLoading('reveal');
    try {
      const res = await revealCurrentQuestion(session.id);
      setSession(res);
      await refreshHostView(session.id);
      soundFx.playCorrectSound();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to reveal answer');
    } finally {
      setActionLoading(null);
    }
  };

  const handlePauseResume = async () => {
    if (!session?.id) return;
    const isPaused = session.status === 'PAUSED';
    setActionLoading('pause');
    try {
      const res = isPaused
        ? await resumeLiveSession(session.id)
        : await pauseLiveSession(session.id);
      setSession(res);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to toggle pause');
    } finally {
      setActionLoading(null);
    }
  };

  const handleEndSession = async () => {
    if (!session?.id) return;
    setActionLoading('end');
    try {
      await endLiveSession(session.id);
      soundFx.playSessionComplete();
      navigate(`/live-quiz/report/${session.id}`);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to end session');
    } finally {
      setActionLoading(null);
    }
  };

  const handleTriggerIntervention = async (type: 'explain' | 'visual' | 'example' | 'followup') => {
    if (!session?.id) return;
    setInterventionLoading(true);
    try {
      const res = await triggerIntervention(session.id, type, currentQuestion?.id);
      setInterventionResult(res);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Intervention trigger failed');
    } finally {
      setInterventionLoading(false);
    }
  };

  const handleCopyCode = () => {
    if (!session?.join_code) return;
    navigator.clipboard.writeText(session.join_code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  if (loading) {
    return (
      <AppLayout title="Live Quiz Host Dashboard">
        <div className="flex h-[80vh] items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <Clock className="h-8 w-8 animate-spin text-[var(--accent-royal)]" />
            <p className="font-semibold text-[var(--text-secondary)]">Initializing live classroom...</p>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (error || !session) {
    return (
      <AppLayout title="Live Quiz Host Dashboard">
        <div className="mx-auto mt-12 max-w-lg rounded-2xl border border-amber-200 bg-amber-50 p-6 text-center">
          <AlertTriangle className="mx-auto h-8 w-8 text-amber-900" />
          <h2 className="mt-2 text-lg font-bold text-amber-900">Session Error</h2>
          <p className="mt-1 text-sm text-amber-900">{error || 'Could not load session'}</p>
          <button
            onClick={() => navigate('/quizzes')}
            className="mt-4 rounded-xl bg-[var(--accent-royal)] px-4 py-2 font-semibold text-white"
          >
            Back to Quizzes
          </button>
        </div>
      </AppLayout>
    );
  }

  const isLobby = session.status === 'LOBBY' || session.status === 'CREATED';
  const isRevealed = session.settings?.question_revealed;
  const totalStudents = summary?.total_participants || participants.length;

  return (
    <AppLayout title="Live Classroom Control Center">
      <SEO title="Live Quiz Host | LearnByGenie" description="Live classroom monitoring and moderation center." />

      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 space-y-6">

        {/* ─── Top Room Control Header ─── */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-sm">
          <div>
            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-0.5 text-xs font-bold uppercase tracking-wider ${
                session.status === 'LIVE' ? 'bg-green-100 text-green-800' :
                session.status === 'PAUSED' ? 'bg-amber-100 text-amber-800' :
                'bg-[var(--accent-royal)]/15 text-[var(--accent-royal)]'
              }`}>
                <span className="h-2 w-2 rounded-full bg-current animate-pulse" />
                {session.status}
              </span>
              <span className="text-xs text-[var(--text-muted)] font-semibold">Teacher Control View</span>
            </div>

            <h1 className="mt-2 font-display text-2xl sm:text-3xl font-bold text-[var(--text-primary)]">
              Room PIN: <span className="font-mono tracking-widest text-[var(--accent-royal)]">{session.join_code}</span>
            </h1>
          </div>

          {/* Action Button Bar */}
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={handleCopyCode}
              className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] px-4 py-2.5 text-sm font-semibold hover:border-[var(--accent-royal)]"
            >
              {copiedCode ? <Check className="h-4 w-4 text-green-600" /> : <Share2 className="h-4 w-4" />}
              <span>{copiedCode ? 'Copied PIN' : 'Share PIN'}</span>
            </button>

            {isLobby ? (
              <button
                onClick={handleNextQuestion}
                disabled={actionLoading === 'next'}
                className="flex items-center gap-2 rounded-xl bg-[var(--accent-royal)] px-6 py-2.5 text-sm font-bold text-white shadow-md hover:opacity-90"
              >
                <Play className="h-4 w-4 fill-white" />
                <span>Start First Question</span>
              </button>
            ) : (
              <>
                <button
                  onClick={handlePauseResume}
                  disabled={actionLoading === 'pause'}
                  className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] px-4 py-2.5 text-sm font-semibold"
                >
                  <Pause className="h-4 w-4" />
                  <span>{session.status === 'PAUSED' ? 'Resume' : 'Pause'}</span>
                </button>

                {!isRevealed ? (
                  <button
                    onClick={handleReveal}
                    disabled={actionLoading === 'reveal'}
                    className="flex items-center gap-2 rounded-xl bg-amber-600 px-5 py-2.5 text-sm font-bold text-white shadow-md hover:bg-amber-700"
                  >
                    <Eye className="h-4 w-4" />
                    <span>Reveal Answer</span>
                  </button>
                ) : (
                  <button
                    onClick={handleNextQuestion}
                    disabled={actionLoading === 'next'}
                    className="flex items-center gap-2 rounded-xl bg-[var(--accent-royal)] px-5 py-2.5 text-sm font-bold text-white shadow-md hover:opacity-90"
                  >
                    <span>Next Question</span>
                    <ArrowRight className="h-4 w-4" />
                  </button>
                )}

                <button
                  onClick={() => setShowEndModal(true)}
                  className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm font-bold text-amber-900 hover:bg-amber-100"
                >
                  <X className="h-4 w-4" />
                  <span>End Session</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* ─── Summary Metrics Ribbon (§8) ─── */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-center">
            <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">Total</div>
            <div className="text-2xl font-black text-[var(--text-primary)] mt-1">{totalStudents}</div>
          </div>
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-center">
            <div className="text-xs font-bold uppercase tracking-wider text-green-600">Active</div>
            <div className="text-2xl font-black text-green-600 mt-1">{summary?.active_count ?? totalStudents}</div>
          </div>
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-center">
            <div className="text-xs font-bold uppercase tracking-wider text-blue-600">Answered</div>
            <div className="text-2xl font-black text-blue-600 mt-1">{responseCount}</div>
          </div>
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-center">
            <div className="text-xs font-bold uppercase tracking-wider text-amber-600">Waiting</div>
            <div className="text-2xl font-black text-amber-600 mt-1">{Math.max(0, totalStudents - responseCount)}</div>
          </div>
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-center">
            <div className="text-xs font-bold uppercase tracking-wider text-amber-900">Flagged</div>
            <div className="text-2xl font-black text-amber-900 mt-1">{summary?.flagged_count ?? 0}</div>
          </div>
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-center">
            <div className="text-xs font-bold uppercase tracking-wider text-purple-600">Banned</div>
            <div className="text-2xl font-black text-purple-600 mt-1">{summary?.banned_count ?? 0}</div>
          </div>
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-center">
            <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">Avg Progress</div>
            <div className="text-2xl font-black text-[var(--text-primary)] mt-1">{summary?.average_progress_pct ?? 0}%</div>
          </div>
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-center">
            <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">Avg Speed</div>
            <div className="text-2xl font-black text-[var(--text-primary)] mt-1">{((summary?.average_speed_ms ?? 0) / 1000).toFixed(1)}s</div>
          </div>
        </div>

        {/* ─── Active Question & Live Bar Chart ─── */}
        {!isLobby && currentQuestion && (
          <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-[var(--border)] pb-4">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
                  Question {(session.current_question_index || 0) + 1} of {session.total_questions}
                </span>
                <h2 className="mt-1 font-display text-xl font-bold">{currentQuestion.question_text}</h2>
              </div>
              {timeLeft !== null && session.status === 'LIVE' && !isRevealed && (
                <div className="flex items-center gap-2 rounded-2xl bg-amber-500/15 px-4 py-2 text-amber-500 font-bold">
                  <Clock className="h-5 w-5" />
                  <span>{timeLeft}s remaining</span>
                </div>
              )}
            </div>

            {/* Realtime Bar Chart */}
            <div className="space-y-3">
              <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
                Live Distribution ({responseCount} of {totalStudents} answered)
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {currentQuestion.options?.map((opt: string, idx: number) => {
                  const count = optionDistribution[opt] || 0;
                  const pct = responseCount > 0 ? Math.round((count / responseCount) * 100) : 0;
                  const isCorrect = Array.isArray(currentQuestion.correct_answer)
                    ? currentQuestion.correct_answer.includes(opt)
                    : currentQuestion.correct_answer === opt;

                  return (
                    <div key={idx} className="relative rounded-2xl border border-[var(--border)] bg-[var(--bg-hover)] p-4 overflow-hidden">
                      <div
                        className={`absolute left-0 top-0 bottom-0 opacity-20 transition-all duration-300 ${
                          isRevealed && isCorrect ? 'bg-green-500' : 'bg-[var(--accent-royal)]'
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                      <div className="relative flex items-center justify-between">
                        <span className="font-semibold text-sm">{opt}</span>
                        <div className="flex items-center gap-2 font-mono font-bold text-sm">
                          <span>{count}</span>
                          <span className="text-[var(--text-muted)]">({pct}%)</span>
                          {isRevealed && isCorrect && <CheckCircle2 className="h-4 w-4 text-green-600 shrink-0" />}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Remedial Interventions Bar */}
            <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-[var(--border)]">
              <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
                AI Interventions:
              </span>
              <button
                onClick={() => handleTriggerIntervention('visual')}
                disabled={interventionLoading}
                className="flex items-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] px-3 py-1.5 text-xs font-bold hover:border-[var(--accent-royal)]"
              >
                <Sparkles className="h-3.5 w-3.5 text-purple-600" />
                <span>Visual Flow (0 Tokens)</span>
              </button>
              <button
                onClick={() => handleTriggerIntervention('explain')}
                disabled={interventionLoading}
                className="flex items-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] px-3 py-1.5 text-xs font-bold hover:border-[var(--accent-royal)]"
              >
                <Lightbulb className="h-3.5 w-3.5 text-amber-600" />
                <span>Explain Now</span>
              </button>
              <button
                onClick={() => handleTriggerIntervention('example')}
                disabled={interventionLoading}
                className="flex items-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] px-3 py-1.5 text-xs font-bold hover:border-[var(--accent-royal)]"
              >
                <HelpCircle className="h-3.5 w-3.5 text-teal-600" />
                <span>Give Example</span>
              </button>
              <button
                onClick={() => handleTriggerIntervention('followup')}
                disabled={interventionLoading}
                className="flex items-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] px-3 py-1.5 text-xs font-bold hover:border-[var(--accent-royal)]"
              >
                <BarChart3 className="h-3.5 w-3.5 text-blue-600" />
                <span>Ask Follow-up</span>
              </button>
            </div>

            {/* Intervention Output Card */}
            {interventionResult && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-2xl border border-purple-500/30 bg-purple-500/5 p-5 space-y-4"
              >
                <div className="flex items-center justify-between font-bold text-sm text-purple-600">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4" />
                    <span>Intervention: {interventionResult.type.toUpperCase()}</span>
                  </div>
                  <button onClick={() => setInterventionResult(null)}>
                    <X className="h-4 w-4" />
                  </button>
                </div>

                {interventionResult.svg && (
                  <div
                    className="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4"
                    dangerouslySetInnerHTML={{ __html: interventionResult.svg }}
                  />
                )}
                {interventionResult.comparison && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="rounded-xl border border-green-500/30 bg-green-50/50 p-4">
                      <div className="font-bold text-green-800 text-sm">{interventionResult.comparison.correct_concept.heading}</div>
                      <div className="mt-1 text-xs text-green-700">{interventionResult.comparison.correct_concept.text}</div>
                    </div>
                    <div className="rounded-xl border border-amber-500/30 bg-amber-50/50 p-4">
                      <div className="font-bold text-amber-900 text-sm">{interventionResult.comparison.common_misconception.heading}</div>
                      <div className="mt-1 text-xs text-amber-900">{interventionResult.comparison.common_misconception.text}</div>
                    </div>
                  </div>
                )}
                {interventionResult.content && (
                  <p className="text-sm text-[var(--text-primary)] leading-relaxed">
                    {interventionResult.content}
                  </p>
                )}
              </motion.div>
            )}
          </div>
        )}

        {/* ─── Student Live Monitoring Table (§8) ─── */}
        <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="font-display text-lg font-bold">Student Live Monitoring</h2>
              <p className="text-xs text-[var(--text-secondary)]">
                Server-side cursor pagination with virtualized view ({totalStudents} participants)
              </p>
            </div>

            {/* Filter & Search Bar */}
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-[var(--text-muted)]" />
                <input
                  type="text"
                  placeholder="Search student..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] pl-9 pr-4 py-1.5 text-xs font-semibold focus:outline-none focus:border-[var(--accent-royal)]"
                />
              </div>

              <select
                value={riskFilter}
                onChange={e => setRiskFilter(e.target.value)}
                className="rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] px-3 py-1.5 text-xs font-semibold"
              >
                <option value="all">All Risk Levels</option>
                <option value="high">High Risk Only</option>
                <option value="medium">Medium Risk</option>
                <option value="low">Low Risk</option>
              </select>

              <label className="flex items-center gap-1.5 text-xs font-semibold cursor-pointer">
                <input
                  type="checkbox"
                  checked={bannedFilter}
                  onChange={e => setBannedFilter(e.target.checked)}
                  className="rounded border-[var(--border)]"
                />
                <span>Banned Only</span>
              </label>
            </div>
          </div>

          {/* Virtualized/Windowed Roster Table */}
          <div className="overflow-x-auto rounded-2xl border border-[var(--border)]">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-[var(--border)] bg-[var(--bg-hover)] text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
                <tr>
                  <th className="py-3 px-4">Student</th>
                  <th className="py-3 px-4">Score</th>
                  <th className="py-3 px-4">Progress</th>
                  <th className="py-3 px-4">Avg Speed</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Risk Level</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)] font-medium">
                {participants.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-sm text-[var(--text-muted)]">
                      No participants match current filters.
                    </td>
                  </tr>
                ) : (
                  participants.map((p) => {
                    const isBanned = p.is_banned;
                    const risk = p.risk_level || 'low';

                    return (
                      <tr
                        key={p.id}
                        className={`hover:bg-[var(--bg-hover)] transition-colors ${
                          isBanned ? 'bg-amber-500/5' : ''
                        }`}
                      >
                        <td className="py-3 px-4 font-bold flex items-center gap-2">
                          <span className="text-base">{p.avatar_seed?.startsWith('avatar_') ? '🎓' : p.avatar_seed || '🎓'}</span>
                          <span>{p.display_name}</span>
                        </td>
                        <td className="py-3 px-4 font-mono font-bold text-[var(--accent-royal)]">
                          {p.score} pts
                        </td>
                        <td className="py-3 px-4 text-xs font-semibold">
                          Q{(p.current_question_index || 0) + 1} ({p.answered_count || 0} ans)
                        </td>
                        <td className="py-3 px-4 text-xs font-mono">
                          {((p.average_response_ms || 0) / 1000).toFixed(1)}s
                        </td>
                        <td className="py-3 px-4 text-xs">
                          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-bold ${
                            p.connection_state === 'active' ? 'bg-green-100 text-green-800' : 'bg-zinc-100 text-zinc-800'
                          }`}>
                            <span className="h-1.5 w-1.5 rounded-full bg-current" />
                            {p.connection_state || 'active'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-xs">
                          <span className={`inline-flex rounded-full px-2 py-0.5 font-bold uppercase text-[10px] ${
                            risk === 'high' ? 'bg-amber-100 text-amber-900' :
                            risk === 'medium' ? 'bg-amber-100 text-amber-800' :
                            'bg-green-100 text-green-800'
                          }`}>
                            {risk} ({p.risk_score || 0})
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right space-x-2">
                          <button
                            onClick={() => handleOpenStudentDetail(p.id)}
                            className="rounded-lg border border-[var(--border)] px-2.5 py-1 text-xs font-semibold hover:border-[var(--accent-royal)]"
                          >
                            Details
                          </button>
                          {isBanned ? (
                            <button
                              onClick={() => handleUnban(p.id)}
                              className="rounded-lg bg-green-600 px-2.5 py-1 text-xs font-bold text-white hover:bg-green-700"
                            >
                              Unban
                            </button>
                          ) : (
                            <button
                              onClick={() => setBanModalStudent(p)}
                              className="rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-900 hover:bg-amber-100"
                            >
                              Ban
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>

      {/* ─── Student Detail Drawer Modal (§9) ─── */}
      <AnimatePresence>
        {selectedStudentId && (
          <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/40 backdrop-blur-sm">
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 250 }}
              className="h-full w-full max-w-lg border-l border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-2xl overflow-y-auto space-y-6"
            >
              <div className="flex items-center justify-between border-b border-[var(--border)] pb-4">
                <div>
                  <h3 className="font-display text-xl font-bold">
                    {studentDetail?.participant?.display_name || 'Student Details'}
                  </h3>
                  <div className="text-xs text-[var(--text-muted)] font-mono">
                    ID: {selectedStudentId}
                  </div>
                </div>
                <button
                  onClick={() => { setSelectedStudentId(null); setStudentDetail(null); }}
                  className="rounded-xl p-2 hover:bg-[var(--bg-hover)]"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {detailLoading ? (
                <div className="flex h-64 items-center justify-center">
                  <Clock className="h-8 w-8 animate-spin text-[var(--accent-royal)]" />
                </div>
              ) : (
                <div className="space-y-6 text-sm">
                  {/* Participant Overview */}
                  <div className="grid grid-cols-2 gap-3 rounded-2xl bg-[var(--bg-hover)] p-4 text-xs font-semibold">
                    <div>Score: <span className="font-bold text-sm text-[var(--accent-royal)]">{studentDetail?.participant?.score} pts</span></div>
                    <div>Streak: <span className="font-bold">{studentDetail?.participant?.streak}</span></div>
                    <div>Risk Score: <span className="font-bold text-amber-900">{studentDetail?.participant?.risk_score}/100</span></div>
                    <div>Status: <span className="font-bold">{studentDetail?.participant?.connection_state}</span></div>
                  </div>

                  {/* Activity Signals & Audit Events */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] flex items-center gap-1.5">
                      <Activity className="h-4 w-4" /> Activity & Risk Signals
                    </h4>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {(studentDetail?.activity_signals?.length || 0) === 0 ? (
                        <p className="text-xs text-[var(--text-muted)]">No suspicious activity signals recorded.</p>
                      ) : (
                        studentDetail?.activity_signals.map((sig: any, idx: number) => (
                          <div key={idx} className="flex items-center justify-between rounded-xl border border-[var(--border)] p-2.5 text-xs">
                            <span className="font-bold text-amber-600">{sig.event_type}</span>
                            <span className="text-[var(--text-muted)] font-mono">{new Date(sig.created_at).toLocaleTimeString()}</span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Response History */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
                      Submitted Responses
                    </h4>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {(studentDetail?.responses?.length || 0) === 0 ? (
                        <p className="text-xs text-[var(--text-muted)]">No responses submitted yet.</p>
                      ) : (
                        studentDetail?.responses.map((resp: any, idx: number) => (
                          <div key={idx} className="rounded-xl border border-[var(--border)] p-3 text-xs space-y-1">
                            <div className="flex items-center justify-between font-bold">
                              <span>Option: {resp.selected_option_id}</span>
                              <span className={resp.is_correct ? 'text-green-600' : 'text-amber-900'}>
                                {resp.is_correct ? 'Correct' : 'Incorrect'} (+{resp.points} pts)
                              </span>
                            </div>
                            <div className="flex items-center justify-between text-[var(--text-muted)] font-mono text-[11px]">
                              <span>Speed: {(resp.response_time_ms / 1000).toFixed(2)}s</span>
                              <span>{new Date(resp.submitted_at).toLocaleTimeString()}</span>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ─── Ban Confirmation Modal (§11) ─── */}
      <AnimatePresence>
        {banModalStudent && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-md rounded-3xl border border-amber-500/30 bg-[var(--bg-card)] p-6 shadow-2xl space-y-4"
            >
              <div className="flex items-center gap-3 text-amber-900">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100">
                  <Ban className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="font-display text-lg font-bold">Ban Participant</h3>
                  <p className="text-xs text-[var(--text-secondary)]">Revoke student access immediately</p>
                </div>
              </div>

              <p className="text-sm text-[var(--text-primary)]">
                Are you sure you want to ban <span className="font-bold">{banModalStudent.display_name}</span>?
                Their attempt will be immediately revoked.
              </p>

              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
                  Reason for Ban
                </label>
                <input
                  type="text"
                  value={banReasonInput}
                  onChange={e => setBanReasonInput(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-hover)] px-3 py-2 text-sm font-semibold focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={() => setBanModalStudent(null)}
                  className="rounded-xl border border-[var(--border)] px-4 py-2 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmBan}
                  disabled={banLoading}
                  className="rounded-xl bg-amber-600 px-5 py-2 text-xs font-bold text-white hover:bg-amber-700"
                >
                  {banLoading ? 'Banning...' : 'Confirm Ban'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ─── End Session Modal ─── */}
      <AnimatePresence>
        {showEndModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-md rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-2xl space-y-4"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-900">
                  <AlertTriangle className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="font-display text-lg font-bold">End Live Session?</h3>
                  <p className="text-xs text-[var(--text-secondary)]">Syncs scores to Bayesian Mastery Engine</p>
                </div>
              </div>
              <p className="text-sm text-[var(--text-secondary)]">
                Ending the session will calculate final student rankings, lock submissions, and generate the audit assessment report.
              </p>
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={() => setShowEndModal(false)}
                  className="rounded-xl border border-[var(--border)] px-4 py-2 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  onClick={handleEndSession}
                  className="rounded-xl bg-amber-600 px-5 py-2 text-xs font-bold text-white hover:bg-amber-700"
                >
                  End Session Now
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
