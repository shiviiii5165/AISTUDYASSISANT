import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Trophy, Users, Target, Clock, ArrowRight, Sparkles, BookOpen,
  HelpCircle, Presentation, FileText, CheckCircle2, XCircle, AlertTriangle, Loader2
} from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { getSessionReport, type SessionAnalytics } from '../lib/liveQuizApi';

const LiveQuizReportPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    const fetchReport = async () => {
      try {
        setLoading(true);
        const data = await getSessionReport(sessionId);
        setReport(data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load session report');
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, [sessionId]);

  if (loading) {
    return (
      <AppLayout title="Live Session Report">
        <div className="flex h-[80vh] items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-[var(--accent-royal)]" />
            <p className="font-semibold text-[var(--text-secondary)]">Generating Session Report...</p>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (error || !report) {
    return (
      <AppLayout title="Live Session Report">
        <div className="mx-auto mt-12 max-w-lg rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
          <AlertTriangle className="mx-auto h-8 w-8 text-red-600" />
          <h2 className="mt-2 text-lg font-bold text-red-900">Report Unavailable</h2>
          <p className="mt-1 text-sm text-red-800">{error || 'Session report could not be retrieved.'}</p>
        </div>
      </AppLayout>
    );
  }

  const analytics: SessionAnalytics = report.analytics || {};
  const participants = report.participants || [];
  const heatmap = analytics.concept_heatmap || [];
  const mostMissed = analytics.most_missed_questions || [];

  const handleSuggestedAction = (actionId: string) => {
    if (actionId === 'revision_quiz') {
      navigate('/quizzes');
    } else if (actionId === 'teach_me') {
      navigate('/teach');
    } else if (actionId === 'remedial_lesson') {
      navigate('/lesson-planner');
    } else {
      navigate('/dashboard');
    }
  };

  return (
    <AppLayout title="Session Report">
      <SEO title="Live Session Report | TeachGenie" description="Post-quiz learning analytics and concept mastery." />

      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8 space-y-8">
        
        {/* Top Header Card */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-8 shadow-sm">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
              <span>Live Room Summary</span>
              <span>•</span>
              <span>Code: {report.session?.join_code}</span>
            </div>
            <h1 className="mt-1 font-display text-3xl font-bold text-[var(--text-primary)]">
              Session Assessment Report
            </h1>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              All metrics calculated deterministically from class responses.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/dashboard')}
              className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-5 py-2.5 text-sm font-bold text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
            >
              Back to Dashboard
            </button>
          </div>
        </div>

        {/* High-Level Class KPI Cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">Students</span>
              <Users className="h-5 w-5 text-[var(--accent-royal)]" />
            </div>
            <div className="mt-2 font-display text-3xl font-bold text-[var(--text-primary)]">
              {participants.length}
            </div>
            <span className="text-xs text-[var(--text-secondary)]">Participated</span>
          </div>

          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">Class Accuracy</span>
              <Target className="h-5 w-5 text-emerald-600" />
            </div>
            <div className="mt-2 font-display text-3xl font-bold text-emerald-600">
              {analytics.overall_accuracy}%
            </div>
            <span className="text-xs text-[var(--text-secondary)]">Correct answers</span>
          </div>

          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">Completion</span>
              <CheckCircle2 className="h-5 w-5 text-blue-600" />
            </div>
            <div className="mt-2 font-display text-3xl font-bold text-[var(--text-primary)]">
              {analytics.completion_rate}%
            </div>
            <span className="text-xs text-[var(--text-secondary)]">{analytics.total_responses} submissions</span>
          </div>

          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">Avg Speed</span>
              <Clock className="h-5 w-5 text-purple-600" />
            </div>
            <div className="mt-2 font-display text-3xl font-bold text-[var(--text-primary)]">
              {(analytics.average_response_time_ms / 1000).toFixed(1)}s
            </div>
            <span className="text-xs text-[var(--text-secondary)]">Per question</span>
          </div>
        </div>

        {/* ─── CONCEPT ACCURACY HEATMAP ──────────────────────────────────────── */}
        <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-sm md:p-8">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h2 className="font-display text-xl font-bold text-[var(--text-primary)]">
                Concept Mastery Heatmap
              </h2>
              <p className="mt-1 text-xs text-[var(--text-secondary)]">
                🟢 Strong (≥70%) • 🟡 Developing (50-70%) • 🔴 Needs Review (&lt;50%)
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {heatmap.map((c, i) => (
              <div
                key={i}
                className="rounded-2xl border p-4 shadow-sm transition-all"
                style={{
                  borderColor: `${c.color}40`,
                  backgroundColor: c.status === 'strong' ? '#F0FDF4' : c.status === 'developing' ? '#FFFBEB' : '#FEF2F2',
                }}
              >
                <div className="flex items-start justify-between">
                  <span className="font-bold text-sm text-[var(--text-primary)]">{c.concept}</span>
                  <span
                    className="rounded-full px-2.5 py-0.5 text-xs font-bold text-white"
                    style={{ backgroundColor: c.color }}
                  >
                    {c.accuracy_pct}%
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>{c.total_responses} answers recorded</span>
                  <span className="capitalize font-semibold" style={{ color: c.color }}>
                    {c.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ─── MOST MISSED QUESTIONS ────────────────────────────────────────── */}
        {mostMissed.length > 0 && (
          <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-sm md:p-8">
            <h2 className="font-display text-xl font-bold text-[var(--text-primary)] mb-4">
              Questions Needing Review
            </h2>
            <div className="space-y-4">
              {mostMissed.map((q, idx) => (
                <div key={idx} className="rounded-2xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5">
                  <div className="flex items-start justify-between gap-4">
                    <h4 className="font-bold text-sm text-[var(--text-primary)]">
                      {q.question_text}
                    </h4>
                    <span className="rounded-lg bg-red-100 px-2.5 py-1 text-xs font-bold text-red-700 shrink-0">
                      {q.accuracy_pct}% Correct
                    </span>
                  </div>
                  {q.top_distractor && (
                    <p className="mt-2 text-xs text-[var(--text-secondary)]">
                      <strong className="text-amber-800">Most common misconception:</strong> {q.top_distractor}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ─── POST-SESSION REMEDIAL ACTION SUGGESTIONS ──────────────────────── */}
        <div className="rounded-3xl border border-[var(--accent-royal)]/20 bg-[var(--accent-baby)]/10 p-6 shadow-sm md:p-8">
          <div className="flex items-center gap-2 mb-2 text-[var(--accent-royal)] font-bold text-xs uppercase tracking-wider">
            <Sparkles className="h-4 w-4" /> Recommended Follow-up Actions
          </div>
          <h2 className="font-display text-xl font-bold text-[var(--text-primary)] mb-2">
            Targeted Remediation
          </h2>
          <p className="text-sm text-[var(--text-secondary)] mb-6">
            Help your class solidify weak concepts identified during today's live session. Each action launches an existing tool scoped directly to these results.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <button
              onClick={() => handleSuggestedAction('remedial_lesson')}
              className="flex flex-col items-start p-4 rounded-2xl border border-[var(--border)] bg-white hover:border-[var(--accent-royal)] shadow-sm text-left transition-all"
            >
              <BookOpen className="h-5 w-5 text-[var(--accent-royal)] mb-2" />
              <span className="font-bold text-sm text-[var(--text-primary)]">Remedial Lesson</span>
              <span className="text-xs text-[var(--text-secondary)] mt-1">Sync with Lesson Planner</span>
            </button>

            <button
              onClick={() => handleSuggestedAction('revision_quiz')}
              className="flex flex-col items-start p-4 rounded-2xl border border-[var(--border)] bg-white hover:border-[var(--accent-royal)] shadow-sm text-left transition-all"
            >
              <HelpCircle className="h-5 w-5 text-emerald-600 mb-2" />
              <span className="font-bold text-sm text-[var(--text-primary)]">Revision Quiz</span>
              <span className="text-xs text-[var(--text-secondary)] mt-1">5-question quick check</span>
            </button>

            <button
              onClick={() => handleSuggestedAction('teach_me')}
              className="flex flex-col items-start p-4 rounded-2xl border border-[var(--border)] bg-white hover:border-[var(--accent-royal)] shadow-sm text-left transition-all"
            >
              <Sparkles className="h-5 w-5 text-purple-600 mb-2" />
              <span className="font-bold text-sm text-[var(--text-primary)]">Interactive Teach Me</span>
              <span className="text-xs text-[var(--text-secondary)] mt-1">Adaptive AI walkthrough</span>
            </button>

            <button
              onClick={() => handleSuggestedAction('presentation')}
              className="flex flex-col items-start p-4 rounded-2xl border border-[var(--border)] bg-white hover:border-[var(--accent-royal)] shadow-sm text-left transition-all"
            >
              <Presentation className="h-5 w-5 text-amber-600 mb-2" />
              <span className="font-bold text-sm text-[var(--text-primary)]">Review Slides</span>
              <span className="text-xs text-[var(--text-secondary)] mt-1">Classroom presentation</span>
            </button>
          </div>
        </div>

        {/* ─── PARTICIPANT LEADERBOARD / ROSTER ──────────────────────────────── */}
        <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-sm md:p-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display text-xl font-bold text-[var(--text-primary)]">
              Participant Results ({participants.length})
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-[var(--border)] text-xs font-bold uppercase text-[var(--text-muted)]">
                <tr>
                  <th className="pb-3">Rank</th>
                  <th className="pb-3">Student</th>
                  <th className="pb-3 text-center">Score</th>
                  <th className="pb-3 text-center">Correct</th>
                  <th className="pb-3 text-right">Streak</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)] font-medium">
                {participants.map((p: any, idx: number) => (
                  <tr key={p.id} className="hover:bg-[var(--bg-secondary)]/50">
                    <td className="py-3 font-mono font-bold text-[var(--text-muted)]">#{idx + 1}</td>
                    <td className="py-3 flex items-center gap-2">
                      <span>{p.avatar_seed || '👤'}</span>
                      <span className="font-semibold text-[var(--text-primary)]">{p.display_name}</span>
                    </td>
                    <td className="py-3 text-center font-mono font-bold text-[var(--accent-royal)]">
                      {p.score} pts
                    </td>
                    <td className="py-3 text-center text-[var(--text-secondary)]">
                      {p.correct_count} / {p.answered_count}
                    </td>
                    <td className="py-3 text-right font-mono text-amber-600">
                      {p.streak > 1 ? `🔥 ${p.streak}` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </AppLayout>
  );
};

export default LiveQuizReportPage;
