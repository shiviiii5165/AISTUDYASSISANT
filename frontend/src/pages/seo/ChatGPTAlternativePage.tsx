import React from 'react';
import { useNavigate } from 'react-router-dom';
import SEO from '../../components/SEO';
import { ArrowRight, BookOpen, Brain, Zap } from 'lucide-react';

const ChatGPTAlternativePage: React.FC = () => {
  const navigate = useNavigate();

  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [{
      "@type": "Question",
      "name": "What is the best ChatGPT alternative for students?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "TeachGenie is widely considered the best ChatGPT alternative for students because it is specifically built for learning. It restricts answers to your uploaded notes, preventing hallucinations and keeping you focused on the actual syllabus."
      }
    }, {
      "@type": "Question",
      "name": "Why shouldn't I just use ChatGPT for studying?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "ChatGPT is a general-purpose AI and often gives generic or outside-the-syllabus answers. TeachGenie acts as a dedicated AI tutor that explains complex topics based purely on your NCERT or university PDFs."
      }
    }]
  };

  return (
    <div className="min-h-[100dvh] bg-[var(--bg-primary)]">
      <SEO 
        title="Best ChatGPT Alternative for Students - TeachGenie"
        description="Looking for a ChatGPT alternative for students? TeachGenie is a dedicated AI study assistant that answers questions from your own PDF notes without hallucinations."
        canonical="/chatgpt-alternative-for-students"
        schema={faqSchema}
      />
      
      <nav className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between border-b border-[var(--border)]">
        <button type="button" aria-label="TeachGenie home" className="flex items-center gap-2" onClick={() => navigate('/')}>
          <img src="/assets/genie-default.png" alt="TeachGenie Logo" className="w-8 h-8 object-contain" />
          <span className="text-xl font-bold text-[var(--text-primary)]">TeachGenie</span>
        </button>
        <button onClick={() => navigate('/auth')} className="text-sm font-semibold bg-[var(--accent-green)] text-white px-5 py-2.5 rounded-xl hover:bg-[var(--accent-green-hover)] transition-colors">
          Get Started
        </button>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-4xl md:text-5xl font-bold text-[var(--text-primary)] mb-6 text-center">
          The Best ChatGPT Alternative for Students
        </h1>
        <p className="text-lg text-[var(--text-secondary)] mb-12 text-center max-w-2xl mx-auto">
          Don't rely on generic AI that invents facts. TeachGenie is an AI study assistant that strictly answers from your uploaded PDFs and notes.
        </p>

        <div className="grid md:grid-cols-3 gap-8 mb-16">
          <div className="p-6 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border)]">
            <BookOpen className="w-8 h-8 text-[var(--accent-green)] mb-4" />
            <h3 className="text-xl font-bold mb-2">Focused Learning</h3>
            <p className="text-[var(--text-secondary)]">Answers are sourced strictly from your PDFs. No out-of-syllabus answers.</p>
          </div>
          <div className="p-6 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border)]">
            <Zap className="w-8 h-8 text-[var(--accent-green-text)] mb-4" />
            <h3 className="text-xl font-bold mb-2">Exam Modes</h3>
            <p className="text-[var(--text-secondary)]">Switch between 'Quick Answer', 'Full Chapter Crux', and 'Exam Shield Notes'.</p>
          </div>
          <div className="p-6 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border)]">
            <Brain className="w-8 h-8 text-purple-600 mb-4" />
            <h3 className="text-xl font-bold mb-2">Built-in MCQs</h3>
            <p className="text-[var(--text-secondary)]">Unlike ChatGPT, TeachGenie automatically tracks your weak topics with generated quizzes.</p>
          </div>
        </div>

        <div className="bg-[var(--bg-secondary)] p-8 rounded-3xl border border-[var(--border)] mb-16">
          <h2 className="text-2xl font-bold mb-6">Frequently Asked Questions</h2>
          <div className="space-y-6">
            <div>
              <h3 className="font-bold text-lg mb-2">What is the best ChatGPT alternative for students?</h3>
              <p className="text-[var(--text-secondary)]">TeachGenie is considered the best ChatGPT alternative for students because it focuses entirely on your uploaded syllabus and provides precise, non-hallucinated educational support.</p>
            </div>
            <div>
              <h3 className="font-bold text-lg mb-2">Why shouldn't I just use ChatGPT for studying?</h3>
              <p className="text-[var(--text-secondary)]">While ChatGPT is powerful, it lacks syllabus constraints. TeachGenie acts as an AI tutor that forces the AI to only use your PDF notes, ensuring accuracy.</p>
            </div>
          </div>
        </div>
        
        <div className="text-center">
          <button onClick={() => navigate('/auth')} className="bg-[var(--accent-green)] text-white px-8 py-4 rounded-xl font-bold text-lg inline-flex items-center gap-2 hover:bg-[var(--accent-green-hover)] transition-colors">
            Try the Best Alternative <ArrowRight className="w-5 h-5" />
          </button>
        </div>
        
        <div className="mt-20 pt-8 border-t border-[var(--border)] text-center text-[var(--text-secondary)]">
          <p>More features: <a href="/ai-tutor-for-students" className="text-[var(--accent-green)] hover:underline">AI Tutor</a> | <a href="/ai-tools-for-students" className="text-[var(--accent-green)] hover:underline">AI Tools for Students</a></p>
        </div>
      </main>
    </div>
  );
};

export default ChatGPTAlternativePage;
