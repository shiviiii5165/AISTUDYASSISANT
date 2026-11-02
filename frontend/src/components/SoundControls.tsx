import { useState } from 'react';
import { Volume2, VolumeX, Waves } from 'lucide-react';
import { soundFx } from '../lib/soundFx';

/** One-click mute (persisted by soundFx) and the optional brown-noise focus sound. */
export default function SoundControls() {
  const [muted, setMuted] = useState(soundFx.isMuted());
  const [focus, setFocus] = useState(false);
  const base = 'p-2 rounded-lg transition hover:bg-[var(--bg-hover)]';

  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        className={`${base} text-[var(--text-secondary)]`}
        aria-pressed={muted}
        aria-label={muted ? 'Turn sound on' : 'Mute sound'}
        title={muted ? 'Turn sound on' : 'Mute sound'}
        onClick={() => {
          setMuted(soundFx.toggleMute());
          setFocus(false);
        }}
      >
        {muted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
      </button>
      <button
        type="button"
        className={`${base} ${focus ? 'text-[var(--lg-mastery-text)]' : 'text-[var(--text-secondary)]'}`}
        aria-pressed={focus}
        aria-label={focus ? 'Stop focus sound' : 'Play brown-noise focus sound'}
        title={muted ? 'Unmute to use focus sound' : 'Brown-noise focus sound'}
        disabled={muted}
        onClick={() => setFocus(soundFx.toggleFocusNoise())}
      >
        <Waves className="w-4 h-4" />
      </button>
    </div>
  );
}
