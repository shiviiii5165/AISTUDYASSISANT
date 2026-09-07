import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, ArrowRight, Loader2, AlertCircle, Volume2, VolumeX, User } from 'lucide-react';
import { joinLiveSession } from '../lib/liveQuizApi';
import { soundFx } from '../lib/soundFx';
import SEO from '../components/SEO';

const AVATARS = ['🦊', '🦉', '🦁', '🐼', '🚀', '⚡', '🌟', '🎨', '🎯', '💡'];

const JoinLiveQuizPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const codeParam = searchParams.get('code') || '';

  const [joinCode, setJoinCode] = useState(codeParam);
  const [displayName, setDisplayName] = useState('');
  const [selectedAvatar, setSelectedAvatar] = useState(AVATARS[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState(soundFx.isMuted());

  useEffect(() => {
    if (codeParam && codeParam.length === 6) {
      setJoinCode(codeParam);
    }
  }, [codeParam]);

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanCode = joinCode.replace(/\s+/g, '').trim();

    if (cleanCode.length !== 6) {
      setError('Please enter a valid 6-digit join code.');
      return;
    }
    if (!displayName.trim()) {
      setError('Please enter your name or nickname.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await joinLiveSession(cleanCode, displayName.trim(), selectedAvatar);
      soundFx.playJoinSound();

      // Store identity in sessionStorage for reconnect
      sessionStorage.setItem(`teachgenie_live_participant_${res.session_id}`, JSON.stringify(res));

      navigate(`/live/${res.session_id}`);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
        err.message ||
        'Could not join. Please check the code and try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleToggleSound = () => {
    const next = soundFx.toggleMute();
    setIsMuted(next);
  };

  return (
    <div className="flex min-h-[100dvh] flex-col items-center justify-center bg-[var(--bg-primary)] px-4 py-8">
      <SEO title="Join Live Quiz | TeachGenie" description="Enter your 6-digit code to join your classroom live quiz." />

      {/* Audio Mute Toggle */}
      <div className="absolute right-4 top-4">
        <button
          onClick={handleToggleSound}
          aria-label={isMuted ? 'Unmute sound' : 'Mute sound'}
          className="flex h-10 w-10 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] shadow-sm transition-colors hover:bg-[var(--bg-hover)]"
        >
          {isMuted ? <VolumeX className="h-5 w-5 text-red-600" /> : <Volume2 className="h-5 w-5 text-[var(--accent-green-text)]" />}
        </button>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-xl sm:p-8"
      >
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--accent-royal)] text-white shadow-md shadow-[var(--accent-royal)]/25">
            <Sparkles className="h-7 w-7" />
          </div>
          <h1 className="font-display text-2xl font-bold text-[var(--text-primary)]">
            Join Live Room
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Enter the 6-digit code shown on the classroom screen.
          </p>
        </div>

        <form onSubmit={handleJoin} className="space-y-5">
          {/* 6-Digit Join Code Input */}
          <div>
            <label htmlFor="join-code" className="block text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
              Join Code
            </label>
            <div className="relative mt-1.5">
              <input
                id="join-code"
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={joinCode}
                onChange={(e) => {
                  setJoinCode(e.target.value.replace(/[^0-9]/g, '').slice(0, 6));
                  if (error) setError(null);
                }}
                placeholder="123456"
                disabled={loading}
                className="w-full rounded-xl border border-[var(--border-strong)] bg-[var(--bg-secondary)] px-4 py-3 text-center font-mono text-3xl font-bold tracking-[0.25em] text-[var(--text-primary)] transition-all focus:border-[var(--accent-royal)] focus:bg-[var(--bg-card)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-royal)]/20 disabled:opacity-60"
              />
            </div>
          </div>

          {/* Student Name */}
          <div>
            <label htmlFor="student-name" className="block text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
              Your Name
            </label>
            <div className="relative mt-1.5">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-[var(--text-muted)]">
                <User className="h-4 w-4" />
              </div>
              <input
                id="student-name"
                type="text"
                maxLength={30}
                value={displayName}
                onChange={(e) => {
                  setDisplayName(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="e.g. Alex"
                disabled={loading}
                className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] py-2.5 pl-10 pr-4 text-sm font-semibold text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent-royal)] focus:bg-[var(--bg-card)] focus:outline-none"
              />
            </div>
          </div>

          {/* Avatar Selector */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-2">
              Choose an Avatar
            </label>
            <div className="flex flex-wrap gap-2 justify-center">
              {AVATARS.map((av) => (
                <button
                  key={av}
                  type="button"
                  onClick={() => setSelectedAvatar(av)}
                  className={`flex h-10 w-10 items-center justify-center rounded-xl text-xl transition-all ${
                    selectedAvatar === av
                      ? 'scale-110 border-2 border-[var(--accent-royal)] bg-[var(--accent-baby)]/30 shadow-sm'
                      : 'border border-[var(--border)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)]'
                  }`}
                >
                  {av}
                </button>
              ))}
            </div>
          </div>

          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="flex items-center gap-2 rounded-xl bg-red-50 p-3 text-xs font-medium text-red-800"
              >
                <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
                <span>{error}</span>
              </motion.div>
            )}
          </AnimatePresence>

          <button
            type="submit"
            disabled={loading || joinCode.length !== 6 || !displayName.trim()}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--accent-royal)] py-3.5 text-sm font-bold text-white shadow-lg shadow-[var(--accent-royal)]/25 transition-all hover:bg-[var(--accent-green-deep)] active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Entering Room...</span>
              </>
            ) : (
              <>
                <span>Enter Room</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </form>
      </motion.div>

      <p className="mt-6 text-center text-xs text-[var(--text-muted)]">
        TeachGenie Real-Time Live Classroom Assessment Engine
      </p>
    </div>
  );
};

export default JoinLiveQuizPage;
