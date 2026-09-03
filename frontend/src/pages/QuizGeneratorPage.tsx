import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  HelpCircle, Globe, FileText, Loader2, ArrowRight, X, AlertTriangle,
  RotateCcw, Presentation,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import AppLayout from '../components/AppLayout';
import HistorySidebar from '../components/HistorySidebar';
import { useSidebarCollapse } from '../hooks/useSidebarCollapse';
import SEO from '../components/SEO';
import { useAuthStore } from '../store/useAuthStore';
import { fetchPdfs, type PDFDocument } from '../lib/api';
import UpgradeModal from '../components/billing/UpgradeModal';
import GreetingHeader from '../components/GreetingHeader';
import { GENIE } from '../lib/assets';
import { generateQuiz, type GenerateQuizRequest } from '../lib/quizApi';

const QUESTION_COUNT_OPTIONS = [5, 10, 15, 20, 25];

const DIFFICULTY_OPTIONS = [
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
];

const LANGUAGE_OPTIONS = [
  { value: 'english', label: 'English' },
  { value: 'hindi', label: 'Hindi' },
  { value: 'hinglish', label: 'Hinglish' },
];

const staggerContainer = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.04
    }
  }
};

const staggerItem = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } }
};

const QuizGeneratorPage: React.FC = () => {
  const { collapsed: historySidebarCollapsed, toggle: toggleHistorySidebar } = useSidebarCollapse('quiz-history');
  const location = useLocation();
  const navigate = useNavigate();
  const presetPdfId = location.state?.presetPdfId;
  const presetConfig = location.state?.presetConfig;

  const [topic, setTopic] = useState(presetConfig?.topic || '');
  const [questionCount, setQuestionCount] = useState<number>(presetConfig?.question_count || 10);
  const [difficulty, setDifficulty] = useState<string>(presetConfig?.difficulty || 'medium');
  const [language, setLanguage] = useState<string>(presetConfig?.language || 'english');
  const [sourceType, setSourceType] = useState<'topic' | 'pdf' | 'stage'>(presetPdfId ? 'pdf' : (presetConfig?.source_type || 'topic'));
  const [selectedPdfId, setSelectedPdfId] = useState<string>(presetPdfId || '');
  const [userPdfs, setUserPdfs] = useState<PDFDocument[]>([]);
  const [loadingPdfs, setLoadingPdfs] = useState<boolean>(false);
  const [enableShuffle, setEnableShuffle] = useState<boolean>(true);
  const [timerEnabled, setTimerEnabled] = useState<boolean>(false);
  const [timerMinutes, setTimerMinutes] = useState<number>(10);
  const [generating, setGenerating] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showUpgradeModal, setShowUpgradeModal] = useState<boolean>(false);
  const [quizHistory, setQuizHistory] = useState<any[]>([]);

  useEffect(() => {
    const initData = async () => {
      const token = useAuthStore.getState().session?.access_token;
      if (!token) return;

      try {
        setLoadingPdfs(true);
        const pdfs = await fetchPdfs();
        const readyPdfs = pdfs.filter(p => p.status === 'ready');
        setUserPdfs(readyPdfs);
        if (readyPdfs.length > 0) {
          setSelectedPdfId(readyPdfs[0].id);
        }
      } catch (e) {
        console.error('Failed to load user PDFs', e);
      } finally {
        setLoadingPdfs(false);
      }

      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/quiz/quizzes`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setQuizHistory(data.quizzes || []);
        }
      } catch (e) {
        console.error('Failed to fetch quiz history', e);
      }
    };
    initData();
  }, [selectedPdfId]);

  const handleGenerate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if ((!topic.trim() && sourceType === 'topic') || generating) return;

    setGenerating(true);
    setErrorMessage(null);

    const payload: GenerateQuizRequest = {
      mode: 'student', // student generation
      source_type: sourceType,
      source_ids: sourceType === 'pdf' ? [selectedPdfId] : [],
      topic: topic.trim() || undefined,
      config: {
        question_count: questionCount,
        difficulty,
        types: ['mcq'],
        language,
        shuffle_questions: enableShuffle,
        shuffle_options: enableShuffle,
        timer_seconds: timerEnabled ? timerMinutes * 60 : undefined,
        adaptive: false,
      },
    };

    if (presetConfig?.stage_id) {
        payload.stage_id = presetConfig.stage_id;
    }
    if (presetConfig?.roadmap_id) {
        payload.roadmap_id = presetConfig.roadmap_id;
    }

    try {
      const data = await generateQuiz(payload);
      const quizId = data.quiz?.id || data.id;
      if (quizId) {
        navigate(`/quiz/${quizId}`);
      } else {
        throw new Error('No quiz returned');
      }
    } catch (err: any) {
      console.error('[QuizGeneratorPage] Generation error:', err);
      setErrorMessage(err.response?.data?.detail || err.message || 'An unexpected error occurred during generation.');
    } finally {
      setGenerating(false);
    }
  };

  const selectedClass = (isSelected: boolean) =>
    isSelected
      ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)] text-[var(--accent-green-text)]'
      : 'border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)]';

  return (
    <AppLayout title="Quiz Generator">
      <SEO
        title="AI Quiz Generator | TeachGenie"
        description="Generate structured quizzes with explanations from your documents or any topic."
      />

      <div className="flex h-full w-full">
        <HistorySidebar
          title="Quizzes"
          items={quizHistory.map(q => ({ id: q.id, title: q.topic, date: q.created_at }))}
          selectedId={null}
          onSelect={(id) => navigate(`/quiz/${id}`)}
          onNew={() => setTopic('')}
          collapsed={historySidebarCollapsed}
          onToggle={toggleHistorySidebar}
        />
        
        <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-4xl">
        <motion.div variants={staggerContainer} initial="hidden" animate="show">
          <motion.div variants={staggerItem} className="mb-8">
            <GreetingHeader
              subtitle="Configure your topic, difficulty, and format to generate a comprehensive quiz."
              avatarImageSrc={GENIE.thinking}
            />
          </motion.div>

          <form onSubmit={handleGenerate} className="space-y-8">
            <motion.div variants={staggerItem}>
              <label htmlFor="quiz-topic" className="mb-2 block text-sm font-semibold text-[var(--text-primary)]">
                Quiz topic
              </label>
              <div className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-2 focus-within:border-[var(--accent-green)]">
                <input
                  id="quiz-topic"
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. Distributed Systems architecture"
                  disabled={generating}
                  className="min-w-0 flex-1 border-none bg-transparent px-3 py-2.5 text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none"
                />
                {topic && !generating && (
                  <button
                    type="button"
                    onClick={() => setTopic('')}
                    aria-label="Clear topic"
                    className="rounded-lg p-2 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                  >
                    <X className="h-4 w-4" aria-hidden="true" />
                  </button>
                )}
                <button
                  type="submit"
                  disabled={generating || (!topic.trim() && sourceType === 'topic')}
                  aria-label="Generate quiz"
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-green)] text-white transition-colors hover:bg-[var(--accent-green-hover)] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {generating ? (
                    <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
                  ) : (
                    <ArrowRight className="h-5 w-5" aria-hidden="true" />
                  )}
                </button>
              </div>
            </motion.div>

            <motion.fieldset variants={staggerItem}>
              <legend className="mb-2 text-sm font-semibold text-[var(--text-primary)]">
                Knowledge source
              </legend>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {[
                  { type: 'topic' as const, label: 'General knowledge', icon: Globe, desc: 'Model subject knowledge' },
                  { type: 'pdf' as const, label: 'My uploaded notes', icon: FileText, desc: 'Grounded in your documents' },
                ].map((src) => {
                  const isSelected = sourceType === src.type;
                  return (
                    <button
                      key={src.type}
                      type="button"
                      onClick={() => setSourceType(src.type)}
                      aria-pressed={isSelected}
                      className={`flex flex-col rounded-xl border p-4 text-left transition-colors ${selectedClass(isSelected)}`}
                    >
                      <span className="mb-2 flex items-center gap-2.5">
                        <src.icon
                          className={`h-5 w-5 shrink-0 ${isSelected ? 'text-[var(--accent-green-text)]' : 'text-[var(--text-secondary)]'}`}
                          aria-hidden="true"
                        />
                        <span className="text-sm font-semibold text-[var(--text-primary)]">{src.label}</span>
                      </span>
                      <span className="text-xs text-[var(--text-secondary)]">{src.desc}</span>
                    </button>
                  );
                })}
              </div>

              {sourceType === 'pdf' && (
                <div className="mt-3 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
                  <label htmlFor="quiz-source" className="mb-2 block text-sm font-semibold text-[var(--text-primary)]">
                    Source document
                  </label>
                  {userPdfs.length > 0 ? (
                    <select
                      id="quiz-source"
                      value={selectedPdfId}
                      onChange={(e) => setSelectedPdfId(e.target.value)}
                      className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2.5 text-sm font-medium text-[var(--text-primary)] focus:border-[var(--accent-green)] focus:outline-none"
                    >
                      {userPdfs.map((pdf) => (
                        <option key={pdf.id} value={pdf.id}>
                          {pdf.name} ({pdf.subject || 'General'}), {pdf.page_count || 1} pages
                        </option>
                      ))}
                    </select>
                  ) : (
                    <p className="text-sm text-[var(--text-secondary)]">
                      No uploaded documents found. Upload one in your Library, or continue with
                      general knowledge.
                    </p>
                  )}
                </div>
              )}
            </motion.fieldset>

            <motion.fieldset variants={staggerItem}>
              <legend className="mb-2 text-sm font-semibold text-[var(--text-primary)]">
                Question count
              </legend>
              <div className="flex flex-wrap gap-2">
                {QUESTION_COUNT_OPTIONS.map((num) => {
                  const isSelected = questionCount === num;
                  return (
                    <button
                      key={num}
                      type="button"
                      onClick={() => setQuestionCount(num)}
                      aria-pressed={isSelected}
                      className={`rounded-lg border px-4 py-2 text-sm font-semibold tabular-nums transition-colors ${
                        isSelected
                          ? 'border-[var(--accent-green)] bg-[var(--accent-green)] text-white'
                          : 'border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)]'
                      }`}
                    >
                      {num}
                    </button>
                  );
                })}
              </div>
            </motion.fieldset>

            <motion.div variants={staggerItem} className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div>
                <label htmlFor="quiz-difficulty" className="mb-1.5 block text-sm font-semibold text-[var(--text-primary)]">
                  Difficulty
                </label>
                <select
                  id="quiz-difficulty"
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2.5 text-sm font-medium text-[var(--text-primary)] focus:border-[var(--accent-green)] focus:outline-none"
                >
                  {DIFFICULTY_OPTIONS.map((d) => (
                    <option key={d.value} value={d.value}>{d.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="quiz-language" className="mb-1.5 block text-sm font-semibold text-[var(--text-primary)]">
                  Language
                </label>
                <select
                  id="quiz-language"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2.5 text-sm font-medium text-[var(--text-primary)] focus:border-[var(--accent-green)] focus:outline-none"
                >
                  {LANGUAGE_OPTIONS.map((l) => (
                    <option key={l.value} value={l.value}>{l.label}</option>
                  ))}
                </select>
              </div>
            </motion.div>

            <motion.fieldset variants={staggerItem} className="border-t border-[var(--border)] pt-6">
              <legend className="sr-only">Quiz features</legend>
              <div className="flex flex-wrap gap-2">
                {[
                  { label: 'Shuffle questions & options', state: enableShuffle, set: setEnableShuffle },
                ].map((opt, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => opt.set(!opt.state)}
                    aria-pressed={opt.state}
                    className={`flex items-center gap-2.5 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                      opt.state
                        ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)] text-[var(--accent-green-text)]'
                        : 'border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'
                    }`}
                  >
                    <span>{opt.label}</span>
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                      opt.state
                        ? 'bg-[var(--accent-green)] text-white'
                        : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)]'
                    }`}>
                      {opt.state ? 'On' : 'Off'}
                    </span>
                  </button>
                ))}
              </div>
            </motion.fieldset>
            
            <motion.div variants={staggerItem} className="flex items-center gap-4 border-t border-[var(--border)] pt-6">
              <label className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
                <input
                  type="checkbox"
                  checked={timerEnabled}
                  onChange={(e) => setTimerEnabled(e.target.checked)}
                  className="rounded text-[var(--accent-green)] focus:ring-[var(--accent-green)]"
                />
                Enable Timer
              </label>
              {timerEnabled && (
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="1"
                    max="180"
                    value={timerMinutes}
                    onChange={(e) => setTimerMinutes(parseInt(e.target.value))}
                    className="w-20 rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-1.5 text-sm font-medium text-[var(--text-primary)] focus:border-[var(--accent-green)] focus:outline-none"
                  />
                  <span className="text-sm text-[var(--text-secondary)]">minutes</span>
                </div>
              )}
            </motion.div>

            <motion.div variants={staggerItem}>
              <button
                type="submit"
                disabled={generating || (!topic.trim() && sourceType === 'topic')}
                className="flex w-full items-center justify-center gap-2.5 rounded-full bg-[var(--accent-royal)] px-8 py-3.5 text-sm font-bold text-white shadow-md shadow-[var(--accent-royal)]/25 transition-all hover:bg-[var(--accent-green-deep)] active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50"
              >
                {generating ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
                    <span>Generating Quiz...</span>
                  </>
                ) : (
                  <>
                    <HelpCircle className="h-5 w-5" aria-hidden="true" />
                    <span>Generate Quiz</span>
                  </>
                )}
              </button>
            </motion.div>
          </form>

          <AnimatePresence>
            {errorMessage && !generating && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                role="alert"
                className="mt-8 rounded-xl border border-red-200 bg-red-50 p-6"
              >
                <div className="flex items-start gap-3">
                  <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-700" aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <h2 className="font-display text-base font-semibold text-red-900">
                      Quiz generation failed
                    </h2>
                    <p className="mt-1 text-sm text-red-800">{errorMessage}</p>
                    <button
                      type="button"
                      onClick={() => handleGenerate()}
                      className="mt-4 inline-flex items-center gap-2 rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-800"
                    >
                      <RotateCcw className="h-4 w-4" aria-hidden="true" />
                      Try again
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          </motion.div>
          </div>
        </div>
      </div>
      <UpgradeModal
        isOpen={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
        message="Upgrade to generate unlimited quizzes from documents."
      />
    </AppLayout>
  );
};

export default QuizGeneratorPage;
