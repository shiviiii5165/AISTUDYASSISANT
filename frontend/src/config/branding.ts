/**
 * LearnByGenie — Canonical Brand Authority
 * ========================================
 * Single source of truth for all user-facing product branding, names,
 * slogans, and derived sub-brand identifiers.
 */

export const BRAND = {
  /** Canonical product brand name */
  name: 'LearnByGenie',
  shortName: 'LearnByGenie',
  aiName: 'LearnByGenie AI',

  /** Derived product features */
  liveQuizName: 'LearnByGenie Live Quiz',
  lessonPlannerName: 'LearnByGenie Lesson Planner',
  notesName: 'LearnByGenie Notes',
  tutorName: 'LearnByGenie Tutor',
  pptName: 'LearnByGenie PPT',
  researchName: 'LearnByGenie Research',
  classroomName: 'LearnByGenie Classroom',
  doubtSolverName: 'LearnByGenie Doubt Solver',

  /** Legacy identifier for backward compatibility only */
  legacyName: 'TeachGenie',

  /** Slogans & Taglines */
  tagline: 'AI Study Assistant & Smart Classroom Platform',
  titleSuffix: 'LearnByGenie - AI Doubt Solver for Students | Chat with Your PDF Notes',

  /** Domains & Email (Infrastructure defaults) */
  brandDomain: 'learnbygenie.com',
  deployedDomain: 'teachgenie.online',
  supportEmail: 'contact@learnbygenie.com',
  legacyEmail: 'contact@teachgenie.online',
} as const;

export type BrandConfig = typeof BRAND;
