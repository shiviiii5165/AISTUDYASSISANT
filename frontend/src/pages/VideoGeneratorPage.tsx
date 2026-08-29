import React, { useState, useEffect, useRef } from 'react';
import { 
  PlayCircle, Clock, Globe, Filter, Sparkles, ChevronDown, 
  Loader2, BookOpen, Brain, HelpCircle, Lightbulb, FileText, 
  RotateCcw, CheckCircle2, AlertCircle, Layers, Video, 
  Download, RefreshCw, Sliders, Palette, ShieldCheck, Film, 
  Plus, Edit3, ChevronRight, CheckSquare, Search,
  BarChart2, Zap, Bookmark, Volume2, Maximize2, Trash2, ArrowRight
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { useAuthStore } from '../store/useAuthStore';
import { fetchPdfs, type PDFDocument } from '../lib/api';
import GreetingHeader from '../components/GreetingHeader';

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
  { value: 'quick', label: 'Quick', desc: 'Fast rendering with Python diagrams & stock footage' },
  { value: 'standard', label: 'Standard', desc: 'Balanced mix of graphics, stock, and AI visuals' },
  { value: 'premium', label: 'Premium', desc: 'Higher fidelity visuals, richer transitions & AI motion' },
];

const STYLE_OPTIONS = [
  { value: 'academic', label: 'Academic Clean', desc: 'Structured university lecture style' },
  { value: 'modern_explainer', label: 'Modern Explainer', desc: 'Fast-paced, high visual clarity' },
  { value: 'technical', label: 'Technical Deep Dive', desc: 'Architectures, terminal code & equations' },
  { value: 'visual_learning', label: 'Visual Learning', desc: 'Diagrams, mental models & concept flows' },
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

const VideoGeneratorPage: React.FC = () => {
  const [topic, setTopic] = useState('');
  const [level, setLevel] = useState('B.Tech');
  const [duration, setDuration] = useState('5');
  const [language, setLanguage] = useState('English');
  const [quality, setQuality] = useState('standard');
  const [style, setStyle] = useState('academic');
  const [aiIntensity, setAiIntensity] = useState<'minimal' | 'balanced' | 'maximum'>('balanced');
  
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
  const handleGenerate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!topic.trim() || generating) return;

    setGenerating(true);
    setLessonId(null);
    setStoryboard(null);
    setFinalVideoUrl(null);
    setMetrics(null);
    setError(null);
    setStatus('processing');
    setActiveSceneIndex(0);

    const token = useAuthStore.getState().session?.access_token;
    const apiUrl = import.meta.env.VITE_API_URL || '';

    try {
      const sourceIds = (sourceType === 'pdf' && selectedPdfId) ? [selectedPdfId] : [];

      const res = await fetch(`${apiUrl}/api/lessons/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          topic: topic.trim(),
          level,
          duration,
          language: language.toLowerCase(),
          style,
          quality,
          source_type: sourceType,
          source_ids: sourceIds,
          youtube_url: youtubeUrl.trim() || null,
        }),
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

      alert(`Scene ${sceneId} updated and final video re-composed successfully!`);
    } catch (err: any) {
      console.error(err);
      alert('Could not regenerate scene. Please try again.');
    } finally {
      setRegeneratingScene(false);
    }
  };

  const toggleBookmark = (idx: number) => {
    setBookmarks(prev => 
      prev.includes(idx) ? prev.filter(i => i !== idx) : [...prev, idx]
    );
  };

  const getVisualBadge = (type: string) => {
    switch (type) {
      case 'python_graphics': return { label: '⚡ Python Graphics', bg: 'bg-blue-50 text-blue-700 border-blue-200' };
      case 'stock_video': return { label: '🎬 Stock Footage', bg: 'bg-emerald-50 text-emerald-700 border-emerald-200' };
      case 'ai_image': return { label: '🎨 AI Concept Art', bg: 'bg-purple-50 text-purple-700 border-purple-200' };
      case 'ai_video': return { label: '✨ AI Motion Video', bg: 'bg-amber-50 text-amber-700 border-amber-200' };
      default: return { label: '📌 Visual Slide', bg: 'bg-slate-50 text-slate-700 border-slate-200' };
    }
  };

  return (
    <AppLayout title="AI Educational Video Studio">
      <SEO 
        title="AI Video Studio — TeachGenie" 
        description="Transform any topic, notes, or YouTube link into an educational video with Python graphics, TTS narration, and captions."
      />

      <div className="min-h-[calc(100vh-64px)] bg-surface text-ink pb-24 pt-12 px-4 sm:px-6 lg:px-8 overflow-hidden font-sans">
        <div className="max-w-4xl mx-auto">

          {/* Header — Greeting (Director Genie) */}
          <GreetingHeader
            subtitle="Ready to direct your next video lesson?"
            avatarImageSrc="/director-genie.png"
            avatarGlowVariant="spotlight"
          />

          <form onSubmit={handleGenerate} className="space-y-8 mt-8">

            {/* Topic Input — Pill Search Bar */}
            <div className="max-w-3xl mx-auto w-full">
              <div className="relative group shadow-sm hover:shadow-md transition-shadow rounded-full bg-surface-card border border-border-soft p-2 flex items-center">
                <button type="button" className="p-3 text-ink-muted hover:text-genie-amber transition-colors ml-1 pointer-events-none">
                  <Film className="w-6 h-6" />
                </button>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => {
                    setTopic(e.target.value);
                    parseNaturalLanguagePrompt(e.target.value);
                  }}
                  placeholder="e.g. Operating Systems Deadlock in Hinglish for B.Tech (5 min)..."
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
            </div>

            {/* Knowledge Source Selector — Large Cards */}
            <div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {[
                  { type: 'topic' as const, label: 'General Knowledge', icon: Globe, desc: 'AI subject knowledge' },
                  { type: 'pdf' as const, label: 'My Uploaded Notes', icon: FileText, desc: 'Grounded in PDF/Notes' },
                  { type: 'youtube' as const, label: 'YouTube Video', icon: Video, desc: 'Learn from a video URL' },
                ].map((src) => {
                  const isSelected = sourceType === src.type;
                  return (
                    <button
                      key={src.type}
                      type="button"
                      onClick={() => setSourceType(src.type)}
                      className={`flex flex-col text-left p-5 rounded-2xl border transition-all cursor-pointer relative overflow-hidden ${
                        isSelected
                          ? 'border-genie-amber bg-genie-amber-soft ring-1 ring-genie-amber shadow-sm'
                          : 'border-border-soft bg-surface-card hover:border-genie-amber/40 shadow-sm hover:shadow-md'
                      }`}
                    >
                      <div className="flex items-center gap-3 mb-2">
                        <div className={`p-2 rounded-full ${isSelected ? 'bg-white text-genie-amber' : 'bg-surface text-ink-muted'}`}>
                          <src.icon className="w-5 h-5" />
                        </div>
                        <span className={`text-sm font-semibold ${isSelected ? 'text-amber-800' : 'text-ink'}`}>{src.label}</span>
                      </div>
                      <span className={`text-xs ml-[3.25rem] ${isSelected ? 'text-amber-700/80' : 'text-ink-muted'}`}>{src.desc}</span>
                    </button>
                  );
                })}
              </div>

              {/* PDF Selector Dropdown */}
              {sourceType === 'pdf' && (
                <div className="mt-4 p-5 bg-genie-amber-soft/50 border border-genie-amber/20 rounded-2xl">
                  <label className="block text-sm font-semibold text-amber-800 mb-2">
                    Select Source Document from Your Library
                  </label>
                  {userPdfs.length > 0 ? (
                    <select
                      value={selectedPdfId}
                      onChange={(e) => setSelectedPdfId(e.target.value)}
                      className="w-full px-4 py-3 bg-surface-card border border-border-soft rounded-full text-sm text-ink focus:outline-none focus:ring-2 focus:ring-genie-amber font-medium shadow-sm appearance-none cursor-pointer"
                    >
                      {userPdfs.map(p => (
                        <option key={p.id} value={p.id}>📄 {p.name} ({p.page_count || 1} pages)</option>
                      ))}
                    </select>
                  ) : (
                    <p className="text-sm text-amber-700/80 bg-white/50 p-3 rounded-xl">
                      No uploaded PDFs found. Upload a PDF in the Library or continue with General Knowledge.
                    </p>
                  )}
                </div>
              )}

              {/* YouTube URL Input */}
              {sourceType === 'youtube' && (
                <div className="mt-4 p-5 bg-genie-amber-soft/50 border border-genie-amber/20 rounded-2xl">
                  <label className="block text-sm font-semibold text-amber-800 mb-2">
                    Enter Public YouTube Video URL
                  </label>
                  <input
                    type="url"
                    value={youtubeUrl}
                    onChange={(e) => setYoutubeUrl(e.target.value)}
                    placeholder="https://www.youtube.com/watch?v=..."
                    className="w-full px-4 py-3 bg-surface-card border border-border-soft rounded-full text-sm text-ink focus:outline-none focus:ring-2 focus:ring-genie-amber font-medium shadow-sm"
                  />
                </div>
              )}
            </div>

            {/* Duration, Quality, Style, Language — Styled Selects */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {/* Duration */}
              <div className="relative group">
                <label className="block text-sm font-semibold text-ink-muted uppercase tracking-wider mb-2">Duration</label>
                <select
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                  className="appearance-none w-full pl-5 pr-10 py-3 bg-surface-card border border-border-soft rounded-full text-sm font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-genie-amber shadow-sm cursor-pointer"
                >
                  {DURATION_OPTIONS.map(d => (
                    <option key={d.val} value={d.val}>{d.label}</option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 text-ink-muted absolute right-4 bottom-3.5 pointer-events-none group-hover:text-ink" />
              </div>

              {/* Quality Tier */}
              <div className="relative group">
                <label className="block text-sm font-semibold text-ink-muted uppercase tracking-wider mb-2">Quality</label>
                <select
                  value={quality}
                  onChange={(e) => setQuality(e.target.value)}
                  className="appearance-none w-full pl-5 pr-10 py-3 bg-surface-card border border-border-soft rounded-full text-sm font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-genie-amber shadow-sm cursor-pointer"
                >
                  {QUALITY_OPTIONS.map(q => (
                    <option key={q.value} value={q.value}>{q.label}</option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 text-ink-muted absolute right-4 bottom-3.5 pointer-events-none group-hover:text-ink" />
              </div>

              {/* Style */}
              <div className="relative group">
                <label className="block text-sm font-semibold text-ink-muted uppercase tracking-wider mb-2">Style</label>
                <select
                  value={style}
                  onChange={(e) => setStyle(e.target.value)}
                  className="appearance-none w-full pl-5 pr-10 py-3 bg-surface-card border border-border-soft rounded-full text-sm font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-genie-amber shadow-sm cursor-pointer"
                >
                  {STYLE_OPTIONS.map(s => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 text-ink-muted absolute right-4 bottom-3.5 pointer-events-none group-hover:text-ink" />
              </div>

              {/* Language */}
              <div className="relative group">
                <label className="block text-sm font-semibold text-ink-muted uppercase tracking-wider mb-2">Language</label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="appearance-none w-full pl-5 pr-10 py-3 bg-surface-card border border-border-soft rounded-full text-sm font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-genie-amber shadow-sm cursor-pointer"
                >
                  {LANGUAGE_OPTIONS.map(l => (
                    <option key={l} value={l}>{l}</option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 text-ink-muted absolute right-4 bottom-3.5 pointer-events-none group-hover:text-ink" />
              </div>
            </div>

            {/* Submit Button */}
            <div className="pt-4 flex justify-center">
              <button
                type="submit"
                disabled={generating || !topic.trim()}
                className="w-full max-w-md py-5 px-8 rounded-full font-bold text-lg shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed bg-gradient-to-r from-genie-amber to-amber-600 text-white border-0 cursor-pointer"
              >
                {generating ? (
                  <>
                    <Loader2 className="w-6 h-6 animate-spin" />
                    <span>Compiling Video...</span>
                  </>
                ) : (
                  <>
                    <Film className="w-6 h-6" />
                    <span>Create {duration}-Minute Video Lesson</span>
                  </>
                )}
              </button>
            </div>

          </form>

        {/* Progress State */}
        {generating && (
          <div className="w-full max-w-xl mx-auto bg-surface-card border border-genie-amber/30 rounded-2xl p-8 text-center shadow-md mt-12 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-genie-amber-soft/20 via-amber-50/20 to-genie-amber-soft/20 animate-pulse" />
            <div className="relative z-10">
              <Loader2 className="w-8 h-8 text-genie-amber animate-spin mx-auto mb-3" />
              <h3 className="text-lg font-bold text-ink mb-1">Compiling Your Video Lesson...</h3>
              <p className="text-sm text-ink-muted mb-4">
                Planning storyboard, generating diagrams, synthesizing TTS narration & compiling FFmpeg stream.
              </p>
              <div className="w-full bg-surface rounded-full h-3 overflow-hidden border border-border-soft">
                <div className="bg-gradient-to-r from-genie-amber to-amber-500 h-full rounded-full w-2/3 animate-pulse" />
              </div>
            </div>
          </div>
        )}

        {/* ═══════════ VIDEO STUDIO RESULTS ═══════════ */}
        {storyboard && (
          <div ref={resultsRef} className="w-full max-w-5xl bg-surface-card border border-border-soft rounded-2xl p-6 sm:p-8 shadow-sm mt-12 mb-10">
            
            {/* Header / Download */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100 mb-6">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="px-2.5 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 text-[11px] font-bold">
                    ✓ Ready to Watch
                  </span>
                  <span className="text-xs font-semibold text-slate-400 capitalize">{storyboard.style} Style</span>
                </div>
                <h2 className="text-xl sm:text-2xl font-bold text-slate-900">{storyboard.topic}</h2>
              </div>

              {finalVideoUrl && (
                <a
                  href={finalVideoUrl}
                  download={`${storyboard.topic.replace(/[^a-zA-Z0-9]/g, '_')}.mp4`}
                  className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-xs shadow-xs flex items-center justify-center gap-2 transition-colors cursor-pointer shrink-0"
                >
                  <Download className="w-4 h-4" /> Download MP4 Video
                </a>
              )}
            </div>

            {/* Navigation Tabs */}
            <div className="flex items-center gap-2 border-b border-slate-100 pb-3 mb-6 overflow-x-auto">
              {[
                { id: 'studio' as const, label: 'Video Studio & Timeline', icon: PlayCircle },
                { id: 'transcript' as const, label: 'Transcript & Search', icon: FileText },
                { id: 'notes' as const, label: 'Lesson Notes & Takeaways', icon: BookOpen },
                { id: 'telemetry' as const, label: 'Telemetry & Cost KPI', icon: BarChart2 },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-colors whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'bg-blue-50 text-blue-700 border border-blue-200'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <tab.icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>

            {/* TAB: STUDIO */}
            {activeTab === 'studio' && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                
                {/* Scene List Timeline */}
                <div className="lg:col-span-1 space-y-2 max-h-[500px] overflow-y-auto pr-1">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Scene Timeline ({storyboard.scenes.length} Scenes)</p>
                  </div>
                  {storyboard.scenes.map((s, i) => {
                    const badge = getVisualBadge(s.visual_type);
                    const isCurrent = i === activeSceneIndex;
                    const isBookmarked = bookmarks.includes(i);

                    return (
                      <div
                        key={s.scene_id}
                        onClick={() => setActiveSceneIndex(i)}
                        className={`p-3 rounded-xl border transition-all cursor-pointer relative ${
                          isCurrent
                            ? 'border-blue-600 bg-blue-50/70 shadow-xs'
                            : 'border-slate-200 bg-white hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="font-bold text-slate-900 truncate max-w-[130px]">{i + 1}. {s.caption || s.purpose}</span>
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] text-slate-400 font-semibold">{s.duration}s</span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleBookmark(i);
                              }}
                              className="text-slate-400 hover:text-amber-500"
                            >
                              <Bookmark className={`w-3.5 h-3.5 ${isBookmarked ? 'text-amber-500 fill-amber-500' : ''}`} />
                            </button>
                          </div>
                        </div>
                        <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold border ${badge.bg}`}>
                          {badge.label}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {/* Active Scene Detail & Inspector Drawer */}
                <div className="lg:col-span-2 bg-slate-50 border border-slate-200 rounded-xl p-5">
                  {storyboard.scenes[activeSceneIndex] && (() => {
                    const sc = storyboard.scenes[activeSceneIndex];
                    const badge = getVisualBadge(sc.visual_type);

                    return (
                      <div>
                        <div className="flex items-center justify-between gap-2 mb-3">
                          <div className="flex items-center gap-2">
                            <span className="w-6 h-6 rounded-lg bg-blue-600 text-white font-bold text-xs flex items-center justify-center">
                              {activeSceneIndex + 1}
                            </span>
                            <h3 className="font-bold text-sm text-slate-900">{sc.caption || sc.purpose}</h3>
                          </div>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${badge.bg}`}>
                            {badge.label}
                          </span>
                        </div>

                        {/* Narration Script */}
                        <div className="bg-white border border-slate-200 rounded-xl p-4 mb-4">
                          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">🎙️ Narration Track</p>
                          <p className="text-sm text-slate-800 leading-relaxed font-medium">{sc.narration}</p>
                        </div>

                        {/* Visual Content Specification */}
                        {sc.visual_spec && (
                          <div className="bg-white border border-slate-200 rounded-xl p-4 mb-4">
                            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">📊 Scene Visual Breakdown</p>
                            {sc.visual_spec.title && (
                              <p className="text-xs font-bold text-slate-900 mb-1">{sc.visual_spec.title}</p>
                            )}
                            {sc.visual_spec.bullets && sc.visual_spec.bullets.length > 0 && (
                              <ul className="text-xs text-slate-600 space-y-1 list-disc pl-4">
                                {sc.visual_spec.bullets.map((b, bi) => (
                                  <li key={bi}>{b}</li>
                                ))}
                              </ul>
                            )}
                          </div>
                        )}

                        {/* Scene Regeneration Action */}
                        <div className="flex flex-wrap items-center gap-2">
                          <button
                            onClick={() => handleRegenerateScene(sc.scene_id)}
                            disabled={regeneratingScene}
                            className="px-4 py-2 bg-white hover:bg-slate-100 border border-slate-200 text-slate-800 rounded-xl font-bold text-xs shadow-xs flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                          >
                            {regeneratingScene ? <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-600" /> : <RefreshCw className="w-3.5 h-3.5 text-blue-600" />}
                            <span>Regenerate Scene {activeSceneIndex + 1}</span>
                          </button>
                        </div>
                      </div>
                    );
                  })()}
                </div>

              </div>
            )}

            {/* TAB: TRANSCRIPT & SEARCH */}
            {activeTab === 'transcript' && (
              <div className="space-y-4 mb-8">
                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="text"
                    value={transcriptSearch}
                    onChange={(e) => setTranscriptSearch(e.target.value)}
                    placeholder="Search video transcript (e.g. congestion, slow start, lock)..."
                    className="w-full pl-9 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>

                <div className="space-y-2 max-h-[400px] overflow-y-auto">
                  {storyboard.scenes
                    .filter(s => !transcriptSearch || s.narration.toLowerCase().includes(transcriptSearch.toLowerCase()))
                    .map((s, i) => (
                      <div
                        key={s.scene_id}
                        onClick={() => {
                          setActiveSceneIndex(i);
                          setActiveTab('studio');
                        }}
                        className="p-3 bg-slate-50 hover:bg-blue-50/50 border border-slate-200 rounded-xl cursor-pointer transition-colors"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[11px] font-bold text-blue-600">Scene {i + 1}</span>
                          <span className="text-[10px] text-slate-400">({s.duration}s)</span>
                        </div>
                        <p className="text-xs text-slate-700 leading-relaxed">{s.narration}</p>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* TAB: TELEMETRY & COST KPI */}
            {activeTab === 'telemetry' && metrics && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl">
                  <p className="text-[11px] font-bold text-slate-400 uppercase mb-1">Total Duration</p>
                  <p className="text-lg font-extrabold text-slate-900">{metrics.total_duration_sec}s</p>
                </div>
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl">
                  <p className="text-[11px] font-bold text-slate-400 uppercase mb-1">AI Video Generated</p>
                  <p className="text-lg font-extrabold text-blue-600">{metrics.ai_video_seconds}s</p>
                </div>
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl">
                  <p className="text-[11px] font-bold text-slate-400 uppercase mb-1">AI Generation Ratio</p>
                  <p className="text-lg font-extrabold text-emerald-600">{(metrics.ai_generation_ratio * 100).toFixed(1)}%</p>
                </div>
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl">
                  <p className="text-[11px] font-bold text-slate-400 uppercase mb-1">Est. Cost / Min</p>
                  <p className="text-lg font-extrabold text-slate-900">${metrics.cost_per_minute_usd}</p>
                </div>
              </div>
            )}

            {/* TAB: SUMMARY NOTES */}
            {activeTab === 'notes' && (
              <div className="p-5 bg-slate-50 border border-slate-200 rounded-xl space-y-4">
                <div>
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2">Learning Objectives</h4>
                  <ul className="text-xs text-slate-700 space-y-1 list-disc pl-4">
                    {storyboard.learning_objectives.map((obj, i) => (
                      <li key={i}>{obj}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-1.5">Educational Synthesis</h4>
                  <p className="text-xs text-slate-700 leading-relaxed">{storyboard.summary_notes}</p>
                </div>
              </div>
            )}

          </div>
        )}

        {/* ═══════════ RECENT VIDEOS ═══════════ */}
        {pastLessons.length > 0 && !generating && !lessonId && (
          <div className="bg-surface-card rounded-2xl border border-border-soft p-6 shadow-sm mt-12">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Clock className="w-4 h-4 text-slate-500" /> Recent Videos ({pastLessons.length})
              </h3>
            </div>
            <div className="divide-y divide-slate-100">
              {pastLessons.map((lesson) => (
                <div key={lesson.id} className="py-3.5 flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-slate-800 truncate">{lesson.topic}</p>
                    <p className="text-xs text-slate-400">
                      {lesson.level || 'B.Tech'}  •  {lesson.language || 'English'}  •  {new Date(lesson.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {lesson.download_url && (
                      <a
                        href={lesson.download_url}
                        download
                        className="p-2 text-slate-400 hover:text-blue-600 rounded-lg hover:bg-slate-50 transition-colors"
                        title="Download video"
                      >
                        <Download className="w-4 h-4" />
                      </a>
                    )}
                    <button
                      onClick={() => handleDeleteLesson(lesson.id)}
                      className="p-2 text-slate-400 hover:text-red-600 rounded-lg hover:bg-slate-50 transition-colors"
                      title="Delete video"
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
    </AppLayout>
  );
};

export default VideoGeneratorPage;
