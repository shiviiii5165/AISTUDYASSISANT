import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Sparkles } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

interface GenieFloatingProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

const GenieFloating: React.FC<GenieFloatingProps> = ({ 
  className,
  size = 'md' 
}) => {
  const prefersReducedMotion = useReducedMotion();
  
  const sizeClasses = {
    sm: 'w-24 h-24',
    md: 'w-32 h-32',
    lg: 'w-48 h-48'
  };

  const containerClasses = cn(
    'relative flex items-center justify-center',
    sizeClasses[size],
    className
  );

  if (prefersReducedMotion) {
    return (
      <div className={containerClasses}>
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-genie-amber-soft/50 via-genie-purple-soft/30 to-transparent blur-xl" />
        <img 
          src="/logo.png" 
          alt="TeachGenie Mascot" 
          className="relative z-10 w-full h-full object-contain"
        />
      </div>
    );
  }

  return (
    <div className={containerClasses}>
      {/* Ambient glowing background */}
      <motion.div 
        className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-genie-amber-soft/70 via-genie-purple-soft/40 to-transparent blur-2xl rounded-full"
        animate={{ opacity: [0.4, 0.7, 0.4] }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      />
      
      {/* Sparkles around the genie */}
      <motion.div 
        className="absolute top-[10%] right-[10%] text-genie-amber-500 z-0"
        animate={{ opacity: [0, 1, 0], scale: [0.5, 1, 0.5], y: [0, -10] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
      >
        <Sparkles className="w-4 h-4" />
      </motion.div>

      <motion.div 
        className="absolute bottom-[20%] left-[10%] text-genie-purple-500 z-0"
        animate={{ opacity: [0, 0.8, 0], scale: [0.5, 1, 0.5], y: [0, -5] }}
        transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut", delay: 1.2 }}
      >
        <Sparkles className="w-3 h-3" />
      </motion.div>

      {/* Floating Mascot */}
      <motion.div
        className="relative z-10 w-full h-full cursor-pointer"
        animate={{ y: [0, -10, 0], rotate: [-2, 2, -2] }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        whileHover={{ rotate: [0, -6, 6, 0] }}
        whileTap={{ rotate: [0, -6, 6, 0] }}
      >
        <img 
          src="/logo.png" 
          alt="TeachGenie Mascot" 
          className="w-full h-full object-contain drop-shadow-xl"
        />
      </motion.div>
    </div>
  );
};

export default GenieFloating;
