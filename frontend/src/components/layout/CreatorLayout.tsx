import React from 'react';
import {
  FileEdit, BookOpen, Layers, Sparkles, UserCog
} from 'lucide-react';
import BasePortalLayout from './BasePortalLayout';
import type { NavGroup } from './BasePortalLayout';

const CREATOR_NAV_GROUPS: NavGroup[] = [
  {
    heading: 'Curriculum & Item Studio',
    items: [
      { path: '/creator', label: 'Creator Studio', icon: FileEdit, exact: true },
      { path: '/notes', label: 'Study Material Studio', icon: BookOpen },
    ],
  },
  {
    heading: 'Account',
    items: [
      { path: '/profile', label: 'Creator Profile', icon: UserCog },
    ],
  },
];

interface CreatorLayoutProps {
  children: React.ReactNode;
  title?: React.ReactNode;
}

export default function CreatorLayout({ children, title }: CreatorLayoutProps) {
  return (
    <BasePortalLayout
      portalRole="content_creator"
      portalName="Creator Studio"
      portalBadge="Author"
      badgeColorClass="bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400"
      navGroups={CREATOR_NAV_GROUPS}
      title={title}
    >
      {children}
    </BasePortalLayout>
  );
}
