import React, { useState, useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/useAuthStore';
import type { UserRole } from '../store/useAuthStore';
import AccessDeniedPage from '../pages/AccessDeniedPage';

interface RoleGuardProps {
  allowedRoles: UserRole[];
  children: React.ReactNode;
}

export default function RoleGuard({ allowedRoles, children }: RoleGuardProps) {
  const location = useLocation();
  const { session, loading, authorizedRoles } = useAuthStore();
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setTimedOut(true);
    }, 2000);
    return () => clearTimeout(timer);
  }, []);

  if (loading && !timedOut && !session) {
    return (
      <div className="min-h-[100dvh] bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-2 border-[var(--brand-primary)] border-t-transparent rounded-full animate-spin" />
          <span className="text-[var(--text-secondary)] text-sm font-medium">Verifying portal authorization...</span>
        </div>
      </div>
    );
  }

  // Check authentication
  if (!session) {
    if (
      import.meta.env.DEV &&
      typeof window !== 'undefined' &&
      (window.location.search.includes('mock_auth=true') ||
        localStorage.getItem('learnbygenie_dev_auth') === 'true' ||
        localStorage.getItem('teachgenie_dev_auth') === 'true')
    ) {
      return <>{children}</>;
    }
    return <Navigate to="/auth" state={{ from: location }} replace />;
  }

  // Super admin has omni-portal authorization
  if (authorizedRoles.includes('super_admin')) {
    return <>{children}</>;
  }

  // Check role authorization overlap
  const isAuthorized = allowedRoles.some((role) => authorizedRoles.includes(role));

  if (!isAuthorized) {
    return <AccessDeniedPage requiredRoles={allowedRoles} />;
  }

  return <>{children}</>;
}
