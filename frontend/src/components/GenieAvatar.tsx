import React, { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import type { Variants } from 'framer-motion';

interface GenieAvatarProps {
  size?: 'sm' | 'md' | 'lg';
  isTyping?: boolean;
  isGenerating?: boolean;
  isSuccess?: boolean;
  isError?: boolean;
}

const SIZE_MAP = {
  sm: { container: 48, img: 40 },
  md: { container: 96, img: 80 },
  lg: { container: 140, img: 120 },
};

// Personality beats — random micro-animations
const PERSONALITY_BEATS = [
  { name: 'driftRight', duration: 0.8 },
  { name: 'driftLeft', duration: 0.8 },
  { name: 'headTilt', duration: 1.0 },
  { name: 'scaleBounce', duration: 0.6 },
  { name: 'sparkle', duration: 1.2 },
];

const GenieAvatar: React.FC<GenieAvatarProps> = ({
  size = 'md',
  isTyping = false,
  isGenerating = false,
  isSuccess = false,
  isError = false,
}) => {
  const prefersReducedMotion = useReducedMotion();
  const [activeBeat, setActiveBeat] = useState<string | null>(null);
  const [sparkles, setSparkles] = useState<{ id: number; x: number; y: number }[]>([]);
  const sparkleId = useRef(0);
  const beatTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const dims = SIZE_MAP[size];

  // Schedule random personality beats
  const scheduleNextBeat = useCallback(() => {
    if (prefersReducedMotion) return;
    const delay = 8000 + Math.random() * 12000; // 8-20s
    beatTimeout.current = setTimeout(() => {
      if (isTyping || isGenerating) {
        scheduleNextBeat();
        return;
      }
      const beat = PERSONALITY_BEATS[Math.floor(Math.random() * PERSONALITY_BEATS.length)];
      setActiveBeat(beat.name);

      if (beat.name === 'sparkle') {
        // Spawn 3-5 sparkle particles
        const count = 3 + Math.floor(Math.random() * 3);
        const newSparkles = Array.from({ length: count }, () => ({
          id: sparkleId.current++,
          x: (Math.random() - 0.5) * dims.container * 0.8,
          y: (Math.random() - 0.5) * dims.container * 0.6,
        }));
        setSparkles(newSparkles);
        setTimeout(() => setSparkles([]), beat.duration * 1000);
      }

      setTimeout(() => {
        setActiveBeat(null);
        scheduleNextBeat();
      }, beat.duration * 1000);
    }, delay);
  }, [prefersReducedMotion, isTyping, isGenerating, dims.container]);

  useEffect(() => {
    scheduleNextBeat();
    return () => {
      if (beatTimeout.current) clearTimeout(beatTimeout.current);
    };
  }, [scheduleNextBeat]);

  // Success sparkle burst
  useEffect(() => {
    if (isSuccess && !prefersReducedMotion) {
      const count = 6;
      const newSparkles = Array.from({ length: count }, () => ({
        id: sparkleId.current++,
        x: (Math.random() - 0.5) * dims.container,
        y: (Math.random() - 0.5) * dims.container * 0.8,
      }));
      setSparkles(newSparkles);
      setTimeout(() => setSparkles([]), 1200);
    }
  }, [isSuccess, prefersReducedMotion, dims.container]);

  // Determine the reactive animation variant
  const getReactiveVariant = () => {
    if (isTyping) return 'leaning';
    if (isGenerating) return 'thinking';
    if (isSuccess) return 'celebrating';
    if (isError) return 'curious';
    return 'idle';
  };

  const variant = getReactiveVariant();

  // Animation variants for the genie image
  const genieVariants: Variants = prefersReducedMotion
    ? {
        idle: { opacity: 1 },
        leaning: { opacity: 0.95 },
        thinking: { opacity: 0.9 },
        celebrating: { opacity: 1 },
        curious: { opacity: 0.95 },
      }
    : {
        idle: {
          y: [0, -8, 0, 4, 0],
          rotate: [0, 1.5, 0, -1.5, 0],
          transition: {
            y: { duration: 3.5, repeat: Infinity, ease: 'easeInOut' },
            rotate: { duration: 4, repeat: Infinity, ease: 'easeInOut' },
          },
        },
        leaning: {
          x: -5,
          rotate: -3,
          scale: 1.02,
          transition: { duration: 0.4, ease: 'easeOut' },
        },
        thinking: {
          y: [0, -4, 0, -2, 0],
          rotate: [0, 2, -1, 1, 0],
          transition: {
            y: { duration: 2, repeat: Infinity, ease: 'easeInOut' },
            rotate: { duration: 2.5, repeat: Infinity, ease: 'easeInOut' },
          },
        },
        celebrating: {
          y: [0, -16, 0],
          scale: [1, 1.08, 1],
          transition: { duration: 0.6, ease: 'easeOut' },
        },
        curious: {
          rotate: [0, 6, 4],
          transition: { duration: 0.5, ease: 'easeOut' },
        },
      };

  // Beat overlay animation
  const getBeatStyle = (): React.CSSProperties => {
    if (prefersReducedMotion || !activeBeat) return {};
    switch (activeBeat) {
      case 'driftRight':
        return { animation: 'driftRight 0.8s ease-in-out' };
      case 'driftLeft':
        return { animation: 'driftLeft 0.8s ease-in-out' };
      case 'headTilt':
        return { animation: 'headTilt 1s ease-in-out' };
      case 'scaleBounce':
        return { animation: 'scaleBounce 0.6s ease-in-out' };
      default:
        return {};
    }
  };

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: dims.container, height: dims.container }}
    >
      {/* Lamp glow effect (behind the genie) */}
      {!prefersReducedMotion && (
        <motion.div
          className="absolute rounded-full"
          style={{
            width: dims.container * 0.9,
            height: dims.container * 0.9,
            background: 'radial-gradient(circle, rgba(232,163,61,0.25) 0%, rgba(201,138,59,0.08) 50%, transparent 70%)',
          }}
          animate={{
            opacity: isGenerating ? [0.4, 0.8, 0.4] : [0.3, 0.6, 0.3],
            scale: isGenerating ? [1, 1.12, 1] : [1, 1.06, 1],
          }}
          transition={{
            duration: isGenerating ? 1.5 : 3,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      )}

      {/* Smoke wisps */}
      {!prefersReducedMotion && size !== 'sm' && (
        <>
          <div
            className="absolute"
            style={{
              bottom: '10%',
              left: '30%',
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: 'rgba(201, 138, 59, 0.12)',
              animation: 'smokeWisp 4s ease-out infinite',
            }}
          />
          <div
            className="absolute"
            style={{
              bottom: '15%',
              right: '35%',
              width: 4,
              height: 4,
              borderRadius: '50%',
              background: 'rgba(201, 138, 59, 0.1)',
              animation: 'smokeWisp 5s ease-out 1.5s infinite',
            }}
          />
        </>
      )}

      {/* The Genie */}
      <motion.div
        style={getBeatStyle()}
        variants={genieVariants}
        animate={variant}
        className="relative z-10"
      >
        <img
          src="/logo.png"
          alt="TeachGenie — your AI teaching companion"
          style={{
            width: dims.img,
            height: dims.img,
            objectFit: 'contain',
            filter: 'drop-shadow(0 4px 12px rgba(43, 27, 18, 0.15))',
          }}
          draggable={false}
        />
      </motion.div>

      {/* Sparkle particles */}
      <AnimatePresence>
        {sparkles.map((s) => (
          <motion.div
            key={s.id}
            className="absolute z-20 pointer-events-none"
            style={{
              width: 6 + Math.random() * 4,
              height: 6 + Math.random() * 4,
            }}
            initial={{ opacity: 0, scale: 0, x: 0, y: 0 }}
            animate={{
              opacity: [0, 1, 0],
              scale: [0.5, 1.2, 0.3],
              x: s.x,
              y: s.y,
              rotate: [0, 180, 360],
            }}
            exit={{ opacity: 0, scale: 0 }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          >
            <svg viewBox="0 0 24 24" fill="none" className="w-full h-full">
              <path
                d="M12 2L13.5 9.5L21 12L13.5 14.5L12 22L10.5 14.5L3 12L10.5 9.5L12 2Z"
                fill="var(--accent-green)"
                opacity="0.8"
              />
            </svg>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};

export default GenieAvatar;
