import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { buttonPress } from '../../lib/motion';

export type ButtonVariant = 
  | 'primary'
  | 'secondary'
  | 'ai'
  | 'creative'
  | 'success'
  | 'info'
  | 'warning'
  | 'danger'
  | 'ghost';

export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
  children?: React.ReactNode;
}

const VARIANT_STYLES: Record<ButtonVariant, string> = {
  primary: 'bg-[var(--brand-primary)] text-white hover:bg-[var(--brand-primary-hover)] border border-transparent shadow-xs hover:shadow-sm focus-visible:ring-[var(--brand-primary)]',
  secondary: 'bg-white text-[var(--text-primary)] hover:bg-[var(--bg-hover)] border border-[var(--border)] shadow-xs hover:border-[var(--border-strong)] focus-visible:ring-[var(--brand-primary)]',
  ai: 'bg-[var(--accent-purple-bg)] text-[var(--accent-purple-text)] hover:bg-[#EDE5F9] border border-[var(--accent-purple-border)] shadow-xs focus-visible:ring-[var(--accent-purple)]',
  creative: 'bg-[var(--accent-pink-bg)] text-[var(--accent-pink-text)] hover:bg-[#FBE4EF] border border-[var(--accent-pink-border)] shadow-xs focus-visible:ring-[var(--accent-pink)]',
  success: 'bg-[var(--accent-green-bg)] text-[var(--accent-green-text)] hover:bg-[#E3F4EA] border border-[var(--accent-green-border)] shadow-xs focus-visible:ring-[var(--accent-green)]',
  info: 'bg-[var(--accent-sky-bg)] text-[var(--accent-sky-text)] hover:bg-[#E2F2FB] border border-[var(--accent-sky-border)] shadow-xs focus-visible:ring-[var(--accent-sky)]',
  warning: 'bg-[var(--accent-yellow-bg)] text-[var(--accent-yellow-text)] hover:bg-[#FEF1D8] border border-[var(--accent-yellow-border)] shadow-xs focus-visible:ring-[var(--accent-yellow)]',
  danger: 'bg-[var(--accent-red-bg)] text-[var(--accent-red-text)] hover:bg-[#FBE4E4] border border-[var(--accent-red-border)] shadow-xs focus-visible:ring-[var(--accent-red)]',
  ghost: 'bg-transparent text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] border border-transparent focus-visible:ring-[var(--brand-primary)]',
};

const SIZE_STYLES: Record<ButtonSize, string> = {
  xs: 'text-xs px-2.5 py-1 gap-1.5 rounded-lg',
  sm: 'text-xs font-medium px-3.5 py-1.5 gap-2 rounded-xl',
  md: 'text-sm font-medium px-4 py-2.5 gap-2 rounded-xl',
  lg: 'text-base font-semibold px-6 py-3 gap-2.5 rounded-2xl',
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = 'primary',
    size = 'md',
    loading = false,
    disabled = false,
    icon,
    iconRight,
    className = '',
    children,
    ...props
  },
  ref
) {
  const prefersReducedMotion = useReducedMotion();
  const isDisabled = disabled || loading;

  return (
    <motion.button
      ref={ref}
      disabled={isDisabled}
      {...(prefersReducedMotion || isDisabled ? {} : buttonPress)}
      className={`
        inline-flex items-center justify-center font-sans select-none
        transition-all duration-150 cursor-pointer
        focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2
        disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none
        ${VARIANT_STYLES[variant]}
        ${SIZE_STYLES[size]}
        ${className}
      `}
      {...(props as any)}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin text-current" />
      ) : icon ? (
        <span className="shrink-0">{icon}</span>
      ) : null}

      {children}

      {!loading && iconRight && (
        <span className="shrink-0">{iconRight}</span>
      )}
    </motion.button>
  );
});

export default Button;

