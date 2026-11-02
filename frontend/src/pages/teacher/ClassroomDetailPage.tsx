import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  ArrowLeft, Users, CheckCircle2, AlertCircle, RefreshCw, 
  Search, ShieldAlert, GraduationCap, ChevronRight 
} from 'lucide-react';
import AppLayout from '../../components/AppLayout';
import { fetchClassroomRoster } from '../../lib/portalsApi';
import type { ClassroomRosterItem } from '../../lib/portalsApi';

export default function ClassroomDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [roster, setRoster] = useState<ClassroomRosterItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const loadRoster = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const res = await fetchClassroomRoster(id);
      setRoster(res);
    } catch (err: any) {
      console.error('Failed to load classroom roster:', err);
      setError(err?.response?.data?.detail || err.message || 'Failed to load classroom roster.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRoster();
  }, [id]);

  const filteredRoster = roster.filter(
    (st) =>
      st.student_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      st.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      st.student_id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <AppLayout title="Classroom Student Roster">
      <div className="max-w-6xl mx-auto p-4 md:p-6 space-y-6">
        {/* Header & Breadcrumb */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--border)] pb-5">
          <div>
            <Link
              to="/teacher"
              className="inline-flex items-center gap-2 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition mb-2"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Teacher Command Center
            </Link>
            <h1 className="text-2xl font-bold font-display text-[var(--text-primary)]">
              Classroom Student Roster & Mastery Ledger
            </h1>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Classroom ID: <span className="font-mono">{id}</span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 text-[var(--text-secondary)] absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search students..."
                className="pl-9 pr-3 py-2 text-xs rounded-xl border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-royal)] w-56"
              />
            </div>
            <button
              onClick={loadRoster}
              disabled={loading}
              className="p-2 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Loading */}
        {loading && roster.length === 0 && (
          <div className="flex flex-col items-center justify-center p-16 space-y-3">
            <div className="w-8 h-8 border-3 border-[var(--accent-royal)] border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-[var(--text-secondary)]">Retrieving enrolled students...</span>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-sm">
            {error}
          </div>
        )}

        {/* Roster Table */}
        {!loading && (
          <div className="border border-[var(--border)] rounded-2xl overflow-hidden bg-[var(--bg-card)]">
            <table className="w-full text-left text-sm">
              <thead className="bg-[var(--bg-hover)] text-xs text-[var(--text-secondary)] border-b border-[var(--border)]">
                <tr>
                  <th className="py-3 px-4">Student</th>
                  <th className="py-3 px-4">Diagnostic Status</th>
                  <th className="py-3 px-4">Mastery %</th>
                  <th className="py-3 px-4">Pending Repairs</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {filteredRoster.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-10 text-center text-xs text-[var(--text-secondary)]">
                      No enrolled students found matching query.
                    </td>
                  </tr>
                ) : (
                  filteredRoster.map((st) => (
                    <tr key={st.student_id} className="hover:bg-[var(--bg-hover)] transition">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-[var(--text-primary)]">
                          {st.student_name}
                        </div>
                        <div className="text-xs text-[var(--text-secondary)] font-mono">
                          {st.email}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {st.diagnostic_completed ? (
                          <span className="inline-flex items-center gap-1 text-xs text-emerald-400">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Completed
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs text-amber-400">
                            <AlertCircle className="w-3.5 h-3.5" />
                            Pending Baseline
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-2 rounded-full bg-[var(--border)] overflow-hidden">
                            <div
                              style={{ width: `${st.mastery_percentage}%` }}
                              className="h-full bg-emerald-500 rounded-full"
                            />
                          </div>
                          <span className="text-xs font-semibold text-[var(--text-primary)]">
                            {st.mastery_percentage}%
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {st.pending_repairs_count > 0 ? (
                          <span className="px-2 py-0.5 rounded text-xs bg-amber-500/10 text-amber-400 border border-amber-500/20 font-medium">
                            {st.pending_repairs_count} Repairs
                          </span>
                        ) : (
                          <span className="text-xs text-[var(--text-secondary)]">None</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Link
                          to={`/parent/child/${st.student_id}`}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--bg-primary)] hover:border-[var(--accent-royal)] text-xs font-medium text-[var(--text-primary)] transition"
                        >
                          View Skills
                          <ChevronRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
