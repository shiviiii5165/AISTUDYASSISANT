import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, ArrowLeft, LogOut, LifeBuoy } from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';
import type { UserRole } from '../store/useAuthStore';
import { BRAND } from '../config/branding';

interface AccessDeniedPageProps {
  requiredRoles?: UserRole[];
}

export default function AccessDeniedPage({ requiredRoles = [] }: AccessDeniedPageProps) {
  const navigate = useNavigate();
  const { user, activeRole, authorizedRoles, signOut } = useAuthStore();

  const getDefaultPortalPath = (role: UserRole) => {
    switch (role) {
      case 'teacher':
        return '/teacher';
      case 'parent':
        return '/parent';
      case 'school_admin':
        return '/school-admin';
      case 'content_creator':
        return '/creator';
      case 'super_admin':
        return '/admin';
      default:
        return '/dashboard';
    }
  };

  const handleReturn = () => {
    const targetRole = (authorizedRoles && authorizedRoles[0]) || activeRole || 'student';
    navigate(getDefaultPortalPath(targetRole));
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] flex flex-col items-center justify-center p-4 sm:p-6 text-[var(--text-primary)]">
      <div className="max-w-md w-full bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl p-6 sm:p-8 shadow-xl text-center space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-amber-50 dark:bg-amber-950/40 text-amber-900 dark:text-amber-900 mx-auto flex items-center justify-center border border-amber-200 dark:border-amber-800">
          <ShieldAlert className="w-8 h-8" />
        </div>

        <div className="space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-amber-900 dark:text-amber-900 bg-amber-100 dark:bg-amber-900/40 px-2.5 py-1 rounded-full">
            HTTP 403 • Authorization Required
          </span>
          <h1 className="text-2xl font-display font-bold text-[var(--text-primary)]">
            Restricted Portal Access
          </h1>
          <p className="text-sm text-[var(--text-secondary)]">
            Your account does not have permission to access this section of {BRAND.name}.
          </p>
        </div>

        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-4 text-xs space-y-2 text-left">
          <div className="flex justify-between items-center">
            <span className="text-[var(--text-muted)]">Signed in as:</span>
            <span className="font-semibold text-[var(--text-primary)] truncate max-w-[200px]">
              {user?.email || 'Authenticated User'}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[var(--text-muted)]">Your Authorized Roles:</span>
            <div className="flex gap-1 flex-wrap">
              {authorizedRoles.map((r) => (
                <span
                  key={r}
                  className="px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border)] font-mono text-[10px] text-[var(--text-primary)]"
                >
                  {r}
                </span>
              ))}
            </div>
          </div>
          {requiredRoles.length > 0 && (
            <div className="flex justify-between items-center">
              <span className="text-[var(--text-muted)]">Required Role(s):</span>
              <span className="font-mono text-[10px] text-amber-900 dark:text-amber-900 font-bold">
                {requiredRoles.join(' or ')}
              </span>
            </div>
          )}
        </div>

        <div className="flex flex-col sm:flex-row gap-3 pt-2">
          <button
            type="button"
            onClick={handleReturn}
            className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-[var(--accent-blue)] text-white text-sm font-semibold hover:opacity-95 transition shadow-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Go to My Portal
          </button>
          <button
            type="button"
            onClick={() => signOut()}
            className="flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] text-sm font-semibold hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] transition"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}

