import React, { useState } from 'react';
import {
  BookOpen, MessageSquare, Target, Menu, X, LogOut, LifeBuoy,
  Presentation, PlayCircle, GraduationCap, Map, HelpCircle,
  ChevronLeft, ChevronRight, Radio,
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { useAuthStore } from '../store/useAuthStore';
import { useSidebarCollapse } from '../hooks/useSidebarCollapse';
import { pageTransition } from '../lib/motion';
import ProfileDropdown from './ProfileDropdown';

/**
 * Shared app shell.
 *
 * Nav is grouped by job rather than listed flat, so the teaching tools read as
 * a first-class set instead of being scattered between study tools. Same eight
 * destinations, same labels, same routes as before.
 */
const NAV_GROUPS: { heading: string; items: { path: string; label: string; icon: React.ElementType }[] }[] = [
  {
    heading: 'Study',
    items: [
      { path: '/dashboard', label: 'Dashboard', icon: Target },
      { path: '/teach', label: 'Teach Me', icon: GraduationCap },
      { path: '/library', label: 'My Library', icon: BookOpen },
      { path: '/chat', label: 'AI Chat', icon: MessageSquare },
    ],
  },
  {
    heading: 'Teach',
    items: [
      { path: '/lesson-planner', label: 'AI Lesson Planner', icon: Map },
      { path: '/decks', label: 'PPT Generator', icon: Presentation },
      { path: '/video', label: 'Video Generator', icon: PlayCircle },
      { path: '/quizzes', label: 'Quiz Generator', icon: HelpCircle },
      { path: '/join', label: 'Live Quiz Room', icon: Radio },
    ],
  },
];

const SUPPORT_ITEM = { path: '/support', label: 'Support', icon: LifeBuoy };

// Routes where content manages its own internal scroll — the main area must be
// fixed-height so flex-1 children (chat list, teach panel, history sidebars) fill the viewport correctly.
const FIXED_HEIGHT_ROUTES = new Set(['/chat', '/teach', '/decks', '/quizzes', '/lesson-planner']);

const AppLayout = ({ children, title }: { children: React.ReactNode; title: React.ReactNode }) => {
  const location = useLocation();
  const isFixedHeight = FIXED_HEIGHT_ROUTES.has(location.pathname);

  const { user, signOut } = useAuthStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { collapsed, toggle } = useSidebarCollapse('app-nav');
  const prefersReducedMotion = useReducedMotion();

  const getInitials = (name?: string) => {
    return name ? name.charAt(0).toUpperCase() : 'U';
  };

  const avatarUrl = user?.avatar_url;

  /** Active state: blue text on the pale blue surface is 6.49:1 (AA). */
  const navLinkClass = (isActive: boolean, dense: boolean, iconOnly: boolean) =>
    [
      'flex items-center rounded-lg text-sm font-medium transition-colors',
      iconOnly ? 'justify-center p-2.5' : (dense ? 'gap-3 px-3 py-2' : 'gap-3 px-3 py-2.5'),
      isActive
        ? 'bg-[var(--accent-blue-light)] text-[var(--accent-blue-text)]'
        : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]',
    ].join(' ');

  const renderNavItem = (
    { path, label, icon: Icon }: { path: string; label: string; icon: React.ElementType },
    opts: { dense: boolean; onNavigate?: () => void; iconOnly?: boolean },
  ) => {
    const isActive = location.pathname === path;
    return (
      <Link
        key={path}
        to={path}
        aria-current={isActive ? 'page' : undefined}
        aria-label={opts.iconOnly ? label : undefined}
        title={opts.iconOnly ? label : undefined}
        onClick={opts.onNavigate}
        className={navLinkClass(isActive, opts.dense, !!opts.iconOnly)}
      >
        <Icon className="h-[18px] w-[18px] shrink-0" aria-hidden={!opts.iconOnly} />
        {!opts.iconOnly && label}
      </Link>
    );
  };

  return (
    <div className="flex h-screen bg-[var(--bg-primary)]">
      {/* ── Desktop Sidebar ── */}
      <aside
        className={`hidden lg:flex shrink-0 flex-col border-r border-[var(--border)] bg-[var(--bg-card)] h-full overflow-hidden transition-[width] duration-200 ${collapsed ? 'w-16' : 'w-60'}`}
      >
        {/* Brand */}
        <div className={`flex items-center border-b border-[var(--border)] ${collapsed ? 'justify-center px-3 py-4' : 'px-5 py-4'}`}>
          <Link
            to="/dashboard"
            aria-label="TeachGenie home"
            className="flex items-center gap-2.5 rounded-lg font-display text-lg font-bold text-[var(--text-primary)]"
          >
            <img src="/assets/genie-default.png" alt="" width={32} height={32} className="h-8 w-8 shrink-0 object-contain" />
            {!collapsed && <span>TeachGenie</span>}
          </Link>
        </div>

        <nav aria-label="Main" className="flex-1 overflow-y-auto px-2 py-3">
          {collapsed ? (
            /* Icon-only rail */
            <div className="space-y-1">
              {[...NAV_GROUPS.flatMap(g => g.items), SUPPORT_ITEM].map((item) =>
                renderNavItem(item, { dense: true, iconOnly: true })
              )}
            </div>
          ) : (
            /* Full labels */
            <div className="space-y-5">
              {NAV_GROUPS.map((group) => (
                <div key={group.heading}>
                  <h2 className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                    {group.heading}
                  </h2>
                  <div className="space-y-0.5">
                    {group.items.map((item) => renderNavItem(item, { dense: true }))}
                  </div>
                </div>
              ))}
              <div className="border-t border-[var(--border)] pt-4">
                {renderNavItem(SUPPORT_ITEM, { dense: true })}
              </div>
            </div>
          )}
        </nav>

        {/* Collapse toggle */}
        <div className="border-t border-[var(--border)] p-2">
          <button
            type="button"
            onClick={toggle}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className={`flex w-full items-center rounded-lg px-2.5 py-2 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] ${collapsed ? 'justify-center' : 'gap-2'}`}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4 shrink-0" aria-hidden="true" />
            ) : (
              <>
                <ChevronLeft className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span>Collapse</span>
              </>
            )}
          </button>
        </div>
      </aside>

      {/* ── Mobile Overlay ── */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-black/30 backdrop-blur-sm"
            onClick={() => setMobileMenuOpen(false)}
          />
          <aside
            className="absolute bottom-0 left-0 top-0 flex w-64 flex-col bg-[var(--bg-card)] shadow-xl"
            aria-label="Main"
          >
            <div className="flex items-center justify-between border-b border-[var(--border)] px-5 py-4">
              <Link
                to="/dashboard"
                className="flex items-center gap-2 rounded-lg font-display text-lg font-bold text-[var(--text-primary)]"
              >
                <img src="/logo.png" alt="" width={32} height={32} className="h-8 w-8 object-contain" />
                TeachGenie
              </Link>
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                aria-label="Close menu"
                className="rounded-lg p-1.5 hover:bg-[var(--bg-hover)]"
              >
                <X className="h-5 w-5 text-[var(--text-secondary)]" aria-hidden="true" />
              </button>
            </div>

            <nav className="flex-1 space-y-5 overflow-y-auto p-3">
              {NAV_GROUPS.map((group) => (
                <div key={group.heading}>
                  <h2 className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                    {group.heading}
                  </h2>
                  <div className="space-y-0.5">
                    {group.items.map((item) =>
                      renderNavItem(item, { dense: false, onNavigate: () => setMobileMenuOpen(false) }),
                    )}
                  </div>
                </div>
              ))}

              <div className="border-t border-[var(--border)] pt-4">
                {renderNavItem(SUPPORT_ITEM, {
                  dense: false,
                  onNavigate: () => setMobileMenuOpen(false),
                })}
              </div>
            </nav>

            <div className="border-t border-[var(--border)] p-3">
              <button
                type="button"
                onClick={signOut}
                className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-red-700 transition-colors hover:bg-red-50"
              >
                <LogOut className="h-5 w-5" aria-hidden="true" />
                Log out
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* ── Main Content ── */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Topbar */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-[var(--border)] bg-[var(--bg-card)] px-4 md:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open menu"
              aria-expanded={mobileMenuOpen}
              className="rounded-lg p-2 transition-colors hover:bg-[var(--bg-hover)] lg:hidden"
            >
              <Menu className="h-5 w-5 text-[var(--text-secondary)]" aria-hidden="true" />
            </button>
            <h1 className="truncate font-display text-base font-semibold text-[var(--text-primary)]">
              {title}
            </h1>
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden text-xs font-medium text-[var(--text-muted)] sm:block mr-2">
              {new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
            </span>
            <ProfileDropdown />
          </div>
        </header>

        {/* Page Content */}
        {isFixedHeight ? (
          /* Fixed-height shell for windowed pages (Chat, Teach Me).
             flex-1 children fill the remaining viewport height correctly here. */
          <main
            className="flex flex-1 w-full overflow-hidden"
            aria-label="Main"
          >
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={location.pathname}
                variants={prefersReducedMotion ? undefined : pageTransition}
                initial="hidden"
                animate="show"
                exit="exit"
                className="flex flex-1 overflow-hidden"
              >
                {children}
              </motion.div>
            </AnimatePresence>
          </main>
        ) : (
          /* Scrollable pages: native scroll, no wrapper positioning */
          <div className="min-h-0 flex-1 overflow-y-auto">
            <main className="w-full pb-8">
              <AnimatePresence mode="wait" initial={false}>
                <motion.div
                  key={location.pathname}
                  variants={prefersReducedMotion ? undefined : pageTransition}
                  initial="hidden"
                  animate="show"
                  exit="exit"
                >
                  {children}
                </motion.div>
              </AnimatePresence>
            </main>
          </div>
        )}
      </div>
    </div>
  );
};

export default AppLayout;
