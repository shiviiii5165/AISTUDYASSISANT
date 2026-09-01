import React from 'react';
import { useNavigate } from 'react-router-dom';
import SEO from '../../components/SEO';
import { ArrowRight, Target, Edit3, Award } from 'lucide-react';

const FreeMCQGeneratorPage: React.FC = () => {
  const navigate = useNavigate();

  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [{
      "@type": "Question",
      "name": "Is there a free MCQ generator for students?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes, TeachGenie offers an AI-powered MCQ generator that extracts questions directly from your uploaded PDF notes to help you practice."
      }
    }, {
      "@type": "Question",
      "name": "How does the AI MCQ generator work?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Simply upload your chapter notes or textbook PDF. TeachGenie reads the document and automatically creates multiple-choice questions testing your knowledge on that specific material."
      }
    }]
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      <SEO 
        title="Free MCQ Generator from PDF - TeachGenie"
        description="Generate unlimited MCQs from your PDF notes automatically. TeachGenie's free AI MCQ generator helps you practice and prepare for exams faster."
        canonical="/free-mcq-generator"
        schema={faqSchema}
      />
      
      <nav className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between border-b border-[var(--border)]">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/')}>
          <img src="/logo.png" alt="TeachGenie Logo" className="w-8 h-8 object-contain" />
          <span className="text-xl font-bold text-[var(--text-primary)]">TeachGenie</span>
        </div>
        <button onClick={() => navigate('/auth')} className="text-sm font-semibold bg-[var(--accent-green)] text-white px-5 py-2.5 rounded-xl hover:bg-green-700 transition-colors">
          Get Started
        </button>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-4xl md:text-5xl font-bold text-[var(--text-primary)] mb-6 text-center">
          Free MCQ Generator from PDF
        </h1>
        <p className="text-lg text-[var(--text-secondary)] mb-12 text-center max-w-2xl mx-auto">
          Turn any textbook, lecture note, or study guide into an interactive quiz instantly. Practice smarter with our AI MCQ generator.
        </p>

        <div className="grid md:grid-cols-3 gap-8 mb-16">
          <div className="p-6 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border)]">
            <Edit3 className="w-8 h-8 text-[var(--accent-green)] mb-4" />
            <h3 className="text-xl font-bold mb-2">1-Click Generation</h3>
            <p className="text-[var(--text-secondary)]">Upload your PDF and let the AI extract the most important concepts into testable questions.</p>
          </div>
          <div className="p-6 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border)]">
            <Target className="w-8 h-8 text-[var(--accent-indigo)] mb-4" />
            <h3 className="text-xl font-bold mb-2">Targeted Practice</h3>
            <p className="text-[var(--text-secondary)]">Identify exactly which sub-topics you are weak in based on your quiz scores.</p>
          </div>
          <div className="p-6 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border)]">
            <Award className="w-8 h-8 text-purple-600 mb-4" />
            <h3 className="text-xl font-bold mb-2">Exam Ready</h3>
            <p className="text-[var(--text-secondary)]">Get predicted exam questions alongside your generated MCQs for comprehensive prep.</p>
          </div>
        </div>

        <div className="bg-[var(--bg-secondary)] p-8 rounded-3xl border border-[var(--border)] mb-16">
          <h2 className="text-2xl font-bold mb-6">Frequently Asked Questions</h2>
          <div className="space-y-6">
            <div>
              <h3 className="font-bold text-lg mb-2">Is there a free MCQ generator for students?</h3>
              <p className="text-[var(--text-secondary)]">Yes, TeachGenie offers a powerful MCQ generator feature. Once you upload your notes, the AI acts as an exam setter to test your knowledge.</p>
            </div>
            <div>
              <h3 className="font-bold text-lg mb-2">How does the AI MCQ generator work?</h3>
              <p className="text-[var(--text-secondary)]">The AI study assistant reads the context of your uploaded PDF, finds the most critical facts and formulas, and crafts tricky multiple-choice questions with detailed explanations.</p>
            </div>
          </div>
        </div>
        
        <div className="text-center">
          <button onClick={() => navigate('/auth')} className="bg-[var(--accent-green)] text-white px-8 py-4 rounded-xl font-bold text-lg inline-flex items-center gap-2 hover:bg-green-700 transition-colors">
            Generate Free MCQs <ArrowRight className="w-5 h-5" />
          </button>
        </div>
        
        <div className="mt-20 pt-8 border-t border-[var(--border)] text-center text-[var(--text-secondary)]">
          <p>More features: <a href="/pdf-chat-ai" className="text-[var(--accent-green)] hover:underline">Chat With PDF Notes</a> | <a href="/exam-preparation-ai" className="text-[var(--accent-green)] hover:underline">Exam Preparation AI</a></p>
        </div>
      </main>
    </div>
  );
};

export default FreeMCQGeneratorPage;
