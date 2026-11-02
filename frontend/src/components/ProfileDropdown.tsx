import React from 'react';
import { Compass, CreditCard, FileText, GitBranch, LogOut, Settings, User, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '../lib/utils';
import { useAuthStore } from '../store/useAuthStore';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';

const GeminiIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
  </svg>
);

const getInitials = (name?: string | null, email?: string | null): string => {
  if (name) return name.charAt(0).toUpperCase();
  if (email) return email.charAt(0).toUpperCase();
  return 'U';
};

export default function ProfileDropdown({ className }: { className?: string }) {
  const { user, signOut } = useAuthStore();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className={cn(
            'flex h-8 shrink-0 items-center gap-1.5 rounded-full',
            'border border-[var(--border)] bg-[var(--bg-card)] pl-1 pr-2.5',
            'transition-all duration-200 hover:bg-[var(--bg-hover)] hover:shadow-sm',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-royal)] focus-visible:ring-offset-1',
            className
          )}
          aria-label="Open profile menu"
        >
          {/* Avatar — h-6 (24 px), 75% of the old 32 px standalone circle */}
          <div className="h-6 w-6 shrink-0 overflow-hidden rounded-full bg-gradient-to-br from-[var(--accent-periwinkle)] to-[var(--accent-royal)] p-px">
            <div className="h-full w-full overflow-hidden rounded-full bg-white flex items-center justify-center">
              {user?.avatar_url ? (
                <img
                  alt={user.full_name || ''}
                  className="h-full w-full rounded-full object-cover"
                  src={user.avatar_url}
                />
              ) : (
                <span className="text-[10px] font-bold text-[var(--text-primary)]">
                  {getInitials(user?.full_name, user?.email)}
                </span>
              )}
            </div>
          </div>
          {/* Name — single line, truncated, hidden on very narrow screens */}
          <span className="hidden max-w-[96px] truncate text-xs font-medium text-[var(--text-secondary)] sm:block">
            {user?.full_name || 'Student'}
          </span>
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-64">
        {/* Identity header inside menu */}
        <DropdownMenuLabel className="pb-2">
          <div className="text-sm font-semibold text-[var(--text-primary)]">{user?.full_name || 'Student'}</div>
          <div className="truncate text-xs font-normal text-[var(--text-secondary)]">{user?.email}</div>
        </DropdownMenuLabel>

        <DropdownMenuSeparator />

        <DropdownMenuItem asChild>
          <Link to="/profile" className="flex items-center gap-3 text-[var(--text-primary)]">
            <User className="h-4 w-4 text-[var(--text-secondary)]" />
            <span>Learning Profile</span>
          </Link>
        </DropdownMenuItem>

        <DropdownMenuItem asChild>
          <Link to="/diagnostic" className="flex items-center gap-3 text-[var(--text-primary)]">
            <Compass className="h-4 w-4 text-emerald-500" />
            <span>Diagnostic Assessment</span>
          </Link>
        </DropdownMenuItem>

        <DropdownMenuItem asChild>
          <Link to="/mastery" className="flex items-center gap-3 text-[var(--text-primary)]">
            <GitBranch className="h-4 w-4 text-indigo-500" />
            <span>Mastery Map</span>
          </Link>
        </DropdownMenuItem>

        <DropdownMenuItem asChild>
          <Link to="/mistakes" className="flex items-center gap-3 text-[var(--text-primary)]">
            <Sparkles className="h-4 w-4 text-purple-500" />
            <span>Mistake DNA</span>
          </Link>
        </DropdownMenuItem>

        <DropdownMenuItem asChild>
          <Link to="/pricing" className="flex items-center gap-3 text-[var(--text-primary)]">
            <CreditCard className="h-4 w-4 text-[var(--text-secondary)]" />
            <span>Subscription</span>
            <span className="ml-auto rounded-md bg-[var(--accent-baby)] px-1.5 py-0.5 text-[10px] font-bold text-[var(--accent-royal)]">
              PRO
            </span>
          </Link>
        </DropdownMenuItem>

        <DropdownMenuItem disabled className="flex items-center gap-3 text-[var(--text-secondary)]">
          <GeminiIcon className="h-4 w-4" />
          <span>Model</span>
          <span className="ml-auto rounded-md bg-[var(--bg-secondary)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-secondary)]">
            Gemini 3.1 Pro
          </span>
        </DropdownMenuItem>

        <DropdownMenuItem asChild>
          <Link to="/privacy-policy" className="flex items-center gap-3 text-[var(--text-primary)]" target="_blank">
            <FileText className="h-4 w-4 text-[var(--text-secondary)]" />
            Terms &amp; Policies
          </Link>
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          onClick={signOut}
          className="flex items-center gap-3 text-amber-900 focus:bg-amber-50 focus:text-amber-900 cursor-pointer"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
