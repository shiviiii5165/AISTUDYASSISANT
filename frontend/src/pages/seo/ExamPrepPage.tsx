import React from 'react';
import { useNavigate } from 'react-router-dom';
import SEO from '../../components/SEO';
import { ArrowRight, BookOpen, GraduationCap } from 'lucide-react';

const ExamPrepPage: React.FC = () => {
  const navigate = useNavigate();

  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [{
      "@type": "Question",
      "name": "Can students use AI for exam preparation?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Absolutely! AI is a powerful tool for exam prep. TeachGenie helps you summarize notes, generate practice questions, and clarify doubts, making your study sessions highly efficient."
      }
    }]
  };

  return (
    <div className="min-h-[100dvh] bg-[var(--bg-primary)]">
      <SEO 
        title="AI Exam Preparation Assistant - TeachGenie"
        description="Prepare for your exams smarter and faster. TeachGenie is an AI exam preparation assistant that helps you study from notes and test your knowledge."
        canonical="/exam-preparation-ai"
        schema={faqSchema}
      />
      
      <nav className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between border-b border-[var(--border)]">
        <button type="button" aria-label="TeachGenie home" className="flex items-center gap-2" onClick={() => navigate('/')}>
          <BookOpen className="w-6 h-6 text-[var(--accent-green)]" />
          <span className="text-xl font-bold text-[var(--text-primary)]">TeachGenie</span>
        </button>
        <button onClick={() => navigate('/auth')} className="text-sm font-semibold bg-[var(--accent-green)] text-white px-5 py-2.5 rounded-xl hover:bg-[var(--accent-green-hover)] transition-colors">
          Get Started
        </button>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-4xl md:text-5xl font-bold text-[var(--text-primary)] mb-6 text-center">
          AI Exam Preparation Assistant
        </h1>
        <p className="text-lg text-[var(--text-secondary)] mb-12 text-center max-w-2xl mx-auto">
          Score higher marks with less stress. Our AI helps you predict exam questions, summarize long chapters, and focus on what truly matters.
        </p>

        <div className="bg-[var(--bg-secondary)] p-8 rounded-3xl border border-[var(--border)] mb-16 text-center">
          <GraduationCap className="w-16 h-16 text-[var(--accent-green)] mx-auto mb-6" />
          <h2 className="text-2xl font-bold mb-4">Study Smarter, Not Harder</h2>
          <p className="text-[var(--text-secondary)] mb-6 max-w-lg mx-auto">
            Whether you're preparing for board exams, JEE, NEET, or university tests, TeachGenie adapts to your syllabus and learning pace.
          </p>
          <button onClick={() => navigate('/auth')} className="bg-[var(--accent-green)] text-white px-8 py-3 rounded-xl font-bold inline-flex items-center gap-2 hover:bg-[var(--accent-green-hover)] transition-colors">
            Start Exam Prep <ArrowRight className="w-5 h-5" />
          </button>
        </div>

        <div className="mb-16">
          <h2 className="text-2xl font-bold mb-6">FAQ</h2>
          <div>
            <h3 className="font-bold text-lg mb-2">Can students use AI for exam preparation?</h3>
            <p className="text-[var(--text-secondary)]">Absolutely! AI is a powerful tool for exam prep. TeachGenie helps you summarize notes, generate practice questions, and clarify doubts, making your study sessions highly efficient.</p>
          </div>
        </div>
        
        <div className="mt-20 pt-8 border-t border-[var(--border)] text-center text-[var(--text-secondary)]">
          <p>Explore: <a href="/ai-tutor-for-students" className="text-[var(--accent-green)] hover:underline">AI Tutor</a> | <a href="/doubt-solver" className="text-[var(--accent-green)] hover:underline">Doubt Solver</a></p>
        </div>
      </main>
    </div>
  );
};

export default ExamPrepPage;
