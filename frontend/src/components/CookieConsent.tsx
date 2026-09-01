import React, { useState, useEffect } from 'react';

const CookieConsent: React.FC = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [showPreferences, setShowPreferences] = useState(false);
  const [preferences, setPreferences] = useState({
    essential: true,
    analytics: true,
  });

  useEffect(() => {
    const consent = localStorage.getItem('teachgenie_cookie_consent');
    if (!consent) {
      // Slight delay so it doesn't flash on load
      const timer = setTimeout(() => setIsVisible(true), 1000);
      return () => clearTimeout(timer);
    } else {
      try {
        const parsed = JSON.parse(consent);
        setPreferences(parsed);
      } catch {
        const timer = setTimeout(() => setIsVisible(true), 1000);
        return () => clearTimeout(timer);
      }
    }
  }, []);

  const saveConsent = (analyticsAllowed: boolean) => {
    const newPreferences = { essential: true, analytics: analyticsAllowed };
    localStorage.setItem('teachgenie_cookie_consent', JSON.stringify(newPreferences));
    setPreferences(newPreferences);
    setIsVisible(false);
    setShowPreferences(false);
    if (analyticsAllowed) {
      console.log('Analytics tracking enabled');
    }
  };

  const handleAcceptAll = () => saveConsent(true);
  const handleRejectNonEssential = () => saveConsent(false);
  const handleSavePreferences = () => saveConsent(preferences.analytics);

  if (!isVisible) return null;

  return (
    <div 
      className="fixed bottom-4 left-4 right-4 z-50 md:bottom-6 md:left-auto md:right-6 md:max-w-sm"
      role="region"
      aria-label="Cookie preferences"
    >
      <div className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--bg-card)] shadow-[var(--shadow-lg)]">
        {!showPreferences ? (
          <div className="p-4">
            <p className="mb-1 text-sm font-semibold text-[var(--text-primary)]">Cookie preferences</p>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed mb-3">
              We use cookies to keep your study sessions secure. Optional analytics cookies help us improve.{' '}
              <a href="/privacy-policy" className="font-medium text-[var(--accent-green-text)] underline">Learn more</a>
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={handleRejectNonEssential}
                className="flex-1 px-3 py-2 text-xs font-medium text-[var(--text-secondary)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)] rounded-lg transition-colors"
              >
                Essential only
              </button>
              <button
                onClick={() => setShowPreferences(true)}
                className="px-3 py-2 text-xs font-medium text-[var(--text-secondary)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)] rounded-lg transition-colors"
              >
                Manage
              </button>
              <button
                onClick={handleAcceptAll}
                className="flex-1 rounded-lg bg-[var(--accent-green)] px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)]"
              >
                Accept all
              </button>
            </div>
          </div>
        ) : (
          <div className="p-4">
            <p className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Manage cookies</p>
            <div className="space-y-2.5 mb-3">
              <label className="flex items-center gap-2.5 p-2.5 bg-[var(--bg-secondary)] rounded-lg">
                <input type="checkbox" checked disabled className="w-3.5 h-3.5 accent-[var(--accent-green)] cursor-not-allowed" />
                <div>
                  <p className="text-xs font-semibold text-[var(--text-primary)]">Essential</p>
                  <p className="text-[10px] text-[var(--text-muted)]">Login, session, security</p>
                </div>
              </label>
              <label className="flex cursor-pointer items-center gap-2.5 rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-2.5 transition-colors hover:bg-[var(--bg-hover)]">
                <input
                  type="checkbox"
                  checked={preferences.analytics}
                  onChange={(e) => setPreferences({ ...preferences, analytics: e.target.checked })}
                  className="w-3.5 h-3.5 accent-[var(--accent-green)]"
                />
                <div>
                  <p className="text-xs font-semibold text-[var(--text-primary)]">Analytics</p>
                  <p className="text-[10px] text-[var(--text-muted)]">Anonymous usage data</p>
                </div>
              </label>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleAcceptAll}
                className="flex-1 px-3 py-2 text-xs font-medium text-[var(--text-secondary)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)] rounded-lg transition-colors"
              >
                Accept all
              </button>
              <button
                onClick={handleSavePreferences}
                className="flex-1 rounded-lg bg-[var(--accent-green)] px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)]"
              >
                Save
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CookieConsent;
