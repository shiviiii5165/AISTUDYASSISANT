import React, { useState } from 'react';
import { Sparkles, Check, X, Loader2 } from 'lucide-react';
import { createCheckoutSession } from '../../services/billing';

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  message?: string;
}

const UpgradeModal: React.FC<UpgradeModalProps> = ({ isOpen, onClose, message }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleUpgrade = async () => {
    setLoading(true);
    setError('');
    try {
      await createCheckoutSession();
      // On success, close and optionally show a toast (omitted for minimal implementation)
      onClose();
    } catch (err: any) {
      setError(err.message || 'Upgrade failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const PRO_FEATURES = [
    'Unlimited PDF uploads',
    'Unlimited AI questions',
    'Full Chapter Crux & No Fact Miss',
    'Formula Coverage & Exam Shield Notes',
    'Generate MCQs & Predict Exams',
    'Handwritten Notes AI',
    'Priority AI responses',
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="upgrade-title">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 w-full max-w-md overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] shadow-[var(--shadow-lg)]">
        <button 
          onClick={onClose}
          aria-label="Close"
          className="absolute right-4 top-4 z-20 rounded-full bg-[var(--bg-secondary)] p-2 transition-colors hover:bg-[var(--bg-hover)]"
        >
          <X className="h-4 w-4 text-[var(--text-secondary)]" aria-hidden="true" />
        </button>

        <div className="relative bg-[var(--accent-green-deep)] p-8 text-center text-white">
          <div className="w-14 h-14 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center mx-auto mb-4 border border-white/30">
            <Sparkles className="h-7 w-7 text-white" aria-hidden="true" />
          </div>
          <h2 id="upgrade-title" className="font-display relative z-10 mb-2 text-2xl font-bold">Upgrade to Pro</h2>
          <p className="relative z-10 mb-4 text-sm text-[var(--accent-green-light)]">
            {message || 'Unlock your full study potential with unlimited AI features.'}
          </p>
          <div className="flex items-baseline justify-center gap-1 relative z-10">
            <span className="font-display text-4xl font-bold tabular-nums">₹199</span>
            <span className="font-medium text-[var(--accent-green-light)]">/month</span>
          </div>
        </div>

        <div className="p-6">
          {error && (
            <div role="alert" className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs font-medium text-amber-900">
              {error}
            </div>
          )}
          
          <ul className="space-y-3 mb-8">
            {PRO_FEATURES.map((feature, i) => (
              <li key={i} className="flex items-start gap-3 text-sm text-[var(--text-secondary)]">
                <div className="mt-0.5 w-4 h-4 rounded-full bg-[var(--accent-green-light)] flex items-center justify-center shrink-0">
                  <Check className="h-2.5 w-2.5 text-[var(--accent-green-text)]" aria-hidden="true" />
                </div>
                {feature}
              </li>
            ))}
          </ul>

          <button
            onClick={handleUpgrade}
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--accent-green)] py-3.5 font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)] active:translate-y-px disabled:cursor-not-allowed disabled:opacity-70"
          >
            {loading ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" /> : 'Upgrade now'}
          </button>
          <p className="text-center text-[10px] text-[var(--text-muted)] mt-3">
            Secure payment powered by Cashfree
          </p>
        </div>
      </div>
    </div>
  );
};

export default UpgradeModal;
