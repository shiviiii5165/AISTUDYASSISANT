import React, { useState, useEffect } from 'react';
import {
  Clock, FileText, Globe, Sparkles, CheckCircle2, Download, Loader2,
  AlertTriangle, Palette, Settings2, RotateCcw, BookOpen, Presentation,
  Trash2, ArrowRight, GraduationCap, PenTool, LayoutGrid, Newspaper, Brain, X,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { useAuthStore } from '../store/useAuthStore';
import { fetchPdfs, type PDFDocument } from '../lib/api';
import UpgradeModal from '../components/billing/UpgradeModal';
import GreetingHeader from '../components/GreetingHeader';

// ═══════════════════════════════════════════════════════════════════════════
// CONFIGURATION OPTIONS
// ═══════════════════════════════════════════════════════════════════════════

const SLIDE_COUNT_OPTIONS = [10, 11, 12, 13, 14, 15];

/** `value` strings are unchanged; the emoji icons became library glyphs. */
const DESIGN_OPTIONS = [
  { value: 'academic', label: 'Academic Clean', icon: GraduationCap, desc: 'University lecture with structured learning progression' },
  { value: 'minimal', label: 'Modern Minimal', icon: PenTool, desc: 'Spacious layout with focal takeaways' },
  { value: 'technical', label: 'Technical Grid', icon: LayoutGrid, desc: 'Architecture diagrams, pipelines and component grids' },
  { value: 'editorial', label: 'Editorial', icon: Newspaper, desc: 'Magazine and report composition with asymmetric balance' },
  { value: 'visual', label: 'Visual Learning', icon: Brain, desc: 'Diagram-first visual pedagogy with concise micro-text' },
];

const THEME_OPTIONS = [
  { value: 'blue_professional', label: 'Blue Pro', colors: ['#1E40AF', '#3B82F6', '#DBEAFE'] },
  { value: 'indigo_innovation', label: 'Indigo', colors: ['#4F46E5', '#818CF8', '#E0E7FF'] },
  { value: 'emerald_academic', label: 'Emerald', colors: ['#059669', '#10B981', '#D1FAE5'] },
  { value: 'teal_corporate', label: 'Teal', colors: ['#0D9488', '#14B8A6', '#CCFBF1'] },
  { value: 'orange_energy', label: 'Orange', colors: ['#C2410C', '#EA580C', '#FFEDD5'] },
  { value: 'minimal_charcoal', label: 'Charcoal', colors: ['#18181B', '#52525B', '#E4E4E7'] },
];

const AUDIENCE_OPTIONS = [
  { value: 'university', label: 'University / Undergraduate' },
  { value: 'high_school', label: 'High School' },
  { value: 'professional', label: 'Industry Professional' },
  { value: 'beginner', label: 'Beginner / General' },
];

const LANGUAGE_OPTIONS = [
  { value: 'english', label: 'English' },
  { value: 'hindi', label: 'Hindi' },
  { value: 'hinglish', label: 'Hinglish' },
];

const SUGGESTED_TOPICS = [
  'Kubernetes Architecture & Orchestration',
  'Deep Learning Transformers & Attention Mechanisms',
  'Operating System Deadlocks & Memory Management',
  'Database Normalization: 1NF to BCNF',
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

const TopicDeckPage: React.FC = () => {
  const [topic, setTopic] = useState('');

  // Presentation Parameters
  const [slideCount, setSlideCount] = useState<number>(12);
  const [design, setDesign] = useState<string>('academic');
  const [themeId, setThemeId] = useState<string>('blue_professional');
  const [audience, setAudience] = useState<string>('university');
  const [language, setLanguage] = useState<string>('english');
  const [depth] = useState<string>('full');

  // Knowledge Source
  const [sourceType, setSourceType] = useState<'general' | 'uploaded_material' | 'uploaded_material_plus_web'>('general');
  const [selectedPdfId, setSelectedPdfId] = useState<string>('');
  const [userPdfs, setUserPdfs] = useState<PDFDocument[]>([]);
  const [, setLoadingPdfs] = useState<boolean>(false);

  // Feature Options Toggles
  const [enableDiagrams, setEnableDiagrams] = useState<boolean>(true);
  const [enableImages, setEnableImages] = useState<boolean>(true);
  const [enableSpeakerNotes, setEnableSpeakerNotes] = useState<boolean>(true);
  const [enableSources, setEnableSources] = useState<boolean>(true);
  const [enableExamples, setEnableExamples] = useState<boolean>(true);
  const [enableQuiz, setEnableQuiz] = useState<boolean>(false);

  // Generation & Status State
  const [generating, setGenerating] = useState<boolean>(false);
  const [stageMessage, setStageMessage] = useState<string>('');
  const [status, setStatus] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [finalSlideCount, setFinalSlideCount] = useState<number | null>(null);
  const [resultTitle, setResultTitle] = useState<string>('');
  const [resultTakeaways, setResultTakeaways] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showUpgradeModal, setShowUpgradeModal] = useState<boolean>(false);

  // History
  const [deckHistory, setDeckHistory] = useState<any[]>([]);

  // Load User's PDFs and Deck History
  useEffect(() => {
    const initData = async () => {
      const token = useAuthStore.getState().session?.access_token;
      if (!token) return;

      // Load user PDFs
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

      // Load deck history
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/decks/`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setDeckHistory(data || []);
        }
      } catch (e) {
        console.error('Failed to fetch deck history', e);
      }
    };

    initData();
  }, []);

  const handleGenerate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!topic.trim() || generating) return;

    setGenerating(true);
    setDownloadUrl(null);
    setFinalSlideCount(null);
    setErrorMessage(null);
    setStatus('processing');
    setStageMessage('Designing the narrative arc and slide blueprint');

    const token = useAuthStore.getState().session?.access_token;
    const apiUrl = import.meta.env.VITE_API_URL || '';

    const payload = {
      topic: topic.trim(),
      slide_count: slideCount,
      depth,
      audience,
      design,
      theme: themeId,
      source_type: sourceType,
      source_id: sourceType !== 'general' ? selectedPdfId : null,
      options: {
        diagrams: enableDiagrams,
        images: enableImages,
        speaker_notes: enableSpeakerNotes,
        sources: enableSources,
        examples: enableExamples,
        quiz: enableQuiz,
      }
    };

    try {
      /* These timers only rotate the status text. The backend reports no
         progress, so no percentage is shown: the bar is indeterminate. */
      const timer1 = setTimeout(() => {
        setStageMessage('Writing slide content and speaker notes');
      }, 3000);

      const timer2 = setTimeout(() => {
        setStageMessage('Building diagrams and visual assets');
      }, 8000);

      const timer3 = setTimeout(() => {
        setStageMessage('Laying out and checking the slides');
      }, 14000);

      const res = await fetch(`${apiUrl}/api/decks/generate-advanced`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);

      if (!res.ok) {
        if (res.status === 403) {
          setShowUpgradeModal(true);
          setGenerating(false);
          setStatus(null);
          return;
        }
        const errData = await res.json();
        throw new Error(errData.detail || 'Presentation generation failed');
      }

      const data = await res.json();
      if (data.status === 'ready' && data.download_url) {
        setStatus('ready');
        setDownloadUrl(data.download_url);
        setFinalSlideCount(data.slide_count || slideCount);
        setResultTitle(data.deck_title || topic);
        setResultTakeaways(data.key_takeaways || []);
      } else {
        throw new Error('Presentation generated but download URL missing.');
      }
    } catch (err: any) {
      console.error('[TopicDeckPage] Generation error:', err);
      setErrorMessage(err.message || 'An unexpected error occurred during generation.');
      setStatus('failed');
    } finally {
      setGenerating(false);
    }
  };

  const handleDeleteDeck = async (deckId: string) => {
    const token = useAuthStore.getState().session?.access_token;
    if (!token) return;
    try {
      await fetch(`${import.meta.env.VITE_API_URL || ''}/api/decks/${deckId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setDeckHistory(prev => prev.filter(d => d.id !== deckId));
    } catch (e) {
      console.error('Failed to delete deck', e);
    }
  };

  const selectedClass = (isSelected: boolean) =>
    isSelected
      ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)]'
      : 'border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)]';

  return (
    <AppLayout title="PPT Generator">
      <SEO
        title="AI Presentation Studio | TeachGenie"
        description="Generate structured PowerPoint presentations with exact slide counts, diagrams, speaker notes, and grounding in your own documents."
      />

      <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 lg:px-8">
        <motion.div variants={staggerContainer} initial="hidden" animate="show">

          <motion.div variants={staggerItem} className="mb-8">
            <GreetingHeader
              subtitle="Describe a topic and get an editable deck with speaker notes."
              avatarImageSrc="/scholar-genie-chibi.png"
            />
          </motion.div>

          <form onSubmit={handleGenerate} className="space-y-8">

            {/* Topic */}
            <motion.div variants={staggerItem}>
              <label htmlFor="deck-topic" className="mb-2 block text-sm font-semibold text-[var(--text-primary)]">
                Presentation topic
              </label>
              <div className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-2 focus-within:border-[var(--accent-green)]">
                <input
                  id="deck-topic"
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="Kubernetes architecture and orchestration"
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
                  disabled={generating || !topic.trim()}
                  aria-label="Generate presentation"
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-green)] text-white transition-colors hover:bg-[var(--accent-green-hover)] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {generating ? (
                    <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
                  ) : (
                    <ArrowRight className="h-5 w-5" aria-hidden="true" />
                  )}
                </button>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                {SUGGESTED_TOPICS.map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setTopic(t)}
                    className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-1.5 text-xs text-[var(--text-secondary)] transition-colors hover:border-[var(--accent-green)] hover:text-[var(--text-primary)]"
                  >
                    {t}
                  </button>
                ))}
              </div>
            </motion.div>

            {/* Knowledge source */}
            <motion.fieldset variants={staggerItem}>
              <legend className="mb-2 text-sm font-semibold text-[var(--text-primary)]">
                Knowledge source
              </legend>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                {[
                  { type: 'general' as const, label: 'General knowledge', icon: Globe, desc: 'Model subject knowledge' },
                  { type: 'uploaded_material' as const, label: 'My uploaded notes', icon: FileText, desc: 'Grounded in your documents' },
                  { type: 'uploaded_material_plus_web' as const, label: 'Document and web', icon: Sparkles, desc: 'Documents plus research' },
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

              {sourceType !== 'general' && (
                <div className="mt-3 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
                  <label htmlFor="deck-source" className="mb-2 block text-sm font-semibold text-[var(--text-primary)]">
                    Source document
                  </label>
                  {userPdfs.length > 0 ? (
                    <select
                      id="deck-source"
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

            {/* Slide count */}
            <motion.fieldset variants={staggerItem}>
              <legend className="mb-2 text-sm font-semibold text-[var(--text-primary)]">
                Slide count
              </legend>
              <div className="flex flex-wrap gap-2">
                {SLIDE_COUNT_OPTIONS.map((num) => {
                  const isSelected = slideCount === num;
                  return (
                    <button
                      key={num}
                      type="button"
                      onClick={() => setSlideCount(num)}
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

            {/* Design + theme + audience */}
            <motion.div variants={staggerItem} className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <fieldset>
                <legend className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
                  <Settings2 className="h-4 w-4 text-[var(--accent-green-text)]" aria-hidden="true" />
                  Design template
                </legend>
                <div className="space-y-2">
                  {DESIGN_OPTIONS.map((d) => {
                    const isSelected = design === d.value;
                    return (
                      <button
                        key={d.value}
                        type="button"
                        onClick={() => setDesign(d.value)}
                        aria-pressed={isSelected}
                        className={`flex w-full items-center justify-between gap-3 rounded-xl border p-3.5 text-left transition-colors ${selectedClass(isSelected)}`}
                      >
                        <span className="flex items-center gap-3">
                          <d.icon
                            className={`h-5 w-5 shrink-0 ${isSelected ? 'text-[var(--accent-green-text)]' : 'text-[var(--text-secondary)]'}`}
                            aria-hidden="true"
                          />
                          <span>
                            <span className="block text-sm font-semibold text-[var(--text-primary)]">{d.label}</span>
                            <span className="mt-0.5 block text-xs text-[var(--text-secondary)]">{d.desc}</span>
                          </span>
                        </span>
                        {isSelected && (
                          <CheckCircle2
                            className="h-5 w-5 shrink-0 text-[var(--accent-green-text)]"
                            aria-hidden="true"
                          />
                        )}
                      </button>
                    );
                  })}
                </div>
              </fieldset>

              <div>
                <fieldset className="mb-6">
                  <legend className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
                    <Palette className="h-4 w-4 text-[var(--accent-green-text)]" aria-hidden="true" />
                    Slide colour theme
                  </legend>
                  <div className="flex flex-wrap gap-2">
                    {THEME_OPTIONS.map((t) => {
                      const isSelected = themeId === t.value;
                      return (
                        <button
                          key={t.value}
                          type="button"
                          onClick={() => setThemeId(t.value)}
                          aria-pressed={isSelected}
                          className={`flex items-center gap-2 rounded-lg border px-3 py-2 transition-colors ${selectedClass(isSelected)}`}
                        >
                          {/* Swatches preview the generated deck, not this UI. */}
                          <span className="flex -space-x-1.5" aria-hidden="true">
                            {t.colors.slice(0, 2).map((c, ci) => (
                              <span
                                key={ci}
                                className="h-4 w-4 rounded-full border border-white"
                                style={{ backgroundColor: c }}
                              />
                            ))}
                          </span>
                          <span className="text-sm font-medium text-[var(--text-primary)]">{t.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </fieldset>

                <div className="space-y-3">
                  <div>
                    <label htmlFor="deck-audience" className="mb-1.5 block text-sm font-semibold text-[var(--text-primary)]">
                      Audience
                    </label>
                    <select
                      id="deck-audience"
                      value={audience}
                      onChange={(e) => setAudience(e.target.value)}
                      className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2.5 text-sm font-medium text-[var(--text-primary)] focus:border-[var(--accent-green)] focus:outline-none"
                    >
                      {AUDIENCE_OPTIONS.map((a) => (
                        <option key={a.value} value={a.value}>{a.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="deck-language" className="mb-1.5 block text-sm font-semibold text-[var(--text-primary)]">
                      Language
                    </label>
                    <select
                      id="deck-language"
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2.5 text-sm font-medium text-[var(--text-primary)] focus:border-[var(--accent-green)] focus:outline-none"
                    >
                      {LANGUAGE_OPTIONS.map((l) => (
                        <option key={l.value} value={l.value}>{l.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Feature toggles */}
            <motion.fieldset variants={staggerItem} className="border-t border-[var(--border)] pt-6">
              <legend className="sr-only">Presentation features</legend>
              <div className="flex flex-wrap gap-2">
                {[
                  { label: 'System and flow diagrams', state: enableDiagrams, set: setEnableDiagrams },
                  { label: 'AI illustrations', state: enableImages, set: setEnableImages },
                  { label: 'Speaker notes', state: enableSpeakerNotes, set: setEnableSpeakerNotes },
                  { label: 'Source citations', state: enableSources, set: setEnableSources },
                  { label: 'Real-world examples', state: enableExamples, set: setEnableExamples },
                  { label: 'Final quiz slide', state: enableQuiz, set: setEnableQuiz },
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
                    {/* State is a word, never colour alone. */}
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

            <motion.div variants={staggerItem}>
              <button
                type="submit"
                disabled={generating || !topic.trim()}
                className="flex w-full items-center justify-center gap-2.5 rounded-xl bg-[var(--accent-green)] px-8 py-3.5 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)] active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50"
              >
                {generating ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
                    <span>{stageMessage || 'Generating presentation'}</span>
                  </>
                ) : (
                  <>
                    <Presentation className="h-5 w-5" aria-hidden="true" />
                    <span>Generate {slideCount} slide presentation</span>
                  </>
                )}
              </button>
            </motion.div>
          </form>

          {/* ═══════════ GENERATION PROGRESS ═══════════ */}
          <AnimatePresence>
            {generating && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mt-8 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-6"
                aria-live="polite"
              >
                {/* Indeterminate: the backend reports no progress, so no
                    percentage is claimed. */}
                <div
                  className="mb-4 h-1.5 w-full overflow-hidden rounded-full bg-[var(--bg-secondary)]"
                  role="progressbar"
                  aria-label="Generating presentation"
                >
                  <div className="h-full w-1/3 animate-pulse rounded-full bg-[var(--accent-green)]" />
                </div>
                <p className="font-display text-base font-semibold text-[var(--text-primary)]">
                  {stageMessage}
                </p>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">
                  This usually takes under a minute. The deck renders as 16:9 widescreen PPTX.
                </p>
              </motion.div>
            )}
          </AnimatePresence>

          {/* ═══════════ ERROR STATE ═══════════ */}
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
                      Presentation generation failed
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

          {/* ═══════════ READY ═══════════ */}
          <AnimatePresence>
            {status === 'ready' && downloadUrl && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-8 rounded-xl border border-[var(--accent-green)] bg-[var(--bg-card)] p-6"
              >
                <div className="flex flex-col gap-4 border-b border-[var(--border)] pb-6 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="mb-2 inline-flex items-center gap-1.5 rounded-lg bg-[var(--accent-green-light)] px-2.5 py-1 text-xs font-semibold text-[var(--accent-green-text)]">
                      <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                      Presentation ready
                    </p>
                    <h2 className="font-display text-2xl font-bold text-[var(--text-primary)]">
                      {resultTitle}
                    </h2>
                    <p className="mt-1 text-sm text-[var(--text-secondary)]">
                      <span className="tabular-nums">{finalSlideCount}</span> slides, {design} template, 16:9 widescreen PPTX
                    </p>
                  </div>
                  <a
                    href={downloadUrl}
                    download={`${resultTitle.replace(/[^a-zA-Z0-9]/g, '_')}.pptx`}
                    className="flex shrink-0 items-center justify-center gap-2 rounded-xl bg-[var(--accent-green)] px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)]"
                  >
                    <Download className="h-4 w-4" aria-hidden="true" />
                    Download PPTX
                  </a>
                </div>

                {resultTakeaways.length > 0 && (
                  <div className="mt-6">
                    <h3 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
                      Key takeaways
                    </h3>
                    <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
                      {resultTakeaways.map((t, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-2.5 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3.5 text-sm text-[var(--text-primary)]"
                        >
                          <BookOpen
                            className="mt-0.5 h-4 w-4 shrink-0 text-[var(--accent-green-text)]"
                            aria-hidden="true"
                          />
                          <span>{t}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* ═══════════ HISTORY ═══════════ */}
          {deckHistory.length > 0 && (
            <section className="mt-10">
              <h2 className="mb-4 flex items-center gap-2.5 font-display text-base font-semibold text-[var(--text-primary)]">
                <Clock className="h-4 w-4 text-[var(--accent-green-text)]" aria-hidden="true" />
                Recent presentations
                <span className="rounded-full border border-[var(--border)] bg-[var(--bg-secondary)] px-2.5 py-0.5 text-xs font-medium tabular-nums text-[var(--text-secondary)]">
                  {deckHistory.length}
                </span>
              </h2>
              <ul className="flex flex-col gap-2">
                {deckHistory.map((deck) => (
                  <li
                    key={deck.id}
                    className="flex items-center justify-between gap-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4"
                  >
                    <div className="flex min-w-0 items-start gap-3">
                      <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-green-light)]">
                        <Presentation
                          className="h-4 w-4 text-[var(--accent-green-text)]"
                          aria-hidden="true"
                        />
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-[var(--text-primary)]">
                          {deck.topic}
                        </p>
                        <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                          <span className="tabular-nums">{deck.slide_count || 12}</span> slides,{' '}
                          {deck.audience || 'University'},{' '}
                          {new Date(deck.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-1">
                      {deck.download_url && (
                        <a
                          href={deck.download_url}
                          download
                          aria-label={`Download ${deck.topic}`}
                          className="rounded-lg p-2.5 text-[var(--text-secondary)] transition-colors hover:bg-[var(--accent-green-light)] hover:text-[var(--accent-green-text)]"
                        >
                          <Download className="h-4 w-4" aria-hidden="true" />
                        </a>
                      )}
                      <button
                        type="button"
                        onClick={() => handleDeleteDeck(deck.id)}
                        aria-label={`Delete ${deck.topic}`}
                        className="rounded-lg p-2.5 text-[var(--text-secondary)] transition-colors hover:bg-red-50 hover:text-red-700"
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

        </motion.div>
      </div>

      {showUpgradeModal && (
        <UpgradeModal
          isOpen={showUpgradeModal}
          onClose={() => setShowUpgradeModal(false)}
        />
      )}
    </AppLayout>
  );
};

export default TopicDeckPage;
