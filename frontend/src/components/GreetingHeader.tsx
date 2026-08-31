import React from 'react';
import { useAuthStore } from '../store/useAuthStore';
import GenieAvatar from './GenieAvatar';

interface GreetingHeaderProps {
  /** Override the default subtitle text */
  subtitle?: string;
  /** Override the default mascot image (default: /logo.png, the Scholar Genie) */
  avatarImageSrc?: string;
  /** Override the glow variant: 'default' (amber lamp) or 'spotlight' (warm rose/amber stage glow) */
  avatarGlowVariant?: 'default' | 'spotlight';
  /** Avatar size ('sm' | 'md' | 'lg' | 'xl' | '2xl') */
  avatarSize?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
}

/**
 * Shared greeting header with time-of-day greeting, the user's first name and
 * the GenieAvatar mascot. Used by Dashboard, PPT Generator and Video Generator.
 *
 * Laid out as a compact row rather than a centred hero: these are daily-use
 * working screens, so the greeting should cost one line of vertical space, not
 * a screenful. Renders an h2 because AppLayout's topbar owns the page h1.
 */
const GreetingHeader: React.FC<GreetingHeaderProps> = ({
  subtitle = 'What would you like to work on today?',
  avatarImageSrc,
  avatarGlowVariant,
  avatarSize = 'md',
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
    <div className="flex items-center gap-4">
      <GenieAvatar
        size={avatarSize}
        {...(avatarImageSrc ? { imageSrc: avatarImageSrc } : {})}
        {...(avatarGlowVariant ? { glowVariant: avatarGlowVariant } : {})}
      />
      <div className="min-w-0">
        <h2 className="font-display text-2xl font-bold tracking-tight text-[var(--text-primary)] sm:text-3xl">
          {getGreeting()}, {firstName}.
        </h2>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">{subtitle}</p>
      </div>
    </div>
  );
};

export default GreetingHeader;
