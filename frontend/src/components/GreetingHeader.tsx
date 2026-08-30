import React from 'react';
import { useAuthStore } from '../store/useAuthStore';
import GenieAvatar from './GenieAvatar';

interface GreetingHeaderProps {
  /** Override the default subtitle text */
  subtitle?: string;
  /** Override the default mascot image (default: /logo.png — the Scholar Genie) */
  avatarImageSrc?: string;
  /** Override the glow variant: 'default' (amber lamp) or 'spotlight' (warm rose/amber stage glow) */
  avatarGlowVariant?: 'default' | 'spotlight';
  /** Avatar size ('sm' | 'md' | 'lg' | 'xl' | '2xl') */
  avatarSize?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
}

/**
 * Shared greeting header with time-of-day greeting, user's first name,
 * and the GenieAvatar mascot. Reusable across Dashboard, PPT Generator, etc.
 */
const GreetingHeader: React.FC<GreetingHeaderProps> = ({
  subtitle = 'What would you like to teach today?',
  avatarImageSrc,
  avatarGlowVariant,
  avatarSize = 'xl',
}) => {
  const { user } = useAuthStore();

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  const firstName =
    (user as any)?.full_name?.split(' ')[0] ||
    (user as any)?.email?.split('@')[0] ||
    'Student';

  return (
    <div className="flex flex-col items-center justify-center text-center space-y-4 pt-4 pb-2">
      <GenieAvatar
        size={avatarSize}
        {...(avatarImageSrc ? { imageSrc: avatarImageSrc } : {})}
        {...(avatarGlowVariant ? { glowVariant: avatarGlowVariant } : {})}
      />
      <h1
        className="text-4xl md:text-5xl tracking-tight mt-2 animate-slideUp font-extrabold"
        style={{ animationDelay: '0.1s' }}
      >
        <span className="bg-gradient-to-r from-ink to-genie-amber bg-clip-text text-transparent">
          {getGreeting()},
        </span>{' '}
        <span className="text-genie-amber">{firstName}</span>.
      </h1>
      <p
        className="text-[var(--text-secondary)] text-lg animate-slideUp"
        style={{ animationDelay: '0.2s' }}
      >
        {subtitle}
      </p>
    </div>
  );
};

export default GreetingHeader;
