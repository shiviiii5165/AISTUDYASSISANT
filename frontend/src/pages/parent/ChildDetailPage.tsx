import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  ArrowLeft, Users, AlertTriangle, Award, Flame, CheckCircle2, 
  HelpCircle, Compass, RefreshCw, Sparkles, BookOpen 
} from 'lucide-react';
import ParentLayout from '../../components/layout/ParentLayout';
import { 
  fetchChildDetailedProgress 
} from '../../lib/portalsApi';
import type { 
  ChildDetailedProgress, 
  ChildMistakeAlert 
} from '../../lib/portalsApi';

export default function ChildDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<ChildDetailedProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const res = await fetchChildDetailedProgress(id);
      setData(res);
    } catch (err: any) {
      console.error('Failed to load child details:', err);
      setError(err?.response?.data?.detail || err.message || 'Failed to load child details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  return (
    <ParentLayout title="Child Progress Details">
      <div className="max-w-5xl mx-auto p-4 md:p-6 space-y-6">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center justify-between">
          <Link
            to="/parent"
            className="inline-flex items-center gap-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Family Hub
          </Link>
          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Loading */}
        {loading && !data && (
          <div className="flex flex-col items-center justify-center p-16 space-y-3">
            <div className="w-8 h-8 border-3 border-[var(--accent-royal)] border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-[var(--text-secondary)]">Retrieving student records and Mistake DNA...</span>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-sm">
            {error}
          </div>
        )}

        {/* Data View */}
        {data && (
          <>
            {/* Student Profile Card */}
            <div className="p-6 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] flex flex-col md:flex-row md:items-center justify-between gap-5 shadow-sm">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center font-bold text-2xl text-purple-400">
                  {data.student.student_name.charAt(0)}
                </div>
                <div>
                  <h1 className="text-2xl font-bold font-display text-[var(--text-primary)]">
                    {data.student.student_name}
                  </h1>
                  <p className="text-sm text-[var(--text-secondary)]">
                    {data.student.grade_or_class} • {data.student.curriculum}{' '}
                    {data.student.target_exam ? `• Goal: ${data.student.target_exam}` : ''}
                  </p>
                  <p className="text-xs text-[var(--text-secondary)] mt-1 font-mono">
                    ID: {data.student.student_id}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4 border-t md:border-t-0 md:border-l border-[var(--border)] pt-4 md:pt-0 md:pl-6">
                <div>
                  <div className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
                    <Award className="w-4 h-4 text-amber-400" />
                    <span>XP Points</span>
                  </div>
                  <span className="text-xl font-bold text-[var(--text-primary)]">
                    {data.student.total_xp.toLocaleString()}
                  </span>
                </div>
                <div className="h-8 w-px bg-[var(--border)]" />
                <div>
                  <div className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
                    <Flame className="w-4 h-4 text-orange-500" />
                    <span>Current Streak</span>
                  </div>
                  <span className="text-xl font-bold text-[var(--text-primary)]">
                    {data.student.current_streak} Days
                  </span>
                </div>
              </div>
            </div>

            {/* Active Misconceptions / Alerts */}
            <div className="space-y-3">
              <h2 className="text-lg font-semibold text-[var(--text-primary)] flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-400" />
                Mistake DNA & Parent Guidance
              </h2>
              <p className="text-xs text-[var(--text-secondary)]">
                Our educational reasoning engine detects cognitive misconception patterns and recommends supportive guidance steps.
              </p>

              {data.active_mistake_alerts.length === 0 ? (
                <div className="p-5 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 text-emerald-300 flex items-center gap-3">
                  <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
                  <div>
                    <h4 className="text-sm font-semibold text-emerald-200">No Persistent Cognitive Blocks</h4>
                    <p className="text-xs text-emerald-400/80">
                      This student is consistently demonstrating sound reasoning across assessed concepts.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  {data.active_mistake_alerts.map((alert: ChildMistakeAlert, idx: number) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/5 space-y-2"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-500/20 text-amber-300">
                            {alert.error_type}
                          </span>
                          <span className="text-sm font-semibold text-[var(--text-primary)]">
                            {alert.skill_id}
                          </span>
                        </div>
                        <span className="text-xs text-amber-400 font-mono">
                          Occurred {alert.occurrence_count} times
                        </span>
                      </div>
                      {alert.recommended_repair_action && (
                        <div className="text-xs text-[var(--text-secondary)] bg-[var(--bg-primary)] p-3 rounded-lg border border-[var(--border)]">
                          <span className="font-semibold text-amber-300 block mb-0.5">
                            Recommended Home Guidance:
                          </span>
                          {alert.recommended_repair_action}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recent Assessment Scores */}
            <div className="space-y-3">
              <h2 className="text-lg font-semibold text-[var(--text-primary)] flex items-center gap-2">
                <Compass className="w-5 h-5 text-blue-400" />
                Recent Diagnostic & Assessment Results
              </h2>
              <div className="border border-[var(--border)] rounded-2xl overflow-hidden bg-[var(--bg-card)]">
                <table className="w-full text-left text-sm">
                  <thead className="bg-[var(--bg-hover)] text-xs text-[var(--text-secondary)] border-b border-[var(--border)]">
                    <tr>
                      <th className="py-3 px-4">Assessment / Module</th>
                      <th className="py-3 px-4">Score</th>
                      <th className="py-3 px-4">Date</th>
                      <th className="py-3 px-4 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)]">
                    {data.recent_quiz_scores.map((score, idx) => (
                      <tr key={idx} className="hover:bg-[var(--bg-hover)] transition">
                        <td className="py-3 px-4 font-medium text-[var(--text-primary)]">
                          {score.quiz_title}
                        </td>
                        <td className="py-3 px-4 font-semibold text-emerald-400">
                          {score.score}
                        </td>
                        <td className="py-3 px-4 text-xs text-[var(--text-secondary)]">
                          {score.date}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className="px-2 py-0.5 rounded-full text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            Verified
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </ParentLayout>
  );
}
