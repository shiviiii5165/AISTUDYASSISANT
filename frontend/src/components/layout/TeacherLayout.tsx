import React from 'react';
import {
  GraduationCap, Users, Map, FileText, Presentation,
  PlayCircle, HelpCircle, Radio, BarChart3, Sparkles, UserCog
} from 'lucide-react';
import BasePortalLayout from './BasePortalLayout';
import type { NavGroup } from './BasePortalLayout';

const TEACHER_NAV_GROUPS: NavGroup[] = [
  {
    heading: 'Classroom & Cohorts',
    items: [
      { path: '/teacher', label: 'Teacher Dashboard', icon: GraduationCap, exact: true },
    ],
  },
  {
    heading: 'Instruction & Content Studio',
    items: [
      { path: '/lesson-planner', label: 'AI Lesson Planner', icon: Map },
      { path: '/notes', label: 'Notes & Study Material', icon: FileText },
      { path: '/decks', label: 'PPT Generator', icon: Presentation },
      { path: '/video', label: 'Video Generator', icon: PlayCircle },
      { path: '/quizzes', label: 'Quiz Generator', icon: HelpCircle },
      { path: '/join', label: 'Live Quiz — Host Room', icon: Radio },
    ],
  },
  {
    heading: 'Account',
    items: [
      { path: '/profile', label: 'Profile & Settings', icon: UserCog },
    ],
  },
];

interface TeacherLayoutProps {
  children: React.ReactNode;
  title?: React.ReactNode;
}

export default function TeacherLayout({ children, title }: TeacherLayoutProps) {
  return (
    <BasePortalLayout
      portalRole="teacher"
      portalName="Teacher Portal"
      portalBadge="Faculty"
      badgeColorClass="bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400"
      navGroups={TEACHER_NAV_GROUPS}
      title={title}
    >
      {children}
    </BasePortalLayout>
  );
}
