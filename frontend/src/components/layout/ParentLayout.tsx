import React from 'react';
import {
  HeartHandshake, Users, ShieldCheck, UserCog
} from 'lucide-react';
import BasePortalLayout from './BasePortalLayout';
import type { NavGroup } from './BasePortalLayout';

const PARENT_NAV_GROUPS: NavGroup[] = [
  {
    heading: 'Family & Children',
    items: [
      { path: '/parent', label: 'Parent Dashboard', icon: HeartHandshake, exact: true },
    ],
  },
  {
    heading: 'Account & Consent',
    items: [
      { path: '/profile', label: 'Guardian Settings', icon: UserCog },
      { path: '/privacy-policy', label: 'Privacy & DPDP Consent', icon: ShieldCheck },
    ],
  },
];

interface ParentLayoutProps {
  children: React.ReactNode;
  title?: React.ReactNode;
}

export default function ParentLayout({ children, title }: ParentLayoutProps) {
  return (
    <BasePortalLayout
      portalRole="parent"
      portalName="Parent Portal"
      portalBadge="Family"
      badgeColorClass="bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400"
      navGroups={PARENT_NAV_GROUPS}
      title={title}
    >
      {children}
    </BasePortalLayout>
  );
}
