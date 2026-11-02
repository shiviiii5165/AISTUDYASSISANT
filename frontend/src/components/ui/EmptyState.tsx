import React from 'react';
import Card from './Card';
import Button from './Button';
import type { ButtonVariant } from './Button';
import type { BadgeTone } from './Badge';

export interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  actionVariant?: ButtonVariant;
  tone?: BadgeTone;
  className?: string;
}

const TONE_WASH: Record<BadgeTone, { bg: string; text: string; border: string }> = {
  blue: { bg: 'bg-[var(--brand-primary-light)]', text: 'text-[var(--brand-primary)]', border: 'border-[var(--brand-primary-soft)]' },
  purple: { bg: 'bg-[var(--accent-purple-bg)]', text: 'text-[var(--accent-purple)]', border: 'border-[var(--accent-purple-border)]' },
  pink: { bg: 'bg-[var(--accent-pink-bg)]', text: 'text-[var(--accent-pink)]', border: 'border-[var(--accent-pink-border)]' },
  sky: { bg: 'bg-[var(--accent-sky-bg)]', text: 'text-[var(--accent-sky)]', border: 'border-[var(--accent-sky-border)]' },
  green: { bg: 'bg-[var(--accent-green-bg)]', text: 'text-[var(--accent-green)]', border: 'border-[var(--accent-green-border)]' },
  yellow: { bg: 'bg-[var(--accent-yellow-bg)]', text: 'text-[var(--accent-yellow)]', border: 'border-[var(--accent-yellow-border)]' },
  red: { bg: 'bg-[var(--accent-red-bg)]', text: 'text-[var(--accent-red)]', border: 'border-[var(--accent-red-border)]' },
  teal: { bg: 'bg-[var(--accent-teal-bg)]', text: 'text-[var(--accent-teal)]', border: 'border-[var(--accent-teal-border)]' },
  neutral: { bg: 'bg-[var(--bg-subtle)]', text: 'text-[var(--text-secondary)]', border: 'border-[var(--border)]' },
};

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  actionVariant = 'primary',
  tone = 'green',
  className = '',
}) => {
  const wash = TONE_WASH[tone] || TONE_WASH.green;

  return (
    <Card variant="elevated" className={`p-10 text-center flex flex-col items-center justify-center max-w-lg mx-auto ${className}`}>
      <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 border ${wash.bg} ${wash.text} ${wash.border} shadow-xs`}>
        {icon}
      </div>

      <h3 className="text-base font-semibold text-[var(--text-primary)] mb-1.5 font-display">
        {title}
      </h3>

      <p className="text-sm text-[var(--text-muted)] max-w-sm mb-6 leading-relaxed">
        {description}
      </p>

      {actionLabel && onAction && (
        <Button variant={actionVariant} size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </Card>
  );
};

export default EmptyState;

