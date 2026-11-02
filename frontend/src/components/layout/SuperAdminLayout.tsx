import React from 'react';
import {
  ShieldCheck, Activity, Cpu, Server, UserCog, Database
} from 'lucide-react';
import BasePortalLayout from './BasePortalLayout';
import type { NavGroup } from './BasePortalLayout';

const SUPER_ADMIN_NAV_GROUPS: NavGroup[] = [
  {
    heading: 'Platform Control Plane',
    items: [
      { path: '/admin', label: 'Platform Telemetry', icon: ShieldCheck, exact: true },
    ],
  },
  {
    heading: 'Platform Account',
    items: [
      { path: '/profile', label: 'Admin Profile', icon: UserCog },
    ],
  },
];

interface SuperAdminLayoutProps {
  children: React.ReactNode;
  title?: React.ReactNode;
}

export default function SuperAdminLayout({ children, title }: SuperAdminLayoutProps) {
  return (
    <BasePortalLayout
      portalRole="super_admin"
      portalName="Super Admin Control Plane"
      portalBadge="Platform"
      badgeColorClass="bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400"
      navGroups={SUPER_ADMIN_NAV_GROUPS}
      title={title}
    >
      {children}
    </BasePortalLayout>
  );
}
