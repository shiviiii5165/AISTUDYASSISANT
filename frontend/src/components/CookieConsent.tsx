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
      className="fixed bottom-4 left-4 right-4 md:left-auto md:right-6 md:bottom-6 md:max-w-sm z-50 animate-slideUp"
    >
      <div className="bg-white rounded-xl shadow-[var(--shadow-lg)] border border-[var(--border)] overflow-hidden">
        {!showPreferences ? (
          <div className="p-4">
            <p className="text-sm font-semibold text-[var(--text-primary)] mb-1">🍪 Cookie Preferences</p>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed mb-3">
              We use cookies to keep your study sessions secure. Optional analytics cookies help us improve.{' '}
              <a href="/privacy-policy" className="text-[var(--accent-indigo)] hover:underline">Learn more</a>
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={handleRejectNonEssential}
                className="flex-1 px-3 py-2 text-xs font-medium text-[var(--text-secondary)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)] rounded-lg transition-colors"
              >
                Essential Only
              </button>
              <button
                onClick={() => setShowPreferences(true)}
                className="px-3 py-2 text-xs font-medium text-[var(--text-secondary)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)] rounded-lg transition-colors"
              >
                Manage
              </button>
              <button
                onClick={handleAcceptAll}
                className="flex-1 px-3 py-2 text-xs font-semibold text-white bg-[var(--accent-green)] hover:bg-green-700 rounded-lg transition-colors"
              >
                Accept All
              </button>
            </div>
          </div>
        ) : (
          <div className="p-4">
            <p className="text-sm font-semibold text-[var(--text-primary)] mb-3">Manage Cookies</p>
            <div className="space-y-2.5 mb-3">
              <label className="flex items-center gap-2.5 p-2.5 bg-[var(--bg-secondary)] rounded-lg">
                <input type="checkbox" checked disabled className="w-3.5 h-3.5 accent-[var(--accent-green)] cursor-not-allowed" />
                <div>
                  <p className="text-xs font-semibold text-[var(--text-primary)]">Essential</p>
                  <p className="text-[10px] text-[var(--text-muted)]">Login, session, security</p>
                </div>
              </label>
              <label className="flex items-center gap-2.5 p-2.5 bg-white border border-[var(--border)] rounded-lg cursor-pointer hover:bg-[var(--bg-hover)] transition-colors">
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
                Accept All
              </button>
              <button
                onClick={handleSavePreferences}
                className="flex-1 px-3 py-2 text-xs font-semibold text-white bg-[var(--accent-indigo)] hover:bg-indigo-700 rounded-lg transition-colors"
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
