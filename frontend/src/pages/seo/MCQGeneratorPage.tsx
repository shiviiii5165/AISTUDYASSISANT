import React from 'react';
import { useNavigate } from 'react-router-dom';
import SEO from '../../components/SEO';
import { ArrowRight, BookOpen, CheckSquare } from 'lucide-react';

const MCQGeneratorPage: React.FC = () => {
  const navigate = useNavigate();

  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [{
      "@type": "Question",
      "name": "Can LearnByGenie generate MCQs?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes! You can upload any PDF notes or textbook chapters, and LearnByGenie will automatically generate multiple-choice questions (MCQs) to help you practice and test your knowledge."
      }
    }]
  };

  return (
    <div className="min-h-[100dvh] bg-[var(--bg-primary)]">
      <SEO 
        title="MCQ Generator from PDF - LearnByGenie"
        description="Generate Multiple Choice Questions (MCQs) automatically from your PDF notes. Test your knowledge and prepare for exams with LearnByGenie."
        canonical="/mcq-generator"
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
          AI MCQ Generator from PDF
        </h1>
        <p className="text-lg text-[var(--text-secondary)] mb-12 text-center max-w-2xl mx-auto">
          Turn your study materials into practice tests instantly. Our AI MCQ generator creates quizzes directly from your uploaded notes.
        </p>

        <div className="bg-[var(--bg-secondary)] p-8 rounded-3xl border border-[var(--border)] mb-16 text-center">
          <CheckSquare className="w-16 h-16 text-[var(--accent-green)] mx-auto mb-6" />
          <h2 className="text-2xl font-bold mb-4">Practice Makes Perfect</h2>
          <p className="text-[var(--text-secondary)] mb-6 max-w-lg mx-auto">
            Reading isn't enough. Active recall is the key to scoring high marks. Generate practice questions in seconds and test your understanding before the actual exam.
          </p>
          <button onClick={() => navigate('/auth')} className="bg-[var(--accent-green)] text-white px-8 py-3 rounded-xl font-bold inline-flex items-center gap-2 hover:bg-[var(--accent-green-hover)] transition-colors">
            Generate MCQs Now <ArrowRight className="w-5 h-5" />
          </button>
        </div>

        <div className="mb-16">
          <h2 className="text-2xl font-bold mb-6">FAQ</h2>
          <div>
            <h3 className="font-bold text-lg mb-2">Can LearnByGenie generate MCQs?</h3>
            <p className="text-[var(--text-secondary)]">Yes! You can upload any PDF notes or textbook chapters, and LearnByGenie will automatically generate multiple-choice questions (MCQs) to help you practice and test your knowledge.</p>
          </div>
        </div>
        
        <div className="mt-20 pt-8 border-t border-[var(--border)] text-center text-[var(--text-secondary)]">
          <p>Explore: <a href="/exam-preparation-ai" className="text-[var(--accent-green)] hover:underline">Exam Prep</a> | <a href="/doubt-solver" className="text-[var(--accent-green)] hover:underline">Doubt Solver</a></p>
        </div>
      </main>
    </div>
  );
};

export default MCQGeneratorPage;
