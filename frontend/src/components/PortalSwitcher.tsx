import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  GraduationCap, Users, Building2, FileEdit, ShieldCheck, 
  Target, ChevronDown, Check 
} from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';
import type { UserRole } from '../store/useAuthStore';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';

interface PortalOption {
  role: UserRole;
  label: string;
  path: string;
  icon: React.ElementType;
  badge: string;
}

const PORTALS: PortalOption[] = [
  { role: 'student', label: 'Student Portal', path: '/dashboard', icon: Target, badge: 'Learner' },
  { role: 'parent', label: 'Parent Portal', path: '/parent', icon: Users, badge: 'Family' },
  { role: 'teacher', label: 'Teacher Portal', path: '/teacher', icon: GraduationCap, badge: 'Faculty' },
  { role: 'school_admin', label: 'School Admin', path: '/school-admin', icon: Building2, badge: 'Institution' },
  { role: 'content_creator', label: 'Creator Studio', path: '/creator', icon: FileEdit, badge: 'Author' },
  { role: 'super_admin', label: 'Super Admin', path: '/admin', icon: ShieldCheck, badge: 'Platform' },
];

export default function PortalSwitcher() {
  const navigate = useNavigate();
  const location = useLocation();
  const { activeRole, authorizedRoles, setActiveRole } = useAuthStore();

  // Rule 1: If user has only 1 role (or none), do NOT render the switcher at all!
  if (!authorizedRoles || authorizedRoles.length <= 1) {
    return null;
  }

  // Rule 2: Strictly filter portals to only server-authorized roles!
  const availablePortals = PORTALS.filter((p) => authorizedRoles.includes(p.role));

  // Determine current portal based on active route or activeRole
  const currentPortal = availablePortals.find((p) => {
    if (location.pathname.startsWith('/parent')) return p.role === 'parent';
    if (location.pathname.startsWith('/teacher')) return p.role === 'teacher';
    if (location.pathname.startsWith('/school-admin')) return p.role === 'school_admin';
    if (location.pathname.startsWith('/creator')) return p.role === 'content_creator';
    if (location.pathname.startsWith('/admin')) return p.role === 'super_admin';
    return p.role === activeRole;
  }) || availablePortals[0];

  const handleSelect = (portal: PortalOption) => {
    setActiveRole(portal.role);
    navigate(portal.path);
  };

  const CurrentIcon = currentPortal.icon;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex h-8 items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--bg-card)] px-2.5 text-xs font-semibold text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition shadow-sm focus:outline-none"
        >
          <CurrentIcon className="w-3.5 h-3.5 text-[var(--accent-royal)]" />
          <span className="hidden sm:inline">{currentPortal.label}</span>
          <span className="sm:hidden">{currentPortal.badge}</span>
          <ChevronDown className="w-3 h-3 text-[var(--text-secondary)] opacity-70" />
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-56 p-1">
        <DropdownMenuLabel className="text-[11px] font-semibold text-[var(--text-secondary)] uppercase tracking-wider px-2 py-1.5">
          Authorized Portals ({availablePortals.length})
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {availablePortals.map((portal) => {
          const Icon = portal.icon;
          const isSelected = currentPortal.role === portal.role;
          return (
            <DropdownMenuItem
              key={portal.role}
              onClick={() => handleSelect(portal)}
              className="flex items-center justify-between px-2.5 py-2 text-xs rounded-lg cursor-pointer hover:bg-[var(--bg-hover)]"
            >
              <div className="flex items-center gap-2">
                <Icon className={`w-4 h-4 ${isSelected ? 'text-[var(--accent-royal)]' : 'text-[var(--text-secondary)]'}`} />
                <span className={isSelected ? 'font-bold text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'}>
                  {portal.label}
                </span>
              </div>
              {isSelected && <Check className="w-3.5 h-3.5 text-[var(--accent-royal)]" />}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
