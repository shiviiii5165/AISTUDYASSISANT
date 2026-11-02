import React, { useEffect, useState } from 'react';
import { 
  Building2, Users, GraduationCap, CheckCircle2, Award, 
  BarChart3, RefreshCw, Radio, Shield, KeyRound 
} from 'lucide-react';
import SchoolAdminLayout from '../../components/layout/SchoolAdminLayout';
import { fetchSchoolAdminOverview } from '../../lib/portalsApi';
import type { SchoolOverview } from '../../lib/portalsApi';

export default function SchoolAdminDashboard() {
  const [data, setData] = useState<SchoolOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchSchoolAdminOverview();
      setData(res);
    } catch (err: any) {
      console.error('Failed to load school admin overview:', err);
      setError(err?.response?.data?.detail || err.message || 'Failed to load school admin overview.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <SchoolAdminLayout title="School Administration">
      <div className="max-w-6xl mx-auto p-4 md:p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--border)] pb-5">
          <div>
            <div className="flex items-center gap-2 text-sm text-[var(--accent-royal)] font-semibold uppercase tracking-wider">
              <Building2 className="w-4 h-4" />
              Institutional Management
            </div>
            <h1 className="text-2xl md:text-3xl font-display font-bold text-[var(--text-primary)] mt-1">
              School Administration Portal
            </h1>
            <p className="text-[var(--text-secondary)] text-sm mt-1">
              Oversee faculty assignments, license allocations, and multi-classroom mastery benchmarks.
            </p>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="p-2.5 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition self-start md:self-auto"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Loading */}
        {loading && !data && (
          <div className="flex flex-col items-center justify-center p-16 space-y-3">
            <div className="w-8 h-8 border-3 border-[var(--accent-royal)] border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-[var(--text-secondary)]">Loading institutional records...</span>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-sm">
            {error}
          </div>
        )}

        {/* Content */}
        {data && (
          <>
            {/* School Info Banner */}
            <div className="p-6 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] flex flex-col md:flex-row md:items-center justify-between gap-5 shadow-sm">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center font-bold text-2xl text-blue-400">
                  <Building2 className="w-8 h-8" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-bold font-display text-[var(--text-primary)]">
                      {data.school_name}
                    </h2>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase tracking-wide">
                      {data.subscription_tier} Tier
                    </span>
                  </div>
                  <p className="text-xs text-[var(--text-secondary)] mt-1 font-mono">
                    Domain: {data.domain || 'learnbygenie.edu'} • ID: {data.school_id}
                  </p>
                </div>
              </div>

              {/* License Seat Usage */}
              <div className="w-full md:w-64 space-y-2 border-t md:border-t-0 md:border-l border-[var(--border)] pt-4 md:pt-0 md:pl-6">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[var(--text-secondary)]">Seat Allocation</span>
                  <span className="font-semibold text-[var(--text-primary)]">
                    {data.allocated_seats} / {data.licensed_seats}
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-[var(--border)] overflow-hidden">
                  <div
                    style={{ width: `${Math.min(100, (data.allocated_seats / data.licensed_seats) * 100)}%` }}
                    className="h-full bg-[var(--accent-royal)] rounded-full"
                  />
                </div>
                <div className="text-[11px] text-[var(--text-secondary)]">
                  {data.licensed_seats - data.allocated_seats} licenses remaining
                </div>
              </div>
            </div>

            {/* School Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)]">
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>Total Enrolled</span>
                  <Users className="w-4 h-4 text-blue-400" />
                </div>
                <div className="text-2xl font-bold text-[var(--text-primary)] mt-1">
                  {data.stats.total_students}
                </div>
                <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">Active students</div>
              </div>

              <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)]">
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>Faculty Staff</span>
                  <GraduationCap className="w-4 h-4 text-purple-400" />
                </div>
                <div className="text-2xl font-bold text-[var(--text-primary)] mt-1">
                  {data.stats.total_teachers}
                </div>
                <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">Assigned teachers</div>
              </div>

              <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)]">
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>School Mastery</span>
                  <Award className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-2xl font-bold text-emerald-400 mt-1">
                  {data.stats.average_school_mastery}%
                </div>
                <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">Curriculum benchmark</div>
              </div>

              <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)]">
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>Live Quizzes</span>
                  <Radio className="w-4 h-4 text-rose-400" />
                </div>
                <div className="text-2xl font-bold text-rose-400 mt-1">
                  {data.stats.active_live_quizzes_today}
                </div>
                <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">Completed today</div>
              </div>
            </div>

            {/* Faculty Roster */}
            <div className="space-y-3">
              <h3 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
                <GraduationCap className="w-5 h-5 text-[var(--accent-royal)]" />
                Faculty Members & Departments
              </h3>

              <div className="border border-[var(--border)] rounded-2xl overflow-hidden bg-[var(--bg-card)]">
                <table className="w-full text-left text-sm">
                  <thead className="bg-[var(--bg-hover)] text-xs text-[var(--text-secondary)] border-b border-[var(--border)]">
                    <tr>
                      <th className="py-3 px-4">Faculty Member</th>
                      <th className="py-3 px-4">Department</th>
                      <th className="py-3 px-4">Classrooms Assigned</th>
                      <th className="py-3 px-4 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)]">
                    {data.teachers.map((t) => (
                      <tr key={t.teacher_id} className="hover:bg-[var(--bg-hover)] transition">
                        <td className="py-3 px-4">
                          <div className="font-semibold text-[var(--text-primary)]">
                            {t.teacher_name}
                          </div>
                          <div className="text-xs text-[var(--text-secondary)] font-mono">
                            {t.email}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-xs text-[var(--text-secondary)]">
                          {t.department}
                        </td>
                        <td className="py-3 px-4 text-xs font-semibold text-[var(--text-primary)]">
                          {t.assigned_classrooms_count} Classrooms
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            {t.status}
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
    </SchoolAdminLayout>
  );
}
