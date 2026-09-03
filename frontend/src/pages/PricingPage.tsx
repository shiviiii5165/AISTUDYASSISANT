import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, X, Sparkles, Zap } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import PublicHeader from '../components/PublicHeader';
import UpgradeModal from '../components/billing/UpgradeModal';
import { useAuthStore } from '../store/useAuthStore';
import SEO from '../components/SEO';


const PricingPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);


  const content = (
    <>
      <SEO
        title="Pricing"
        description="Simple, student-friendly pricing. Upgrade to TeachGenie Pro for unlimited AI chat, advanced modes, and predicted exam questions."
      />
      <div className="mx-auto max-w-5xl px-4 py-12 md:px-6 md:py-20">
        {/* Header */}
        <div className="mb-12 text-center md:mb-16">
          <span className="mb-4 inline-block rounded-full bg-[var(--accent-baby)]/40 px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-[var(--accent-royal)]">
            Pricing
          </span>
          <h1 className="font-display text-3xl font-bold tracking-tight text-[var(--text-primary)] md:text-4xl">
            Simple, student-friendly pricing
          </h1>
          <p className="mx-auto mt-3 max-w-xl text-[var(--text-secondary)] text-sm md:text-base">
            Start learning from your notes for free. Upgrade to Pro when you need unlimited AI power for exams.
          </p>
        </div>

        <div className="mx-auto grid max-w-4xl grid-cols-1 gap-6 md:grid-cols-2">
          {/* Free Plan */}
          <div className="flex flex-col rounded-2xl border border-[var(--border)] bg-white p-7 shadow-bento md:p-9">
            <div className="mb-2 inline-flex items-center gap-2">
              <h2 className="font-display text-xl font-bold text-[var(--text-primary)]">Free Plan</h2>
            </div>
            <div className="mb-5 flex items-baseline gap-1">
              <span className="font-display text-4xl font-black text-[var(--text-primary)]">₹0</span>
              <span className="font-medium text-[var(--text-secondary)]">/month</span>
            </div>
            <p className="mb-6 text-sm text-[var(--text-secondary)]">
              Perfect for getting started and experiencing AI learning.
            </p>
            <button
              onClick={() => { if (!user) navigate('/auth'); else navigate('/dashboard'); }}
              className="mb-8 w-full rounded-full border border-[var(--border)] bg-[var(--bg-secondary)] px-4 py-3 font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)]"
            >
              {user ? 'Current Plan' : 'Start free'}
            </button>
            <div className="flex-1 space-y-4">
              <p className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">Included</p>
              <ul className="space-y-3">
                {['3 PDF uploads', '20 AI questions per day', 'Basic AI chat & PDF explanation', 'Basic MCQ generation & page citations'].map((f) => (
                  <li key={f} className="flex items-start gap-3 text-sm text-[var(--text-primary)]">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-[var(--accent-royal)]" aria-hidden="true" />
                    {f}
                  </li>
                ))}
              </ul>
              <div className="mt-4 space-y-3 border-t border-[var(--border)] pt-4 opacity-50">
                {['Full Chapter Crux or No Fact Miss', 'Formula Coverage', 'Exam Predictor or Handwritten AI'].map((f) => (
                  <div key={f} className="flex items-start gap-3 text-sm text-[var(--text-secondary)]">
                    <X className="mt-0.5 h-4 w-4 shrink-0 text-[var(--text-muted)]" aria-hidden="true" />
                    {f}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Pro Plan */}
          <div className="relative flex flex-col overflow-hidden rounded-2xl border-2 border-[var(--accent-royal)] bg-white p-7 shadow-bento-hover md:p-9">
            {/* Recommended badge */}
            <div className="absolute right-0 top-0 flex items-center gap-1 rounded-bl-xl bg-[var(--accent-royal)] px-3 py-1.5 text-xs font-bold text-white">
              <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
              Recommended
            </div>
            <div className="mb-2 flex items-center gap-2">
              <h2 className="font-display text-xl font-bold text-[var(--accent-royal)]">Pro Plan</h2>
              <Zap className="h-5 w-5 text-[var(--accent-royal)]" aria-hidden="true" />
            </div>
            <div className="mb-5 flex items-baseline gap-1">
              <span className="font-display text-4xl font-black text-[var(--text-primary)]">₹199</span>
              <span className="font-medium text-[var(--text-secondary)]">/month</span>
            </div>
            <p className="mb-6 text-sm text-[var(--text-secondary)]">
              Unlimited access to all AI study features for top exam scores.
            </p>
            <button
              onClick={() => { if (!user) navigate('/auth'); else setShowUpgradeModal(true); }}
              className="mb-8 w-full rounded-full bg-[var(--accent-royal)] px-4 py-3 font-bold text-white shadow-md shadow-[var(--accent-royal)]/25 transition-all hover:bg-[var(--accent-green-deep)]"
            >
              Upgrade to Pro
            </button>
            <div className="flex-1 space-y-4">
              <p className="text-xs font-bold uppercase tracking-wider text-[var(--accent-royal)]">Everything in Free, plus:</p>
              <ul className="space-y-3">
                {[
                  'Unlimited PDF uploads & AI questions',
                  'Full Chapter Crux & No Fact Miss modes',
                  'Formula Coverage & Exam Shield Notes',
                  'Predicted Exam Questions',
                  'Handwritten Notes AI support',
                  'Priority AI responses',
                ].map((f) => (
                  <li key={f} className="flex items-start gap-3 text-sm font-medium text-[var(--text-primary)]">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-[var(--accent-royal)]" aria-hidden="true" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
      
      <UpgradeModal 
        isOpen={showUpgradeModal} 
        onClose={() => setShowUpgradeModal(false)} 
      />
    </>
  );

  return user ? (
    <AppLayout title="Pricing">{content}</AppLayout>
  ) : (
    <div className="min-h-[100dvh] bg-[var(--bg-primary)]">
      <PublicHeader />
      {content}
    </div>
  );
};

export default PricingPage;
