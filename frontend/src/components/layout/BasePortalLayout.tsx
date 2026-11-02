import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { 
  Menu, X, ChevronLeft, ChevronRight, LifeBuoy, Sparkles 
} from 'lucide-react';
import { useAuthStore } from '../../store/useAuthStore';
import type { UserRole } from '../../store/useAuthStore';
import { useSidebarCollapse } from '../../hooks/useSidebarCollapse';
import { pageTransition } from '../../lib/motion';
import ProfileDropdown from '../ProfileDropdown';
import PortalSwitcher from '../PortalSwitcher';
import { BRAND } from '../../config/branding';

export interface NavItem {
  path: string;
  label: string;
  icon: React.ElementType;
  badge?: string;
  exact?: boolean;
}

export interface NavGroup {
  heading?: string;
  items: NavItem[];
}

export interface BasePortalLayoutProps {
  portalRole: UserRole;
  portalName: string;
  portalBadge: string;
  badgeColorClass?: string;
  navGroups: NavGroup[];
  title?: React.ReactNode;
  children: React.ReactNode;
}

const SUPPORT_ITEM: NavItem = { path: '/support', label: 'Support', icon: LifeBuoy };
const FIXED_HEIGHT_ROUTES = new Set(['/chat', '/teach', '/decks', '/quizzes', '/lesson-planner', '/notes']);

