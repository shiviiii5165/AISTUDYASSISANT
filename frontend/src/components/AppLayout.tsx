import React, { useState } from 'react';
import {
  BookOpen, MessageSquare, Target, Bell, Menu, X, LogOut, LifeBuoy,
  Presentation, PlayCircle, GraduationCap, Map,
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/useAuthStore';

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
    ],
  },
];

const SUPPORT_ITEM = { path: '/support', label: 'Support', icon: LifeBuoy };

const AppLayout = ({ children, title }: { children: React.ReactNode; title: React.ReactNode }) => {
  const location = useLocation();

  const { user, signOut } = useAuthStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);

  const getInitials = (name?: string) => {
    return name ? name.charAt(0).toUpperCase() : 'U';
  };

  const avatarUrl = user?.avatar_url;

  /** Active state: green text on the pale green surface is 6.49:1 (AA). */
  const navLinkClass = (isActive: boolean, dense: boolean) =>
    [
      'flex items-center gap-3 rounded-lg text-sm font-medium transition-colors',
      dense ? 'px-3 py-2' : 'px-3 py-2.5',
      isActive
        ? 'bg-[var(--accent-green-light)] text-[var(--accent-green-text)]'
        : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]',
    ].join(' ');

  const renderNavItem = (
    { path, label, icon: Icon }: { path: string; label: string; icon: React.ElementType },
    opts: { dense: boolean; onNavigate?: () => void },
  ) => {
    const isActive = location.pathname === path;
    return (
      <Link
        key={path}
        to={path}
        aria-current={isActive ? 'page' : undefined}
        onClick={opts.onNavigate}
        className={navLinkClass(isActive, opts.dense)}
      >
        <Icon className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
        {label}
      </Link>
    );
  };

  return (
    <div className="flex min-h-[100dvh] bg-[var(--bg-primary)]">
      {/* ── Desktop Sidebar ── */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--bg-card)] md:flex">
        <div className="px-5 py-4">
          <Link
            to="/dashboard"
            className="flex items-center gap-2.5 rounded-lg font-display text-lg font-bold text-[var(--text-primary)]"
          >
            <img src="/logo.png" alt="" width={32} height={32} className="h-8 w-8 object-contain" />
            TeachGenie
          </Link>
        </div>

        <nav aria-label="Main" className="flex-1 space-y-5 overflow-y-auto px-3 pb-4">
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
        </nav>
      </aside>

      {/* ── Mobile Overlay ── */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
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
                Sign Out
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* ── Main Content ── */}
      <div className="flex h-[100dvh] min-w-0 flex-1 flex-col overflow-hidden">
        {/* Topbar */}
        <header className="relative z-10 flex h-14 shrink-0 items-center justify-between border-b border-[var(--border)] bg-[var(--bg-card)] px-4 md:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open menu"
              aria-expanded={mobileMenuOpen}
              className="rounded-lg p-2 transition-colors hover:bg-[var(--bg-hover)] md:hidden"
            >
              <Menu className="h-5 w-5 text-[var(--text-secondary)]" aria-hidden="true" />
            </button>
            <h1 className="truncate font-display text-base font-semibold text-[var(--text-primary)]">
              {title}
            </h1>
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden text-xs font-medium text-[var(--text-muted)] sm:block">
              {new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
            </span>

            <div className="relative">
              <button
                type="button"
                onClick={() => {
                  setShowNotifications(!showNotifications);
                  setShowProfileMenu(false);
                }}
                aria-label="Notifications"
                aria-expanded={showNotifications}
                aria-haspopup="true"
                className="rounded-lg p-2 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)]"
              >
                <Bell className="h-[18px] w-[18px]" aria-hidden="true" />
              </button>
              {showNotifications && (
                <>
                  <div className="fixed inset-0 z-20" onClick={() => setShowNotifications(false)} />
                  <div className="absolute right-0 top-full z-30 mt-2 w-64 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] py-2 shadow-[var(--shadow-lg)]">
                    <div className="border-b border-[var(--border)] px-4 py-2">
                      <h2 className="text-sm font-semibold text-[var(--text-primary)]">Notifications</h2>
                    </div>
                    <p className="p-4 text-center text-sm text-[var(--text-secondary)]">
                      No new notifications
                    </p>
                  </div>
                </>
              )}
            </div>

            <div className="relative">
              <button
                type="button"
                onClick={() => {
                  setShowProfileMenu(!showProfileMenu);
                  setShowNotifications(false);
                }}
                aria-label="Account menu"
                aria-expanded={showProfileMenu}
                aria-haspopup="true"
                className="flex items-center rounded-full"
              >
                {avatarUrl ? (
                  <img
                    src={avatarUrl}
                    alt=""
                    className="h-8 w-8 rounded-full border border-[var(--border)] object-cover transition-colors hover:border-[var(--accent-green)]"
                  />
                ) : (
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--accent-green)] text-xs font-bold text-white transition-opacity hover:opacity-90">
                    {getInitials(user?.full_name || user?.email)}
                  </span>
                )}
              </button>
              {showProfileMenu && (
                <>
                  <div className="fixed inset-0 z-20" onClick={() => setShowProfileMenu(false)} />
                  <div className="absolute right-0 top-full z-30 mt-2 w-52 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] py-1 shadow-[var(--shadow-lg)]">
                    <div className="mb-1 border-b border-[var(--border)] px-4 py-2.5">
                      <p className="truncate text-sm font-semibold text-[var(--text-primary)]">
                        {user?.full_name || 'Student'}
                      </p>
                      <p className="truncate text-xs text-[var(--text-secondary)]">{user?.email}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setShowProfileMenu(false);
                        signOut();
                      }}
                      className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-red-700 transition-colors hover:bg-red-50"
                    >
                      <LogOut className="h-4 w-4" aria-hidden="true" />
                      Log out
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
