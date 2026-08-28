import React, { useState, useEffect } from 'react';
import { 
  ArrowUp, Clock, FileText, Globe, Sparkles, Filter, ChevronDown, CheckCircle2, 
  Download, Loader2, AlertTriangle, Layers, Palette, Users, Zap, Settings2, 
  Eye, RotateCcw, CheckSquare, Square, BookOpen, Presentation, RefreshCw, Trash2, Plus, ArrowRight
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { useAuthStore } from '../store/useAuthStore';
import { fetchPdfs, type PDFDocument } from '../lib/api';
import UpgradeModal from '../components/billing/UpgradeModal';
import GenieFloating from '../components/mascot/GenieFloating';

// ═══════════════════════════════════════════════════════════════════════════
// CONFIGURATION OPTIONS
// ═══════════════════════════════════════════════════════════════════════════

const SLIDE_COUNT_OPTIONS = [10, 11, 12, 13, 14, 15];

const DESIGN_OPTIONS = [
  { value: 'academic', label: 'Academic Clean', icon: '🎓', desc: 'University lecture with structured learning progression' },
  { value: 'minimal', label: 'Modern Minimal', icon: '✨', desc: 'Canva-style spacious layout with focal takeaways' },
  { value: 'technical', label: 'Technical Grid', icon: '⚙️', desc: 'Architecture diagrams, pipelines & component grids' },
  { value: 'editorial', label: 'Editorial', icon: '📰', desc: 'Magazine & report composition with asymmetric balance' },
  { value: 'visual', label: 'Visual Learning', icon: '🧠', desc: 'Diagram-first visual pedagogy with concise micro-text' },
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
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
};

const TopicDeckPage: React.FC = () => {
  const { user: currentUser } = useAuthStore();
  const [topic, setTopic] = useState('');
  
  // Presentation Parameters
  const [slideCount, setSlideCount] = useState<number>(12);
  const [design, setDesign] = useState<string>('academic');
  const [themeId, setThemeId] = useState<string>('blue_professional');
  const [audience, setAudience] = useState<string>('university');
  const [language, setLanguage] = useState<string>('english');
  const [depth, setDepth] = useState<string>('full');

  // Knowledge Source
  const [sourceType, setSourceType] = useState<'general' | 'uploaded_material' | 'uploaded_material_plus_web'>('general');
  const [selectedPdfId, setSelectedPdfId] = useState<string>('');
  const [userPdfs, setUserPdfs] = useState<PDFDocument[]>([]);
  const [loadingPdfs, setLoadingPdfs] = useState<boolean>(false);

  // Feature Options Toggles
  const [enableDiagrams, setEnableDiagrams] = useState<boolean>(true);
  const [enableImages, setEnableImages] = useState<boolean>(true);
  const [enableSpeakerNotes, setEnableSpeakerNotes] = useState<boolean>(true);
  const [enableSources, setEnableSources] = useState<boolean>(true);
  const [enableExamples, setEnableExamples] = useState<boolean>(true);
  const [enableQuiz, setEnableQuiz] = useState<boolean>(false);

  // Generation & Status State
  const [generating, setGenerating] = useState<boolean>(false);
  const [currentStage, setCurrentStage] = useState<number>(0);
  const [stageMessage, setStageMessage] = useState<string>('');
  const [progressPercent, setProgressPercent] = useState<number>(0);
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
    setCurrentStage(0);
    setProgressPercent(15);
    setStageMessage('Designing narrative arc & slide blueprint...');

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
      // Advance stage timers for UX feedback
      const timer1 = setTimeout(() => {
        setCurrentStage(1);
        setProgressPercent(45);
        setStageMessage('Generating scannable content & rich speaker notes in batches...');
      }, 3000);

      const timer2 = setTimeout(() => {
        setCurrentStage(2);
        setProgressPercent(75);
        setStageMessage('Resolving deterministic diagrams & visual assets...');
      }, 8000);

      const timer3 = setTimeout(() => {
        setCurrentStage(3);
        setProgressPercent(90);
        setStageMessage('Executing Python QA bounds inspection & slide formatting...');
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
        setProgressPercent(100);
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

  return (
    <AppLayout title="AI Presentation Studio">
      <SEO 
        title="TeachGenie AI Presentation Studio — NotebookLM Quality PPTs" 
        description="Generate deterministic, beautifully designed PowerPoint presentations with exact slide counts, structured diagrams, and verified knowledge grounding." 
      />

      <div className="min-h-[calc(100vh-64px)] bg-surface text-ink pb-24 pt-12 px-4 sm:px-6 lg:px-8 overflow-hidden font-sans">
        <motion.div 
          className="max-w-4xl mx-auto"
          variants={staggerContainer}
          initial="hidden"
          animate="show"
        >
          
          {/* Header Banner - Screen A Style */}
          <motion.div variants={staggerItem} className="text-center mb-12 flex flex-col items-center">
            
            {/* Status Badges */}
            <div className="flex items-center justify-center gap-2 mb-8">
              <div className="px-4 py-1.5 rounded-full bg-genie-amber-soft text-genie-amber font-semibold text-sm shadow-sm flex items-center gap-1.5 border border-border-soft">
                📊 {deckHistory.length} total created
              </div>
            </div>

            {/* Floating Genie */}
            <GenieFloating size="lg" className="mb-4" />

            {/* Headline */}
            <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-3">
              <span className="text-ink block mb-1">Transform Ideas into</span>
              <span className="bg-gradient-to-r from-genie-purple to-genie-amber bg-clip-text text-transparent pb-1">Professional Slide Decks</span>
            </h1>
            <p className="mt-2 text-ink-muted text-lg max-w-2xl mx-auto">
              Choose your knowledge source, exact slide count, and design system. Rendered with clean Python typography.
            </p>
          </motion.div>

          <form onSubmit={handleGenerate} className="space-y-10">
            
            {/* Topic Input - Big Pill Search Bar */}
            <motion.div variants={staggerItem} className="max-w-3xl mx-auto w-full">
              <div className="relative group shadow-sm hover:shadow-md transition-shadow rounded-full bg-surface-card border border-border-soft p-2 flex items-center">
                <button type="button" className="p-3 text-ink-muted hover:text-genie-purple transition-colors ml-1 pointer-events-none">
                  <Plus className="w-6 h-6" />
                </button>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="What would you like to present today?"
                  disabled={generating}
                  className="flex-1 bg-transparent border-none text-ink placeholder:text-ink-muted/60 focus:ring-0 text-lg px-2 py-3 focus:outline-none"
                />
                {topic && !generating && (
                  <button
                    type="button"
                    onClick={() => setTopic('')}
                    className="p-2 text-ink-muted hover:text-ink transition-colors mr-1 cursor-pointer"
                  >
                    ✕
                  </button>
                )}
                <button
                  type="submit"
                  disabled={generating || !topic.trim()}
                  className="ml-2 w-12 h-12 rounded-full bg-genie-amber text-white flex items-center justify-center hover:bg-amber-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm shrink-0 cursor-pointer"
                >
                  {generating ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowRight className="w-5 h-5" />}
                </button>
              </div>

              {/* Suggestion Chips */}
              <div className="mt-4 flex flex-wrap gap-2 justify-center">
                {SUGGESTED_TOPICS.map((t) => (
                  <motion.button
                    whileTap={{ scale: 0.96 }}
                    key={t}
                    type="button"
                    onClick={() => setTopic(t)}
                    className="text-xs px-4 py-2 rounded-full border border-border-soft bg-surface-card text-ink-muted hover:text-ink hover:border-genie-purple/30 hover:bg-genie-purple-soft/30 transition-colors cursor-pointer shadow-sm"
                  >
                    {t}
                  </motion.button>
                ))}
              </div>
            </motion.div>

            {/* Knowledge Source Selector */}
            <motion.div variants={staggerItem} className="pt-2">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {[
                  { type: 'general' as const, label: 'General Knowledge', icon: Globe, desc: 'AI subject knowledge' },
                  { type: 'uploaded_material' as const, label: 'My Uploaded Notes', icon: FileText, desc: 'Grounded in PDF/Notes' },
                  { type: 'uploaded_material_plus_web' as const, label: 'Document + Web', icon: Sparkles, desc: 'Document + Research' },
                ].map((src) => {
                  const isSelected = sourceType === src.type;
                  return (
                    <motion.button
                      whileTap={{ scale: 0.98 }}
                      key={src.type}
                      type="button"
                      onClick={() => setSourceType(src.type)}
                      className={`flex flex-col text-left p-5 rounded-2xl border transition-all cursor-pointer relative overflow-hidden ${
                        isSelected
                          ? 'border-genie-purple bg-genie-purple-soft ring-1 ring-genie-purple shadow-sm'
                          : 'border-border-soft bg-surface-card hover:border-genie-purple/40 shadow-sm hover:shadow-md'
                      }`}
                    >
                      <div className="flex items-center gap-3 mb-2">
                        <div className={`p-2 rounded-full ${isSelected ? 'bg-white text-genie-purple' : 'bg-surface text-ink-muted'}`}>
                          <src.icon className="w-5 h-5" />
                        </div>
                        <span className={`text-sm font-semibold ${isSelected ? 'text-genie-purple' : 'text-ink'}`}>{src.label}</span>
                      </div>
                      <span className={`text-xs ml-[3.25rem] ${isSelected ? 'text-genie-purple/80' : 'text-ink-muted'}`}>{src.desc}</span>
                    </motion.button>
                  );
                })}
              </div>

              {/* If Uploaded Material Selected: Show Document Dropdown */}
              {sourceType !== 'general' && (
                <motion.div 
                  initial={{ opacity: 0, height: 0 }} 
                  animate={{ opacity: 1, height: 'auto' }} 
                  className="mt-4 p-5 bg-genie-purple-soft/50 border border-genie-purple/20 rounded-2xl"
                >
                  <label className="block text-sm font-semibold text-genie-purple mb-2">
                    Select Source Document from Your Library
                  </label>
                  {userPdfs.length > 0 ? (
                    <select
                      value={selectedPdfId}
                      onChange={(e) => setSelectedPdfId(e.target.value)}
                      className="w-full px-4 py-3 bg-surface-card border border-border-soft rounded-full text-sm text-ink focus:outline-none focus:ring-2 focus:ring-genie-purple font-medium shadow-sm appearance-none cursor-pointer"
                    >
                      {userPdfs.map((pdf) => (
                        <option key={pdf.id} value={pdf.id}>
                          📄 {pdf.name} ({pdf.subject || 'General'}) — {pdf.page_count || 1} pages
                        </option>
                      ))}
                    </select>
                  ) : (
                    <p className="text-sm text-genie-purple/80 bg-white/50 p-3 rounded-xl">
                      No uploaded PDFs found. You can upload a PDF in the Library or continue with General Knowledge.
                    </p>
                  )}
                </motion.div>
              )}
            </motion.div>

            {/* Exact Slide Count & Options Row */}
            <motion.div variants={staggerItem} className="flex flex-col gap-6">
              
              <div className="flex flex-wrap items-center justify-center gap-3">
                <span className="text-sm font-semibold text-ink-muted mr-2">Exact Slide Count:</span>
                {SLIDE_COUNT_OPTIONS.map((num) => {
                  const isSelected = slideCount === num;
                  return (
                    <motion.button
                      whileTap={{ scale: 0.95 }}
                      key={num}
                      type="button"
                      onClick={() => setSlideCount(num)}
                      className={`px-5 py-2 rounded-full border text-sm font-bold transition-all shadow-sm cursor-pointer ${
                        isSelected
                          ? 'border-genie-purple bg-genie-purple text-white shadow-md'
                          : 'border-border-soft bg-surface-card text-ink hover:bg-surface'
                      }`}
                    >
                      {num} Slides
                    </motion.button>
                  );
                })}
              </div>

              {/* Design Template System */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pt-4">
                <div>
                  <h3 className="text-sm font-semibold text-ink-muted uppercase tracking-wider mb-4">Design Template System</h3>
                  <div className="space-y-3">
                    {DESIGN_OPTIONS.map((d) => {
                      const isSelected = design === d.value;
                      return (
                        <motion.button
                          whileTap={{ scale: 0.98 }}
                          key={d.value}
                          type="button"
                          onClick={() => setDesign(d.value)}
                          className={`w-full flex items-center justify-between p-4 rounded-2xl border text-left transition-all cursor-pointer shadow-sm ${
                            isSelected
                              ? 'border-genie-purple bg-genie-purple-soft ring-1 ring-genie-purple'
                              : 'border-border-soft bg-surface-card hover:border-genie-purple/40 hover:shadow-md'
                          }`}
                        >
                          <div className="flex items-center gap-4">
                            <span className="text-2xl">{d.icon}</span>
                            <div>
                              <p className={`text-sm font-bold ${isSelected ? 'text-genie-purple' : 'text-ink'}`}>{d.label}</p>
                              <p className={`text-xs mt-0.5 ${isSelected ? 'text-genie-purple/80' : 'text-ink-muted'}`}>{d.desc}</p>
                            </div>
                          </div>
                          {isSelected && <CheckCircle2 className="w-5 h-5 text-genie-purple shrink-0" />}
                        </motion.button>
                      );
                    })}
                  </div>
                </div>

                {/* Theme Palette & Audience */}
                <div>
                  <h3 className="text-sm font-semibold text-ink-muted uppercase tracking-wider mb-4">Color Theme Palette</h3>
                  <div className="flex flex-wrap gap-3 mb-8">
                    {THEME_OPTIONS.map((t) => {
                      const isSelected = themeId === t.value;
                      return (
                        <motion.button
                          whileTap={{ scale: 0.95 }}
                          key={t.value}
                          type="button"
                          onClick={() => setThemeId(t.value)}
                          className={`flex items-center gap-2 px-4 py-2.5 rounded-full border transition-all cursor-pointer shadow-sm relative ${
                            isSelected
                              ? 'border-genie-purple bg-genie-purple-soft ring-1 ring-genie-purple shadow-md z-10'
                              : 'border-border-soft bg-surface-card hover:bg-surface'
                          }`}
                        >
                          <div className="flex -space-x-1.5 shrink-0 shadow-sm rounded-full bg-white p-0.5">
                            {t.colors.slice(0,2).map((c, ci) => (
                              <div key={ci} className="w-4 h-4 rounded-full border border-white" style={{ backgroundColor: c }} />
                            ))}
                          </div>
                          <span className={`text-sm font-semibold ${isSelected ? 'text-genie-purple' : 'text-ink'}`}>{t.label}</span>
                        </motion.button>
                      );
                    })}
                  </div>

                  <h3 className="text-sm font-semibold text-ink-muted uppercase tracking-wider mb-4">Audience & Language</h3>
                  <div className="flex flex-wrap gap-4">
                    <div className="relative group">
                      <select
                        value={audience}
                        onChange={(e) => setAudience(e.target.value)}
                        className="appearance-none pl-5 pr-10 py-3 bg-surface-card border border-border-soft rounded-full text-sm font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-genie-purple shadow-sm min-w-[200px] cursor-pointer"
                      >
                        {AUDIENCE_OPTIONS.map((a) => (
                          <option key={a.value} value={a.value}>{a.label}</option>
                        ))}
                      </select>
                      <ChevronDown className="w-4 h-4 text-ink-muted absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none group-hover:text-ink" />
                    </div>
                    <div className="relative group">
                      <select
                        value={language}
                        onChange={(e) => setLanguage(e.target.value)}
                        className="appearance-none pl-5 pr-10 py-3 bg-surface-card border border-border-soft rounded-full text-sm font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-genie-purple shadow-sm min-w-[140px] cursor-pointer"
                      >
                        {LANGUAGE_OPTIONS.map((l) => (
                          <option key={l.value} value={l.value}>{l.label}</option>
                        ))}
                      </select>
                      <ChevronDown className="w-4 h-4 text-ink-muted absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none group-hover:text-ink" />
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Presentation Component Features (Toggle Pills) */}
            <motion.div variants={staggerItem} className="pt-6 border-t border-border-soft">
              <div className="flex flex-wrap items-center justify-center gap-3">
                {[
                  { label: 'System & Flow Diagrams', state: enableDiagrams, set: setEnableDiagrams },
                  { label: 'Selective AI Illustrations', state: enableImages, set: setEnableImages },
                  { label: 'Rich Speaker Notes', state: enableSpeakerNotes, set: setEnableSpeakerNotes },
                  { label: 'Document Source Citations', state: enableSources, set: setEnableSources },
                  { label: 'Real-World Case Examples', state: enableExamples, set: setEnableExamples },
                  { label: 'Interactive Final Quiz', state: enableQuiz, set: setEnableQuiz },
                ].map((opt, i) => (
                  <motion.button
                    whileTap={{ scale: 0.95 }}
                    key={i}
                    type="button"
                    onClick={() => opt.set(!opt.state)}
                    className={`flex items-center gap-3 px-4 py-2.5 rounded-full border text-sm font-semibold transition-colors shadow-sm cursor-pointer ${
                      opt.state
                        ? 'border-genie-purple bg-genie-purple-soft text-genie-purple ring-1 ring-genie-purple'
                        : 'border-border-soft bg-surface-card text-ink-muted hover:text-ink hover:bg-surface'
                    }`}
                  >
                    <span>{opt.label}</span>
                    <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full font-bold ${
                      opt.state ? 'bg-genie-purple text-white' : 'bg-surface text-ink-muted border border-border-soft'
                    }`}>
                      {opt.state ? 'ON' : 'OFF'}
                    </span>
                  </motion.button>
                ))}
              </div>
            </motion.div>

            {/* Submit Button */}
            <motion.div variants={staggerItem} className="pt-8 flex justify-center">
              <motion.button
                whileTap={(!generating && topic.trim()) ? { scale: 0.96 } : {}}
                type="submit"
                disabled={generating || !topic.trim()}
                className="w-full max-w-md py-5 px-8 rounded-full font-bold text-lg shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed bg-gradient-to-r from-genie-purple to-genie-amber text-white border-0 cursor-pointer"
              >
                {generating ? (
                  <>
                    <Loader2 className="w-6 h-6 animate-spin" />
                    <span>{stageMessage || 'Generating Presentation...'}</span>
                  </>
                ) : (
                  <>
                    <Presentation className="w-6 h-6" />
                    <span>Generate {slideCount}-Slide Presentation (.pptx)</span>
                  </>
                )}
              </motion.button>
            </motion.div>
          </form>

          {/* ═══════════ LIVE GENERATION PROGRESS TRACKER ═══════════ */}
          <AnimatePresence>
            {generating && (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="bg-surface-card rounded-2xl border border-genie-amber/30 shadow-md p-8 mt-12 text-center relative overflow-hidden"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-genie-purple-soft/20 via-genie-amber-soft/20 to-genie-purple-soft/20 animate-pulse" />
                <div className="relative z-10">
                  <div className="flex items-center justify-between text-xs font-bold text-ink-muted mb-4 uppercase tracking-widest">
                    <span>Stage {currentStage + 1} of 4</span>
                    <span className="text-genie-purple">{progressPercent}% Complete</span>
                  </div>
                  
                  <div className="w-full bg-surface rounded-full h-3 mb-6 overflow-hidden border border-border-soft">
                    <div 
                      className="bg-gradient-to-r from-genie-purple to-genie-amber h-full rounded-full transition-all duration-700 ease-out" 
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>

                  <p className="text-lg font-bold text-ink mb-1">{stageMessage}</p>
                  <p className="text-sm text-ink-muted">Deterministic Python layout engine rendering 16:9 widescreen canvas...</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* ═══════════ ERROR STATE ═══════════ */}
          <AnimatePresence>
            {errorMessage && !generating && (
              <motion.div 
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                className="bg-red-50 border border-red-200 rounded-2xl p-8 mt-12 text-center shadow-sm"
              >
                <AlertTriangle className="w-10 h-10 text-red-500 mx-auto mb-3" />
                <h3 className="text-lg font-bold text-red-900 mb-2">Presentation Generation Failed</h3>
                <p className="text-sm text-red-700 mb-6">{errorMessage}</p>
                <button
                  onClick={handleGenerate}
                  className="px-6 py-2.5 bg-red-600 text-white rounded-full text-sm font-bold hover:bg-red-700 inline-flex items-center gap-2 shadow-sm cursor-pointer"
                >
                  <RotateCcw className="w-4 h-4" /> Try Again
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* ═══════════ PRESENTATION READY VIEW ═══════════ */}
          <AnimatePresence>
            {status === 'ready' && downloadUrl && (
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                className="bg-surface-card rounded-2xl border border-sage-500/30 shadow-md p-8 mt-12"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 pb-8 border-b border-border-soft">
                  <div>
                    <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-sage-50 text-sage-600 text-sm font-bold mb-3 border border-sage-500/20 shadow-sm">
                      <CheckCircle2 className="w-4 h-4" /> Presentation Ready
                    </div>
                    <h2 className="text-3xl font-bold text-ink">{resultTitle}</h2>
                    <p className="text-base text-ink-muted mt-2 font-medium">
                      {finalSlideCount} Slides  •  {design.toUpperCase()} Template  •  16:9 Widescreen (.pptx)
                    </p>
                  </div>
                  <a
                    href={downloadUrl}
                    download={`${resultTitle.replace(/[^a-zA-Z0-9]/g, '_')}.pptx`}
                    className="px-8 py-4 bg-sage-600 hover:bg-sage-700 text-white rounded-full font-bold text-base shadow-sm hover:shadow-md flex items-center justify-center gap-2 shrink-0 transition-all cursor-pointer"
                  >
                    <Download className="w-5 h-5" /> Download PPTX
                  </a>
                </div>

                {resultTakeaways.length > 0 && (
                  <div className="mt-8">
                    <h4 className="text-sm font-bold text-ink-muted uppercase tracking-wider mb-4">Core Deck Takeaways</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {resultTakeaways.map((t, i) => (
                        <div key={i} className="p-4 bg-surface rounded-2xl border border-border-soft text-sm text-ink font-medium flex items-start gap-3 shadow-sm">
                          <span className="text-sage-500 font-bold text-lg leading-none mt-0.5">✦</span>
                          <span>{t}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* ═══════════ PREVIOUS DECKS HISTORY ═══════════ */}
          {deckHistory.length > 0 && (
            <motion.div variants={staggerItem} className="mt-16">
              <h3 className="text-lg font-bold text-ink mb-6 flex items-center gap-2 px-2">
                <Clock className="w-5 h-5 text-genie-purple" /> Recent Presentations
              </h3>
              <div className="flex flex-col gap-3">
                {deckHistory.map((deck, idx) => (
                  <motion.div 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.04 }}
                    whileHover={{ y: -2, boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)' }}
                    key={deck.id} 
                    className="p-5 bg-surface-card rounded-2xl border border-border-soft flex items-center justify-between gap-4 transition-all shadow-sm"
                  >
                    <div className="flex items-start gap-4 min-w-0">
                      <div className="w-10 h-10 rounded-full bg-genie-purple-soft flex items-center justify-center shrink-0 mt-0.5">
                        <Presentation className="w-5 h-5 text-genie-purple" />
                      </div>
                      <div>
                        <p className="text-base font-bold text-ink truncate">{deck.topic}</p>
                        <p className="text-sm text-ink-muted font-medium mt-0.5">
                          {deck.slide_count || 12} slides  •  {deck.audience || 'University'}  •  {new Date(deck.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {deck.download_url && (
                        <a
                          href={deck.download_url}
                          download
                          className="p-3 text-ink-muted hover:text-sage-600 hover:bg-sage-50 rounded-full transition-colors cursor-pointer"
                          title="Download presentation"
                        >
                          <Download className="w-5 h-5" />
                        </a>
                      )}
                      <button
                        onClick={() => handleDeleteDeck(deck.id)}
                        className="p-3 text-ink-muted hover:text-red-600 hover:bg-red-50 rounded-full transition-colors cursor-pointer"
                        title="Delete presentation"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
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
