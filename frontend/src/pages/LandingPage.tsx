import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Upload, MessageSquare, BookOpen, Brain, Languages, FileText, Sparkles, ArrowRight, Shield, Zap, HelpCircle } from 'lucide-react';
import SEO from '../components/SEO';

const fadeInUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.6, ease: "easeOut" as const },
  }),
};

const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  const homepageSchema = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebSite",
        "@id": "https://teachgenie.online/#website",
        "url": "https://teachgenie.online",
        "name": "TeachGenie",
        "description": "AI Tutor for Students | Chat With PDFs, Notes & Generate MCQs",
        "publisher": {
          "@id": "https://teachgenie.online/#organization"
        }
      },
      {
        "@type": "Organization",
        "@id": "https://teachgenie.online/#organization",
        "name": "TeachGenie",
        "url": "https://teachgenie.online",
        "logo": {
          "@type": "ImageObject",
          "url": "https://teachgenie.online/logo.png"
        }
      },
      {
        "@type": "SoftwareApplication",
        "name": "TeachGenie",
        "applicationCategory": "EducationalApplication",
        "operatingSystem": "All",
        "offers": {
          "@type": "Offer",
          "price": "0",
          "priceCurrency": "INR"
        }
      },
      {
        "@type": "FAQPage",
        "mainEntity": [
          {
            "@type": "Question",
            "name": "What is TeachGenie?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "TeachGenie is an AI study assistant for students. It acts as your personal AI tutor that can read your uploaded PDF notes and answer your doubts based on them."
            }
          },
          {
            "@type": "Question",
            "name": "Can AI explain PDF notes?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Yes, TeachGenie can read any PDF notes, textbooks, or coaching materials and explain complex topics from them in simple language."
            }
          },
          {
            "@type": "Question",
            "name": "Can TeachGenie generate MCQs?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Yes, TeachGenie can automatically generate multiple-choice questions (MCQs) from your uploaded PDFs to help you practice for exams."
            }
          },
          {
            "@type": "Question",
            "name": "Is TeachGenie useful for CBSE students?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Absolutely. CBSE students can upload NCERT PDFs or school notes and ask questions to prepare effectively for their board exams."
            }
          },
          {
            "@type": "Question",
            "name": "Can students use AI for exam preparation?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Yes, AI is highly effective for exam preparation. It helps by summarizing notes, predicting exam questions, and solving doubts 24/7."
            }
          }
        ]
      }
    ]
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] overflow-hidden">
      <SEO 
        title="TeachGenie – AI Tutor for Students | Chat With PDFs, Notes & MCQs"
        description="TeachGenie is an AI study assistant for students. Upload PDF notes, ask doubts, get simple explanations, generate MCQs, predicted exam questions and prepare smarter with your AI tutor."
        schema={homepageSchema}
      />
      {/* ── Nav ── */}
      <nav className="max-w-6xl mx-auto px-4 md:px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <img src="/logo.png" alt="TeachGenie" className="w-10 h-10 object-contain drop-shadow-sm" />
          <span className="text-lg font-bold text-[var(--text-primary)]">TeachGenie</span>
        </div>
        <div className="flex items-center gap-2 md:gap-3">
          <button
            onClick={() => navigate('/auth')}
            className="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors px-3 py-2 hidden sm:block"
          >
            Log in
          </button>
          <button
            onClick={() => navigate('/auth')}
            className="text-sm font-semibold bg-[var(--accent-green)] text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors shadow-sm"
          >
            Get Started
          </button>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="max-w-4xl mx-auto px-4 md:px-6 pt-10 md:pt-16 pb-14 md:pb-20 text-center relative">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[500px] h-[350px] bg-gradient-to-b from-[var(--accent-green)]/5 via-[var(--accent-indigo)]/5 to-transparent rounded-full blur-3xl pointer-events-none" />
        
        <motion.div initial="hidden" animate="visible" className="relative z-10">
          <motion.div custom={0} variants={fadeInUp} className="inline-flex items-center gap-2 px-3 py-1 bg-[var(--accent-green-light)] text-[var(--accent-green)] rounded-full text-xs font-semibold mb-5">
            <Sparkles className="w-3.5 h-3.5" />
            Your AI Teacher. Anytime, Anywhere.
          </motion.div>

          <motion.h1 custom={1} variants={fadeInUp} className="text-3xl sm:text-4xl md:text-5xl font-bold text-[var(--text-primary)] mb-5 leading-tight tracking-tight">
            AI Tutor for Students — <br className="hidden sm:block"/>
            <span className="bg-gradient-to-r from-[var(--accent-green)] to-[var(--accent-indigo)] bg-clip-text text-transparent">
              Learn From Your Notes With AI
            </span>
          </motion.h1>

          <motion.p custom={2} variants={fadeInUp} className="text-sm sm:text-base text-[var(--text-secondary)] mb-8 max-w-xl mx-auto leading-relaxed">
            Upload your notes and PDFs. Ask questions, understand concepts in simple language, generate MCQs, and prepare for exams with your personal AI tutor.
          </motion.p>
          
          <motion.div custom={3} variants={fadeInUp} className="flex flex-col sm:flex-row gap-3 justify-center">
            <button 
              onClick={() => navigate('/auth?intent=upload')} 
              className="bg-[var(--accent-green)] text-white px-6 py-3 rounded-xl font-semibold shadow-md hover:bg-green-700 hover:shadow-lg transition-all flex items-center justify-center gap-2 text-sm"
            >
              Upload Your First PDF
              <ArrowRight className="w-4 h-4" />
            </button>
            <a 
              href="#how-it-works"
              className="border border-[var(--border-strong)] text-[var(--text-primary)] px-6 py-3 rounded-xl font-semibold hover:bg-[var(--bg-hover)] transition-colors text-sm text-center"
            >
              See how it works
            </a>
          </motion.div>
        </motion.div>
      </section>

      {/* ── SEO Section 1: Study Assistant ── */}
      <section className="bg-[var(--bg-secondary)] border-y border-[var(--border)]">
        <div className="max-w-4xl mx-auto px-4 md:px-6 py-12 md:py-16 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-4">
            AI Study Assistant For Students
          </h2>
          <p className="text-[var(--text-secondary)] max-w-2xl mx-auto text-sm sm:text-base leading-relaxed">
            TeachGenie isn't just a search engine. It's a dedicated AI study assistant that understands your syllabus. By uploading your specific textbooks or handwritten notes, the AI adapts to your curriculum, giving you precise, relevant answers that actually help you score better marks.
          </p>
        </div>
      </section>

      {/* ── How It Works / PDF Chat ── */}
      <section id="how-it-works" className="max-w-4xl mx-auto px-4 md:px-6 py-12 md:py-16">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} className="text-center mb-10">
          <motion.h2 custom={0} variants={fadeInUp} className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-2">
            Chat With Your PDF Notes Using AI
          </motion.h2>
          <motion.p custom={1} variants={fadeInUp} className="text-[var(--text-secondary)] max-w-xl mx-auto text-sm">
            Transform static documents into interactive learning experiences.
          </motion.p>
        </motion.div>

        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-50px" }} className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            {
              icon: <Upload className="w-6 h-6 text-[var(--accent-green)]" />,
              step: '01',
              title: 'Upload PDF',
              desc: 'Drag and drop any study material — NCERT textbooks, coaching notes, question banks.',
              color: 'bg-green-50 border-green-100',
            },
            {
              icon: <MessageSquare className="w-6 h-6 text-[var(--accent-indigo)]" />,
              step: '02',
              title: 'Ask in Hindi or English',
              desc: 'Type your doubt naturally. "Explain photosynthesis" or "Newton ka teesra niyam samjhao".',
              color: 'bg-indigo-50 border-indigo-100',
            },
            {
              icon: <Brain className="w-6 h-6 text-purple-600" />,
              step: '03',
              title: 'Get Cited Answers',
              desc: 'AI answers from YOUR PDF only with exact page numbers. No hallucinations, no internet fluff.',
              color: 'bg-purple-50 border-purple-100',
            },
          ].map((item, i) => (
            <motion.div key={i} custom={i} variants={fadeInUp} className={`p-5 rounded-xl border ${item.color} relative group hover:shadow-[var(--shadow-md)] transition-all duration-300`}>
              <div className="absolute top-3 right-3 text-3xl font-black text-black/[0.04]">{item.step}</div>
              <div className="w-11 h-11 bg-white rounded-lg flex items-center justify-center mb-4 shadow-sm group-hover:scale-105 transition-transform">{item.icon}</div>
              <h3 className="text-sm font-bold text-[var(--text-primary)] mb-1.5">{item.title}</h3>
              <p className="text-[var(--text-secondary)] text-xs leading-relaxed">{item.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* ── Features ── */}
      <section className="bg-white border-y border-[var(--border)]">
        <div className="max-w-4xl mx-auto px-4 md:px-6 py-12 md:py-16">
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} className="text-center mb-10">
            <motion.h2 custom={0} variants={fadeInUp} className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-2">
              Generate MCQs From Your Study Material
            </motion.h2>
            <motion.p custom={1} variants={fadeInUp} className="text-[var(--text-secondary)] max-w-xl mx-auto text-sm">
              Test your knowledge instantly with our AI exam preparation assistant.
            </motion.p>
          </motion.div>

          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-50px" }} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              {
                icon: <Languages className="w-4.5 h-4.5 text-[var(--accent-green)]" />,
                title: 'Understand Difficult Topics Easily',
                desc: 'Get step-by-step explanations for complex problems in Hindi, English, or Hinglish.',
              },
              {
                icon: <FileText className="w-4.5 h-4.5 text-[var(--accent-indigo)]" />,
                title: 'Page Citations',
                desc: 'Every answer shows the exact page numbers from your uploaded PDF so you can verify.',
              },
              {
                icon: <Shield className="w-4.5 h-4.5 text-purple-600" />,
                title: 'No Hallucinations',
                desc: 'Answers come only from YOUR PDF — never from random internet searches.',
              },
              {
                icon: <BookOpen className="w-4.5 h-4.5 text-rose-600" />,
                title: 'Any Notes Work',
                desc: 'NCERT, RD Sharma, HC Verma, coaching modules, and handwritten notes are all supported.',
              },
              {
                icon: <Zap className="w-4.5 h-4.5 text-amber-600" />,
                title: 'AI Exam Preparation Assistant',
                desc: 'Predict exam questions and get tailored practice tests to boost your confidence.',
              },
              {
                icon: <Sparkles className="w-4.5 h-4.5 text-cyan-600" />,
                title: 'Step-by-Step Solutions',
                desc: 'Stuck on numericals? Get detailed, step-by-step breakdowns for maths and physics.',
              },
            ].map((feature, i) => (
              <motion.div key={i} custom={i} variants={fadeInUp} className="p-4 rounded-xl border border-[var(--border)] hover:border-[var(--accent-green)]/40 hover:shadow-[var(--shadow-md)] transition-all duration-300 bg-[var(--bg-primary)] group">
                <div className="w-9 h-9 bg-[var(--bg-secondary)] rounded-lg flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">{feature.icon}</div>
                <h3 className="font-bold text-[var(--text-primary)] text-sm mb-1">{feature.title}</h3>
                <p className="text-[var(--text-secondary)] text-xs leading-relaxed">{feature.desc}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── FAQ Section ── */}
      <section className="bg-[var(--bg-secondary)] py-12 md:py-16">
        <div className="max-w-3xl mx-auto px-4 md:px-6">
          <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-8 text-center">
            Frequently Asked Questions
          </h2>
          
          <div className="space-y-3">
            {[
              { q: 'What is TeachGenie?', a: 'TeachGenie is an AI study assistant for students. It acts as your personal AI tutor that can read your uploaded PDF notes and answer your doubts based on them.' },
              { q: 'Can AI explain PDF notes?', a: 'Yes, TeachGenie can read any PDF notes, textbooks, or coaching materials and explain complex topics from them in simple language.' },
              { q: 'Can TeachGenie generate MCQs?', a: 'Yes, TeachGenie can automatically generate multiple-choice questions (MCQs) from your uploaded PDFs to help you practice for exams.' },
              { q: 'Is TeachGenie useful for CBSE students?', a: 'Absolutely. CBSE students can upload NCERT PDFs or school notes and ask questions to prepare effectively for their board exams.' },
              { q: 'Can students use AI for exam preparation?', a: 'Yes, AI is highly effective for exam preparation. It helps by summarizing notes, predicting exam questions, and solving doubts 24/7.' },
            ].map((faq, i) => (
              <div key={i} className="bg-white p-4 md:p-5 rounded-xl border border-[var(--border)] shadow-[var(--shadow-sm)]">
                <h3 className="text-sm font-bold text-[var(--text-primary)] mb-1.5 flex items-center gap-2">
                  <HelpCircle className="w-4 h-4 text-[var(--accent-green)] shrink-0" />
                  {faq.q}
                </h3>
                <p className="text-[var(--text-secondary)] text-xs leading-relaxed ml-6">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="max-w-4xl mx-auto px-4 md:px-6 py-12 md:py-16 text-center">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }}>
          <motion.h2 custom={0} variants={fadeInUp} className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-3">
            Ready to study smarter?
          </motion.h2>
          <motion.p custom={1} variants={fadeInUp} className="text-[var(--text-secondary)] mb-6 max-w-md mx-auto text-sm">
            Join thousands of students who are learning directly from their own notes with AI.
          </motion.p>
          <motion.button
            custom={2}
            variants={fadeInUp}
            onClick={() => navigate('/auth')}
            className="bg-[var(--accent-green)] text-white px-8 py-3 rounded-xl font-semibold text-sm shadow-md hover:bg-green-700 hover:shadow-lg transition-all inline-flex items-center gap-2"
          >
            Start for Free
            <ArrowRight className="w-4 h-4" />
          </motion.button>
        </motion.div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-[var(--border)] bg-[var(--bg-secondary)]">
        <div className="max-w-5xl mx-auto px-4 md:px-6 py-8 md:py-10">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center gap-2 mb-3">
                <img src="/logo.png" alt="TeachGenie" className="w-8 h-8 object-contain" />
                <span className="font-bold text-[var(--text-primary)] text-base">TeachGenie</span>
              </div>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                Your AI Teacher. Anytime, Anywhere.
              </p>
            </div>
            
            <div>
              <h4 className="font-bold text-[var(--text-primary)] text-xs uppercase tracking-wider mb-3">Features</h4>
              <ul className="space-y-1.5 text-xs text-[var(--text-secondary)]">
                <li><Link to="/pdf-chat-ai" className="hover:text-[var(--accent-green)] transition-colors">Chat with PDF</Link></li>
                <li><Link to="/mcq-generator" className="hover:text-[var(--accent-green)] transition-colors">MCQ Generator</Link></li>
                <li><Link to="/doubt-solver" className="hover:text-[var(--accent-green)] transition-colors">Doubt Solver</Link></li>
                <li><Link to="/exam-preparation-ai" className="hover:text-[var(--accent-green)] transition-colors">Exam Prep AI</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-bold text-[var(--text-primary)] text-xs uppercase tracking-wider mb-3">Resources</h4>
              <ul className="space-y-1.5 text-xs text-[var(--text-secondary)]">
                <li><Link to="/ai-tutor-for-students" className="hover:text-[var(--accent-green)] transition-colors">AI Tutor for Students</Link></li>
                <li><Link to="/blog" className="hover:text-[var(--accent-green)] transition-colors">Blog</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-bold text-[var(--text-primary)] text-xs uppercase tracking-wider mb-3">Legal</h4>
              <ul className="space-y-1.5 text-xs text-[var(--text-secondary)]">
                <li><Link to="/privacy-policy" className="hover:text-[var(--accent-green)] transition-colors">Privacy Policy</Link></li>
                <li><Link to="/terms-of-service" className="hover:text-[var(--accent-green)] transition-colors">Terms of Service</Link></li>
                <li><Link to="/cookie-policy" className="hover:text-[var(--accent-green)] transition-colors">Cookie Policy</Link></li>
              </ul>
            </div>
          </div>
          
          <div className="pt-5 border-t border-[var(--border)] flex flex-col md:flex-row items-center justify-between gap-3">
            <p className="text-xs text-[var(--text-muted)]">
              © {new Date().getFullYear()} TeachGenie. Built for students, with ❤️
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
