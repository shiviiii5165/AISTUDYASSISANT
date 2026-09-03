/**
 * TeachGenie Motion System
 * ========================
 * Shared Framer Motion variants for consistent animation across the app.
 *
 * Easing: cubic-bezier(0.16, 1, 0.3, 1) — expo out. Fast departure,
 * smooth deceleration. Never overshoots. Feels snappy without bounciness.
 *
 * Usage:
 *   import { fadeUp, staggerContainer } from '../lib/motion';
 *   <motion.div variants={staggerContainer} initial="hidden" whileInView="show" viewport={{ once: true }}>
 *     <motion.p variants={fadeUp}>Content</motion.p>
 *   </motion.div>
 *
 * All animations are controlled by parent useReducedMotion checks.
 * To disable wholesale: pass `variants={prefersReducedMotion ? undefined : fadeUp}`.
 */
import type { Variants } from 'framer-motion';

const EXPO_OUT = [0.16, 1, 0.3, 1] as const;

// ── Entrance variants ────────────────────────────────────────────────────────

/** Fade + 16px upward slide — primary entrance for most content blocks */
export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 16 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.5, ease: EXPO_OUT } },
};

/** Fade only — for overlays, panels, modals */
export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  show:   { opacity: 1, transition: { duration: 0.3, ease: EXPO_OUT } },
};

/** Scale in from 96% — cards, dialogs, tooltips */
export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.96 },
  show:   { opacity: 1, scale: 1, transition: { duration: 0.35, ease: EXPO_OUT } },
};

/** Slide in from the left — sidebars, drawers */
export const slideInLeft: Variants = {
  hidden: { opacity: 0, x: -20 },
  show:   { opacity: 1, x: 0, transition: { duration: 0.35, ease: EXPO_OUT } },
};

/** Slide in from the right — right panels, roadmap */
export const slideInRight: Variants = {
  hidden: { opacity: 0, x: 20 },
  show:   { opacity: 1, x: 0, transition: { duration: 0.35, ease: EXPO_OUT } },
};

/** Slide up from bottom — mobile sheets */
export const slideUp: Variants = {
  hidden: { opacity: 0, y: 32 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.4, ease: EXPO_OUT } },
  exit:   { opacity: 0, y: 32, transition: { duration: 0.25, ease: EXPO_OUT } },
};

// ── Container variants ───────────────────────────────────────────────────────

/** Stagger children with 70ms gap — use as parent of fadeUp children */
export const staggerContainer: Variants = {
  hidden: {},
  show:   { transition: { staggerChildren: 0.07, delayChildren: 0.05 } },
};

/** Tighter stagger for lists — 50ms gap */
export const staggerList: Variants = {
  hidden: {},
  show:   { transition: { staggerChildren: 0.05 } },
};

// ── Page transition ──────────────────────────────────────────────────────────

/** Route-level enter/exit — very short, never distracting */
export const pageTransition: Variants = {
  hidden: { opacity: 0 },
  show:   { opacity: 1, transition: { duration: 0.2, ease: EXPO_OUT } },
  exit:   { opacity: 0, transition: { duration: 0.15, ease: EXPO_OUT } },
};

// ── Micro-interaction props ──────────────────────────────────────────────────

/**
 * Subtle lift on hover for interactive cards. Spread onto a motion element:
 *   <motion.div {...cardHover}>...</motion.div>
 *
 * CSS shadow transition handles the shadow; Framer only drives translateY.
 */
export const cardHover = {
  whileHover: { y: -3, transition: { duration: 0.2, ease: EXPO_OUT } },
  whileTap:   { y: 0, scale: 0.99, transition: { duration: 0.1 } },
} as const;

/**
 * Gentle press feedback for buttons.
 */
export const buttonPress = {
  whileTap: { scale: 0.97, transition: { duration: 0.1 } },
} as const;

// ── Viewport defaults ────────────────────────────────────────────────────────

/** Standard viewport config for scroll-triggered reveals */
export const viewport = { once: true, amount: 0.2 } as const;
