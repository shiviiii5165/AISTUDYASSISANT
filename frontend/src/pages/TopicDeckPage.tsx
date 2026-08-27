import React, { useState, useEffect } from 'react';
import { 
  ArrowUp, Clock, FileText, Globe, Sparkles, Filter, ChevronDown, CheckCircle2, 
  Download, Loader2, AlertTriangle, Layers, Palette, Users, Zap, Settings2, 
  Eye, RotateCcw, CheckSquare, Square, BookOpen, Presentation, RefreshCw, Trash2
} from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { useAuthStore } from '../store/useAuthStore';
import { fetchPdfs, PDFDocument } from '../lib/api';
import UpgradeModal from '../components/billing/UpgradeModal';

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

      <div className="min-h-[calc(100vh-64px)] bg-[#F8FAFC] text-slate-900 pb-16 pt-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto">
          
          {/* Header Banner */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-50 border border-blue-200/60 text-blue-700 text-xs font-semibold uppercase tracking-wider mb-3 shadow-xs">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Production AI Presentation Engine</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900">
              Transform Ideas into Professional Slide Decks
            </h1>
            <p className="mt-2 text-slate-600 text-base max-w-2xl mx-auto">
              Choose your knowledge source, exact slide count, and design system. Rendered with clean Python typography.
            </p>
          </div>

          {/* Main Creator Card */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8 mb-8 transition-all">
            <form onSubmit={handleGenerate}>
              
              {/* 1. Topic Input */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-slate-800 mb-2">
                  Presentation Topic or Key Concept
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g., Cloud Computing Architecture: Distributed Systems at Scale"
                    disabled={generating}
                    className="w-full px-4 py-3.5 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/30 focus:border-blue-600 font-medium transition-colors text-base"
                  />
                  {topic && !generating && (
                    <button
                      type="button"
                      onClick={() => setTopic('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-sm p-1"
                    >
                      ✕
                    </button>
                  )}
                </div>

                {/* Quick Topic Suggestions */}
                <div className="mt-2.5 flex flex-wrap gap-2 items-center">
                  <span className="text-xs font-medium text-slate-500">Suggestions:</span>
                  {SUGGESTED_TOPICS.map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setTopic(t)}
                      className="text-xs px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors cursor-pointer"
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              {/* 2. Knowledge Source Selector */}
              <div className="mb-6 pt-4 border-t border-slate-100">
                <label className="block text-sm font-semibold text-slate-800 mb-2">
                  Knowledge Grounding Source
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {[
                    { type: 'general' as const, label: 'General Knowledge', icon: Globe, desc: 'AI subject knowledge' },
                    { type: 'uploaded_material' as const, label: 'My Uploaded Notes', icon: FileText, desc: 'Grounded in PDF/Notes' },
                    { type: 'uploaded_material_plus_web' as const, label: 'Document + Web', icon: Sparkles, desc: 'Document + Research' },
                  ].map((src) => (
                    <button
                      key={src.type}
                      type="button"
                      onClick={() => setSourceType(src.type)}
                      className={`flex flex-col text-left p-3.5 rounded-xl border transition-all cursor-pointer ${
                        sourceType === src.type
                          ? 'border-blue-600 bg-blue-50/50 ring-1 ring-blue-600 shadow-xs'
                          : 'border-slate-200 bg-white hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <src.icon className={`w-4 h-4 ${sourceType === src.type ? 'text-blue-600' : 'text-slate-500'}`} />
                        <span className="text-sm font-semibold text-slate-900">{src.label}</span>
                      </div>
                      <span className="text-xs text-slate-500">{src.desc}</span>
                    </button>
                  ))}
                </div>

                {/* If Uploaded Material Selected: Show Document Dropdown */}
                {sourceType !== 'general' && (
                  <div className="mt-3 p-3.5 bg-blue-50/60 border border-blue-200/80 rounded-xl">
                    <label className="block text-xs font-semibold text-blue-900 mb-1.5">
                      Select Source Document from Your Library:
                    </label>
                    {userPdfs.length > 0 ? (
                      <select
                        value={selectedPdfId}
                        onChange={(e) => setSelectedPdfId(e.target.value)}
                        className="w-full px-3 py-2 bg-white border border-blue-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
                      >
                        {userPdfs.map((pdf) => (
                          <option key={pdf.id} value={pdf.id}>
                            📄 {pdf.name} ({pdf.subject || 'General'}) — {pdf.page_count || 1} pages
                          </option>
                        ))}
                      </select>
                    ) : (
                      <p className="text-xs text-blue-800">
                        No uploaded PDFs found. You can upload a PDF in the Library or continue with General Knowledge.
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* 3. Exact Slide Count Selector (10..15) */}
              <div className="mb-6 pt-4 border-t border-slate-100">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-semibold text-slate-800">
                    Exact Slide Count
                  </label>
                  <span className="text-xs font-medium text-slate-500">
                    Guaranteed exact count ({slideCount} slides)
                  </span>
                </div>
                <div className="grid grid-cols-6 gap-2">
                  {SLIDE_COUNT_OPTIONS.map((num) => (
                    <button
                      key={num}
                      type="button"
                      onClick={() => setSlideCount(num)}
                      className={`py-2.5 rounded-xl border text-center font-bold text-sm transition-all cursor-pointer ${
                        slideCount === num
                          ? 'border-blue-600 bg-blue-600 text-white shadow-xs'
                          : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100'
                      }`}
                    >
                      {num} Slides
                    </button>
                  ))}
                </div>
              </div>

              {/* 4. Design Systems & Themes */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6 pt-4 border-t border-slate-100">
                
                {/* Design Template System */}
                <div>
                  <label className="block text-sm font-semibold text-slate-800 mb-2">
                    Design Template System
                  </label>
                  <div className="space-y-2">
                    {DESIGN_OPTIONS.map((d) => (
                      <button
                        key={d.value}
                        type="button"
                        onClick={() => setDesign(d.value)}
                        className={`w-full flex items-center justify-between p-3 rounded-xl border text-left transition-all cursor-pointer ${
                          design === d.value
                            ? 'border-blue-600 bg-blue-50/50 ring-1 ring-blue-600'
                            : 'border-slate-200 bg-white hover:border-slate-300'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <span className="text-lg">{d.icon}</span>
                          <div>
                            <p className="text-sm font-bold text-slate-900">{d.label}</p>
                            <p className="text-xs text-slate-500 line-clamp-1">{d.desc}</p>
                          </div>
                        </div>
                        {design === d.value && <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0" />}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Theme Palette & Audience */}
                <div>
                  <label className="block text-sm font-semibold text-slate-800 mb-2">
                    Color Theme Palette
                  </label>
                  <div className="grid grid-cols-2 gap-2 mb-4">
                    {THEME_OPTIONS.map((t) => (
                      <button
                        key={t.value}
                        type="button"
                        onClick={() => setThemeId(t.value)}
                        className={`flex items-center gap-2 p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                          themeId === t.value
                            ? 'border-blue-600 bg-blue-50/50 ring-1 ring-blue-600'
                            : 'border-slate-200 bg-white hover:border-slate-300'
                        }`}
                      >
                        <div className="flex -space-x-1 shrink-0">
                          {t.colors.map((c, ci) => (
                            <div key={ci} className="w-3.5 h-3.5 rounded-full border border-white" style={{ backgroundColor: c }} />
                          ))}
                        </div>
                        <span className="text-xs font-semibold text-slate-800 truncate">{t.label}</span>
                      </button>
                    ))}
                  </div>

                  {/* Audience & Language */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Target Audience</label>
                      <select
                        value={audience}
                        onChange={(e) => setAudience(e.target.value)}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      >
                        {AUDIENCE_OPTIONS.map((a) => (
                          <option key={a.value} value={a.value}>{a.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Language</label>
                      <select
                        value={language}
                        onChange={(e) => setLanguage(e.target.value)}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      >
                        {LANGUAGE_OPTIONS.map((l) => (
                          <option key={l.value} value={l.value}>{l.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
              </div>

              {/* 5. Pedagogical & Visual Toggles */}
              <div className="mb-8 pt-4 border-t border-slate-100">
                <label className="block text-sm font-semibold text-slate-800 mb-3">
                  Presentation Component Features
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {[
                    { label: 'System & Flow Diagrams', state: enableDiagrams, set: setEnableDiagrams },
                    { label: 'Selective AI Illustrations', state: enableImages, set: setEnableImages },
                    { label: 'Rich Speaker Notes', state: enableSpeakerNotes, set: setEnableSpeakerNotes },
                    { label: 'Document Source Citations', state: enableSources, set: setEnableSources },
                    { label: 'Real-World Case Examples', state: enableExamples, set: setEnableExamples },
                    { label: 'Interactive Final Quiz', state: enableQuiz, set: setEnableQuiz },
                  ].map((opt, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => opt.set(!opt.state)}
                      className={`flex items-center gap-2 p-2.5 rounded-lg border text-left text-xs font-semibold cursor-pointer transition-colors ${
                        opt.state
                          ? 'border-blue-200 bg-blue-50/70 text-blue-900'
                          : 'border-slate-200 bg-slate-50 text-slate-500 hover:bg-slate-100'
                      }`}
                    >
                      {opt.state ? (
                        <CheckSquare className="w-4 h-4 text-blue-600 shrink-0" />
                      ) : (
                        <Square className="w-4 h-4 text-slate-400 shrink-0" />
                      )}
                      <span className="truncate">{opt.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Submit Button */}
              <div>
                <button
                  type="submit"
                  disabled={generating || !topic.trim()}
                  className="w-full py-4 px-6 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-base shadow-sm hover:shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {generating ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span>{stageMessage || 'Generating Presentation...'}</span>
                    </>
                  ) : (
                    <>
                      <Presentation className="w-5 h-5" />
                      <span>Generate {slideCount}-Slide Presentation (.pptx)</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* ═══════════ LIVE GENERATION PROGRESS TRACKER ═══════════ */}
          {generating && (
            <div className="bg-white rounded-2xl border border-blue-200 shadow-sm p-6 mb-8 text-center animate-pulse">
              <div className="flex items-center justify-between text-xs font-bold text-slate-500 mb-2">
                <span>STAGE {currentStage + 1} OF 4</span>
                <span className="text-blue-600">{progressPercent}% COMPLETE</span>
              </div>
              
              {/* Progress Bar */}
              <div className="w-full bg-slate-100 rounded-full h-2.5 mb-4 overflow-hidden">
                <div 
                  className="bg-blue-600 h-2.5 rounded-full transition-all duration-700 ease-out" 
                  style={{ width: `${progressPercent}%` }}
                />
              </div>

              <p className="text-base font-bold text-slate-900 mb-1">{stageMessage}</p>
              <p className="text-xs text-slate-500">Deterministic Python layout engine rendering 16:9 widescreen canvas...</p>
            </div>
          )}

          {/* ═══════════ ERROR STATE ═══════════ */}
          {errorMessage && !generating && (
            <div className="bg-red-50 border border-red-200 rounded-2xl p-6 mb-8 text-center">
              <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-2" />
              <h3 className="text-base font-bold text-red-900 mb-1">Presentation Generation Failed</h3>
              <p className="text-xs text-red-700 mb-4">{errorMessage}</p>
              <button
                onClick={handleGenerate}
                className="px-4 py-2 bg-red-600 text-white rounded-lg text-xs font-bold hover:bg-red-700 inline-flex items-center gap-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5" /> Try Again
              </button>
            </div>
          )}

          {/* ═══════════ PRESENTATION READY VIEW ═══════════ */}
          {status === 'ready' && downloadUrl && (
            <div className="bg-white rounded-2xl border border-emerald-200 shadow-sm p-6 sm:p-8 mb-8">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
                <div>
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs font-bold mb-2">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Presentation Ready
                  </div>
                  <h2 className="text-2xl font-bold text-slate-900">{resultTitle}</h2>
                  <p className="text-sm text-slate-500 mt-1">
                    {finalSlideCount} Slides  •  {design.toUpperCase()} Template  •  16:9 Widescreen (.pptx)
                  </p>
                </div>
                <a
                  href={downloadUrl}
                  download={`${resultTitle.replace(/[^a-zA-Z0-9]/g, '_')}.pptx`}
                  className="px-6 py-3.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-sm shadow-sm flex items-center justify-center gap-2 shrink-0 transition-colors"
                >
                  <Download className="w-4 h-4" /> Download PPTX
                </a>
              </div>

              {/* Takeaways Preview */}
              {resultTakeaways.length > 0 && (
                <div className="mt-6">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Core Deck Takeaways</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {resultTakeaways.map((t, i) => (
                      <div key={i} className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-700 flex items-start gap-2">
                        <span className="text-emerald-500 font-bold">✦</span>
                        <span>{t}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ═══════════ PREVIOUS DECKS HISTORY ═══════════ */}
          {deckHistory.length > 0 && (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-slate-500" /> Recent Presentations ({deckHistory.length})
                </h3>
              </div>
              <div className="divide-y divide-slate-100">
                {deckHistory.map((deck) => (
                  <div key={deck.id} className="py-3.5 flex items-center justify-between gap-4">
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-slate-800 truncate">{deck.topic}</p>
                      <p className="text-xs text-slate-400">
                        {deck.slide_count || 12} slides  •  {deck.audience || 'University'}  •  {new Date(deck.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => handleDeleteDeck(deck.id)}
                        className="p-2 text-slate-400 hover:text-red-600 rounded-lg hover:bg-slate-50 transition-colors"
                        title="Delete presentation"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

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
