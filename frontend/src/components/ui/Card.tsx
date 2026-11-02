import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { cardHover, card3DTilt } from '../../lib/motion';

export type CardVariant = 'default' | 'elevated' | 'feature' | 'interactive' | 'flat';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  interactive?: boolean;
  tilt?: boolean;
  className?: string;
  children?: React.ReactNode;
}

const VARIANT_CLASSES: Record<CardVariant, string> = {
  default: 'bg-[var(--bg-card)] border border-[var(--border)] shadow-xs rounded-2xl',
  elevated: 'bg-[var(--bg-card)] border border-[var(--border)] shadow-sm rounded-2xl',
  feature: 'bg-[var(--bg-card)] border border-[var(--border)] shadow-md rounded-2xl relative overflow-hidden',
  interactive: 'bg-[var(--bg-card)] border border-[var(--border)] shadow-xs hover:shadow-hover hover:border-[var(--border-strong)] rounded-2xl cursor-pointer transition-colors duration-200',
  flat: 'bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl',
};

export const Card = React.forwardRef<HTMLDivElement, CardProps>(function Card(
  {
    variant = 'default',
    interactive = false,
    tilt = false,
    className = '',
    children,
    ...props
  },
  ref
) {
  const prefersReducedMotion = useReducedMotion();
  const isInteractive = interactive || variant === 'interactive';

  const motionProps = prefersReducedMotion || !isInteractive
    ? {}
    : tilt
      ? card3DTilt
      : cardHover;

  return (
    <motion.div
      ref={ref}
      {...motionProps}
      className={`
        ${VARIANT_CLASSES[variant]}
        ${isInteractive ? 'cursor-pointer' : ''}
        ${className}
      `}
      {...(props as any)}
    >
      {children}
    </motion.div>
  );
});

export default Card;

