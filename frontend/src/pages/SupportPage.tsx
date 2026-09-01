import React, { useState } from 'react';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { Mail, MessageSquare, Send, CheckCircle } from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';

const SupportPage: React.FC = () => {
  const { user } = useAuthStore();
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

  return (
    <AppLayout title="Support">
      <SEO 
        title="Support & Help Center" 
        description="Get help with TeachGenie, report issues, and find answers to common questions." 
      />
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">How can we help you?</h1>
          <p className="text-[var(--text-secondary)] text-sm">Find answers in our FAQs or send a message to our support team.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Contact Form */}
          <div className="bg-white p-6 rounded-2xl border border-[var(--border)] shadow-[var(--shadow-sm)]">
            <h2 className="text-lg font-bold text-[var(--text-primary)] mb-4 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-[var(--accent-indigo)]" />
              Contact Support
            </h2>
            
            {submitted ? (
              <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
                <CheckCircle className="w-10 h-10 text-green-500 mx-auto mb-3" />
                <h3 className="font-bold text-green-800 mb-1">Message Sent!</h3>
                <p className="text-sm text-green-700">We've received your request and will get back to you shortly.</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-[var(--text-primary)] mb-1">Email Address</label>
                  <input
                    type="email"
                    value={user?.email || ''}
                    disabled
                    className="w-full px-3 py-2.5 rounded-lg border border-[var(--border)] bg-gray-50 text-[var(--text-muted)] text-sm cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-[var(--text-primary)] mb-1">Subject</label>
                  <input
                    type="text"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="E.g., Issue with PDF upload"
                    required
                    className="w-full px-3 py-2.5 rounded-lg border border-[var(--border)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-indigo)] transition-all bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-[var(--text-primary)] mb-1">How can we help?</label>
                  <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Please describe your issue or question in detail..."
                    required
                    rows={4}
                    className="w-full px-3 py-2.5 rounded-lg border border-[var(--border)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-indigo)] transition-all bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm resize-none"
                  />
                </div>
                <button
                  type="submit"
                  className="w-full bg-[var(--text-primary)] text-white font-semibold py-2.5 rounded-lg hover:bg-gray-800 transition-colors flex items-center justify-center gap-2 text-sm"
                >
                  <Send className="w-4 h-4" />
                  Send Message
                </button>
              </form>
            )}
          </div>

          {/* FAQs */}
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[var(--text-primary)] mb-4">Frequently Asked Questions</h2>
            
            <div className="space-y-3">
              {[
                {
                  q: "How many PDFs can I upload on the free plan?",
                  a: "You can upload up to 3 PDFs on the free plan. Upgrade to Pro for unlimited uploads."
                },
                {
                  q: "Why can't I access Full Chapter Crux?",
                  a: "Advanced AI modes like Full Chapter Crux, Formula Coverage, and Exam Predictor are exclusively available on our Pro plan."
                },
                {
                  q: "How do I cancel my Pro subscription?",
                  a: "You can cancel your subscription at any time from the billing section in your account settings."
                },
                {
                  q: "My PDF failed to process. What should I do?",
                  a: "Ensure your PDF is not password protected and contains readable text. If it's a scanned document or handwritten notes, the AI may take longer or struggle if the handwriting is unclear."
                }
              ].map((faq, idx) => (
                <div key={idx} className="bg-white p-4 rounded-xl border border-[var(--border)] shadow-[var(--shadow-sm)]">
                  <h3 className="text-sm font-bold text-[var(--text-primary)] mb-1.5">{faq.q}</h3>
                  <p className="text-xs text-[var(--text-secondary)] leading-relaxed">{faq.a}</p>
                </div>
              ))}
            </div>

            <div className="mt-6 bg-[var(--bg-secondary)] p-4 rounded-xl border border-[var(--border)] text-center">
              <Mail className="w-6 h-6 text-[var(--text-muted)] mx-auto mb-2" />
              <p className="text-xs text-[var(--text-secondary)]">
                Prefer email? Contact us directly at <br/>
                <a href="mailto:support@teachgenie.online" className="font-medium text-[var(--accent-indigo)] hover:underline">support@teachgenie.online</a>
              </p>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

export default SupportPage;
