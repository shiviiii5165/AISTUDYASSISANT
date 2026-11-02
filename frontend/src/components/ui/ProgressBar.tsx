import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import type { BadgeTone } from './Badge';

export interface ProgressBarProps {
  value: number; // 0 to 100
  tone?: BadgeTone;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

const TONE_FILL: Record<BadgeTone, string> = {
  blue: 'bg-[var(--brand-primary)]',
  purple: 'bg-[var(--accent-purple)]',
  pink: 'bg-[var(--accent-pink)]',
  sky: 'bg-[var(--accent-sky)]',
  green: 'bg-[var(--accent-green)]',
  yellow: 'bg-[var(--accent-yellow)]',
  red: 'bg-[var(--accent-red)]',
  teal: 'bg-[var(--accent-teal)]',
  neutral: 'bg-[var(--text-secondary)]',
};

const HEIGHT_CLASSES = {
  sm: 'h-1.5 rounded-full',
  md: 'h-2.5 rounded-full',
  lg: 'h-3.5 rounded-full',
};

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  tone = 'blue',
  size = 'md',
  showLabel = false,
  className = '',
}) => {
  const prefersReducedMotion = useReducedMotion();
  const clamped = Math.min(100, Math.max(0, value));
  const fillClass = TONE_FILL[tone] || TONE_FILL.blue;

  return (
    <div className={`w-full ${className}`}>
      {showLabel && (
        <div className="flex justify-between items-center text-xs font-medium text-[var(--text-muted)] mb-1.5">
          <span>Progress</span>
          <span className="text-[var(--text-primary)] font-semibold">{Math.round(clamped)}%</span>
        </div>
      )}

      <div className={`w-full bg-[var(--bg-subtle)] border border-[var(--border)] overflow-hidden ${HEIGHT_CLASSES[size]}`}>
        <motion.div
          initial={prefersReducedMotion ? false : { width: 0 }}
          animate={{ width: `${clamped}%` }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className={`h-full rounded-full ${fillClass}`}
        />
      </div>
    </div>
  );
};

export default ProgressBar;

