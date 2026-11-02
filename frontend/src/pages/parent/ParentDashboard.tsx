import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  Users, AlertTriangle, Award, Flame, Plus, ChevronRight, 
  Sparkles, CheckCircle2, RefreshCw, HeartHandshake, BookOpen
} from 'lucide-react';
import ParentLayout from '../../components/layout/ParentLayout';
import { 
  fetchParentDashboard, 
  linkChild 
} from '../../lib/portalsApi';
import type { 
  ParentDashboardSummary, 
  ParentChildView 
} from '../../lib/portalsApi';

export default function ParentDashboard() {
  const [data, setData] = useState<ParentDashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Link Child modal state
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [childIdInput, setChildIdInput] = useState('');
  const [relationshipInput, setRelationshipInput] = useState('Parent');
  const [linking, setLinking] = useState(false);
  const [linkMsg, setLinkMsg] = useState<{ text: string; error: boolean } | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchParentDashboard();
      setData(res);
    } catch (err: any) {
      console.error('Failed to load parent dashboard:', err);
      setError(err?.response?.data?.detail || err.message || 'Failed to load parent dashboard.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleLinkChild = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!childIdInput.trim()) return;

    try {
      setLinking(true);
      setLinkMsg(null);
      const res = await linkChild(childIdInput.trim(), relationshipInput);
      setLinkMsg({ text: res.message, error: false });
      setChildIdInput('');
      await loadData();
      setTimeout(() => setShowLinkModal(false), 1200);
    } catch (err: any) {
      setLinkMsg({
        text: err?.response?.data?.detail || err.message || 'Failed to link child.',
        error: true,
      });
    } finally {
      setLinking(false);
    }
  };

  return (
    <ParentLayout title="Parent Portal">
      <div className="max-w-6xl mx-auto p-4 md:p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--border)] pb-5">
          <div>
            <div className="flex items-center gap-2 text-sm text-[var(--accent-purple)] font-semibold uppercase tracking-wider">
              <HeartHandshake className="w-4 h-4" />
              Parent Oversight & Growth Portal
            </div>
            <h1 className="text-2xl md:text-3xl font-display font-bold text-[var(--text-primary)] mt-1">
              Family Learning Hub
            </h1>
            <p className="text-[var(--text-secondary)] text-sm mt-1">
              Monitor your children's real-time skill mastery, active misconception patterns, and study streaks.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowLinkModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[var(--accent-royal)] text-white text-sm font-semibold hover:bg-opacity-90 shadow-sm transition"
            >
              <Plus className="w-4 h-4" />
              Link Child
            </button>
            <button
              onClick={loadData}
              disabled={loading}
              className="p-2.5 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition"
              title="Refresh dashboard"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Global Alerts Banner if any */}
        {data && data.unread_alerts_count > 0 && (
          <div className="flex items-start gap-3 p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-200">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-sm">
              <span className="font-semibold text-amber-300">Attention Needed: </span>
              {data.unread_alerts_count} recurring misconception pattern(s) identified across your linked children.
              Review the detailed breakdown below for recommended constructive coaching actions.
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && !data && (
          <div className="flex flex-col items-center justify-center p-16 space-y-3">
            <div className="w-8 h-8 border-3 border-[var(--accent-royal)] border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-[var(--text-secondary)]">Loading child learning metrics...</span>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-sm">
            {error}
          </div>
        )}

        {/* Children Grid */}
        {data && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-[var(--text-primary)] flex items-center gap-2">
              <Users className="w-5 h-5 text-[var(--accent-royal)]" />
              Enrolled Children ({data.linked_children.length})
            </h2>

            {data.linked_children.length === 0 ? (
              <div className="text-center p-10 border border-dashed border-[var(--border)] rounded-2xl bg-[var(--bg-card)] space-y-3">
                <Users className="w-10 h-10 text-[var(--text-secondary)] mx-auto opacity-50" />
                <h3 className="text-base font-semibold text-[var(--text-primary)]">No children linked yet</h3>
                <p className="text-sm text-[var(--text-secondary)] max-w-md mx-auto">
                  Link your child's student account using their UUID to start monitoring their daily study progress and mastery graph.
                </p>
                <button
                  onClick={() => setShowLinkModal(true)}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--accent-royal)] text-white text-sm font-semibold hover:bg-opacity-90 transition mt-2"
                >
                  <Plus className="w-4 h-4" />
                  Link Child Now
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {data.linked_children.map((child: ParentChildView) => (
                  <div
                    key={child.student_id}
                    className="p-5 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] hover:border-[var(--accent-royal)] transition shadow-sm space-y-4"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center font-bold text-lg text-purple-400">
                          {child.student_name.charAt(0)}
                        </div>
                        <div>
                          <h3 className="text-base font-bold text-[var(--text-primary)]">
                            {child.student_name}
                          </h3>
                          <p className="text-xs text-[var(--text-secondary)]">
                            {child.grade_or_class} • {child.curriculum} {child.target_exam ? `• ${child.target_exam}` : ''}
                          </p>
                        </div>
                      </div>
                      <Link
                        to={`/parent/child/${child.student_id}`}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--accent-royal)] hover:underline"
                      >
                        Detailed View
                        <ChevronRight className="w-4 h-4" />
                      </Link>
                    </div>

                    {/* Stats Row */}
                    <div className="grid grid-cols-3 gap-2 p-3 rounded-xl bg-[var(--bg-hover)] text-center">
                      <div>
                        <div className="flex items-center justify-center gap-1 text-xs text-[var(--text-secondary)]">
                          <Award className="w-3.5 h-3.5 text-amber-400" />
                          <span>Total XP</span>
                        </div>
                        <span className="text-base font-bold text-[var(--text-primary)] mt-0.5 block">
                          {child.total_xp.toLocaleString()}
                        </span>
                      </div>
                      <div>
                        <div className="flex items-center justify-center gap-1 text-xs text-[var(--text-secondary)]">
                          <Flame className="w-3.5 h-3.5 text-orange-500" />
                          <span>Streak</span>
                        </div>
                        <span className="text-base font-bold text-[var(--text-primary)] mt-0.5 block">
                          {child.current_streak} days
                        </span>
                      </div>
                      <div>
                        <div className="flex items-center justify-center gap-1 text-xs text-[var(--text-secondary)]">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Mastered</span>
                        </div>
                        <span className="text-base font-bold text-emerald-400 mt-0.5 block">
                          {child.mastered_skills_count}
                        </span>
                      </div>
                    </div>

                    {/* Topic Status Breakdown */}
                    <div className="space-y-2 text-xs">
                      <div className="flex justify-between text-[var(--text-secondary)]">
                        <span>Curriculum Progress</span>
                        <span>
                          {child.mastered_skills_count + child.in_progress_skills_count} Active Skills
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-[var(--border)] overflow-hidden flex">
                        <div
                          style={{
                            width: `${Math.min(100, (child.mastered_skills_count / Math.max(1, child.mastered_skills_count + child.in_progress_skills_count + child.needs_repair_count)) * 100)}%`,
                          }}
                          className="bg-emerald-500"
                          title="Mastered"
                        />
                        <div
                          style={{
                            width: `${Math.min(100, (child.in_progress_skills_count / Math.max(1, child.mastered_skills_count + child.in_progress_skills_count + child.needs_repair_count)) * 100)}%`,
                          }}
                          className="bg-blue-500"
                          title="Developing"
                        />
                        <div
                          style={{
                            width: `${Math.min(100, (child.needs_repair_count / Math.max(1, child.mastered_skills_count + child.in_progress_skills_count + child.needs_repair_count)) * 100)}%`,
                          }}
                          className="bg-amber-500"
                          title="Needs Repair"
                        />
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-[var(--text-secondary)] pt-1">
                        <span className="text-emerald-400 font-medium">● {child.mastered_skills_count} Mastered</span>
                        <span className="text-blue-400 font-medium">● {child.in_progress_skills_count} In Progress</span>
                        <span className="text-amber-400 font-medium">● {child.needs_repair_count} Needs Repair</span>
                      </div>
                    </div>

                    {/* Active Misconceptions Badge */}
                    {child.active_mistakes_count > 0 ? (
                      <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-between text-xs text-amber-300">
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-amber-400" />
                          <span>{child.active_mistakes_count} active mistake patterns detected</span>
                        </div>
                        <Link
                          to={`/parent/child/${child.student_id}`}
                          className="font-semibold underline hover:text-amber-200"
                        >
                          View Repairs
                        </Link>
                      </div>
                    ) : (
                      <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-2 text-xs text-emerald-400">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>All core foundational topics in good standing</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Link Child Modal */}
        {showLinkModal && (
          <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="w-full max-w-md bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-[var(--text-primary)]">Link Student Account</h3>
                <button
                  onClick={() => setShowLinkModal(false)}
                  className="text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                >
                  ✕
                </button>
              </div>
              <p className="text-xs text-[var(--text-secondary)]">
                Enter your child's student UUID or email identifier to link your parent dashboard.
              </p>

              <form onSubmit={handleLinkChild} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                    Student ID (UUID or Email)
                  </label>
                  <input
                    type="text"
                    value={childIdInput}
                    onChange={(e) => setChildIdInput(e.target.value)}
                    placeholder="e.g. 00000000-0000-0000-0000-000000000001"
                    className="w-full px-3 py-2 text-sm rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-royal)]"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                    Relationship
                  </label>
                  <select
                    value={relationshipInput}
                    onChange={(e) => setRelationshipInput(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-royal)]"
                  >
                    <option value="Parent">Parent</option>
                    <option value="Mother">Mother</option>
                    <option value="Father">Father</option>
                    <option value="Guardian">Guardian</option>
                  </select>
                </div>

                {linkMsg && (
                  <div
                    className={`p-3 rounded-xl text-xs ${
                      linkMsg.error
                        ? 'bg-rose-500/10 border border-rose-500/20 text-rose-300'
                        : 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-300'
                    }`}
                  >
                    {linkMsg.text}
                  </div>
                )}

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowLinkModal(false)}
                    className="px-4 py-2 rounded-xl text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={linking}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-[var(--accent-royal)] text-white hover:bg-opacity-90 disabled:opacity-50"
                  >
                    {linking ? 'Linking...' : 'Confirm Link'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </ParentLayout>
  );
}
