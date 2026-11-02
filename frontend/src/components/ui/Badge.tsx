import React from 'react';

export type BadgeTone = 
  | 'blue' 
  | 'purple' 
  | 'pink' 
  | 'sky' 
  | 'green' 
  | 'yellow' 
  | 'red' 
  | 'teal' 
  | 'neutral';

export type BadgeSize = 'xs' | 'sm' | 'md';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  size?: BadgeSize;
  dot?: boolean;
  icon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

const TONE_CLASSES: Record<BadgeTone, string> = {
  blue: 'bg-[var(--brand-primary-light)] text-[var(--accent-blue-text)] border border-[var(--brand-primary-soft)]',
  purple: 'bg-[var(--accent-purple-bg)] text-[var(--accent-purple-text)] border border-[var(--accent-purple-border)]',
  pink: 'bg-[var(--accent-pink-bg)] text-[var(--accent-pink-text)] border border-[var(--accent-pink-border)]',
  sky: 'bg-[var(--accent-sky-bg)] text-[var(--accent-sky-text)] border border-[var(--accent-sky-border)]',
  green: 'bg-[var(--accent-green-bg)] text-[var(--accent-green-text)] border border-[var(--accent-green-border)]',
  yellow: 'bg-[var(--accent-yellow-bg)] text-[var(--accent-yellow-text)] border border-[var(--accent-yellow-border)]',
  red: 'bg-[var(--accent-red-bg)] text-[var(--accent-red-text)] border border-[var(--accent-red-border)]',
  teal: 'bg-[var(--accent-teal-bg)] text-[var(--accent-teal-text)] border border-[var(--accent-teal-border)]',
  neutral: 'bg-[var(--bg-subtle)] text-[var(--text-secondary)] border border-[var(--border)]',
};

const DOT_COLORS: Record<BadgeTone, string> = {
  blue: 'bg-[var(--brand-primary)]',
  purple: 'bg-[var(--accent-purple)]',
  pink: 'bg-[var(--accent-pink)]',
  sky: 'bg-[var(--accent-sky)]',
  green: 'bg-[var(--accent-green)]',
  yellow: 'bg-[var(--accent-yellow)]',
  red: 'bg-[var(--accent-red)]',
  teal: 'bg-[var(--accent-teal)]',
  neutral: 'bg-[var(--text-muted)]',
};

const SIZE_CLASSES: Record<BadgeSize, string> = {
  xs: 'px-2 py-0.5 text-[10px] gap-1',
  sm: 'px-2.5 py-0.5 text-xs gap-1.5',
  md: 'px-3 py-1 text-xs gap-2',
};

export const Badge: React.FC<BadgeProps> = ({
  tone = 'blue',
  size = 'sm',
  dot = false,
  icon,
  children,
  className = '',
  ...props
}) => {
  return (
    <span
      className={`
        inline-flex items-center rounded-full font-semibold
        select-none transition-colors duration-150
        ${TONE_CLASSES[tone]}
        ${SIZE_CLASSES[size]}
        ${className}
      `}
      {...props}
    >
      {dot && (
        <span
          className={`w-1.5 h-1.5 rounded-full shrink-0 ${DOT_COLORS[tone]}`}
          aria-hidden="true"
        />
      )}
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{children}</span>
    </span>
  );
};


export default Badge;
