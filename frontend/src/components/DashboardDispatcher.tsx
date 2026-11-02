import React, { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/useAuthStore';
import Dashboard from '../pages/Dashboard';

export default function DashboardDispatcher() {
  const { activeRole, authorizedRoles, loading, session } = useAuthStore();
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    // 2-second fallback timer: never trap user on loading screen
    const timer = setTimeout(() => {
      setTimedOut(true);
    }, 2000);
    return () => clearTimeout(timer);
  }, []);

  // Only show loading if we don't have session yet and haven't timed out
  if (loading && !timedOut && !session) {
    return (
      <div className="min-h-[100dvh] bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-2 border-[var(--brand-primary)] border-t-transparent rounded-full animate-spin" />
          <span className="text-[var(--text-secondary)] text-sm font-medium">Loading your portal...</span>
        </div>
      </div>
    );
  }

  if (!session) {
    if (
      import.meta.env.DEV &&
      typeof window !== 'undefined' &&
      (window.location.search.includes('mock_auth=true') ||
        localStorage.getItem('learnbygenie_dev_auth') === 'true' ||
        localStorage.getItem('teachgenie_dev_auth') === 'true')
    ) {
      // Dev mode allows preview
    } else {
      return <Navigate to="/auth" replace />;
    }
  }

  // If user only has a non-student primary role or switched to that role, dispatch to their portal
  const effectiveRole = activeRole || (authorizedRoles && authorizedRoles[0]) || 'student';

  if (effectiveRole === 'teacher' && authorizedRoles.includes('teacher')) {
    return <Navigate to="/teacher" replace />;
  }
  if (effectiveRole === 'parent' && authorizedRoles.includes('parent')) {
    return <Navigate to="/parent" replace />;
  }
  if (effectiveRole === 'school_admin' && authorizedRoles.includes('school_admin')) {
    return <Navigate to="/school-admin" replace />;
  }
  if (effectiveRole === 'content_creator' && authorizedRoles.includes('content_creator')) {
    return <Navigate to="/creator" replace />;
  }
  if (effectiveRole === 'super_admin' && authorizedRoles.includes('super_admin')) {
    return <Navigate to="/admin" replace />;
  }

  // Default: Student Portal Dashboard
  return <Dashboard />;
}
