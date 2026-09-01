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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md relative z-10 animate-slideUp overflow-hidden">
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 p-2 bg-gray-100 rounded-full hover:bg-gray-200 transition-colors z-20"
        >
          <X className="w-4 h-4 text-gray-600" />
        </button>

        <div className="bg-gradient-to-br from-indigo-500 to-purple-600 p-8 text-center text-white relative">
          <div className="absolute inset-0 opacity-20 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMiIgY3k9IjIiIHI9IjIiIGZpbGw9IiNmZmYiLz48L3N2Zz4=')] bg-repeat" />
          <div className="w-14 h-14 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center mx-auto mb-4 border border-white/30">
            <Sparkles className="w-7 h-7 text-white" />
          </div>
          <h2 className="text-2xl font-bold mb-2 relative z-10">Upgrade to Pro</h2>
          <p className="text-indigo-100 text-sm mb-4 relative z-10">
            {message || 'Unlock your full study potential with unlimited AI features.'}
          </p>
          <div className="flex items-baseline justify-center gap-1 relative z-10">
            <span className="text-4xl font-black">₹199</span>
            <span className="text-indigo-200 font-medium">/month</span>
          </div>
        </div>

        <div className="p-6">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs font-medium">
              {error}
            </div>
          )}
          
          <ul className="space-y-3 mb-8">
            {PRO_FEATURES.map((feature, i) => (
              <li key={i} className="flex items-start gap-3 text-sm text-[var(--text-secondary)]">
                <div className="mt-0.5 w-4 h-4 rounded-full bg-[var(--accent-green-light)] flex items-center justify-center shrink-0">
                  <Check className="w-2.5 h-2.5 text-[var(--accent-green)]" />
                </div>
                {feature}
              </li>
            ))}
          </ul>

          <button
            onClick={handleUpgrade}
            disabled={loading}
            className="w-full bg-[var(--text-primary)] text-white font-bold py-3.5 rounded-xl hover:bg-gray-800 transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Upgrade Now'}
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
