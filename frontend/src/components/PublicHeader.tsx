import React from 'react';
import { Link, useNavigate } from 'react-router-dom';

export default function PublicHeader() {
  const navigate = useNavigate();
  return (
    <header className="sticky top-0 z-40 w-full border-b border-[var(--border)] bg-[var(--bg-card)]/80 backdrop-blur">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 md:px-6">
        <Link to="/" className="flex items-center gap-2.5 font-display text-lg font-bold text-[var(--text-primary)]">
          <img src="/assets/genie-default.png" alt="" className="h-8 w-8 object-contain" />
          TeachGenie
        </Link>
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => navigate('/auth')} className="rounded-lg px-3 py-2 text-sm font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]">
            Log in
          </button>
          <button type="button" onClick={() => navigate('/auth')} className="rounded-lg bg-[var(--accent-green)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)] active:translate-y-px">
            Start free
          </button>
        </div>
      </nav>
    </header>
  );
}
