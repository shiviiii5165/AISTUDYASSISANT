import React, { useEffect, useState } from 'react';
import { 
  ShieldCheck, Activity, Cpu, Database, Server, RefreshCw, 
  AlertTriangle, CheckCircle2, UserCog, Zap, Lock 
} from 'lucide-react';
import AppLayout from '../../components/AppLayout';
import { 
  fetchSuperAdminOverview, 
  updateUserRole 
} from '../../lib/portalsApi';
import type { 
  SystemHealthOverview, 
  LLMProviderTelemetry 
} from '../../lib/portalsApi';

export default function SuperAdminDashboard() {
  const [data, setData] = useState<SystemHealthOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Role Assignment State
  const [targetUserId, setTargetUserId] = useState('');
  const [newRole, setNewRole] = useState('teacher');
  const [updatingRole, setUpdatingRole] = useState(false);
  const [roleMsg, setRoleMsg] = useState<{ text: string; error: boolean } | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchSuperAdminOverview();
      setData(res);
    } catch (err: any) {
      console.error('Failed to load super admin overview:', err);
      setError(err?.response?.data?.detail || err.message || 'Failed to load system telemetry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleUpdateRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetUserId.trim()) return;

    try {
      setUpdatingRole(true);
      setRoleMsg(null);
      const res = await updateUserRole(targetUserId.trim(), newRole);
      setRoleMsg({ text: res.message, error: false });
      setTargetUserId('');
    } catch (err: any) {
      setRoleMsg({
        text: err?.response?.data?.detail || err.message || 'Failed to assign role.',
        error: true,
      });
    } finally {
      setUpdatingRole(false);
    }
  };

  return (
    <AppLayout title="Super Administrator Telemetry">
      <div className="max-w-6xl mx-auto p-4 md:p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--border)] pb-5">
          <div>
            <div className="flex items-center gap-2 text-sm text-rose-400 font-semibold uppercase tracking-wider">
              <ShieldCheck className="w-4 h-4" />
              Platform Reliability & Governance
            </div>
            <h1 className="text-2xl md:text-3xl font-display font-bold text-[var(--text-primary)] mt-1">
              Super Admin Control Plane
            </h1>
            <p className="text-[var(--text-secondary)] text-sm mt-1">
              Live multi-LLM telemetry, failover circuit breakers, and institutional RBAC authority.
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
            <span className="text-sm text-[var(--text-secondary)]">Sampling system telemetry & LLM latencies...</span>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-sm">
            {error}
          </div>
        )}

        {/* Telemetry Overview */}
        {data && (
          <>
            {/* Top Stat Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)]">
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>Service Status</span>
                  <Server className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-xl font-bold text-emerald-400 mt-1 capitalize">
                  {data.service_status}
                </div>
                <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                  Uptime: {data.uptime_percentage}%
                </div>
              </div>

              <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)]">
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>Database Tier</span>
                  <Database className="w-4 h-4 text-blue-400" />
                </div>
                <div className="text-xl font-bold text-[var(--text-primary)] mt-1 capitalize">
                  {data.database_health}
                </div>
                <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                  Fail-closed resilient
                </div>
              </div>

              <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)]">
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>Active Sessions</span>
                  <Activity className="w-4 h-4 text-purple-400" />
                </div>
                <div className="text-xl font-bold text-purple-400 mt-1">
                  {data.total_active_users.toLocaleString()}
                </div>
                <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                  Across 6 portals
                </div>
              </div>

              <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)]">
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>Circuit Breaker</span>
                  <Zap className="w-4 h-4 text-amber-400" />
                </div>
                <div className="text-xl font-bold text-amber-400 mt-1">
                  Healthy
                </div>
                <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                  Zero trips recorded
                </div>
              </div>
            </div>

            {/* Multi-LLM Provider Telemetry Table */}
            <div className="space-y-3">
              <h3 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
                <Cpu className="w-5 h-5 text-[var(--accent-royal)]" />
                AI Inference Routing & Provider Latency
              </h3>

              <div className="border border-[var(--border)] rounded-2xl overflow-hidden bg-[var(--bg-card)]">
                <table className="w-full text-left text-sm">
                  <thead className="bg-[var(--bg-hover)] text-xs text-[var(--text-secondary)] border-b border-[var(--border)]">
                    <tr>
                      <th className="py-3 px-4">Provider / Model Tier</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">P95 Latency</th>
                      <th className="py-3 px-4">Tokens Consumed</th>
                      <th className="py-3 px-4 text-right">Error Rate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)]">
                    {data.llm_telemetry.map((llm, idx) => (
                      <tr key={idx} className="hover:bg-[var(--bg-hover)] transition">
                        <td className="py-3 px-4 font-semibold text-[var(--text-primary)]">
                          {llm.provider_name}
                        </td>
                        <td className="py-3 px-4">
                          <span className="inline-flex items-center gap-1.5 text-xs text-emerald-400">
                            <span className="w-2 h-2 rounded-full bg-emerald-400" />
                            {llm.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-xs font-mono text-[var(--text-secondary)]">
                          {llm.latency_ms} ms
                        </td>
                        <td className="py-3 px-4 text-xs font-mono text-[var(--text-primary)]">
                          {llm.tokens_used_today.toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-xs font-semibold text-right text-emerald-400">
                          {llm.error_rate_percentage}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* User Role Authority Tool */}
            <div className="p-5 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] space-y-4 shadow-sm">
              <div className="flex items-center gap-2">
                <UserCog className="w-5 h-5 text-purple-400" />
                <div>
                  <h3 className="text-base font-bold text-[var(--text-primary)]">
                    Institutional Role Authority & User Management
                  </h3>
                  <p className="text-xs text-[var(--text-secondary)]">
                    Grant administrative, faculty, or content creator permissions with immutable server-side enforcement.
                  </p>
                </div>
              </div>

              <form onSubmit={handleUpdateRole} className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                <div className="sm:col-span-2">
                  <input
                    type="text"
                    value={targetUserId}
                    onChange={(e) => setTargetUserId(e.target.value)}
                    placeholder="User ID (UUID or email)"
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-royal)] font-mono"
                    required
                  />
                </div>
                <div className="flex gap-2">
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-royal)]"
                  >
                    <option value="student">Student</option>
                    <option value="parent">Parent</option>
                    <option value="teacher">Teacher</option>
                    <option value="school_admin">School Admin</option>
                    <option value="content_creator">Content Creator</option>
                    <option value="super_admin">Super Admin</option>
                  </select>
                  <button
                    type="submit"
                    disabled={updatingRole}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-[var(--accent-royal)] text-white hover:bg-opacity-90 transition whitespace-nowrap disabled:opacity-50"
                  >
                    {updatingRole ? 'Updating...' : 'Assign Role'}
                  </button>
                </div>
              </form>

              {roleMsg && (
                <div
                  className={`p-3 rounded-xl text-xs ${
                    roleMsg.error
                      ? 'bg-rose-500/10 border border-rose-500/20 text-rose-300'
                      : 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-300'
                  }`}
                >
                  {roleMsg.text}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}
