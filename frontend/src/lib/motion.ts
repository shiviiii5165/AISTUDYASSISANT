/**
 * LearnByGenie Premium Motion System
 * ==================================
 * Direction: Smooth, refined micro-interactions and soft 3D depth.
 * Complies with Section 2 & 3 Motion Design Tokens of Master Engineering Prompt.
 */
import type { Variants } from 'framer-motion';

export const motionTokens = {
  instant: 100,
  fast: 150,
  standard: 220,
  smooth: 320,
  emphasis: 450,
  chart: 650,
  celebration: 800,
} as const;

/** Standard ease-out curve for fast departure and smooth deceleration without bounciness */
export const EASING_SMOOTH = [0.22, 1, 0.36, 1] as const;
export const EASING_EXPO = [0.16, 1, 0.3, 1] as const;

// ── Page Transitions (Section 2.A) ──────────────────────────────────────────
// Initial opacity: 0, y: 12px -> opacity: 1, y: 0 (220ms), exit: 150ms
export const pageTransition: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: { 
    opacity: 1, 
    y: 0, 
    transition: { 
      duration: motionTokens.standard / 1000, 
      ease: EASING_SMOOTH 
    } 
  },
  exit: { 
    opacity: 0, 
    y: -8, 
    transition: { 
      duration: motionTokens.fast / 1000, 
      ease: EASING_SMOOTH 
    } 
  },
};

// ── Staggered Content Entrance (Section 2.B) ────────────────────────────────
export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.045, // 45ms gentle stagger
      delayChildren: 0.02,
    },
  },
};

export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: {
    opacity: 1,
    y: 0,
    transition: {
      duration: motionTokens.standard / 1000,
      ease: EASING_SMOOTH,
    },
  },
};

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 12 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: motionTokens.smooth / 1000, ease: EASING_SMOOTH },
  },
};

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { duration: motionTokens.standard / 1000, ease: EASING_SMOOTH },
  },
};

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.97 },
  show: {
    opacity: 1,
    scale: 1,
    transition: { duration: motionTokens.standard / 1000, ease: EASING_SMOOTH },
  },
};

// ── Premium Soft 3D Card Effects (Section 2.C) ──────────────────────────────
export const cardHover = {
  whileHover: { 
    y: -3, 
    transition: { duration: motionTokens.fast / 1000, ease: EASING_SMOOTH } 
  },
  whileTap: { 
    y: 0, 
    scale: 0.99, 
    transition: { duration: 0.1 } 
  },
} as const;

export const card3DTilt = {
  whileHover: {
    y: -4,
    rotateX: 1,
    rotateY: -1,
    transition: { duration: motionTokens.standard / 1000, ease: EASING_SMOOTH },
  },
  whileTap: {
    y: -1,
    scale: 0.99,
    rotateX: 0,
    rotateY: 0,
    transition: { duration: 0.1 },
  },
} as const;

// ── Button Interactions (Section 2.D) ───────────────────────────────────────
export const buttonPress = {
  whileHover: { 
    y: -1, 
    transition: { duration: motionTokens.fast / 1000, ease: EASING_SMOOTH } 
  },
  whileTap: { 
    scale: 0.98, 
    transition: { duration: 0.08 } 
  },
} as const;

// ── Viewport Observer Config ────────────────────────────────────────────────
export const viewport = { once: true, amount: 0.15 } as const;
