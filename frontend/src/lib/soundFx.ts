/**
 * Procedural Web Audio API Sound Effects (Zero External Asset Dependencies)
 * =========================================================================
 * Generates energetic, modern, gentle game sounds directly via the browser's
 * AudioContext oscillator and gain nodes. Respects autoplay policies and supports
 * full mute toggling. Every sound has visual parity for silent mode.
 */

import { getMigratedStorageItem, setMigratedStorageItem } from './storageMigration';

class SoundEffectsManager {
  private ctx: AudioContext | null = null;
  private muted: boolean = false;
  private focusNoise: AudioBufferSourceNode | null = null;

  constructor() {
    // Check localStorage preference
    const saved = getMigratedStorageItem('learnbygenie_sound_muted', 'teachgenie_sound_muted');
    if (saved !== null) {
      this.muted = saved === 'true';
    }
  }

  private initContext() {
    if (!this.ctx && typeof window !== 'undefined') {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume().catch(() => {});
    }
  }

  public isMuted(): boolean {
    return this.muted;
  }

  public toggleMute(): boolean {
    this.setMuted(!this.muted);
    return this.muted;
  }

  public setMuted(muted: boolean) {
    this.muted = muted;
    if (muted && this.focusNoise) {
      this.focusNoise.stop();
      this.focusNoise = null;
    }
    setMigratedStorageItem('learnbygenie_sound_muted', 'teachgenie_sound_muted', String(muted));
  }

  /**
   * Gentle pop tone when student joins lobby
   */
  public playJoinSound() {
    if (this.muted) return;
    this.initContext();
    if (!this.ctx) return;

    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(440, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(880, this.ctx.currentTime + 0.12);

      gain.gain.setValueAtTime(0.15, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.12);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start();
      osc.stop(this.ctx.currentTime + 0.12);
    } catch {
      // Audio context error swallowed gracefully
    }
  }

  /**
   * Rewarding major arpeggio for correct answer
   */
  public playCorrectSound() {
    if (this.muted) return;
    this.initContext();
    if (!this.ctx) return;

    try {
      const now = this.ctx.currentTime;
      const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6

      notes.forEach((freq, i) => {
        if (!this.ctx) return;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, now + i * 0.06);

        gain.gain.setValueAtTime(0.12, now + i * 0.06);
        gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.06 + 0.2);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(now + i * 0.06);
        osc.stop(now + i * 0.06 + 0.2);
      });
    } catch {}
  }

  /**
   * Gentle, non-shaming minor dip tone for incorrect answer
   */
  public playIncorrectSound() {
    if (this.muted) return;
    this.initContext();
    if (!this.ctx) return;

    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(320, now);
      osc.frequency.exponentialRampToValueAtTime(240, now + 0.25);

      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(now);
      osc.stop(now + 0.25);
    } catch {}
  }

  /**
   * Soft clock tick for final 5 seconds countdown
   */
  public playTimerTick() {
    if (this.muted) return;
    this.initContext();
    if (!this.ctx) return;

    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(800, now);

      gain.gain.setValueAtTime(0.06, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(now);
      osc.stop(now + 0.04);
    } catch {}
  }

  /**
   * Celebratory chord progression when session finishes
   */
  public playSessionComplete() {
    if (this.muted) return;
    this.initContext();
    if (!this.ctx) return;

    try {
      const now = this.ctx.currentTime;
      const chord = [523.25, 659.25, 783.99, 987.77, 1046.50];

      chord.forEach((freq, idx) => {
        if (!this.ctx) return;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, now + idx * 0.08);

        gain.gain.setValueAtTime(0.1, now + idx * 0.08);
        gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.08 + 0.6);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(now + idx * 0.08);
        osc.stop(now + idx * 0.08 + 0.6);
      });
    } catch {}
  }

  private playTone(
    freq: number,
    startOffset: number,
    duration: number,
    peak: number,
    endFreq?: number,
  ) {
    if (!this.ctx) return;
    const start = this.ctx.currentTime + startOffset;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, start);
    if (endFreq) osc.frequency.linearRampToValueAtTime(endFreq, start + duration);

    gain.gain.setValueAtTime(peak, start);
    gain.gain.exponentialRampToValueAtTime(0.001, start + duration);

    osc.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start(start);
    osc.stop(start + duration);
  }

  private playIfAudible(render: () => void) {
    if (this.muted) return;
    this.initContext();
    if (!this.ctx) return;
    try {
      render();
    } catch {
      // Audio context error swallowed gracefully
    }
  }

  /** Ascending major third for a verified step (440 Hz to 554 Hz, 180 ms). */
  public playStepVerified() {
    this.playIfAudible(() => this.playTone(440, 0, 0.18, 0.12, 554));
  }

  /** Soft marimba-like tap when a hint is revealed (330 Hz, 90 ms). */
  public playHintReveal() {
    this.playIfAudible(() => this.playTone(330, 0, 0.09, 0.1));
  }

  /** Calm C4 pulse when a mistake is logged; never a buzzer. */
  public playMistakeLogged() {
    this.playIfAudible(() => this.playTone(261.6, 0, 0.2, 0.08));
  }

  /** C-major triad arpeggio lasting 650 ms for boss mastery. */
  public playBossMastery() {
    this.playIfAudible(() => {
      [261.63, 329.63, 392.0].forEach((freq, i) => {
        this.playTone(freq, i * 0.15, 0.65 - i * 0.15, 0.1);
      });
    });
  }

  /** Starts or stops looping brown noise; returns whether it is now playing. */
  public toggleFocusNoise(): boolean {
    if (this.focusNoise) {
      this.focusNoise.stop();
      this.focusNoise = null;
      return false;
    }
    if (this.muted) return false;
    this.initContext();
    if (!this.ctx) return false;

    const buffer = this.ctx.createBuffer(1, this.ctx.sampleRate * 4, this.ctx.sampleRate);
    const samples = buffer.getChannelData(0);
    let last = 0;
    for (let i = 0; i < samples.length; i++) {
      last = (last + 0.02 * (Math.random() * 2 - 1)) / 1.02;
      samples[i] = last * 3.5;
    }

    const source = this.ctx.createBufferSource();
    const gain = this.ctx.createGain();
    source.buffer = buffer;
    source.loop = true;
    gain.gain.value = 0.05;
    source.connect(gain);
    gain.connect(this.ctx.destination);
    source.start();
    this.focusNoise = source;
    return true;
  }

  public playWrongSound() {
    this.playIncorrectSound();
  }

  public playClick() {
    this.playTimerTick();
  }
}

export const soundFx = new SoundEffectsManager();
