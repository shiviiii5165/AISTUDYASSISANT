import React, { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Clock, FileText, Globe, Sparkles, CheckCircle2, Download, Loader2,
  AlertTriangle, Palette, Settings2, RotateCcw, BookOpen, Presentation,
  Trash2, ArrowRight, GraduationCap, PenTool, LayoutGrid, Newspaper, Brain, X,
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
import { GENIE, ILLUSTRATIONS } from '../lib/assets';
import { HoverCard, ScrollReveal, WavyText } from '../components/MotionUtils';
import Loader from '../components/Loader';

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
  const { collapsed: historySidebarCollapsed, toggle: toggleHistorySidebar } = useSidebarCollapse('deck-history');
  const location = useLocation();
  const presetConfig = location.state?.presetConfig;

  const [topic, setTopic] = useState(presetConfig?.topic || '');

  // Presentation Parameters
  const [slideCount, setSlideCount] = useState<number>(presetConfig?.slide_count || 12);
  const [design, setDesign] = useState<string>(presetConfig?.design || 'academic');
  const [themeId, setThemeId] = useState<string>(presetConfig?.theme || 'blue_professional');
  const [audience, setAudience] = useState<string>(presetConfig?.audience || 'university');
  const [language, setLanguage] = useState<string>(presetConfig?.language || 'english');
  const [depth] = useState<string>(presetConfig?.depth || 'full');

  // Knowledge Source
  const [sourceType, setSourceType] = useState<'general' | 'uploaded_material' | 'uploaded_material_plus_web'>(presetConfig?.source_type || 'general');
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
          setDeckHistory(Array.isArray(data) ? data : []);
        } else {
          setDeckHistory([]);
        }
      } catch (e) {
        console.error('Failed to fetch deck history', e);
        setDeckHistory([]);
      }
    };

    initData();
  }, []);

  const handleGenerate = async (e?: React.FormEvent, overridePayload?: any) => {
    if (e) e.preventDefault();
    if ((!topic.trim() && !overridePayload) || generating) return;

    setGenerating(true);
    setDownloadUrl(null);
    setFinalSlideCount(null);
    setErrorMessage(null);
    setStatus('processing');
    setStageMessage('Designing the narrative arc and slide blueprint');

    const token = useAuthStore.getState().session?.access_token;
    const apiUrl = import.meta.env.VITE_API_URL || '';

    const payload = overridePayload || {
      topic: topic.trim(),
      slide_count: slideCount,
      depth,
      audience,
      design,
      theme: themeId,
      source_type: sourceType,
      source_id: sourceType !== 'general' ? selectedPdfId : null,
      custom_context: presetConfig?.custom_context,
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

      // Synchronous completion (legacy path): use it directly.
      if (data.status === 'ready' && data.download_url) {
        setStatus('ready');
        setDownloadUrl(data.download_url);
        setFinalSlideCount(data.slide_count || slideCount);
        setResultTitle(data.deck_title || topic);
        setResultTakeaways(data.key_takeaways || []);
        return;
      }

      // Async path: the backend now returns 202 { deck_id, status: "processing" }
      // and generates in the background. Poll /{deck_id} until ready or failed.
      const deckId = data.deck_id;
      if (!deckId) {
        throw new Error('Presentation generation did not start correctly.');
      }

      const deadline = Date.now() + 5 * 60 * 1000; // 5 min cap
      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 3000));
        const pollRes = await fetch(`${apiUrl}/api/decks/${deckId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!pollRes.ok) continue;
        const pollData = await pollRes.json();
        if (pollData.status === 'ready' && pollData.download_url) {
          setStatus('ready');
          setDownloadUrl(pollData.download_url);
          setFinalSlideCount(pollData.slide_count || slideCount);
          setResultTitle(pollData.deck_title || topic);
          setResultTakeaways(pollData.key_takeaways || []);
          return;
        }
        if (pollData.status === 'failed') {
          throw new Error(pollData.error_message || 'Presentation generation failed.');
        }
      }
      throw new Error('Presentation generation timed out. Please try again.');
    } catch (err: any) {
      console.error('[TopicDeckPage] Generation error:', err);
      setErrorMessage(err.message || 'An unexpected error occurred during generation.');
      setStatus('failed');
    } finally {
      setGenerating(false);
    }
  };

  const handleDeleteDeck = async (deckId: string) => {
    if (!window.confirm("Are you sure you want to delete this deck?")) return;
    
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
      ? 'border-[var(--accent-royal)] bg-[var(--accent-baby)]/10 ring-1 ring-[var(--accent-royal)]'
      : 'border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)]';

  return (
    <AppLayout title="PPT Generator">
      <SEO 
        title="AI PowerPoint Generator | TeachGenie"
        description="Convert syllabus topics and notes into fully styled PowerPoint presentations."
      />
      <div className="flex h-full w-full">
        <HistorySidebar
          title="Presentations"
          items={(Array.isArray(deckHistory) ? deckHistory : []).map(d => ({ id: d.id, title: d.topic, date: d.created_at }))}
          selectedId={null} // Decks don't have a "selected" viewer state yet, they just download
          onSelect={(id) => {
            const deck = (Array.isArray(deckHistory) ? deckHistory : []).find(d => d.id === id);
            if (deck?.download_url) {
              window.open(deck.download_url, '_blank');
            } else if (deck) {
              setTopic(deck.topic);
            }
          }}
          onNew={() => { setStatus(null); setTopic(''); }}
          collapsed={historySidebarCollapsed}
          onToggle={toggleHistorySidebar}
        />
        
        <div className="flex-1 overflow-y-auto px-4 py-8 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-4xl">
            <motion.div variants={staggerContainer} initial="hidden" animate="show">

              <motion.div variants={staggerItem} className="mb-10">
                <GreetingHeader
                  subtitle="Describe a topic and get an editable deck with speaker notes."
                  avatarImageSrc={GENIE.teaching}
                />
              </motion.div>

              {generating && (
                <motion.div variants={staggerItem} className="mb-6">
                  <img src={ILLUSTRATIONS.pptGenerating} alt="" aria-hidden="true" className="mx-auto h-48 w-48 object-contain" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
                </motion.div>
              )}

              <form onSubmit={handleGenerate} className="space-y-10">

                {/* Topic */}
                <motion.div variants={staggerItem}>
                  <label htmlFor="deck-topic" className="mb-3 block text-sm font-semibold text-[var(--text-primary)]">
                    Presentation topic
                  </label>
                  <div className="flex items-center gap-2 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-2 focus-within:border-[var(--accent-royal)] focus-within:ring-1 focus-within:ring-[var(--accent-royal)] transition-all">
                    <input
                      id="deck-topic"
                      type="text"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      placeholder="Kubernetes architecture and orchestration"
                      disabled={generating}
                      className="min-w-0 flex-1 border-none bg-transparent px-4 py-3 text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none"
                    />
                    {topic && !generating && (
                      <button
                        type="button"
                        onClick={() => setTopic('')}
                        aria-label="Clear topic"
                        className="rounded-xl p-2.5 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                      >
                        <X className="h-4 w-4" aria-hidden="true" />
                      </button>
                    )}
                    <button
                      type="submit"
                      disabled={generating || !topic.trim()}
                      aria-label="Generate presentation"
                      className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-royal)] text-white transition-colors hover:bg-[var(--accent-royal)]/90 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {generating ? (
                        <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
                      ) : (
                        <ArrowRight className="h-5 w-5" aria-hidden="true" />
                      )}
                    </button>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2.5">
                    {SUGGESTED_TOPICS.map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => setTopic(t)}
                        className="rounded-full border border-[var(--border)] bg-[var(--bg-card)] px-4 py-2 text-xs font-medium text-[var(--text-secondary)] transition-all hover:border-[var(--accent-royal)] hover:text-[var(--accent-royal)] hover:shadow-sm"
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </motion.div>

                {/* Knowledge source */}
                <motion.fieldset variants={staggerItem}>
                  <legend className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
                    Knowledge source
                  </legend>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                    {[
                      { type: 'general' as const, label: 'General knowledge', icon: Globe, desc: 'Model subject knowledge' },
                      { type: 'uploaded_material' as const, label: 'My uploaded notes', icon: FileText, desc: 'Grounded in your documents' },
                      { type: 'uploaded_material_plus_web' as const, label: 'Document and web', icon: Sparkles, desc: 'Documents plus research' },
                    ].map((src) => {
                      const isSelected = sourceType === src.type;
                      return (
                        <HoverCard key={src.type}>
                          <button
                            type="button"
                            onClick={() => setSourceType(src.type)}
                            aria-pressed={isSelected}
                            className={`flex h-full w-full flex-col rounded-2xl border p-5 text-left transition-all duration-300 ${selectedClass(isSelected)}`}
                          >
                            <span className="mb-3 flex items-center gap-3">
                              <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${isSelected ? 'bg-[var(--accent-royal)] text-white' : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)]'}`}>
                                <src.icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                              </span>
                              <span className={`text-sm font-bold ${isSelected ? 'text-[var(--accent-royal)]' : 'text-[var(--text-primary)]'}`}>{src.label}</span>
                            </span>
                            <span className="text-xs text-[var(--text-secondary)] leading-relaxed">{src.desc}</span>
                          </button>
                        </HoverCard>
                      );
                    })}
                  </div>

                  {sourceType !== 'general' && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="mt-4 rounded-2xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5"
                    >
                      <label htmlFor="deck-source" className="mb-2 block text-sm font-bold text-[var(--text-primary)]">
                        Source document
                      </label>
                      {userPdfs.length > 0 ? (
                        <select
                          id="deck-source"
                          value={selectedPdfId}
                          onChange={(e) => setSelectedPdfId(e.target.value)}
                          className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 text-sm font-medium text-[var(--text-primary)] focus:border-[var(--accent-royal)] focus:ring-1 focus:ring-[var(--accent-royal)] focus:outline-none transition-all"
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
                    </motion.div>
                  )}
                </motion.fieldset>

                {/* Slide count */}
                <motion.fieldset variants={staggerItem}>
                  <legend className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
                    Slide count
                  </legend>
                  <div className="flex flex-wrap gap-3">
                    {SLIDE_COUNT_OPTIONS.map((num) => {
                      const isSelected = slideCount === num;
                      return (
                        <button
                          key={num}
                          type="button"
                          onClick={() => setSlideCount(num)}
                          aria-pressed={isSelected}
                          className={`rounded-full border px-6 py-2.5 text-sm font-bold tabular-nums transition-all ${
                            isSelected
                              ? 'border-[var(--accent-royal)] bg-[var(--accent-royal)] text-white shadow-md'
                              : 'border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-primary)] hover:border-[var(--accent-royal)] hover:text-[var(--accent-royal)]'
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
                    <legend className="mb-4 flex items-center gap-2 text-sm font-bold text-[var(--text-primary)]">
                      <Settings2 className="h-5 w-5 text-[var(--accent-royal)]" aria-hidden="true" />
                      Design template
                    </legend>
                    <div className="space-y-3">
                      {DESIGN_OPTIONS.map((d) => {
                        const isSelected = design === d.value;
                        return (
                          <button
                            key={d.value}
                            type="button"
                            onClick={() => setDesign(d.value)}
                            aria-pressed={isSelected}
                            className={`flex w-full items-center justify-between gap-4 rounded-2xl border p-4 text-left transition-all duration-300 ${selectedClass(isSelected)}`}
                          >
                            <span className="flex items-center gap-4">
                              <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${isSelected ? 'bg-[var(--accent-royal)] text-white' : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)]'}`}>
                                <d.icon className="h-5 w-5" aria-hidden="true" />
                              </span>
                              <span>
                                <span className={`block text-sm font-bold ${isSelected ? 'text-[var(--accent-royal)]' : 'text-[var(--text-primary)]'}`}>{d.label}</span>
                                <span className="mt-1 block text-xs text-[var(--text-secondary)] leading-relaxed">{d.desc}</span>
                              </span>
                            </span>
                            {isSelected && (
                              <CheckCircle2
                                className="h-6 w-6 shrink-0 text-[var(--accent-royal)]"
                                aria-hidden="true"
                              />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </fieldset>

                  <div>
                    <fieldset className="mb-8">
                      <legend className="mb-4 flex items-center gap-2 text-sm font-bold text-[var(--text-primary)]">
                        <Palette className="h-5 w-5 text-[var(--accent-royal)]" aria-hidden="true" />
                        Slide colour theme
                      </legend>
                      <div className="flex flex-wrap gap-3">
                        {THEME_OPTIONS.map((t) => {
                          const isSelected = themeId === t.value;
                          return (
                            <button
                              key={t.value}
                              type="button"
                              onClick={() => setThemeId(t.value)}
                              aria-pressed={isSelected}
                              className={`flex items-center gap-2.5 rounded-full border px-4 py-2 transition-all ${selectedClass(isSelected)} ${isSelected ? 'shadow-sm' : 'hover:border-[var(--accent-royal)]'}`}
                            >
                              {/* Swatches preview the generated deck, not this UI. */}
                              <span className="flex -space-x-1.5" aria-hidden="true">
                                {t.colors.slice(0, 2).map((c, ci) => (
                                  <span
                                    key={ci}
                                    className="h-5 w-5 rounded-full border-2 border-white shadow-sm"
                                    style={{ backgroundColor: c }}
                                  />
                                ))}
                              </span>
                              <span className={`text-sm font-bold ${isSelected ? 'text-[var(--accent-royal)]' : 'text-[var(--text-primary)]'}`}>{t.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    </fieldset>

                    <div className="space-y-4">
                      <div>
                        <label htmlFor="deck-audience" className="mb-2 block text-sm font-bold text-[var(--text-primary)]">
                          Audience
                        </label>
                        <select
                          id="deck-audience"
                          value={audience}
                          onChange={(e) => setAudience(e.target.value)}
                          className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 text-sm font-medium text-[var(--text-primary)] focus:border-[var(--accent-royal)] focus:ring-1 focus:ring-[var(--accent-royal)] focus:outline-none transition-colors"
                        >
                          {AUDIENCE_OPTIONS.map((a) => (
                            <option key={a.value} value={a.value}>{a.label}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label htmlFor="deck-language" className="mb-2 block text-sm font-bold text-[var(--text-primary)]">
                          Language
                        </label>
                        <select
                          id="deck-language"
                          value={language}
                          onChange={(e) => setLanguage(e.target.value)}
                          className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 text-sm font-medium text-[var(--text-primary)] focus:border-[var(--accent-royal)] focus:ring-1 focus:ring-[var(--accent-royal)] focus:outline-none transition-colors"
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
                <motion.fieldset variants={staggerItem} className="border-t border-[var(--border)] pt-8">
                  <legend className="sr-only">Presentation features</legend>
                  <div className="flex flex-wrap gap-3">
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
                        className={`flex items-center gap-3 rounded-full border px-5 py-2.5 text-sm font-bold transition-all ${
                          opt.state
                            ? 'border-[var(--accent-royal)] bg-[var(--accent-baby)]/20 text-[var(--accent-royal)] shadow-sm ring-1 ring-[var(--accent-royal)]'
                            : 'border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:border-[var(--accent-royal)]/50 hover:bg-[var(--bg-hover)]'
                        }`}
                      >
                        <span>{opt.label}</span>
                        {/* State is a word, never colour alone. */}
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-black uppercase tracking-wider ${
                          opt.state
                            ? 'bg-[var(--accent-royal)] text-white'
                            : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)]'
                        }`}>
                          {opt.state ? 'On' : 'Off'}
                        </span>
                      </button>
                    ))}
                  </div>
                </motion.fieldset>

                <motion.div variants={staggerItem}>
                  <HoverCard>
                    <button
                      type="submit"
                      disabled={generating || !topic.trim()}
                      className="btn-gold flex w-full items-center justify-center gap-3 px-8 py-4 text-base"
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
                  </HoverCard>
                </motion.div>
              </form>

              {/* ═══════════ GENERATION PROGRESS ═══════════ */}
              <AnimatePresence>
                {generating && (
                  <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="mt-8 overflow-hidden rounded-xl border border-[var(--border)] bg-white p-6 shadow-sm dark:bg-zinc-900"
                    aria-live="polite"
                  >
                    <Loader
                      title="Generating your presentation..."
                      subtitle={stageMessage || "This usually takes under a minute. The deck renders as 16:9 widescreen PPTX."}
                      size="md"
                    />
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
                    className="mt-10 rounded-2xl border border-[var(--accent-royal)] bg-[var(--bg-card)] p-8 shadow-bento"
                  >
                    <div className="flex flex-col gap-6 border-b border-[var(--border)] pb-8 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <p className="mb-3 inline-flex items-center gap-2 rounded-full bg-[var(--accent-baby)]/30 px-3 py-1.5 text-xs font-bold text-[var(--accent-royal)]">
                          <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                          Presentation ready
                        </p>
                        <h2 className="font-display text-3xl font-bold text-[var(--text-primary)]">
                          <WavyText text={resultTitle} />
                        </h2>
                        <p className="mt-2 text-sm text-[var(--text-secondary)]">
                          <span className="tabular-nums font-bold">{finalSlideCount}</span> slides, <span className="font-bold">{design}</span> template, 16:9 widescreen PPTX
                        </p>
                      </div>
                      <a
                        href={downloadUrl}
                        download={`${resultTitle.replace(/[^a-zA-Z0-9]/g, '_')}.pptx`}
                        className="btn-gold flex shrink-0 items-center justify-center gap-2 px-8 py-4 text-sm"
                      >
                        <Download className="h-5 w-5" aria-hidden="true" />
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
                    {(Array.isArray(deckHistory) ? deckHistory : []).map((deck) => (
                      <ScrollReveal key={deck.id}>
                        <li
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
                      </ScrollReveal>
                    ))}
                  </ul>
                </section>
              )}

            </motion.div>
          </div>
        </div>
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
