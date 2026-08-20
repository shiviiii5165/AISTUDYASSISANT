import React from 'react';
import { useNavigate } from 'react-router-dom';
import SEO from '../../components/SEO';
import { ArrowRight, BookOpen, HelpCircle } from 'lucide-react';

const DoubtSolverPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      <SEO 
        title="AI Doubt Solver App - Clear Your Concepts Instantly"
        description="Got a question? The TeachGenie AI doubt solver app provides instant, accurate answers and explanations based on your own study materials."
        canonical="/doubt-solver"
      />
      
      <nav className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between border-b border-[var(--border)]">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/')}>
          <BookOpen className="w-6 h-6 text-[var(--accent-green)]" />
          <span className="text-xl font-bold text-[var(--text-primary)]">TeachGenie</span>
        </div>
        <button onClick={() => navigate('/auth')} className="text-sm font-semibold bg-[var(--accent-green)] text-white px-5 py-2.5 rounded-xl hover:bg-green-700 transition-colors">
          Get Started
        </button>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-4xl md:text-5xl font-bold text-[var(--text-primary)] mb-6 text-center">
          AI Doubt Solver App
        </h1>
        <p className="text-lg text-[var(--text-secondary)] mb-12 text-center max-w-2xl mx-auto">
          Never stay stuck on a problem again. Get instant, step-by-step solutions to your doubts anytime, anywhere.
        </p>

        <div className="bg-[var(--bg-secondary)] p-8 rounded-3xl border border-[var(--border)] mb-16 text-center">
          <HelpCircle className="w-16 h-16 text-[var(--accent-green)] mx-auto mb-6" />
          <h2 className="text-2xl font-bold mb-4">Clear Doubts 24/7</h2>
          <p className="text-[var(--text-secondary)] mb-6 max-w-lg mx-auto">
            Stuck late at night? TeachGenie is always awake. Ask questions in English or Hindi/Hinglish, and get easy-to-understand explanations with page citations from your PDFs.
          </p>
          <button onClick={() => navigate('/auth')} className="bg-[var(--accent-green)] text-white px-8 py-3 rounded-xl font-bold inline-flex items-center gap-2 hover:bg-green-700 transition-colors">
            Ask a Doubt Now <ArrowRight className="w-5 h-5" />
          </button>
        </div>

        <div className="mt-20 pt-8 border-t border-[var(--border)] text-center text-[var(--text-secondary)]">
          <p>Explore: <a href="/ai-tutor-for-students" className="text-[var(--accent-green)] hover:underline">AI Tutor</a> | <a href="/mcq-generator" className="text-[var(--accent-green)] hover:underline">MCQ Generator</a></p>
        </div>
      </main>
    </div>
  );
};

export default DoubtSolverPage;
