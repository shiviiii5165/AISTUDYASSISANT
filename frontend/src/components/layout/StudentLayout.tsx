import React from 'react';
import {
  Target, Compass, ShieldCheck, ListChecks, FileText,
  GraduationCap, Sparkles, BookOpen, MessageSquare,
  HelpCircle, Radio, Map, User
} from 'lucide-react';
import BasePortalLayout from './BasePortalLayout';
import type { NavGroup } from './BasePortalLayout';

const STUDENT_NAV_GROUPS: NavGroup[] = [
  {
    heading: 'Learning Core',
    items: [
      { path: '/dashboard', label: 'Dashboard', icon: Target, exact: true },
      { path: '/studio', label: 'Learn Studio', icon: GraduationCap },
      { path: '/diagnostic', label: 'Diagnostic Assessment', icon: Sparkles },
      { path: '/practice', label: 'Adaptive Practice', icon: Compass },
      { path: '/step-check', label: 'Step Check', icon: ListChecks },
      { path: '/transfer-check', label: 'Independent Check', icon: ShieldCheck },
      { path: '/mistakes', label: 'Mistake DNA', icon: Sparkles },
      { path: '/mastery-map', label: 'Mastery Map', icon: Map },
    ],
  },
  {
    heading: 'Study Tools',
    items: [
      { path: '/teach', label: 'Teach Me', icon: GraduationCap },
      { path: '/chat', label: 'AI Tutor', icon: MessageSquare },
      { path: '/notes', label: 'AI Notes', icon: FileText },
      { path: '/library', label: 'My Library', icon: BookOpen },
      { path: '/quizzes', label: 'Quiz Practice', icon: HelpCircle },
      { path: '/join', label: 'Live Quiz — Join', icon: Radio },
    ],
  },
  {
    heading: 'Account',
    items: [
      { path: '/profile', label: 'Profile & Settings', icon: User },
    ],
  },
];

interface StudentLayoutProps {
  children: React.ReactNode;
  title?: React.ReactNode;
}

export default function StudentLayout({ children, title }: StudentLayoutProps) {
  return (
    <BasePortalLayout
      portalRole="student"
      portalName="Student Portal"
      portalBadge="Learner"
      badgeColorClass="bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"
      navGroups={STUDENT_NAV_GROUPS}
      title={title}
    >
      {children}
    </BasePortalLayout>
  );
}
