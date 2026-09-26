import React from 'react';
import { useNavigate } from 'react-router-dom';
import SEO from '../../components/SEO';
import { ArrowRight, BookOpen, Brain, MessageSquare } from 'lucide-react';

const AITutorPage: React.FC = () => {
  const navigate = useNavigate();

  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [{
      "@type": "Question",
      "name": "What is an AI tutor for students?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "An AI tutor is a smart study assistant that helps students understand concepts, answer doubts, and prepare for exams using artificial intelligence."
      }
    }, {
      "@type": "Question",
      "name": "Is LearnByGenie useful for CBSE students?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes, LearnByGenie is highly effective for CBSE students as it can explain NCERT textbook concepts, solve doubts, and generate practice MCQs."
      }
    }]
  };

  return (
    <div className="min-h-[100dvh] bg-[var(--bg-primary)]">
      <SEO 
        title="AI Tutor for Students - Your Personal Study Assistant"
        description="Looking for an AI tutor for students? LearnByGenie acts as your personal AI study assistant. Upload notes, ask doubts, and prepare for exams easily."
        canonical="/ai-tutor-for-students"
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
          The Best AI Tutor for Students
        </h1>
        <p className="text-lg text-[var(--text-secondary)] mb-12 text-center max-w-2xl mx-auto">
          Struggling with complex topics? Our AI tutor for students breaks down difficult concepts into simple language, straight from your own study materials.
        </p>

        <div className="grid md:grid-cols-3 gap-8 mb-16">
          <div className="p-6 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border)]">
            <Brain className="w-8 h-8 text-[var(--accent-green)] mb-4" />
            <h3 className="text-xl font-bold mb-2">Smart Explanations</h3>
            <p className="text-[var(--text-secondary)]">Get step-by-step explanations for math, science, and more.</p>
          </div>
          <div className="p-6 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border)]">
            <MessageSquare className="w-8 h-8 text-[var(--accent-green-text)] mb-4" />
            <h3 className="text-xl font-bold mb-2">24/7 Doubt Solving</h3>
            <p className="text-[var(--text-secondary)]">Your AI tutor is always awake and ready to answer your questions.</p>
          </div>
          <div className="p-6 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border)]">
            <BookOpen className="w-8 h-8 text-purple-600 mb-4" />
            <h3 className="text-xl font-bold mb-2">Learn from Notes</h3>
            <p className="text-[var(--text-secondary)]">Upload your own PDFs and the AI will teach you from them.</p>
          </div>
        </div>

        <div className="bg-[var(--bg-secondary)] p-8 rounded-3xl border border-[var(--border)] mb-16">
          <h2 className="text-2xl font-bold mb-6">Frequently Asked Questions</h2>
          <div className="space-y-6">
            <div>
              <h3 className="font-bold text-lg mb-2">What is an AI tutor for students?</h3>
              <p className="text-[var(--text-secondary)]">An AI tutor is a smart study assistant that helps students understand concepts, answer doubts, and prepare for exams using artificial intelligence.</p>
            </div>
            <div>
              <h3 className="font-bold text-lg mb-2">Is LearnByGenie useful for CBSE students?</h3>
              <p className="text-[var(--text-secondary)]">Yes, LearnByGenie is highly effective for CBSE students as it can explain NCERT textbook concepts, solve doubts, and generate practice MCQs.</p>
            </div>
          </div>
        </div>
        
        <div className="text-center">
          <button onClick={() => navigate('/auth')} className="bg-[var(--accent-green)] text-white px-8 py-4 rounded-xl font-bold text-lg inline-flex items-center gap-2 hover:bg-[var(--accent-green-hover)] transition-colors">
            Start Learning Now <ArrowRight className="w-5 h-5" />
          </button>
        </div>
        
        <div className="mt-20 pt-8 border-t border-[var(--border)] text-center text-[var(--text-secondary)]">
          <p>More features: <a href="/pdf-chat-ai" className="text-[var(--accent-green)] hover:underline">Chat with PDF</a> | <a href="/mcq-generator" className="text-[var(--accent-green)] hover:underline">MCQ Generator</a></p>
        </div>
      </main>
    </div>
  );
};

export default AITutorPage;
