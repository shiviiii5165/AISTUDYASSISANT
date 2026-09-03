import { useState, useCallback } from 'react';

/**
 * Persist a sidebar's collapsed state in localStorage.
 * Mobile drawer behavior is unaffected — this only governs the desktop rail.
 *
 * @param storageKey - unique key scoped to `sidebar-` prefix, e.g. "app-nav"
 * @param defaultCollapsed - initial state when no localStorage entry exists
 */
export function useSidebarCollapse(storageKey: string, defaultCollapsed = false) {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      const raw = localStorage.getItem(`sidebar-${storageKey}`);
      return raw !== null ? raw === 'true' : defaultCollapsed;
    } catch {
      return defaultCollapsed;
    }
  });

  const toggle = useCallback(() => {
    setCollapsed(prev => {
      const next = !prev;
      try { localStorage.setItem(`sidebar-${storageKey}`, String(next)); } catch {}
      return next;
    });
  }, [storageKey]);

  return { collapsed, toggle };
}
