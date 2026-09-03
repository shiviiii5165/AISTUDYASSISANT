import React, { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import {
  PlayCircle, Clock, Globe, Loader2, BookOpen, FileText,
  CheckCircle2, AlertCircle, Video, Download, RefreshCw, Film,
  Search, BarChart2, Bookmark, Trash2, ArrowRight, X,
} from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { useAuthStore } from '../store/useAuthStore';
import { fetchPdfs, type PDFDocument } from '../lib/api';
import GreetingHeader from '../components/GreetingHeader';
import Loader from '../components/Loader';

// ═══════════════════════════════════════════════════════════════════════════
// TYPES & CONFIG
// ═══════════════════════════════════════════════════════════════════════════

interface SourceRef {
  source_type?: string;
  page_number?: number;
  slide_number?: number;
  timestamp_start?: number;
  timestamp_end?: number;
  snippet?: string;
}

interface SceneSpec {
  scene_id: string;
  order: number;
  concept_id: string;
  purpose: string;
  duration: number;
  narration: string;
  visual_type: string;
  visual_spec: {
    title?: string;
    bullets?: string[];
    formula?: string;
    diagram_type?: string;
    stock_keywords?: string[];
  };
  caption: string;
  ai_video_score?: number;
  source_refs?: SourceRef[];
  status: string;
}

interface VideoMetrics {
  total_duration_sec: number;
  ai_video_seconds: number;
  ai_image_count: number;
  stock_media_count: number;
  python_graphics_count: number;
  tts_characters: number;
  cost_per_minute_usd: number;
  ai_generation_ratio: number;
  render_time_sec: number;
}

interface StoryboardData {
  topic: string;
  style: string;
  language: string;
  total_duration: number;
  scenes: SceneSpec[];
  learning_objectives: string[];
  summary_notes: string;
}

const QUALITY_OPTIONS = [
  { value: 'quick', label: 'Quick', desc: 'Fast rendering with diagrams and stock footage' },
  { value: 'standard', label: 'Standard', desc: 'Balanced mix of graphics, stock, and AI visuals' },
  { value: 'premium', label: 'Premium', desc: 'Higher fidelity visuals and richer transitions' },
];

const STYLE_OPTIONS = [
  { value: 'academic', label: 'Academic Clean', desc: 'Structured university lecture style' },
  { value: 'modern_explainer', label: 'Modern Explainer', desc: 'Fast-paced, high visual clarity' },
  { value: 'technical', label: 'Technical Deep Dive', desc: 'Architectures, code and equations' },
  { value: 'visual_learning', label: 'Visual Learning', desc: 'Diagrams, mental models and concept flows' },
  { value: 'cinematic', label: 'Documentary', desc: 'Rich b-roll and narrative storytelling' },
];

const DURATION_OPTIONS = [
  { val: '1', label: '1 min' },
  { val: '3', label: '3 min' },
  { val: '5', label: '5 min' },
  { val: '10', label: '10 min' },
  { val: '15', label: '15 min' },
];

const LEVEL_OPTIONS = ['Class 9', 'Class 10', 'Class 11', 'Class 12', 'B.Tech', 'Undergrad', 'Graduate'];
const LANGUAGE_OPTIONS = ['English', 'Hindi', 'Hinglish'];

/** Visual-type labels. Emoji removed; every badge carries a word. */
const VISUAL_BADGES: Record<string, string> = {
  python_graphics: 'Rendered graphics',
  stock_video: 'Stock footage',
  ai_image: 'AI concept art',
  ai_video: 'AI motion video',
};

const VideoGeneratorPage: React.FC = () => {
  const location = useLocation();
  const presetConfig = location.state?.presetConfig;

  const [topic, setTopic] = useState(presetConfig?.topic || '');
  const [level, setLevel] = useState(presetConfig?.level || 'B.Tech');
  const [duration, setDuration] = useState(presetConfig?.target_duration_minutes?.toString() || '5');
  const [language, setLanguage] = useState(
    presetConfig?.language 
      ? presetConfig.language.charAt(0).toUpperCase() + presetConfig.language.slice(1) 
      : 'English'
  );
  const [quality, setQuality] = useState('standard');
  const [style, setStyle] = useState('academic');

  // Knowledge Sources
  const [sourceType, setSourceType] = useState('topic');
  const [selectedPdfId, setSelectedPdfId] = useState('');
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [userPdfs, setUserPdfs] = useState<PDFDocument[]>([]);

  // Generation State
  const [generating, setGenerating] = useState(false);
  const [regeneratingScene, setRegeneratingScene] = useState(false);
  const [lessonId, setLessonId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [storyboard, setStoryboard] = useState<StoryboardData | null>(null);
  const [finalVideoUrl, setFinalVideoUrl] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<VideoMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  /* Replaces two window.alert() calls in handleRegenerateScene. Same
     trigger and message, rendered inline and announced politely. */
  const [sceneNotice, setSceneNotice] = useState<string | null>(null);

  // Studio & Navigation State
  const [activeSceneIndex, setActiveSceneIndex] = useState(0);
  const [activeTab, setActiveTab] = useState<'studio' | 'transcript' | 'notes' | 'telemetry'>('studio');
  const [transcriptSearch, setTranscriptSearch] = useState('');
  const [bookmarks, setBookmarks] = useState<number[]>([]);
  const [pastLessons, setPastLessons] = useState<any[]>([]);

  const resultsRef = useRef<HTMLDivElement>(null);

  // Natural Language Prompt Parser
  const parseNaturalLanguagePrompt = (text: string) => {
    const lower = text.toLowerCase();

    // Duration detection
    if (lower.includes('1 minute') || lower.includes('1 min') || lower.includes('1m')) setDuration('1');
    else if (lower.includes('3 minute') || lower.includes('3 min') || lower.includes('3m')) setDuration('3');
    else if (lower.includes('10 minute') || lower.includes('10 min') || lower.includes('10m')) setDuration('10');
    else if (lower.includes('15 minute') || lower.includes('15 min') || lower.includes('15m')) setDuration('15');
    else if (lower.includes('5 minute') || lower.includes('5 min') || lower.includes('5m')) setDuration('5');

    // Language detection
    if (lower.includes('hinglish')) setLanguage('Hinglish');
    else if (lower.includes('hindi')) setLanguage('Hindi');
    else if (lower.includes('english')) setLanguage('English');

    // Level detection
    if (lower.includes('b.tech') || lower.includes('btech') || lower.includes('engineering')) setLevel('B.Tech');
    else if (lower.includes('class 12') || lower.includes('12th')) setLevel('Class 12');
    else if (lower.includes('class 10') || lower.includes('10th')) setLevel('Class 10');

    // Source detection
    if (lower.includes('notes') || lower.includes('pdf')) setSourceType('pdf');
    else if (lower.includes('youtube')) setSourceType('youtube');
  };

  // Load User PDFs & Past Lessons
  useEffect(() => {
    const loadData = async () => {
      try {
        const token = useAuthStore.getState().session?.access_token;
        const pdfs = await fetchPdfs();
        setUserPdfs(pdfs.filter(p => p.status === 'ready'));

        const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lessons/`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setPastLessons(data);
        }
      } catch (e) {
        console.error("Failed to load initial data", e);
      }
    };
    loadData();
  }, []);

  // Poll for Video Status
  useEffect(() => {
    let intervalId: any;
    if (lessonId && (status === 'processing' || status === 'planning' || status === 'assets' || status === 'audio')) {
      intervalId = setInterval(async () => {
        try {
          const token = useAuthStore.getState().session?.access_token;
          const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lessons/${lessonId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          const data = await res.json();

          setStatus(data.status);

          if (data.status === 'ready' && data.lesson_json) {
            setStoryboard(data.lesson_json);
            if (data.final_video_url) setFinalVideoUrl(data.final_video_url);
            if (data.metrics) setMetrics(data.metrics);
            setGenerating(false);
            clearInterval(intervalId);
            setTimeout(() => {
              resultsRef.current?.scrollIntoView({ behavior: 'smooth' });
            }, 300);
          } else if (data.status === 'failed') {
            setError(data.error_message || 'Video generation failed.');
            setGenerating(false);
            clearInterval(intervalId);
          }
        } catch (e) {
          console.error("Polling error", e);
        }
      }, 3000);
    }
    return () => clearInterval(intervalId);
  }, [lessonId, status]);

  const handleDeleteLesson = async (id: string) => {
    // Native confirm kept deliberately: deletion is irreversible and the
    // guarantee must stay exactly as reliable as before.
    if (!window.confirm("Are you sure you want to delete this video lesson?")) return;
    const token = useAuthStore.getState().session?.access_token;
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lessons/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        setPastLessons(prev => prev.filter(l => l.id !== id));
      }
    } catch (e) {
      console.error("Failed to delete lesson", e);
    }
  };

  // Start Generation
  const handleGenerate = async (e?: React.FormEvent, overridePayload?: any) => {
    if (e) e.preventDefault();
    if ((!topic.trim() && !overridePayload) || generating) return;

    setGenerating(true);
    setLessonId(null);
    setStoryboard(null);
    setFinalVideoUrl(null);
    setMetrics(null);
    setError(null);
    setSceneNotice(null);
    setStatus('processing');
    setActiveSceneIndex(0);

    const token = useAuthStore.getState().session?.access_token;
    const apiUrl = import.meta.env.VITE_API_URL || '';

    try {
      const sourceIds = (sourceType === 'pdf' && selectedPdfId) ? [selectedPdfId] : [];

      const payload = overridePayload || {
        topic: topic.trim(),
        level,
        duration,
        language: language.toLowerCase(),
        style,
        quality,
        source_type: sourceType,
        source_ids: sourceIds,
        youtube_url: youtubeUrl.trim() || null,
      };

      const res = await fetch(`${apiUrl}/api/lessons/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error('Failed to initiate video generation');
      const data = await res.json();
      setLessonId(data.lesson_id);

    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to start video generation');
      setGenerating(false);
      setStatus('failed');
    }
  };

  // Regenerate Single Scene
  const handleRegenerateScene = async (sceneId: string) => {
    if (!lessonId || regeneratingScene) return;

    setRegeneratingScene(true);
    setSceneNotice(null);
    const token = useAuthStore.getState().session?.access_token;
    const apiUrl = import.meta.env.VITE_API_URL || '';

    try {
      const res = await fetch(`${apiUrl}/api/lessons/${lessonId}/regenerate-scene`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ scene_id: sceneId }),
      });

      if (!res.ok) throw new Error('Scene regeneration failed');
      const data = await res.json();
      if (data.final_video_url) setFinalVideoUrl(data.final_video_url);

      setSceneNotice(`Scene ${sceneId} updated and the final video was recomposed.`);
    } catch (err: any) {
      console.error(err);
      setSceneNotice('Could not regenerate scene. Please try again.');
    } finally {
      setRegeneratingScene(false);
    }
  };

  const toggleBookmark = (idx: number) => {
    setBookmarks(prev =>
      prev.includes(idx) ? prev.filter(i => i !== idx) : [...prev, idx]
    );
  };

  const visualBadge = (type: string) => VISUAL_BADGES[type] || 'Visual slide';

  const selectClass =
    'w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2.5 text-sm font-medium text-[var(--text-primary)] focus:border-[var(--accent-green)] focus:outline-none';

  const TABS = [
    { id: 'studio' as const, label: 'Scenes', icon: PlayCircle },
    { id: 'transcript' as const, label: 'Transcript', icon: FileText },
    { id: 'notes' as const, label: 'Lesson notes', icon: BookOpen },
    { id: 'telemetry' as const, label: 'Cost and usage', icon: BarChart2 },
  ];

  return (
    <AppLayout title="Video Generator">
      <SEO
        title="AI Video Studio | TeachGenie"
        description="Transform any topic, notes, or YouTube link into an educational video with generated graphics, narration, and captions."
      />

      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">

        <div className="mb-8">
          <GreetingHeader
            subtitle="Turn a topic, your notes, or a video link into a narrated lesson."
            avatarImageSrc="/assets/genie-default.png"
            avatarGlowVariant="spotlight"
          />
        </div>

        <form onSubmit={handleGenerate} className="space-y-6">

          {/* Topic */}
          <div>
            <label htmlFor="video-topic" className="mb-2 block text-sm font-semibold text-[var(--text-primary)]">
              Video topic
            </label>
            <div className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-2 focus-within:border-[var(--accent-green)]">
              <Film className="ml-2 h-5 w-5 shrink-0 text-[var(--text-secondary)]" aria-hidden="true" />
              <input
                id="video-topic"
                type="text"
                value={topic}
                onChange={(e) => {
                  setTopic(e.target.value);
                  parseNaturalLanguagePrompt(e.target.value);
                }}
                placeholder="Operating systems deadlock in Hinglish for B.Tech, 5 min"
                disabled={generating}
                className="min-w-0 flex-1 border-none bg-transparent px-2 py-2.5 text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none"
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
                aria-label="Create video lesson"
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-green)] text-white transition-colors hover:bg-[var(--accent-green-hover)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {generating ? (
                  <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
                ) : (
                  <ArrowRight className="h-5 w-5" aria-hidden="true" />
                )}
              </button>
            </div>
            <p className="mt-1.5 text-xs text-[var(--text-secondary)]">
              Mentioning a length, language or level in the topic sets those options automatically.
            </p>
          </div>

          {/* Knowledge source */}
          <fieldset>
            <legend className="mb-2 text-sm font-semibold text-[var(--text-primary)]">
              Knowledge source
            </legend>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {[
                { type: 'topic' as const, label: 'General knowledge', icon: Globe, desc: 'Model subject knowledge' },
                { type: 'pdf' as const, label: 'My uploaded notes', icon: FileText, desc: 'Grounded in your documents' },
                { type: 'youtube' as const, label: 'YouTube video', icon: Video, desc: 'Learn from a video URL' },
              ].map((src) => {
                const isSelected = sourceType === src.type;
                return (
                  <button
                    key={src.type}
                    type="button"
                    onClick={() => setSourceType(src.type)}
                    aria-pressed={isSelected}
                    className={`flex flex-col rounded-xl border p-4 text-left transition-colors ${
                      isSelected
                        ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)]'
                        : 'border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)]'
                    }`}
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
                <label htmlFor="video-source-pdf" className="mb-2 block text-sm font-semibold text-[var(--text-primary)]">
                  Source document
                </label>
                {userPdfs.length > 0 ? (
                  <select
                    id="video-source-pdf"
                    value={selectedPdfId}
                    onChange={(e) => setSelectedPdfId(e.target.value)}
                    className={selectClass}
                  >
                    {userPdfs.map(p => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.page_count || 1} pages)
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

            {sourceType === 'youtube' && (
              <div className="mt-3 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
                <label htmlFor="video-youtube" className="mb-2 block text-sm font-semibold text-[var(--text-primary)]">
                  Public YouTube video URL
                </label>
                <input
                  id="video-youtube"
                  type="url"
                  value={youtubeUrl}
                  onChange={(e) => setYoutubeUrl(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v="
                  className={selectClass}
                />
              </div>
            )}
          </fieldset>

          {/* Options */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <label htmlFor="video-duration" className="mb-1.5 block text-sm font-semibold text-[var(--text-primary)]">
                Duration
              </label>
              <select
                id="video-duration"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                className={selectClass}
              >
                {DURATION_OPTIONS.map(d => (
                  <option key={d.val} value={d.val}>{d.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="video-quality" className="mb-1.5 block text-sm font-semibold text-[var(--text-primary)]">
                Quality
              </label>
              <select
                id="video-quality"
                value={quality}
                onChange={(e) => setQuality(e.target.value)}
                className={selectClass}
              >
                {QUALITY_OPTIONS.map(q => (
                  <option key={q.value} value={q.value}>{q.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="video-style" className="mb-1.5 block text-sm font-semibold text-[var(--text-primary)]">
                Style
              </label>
              <select
                id="video-style"
                value={style}
                onChange={(e) => setStyle(e.target.value)}
                className={selectClass}
              >
                {STYLE_OPTIONS.map(s => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="video-language" className="mb-1.5 block text-sm font-semibold text-[var(--text-primary)]">
                Language
              </label>
              <select
                id="video-language"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className={selectClass}
              >
                {LANGUAGE_OPTIONS.map(l => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="video-level" className="mb-1.5 block text-sm font-semibold text-[var(--text-primary)]">
              Level
            </label>
            <select
              id="video-level"
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              className={`${selectClass} sm:max-w-xs`}
            >
              {LEVEL_OPTIONS.map(l => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            disabled={generating || !topic.trim()}
            className="flex w-full items-center justify-center gap-2.5 rounded-xl bg-[var(--accent-green)] px-8 py-3.5 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)] active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50"
          >
            {generating ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
                <span>Compiling video</span>
              </>
            ) : (
              <>
                <Film className="h-5 w-5" aria-hidden="true" />
                <span>Create {duration} minute video lesson</span>
              </>
            )}
          </button>
        </form>

        {/* Generation wait — full Loader component */}
        {generating && (
          <div
            className="mt-8 flex items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] py-12 shadow-bento"
            aria-live="polite"
          >
            <Loader
              title="Compiling your video lesson"
              subtitle="Planning the storyboard, building visuals and recording narration. This can take several minutes."
              size="md"
            />
          </div>
        )}

        {/* Error */}
        {error && !generating && (
          <div role="alert" className="mt-8 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-5">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-700" aria-hidden="true" />
            <div>
              <h2 className="font-display text-base font-semibold text-red-900">
                Video generation failed
              </h2>
              <p className="mt-1 text-sm text-red-800">{error}</p>
            </div>
          </div>
        )}

        {/* ═══════════ VIDEO STUDIO RESULTS ═══════════ */}
        {storyboard && (
          <div
            ref={resultsRef}
            className="mb-10 mt-8 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5 sm:p-6"
          >

            <div className="mb-6 flex flex-col gap-4 border-b border-[var(--border)] pb-5 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <div className="mb-1.5 flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 rounded-md bg-[var(--accent-green-light)] px-2 py-0.5 text-[11px] font-semibold text-[var(--accent-green-text)]">
                    <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                    Ready to watch
                  </span>
                  <span className="text-xs font-medium capitalize text-[var(--text-secondary)]">
                    {storyboard.style} style
                  </span>
                </div>
                <h2 className="font-display text-xl font-bold text-[var(--text-primary)] sm:text-2xl">
                  {storyboard.topic}
                </h2>
              </div>

              {finalVideoUrl && (
                <a
                  href={finalVideoUrl}
                  download={`${storyboard.topic.replace(/[^a-zA-Z0-9]/g, '_')}.mp4`}
                  className="flex shrink-0 items-center justify-center gap-2 rounded-xl bg-[var(--accent-green)] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)]"
                >
                  <Download className="h-4 w-4" aria-hidden="true" />
                  Download MP4
                </a>
              )}
            </div>

            {sceneNotice && (
              <p
                aria-live="polite"
                className="mb-4 rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2 text-sm text-[var(--text-secondary)]"
              >
                {sceneNotice}
              </p>
            )}

            {/* Tabs */}
            <div role="tablist" aria-label="Video details" className="mb-5 flex items-center gap-1.5 overflow-x-auto border-b border-[var(--border)] pb-3">
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  id={`tab-${tab.id}`}
                  aria-selected={activeTab === tab.id}
                  aria-controls={`panel-${tab.id}`}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    activeTab === tab.id
                      ? 'bg-[var(--accent-green-light)] text-[var(--accent-green-text)]'
                      : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  <tab.icon className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>

            {/* TAB: STUDIO */}
            {activeTab === 'studio' && (
              <div id="panel-studio" role="tabpanel" aria-labelledby="tab-studio" className="mb-6 grid grid-cols-1 gap-5 lg:grid-cols-3">

                <div className="lg:col-span-1">
                  <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                    Scene timeline, <span className="tabular-nums">{storyboard.scenes.length}</span> scenes
                  </h3>
                  <ul className="max-h-[500px] space-y-2 overflow-y-auto pr-1">
                    {storyboard.scenes.map((s, i) => {
                      const isCurrent = i === activeSceneIndex;
                      const isBookmarked = bookmarks.includes(i);

                      return (
                        <li key={s.scene_id} className="relative">
                          {/* Real button: the scene list was previously a div
                              with onClick and unreachable by keyboard. */}
                          <button
                            type="button"
                            onClick={() => setActiveSceneIndex(i)}
                            aria-current={isCurrent ? 'true' : undefined}
                            className={`w-full rounded-xl border p-3 pr-9 text-left transition-colors ${
                              isCurrent
                                ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)]'
                                : 'border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)]'
                            }`}
                          >
                            <span className="mb-1 flex items-center justify-between gap-2 text-xs">
                              <span className="truncate font-semibold text-[var(--text-primary)]">
                                {i + 1}. {s.caption || s.purpose}
                              </span>
                              <span className="shrink-0 text-[10px] font-semibold tabular-nums text-[var(--text-secondary)]">
                                {s.duration}s
                              </span>
                            </span>
                            <span className="inline-block rounded border border-[var(--border)] bg-[var(--bg-secondary)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-secondary)]">
                              {visualBadge(s.visual_type)}
                            </span>
                          </button>
                          <button
                            type="button"
                            onClick={() => toggleBookmark(i)}
                            aria-pressed={isBookmarked}
                            aria-label={`${isBookmarked ? 'Remove bookmark from' : 'Bookmark'} scene ${i + 1}`}
                            className="absolute right-2 top-2 rounded p-1 text-[var(--text-muted)] transition-colors hover:text-[var(--accent-green-text)]"
                          >
                            <Bookmark
                              className={`h-3.5 w-3.5 ${isBookmarked ? 'fill-[var(--accent-green-text)] text-[var(--accent-green-text)]' : ''}`}
                              aria-hidden="true"
                            />
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>

                {/* Active scene */}
                <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5 lg:col-span-2">
                  {storyboard.scenes[activeSceneIndex] && (() => {
                    const sc = storyboard.scenes[activeSceneIndex];

                    return (
                      <div>
                        <div className="mb-3 flex items-center justify-between gap-2">
                          <div className="flex min-w-0 items-center gap-2">
                            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-green)] text-xs font-bold tabular-nums text-white">
                              {activeSceneIndex + 1}
                            </span>
                            <h3 className="truncate font-display text-sm font-semibold text-[var(--text-primary)]">
                              {sc.caption || sc.purpose}
                            </h3>
                          </div>
                          <span className="shrink-0 rounded border border-[var(--border)] bg-[var(--bg-card)] px-2 py-0.5 text-[10px] font-semibold text-[var(--text-secondary)]">
                            {visualBadge(sc.visual_type)}
                          </span>
                        </div>

                        <div className="mb-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4">
                          <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                            Narration
                          </h4>
                          <p className="text-sm leading-relaxed text-[var(--text-primary)]">
                            {sc.narration}
                          </p>
                        </div>

                        {sc.visual_spec && (
                          <div className="mb-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4">
                            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                              Scene visuals
                            </h4>
                            {sc.visual_spec.title && (
                              <p className="mb-1 text-xs font-semibold text-[var(--text-primary)]">
                                {sc.visual_spec.title}
                              </p>
                            )}
                            {sc.visual_spec.bullets && sc.visual_spec.bullets.length > 0 && (
                              <ul className="list-disc space-y-1 pl-4 text-xs text-[var(--text-secondary)]">
                                {sc.visual_spec.bullets.map((b, bi) => (
                                  <li key={bi}>{b}</li>
                                ))}
                              </ul>
                            )}
                          </div>
                        )}

                        <button
                          type="button"
                          onClick={() => handleRegenerateScene(sc.scene_id)}
                          disabled={regeneratingScene}
                          className="flex items-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-2 text-xs font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)] disabled:opacity-50"
                        >
                          {regeneratingScene ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                          ) : (
                            <RefreshCw className="h-3.5 w-3.5 text-[var(--accent-green-text)]" aria-hidden="true" />
                          )}
                          <span>Regenerate scene {activeSceneIndex + 1}</span>
                        </button>
                      </div>
                    );
                  })()}
                </div>

              </div>
            )}

            {/* TAB: TRANSCRIPT */}
            {activeTab === 'transcript' && (
              <div id="panel-transcript" role="tabpanel" aria-labelledby="tab-transcript" className="mb-6 space-y-4">
                <div className="relative">
                  <Search
                    className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-[var(--text-muted)]"
                    aria-hidden="true"
                  />
                  <label htmlFor="transcript-search" className="sr-only">Search transcript</label>
                  <input
                    id="transcript-search"
                    type="text"
                    value={transcriptSearch}
                    onChange={(e) => setTranscriptSearch(e.target.value)}
                    placeholder="Search the transcript"
                    className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] py-2.5 pl-9 pr-4 text-sm font-medium text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent-green)] focus:outline-none"
                  />
                </div>

                <ul className="max-h-[400px] space-y-2 overflow-y-auto">
                  {storyboard.scenes
                    .filter(s => !transcriptSearch || s.narration.toLowerCase().includes(transcriptSearch.toLowerCase()))
                    .map((s, i) => (
                      <li key={s.scene_id}>
                        <button
                          type="button"
                          onClick={() => {
                            setActiveSceneIndex(i);
                            setActiveTab('studio');
                          }}
                          className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-left transition-colors hover:bg-[var(--bg-hover)]"
                        >
                          <span className="mb-1 flex items-center gap-2">
                            <span className="text-[11px] font-semibold text-[var(--accent-green-text)]">
                              Scene {i + 1}
                            </span>
                            <span className="text-[10px] tabular-nums text-[var(--text-muted)]">
                              {s.duration}s
                            </span>
                          </span>
                          <span className="block text-xs leading-relaxed text-[var(--text-secondary)]">
                            {s.narration}
                          </span>
                        </button>
                      </li>
                    ))}
                </ul>
              </div>
            )}

            {/* TAB: COST AND USAGE */}
            {activeTab === 'telemetry' && metrics && (
              <dl
                id="panel-telemetry"
                role="tabpanel"
                aria-labelledby="tab-telemetry"
                className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4"
              >
                {[
                  { label: 'Total duration', value: `${metrics.total_duration_sec}s` },
                  { label: 'AI video generated', value: `${metrics.ai_video_seconds}s` },
                  { label: 'AI generation ratio', value: `${(metrics.ai_generation_ratio * 100).toFixed(1)}%` },
                  { label: 'Est. cost per minute', value: `$${metrics.cost_per_minute_usd}` },
                ].map((m) => (
                  <div key={m.label} className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
                    <dt className="mb-1 text-[11px] font-semibold uppercase text-[var(--text-secondary)]">
                      {m.label}
                    </dt>
                    <dd className="font-display text-lg font-bold tabular-nums text-[var(--text-primary)]">
                      {m.value}
                    </dd>
                  </div>
                ))}
              </dl>
            )}

            {/* TAB: NOTES */}
            {activeTab === 'notes' && (
              <div
                id="panel-notes"
                role="tabpanel"
                aria-labelledby="tab-notes"
                className="space-y-4 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5"
              >
                <div>
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--text-primary)]">
                    Learning objectives
                  </h3>
                  <ul className="list-disc space-y-1 pl-4 text-xs text-[var(--text-secondary)]">
                    {storyboard.learning_objectives.map((obj, i) => (
                      <li key={i}>{obj}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-[var(--text-primary)]">
                    Summary
                  </h3>
                  <p className="text-xs leading-relaxed text-[var(--text-secondary)]">
                    {storyboard.summary_notes}
                  </p>
                </div>
              </div>
            )}

          </div>
        )}

        {/* ═══════════ RECENT VIDEOS ═══════════ */}
        {pastLessons.length > 0 && !generating && !lessonId && (
          <section className="mt-8 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
            <h2 className="mb-3 flex items-center gap-2 font-display text-base font-semibold text-[var(--text-primary)]">
              <Clock className="h-4 w-4 text-[var(--accent-green-text)]" aria-hidden="true" />
              Recent videos
              <span className="rounded-full border border-[var(--border)] bg-[var(--bg-secondary)] px-2 py-0.5 text-xs font-medium tabular-nums text-[var(--text-secondary)]">
                {pastLessons.length}
              </span>
            </h2>
            <ul className="divide-y divide-[var(--border)]">
              {pastLessons.map((lesson) => (
                <li key={lesson.id} className="flex items-center justify-between gap-4 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-[var(--text-primary)]">
                      {lesson.topic}
                    </p>
                    <p className="text-xs text-[var(--text-secondary)]">
                      {lesson.level || 'B.Tech'}, {lesson.language || 'English'},{' '}
                      {new Date(lesson.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    {lesson.download_url && (
                      <a
                        href={lesson.download_url}
                        download
                        aria-label={`Download ${lesson.topic}`}
                        className="rounded-lg p-2 text-[var(--text-secondary)] transition-colors hover:bg-[var(--accent-green-light)] hover:text-[var(--accent-green-text)]"
                      >
                        <Download className="h-4 w-4" aria-hidden="true" />
                      </a>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDeleteLesson(lesson.id)}
                      aria-label={`Delete ${lesson.topic}`}
                      className="rounded-lg p-2 text-[var(--text-secondary)] transition-colors hover:bg-red-50 hover:text-red-700"
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

      </div>
    </AppLayout>
  );
};

export default VideoGeneratorPage;
