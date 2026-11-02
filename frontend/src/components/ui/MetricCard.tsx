import React from 'react';
import Card from './Card';
import type { BadgeTone } from './Badge';

export interface MetricCardProps {
  label: string;
  value: React.ReactNode;
  icon: React.ReactNode;
  tone?: BadgeTone;
  subtitle?: React.ReactNode;
  trend?: {
    value: string;
    positive?: boolean;
  };
  className?: string;
  onClick?: () => void;
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

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  icon,
  tone = 'blue',
  subtitle,
  trend,
  className = '',
  onClick,
}) => {
  const wash = TONE_WASH[tone] || TONE_WASH.blue;

  return (
    <Card
      variant="elevated"
      interactive={!!onClick}
      onClick={onClick}
      className={`p-5 flex flex-col justify-between ${className}`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <span className="text-xs font-medium text-[var(--text-muted)] tracking-wider uppercase">
            {label}
          </span>
          <div className="text-2xl font-bold font-display text-[var(--text-primary)] mt-1">
            {value}
          </div>
        </div>

        <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 border ${wash.bg} ${wash.text} ${wash.border} shadow-xs`}>
          {icon}
        </div>
      </div>

      {(subtitle || trend) && (
        <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)] pt-2 border-t border-[var(--border)]">
          {trend && (
            <span className={`font-semibold ${trend.positive ? 'text-[var(--accent-green)]' : 'text-[var(--accent-red)]'}`}>
              {trend.value}
            </span>
          )}
          {subtitle && <span>{subtitle}</span>}
        </div>
      )}
    </Card>
  );
};

export default MetricCard;

