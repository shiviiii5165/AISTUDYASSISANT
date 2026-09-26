import React, { useState, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import {
  Upload, MessageSquare, FileSearch, Languages, FileText, PenLine,
  ArrowRight, ShieldCheck, ListChecks, Presentation, Map, Video, Plus, Minus,
  GraduationCap, BookOpen, Zap, CheckCircle2,
} from 'lucide-react';
import SEO from '../components/SEO';
import { LANDING } from '../lib/assets';
import { MagneticButton } from '../components/MotionUtils';

const EASE = [0.16, 1, 0.3, 1] as const;

// Reusable wave SVG divider — direction controls which way the wave curves
const WaveDivider = ({
  fromColor,
  toColor,
  flip = false,
}: {
  fromColor: string;
  toColor: string;
  flip?: boolean;
}) => (
  <div
    className="relative w-full overflow-hidden leading-none"
    style={{ background: fromColor, marginBottom: '-2px' }}
    aria-hidden="true"
  >
    <svg
      viewBox="0 0 1440 80"
      xmlns="http://www.w3.org/2000/svg"
      preserveAspectRatio="none"
      className="block w-full"
      style={{ height: '70px', transform: flip ? 'scaleY(-1)' : undefined }}
    >
      <path
        d="M0,40 C240,80 480,0 720,40 C960,80 1200,0 1440,40 L1440,80 L0,80 Z"
        fill={toColor}
      />
    </svg>
  </div>
);

// Small white pill-card used inside blue sections (Weav floating-feature-card pattern)
const PillCard = ({
  icon: Icon,
  label,
}: {
  icon: React.ElementType;
  label: string;
}) => (
  <span className="inline-flex items-center gap-2 rounded-full bg-white/90 px-4 py-2 text-sm font-semibold text-[#1B2CC1] shadow-md backdrop-blur-sm">
    <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
    {label}
  </span>
);

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const reduce = useReducedMotion();
  const [openFaq, setOpenFaq] = useState<number | null>(0);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const goToAuth = () => navigate('/auth');

  const homepageSchema = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebSite",
        "@id": "https://teachgenie.online/#website",
        "url": "https://teachgenie.online",
        "name": "LearnByGenie",
        "description": "AI Tutor for Students | Chat With PDFs, Notes & Generate MCQs",
        "publisher": { "@id": "https://teachgenie.online/#organization" },
      },
      {
        "@type": "Organization",
        "@id": "https://teachgenie.online/#organization",
        "name": "LearnByGenie",
        "url": "https://teachgenie.online",
        "logo": { "@type": "ImageObject", "url": "https://teachgenie.online/logo.png" },
      },
      {
        "@type": "SoftwareApplication",
        "name": "LearnByGenie",
        "applicationCategory": "EducationalApplication",
        "operatingSystem": "All",
        "offers": { "@type": "Offer", "price": "0", "priceCurrency": "INR" },
      },
      {
        "@type": "FAQPage",
        "mainEntity": [
          { "@type": "Question", "name": "What is LearnByGenie?", "acceptedAnswer": { "@type": "Answer", "text": "LearnByGenie is an AI study assistant for students. It acts as your personal AI tutor that can read your uploaded PDF notes and answer your doubts based on them." } },
          { "@type": "Question", "name": "Can AI explain PDF notes?", "acceptedAnswer": { "@type": "Answer", "text": "Yes, LearnByGenie can read any PDF notes, textbooks, or coaching materials and explain complex topics from them in simple language." } },
          { "@type": "Question", "name": "Can LearnByGenie generate MCQs?", "acceptedAnswer": { "@type": "Answer", "text": "Yes, LearnByGenie can automatically generate multiple-choice questions (MCQs) from your uploaded PDFs to help you practice for exams." } },
          { "@type": "Question", "name": "Is LearnByGenie useful for CBSE students?", "acceptedAnswer": { "@type": "Answer", "text": "Absolutely. CBSE students can upload NCERT PDFs or school notes and ask questions to prepare effectively for their board exams." } },
          { "@type": "Question", "name": "Can students use AI for exam preparation?", "acceptedAnswer": { "@type": "Answer", "text": "Yes, AI is highly effective for exam preparation. It helps by summarizing notes, predicting exam questions, and solving doubts 24/7." } },
        ],
      },
    ],
  };

  const faqs = [
    { q: 'What is LearnByGenie?', a: 'LearnByGenie is an AI study assistant for students. It acts as your personal AI tutor that can read your uploaded PDF notes and answer your doubts based on them.' },
    { q: 'Can AI explain PDF notes?', a: 'Yes, LearnByGenie can read any PDF notes, textbooks, or coaching materials and explain complex topics from them in simple language.' },
    { q: 'Can LearnByGenie generate MCQs?', a: 'Yes, LearnByGenie can automatically generate multiple-choice questions (MCQs) from your uploaded PDFs to help you practice for exams.' },
    { q: 'Is LearnByGenie useful for CBSE students?', a: 'Absolutely. CBSE students can upload NCERT PDFs or school notes and ask questions to prepare effectively for their board exams.' },
    { q: 'Can students use AI for exam preparation?', a: 'Yes, AI is highly effective for exam preparation. It helps by summarizing notes, predicting exam questions, and solving doubts 24/7.' },
  ];

  const steps = [
    { icon: Upload, title: 'Upload', desc: 'Add a PDF textbook, a coaching module or a photo of your handwritten notes.' },
    { icon: MessageSquare, title: 'Ask', desc: 'Type the doubt the way you would say it out loud, in English, Hindi or Hinglish.' },
    { icon: FileSearch, title: 'Verify', desc: 'Every answer carries the page it came from, so you can open the book and confirm it.' },
  ];

  const studentPoints = [
    'Ask questions against your own PDFs and handwritten notes',
    'Answers cite the exact page, so nothing has to be taken on trust',
    'Practice MCQs generated from the material you actually study',
    'Guided Teach Me sessions that adapt as your answers improve',
  ];

  const teacherPoints = [
    'Lesson roadmaps staged by learning objective, with timings, prerequisites and checkpoint questions',
    'Core, support and extension variants planned for every stage',
    'Slide decks of 10 to 15 slides with speaker notes and diagrams, downloadable as PPTX',
    'Video lessons built scene by scene, with any single scene regenerable',
  ];

  const featurePills = [
    { icon: Upload, label: 'PDF Upload' },
    { icon: MessageSquare, label: 'AI Chat' },
    { icon: ListChecks, label: 'MCQ Generator' },
    { icon: GraduationCap, label: 'Teach Me Mode' },
    { icon: Presentation, label: 'Slide Decks' },
    { icon: Map, label: 'Lesson Planner' },
    { icon: Video, label: 'Video Lessons' },
    { icon: BookOpen, label: 'Note Analysis' },
    { icon: Zap, label: 'Instant Answers' },
    { icon: Languages, label: 'Hindi / Hinglish' },
  ];

  return (
    <div ref={wrapperRef} className="bg-[#FAFAF8]">
      <SEO
        title="LearnByGenie - AI Tutor for Students | Chat With PDFs, Notes & MCQs"
        description="LearnByGenie is an AI study assistant for students. Upload PDF notes, ask doubts, get simple explanations, generate MCQs, predicted exam questions and prepare smarter with your AI tutor."
        schema={homepageSchema}
      />

      <a href="#main" className="skip-link sr-only focus:not-sr-only">Skip to content</a>

      {/* ── Teak-style fixed nav ── */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-[rgba(9,21,64,0.08)] bg-[#FAFAF8]/90 backdrop-blur-md">
        <nav
          aria-label="Primary"
          className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-6 px-4 md:px-6"
        >
          {/* Logo mark — small square, Teak pattern */}
          <Link
            to="/"
            className="flex shrink-0 items-center gap-2.5 rounded-lg"
            aria-label="LearnByGenie home"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#1B2CC1]">
              <img src="/assets/genie-default.png" alt="" width={20} height={20} className="h-5 w-5 object-contain brightness-0 invert" />
            </div>
            <span className="font-display text-base font-bold tracking-tight text-[#091540]">
              LearnByGenie
            </span>
          </Link>

          {/* Minimal text links (Teak pattern) */}
          <div className="hidden items-center gap-1 md:flex">
            <Link to="/pricing" className="rounded-lg px-3 py-2 text-sm font-medium text-[#6B7280] transition-colors hover:bg-[#F3F4F6] hover:text-[#091540]">
              Pricing
            </Link>
            <Link to="/support" className="rounded-lg px-3 py-2 text-sm font-medium text-[#6B7280] transition-colors hover:bg-[#F3F4F6] hover:text-[#091540]">
              Support
            </Link>
            <button
              type="button"
              onClick={goToAuth}
              className="rounded-lg px-3 py-2 text-sm font-medium text-[#6B7280] transition-colors hover:bg-[#F3F4F6] hover:text-[#091540]"
            >
              Log in
            </button>
          </div>

          {/* Pill CTA — Teak pattern: solid Vibrant Royal */}
          <MagneticButton>
            <button
              type="button"
              onClick={goToAuth}
              className="rounded-full bg-[#1B2CC1] px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all duration-200 hover:bg-[#091540] hover:shadow-md active:scale-[0.98]"
            >
              Start free
            </button>
          </MagneticButton>
        </nav>
      </header>

      {/* ── ScrollSmoother wrapper ── */}
      <div id="lp-smooth-wrapper">
        <div id="lp-smooth-content">
          <main id="main" className="pt-16">

            {/* ══ SECTION 1: Hero — cream background ══ */}
            <section className="relative overflow-hidden bg-[#FAFAF8]">
              <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-10 px-4 pb-20 pt-24 md:px-6 md:pb-28 md:pt-32 lg:grid-cols-2">

                {/* Left: headline + CTA */}
                <div className="flex flex-col items-start">
                  <motion.p
                    initial={reduce ? false : { opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, ease: EASE }}
                    className="mb-5 inline-flex items-center gap-2 rounded-full bg-[#ABD2FA]/40 px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-[#1B2CC1]"
                  >
                    <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                    AI-Powered Study Assistant
                  </motion.p>

                  <motion.h1
                    initial={reduce ? false : { opacity: 0, y: 24 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.65, delay: 0.08, ease: EASE }}
                    className="font-display text-5xl font-bold leading-[1.05] tracking-tight text-[#091540] sm:text-6xl lg:text-7xl"
                  >
                    Study from your notes.{' '}
                    <span className="text-[#1B2CC1]">Teach from them too.</span>
                  </motion.h1>

                  <motion.p
                    initial={reduce ? false : { opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.55, delay: 0.18, ease: EASE }}
                    className="mt-6 max-w-[44ch] text-lg leading-relaxed text-[#6B7280]"
                  >
                    Upload your material once. Students get cited answers and practice questions.
                    Teachers get lesson plans, slide decks and video lessons.
                  </motion.p>

                  <motion.div
                    initial={reduce ? false : { opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.28, ease: EASE }}
                    className="mt-10 flex flex-col gap-3 sm:flex-row"
                  >
                    <MagneticButton>
                      <button
                        type="button"
                        onClick={goToAuth}
                        className="inline-flex items-center justify-center gap-2 rounded-full bg-[#1B2CC1] px-8 py-4 text-base font-semibold text-white shadow-lg shadow-[#1B2CC1]/30 transition-all duration-200 hover:bg-[#091540] hover:shadow-xl hover:shadow-[#091540]/20 active:scale-[0.98]"
                      >
                        Start free
                        <ArrowRight className="h-5 w-5" aria-hidden="true" />
                      </button>
                    </MagneticButton>
                    <a
                      href="#how-it-works"
                      className="inline-flex items-center justify-center rounded-full border border-[rgba(9,21,64,0.2)] px-8 py-4 text-base font-semibold text-[#091540] transition-colors hover:bg-[#ABD2FA]/20"
                    >
                      See how it works
                    </a>
                  </motion.div>
                </div>

                {/* Right: browser-window product mockup */}
                <motion.div
                  initial={reduce ? false : { opacity: 0, scale: 0.95, y: 20 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  transition={{ duration: 0.9, delay: 0.15, ease: 'easeOut' }}
                  className="relative hidden lg:flex items-center justify-center"
                >
                  {/* Soft glow blobs */}
                  <div className="absolute top-1/4 left-1/4 h-56 w-56 rounded-full bg-[#ABD2FA] blur-[70px] opacity-50" />
                  <div className="absolute bottom-1/4 right-1/4 h-56 w-56 rounded-full bg-[#7692FF] blur-[70px] opacity-30" />

                  {/* Browser chrome frame */}
                  <div className="relative w-full rounded-2xl border border-[rgba(9,21,64,0.1)] bg-white shadow-2xl shadow-[rgba(9,21,64,0.12)]">
                    {/* Chrome bar */}
                    <div className="flex items-center gap-2 border-b border-[rgba(9,21,64,0.08)] px-4 py-3">
                      <span className="h-3 w-3 rounded-full bg-[#FF5F57]" />
                      <span className="h-3 w-3 rounded-full bg-[#FFBD2E]" />
                      <span className="h-3 w-3 rounded-full bg-[#28C840]" />
                      <div className="mx-auto h-6 w-48 rounded-md bg-[#F3F4F6] text-center text-[10px] leading-6 text-[#9CA3AF]">
                        learnbygenie.com/dashboard
                      </div>
                    </div>
                    {/* Screenshot area */}
                    <div className="relative min-h-[320px] overflow-hidden rounded-b-2xl bg-[#FAFAF8]">
                      <img
                        src={LANDING.hero}
                        alt="LearnByGenie dashboard"
                        className="w-full object-cover object-top"
                        onError={(e) => {
                          // Fallback: show a styled placeholder
                          const target = e.currentTarget;
                          target.style.display = 'none';
                          const parent = target.parentElement;
                          if (parent) {
                            parent.innerHTML = `
                              <div class="flex flex-col gap-4 p-6">
                                <div class="h-8 w-48 rounded-lg bg-[#ABD2FA]/50"></div>
                                <div class="grid grid-cols-3 gap-3">
                                  ${[1,2,3].map(() => `<div class="h-24 rounded-xl bg-white border border-[rgba(9,21,64,0.08)] shadow-sm p-3"><div class="h-3 w-16 rounded bg-[#ABD2FA]/60 mb-2"></div><div class="h-6 w-10 rounded bg-[#1B2CC1]/20"></div></div>`).join('')}
                                </div>
                                <div class="h-32 rounded-xl bg-white border border-[rgba(9,21,64,0.08)] shadow-sm p-4">
                                  <div class="h-3 w-full rounded bg-[#F3F4F6] mb-2"></div>
                                  <div class="h-3 w-4/5 rounded bg-[#F3F4F6] mb-2"></div>
                                  <div class="h-3 w-3/5 rounded bg-[#F3F4F6]"></div>
                                </div>
                              </div>
                            `;
                          }
                        }}
                      />
                    </div>
                  </div>
                </motion.div>
              </div>
            </section>

            {/* Wave: cream → royal blue */}
            <div className="wave-divider">
              <WaveDivider fromColor="#FAFAF8" toColor="#1B2CC1" />
            </div>

            {/* ══ SECTION 2: How it works — royal blue band ══ */}
            <section id="how-it-works" className="bg-[#1B2CC1] py-20 md:py-28">
              <div className="mx-auto max-w-6xl px-4 md:px-6">
                <div className="gsap-reveal mb-4 text-center">
                  <span className="rounded-full bg-white/20 px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-white">
                    How it works
                  </span>
                </div>
                <h2 className="gsap-reveal font-display text-center text-3xl font-bold tracking-tight text-white sm:text-4xl">
                  Three steps, then verify it yourself
                </h2>

                {/* Steps as pill-card row */}
                <div className="mt-14 grid grid-cols-1 gap-6 md:grid-cols-3">
                  {steps.map((step, i) => (
                    <div key={step.title} className="gsap-reveal flex flex-col items-center text-center">
                      {/* Step number ring */}
                      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-white/10 text-xl font-bold text-white ring-2 ring-white/30">
                        {i + 1}
                      </div>
                      <step.icon className="mb-3 h-7 w-7 text-[#ABD2FA]" aria-hidden="true" />
                      <h3 className="font-display text-lg font-semibold text-white">{step.title}</h3>
                      <p className="mt-2 max-w-[32ch] text-sm leading-relaxed text-[#ABD2FA]">{step.desc}</p>
                    </div>
                  ))}
                </div>

                {/* Floating pill cards — Weav floating-feature-card pattern */}
                <div className="mt-16 flex flex-wrap justify-center gap-3">
                  {featurePills.map((pill) => (
                    <div key={pill.label} className="gsap-reveal">
                      <PillCard icon={pill.icon} label={pill.label} />
                    </div>
                  ))}
                </div>
              </div>
            </section>

            {/* Wave: royal blue → cream */}
            <div className="wave-divider">
              <WaveDivider fromColor="#1B2CC1" toColor="#FAFAF8" flip />
            </div>

            {/* ══ SECTION 3: Two audiences — cream ══ */}
            <section className="bg-[#FAFAF8] py-20 md:py-28">
              <div className="mx-auto max-w-6xl px-4 md:px-6">
                <h2 className="gsap-reveal font-display max-w-[24ch] text-3xl font-bold tracking-tight text-[#091540] sm:text-4xl">
                  Two jobs, one set of material
                </h2>

                <div className="mt-12 grid grid-cols-1 gap-6 lg:grid-cols-2">
                  {/* Student card */}
                  <div className="gsap-reveal rounded-2xl border border-[rgba(9,21,64,0.08)] bg-white p-7 shadow-[0_4px_20px_-2px_rgba(9,21,64,0.05)] md:p-8">
                    <div className="mb-6 flex items-center gap-3">
                      <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#ABD2FA]/40">
                        <ListChecks className="h-5 w-5 text-[#1B2CC1]" aria-hidden="true" />
                      </span>
                      <h3 className="font-display text-xl font-semibold text-[#091540]">If you are studying</h3>
                    </div>
                    <ul className="space-y-4">
                      {studentPoints.map((point) => (
                        <li key={point} className="flex gap-3 text-sm leading-relaxed text-[#6B7280]">
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#1B2CC1]" aria-hidden="true" />
                          {point}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Teacher card */}
                  <div className="gsap-reveal rounded-2xl border border-[rgba(9,21,64,0.08)] bg-white p-7 shadow-[0_4px_20px_-2px_rgba(9,21,64,0.05)] md:p-8">
                    <div className="mb-6 flex items-center gap-3">
                      <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#ABD2FA]/40">
                        <Map className="h-5 w-5 text-[#1B2CC1]" aria-hidden="true" />
                      </span>
                      <h3 className="font-display text-xl font-semibold text-[#091540]">If you are teaching</h3>
                    </div>
                    <ul className="space-y-4">
                      {teacherPoints.map((point) => (
                        <li key={point} className="flex gap-3 text-sm leading-relaxed text-[#6B7280]">
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#1B2CC1]" aria-hidden="true" />
                          {point}
                        </li>
                      ))}
                    </ul>
                    <div className="mt-6 flex flex-wrap gap-2 border-t border-[rgba(9,21,64,0.08)] pt-5">
                      {[{ icon: Map, label: 'Lesson planner' }, { icon: Presentation, label: 'Slide decks' }, { icon: Video, label: 'Video lessons' }].map((t) => (
                        <span key={t.label} className="inline-flex items-center gap-1.5 rounded-full bg-[#ABD2FA]/30 px-3 py-1.5 text-xs font-semibold text-[#1B2CC1]">
                          <t.icon className="h-3.5 w-3.5" aria-hidden="true" />
                          {t.label}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* Wave: cream → periwinkle (lighter blue for variety) */}
            <div className="wave-divider">
              <WaveDivider fromColor="#FAFAF8" toColor="#7692FF" />
            </div>

            {/* ══ SECTION 4: Features bento — periwinkle band ══ */}
            <section className="bg-[#7692FF] py-20 md:py-28">
              <div className="mx-auto max-w-6xl px-4 md:px-6">
                <div className="gsap-reveal mb-4 text-center">
                  <span className="rounded-full bg-white/20 px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-white">
                    Features
                  </span>
                </div>
                <h2 className="gsap-reveal font-display text-center text-3xl font-bold tracking-tight text-white sm:text-5xl">
                  What the answer actually gives you
                </h2>

                <div className="mt-14 grid auto-rows-[280px] grid-flow-dense grid-cols-1 gap-5 md:grid-cols-6">
                  {/* Hero bento cell — navy bg, spans 4 cols 2 rows */}
                  <div className="gsap-reveal relative flex flex-col justify-end overflow-hidden rounded-2xl bg-[#091540] p-8 md:col-span-4 md:row-span-2 md:p-10">
                    <div className="absolute -right-8 -top-8 h-56 w-56 rounded-full bg-[#1B2CC1]/40 blur-3xl" />
                    <FileText className="mb-5 h-9 w-9 text-[#ABD2FA]" aria-hidden="true" />
                    <h3 className="font-display text-3xl font-bold leading-tight text-white md:text-4xl">
                      The page number comes with the answer
                    </h3>
                    <p className="mt-4 max-w-[44ch] text-base leading-relaxed text-[#ABD2FA]">
                      Responses are drawn from the document you uploaded and point back to where they
                      came from, so a wrong answer is something you can catch rather than something you
                      have to trust.
                    </p>
                  </div>

                  {/* Handwritten notes — white card */}
                  <div className="gsap-reveal flex flex-col rounded-2xl bg-white p-7 md:col-span-2">
                    <PenLine className="mb-4 h-7 w-7 text-[#1B2CC1]" aria-hidden="true" />
                    <h3 className="font-display text-xl font-bold text-[#091540]">Handwritten notes work</h3>
                    <p className="mt-2 text-sm leading-relaxed text-[#6B7280]">
                      Photograph a page of your own writing and ask questions against it.
                    </p>
                  </div>

                  {/* Practice questions */}
                  <div className="gsap-reveal flex flex-col rounded-2xl bg-white p-7 md:col-span-2">
                    <ListChecks className="mb-4 h-7 w-7 text-[#1B2CC1]" aria-hidden="true" />
                    <h3 className="font-display text-xl font-bold text-[#091540]">Practice questions</h3>
                    <p className="mt-2 text-sm leading-relaxed text-[#6B7280]">
                      Multiple choice sets built from your material, not from a generic question bank.
                    </p>
                  </div>

                  {/* Slide decks */}
                  <div className="gsap-reveal flex flex-col rounded-2xl bg-white/90 p-7 md:col-span-3">
                    <Presentation className="mb-4 h-7 w-7 text-[#1B2CC1]" aria-hidden="true" />
                    <h3 className="font-display text-xl font-bold text-[#091540]">Decks with speaker notes</h3>
                    <p className="mt-2 text-sm leading-relaxed text-[#6B7280]">
                      Ten to fifteen slides, six themes, downloadable as PPTX.
                    </p>
                  </div>

                  {/* Lesson plans */}
                  <div className="gsap-reveal flex flex-col rounded-2xl bg-[#ABD2FA]/30 p-7 md:col-span-3">
                    <Map className="mb-4 h-7 w-7 text-[#1B2CC1]" aria-hidden="true" />
                    <h3 className="font-display text-xl font-bold text-[#091540]">Plans that sequence themselves</h3>
                    <p className="mt-2 text-sm leading-relaxed text-[#091540]/70">
                      Stages ordered by prerequisite, each with its own timing and checkpoint.
                    </p>
                  </div>
                </div>
              </div>
            </section>

            {/* Wave: periwinkle → cream */}
            <div className="wave-divider">
              <WaveDivider fromColor="#7692FF" toColor="#FAFAF8" flip />
            </div>

            {/* ══ SECTION 5: FAQ — cream ══ */}
            <section className="bg-[#FAFAF8] py-20 md:py-28">
              <div className="mx-auto max-w-6xl px-4 md:px-6">
                <div className="grid grid-cols-1 gap-y-10 lg:grid-cols-12 lg:gap-x-16">
                  <div className="lg:col-span-4">
                    <h2 className="gsap-reveal font-display text-2xl font-bold leading-tight tracking-tight text-[#091540] sm:text-3xl lg:sticky lg:top-24">
                      Questions people ask first
                    </h2>
                  </div>
                  <div className="divide-y divide-[rgba(9,21,64,0.08)] border-t border-[rgba(9,21,64,0.08)] lg:col-span-8">
                    {faqs.map((faq, i) => {
                      const isOpen = openFaq === i;
                      return (
                        <div key={faq.q} className="gsap-reveal">
                          <h3>
                            <button
                              type="button"
                              onClick={() => setOpenFaq(isOpen ? null : i)}
                              aria-expanded={isOpen}
                              aria-controls={`faq-answer-${i}`}
                              id={`faq-question-${i}`}
                              className="flex w-full items-center justify-between gap-6 py-5 text-left transition-colors hover:text-[#1B2CC1]"
                            >
                              <span className="font-display text-base font-semibold text-[#091540] sm:text-lg">
                                {faq.q}
                              </span>
                              {isOpen ? (
                                <Minus className="h-4 w-4 shrink-0 text-[#6B7280]" aria-hidden="true" />
                              ) : (
                                <Plus className="h-4 w-4 shrink-0 text-[#6B7280]" aria-hidden="true" />
                              )}
                            </button>
                          </h3>
                          <div
                            id={`faq-answer-${i}`}
                            role="region"
                            aria-labelledby={`faq-question-${i}`}
                            hidden={!isOpen}
                          >
                            <p className="max-w-[62ch] pb-6 text-sm leading-relaxed text-[#6B7280]">
                              {faq.a}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </section>

            {/* Wave: cream → navy */}
            <div className="wave-divider">
              <WaveDivider fromColor="#FAFAF8" toColor="#091540" />
            </div>

            {/* ══ SECTION 6: Closing CTA — deep navy ══ */}
            <section className="bg-[#091540]">
              <div className="mx-auto max-w-6xl px-4 pb-28 pt-24 md:px-6 md:pb-36 md:pt-32">
                <div className="grid grid-cols-1 items-end gap-10 lg:grid-cols-12">
                  <h2 className="gsap-reveal font-display max-w-[14ch] text-4xl font-bold leading-[1.0] tracking-[-0.03em] text-white sm:text-5xl lg:col-span-7 lg:text-6xl">
                    Put your first PDF in and ask it something
                  </h2>
                  <div className="gsap-reveal lg:col-span-4 lg:col-start-9">
                    <p className="max-w-[40ch] leading-relaxed text-[#ABD2FA]">
                      Free to start. No card needed to upload a document and see whether the answers hold up.
                    </p>
                    <MagneticButton>
                      <button
                        type="button"
                        onClick={goToAuth}
                        className="mt-7 inline-flex items-center gap-2 rounded-full bg-white px-7 py-3.5 text-sm font-semibold text-[#091540] transition-all duration-200 hover:bg-[#ABD2FA] active:scale-[0.98]"
                      >
                        Start free
                        <ArrowRight className="h-4 w-4" aria-hidden="true" />
                      </button>
                    </MagneticButton>
                  </div>
                </div>
              </div>
            </section>

          </main>

          {/* ── Footer ── */}
          <footer className="border-t border-[rgba(9,21,64,0.1)] bg-[#FAFAF8]">
            <div className="mx-auto max-w-6xl px-4 py-12 md:px-6">
              <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
                <div className="col-span-2 md:col-span-1">
                  <div className="mb-3 flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-md bg-[#1B2CC1]">
                      <img src="/logo.png" alt="" width={16} height={16} className="h-4 w-4 object-contain brightness-0 invert" />
                    </div>
                    <span className="font-display text-base font-bold text-[#091540]">LearnByGenie</span>
                  </div>
                  <p className="max-w-[30ch] text-sm leading-relaxed text-[#6B7280]">
                    Study and teaching tools that work from the material you already have.
                  </p>
                </div>

                <nav aria-label="Features">
                  <h2 className="mb-3 text-sm font-semibold text-[#091540]">Features</h2>
                  <ul className="space-y-2 text-sm text-[#6B7280]">
                    <li><Link to="/pdf-chat-ai" className="transition-colors hover:text-[#1B2CC1]">Chat with PDF</Link></li>
                    <li><Link to="/mcq-generator" className="transition-colors hover:text-[#1B2CC1]">MCQ generator</Link></li>
                    <li><Link to="/doubt-solver" className="transition-colors hover:text-[#1B2CC1]">Doubt solver</Link></li>
                    <li><Link to="/exam-preparation-ai" className="transition-colors hover:text-[#1B2CC1]">Exam prep AI</Link></li>
                  </ul>
                </nav>

                <nav aria-label="Resources">
                  <h2 className="mb-3 text-sm font-semibold text-[#091540]">Resources</h2>
                  <ul className="space-y-2 text-sm text-[#6B7280]">
                    <li><Link to="/ai-tutor-for-students" className="transition-colors hover:text-[#1B2CC1]">AI tutor for students</Link></li>
                    <li><Link to="/blog" className="transition-colors hover:text-[#1B2CC1]">Blog</Link></li>
                    <li><Link to="/pricing" className="transition-colors hover:text-[#1B2CC1]">Pricing</Link></li>
                    <li><Link to="/support" className="transition-colors hover:text-[#1B2CC1]">Support</Link></li>
                  </ul>
                </nav>

                <nav aria-label="Legal">
                  <h2 className="mb-3 text-sm font-semibold text-[#091540]">Legal</h2>
                  <ul className="space-y-2 text-sm text-[#6B7280]">
                    <li><Link to="/privacy-policy" className="transition-colors hover:text-[#1B2CC1]">Privacy policy</Link></li>
                    <li><Link to="/terms-of-service" className="transition-colors hover:text-[#1B2CC1]">Terms of service</Link></li>
                    <li><Link to="/cookie-policy" className="transition-colors hover:text-[#1B2CC1]">Cookie policy</Link></li>
                  </ul>
                </nav>
              </div>

              <div className="mt-10 border-t border-[rgba(9,21,64,0.08)] pt-6">
                <p className="text-sm text-[#9CA3AF]">
                  © {new Date().getFullYear()} LearnByGenie
                </p>
              </div>
            </div>
          </footer>

        </div>{/* /lp-smooth-content */}
      </div>{/* /lp-smooth-wrapper */}
    </div>
  );
};

export default LandingPage;
