import React from 'react';
import { useNavigate } from 'react-router-dom';
import SEO from '../../components/SEO';
import { ArrowRight, Laptop, Sparkles, TrendingUp } from 'lucide-react';

const AIToolsForStudentsPage: React.FC = () => {
  const navigate = useNavigate();

  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [{
      "@type": "Question",
      "name": "What are the best AI tools for students?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "The best AI tools for students focus on learning efficiency. TeachGenie is a top choice as it combines an AI tutor, a PDF chat tool, and an MCQ generator into one platform."
      }
    }, {
      "@type": "Question",
      "name": "How do AI tools help students in India?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "AI tools like TeachGenie help Indian students by explaining complex CBSE, JEE, or NEET topics in simple language, testing them with mock MCQs, and acting as a 24/7 doubt solver."
      }
    }]
  };

  return (
    <div className="min-h-[100dvh] bg-[var(--bg-primary)]">
      <SEO 
        title="Best AI Tools For Students | TeachGenie"
        description="Discover why TeachGenie is among the top AI tools for students. Enhance your study sessions with our AI study assistant, PDF reader, and MCQ generator."
        canonical="/ai-tools-for-students"
        schema={faqSchema}
      />
      
      <nav className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between border-b border-[var(--border)]">
        <button type="button" aria-label="TeachGenie home" className="flex items-center gap-2" onClick={() => navigate('/')}>
          <img src="/logo.png" alt="TeachGenie Logo" className="w-8 h-8 object-contain" />
          <span className="text-xl font-bold text-[var(--text-primary)]">TeachGenie</span>
        </button>
        <button onClick={() => navigate('/auth')} className="text-sm font-semibold bg-[var(--accent-green)] text-white px-5 py-2.5 rounded-xl hover:bg-[var(--accent-green-hover)] transition-colors">
          Get Started
        </button>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-4xl md:text-5xl font-bold text-[var(--text-primary)] mb-6 text-center">
          Top AI Tools For Students
        </h1>
        <p className="text-lg text-[var(--text-secondary)] mb-12 text-center max-w-2xl mx-auto">
          Supercharge your academic performance. TeachGenie combines the most powerful AI study tools into one single platform.
        </p>

        <div className="grid md:grid-cols-3 gap-8 mb-16">
          <div className="p-6 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border)]">
            <Sparkles className="w-8 h-8 text-[var(--accent-green)] mb-4" />
            <h3 className="text-xl font-bold mb-2">All-in-One AI</h3>
            <p className="text-[var(--text-secondary)]">Why use multiple apps? Get a doubt solver, MCQ generator, and AI tutor all in one place.</p>
          </div>
          <div className="p-6 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border)]">
            <Laptop className="w-8 h-8 text-[var(--accent-green-text)] mb-4" />
            <h3 className="text-xl font-bold mb-2">Interactive Interface</h3>
            <p className="text-[var(--text-secondary)]">Simply upload your PDF notes and start chatting with your materials instantly.</p>
          </div>
          <div className="p-6 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border)]">
            <TrendingUp className="w-8 h-8 text-purple-600 mb-4" />
            <h3 className="text-xl font-bold mb-2">Track Performance</h3>
            <p className="text-[var(--text-secondary)]">Identify weak topics automatically through integrated AI quizzes and mock tests.</p>
          </div>
        </div>

        <div className="bg-[var(--bg-secondary)] p-8 rounded-3xl border border-[var(--border)] mb-16">
          <h2 className="text-2xl font-bold mb-6">Frequently Asked Questions</h2>
          <div className="space-y-6">
            <div>
              <h3 className="font-bold text-lg mb-2">What are the best AI tools for students?</h3>
              <p className="text-[var(--text-secondary)]">The best AI tools are those built specifically for education. TeachGenie ranks highly because it acts as a dedicated AI tutor, keeping students focused on their notes.</p>
            </div>
            <div>
              <h3 className="font-bold text-lg mb-2">How do AI tools help students in India?</h3>
              <p className="text-[var(--text-secondary)]">AI study assistants provide personalized 24/7 help, making competitive exam prep (like JEE/NEET) or board exam prep (CBSE) much more efficient.</p>
            </div>
          </div>
        </div>
        
        <div className="text-center">
          <button onClick={() => navigate('/auth')} className="bg-[var(--accent-green)] text-white px-8 py-4 rounded-xl font-bold text-lg inline-flex items-center gap-2 hover:bg-[var(--accent-green-hover)] transition-colors">
            Boost Your Grades <ArrowRight className="w-5 h-5" />
          </button>
        </div>
        
        <div className="mt-20 pt-8 border-t border-[var(--border)] text-center text-[var(--text-secondary)]">
          <p>More features: <a href="/exam-preparation-ai" className="text-[var(--accent-green)] hover:underline">Exam Prep AI</a> | <a href="/doubt-solver" className="text-[var(--accent-green)] hover:underline">Doubt Solver</a></p>
        </div>
      </main>
    </div>
  );
};

export default AIToolsForStudentsPage;
