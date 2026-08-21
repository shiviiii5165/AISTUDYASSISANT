import React, { useState } from 'react';
import { BookOpen, MessageSquare, Target, Bell, Menu, X, LogOut, LifeBuoy } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/useAuthStore';

const NAV_ITEMS = [
  { path: '/dashboard', label: 'Dashboard', icon: Target },
  { path: '/library', label: 'My Library', icon: BookOpen },
  { path: '/chat', label: 'AI Chat', icon: MessageSquare },
  { path: '/support', label: 'Support', icon: LifeBuoy },
];

const AppLayout = ({ children, title, sidebarOverride }: { children: React.ReactNode; title: React.ReactNode; sidebarOverride?: React.ReactNode }) => {
  const location = useLocation();

  const { user, signOut } = useAuthStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);

  const getInitials = (name?: string) => {
    return name ? name.charAt(0).toUpperCase() : 'U';
  };

  const avatarUrl = user?.avatar_url;

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] flex">
      {/* ── Desktop Sidebar ── */}
      <aside className="w-60 bg-[var(--bg-card)] border-r border-[var(--border)] hidden md:flex flex-col shrink-0">
        <div className="px-5 py-5">
          <Link to="/dashboard" className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-3">
            <img src="/logo.png" alt="TeachGenie Logo" className="w-10 h-10 object-contain drop-shadow-sm" />
            TeachGenie
          </Link>
        </div>
        <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
          {sidebarOverride ? sidebarOverride : NAV_ITEMS.map(({ path, label, icon: Icon }) => {
            const isActive = location.pathname === path;
            return (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-[var(--accent-green-light)] text-[var(--accent-green)]'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]'
                }`}
              >
                <Icon className={`w-[18px] h-[18px] ${isActive ? 'text-[var(--accent-green)]' : ''}`} />
                {label}
              </Link>
            );
          })}
        </nav>

      </aside>

      {/* ── Mobile Overlay ── */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setMobileMenuOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-64 bg-[var(--bg-card)] shadow-xl animate-slideUp flex flex-col">
            <div className="px-5 py-4 flex items-center justify-between border-b border-[var(--border)]">
              <Link to="/dashboard" className="text-lg font-bold text-[var(--text-primary)] flex items-center gap-2">
                <img src="/logo.png" alt="TeachGenie Logo" className="w-9 h-9 object-contain" />
                TeachGenie
              </Link>
              <button onClick={() => setMobileMenuOpen(false)} className="p-1.5 rounded-lg hover:bg-[var(--bg-hover)]">
                <X className="w-5 h-5 text-[var(--text-secondary)]" />
              </button>
            </div>
            <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
              {sidebarOverride ? sidebarOverride : NAV_ITEMS.map(({ path, label, icon: Icon }) => {
                const isActive = location.pathname === path;
                return (
                  <Link
                    key={path}
                    to={path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-[var(--accent-green-light)] text-[var(--accent-green)]'
                        : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'
                    }`}
                  >
                    <Icon className={`w-5 h-5 ${isActive ? 'text-[var(--accent-green)]' : ''}`} />
                    {label}
                  </Link>
                );
              })}
            </nav>
            <div className="p-3 border-t border-[var(--border)]">
              <button
                onClick={signOut}
                className="flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium text-red-500 hover:bg-red-50 transition-colors w-full"
              >
                <LogOut className="w-5 h-5" />
                Sign Out
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* ── Main Content ── */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden min-w-0">
        {/* Topbar */}
        <header className="h-14 border-b border-[var(--border)] bg-[var(--bg-card)] flex items-center justify-between px-4 md:px-6 shrink-0 z-10 relative shadow-sm">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="p-2 rounded-lg hover:bg-[var(--bg-hover)] transition-colors md:hidden"
            >
              <Menu className="w-5 h-5 text-[var(--text-secondary)]" />
            </button>
            <h2 className="text-base font-bold text-[var(--text-primary)] truncate">{title}</h2>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-[var(--text-muted)] font-medium hidden sm:block">
              {new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
            </span>
            <div className="relative">
              <button 
                onClick={() => {
                  setShowNotifications(!showNotifications);
                  setShowProfileMenu(false);
                }}
                className="p-2 text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] rounded-lg transition-colors relative"
              >
                <Bell className="w-[18px] h-[18px]" />
              </button>
              {showNotifications && (
                <>
                  <div className="fixed inset-0 z-20" onClick={() => setShowNotifications(false)} />
                  <div className="absolute right-0 top-full mt-2 w-64 bg-[var(--bg-card)] border border-[var(--border)] rounded-xl shadow-lg z-30 py-2">
                    <div className="px-4 py-2 border-b border-[var(--border)]">
                      <h3 className="text-sm font-bold text-[var(--text-primary)]">Notifications</h3>
                    </div>
                    <div className="p-4 text-center text-[var(--text-secondary)] text-sm">
                      No new notifications
                    </div>
                  </div>
                </>
              )}
            </div>

            <div className="relative">
              <button 
                onClick={() => {
                  setShowProfileMenu(!showProfileMenu);
                  setShowNotifications(false);
                }}
                className="flex items-center outline-none"
              >
                {avatarUrl ? (
                  <img src={avatarUrl} alt="Avatar" className="w-8 h-8 rounded-full object-cover border-2 border-[var(--border)] hover:border-[var(--accent-indigo)] transition-colors" />
                ) : (
                  <div className="w-8 h-8 bg-[var(--accent-indigo)] rounded-full flex items-center justify-center text-white font-bold text-xs hover:opacity-90 transition-opacity">
                    {getInitials(user?.full_name || user?.email)}
                  </div>
                )}
              </button>
              {showProfileMenu && (
                <>
                  <div className="fixed inset-0 z-20" onClick={() => setShowProfileMenu(false)} />
                  <div className="absolute right-0 top-full mt-2 w-48 bg-[var(--bg-card)] border border-[var(--border)] rounded-xl shadow-lg z-30 py-1">
                    <div className="px-4 py-2.5 border-b border-[var(--border)] mb-1">
                      <p className="text-sm font-bold text-[var(--text-primary)] truncate">{user?.full_name || 'Student'}</p>
                      <p className="text-xs text-[var(--text-secondary)] truncate">{user?.email}</p>
                    </div>
                    <button
                      onClick={() => {
                        setShowProfileMenu(false);
                        signOut();
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-red-500 hover:bg-red-50 flex items-center gap-2 transition-colors"
                    >
                      <LogOut className="w-4 h-4" />
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
