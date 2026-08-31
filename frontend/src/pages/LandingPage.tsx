import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import {
  Upload, MessageSquare, FileSearch, Languages, FileText, PenLine,
  ArrowRight, ShieldCheck, ListChecks, Presentation, Map, Video, Plus, Minus,
} from 'lucide-react';
import SEO from '../components/SEO';

/**
 * Landing page.
 *
 * Design constraints applied here (design-taste-frontend):
 *  - One accent (green) across the whole page. No indigo/purple/rose/amber/cyan.
 *  - Zero em-dashes, zero emoji, zero gradient text.
 *  - No three-equal-card feature rows; six distinct layout families.
 *  - No product screenshots are available, so no fake screenshot divs and no
 *    stock photography. Depth comes from type scale, tinted surfaces, column
 *    offsets and a full-bleed brand band instead.
 */

const EASE = [0.16, 1, 0.3, 1] as const;

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const reduce = useReducedMotion();
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  /** Entry animation, disabled wholesale under prefers-reduced-motion. */
  const reveal = (i = 0) => ({
    initial: reduce ? false : { opacity: 0, y: 20 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, amount: 0.25 },
    transition: { duration: 0.55, delay: reduce ? 0 : i * 0.07, ease: EASE },
  });

  const goToAuth = () => navigate('/auth');

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

  /* FAQ copy is byte-identical to the FAQPage schema above. Changing one
     without the other breaks the rich result, so they stay in sync. */
  const faqs = [
    {
      q: 'What is TeachGenie?',
      a: 'TeachGenie is an AI study assistant for students. It acts as your personal AI tutor that can read your uploaded PDF notes and answer your doubts based on them.',
    },
    {
      q: 'Can AI explain PDF notes?',
      a: 'Yes, TeachGenie can read any PDF notes, textbooks, or coaching materials and explain complex topics from them in simple language.',
    },
    {
      q: 'Can TeachGenie generate MCQs?',
      a: 'Yes, TeachGenie can automatically generate multiple-choice questions (MCQs) from your uploaded PDFs to help you practice for exams.',
    },
    {
      q: 'Is TeachGenie useful for CBSE students?',
      a: 'Absolutely. CBSE students can upload NCERT PDFs or school notes and ask questions to prepare effectively for their board exams.',
    },
    {
      q: 'Can students use AI for exam preparation?',
      a: 'Yes, AI is highly effective for exam preparation. It helps by summarizing notes, predicting exam questions, and solving doubts 24/7.',
    },
  ];

  const steps = [
    {
      icon: Upload,
      title: 'Upload',
      desc: 'Add a PDF textbook, a coaching module or a photo of your handwritten notes.',
    },
    {
      icon: MessageSquare,
      title: 'Ask',
      desc: 'Type the doubt the way you would say it out loud, in English, Hindi or Hinglish.',
    },
    {
      icon: FileSearch,
      title: 'Check the citation',
      desc: 'Every answer carries the page it came from, so you can open the book and confirm it.',
    },
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

  return (
    <div className="min-h-[100dvh] bg-[var(--bg-primary)]">
      <SEO
        title="TeachGenie - AI Tutor for Students | Chat With PDFs, Notes & MCQs"
        description="TeachGenie is an AI study assistant for students. Upload PDF notes, ask doubts, get simple explanations, generate MCQs, predicted exam questions and prepare smarter with your AI tutor."
        schema={homepageSchema}
      />

      <a href="#main" className="skip-link">Skip to content</a>

      {/* ── Nav ── */}
      <header className="sticky top-0 z-40 border-b border-[var(--border)] bg-[var(--bg-primary)]/90 backdrop-blur-md">
        <nav
          aria-label="Primary"
          className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 md:px-6"
        >
          <Link to="/" className="flex shrink-0 items-center gap-2 rounded-lg" aria-label="TeachGenie home">
            <img src="/logo.png" alt="" width={36} height={36} className="h-9 w-9 object-contain" />
            <span className="font-display text-lg font-bold tracking-tight text-[var(--text-primary)]">
              TeachGenie
            </span>
          </Link>

          <div className="flex items-center gap-1 sm:gap-2">
            <Link
              to="/pricing"
              className="rounded-lg px-3 py-2 text-sm font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            >
              Pricing
            </Link>
            <button
              type="button"
              onClick={goToAuth}
              className="rounded-lg px-3 py-2 text-sm font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            >
              Log in
            </button>
            <button
              type="button"
              onClick={goToAuth}
              className="rounded-lg bg-[var(--accent-green)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)] active:translate-y-px"
            >
              Start free
            </button>
          </div>
        </nav>
      </header>

      <main id="main">
        {/* ── Hero: left-aligned, asymmetric. No centered stack, no gradient text. ── */}
        <section className="relative overflow-hidden border-b border-[var(--border)]">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -top-40 right-[-10%] h-[520px] w-[520px] rounded-full bg-[var(--accent-green)] opacity-[0.06] blur-3xl"
          />
          <div className="relative mx-auto grid max-w-6xl grid-cols-1 gap-10 px-4 pb-16 pt-14 md:px-6 md:pb-24 md:pt-20 lg:grid-cols-12 lg:gap-8">
            <div className="lg:col-span-8">
              <motion.p
                {...reveal(0)}
                className="mb-5 inline-flex items-center gap-2 rounded-full bg-[var(--accent-green-light)] px-3 py-1 text-xs font-semibold text-[var(--accent-green-text)]"
              >
                <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
                Answers you can check against the page
              </motion.p>

              <motion.h1
                {...reveal(1)}
                className="font-display text-4xl font-bold leading-[1.08] tracking-tight text-[var(--text-primary)] sm:text-5xl lg:text-6xl"
                style={{ textWrap: 'balance' } as React.CSSProperties}
              >
                Study from your own notes.
                <br className="hidden sm:block" />
                <span className="text-[var(--accent-green-text)]"> Teach from them too.</span>
              </motion.h1>

              <motion.p
                {...reveal(2)}
                className="mt-5 max-w-[52ch] text-base leading-relaxed text-[var(--text-secondary)] sm:text-lg"
              >
                Upload your material once. Students get cited answers and practice questions.
                Teachers get lesson plans, slide decks and video lessons.
              </motion.p>

              <motion.div {...reveal(3)} className="mt-8 flex flex-col gap-3 sm:flex-row">
                <button
                  type="button"
                  onClick={goToAuth}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-[var(--accent-green)] px-6 py-3 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--accent-green-hover)] active:translate-y-px"
                >
                  Start free
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </button>
                <a
                  href="#how-it-works"
                  className="inline-flex items-center justify-center rounded-xl border border-[var(--border-strong)] px-6 py-3 text-sm font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)]"
                >
                  See how it works
                </a>
              </motion.div>
            </div>

            {/* Right column carries the language range, which is real product
                configuration (english / hindi / hinglish), not decoration. */}
            <motion.aside
              {...reveal(4)}
              className="self-end rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 lg:col-span-4"
            >
              <p className="font-display text-sm font-semibold text-[var(--text-primary)]">
                Works in the language you think in
              </p>
              <ul className="mt-4 space-y-2.5">
                {['English', 'Hindi', 'Hinglish'].map((lang) => (
                  <li key={lang} className="flex items-center gap-2.5 text-sm text-[var(--text-secondary)]">
                    <Languages className="h-4 w-4 shrink-0 text-[var(--accent-green-text)]" aria-hidden="true" />
                    {lang}
                  </li>
                ))}
              </ul>
              <p className="mt-5 border-t border-[var(--border)] pt-4 text-sm leading-relaxed text-[var(--text-secondary)]">
                Ask in Hinglish, get the explanation back the same way.
              </p>
            </motion.aside>
          </div>
        </section>

        {/* ── How it works: stepped band, not three equal cards ── */}
        <section id="how-it-works" className="mx-auto max-w-6xl px-4 py-16 md:px-6 md:py-24">
          <motion.h2
            {...reveal(0)}
            className="font-display max-w-[20ch] text-3xl font-bold tracking-tight text-[var(--text-primary)] sm:text-4xl"
          >
            Three steps, then you can verify it yourself
          </motion.h2>

          <div className="relative mt-12">
            <div
              aria-hidden="true"
              className="absolute left-0 right-0 top-6 hidden h-px bg-[var(--border)] md:block"
            />
            <ol className="grid grid-cols-1 gap-10 md:grid-cols-3 md:gap-8">
              {steps.map((step, i) => (
                <motion.li key={step.title} {...reveal(i)} className="relative">
                  <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--bg-card)]">
                    <step.icon className="h-5 w-5 text-[var(--accent-green-text)]" aria-hidden="true" />
                  </div>
                  <h3 className="font-display text-lg font-semibold text-[var(--text-primary)]">
                    {step.title}
                  </h3>
                  <p className="mt-2 max-w-[38ch] text-sm leading-relaxed text-[var(--text-secondary)]">
                    {step.desc}
                  </p>
                </motion.li>
              ))}
            </ol>
          </div>
        </section>

        {/* ── Two audiences: the structural fix for teacher invisibility ── */}
        <section className="border-y border-[var(--border)] bg-[var(--bg-secondary)]">
          <div className="mx-auto max-w-6xl px-4 py-16 md:px-6 md:py-24">
            <motion.h2
              {...reveal(0)}
              className="font-display max-w-[24ch] text-3xl font-bold tracking-tight text-[var(--text-primary)] sm:text-4xl"
            >
              Two jobs, one set of material
            </motion.h2>

            <div className="mt-12 grid grid-cols-1 gap-6 lg:grid-cols-2">
              <motion.div
                {...reveal(1)}
                className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-7 md:p-8"
              >
                <div className="mb-6 flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--accent-green-light)]">
                    <ListChecks className="h-5 w-5 text-[var(--accent-green-text)]" aria-hidden="true" />
                  </span>
                  <h3 className="font-display text-xl font-semibold text-[var(--text-primary)]">
                    If you are studying
                  </h3>
                </div>
                <ul className="space-y-4">
                  {studentPoints.map((point) => (
                    <li key={point} className="flex gap-3 text-sm leading-relaxed text-[var(--text-secondary)]">
                      <span
                        aria-hidden="true"
                        className="mt-2 h-1 w-4 shrink-0 rounded-full bg-[var(--accent-green)]"
                      />
                      {point}
                    </li>
                  ))}
                </ul>
              </motion.div>

              <motion.div
                {...reveal(2)}
                className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-7 md:p-8"
              >
                <div className="mb-6 flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--accent-green-light)]">
                    <Map className="h-5 w-5 text-[var(--accent-green-text)]" aria-hidden="true" />
                  </span>
                  <h3 className="font-display text-xl font-semibold text-[var(--text-primary)]">
                    If you are teaching
                  </h3>
                </div>
                <ul className="space-y-4">
                  {teacherPoints.map((point) => (
                    <li key={point} className="flex gap-3 text-sm leading-relaxed text-[var(--text-secondary)]">
                      <span
                        aria-hidden="true"
                        className="mt-2 h-1 w-4 shrink-0 rounded-full bg-[var(--accent-green)]"
                      />
                      {point}
                    </li>
                  ))}
                </ul>

                <div className="mt-7 flex flex-wrap gap-2 border-t border-[var(--border)] pt-6">
                  {[
                    { icon: Map, label: 'Lesson planner' },
                    { icon: Presentation, label: 'Slide decks' },
                    { icon: Video, label: 'Video lessons' },
                  ].map((tool) => (
                    <span
                      key={tool.label}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--bg-secondary)] px-2.5 py-1.5 text-xs font-medium text-[var(--text-secondary)]"
                    >
                      <tool.icon className="h-3.5 w-3.5" aria-hidden="true" />
                      {tool.label}
                    </span>
                  ))}
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* ── Bento: exactly 5 cells for 5 items, dense flow, tinted variation ── */}
        <section className="mx-auto max-w-6xl px-4 pb-20 pt-24 md:px-6 md:pb-24 md:pt-32">
          <motion.h2
            {...reveal(0)}
            className="font-display ml-auto max-w-[20ch] text-3xl font-bold leading-tight tracking-tight text-[var(--text-primary)] sm:text-4xl lg:text-right"
          >
            What the answer actually gives you
          </motion.h2>

          <div className="mt-14 grid auto-rows-auto grid-flow-dense grid-cols-1 gap-4 md:grid-cols-6">
            <motion.article
              {...reveal(0)}
              className="flex flex-col justify-end rounded-2xl bg-[var(--accent-green-deep)] p-8 md:col-span-4 md:row-span-2 md:p-12"
            >
              <FileText className="mb-6 h-7 w-7 text-[var(--accent-green-light)]" aria-hidden="true" />
              <h3 className="font-display text-3xl font-bold leading-[1.1] tracking-tight text-white md:text-4xl">
                The page number comes with the answer
              </h3>
              <p className="mt-4 max-w-[44ch] leading-relaxed text-[var(--accent-green-light)]">
                Responses are drawn from the document you uploaded and point back to where they
                came from, so a wrong answer is something you can catch rather than something you
                have to trust.
              </p>
            </motion.article>

            <motion.article
              {...reveal(1)}
              className="rounded-2xl border border-[var(--border)] bg-[var(--accent-green-light)] p-7 md:col-span-2"
            >
              <PenLine className="mb-4 h-5 w-5 text-[var(--accent-green-text)]" aria-hidden="true" />
              <h3 className="font-display text-lg font-semibold text-[var(--text-primary)]">
                Handwritten notes work
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                Photograph a page of your own writing and ask questions against it.
              </p>
            </motion.article>

            <motion.article
              {...reveal(2)}
              className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-7 md:col-span-2"
            >
              <ListChecks className="mb-4 h-5 w-5 text-[var(--accent-green-text)]" aria-hidden="true" />
              <h3 className="font-display text-lg font-semibold text-[var(--text-primary)]">
                Practice questions
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                Multiple choice sets built from your material, not from a generic question bank.
              </p>
            </motion.article>

            <motion.article
              {...reveal(3)}
              className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-7 md:col-span-3"
            >
              <Presentation className="mb-4 h-5 w-5 text-[var(--accent-green-text)]" aria-hidden="true" />
              <h3 className="font-display text-lg font-semibold text-[var(--text-primary)]">
                Decks with speaker notes
              </h3>
              <p className="mt-2 max-w-[42ch] text-sm leading-relaxed text-[var(--text-secondary)]">
                Ten to fifteen slides, six themes, downloadable as a PPTX you can edit.
              </p>
            </motion.article>

            <motion.article
              {...reveal(4)}
              className="relative overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--bg-secondary)] p-7 md:col-span-3"
            >
              <div
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 opacity-[0.5]"
                style={{
                  backgroundImage:
                    'radial-gradient(var(--border-strong) 1px, transparent 1px)',
                  backgroundSize: '14px 14px',
                }}
              />
              <div className="relative">
                <Map className="mb-4 h-5 w-5 text-[var(--accent-green-text)]" aria-hidden="true" />
                <h3 className="font-display text-lg font-semibold text-[var(--text-primary)]">
                  Plans that sequence themselves
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                  Stages ordered by prerequisite, each with its own timing and checkpoint.
                </p>
              </div>
            </motion.article>
          </div>
        </section>

        {/* ── FAQ: disclosure list, hairline dividers, no card boxes ── */}
        <section className="border-t border-[var(--border)] bg-[var(--bg-secondary)]">
          <div className="mx-auto max-w-6xl px-4 pb-24 pt-20 md:px-6 md:pb-28 md:pt-24">
            <div className="grid grid-cols-1 gap-y-10 lg:grid-cols-12 lg:gap-x-16">
            <div className="lg:col-span-4">
            <motion.h2
              {...reveal(0)}
              className="font-display text-2xl font-bold leading-tight tracking-tight text-[var(--text-primary)] sm:text-3xl lg:sticky lg:top-28"
            >
              Questions people ask first
            </motion.h2>
            </div>

            <div className="divide-y divide-[var(--border)] border-t border-[var(--border)] lg:col-span-8">
              {faqs.map((faq, i) => {
                const isOpen = openFaq === i;
                return (
                  <div key={faq.q}>
                    <h3>
                      <button
                        type="button"
                        onClick={() => setOpenFaq(isOpen ? null : i)}
                        aria-expanded={isOpen}
                        aria-controls={`faq-answer-${i}`}
                        id={`faq-question-${i}`}
                        className="flex w-full items-center justify-between gap-6 py-5 text-left transition-colors hover:text-[var(--accent-green-text)]"
                      >
                        <span className="font-display text-base font-semibold text-[var(--text-primary)] sm:text-lg">
                          {faq.q}
                        </span>
                        {isOpen ? (
                          <Minus className="h-4 w-4 shrink-0 text-[var(--text-secondary)]" aria-hidden="true" />
                        ) : (
                          <Plus className="h-4 w-4 shrink-0 text-[var(--text-secondary)]" aria-hidden="true" />
                        )}
                      </button>
                    </h3>
                    <div
                      id={`faq-answer-${i}`}
                      role="region"
                      aria-labelledby={`faq-question-${i}`}
                      hidden={!isOpen}
                    >
                      <p className="max-w-[62ch] pb-6 text-sm leading-relaxed text-[var(--text-secondary)]">
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

        {/* ── Closing CTA ── */}
        {/* Full bleed: breaks the max-width container the rest of the page
            sits inside, and sets the headline against the copy rather than
            centring both. */}
        <section className="bg-[var(--accent-green-deep)]">
          <div className="mx-auto max-w-6xl px-4 pb-28 pt-24 md:px-6 md:pb-36 md:pt-32">
            <motion.div {...reveal(0)} className="grid grid-cols-1 items-end gap-10 lg:grid-cols-12">
              <h2 className="font-display max-w-[14ch] text-4xl font-bold leading-[1.0] tracking-[-0.03em] text-white sm:text-5xl lg:col-span-7 lg:text-6xl">
                Put your first PDF in and ask it something
              </h2>
              <div className="lg:col-span-4 lg:col-start-9">
                <p className="max-w-[40ch] leading-relaxed text-[var(--accent-green-light)]">
                  Free to start. No card needed to upload a document and see whether the answers
                  hold up.
                </p>
                <button
                  type="button"
                  onClick={goToAuth}
                  className="mt-7 inline-flex items-center gap-2 rounded-xl bg-white px-7 py-3.5 text-sm font-semibold text-[var(--accent-green-deep)] transition-colors hover:bg-[var(--accent-green-light)] active:translate-y-px"
                >
                  Start free
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
            </motion.div>
          </div>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-[var(--border)] bg-[var(--bg-secondary)]">
        <div className="mx-auto max-w-6xl px-4 py-12 md:px-6">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            <div className="col-span-2 md:col-span-1">
              <div className="mb-3 flex items-center gap-2">
                <img src="/logo.png" alt="" width={32} height={32} className="h-8 w-8 object-contain" />
                <span className="font-display text-base font-bold text-[var(--text-primary)]">
                  TeachGenie
                </span>
              </div>
              <p className="max-w-[30ch] text-sm leading-relaxed text-[var(--text-secondary)]">
                Study and teaching tools that work from the material you already have.
              </p>
            </div>

            <nav aria-label="Features">
              <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Features</h2>
              <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
                <li><Link to="/pdf-chat-ai" className="transition-colors hover:text-[var(--accent-green-text)]">Chat with PDF</Link></li>
                <li><Link to="/mcq-generator" className="transition-colors hover:text-[var(--accent-green-text)]">MCQ generator</Link></li>
                <li><Link to="/doubt-solver" className="transition-colors hover:text-[var(--accent-green-text)]">Doubt solver</Link></li>
                <li><Link to="/exam-preparation-ai" className="transition-colors hover:text-[var(--accent-green-text)]">Exam prep AI</Link></li>
              </ul>
            </nav>

            <nav aria-label="Resources">
              <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Resources</h2>
              <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
                <li><Link to="/ai-tutor-for-students" className="transition-colors hover:text-[var(--accent-green-text)]">AI tutor for students</Link></li>
                <li><Link to="/blog" className="transition-colors hover:text-[var(--accent-green-text)]">Blog</Link></li>
                <li><Link to="/pricing" className="transition-colors hover:text-[var(--accent-green-text)]">Pricing</Link></li>
                <li><Link to="/support" className="transition-colors hover:text-[var(--accent-green-text)]">Support</Link></li>
              </ul>
            </nav>

            <nav aria-label="Legal">
              <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Legal</h2>
              <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
                <li><Link to="/privacy-policy" className="transition-colors hover:text-[var(--accent-green-text)]">Privacy policy</Link></li>
                <li><Link to="/terms-of-service" className="transition-colors hover:text-[var(--accent-green-text)]">Terms of service</Link></li>
                <li><Link to="/cookie-policy" className="transition-colors hover:text-[var(--accent-green-text)]">Cookie policy</Link></li>
              </ul>
            </nav>
          </div>

          <div className="mt-10 border-t border-[var(--border)] pt-6">
            <p className="text-sm text-[var(--text-muted)]">
              © {new Date().getFullYear()} TeachGenie
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
