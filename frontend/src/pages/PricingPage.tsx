import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, X, Sparkles, Zap } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import UpgradeModal from '../components/billing/UpgradeModal';
import { useAuthStore } from '../store/useAuthStore';
import SEO from '../components/SEO';


const PricingPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);


  return (
    <AppLayout title="Pricing">
      <SEO 
        title="Pricing" 
        description="Simple, student-friendly pricing. Upgrade to TeachGenie Pro for unlimited AI chat, advanced modes, and predicted exam questions." 
      />
      <div className="max-w-5xl mx-auto px-4 md:px-6 py-8 md:py-12">
        <div className="text-center mb-10 md:mb-14">
          <h1 className="text-3xl md:text-4xl font-bold text-[var(--text-primary)] mb-4 tracking-tight">
            Simple, student-friendly pricing
          </h1>
          <p className="text-[var(--text-secondary)] max-w-xl mx-auto text-sm md:text-base">
            Start learning from your notes for free. Upgrade to Pro when you need unlimited AI power for exams.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          {/* Free Plan */}
          <div className="bg-white rounded-2xl p-6 md:p-8 border border-[var(--border)] shadow-[var(--shadow-sm)] flex flex-col">
            <h2 className="text-xl font-bold text-[var(--text-primary)] mb-2">Free Plan</h2>
            <div className="flex items-baseline gap-1 mb-6">
              <span className="text-3xl md:text-4xl font-black text-[var(--text-primary)]">₹0</span>
              <span className="text-[var(--text-secondary)] font-medium">/month</span>
            </div>
            <p className="text-sm text-[var(--text-secondary)] mb-6">
              Perfect for getting started and experiencing AI learning.
            </p>
            <button
              onClick={() => {
                if (!user) navigate('/auth');
                else navigate('/dashboard');
              }}
              className="w-full py-3 px-4 bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)] text-[var(--text-primary)] font-semibold rounded-xl border border-[var(--border)] transition-colors mb-8"
            >
              {user ? 'Current Plan' : 'Start free'}
            </button>
            <div className="space-y-4 flex-1">
              <h3 className="text-xs font-bold text-[var(--text-primary)] uppercase tracking-wider">Features included:</h3>
              <ul className="space-y-3">
                <li className="flex items-start gap-3 text-sm text-[var(--text-primary)]">
                  <Check className="w-5 h-5 text-[var(--accent-green)] shrink-0" />
                  3 PDF uploads
                </li>
                <li className="flex items-start gap-3 text-sm text-[var(--text-primary)]">
                  <Check className="w-5 h-5 text-[var(--accent-green)] shrink-0" />
                  20 AI questions per day
                </li>
                <li className="flex items-start gap-3 text-sm text-[var(--text-primary)]">
                  <Check className="w-5 h-5 text-[var(--accent-green)] shrink-0" />
                  Basic AI chat & PDF explanation
                </li>
                <li className="flex items-start gap-3 text-sm text-[var(--text-primary)]">
                  <Check className="w-5 h-5 text-[var(--accent-green)] shrink-0" />
                  Basic MCQ generation & Page citations
                </li>
              </ul>
              
              <div className="pt-4 mt-4 border-t border-[var(--border)] space-y-3 opacity-60">
                <ul className="space-y-3">
                <li className="flex items-start gap-3 text-sm text-[var(--text-secondary)]">
                  <X className="w-4 h-4 text-[var(--text-muted)] shrink-0 mt-0.5" />
                  No Full Chapter Crux or No Fact Miss
                </li>
                <li className="flex items-start gap-3 text-sm text-[var(--text-secondary)]">
                  <X className="w-4 h-4 text-[var(--text-muted)] shrink-0 mt-0.5" />
                  No Formula Coverage
                </li>
                <li className="flex items-start gap-3 text-sm text-[var(--text-secondary)]">
                  <X className="w-4 h-4 text-[var(--text-muted)] shrink-0 mt-0.5" />
                  No Exam Predictor or Handwritten AI
                </li>
                </ul>
              </div>
            </div>
          </div>

          {/* Pro Plan */}
          <div className="bg-white rounded-2xl p-6 md:p-8 border-2 border-[var(--accent-green)] shadow-xl flex flex-col relative overflow-hidden">
            <div className="absolute top-0 right-0 bg-[var(--accent-green)] text-white text-xs font-bold px-3 py-1.5 rounded-bl-lg flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5" /> Recommended
            </div>
            <h2 className="text-xl font-bold text-[var(--accent-green-text)] mb-2 flex items-center gap-2">
              Pro Plan <Zap className="w-5 h-5" />
            </h2>
            <div className="flex items-baseline gap-1 mb-6">
              <span className="text-3xl md:text-4xl font-black text-[var(--text-primary)]">₹199</span>
              <span className="text-[var(--text-secondary)] font-medium">/month</span>
            </div>
            <p className="text-sm text-[var(--text-secondary)] mb-6">
              Unlimited access to all AI study features for top exam scores.
            </p>
            <button
              onClick={() => {
                if (!user) navigate('/auth');
                else setShowUpgradeModal(true);
              }}
              className="w-full py-3 px-4 bg-[var(--text-primary)] hover:bg-gray-800 text-white font-bold rounded-xl shadow-md transition-all mb-8"
            >
              Upgrade to Pro
            </button>
            <div className="space-y-4 flex-1">
              <h3 className="text-xs font-bold text-[var(--accent-green-text)] uppercase tracking-wider">Everything in Free, plus:</h3>
              <ul className="space-y-3">
                <li className="flex items-start gap-3 text-sm font-medium text-[var(--text-primary)]">
                  <Check className="w-5 h-5 text-[var(--accent-green-text)] shrink-0" />
                  Unlimited PDF uploads & AI questions
                </li>
                <li className="flex items-start gap-3 text-sm text-[var(--text-primary)]">
                  <Check className="w-5 h-5 text-[var(--accent-green-text)] shrink-0" />
                  Full Chapter Crux & No Fact Miss modes
                </li>
                <li className="flex items-start gap-3 text-sm text-[var(--text-primary)]">
                  <Check className="w-5 h-5 text-[var(--accent-green-text)] shrink-0" />
                  Formula Coverage & Exam Shield Notes
                </li>
                <li className="flex items-start gap-3 text-sm text-[var(--text-primary)]">
                  <Check className="w-5 h-5 text-[var(--accent-green-text)] shrink-0" />
                  Predicted Exam Questions
                </li>
                <li className="flex items-start gap-3 text-sm text-[var(--text-primary)]">
                  <Check className="w-5 h-5 text-[var(--accent-green-text)] shrink-0" />
                  Handwritten Notes AI Support
                </li>
                <li className="flex items-start gap-3 text-sm text-[var(--text-primary)]">
                  <Check className="w-5 h-5 text-[var(--accent-green-text)] shrink-0" />
                  Priority AI responses
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      
      <UpgradeModal 
        isOpen={showUpgradeModal} 
        onClose={() => setShowUpgradeModal(false)} 
      />
    </AppLayout>
  );
};

export default PricingPage;
