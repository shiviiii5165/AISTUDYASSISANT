import React from 'react';
import { useAuthStore } from '../store/useAuthStore';
import StudentLayout from './layout/StudentLayout';
import TeacherLayout from './layout/TeacherLayout';
import ParentLayout from './layout/ParentLayout';
import SchoolAdminLayout from './layout/SchoolAdminLayout';
import CreatorLayout from './layout/CreatorLayout';
import SuperAdminLayout from './layout/SuperAdminLayout';

export interface AppLayoutProps {
  children: React.ReactNode;
  title: React.ReactNode;
}

/**
 * Adaptive App Shell:
 * Automatically resolves to the user's active, server-authorized portal layout.
 * Eliminates monolithic navigation where all roles were mixed in one sidebar.
 */
export default function AppLayout({ children, title }: AppLayoutProps) {
  const { activeRole } = useAuthStore();

  switch (activeRole) {
    case 'teacher':
      return <TeacherLayout title={title}>{children}</TeacherLayout>;
    case 'parent':
      return <ParentLayout title={title}>{children}</ParentLayout>;
    case 'school_admin':
      return <SchoolAdminLayout title={title}>{children}</SchoolAdminLayout>;
    case 'content_creator':
      return <CreatorLayout title={title}>{children}</CreatorLayout>;
    case 'super_admin':
      return <SuperAdminLayout title={title}>{children}</SuperAdminLayout>;
    case 'student':
    default:
      return <StudentLayout title={title}>{children}</StudentLayout>;
  }
}
