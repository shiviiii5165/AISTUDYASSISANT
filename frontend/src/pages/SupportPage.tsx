import React, { useState } from 'react';
import AppLayout from '../components/AppLayout';
import PublicHeader from '../components/PublicHeader';
import SEO from '../components/SEO';
import { Mail, MessageSquare, Send, CheckCircle } from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';
import { ILLUSTRATIONS } from '../lib/assets';
import { BRAND } from '../config/branding';

const SupportPage: React.FC = () => {
  const { user } = useAuthStore();
  const [email, setEmail] = useState('');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim() || !message.trim()) return;
    
    // Here we would normally send the ticket to the backend
    setSubmitted(true);
    setSubject('');
    setMessage('');

    setTimeout(() => {
      setSubmitted(false);
    }, 5000);
  };

  const inputBase = 'w-full rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] px-3.5 py-2.5 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] transition-all focus:border-[var(--accent-royal)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-royal)]/20';

  const content = (
    <>
      <SEO
        title="Support & Help Center"
        description="Get help with LearnByGenie, report issues, and find answers to common questions."
      />
      <div className="mx-auto max-w-4xl px-4 py-10 md:px-6 md:py-16">
        {/* Header */}
        <div className="mb-10 text-center">
          <img
            src={ILLUSTRATIONS.support}
            alt=""
            aria-hidden="true"
            className="mx-auto mb-6 h-24 w-auto object-contain"
            onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
          />
          <span className="mb-3 inline-block rounded-full bg-[var(--accent-baby)]/40 px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-[var(--accent-royal)]">
            Support
          </span>
          <h1 className="font-display text-2xl font-bold text-[var(--text-primary)] md:text-3xl">
            How can we help you?
          </h1>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">
            Find answers in our FAQs or send a message to our support team.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
          {/* Contact Form */}
          <div className="rounded-2xl border border-[var(--border)] bg-white p-6 shadow-bento md:p-8">
            <h2 className="mb-5 flex items-center gap-2 font-display text-lg font-bold text-[var(--text-primary)]">
              <MessageSquare className="h-5 w-5 text-[var(--accent-royal)]" aria-hidden="true" />
              Contact support
            </h2>

            {submitted ? (
              <div className="rounded-xl border border-[var(--accent-baby)] bg-[var(--accent-baby)]/20 p-6 text-center">
                <CheckCircle className="mx-auto mb-3 h-10 w-10 text-[var(--accent-royal)]" aria-hidden="true" />
                <h3 className="font-display font-bold text-[var(--text-primary)]">Message Sent!</h3>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">We've received your request and will get back to you shortly.</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-xs font-semibold text-[var(--text-primary)]">Email Address</label>
                  <input
                    type="email"
                    value={user?.email || email}
                    onChange={(e) => !user && setEmail(e.target.value)}
                    disabled={!!user}
                    required
                    className={user
                      ? 'w-full cursor-not-allowed rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-3.5 py-2.5 text-sm text-[var(--text-muted)]'
                      : inputBase
                    }
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-semibold text-[var(--text-primary)]">Subject</label>
                  <input
                    type="text"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="E.g., Issue with PDF upload"
                    required
                    className={inputBase}
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-semibold text-[var(--text-primary)]">How can we help?</label>
                  <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Please describe your issue or question in detail..."
                    required
                    rows={4}
                    className={`${inputBase} resize-none`}
                  />
                </div>
                <button
                  type="submit"
                  className="flex w-full items-center justify-center gap-2 rounded-full bg-[var(--accent-royal)] py-2.5 text-sm font-bold text-white shadow-md shadow-[var(--accent-royal)]/25 transition-all hover:bg-[var(--accent-green-deep)]"
                >
                  <Send className="h-4 w-4" aria-hidden="true" />
                  Send Message
                </button>
              </form>
            )}
          </div>

          {/* FAQs */}
          <div>
            <h2 className="mb-5 font-display text-lg font-bold text-[var(--text-primary)]">Frequently Asked Questions</h2>
            <div className="space-y-3">
              {[
                {
                  q: 'How many PDFs can I upload on the free plan?',
                  a: 'You can upload up to 3 PDFs on the free plan. Upgrade to Pro for unlimited uploads.',
                },
                {
                  q: "Why can't I access Full Chapter Crux?",
                  a: 'Advanced AI modes like Full Chapter Crux, Formula Coverage, and Exam Predictor are exclusively available on our Pro plan.',
                },
                {
                  q: 'How do I cancel my Pro subscription?',
                  a: 'You can cancel your subscription at any time from the billing section in your account settings.',
                },
                {
                  q: 'My PDF failed to process. What should I do?',
                  a: "Ensure your PDF is not password protected and contains readable text. If it's a scanned document or handwritten notes, the AI may take longer or struggle if the handwriting is unclear.",
                },
              ].map((faq, idx) => (
                <div key={idx} className="rounded-xl border border-[var(--border)] bg-white p-4 shadow-bento">
                  <h3 className="mb-1.5 text-sm font-bold text-[var(--text-primary)]">{faq.q}</h3>
                  <p className="text-xs leading-relaxed text-[var(--text-secondary)]">{faq.a}</p>
                </div>
              ))}
            </div>

            <div className="mt-5 rounded-xl border border-[var(--border)] bg-[var(--accent-baby)]/10 p-4 text-center">
              <Mail className="mx-auto mb-2 h-6 w-6 text-[var(--accent-royal)]" aria-hidden="true" />
              <p className="text-xs text-[var(--text-secondary)]">
                Prefer email? Contact us directly at{' '}
                <a
                  href={`mailto:${BRAND.supportEmail}`}
                  className="font-semibold text-[var(--accent-royal)] hover:underline"
                >
                  {BRAND.supportEmail}
                </a>
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );

  return user ? (
    <AppLayout title="Support">{content}</AppLayout>
  ) : (
    <div className="min-h-[100dvh] bg-[var(--bg-primary)]">
      <PublicHeader />
      {content}
    </div>
  );
};

export default SupportPage;
