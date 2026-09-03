import React, { type ReactNode } from 'react';
import { motion, type Variants } from 'framer-motion';
export const ScrollReveal = ({ children, className = '' }: { children: ReactNode; className?: string }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: false, amount: 0.1, margin: "0px 0px -10% 0px" }}
      transition={{ duration: 0.8, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
};

export const WavyText = ({ text, className = '' }: { text: string; className?: string }) => {
  const letters = Array.from(text);

  const container = {
    hidden: { opacity: 0 },
    visible: (i = 1) => ({
      opacity: 1,
      transition: { staggerChildren: 0.03, delayChildren: 0.04 * i },
    }),
  };

  const child: Variants = {
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        type: 'spring',
        damping: 12,
        stiffness: 100,
      },
    },
    hidden: {
      opacity: 0,
      y: 20,
      transition: {
        type: 'spring',
        damping: 12,
        stiffness: 100,
      },
    },
  };

  return (
    <motion.span
      style={{ display: 'inline-flex', overflow: 'hidden' }}
      variants={container}
      initial="hidden"
      animate="visible"
      className={className}
    >
      {letters.map((letter, index) => (
        <motion.span variants={child} key={index} style={{ display: 'inline-block' }}>
          {letter === ' ' ? '\u00A0' : letter}
        </motion.span>
      ))}
    </motion.span>
  );
};

export const HoverCard = ({ children, className = '' }: { children: ReactNode; className?: string }) => {
  return (
    <motion.div
      whileHover={{ y: -5, scale: 1.01 }}
      whileTap={{ scale: 0.98 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      className={className}
    >
      {children}
    </motion.div>
  );
};


export const MagneticButton = ({ children, className = '' }: { children: ReactNode; className?: string }) => {
  const ref = React.useRef<HTMLDivElement>(null);
  const [position, setPosition] = React.useState({ x: 0, y: 0 });

  const handleMouse = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!ref.current) return;
    const { clientX, clientY } = e;
    const { height, width, left, top } = ref.current.getBoundingClientRect();
    const middleX = clientX - (left + width / 2);
    const middleY = clientY - (top + height / 2);
    setPosition({ x: middleX * 0.2, y: middleY * 0.2 });
  };

  const reset = () => {
    setPosition({ x: 0, y: 0 });
  };

  return (
    <motion.div
      ref={ref}
      onMouseMove={handleMouse}
      onMouseLeave={reset}
      animate={{ x: position.x, y: position.y }}
      transition={{ type: "spring", stiffness: 150, damping: 15, mass: 0.1 }}
      className={className}
      style={{ display: "inline-block" }}
    >
      {children}
    </motion.div>
  );
};
