/**
 * Single source of truth for subject tags.
 *
 * These values were previously duplicated in Dashboard.tsx and LibraryPage.tsx
 * with DIFFERENT shades. Dashboard used bg-*-50 with text-*-600, which failed
 * WCAG AA (4.5:1 for small text) on five of the nine subjects:
 *
 *   emerald 3.58   amber 3.07   rose 4.28   cyan 3.54   orange 3.35
 *
 * Library's bg-*-100 with text-*-700 passes on all nine (lowest is amber at
 * 4.51), so that is the set kept here. Measured, not assumed.
 *
 * `dot` is a solid swatch for use as a small colour chip, where the pale
 * surface colours would be nearly invisible against a white background.
 */
export interface SubjectStyle {
  bg: string;
  text: string;
  dot: string;
}

export const SUBJECTS = [
  'General',
  'Physics',
  'Chemistry',
  'Biology',
  'Maths',
  'English',
  'History',
  'Computer Science',
  'Economics',
] as const;

export const SUBJECT_COLORS: Record<string, SubjectStyle> = {
  Physics: { bg: 'bg-blue-100', text: 'text-blue-700', dot: 'bg-blue-600' },
  Chemistry: { bg: 'bg-indigo-100', text: 'text-indigo-700', dot: 'bg-indigo-600' },
  Biology: { bg: 'bg-emerald-100', text: 'text-emerald-700', dot: 'bg-emerald-600' },
  Maths: { bg: 'bg-purple-100', text: 'text-purple-700', dot: 'bg-purple-600' },
  English: { bg: 'bg-amber-100', text: 'text-amber-700', dot: 'bg-amber-600' },
  History: { bg: 'bg-rose-100', text: 'text-rose-700', dot: 'bg-rose-600' },
  'Computer Science': { bg: 'bg-cyan-100', text: 'text-cyan-700', dot: 'bg-cyan-600' },
  Economics: { bg: 'bg-orange-100', text: 'text-orange-700', dot: 'bg-orange-600' },
  General: { bg: 'bg-gray-100', text: 'text-gray-700', dot: 'bg-gray-500' },
};

/** Falls back to General for any subject the backend sends that we do not style. */
export function subjectStyle(subject: string | undefined): SubjectStyle {
  return (subject && SUBJECT_COLORS[subject]) || SUBJECT_COLORS.General;
}
