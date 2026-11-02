import React from 'react';
import {
  Building2, Users, GraduationCap, ShieldCheck, UserCog
} from 'lucide-react';
import BasePortalLayout from './BasePortalLayout';
import type { NavGroup } from './BasePortalLayout';

const SCHOOL_ADMIN_NAV_GROUPS: NavGroup[] = [
  {
    heading: 'Institutional Oversight',
    items: [
      { path: '/school-admin', label: 'School Overview', icon: Building2, exact: true },
    ],
  },
  {
    heading: 'Administration & Governance',
    items: [
      { path: '/profile', label: 'Admin Settings', icon: UserCog },
      { path: '/privacy-policy', label: 'Compliance & Safety', icon: ShieldCheck },
    ],
  },
];

interface SchoolAdminLayoutProps {
  children: React.ReactNode;
  title?: React.ReactNode;
}

export default function SchoolAdminLayout({ children, title }: SchoolAdminLayoutProps) {
  return (
    <BasePortalLayout
      portalRole="school_admin"
      portalName="School Administration"
      portalBadge="Institution"
      badgeColorClass="bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-400"
      navGroups={SCHOOL_ADMIN_NAV_GROUPS}
      title={title}
    >
      {children}
    </BasePortalLayout>
  );
}
