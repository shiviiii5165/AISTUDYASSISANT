import React from 'react';
import { useNavigate } from 'react-router-dom';
import SEO from '../../components/SEO';
import { ArrowRight, BookOpen, FileText } from 'lucide-react';

const PDFChatPage: React.FC = () => {
  const navigate = useNavigate();

  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [{
      "@type": "Question",
      "name": "Can AI explain PDF notes?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes, LearnByGenie's AI can analyze your PDF notes and explain complex concepts from them in simple language."
      }
    }]
  };

  return (
    <div className="min-h-[100dvh] bg-[var(--bg-primary)]">
      <SEO 
        title="Chat With Your PDF Notes Using AI"
        description="Upload your PDF notes and textbooks to LearnByGenie and chat with them using AI. Ask questions, get summaries, and study smarter."
        canonical="/pdf-chat-ai"
        schema={faqSchema}
      />
      
      <nav className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between border-b border-[var(--border)]">
        <button type="button" aria-label="LearnByGenie home" className="flex items-center gap-2" onClick={() => navigate('/')}>
          <BookOpen className="w-6 h-6 text-[var(--accent-green)]" />
          <span className="text-xl font-bold text-[var(--text-primary)]">LearnByGenie</span>
        </button>
        <button onClick={() => navigate('/auth')} className="text-sm font-semibold bg-[var(--accent-green)] text-white px-5 py-2.5 rounded-xl hover:bg-[var(--accent-green-hover)] transition-colors">
          Get Started
        </button>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-4xl md:text-5xl font-bold text-[var(--text-primary)] mb-6 text-center">
          Chat With PDF Notes Using AI
        </h1>
        <p className="text-lg text-[var(--text-secondary)] mb-12 text-center max-w-2xl mx-auto">
          Don't just read your PDFs. Interact with them. LearnByGenie allows you to chat directly with your notes, textbooks, and study materials.
        </p>

        <div className="bg-[var(--bg-secondary)] p-8 rounded-3xl border border-[var(--border)] mb-16 text-center">
          <FileText className="w-16 h-16 text-[var(--accent-green)] mx-auto mb-6" />
          <h2 className="text-2xl font-bold mb-4">How it works</h2>
          <p className="text-[var(--text-secondary)] mb-6 max-w-lg mx-auto">
            1. Upload your PDF file.<br/>
            2. The AI reads and understands the content.<br/>
            3. Ask any question and get answers cited directly from the PDF.
          </p>
          <button onClick={() => navigate('/auth')} className="bg-[var(--accent-green)] text-white px-8 py-3 rounded-xl font-bold inline-flex items-center gap-2 hover:bg-[var(--accent-green-hover)] transition-colors">
            Upload PDF Now <ArrowRight className="w-5 h-5" />
          </button>
        </div>

        <div className="mb-16">
          <h2 className="text-2xl font-bold mb-6">FAQ</h2>
          <div>
            <h3 className="font-bold text-lg mb-2">Can AI explain PDF notes?</h3>
            <p className="text-[var(--text-secondary)]">Yes, LearnByGenie's AI can analyze your PDF notes and explain complex concepts from them in simple language.</p>
          </div>
        </div>
        
        <div className="mt-20 pt-8 border-t border-[var(--border)] text-center text-[var(--text-secondary)]">
          <p>Explore: <a href="/ai-tutor-for-students" className="text-[var(--accent-green)] hover:underline">AI Tutor</a> | <a href="/exam-preparation-ai" className="text-[var(--accent-green)] hover:underline">Exam Prep AI</a></p>
        </div>
      </main>
    </div>
  );
};

export default PDFChatPage;