export default function BasePortalLayout({
  portalRole,
  portalName,
  portalBadge,
  badgeColorClass = 'bg-[var(--accent-blue-light)] text-[var(--accent-blue-text)]',
  navGroups,
  title,
  children,
}: BasePortalLayoutProps) {
  const location = useLocation();
  const isFixedHeight = FIXED_HEIGHT_ROUTES.has(location.pathname);
  const { user } = useAuthStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { collapsed, toggle } = useSidebarCollapse(`nav-${portalRole}`);
  const prefersReducedMotion = useReducedMotion();

  const getInitials = (name?: string) => (name ? name.charAt(0).toUpperCase() : 'U');
  const avatarUrl = user?.avatar_url;

  const isItemActive = (item: NavItem) => {
    if (item.exact) return location.pathname === item.path;
    if (location.pathname === item.path) return true;
    if (item.path !== '/' && item.path !== '/dashboard' && item.path !== '/teacher' && item.path !== '/parent' && item.path !== '/school-admin' && item.path !== '/creator' && item.path !== '/admin') {
      return location.pathname.startsWith(item.path);
    }
    return false;
  };

  const navLinkClass = (isActive: boolean, dense: boolean, iconOnly: boolean) =>
    [
      'flex items-center rounded-lg text-sm font-medium transition-colors relative group',
      iconOnly ? 'justify-center p-2.5' : (dense ? 'gap-3 px-3 py-2' : 'gap-3 px-3 py-2.5'),
      isActive
        ? 'bg-[var(--accent-blue-light)] text-[var(--accent-blue-text)] font-semibold shadow-xs'
        : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]',
    ].join(' ');

  const renderNavItem = (
    item: NavItem,
    opts: { dense: boolean; onNavigate?: () => void; iconOnly?: boolean }
  ) => {
    const isActive = isItemActive(item);
    const Icon = item.icon;
    return (
      <Link
        key={item.path}
        to={item.path}
        onClick={opts.onNavigate}
        title={opts.iconOnly ? item.label : undefined}
        aria-label={item.label}
        aria-current={isActive ? 'page' : undefined}
        className={navLinkClass(isActive, opts.dense, !!opts.iconOnly)}
      >
        <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-[var(--accent-blue-text)]' : 'text-[var(--text-muted)] group-hover:text-[var(--text-primary)]'}`} />
        {!opts.iconOnly && (
          <div className="flex items-center justify-between flex-1 min-w-0">
            <span className="truncate">{item.label}</span>
            {item.badge && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-[var(--bg-secondary)] text-[var(--text-muted)] border border-[var(--border)]">
                {item.badge}
              </span>
            )}
          </div>
        )}
      </Link>
    );
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] flex text-[var(--text-primary)] font-sans antialiased selection:bg-[var(--accent-blue-light)] selection:text-[var(--accent-blue-text)]">
      {/* Desktop Sidebar */}
      <aside
        className={`hidden md:flex flex-col bg-[var(--bg-card)] border-r border-[var(--border)] z-30 transition-[width] duration-300 ease-in-out shrink-0 ${
          collapsed ? 'w-16' : 'w-64'
        }`}
      >
        {/* Brand & Portal Badge */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-[var(--border)]">
          {!collapsed ? (
            <Link to="/" className="flex items-center gap-2 min-w-0">
              <span className="text-xl font-display font-extrabold text-[var(--accent-green)] tracking-tight">
                {BRAND.name}
              </span>
              <span className={`text-[10px] font-bold tracking-wide uppercase px-2 py-0.5 rounded-full ${badgeColorClass}`}>
                {portalBadge}
              </span>
            </Link>
          ) : (
            <Link to="/" className="mx-auto" title={portalName}>
              <span className="text-xl font-display font-black text-[var(--accent-green)]">
                {BRAND.name.charAt(0)}
              </span>
            </Link>
          )}

          <button
            type="button"
            onClick={toggle}
            className={`p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition ${
              collapsed ? 'mx-auto mt-2' : ''
            }`}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Portal-Specific Navigation Items */}
        <nav className="flex-1 overflow-y-auto px-2 py-4 space-y-4">
          {navGroups.map((group, gIdx) => (
            <div key={group.heading || `grp-${gIdx}`} className="space-y-1">
              {group.heading && !collapsed && (
                <div className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  {group.heading}
                </div>
              )}
              {group.items.map((item) =>
                renderNavItem(item, { dense: true, iconOnly: collapsed })
              )}
            </div>
          ))}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-2 border-t border-[var(--border)] space-y-1">
          {renderNavItem(SUPPORT_ITEM, { dense: true, iconOnly: collapsed })}
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="h-16 bg-[var(--bg-card)]/90 backdrop-blur-md border-b border-[var(--border)] sticky top-0 z-20 flex items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
              aria-label="Open navigation menu"
            >
              <Menu className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2 truncate">
              {title && (
                <div className="font-display font-semibold text-lg text-[var(--text-primary)] truncate">
                  {title}
                </div>
              )}
            </div>
          </div>

          {/* Header Controls: Portal Switcher & Profile */}
          <div className="flex items-center gap-2 sm:gap-3">
            <PortalSwitcher />
            <ProfileDropdown />
          </div>
        </header>

        {/* Page Content Body */}
        <main className={`flex-1 ${isFixedHeight ? 'overflow-hidden flex flex-col' : 'overflow-y-auto'}`}>
          <motion.div
            key={location.pathname}
            initial="initial"
            animate="animate"
            exit="exit"
            variants={prefersReducedMotion ? {} : pageTransition}
            className="flex-1 flex flex-col h-full"
          >
            {children}
          </motion.div>
        </main>
      </div>

      {/* Mobile Drawer Navigation */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <div className="fixed inset-0 z-50 md:hidden flex">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileMenuOpen(false)}
              className="fixed inset-0 bg-black/40 backdrop-blur-xs"
            />

            {/* Drawer */}
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 250 }}
              className="relative w-72 max-w-[85vw] bg-[var(--bg-card)] h-full flex flex-col shadow-2xl z-10"
            >
              <div className="h-16 flex items-center justify-between px-4 border-b border-[var(--border)]">
                <div className="flex items-center gap-2">
                  <span className="text-xl font-display font-extrabold text-[var(--accent-green)]">
                    {BRAND.name}
                  </span>
                  <span className={`text-[10px] font-bold tracking-wide uppercase px-2 py-0.5 rounded-full ${badgeColorClass}`}>
                    {portalBadge}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
                  aria-label="Close menu"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <nav className="flex-1 overflow-y-auto p-3 space-y-4">
                {navGroups.map((group, gIdx) => (
                  <div key={group.heading || `mob-grp-${gIdx}`} className="space-y-1">
                    {group.heading && (
                      <div className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                        {group.heading}
                      </div>
                    )}
                    {group.items.map((item) =>
                      renderNavItem(item, {
                        dense: false,
                        onNavigate: () => setMobileMenuOpen(false),
                      })
                    )}
                  </div>
                ))}
              </nav>

              <div className="p-3 border-t border-[var(--border)]">
                {renderNavItem(SUPPORT_ITEM, {
                  dense: false,
                  onNavigate: () => setMobileMenuOpen(false),
                })}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
