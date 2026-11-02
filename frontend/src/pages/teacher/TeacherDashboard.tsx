import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  GraduationCap, Users, BookOpen, Presentation, Radio, Plus,
  ChevronRight, AlertCircle, RefreshCw, BarChart3, Sparkles
} from 'lucide-react';
import AppLayout from '../../components/AppLayout';
import {
  fetchTeacherDashboard,
  createClassroom
} from '../../lib/portalsApi';
import type {
  TeacherDashboardSummary,
  ClassroomView
} from '../../lib/portalsApi';

export default function TeacherDashboard() {
  const [data, setData] = useState<TeacherDashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New Classroom Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [name, setName] = useState('');
  const [gradeLevel, setGradeLevel] = useState('Class 10');
  const [stream, setStream] = useState('Science');
  const [academicYear, setAcademicYear] = useState('2026-2027');
  const [creating, setCreating] = useState(false);
  const [createMsg, setCreateMsg] = useState<{ text: string; error: boolean } | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchTeacherDashboard();
      setData(res);
    } catch (err: any) {
      console.error('Failed to load teacher dashboard:', err);
      setError(err?.response?.data?.detail || err.message || 'Failed to load teacher dashboard.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateClassroom = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      setCreating(true);
      setCreateMsg(null);
      await createClassroom({
        name: name.trim(),
        grade_level: gradeLevel,
        academic_stream: stream,
        academic_year: academicYear,
      });
      setCreateMsg({ text: 'Classroom created successfully!', error: false });
      setName('');
      await loadData();
      setTimeout(() => setShowCreateModal(false), 1000);
    } catch (err: any) {
      setCreateMsg({
        text: err?.response?.data?.detail || err.message || 'Failed to create classroom.',
        error: true,
      });
    } finally {
      setCreating(false);
    }
  };

  return (
    <AppLayout title="Teacher Portal">
      <div className="max-w-6xl mx-auto p-4 md:p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--border)] pb-5">
          <div>
            <div className="flex items-center gap-2 text-sm text-[var(--accent-royal)] font-semibold uppercase tracking-wider">
              <GraduationCap className="w-4 h-4" />
              Teacher Command Center
            </div>
            <h1 className="text-2xl md:text-3xl font-display font-bold text-[var(--text-primary)] mt-1">
              Classroom & Curriculum Management
            </h1>
            <p className="text-[var(--text-secondary)] text-sm mt-1">
              Track class-wide mastery, identify shared misconceptions, and orchestrate interactive learning sessions.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[var(--accent-royal)] text-white text-sm font-semibold hover:bg-opacity-90 shadow-sm transition"
            >
              <Plus className="w-4 h-4" />
              New Classroom
            </button>
            <button
              onClick={loadData}
              disabled={loading}
              className="p-2.5 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition"
              title="Refresh dashboard"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Quick Launchpad for Teaching Tools */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Link
            to="/lesson-planner"
            className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] hover:border-[var(--accent-royal)] transition flex flex-col items-center text-center gap-2 group"
          >
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center group-hover:scale-105 transition">
              <BookOpen className="w-5 h-5" />
            </div>
            <span className="text-xs font-semibold text-[var(--text-primary)]">AI Lesson Planner</span>
          </Link>
          <Link
            to="/decks"
            className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] hover:border-[var(--accent-royal)] transition flex flex-col items-center text-center gap-2 group"
          >
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center group-hover:scale-105 transition">
              <Presentation className="w-5 h-5" />
            </div>
            <span className="text-xs font-semibold text-[var(--text-primary)]">PPT Deck Generator</span>
          </Link>
          <Link
            to="/quizzes"
            className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] hover:border-[var(--accent-royal)] transition flex flex-col items-center text-center gap-2 group"
          >
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center group-hover:scale-105 transition">
              <BarChart3 className="w-5 h-5" />
            </div>
            <span className="text-xs font-semibold text-[var(--text-primary)]">Quiz Generator</span>
          </Link>
          <Link
            to="/join"
            className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] hover:border-[var(--accent-royal)] transition flex flex-col items-center text-center gap-2 group"
          >
            <div className="w-10 h-10 rounded-xl bg-rose-500/10 text-rose-400 flex items-center justify-center group-hover:scale-105 transition">
              <Radio className="w-5 h-5" />
            </div>
            <span className="text-xs font-semibold text-[var(--text-primary)]">Live Quiz Arena</span>
          </Link>
        </div>

        {/* Loading State */}
        {loading && !data && (
          <div className="flex flex-col items-center justify-center p-16 space-y-3">
            <div className="w-8 h-8 border-3 border-[var(--accent-royal)] border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-[var(--text-secondary)]">Loading classrooms and class misconception DNA...</span>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-sm">
            {error}
          </div>
        )}

        {/* Content */}
        {data && (
          <>
            {/* Top Class-Wide Misconceptions Widget */}
            {data.top_class_misconceptions.length > 0 && (
              <div className="p-5 rounded-2xl border border-amber-500/20 bg-amber-500/5 space-y-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-amber-400" />
                  <h2 className="text-base font-bold text-[var(--text-primary)]">
                    Class-Wide Misconception Signals & Reteach Recommendations
                  </h2>
                </div>
                <p className="text-xs text-[var(--text-secondary)]">
                  Aggregated from student diagnostic and quiz errors. Use these evidence-backed insights to guide tomorrow's classroom instruction.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                  {data.top_class_misconceptions.map((item, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] space-y-2"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <span className="text-xs font-semibold text-[var(--text-primary)]">
                            {item.skill_name}
                          </span>
                          <span className="block text-[11px] text-amber-400 font-mono">
                            Error Pattern: {item.error_type}
                          </span>
                        </div>
                        <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-500/10 text-amber-300 border border-amber-500/20">
                          {item.affected_students_count} Students
                        </span>
                      </div>
                      <div className="text-xs text-[var(--text-secondary)] bg-[var(--bg-hover)] p-2.5 rounded-lg border border-[var(--border)]">
                        <strong className="text-[var(--text-primary)]">Suggested Reteach: </strong>
                        {item.recommended_reteach_strategy}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Classrooms Section */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-[var(--text-primary)] flex items-center gap-2">
                  <Users className="w-5 h-5 text-[var(--accent-royal)]" />
                  Active Classrooms ({data.classrooms.length})
                </h2>
                <span className="text-xs text-[var(--text-secondary)]">
                  Total Students: <strong className="text-[var(--text-primary)]">{data.total_students}</strong>
                </span>
              </div>

              {data.classrooms.length === 0 ? (
                <div className="text-center p-10 border border-dashed border-[var(--border)] rounded-2xl bg-[var(--bg-card)] space-y-3">
                  <GraduationCap className="w-10 h-10 text-[var(--text-secondary)] mx-auto opacity-50" />
                  <h3 className="text-base font-semibold text-[var(--text-primary)]">No classrooms created yet</h3>
                  <p className="text-sm text-[var(--text-secondary)] max-w-md mx-auto">
                    Create your first classroom to begin enrolling students, monitoring diagnostic readiness, and assigning live quizzes.
                  </p>
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--accent-royal)] text-white text-sm font-semibold hover:bg-opacity-90 transition mt-2"
                  >
                    <Plus className="w-4 h-4" />
                    Create Classroom
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {data.classrooms.map((cls: ClassroomView) => (
                    <div
                      key={cls.id}
                      className="p-5 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] hover:border-[var(--accent-royal)] transition shadow-sm space-y-3 flex flex-col justify-between"
                    >
                      <div className="space-y-2">
                        <div className="flex items-start justify-between">
                          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                            {cls.grade_level}
                          </span>
                          <span className="text-xs text-[var(--text-secondary)] font-mono">
                            {cls.academic_year}
                          </span>
                        </div>
                        <h3 className="text-base font-bold text-[var(--text-primary)]">
                          {cls.name}
                        </h3>
                        {cls.academic_stream && (
                          <p className="text-xs text-[var(--text-secondary)]">
                            Stream: {cls.academic_stream}
                          </p>
                        )}
                      </div>

                      <div className="pt-3 border-t border-[var(--border)] space-y-2">
                        <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                          <span>Enrolled Students</span>
                          <span className="font-semibold text-[var(--text-primary)]">{cls.student_count}</span>
                        </div>
                        <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                          <span>Average Mastery</span>
                          <span className="font-semibold text-emerald-400">{cls.average_mastery_percentage}%</span>
                        </div>

                        <Link
                          to={`/teacher/classroom/${cls.id}`}
                          className="w-full inline-flex items-center justify-center gap-1.5 py-2 rounded-xl bg-[var(--bg-hover)] text-xs font-semibold text-[var(--text-primary)] hover:bg-[var(--accent-royal)] hover:text-white transition mt-2"
                        >
                          View Student Roster
                          <ChevronRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {/* Create Classroom Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="w-full max-w-md bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-[var(--text-primary)]">Create New Classroom</h3>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleCreateClassroom} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                    Classroom Name
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Grade 10 - Section A Mathematics"
                    className="w-full px-3 py-2 text-sm rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-royal)]"
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                      Grade Level
                    </label>
                    <select
                      value={gradeLevel}
                      onChange={(e) => setGradeLevel(e.target.value)}
                      className="w-full px-3 py-2 text-sm rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-royal)]"
                    >
                      <option value="Class 9">Class 9</option>
                      <option value="Class 10">Class 10</option>
                      <option value="Class 11">Class 11</option>
                      <option value="Class 12">Class 12</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                      Academic Year
                    </label>
                    <input
                      type="text"
                      value={academicYear}
                      onChange={(e) => setAcademicYear(e.target.value)}
                      className="w-full px-3 py-2 text-sm rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-royal)]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                    Stream / Track
                  </label>
                  <input
                    type="text"
                    value={stream}
                    onChange={(e) => setStream(e.target.value)}
                    placeholder="e.g. Science / Mathematics / CBSE"
                    className="w-full px-3 py-2 text-sm rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-royal)]"
                  />
                </div>

                {createMsg && (
                  <div
                    className={`p-3 rounded-xl text-xs ${createMsg.error
                        ? 'bg-rose-500/10 border border-rose-500/20 text-rose-300'
                        : 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-300'
                      }`}
                  >
                    {createMsg.text}
                  </div>
                )}

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 rounded-xl text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creating}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-[var(--accent-royal)] text-white hover:bg-opacity-90 disabled:opacity-50"
                  >
                    {creating ? 'Creating...' : 'Create Classroom'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
