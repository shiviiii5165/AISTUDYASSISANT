import React, { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import {
  PlayCircle, Clock, Globe, Loader2, BookOpen, FileText,
  CheckCircle2, AlertCircle, Video, Download, RefreshCw, Film,
  Search, BarChart2, Bookmark, Trash2, ArrowRight, X, MessageSquare,
  HelpCircle, Sparkles, Send, Check, CornerDownRight, Lightbulb
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
  concept_name?: string;
  purpose: string;
  duration: number;
  narration: string;
  visual_strategy?: string;
  visual_type?: string;
  visual_spec: {
    title?: string;
    subtitle?: string;
    bullets?: string[];
    formula?: string;
    diagram_type?: string;
    stock_keywords?: string[];
    steps?: string[];
  };
  caption: string;
  ai_video_score?: number;
  source_refs?: SourceRef[];
  status: string;
}

export interface QualityScoreData {
  total_score: number;
  passed_gates: boolean;
  concept_coverage: number;
  prerequisite_order: number;
  visual_relevance: number;
  example_quality: number;
  misconception_handling: number;
  language_naturalness: number;
  narration_visual_sync: number;
  doubt_context_readiness: number;
}

export interface RepairLogData {
  pre_repair_score: number;
  post_repair_score: number;
  score_delta: number;
  repair_actions: string[];
}

export interface TelemetryData {
  intent_parse_ms: number;
  domain_detection_ms: number;
  curriculum_ms: number;
  storyboard_ms: number;
  visual_render_ms: number;
  tts_ms: number;
  composition_ms: number;
  qa_ms: number;
  repair_ms: number;
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
  quality_score?: QualityScoreData;
  repair_log?: RepairLogData;
  telemetry?: TelemetryData;
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

interface MasteryCheckData {
  target_concept_id: string;
  question: string;
  options: string[];
  correct_answer_index: number;
  explanation: string;
  evaluated?: boolean;
  selected_index?: number;
  is_correct?: boolean;
  feedback?: string;
}

interface DoubtMessage {
  id: string;
  sender: 'user' | 'tutor';
  text: string;
  timestamp: number;
  strategy_used?: string;
  mini_diagram?: string;
  step_trace?: string[];
  mastery_check?: MasteryCheckData;
  referential_anchor?: {
    label?: string;
    anchor_type?: string;
    content_snippet?: string;
    timestamp_sec?: number;
  };
}

const QUALITY_OPTIONS = [
  { value: 'quick', label: 'Quick', desc: 'Fast rendering with diagrams and clear visuals' },
  { value: 'standard', label: 'Standard', desc: 'Balanced mix of graphics and dynamic visual flows' },
  { value: 'premium', label: 'Premium', desc: 'Higher fidelity visuals and richer transitions' },
];

const STYLE_OPTIONS = [
  { value: 'academic', label: 'Academic Clean', desc: 'Structured university lecture style' },
  { value: 'modern_explainer', label: 'Modern Explainer', desc: 'Fast-paced, high visual clarity' },
  { value: 'technical', label: 'Technical Deep Dive', desc: 'Architectures, code and equations' },
  { value: 'visual_learning', label: 'Visual Learning', desc: 'Diagrams, mental models and concept flows' },
  { value: 'cinematic', label: 'Documentary', desc: 'Rich narrative storytelling' },
];

const DURATION_OPTIONS = [
  { val: '1', label: '1 min' },
  { val: '3', label: '3 min' },
  { val: '5', label: '5 min' },
  { val: '7', label: '7 min' },
  { val: '10', label: '10 min' },
];

const LEVEL_OPTIONS = ['Class 9', 'Class 10', 'Class 11', 'Class 12', 'B.Tech', 'Undergrad', 'Graduate'];
const LANGUAGE_OPTIONS = ['English', 'Hindi', 'Hinglish'];

const QUICK_DOUBT_BUTTONS = [
  { label: 'Explain simpler', query: 'Please explain this in simpler terms' },
  { label: 'Show visually', query: 'Can you break this down visually step by step?' },
  { label: 'Give another example', query: 'Can you give another real-world example of this?' },
  { label: 'Explain from basics', query: 'Explain the core prerequisite basics behind this' },
  { label: 'Acha 20 wala?', query: 'acha 20 wala?' },
  { label: 'Upar wali step', query: 'upar wali step smjha do' },
  { label: 'Uske pehle wala', query: 'nahi uske pehle wala' },
];

const formatTimestamp = (sec: number) => {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
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
      : 'Hinglish'
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
  const [sceneNotice, setSceneNotice] = useState<string | null>(null);

  // Player & Interactive Video Teacher State
  const [activeSceneIndex, setActiveSceneIndex] = useState(0);
  const [currentPlaybackTime, setCurrentPlaybackTime] = useState(0.0);
  const [activeTab, setActiveTab] = useState<'doubt' | 'studio' | 'transcript' | 'notes' | 'telemetry'>('doubt');
  const [transcriptSearch, setTranscriptSearch] = useState('');
  const [bookmarks, setBookmarks] = useState<number[]>([]);
  const [pastLessons, setPastLessons] = useState<any[]>([]);

  // Ask Your Doubt State
  const [doubtMessages, setDoubtMessages] = useState<DoubtMessage[]>([]);
  const [doubtSessionId, setDoubtSessionId] = useState<string | null>(null);
  const [currentDoubtInput, setCurrentDoubtInput] = useState('');
  const [askingDoubt, setAskingDoubt] = useState(false);
  const [triedStrategies, setTriedStrategies] = useState<string[]>([]);

  // Learner Mastery & Telemetry State (V2.1 Hardening)
  const [masteryProfile, setMasteryProfile] = useState<any>(null);
  const [showDevTelemetry, setShowDevTelemetry] = useState(false);
  const lastSyncTimeRef = useRef<number>(0);
  const lastActiveSceneRef = useRef<number>(-1);

  const videoPlayerRef = useRef<HTMLVideoElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const doubtBottomRef = useRef<HTMLDivElement>(null);

  // Throttled / Event-Driven Playback Progress Sync (Decision #2)
  const syncProgress = async (t: number, eventType: string) => {
    if (!lessonId) return;
    try {
      const token = useAuthStore.getState().session?.access_token;
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lessons/${lessonId}/progress`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ timestamp: t, event_type: eventType })
      });
      if (res.ok) {
        const data = await res.json();
        setMasteryProfile(data);
        lastSyncTimeRef.current = t;
      }
    } catch (e) {
      // Non-blocking background telemetry sync
    }
  };

  // Natural Language Prompt Parser
  const parseNaturalLanguagePrompt = (text: string) => {
    const lower = text.toLowerCase();

    if (lower.includes('1 minute') || lower.includes('1 min') || lower.includes('1m')) setDuration('1');
    else if (lower.includes('3 minute') || lower.includes('3 min') || lower.includes('3m')) setDuration('3');
    else if (lower.includes('7 minute') || lower.includes('7 min') || lower.includes('7m')) setDuration('7');
    else if (lower.includes('10 minute') || lower.includes('10 min') || lower.includes('10m')) setDuration('10');
    else if (lower.includes('5 minute') || lower.includes('5 min') || lower.includes('5m')) setDuration('5');

    if (lower.includes('hinglish')) setLanguage('Hinglish');
    else if (lower.includes('hindi')) setLanguage('Hindi');
    else if (lower.includes('english')) setLanguage('English');

    if (lower.includes('b.tech') || lower.includes('btech') || lower.includes('engineering')) setLevel('B.Tech');
    else if (lower.includes('class 12') || lower.includes('12th')) setLevel('Class 12');
    else if (lower.includes('class 10') || lower.includes('10th')) setLevel('Class 10');
    else if (lower.includes('class 9') || lower.includes('9th')) setLevel('Class 9');

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

  // Video Timeupdate & Active Scene Synchronization (Throttled, Decision #2)
  const handleTimeUpdate = () => {
    if (!videoPlayerRef.current || !storyboard || !storyboard.scenes) return;
    const t = videoPlayerRef.current.currentTime;
    setCurrentPlaybackTime(t);

    let accum = 0;
    let sceneIdx = 0;
    for (let i = 0; i < storyboard.scenes.length; i++) {
      accum += storyboard.scenes[i].duration;
      if (t <= accum) {
        sceneIdx = i;
        break;
      }
    }
    setActiveSceneIndex(sceneIdx);

    // Event-driven sync: scene-boundary or throttled 12s interval (Decision #2)
    const isBoundary = sceneIdx !== lastActiveSceneRef.current && lastActiveSceneRef.current !== -1;
    const isThrottled = Math.abs(t - lastSyncTimeRef.current) >= 12;

    if (isBoundary) {
      lastActiveSceneRef.current = sceneIdx;
      syncProgress(t, 'scene_boundary');
    } else if (isThrottled) {
      syncProgress(t, 'throttled_interval');
    }

    if (lastActiveSceneRef.current === -1) {
      lastActiveSceneRef.current = sceneIdx;
    }
  };

  const seekToScene = (index: number) => {
    if (!videoPlayerRef.current || !storyboard) return;
    let seekTime = 0;
    for (let i = 0; i < index; i++) {
      seekTime += storyboard.scenes[i].duration;
    }
    videoPlayerRef.current.currentTime = seekTime;
    videoPlayerRef.current.play();
    setActiveSceneIndex(index);
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
    setDoubtMessages([]);
    setTriedStrategies([]);

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

  // Ask Your Doubt Submission
  const handleAskDoubt = async (customQuery?: string) => {
    const question = (customQuery || currentDoubtInput).trim();
    if (!question || !lessonId) return;

    const userMsg: DoubtMessage = {
      id: `user_${Date.now()}`,
      sender: 'user',
      text: question,
      timestamp: currentPlaybackTime,
    };
    setDoubtMessages(prev => [...prev, userMsg]);
    setCurrentDoubtInput('');
    setAskingDoubt(true);

    setTimeout(() => {
      doubtBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);

    try {
      const token = useAuthStore.getState().session?.access_token;
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lessons/${lessonId}/ask-doubt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          timestamp: currentPlaybackTime,
          question: question,
          doubt_session_id: doubtSessionId,
          tried_strategies: triedStrategies
        })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.doubt_session_id) {
          setDoubtSessionId(data.doubt_session_id);
        }
        if (data.strategy_used && !triedStrategies.includes(data.strategy_used)) {
          setTriedStrategies(prev => [...prev, data.strategy_used]);
        }
        const tutorMsg: DoubtMessage = {
          id: `tutor_${Date.now()}`,
          sender: 'tutor',
          text: data.explanation_markdown || 'Here is the step breakdown.',
          timestamp: currentPlaybackTime,
          strategy_used: data.strategy_used,
          mini_diagram: data.mini_diagram,
          step_trace: data.step_trace,
          mastery_check: data.mastery_check,
          referential_anchor: data.referential_anchor,
        };
        setDoubtMessages(prev => [...prev, tutorMsg]);
      } else {
        setDoubtMessages(prev => [...prev, {
          id: `tutor_${Date.now()}`,
          sender: 'tutor',
          text: `At timestamp ${formatTimestamp(currentPlaybackTime)}, the key focus is understanding the operational mechanism and ensuring references remain valid.`,
          timestamp: currentPlaybackTime
        }]);
      }
    } catch (e) {
      console.error("Doubt error:", e);
    } finally {
      setAskingDoubt(false);
      setTimeout(() => {
        doubtBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
  };

  // Evaluate Quick Mastery Check
  const handleAnswerMasteryCheck = async (msgId: string, check: MasteryCheckData, optionIdx: number) => {
    if (!lessonId) return;
    try {
      const token = useAuthStore.getState().session?.access_token;
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lessons/${lessonId}/mastery-check`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          target_concept_id: check.target_concept_id,
          question: check.question,
          options: check.options,
          correct_answer_index: check.correct_answer_index,
          selected_index: optionIdx,
          explanation: check.explanation
        })
      });

      const data = await res.json();
      setDoubtMessages(prev => prev.map(m => {
        if (m.id === msgId && m.mastery_check) {
          return {
            ...m,
            mastery_check: {
              ...m.mastery_check,
              evaluated: true,
              selected_index: optionIdx,
              is_correct: data.is_correct,
              feedback: data.feedback
            }
          };
        }
        return m;
      }));
    } catch (e) {
      console.error("Mastery check evaluation error:", e);
    }
  };

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
      setSceneNotice(`Scene ${sceneId} updated and recompiled into final video.`);
    } catch (err: any) {
      setSceneNotice('Could not regenerate scene. Please try again.');
    } finally {
      setRegeneratingScene(false);
    }
  };

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

  const toggleBookmark = (idx: number) => {
    setBookmarks(prev => prev.includes(idx) ? prev.filter(i => i !== idx) : [...prev, idx]);
  };

  const selectClass =
    'w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2.5 text-sm font-medium text-[var(--text-primary)] focus:border-[var(--accent-green)] focus:outline-none';

  const TABS = [
    { id: 'doubt' as const, label: 'Ask Your Doubt', icon: HelpCircle },
    { id: 'studio' as const, label: 'Scenes', icon: PlayCircle },
    { id: 'transcript' as const, label: 'Transcript', icon: FileText },
    { id: 'notes' as const, label: 'Lesson notes', icon: BookOpen },
    { id: 'telemetry' as const, label: 'Telemetry', icon: BarChart2 },
  ];

  const currentScene = storyboard?.scenes[activeSceneIndex];

  return (
    <AppLayout title="LearnByGenie AI Video Teacher">
      <SEO
        title="LearnByGenie AI Video Teacher | Interactive Pedagogical Learning"
        description="Create dynamic concept videos with animated visualizers and ask context-aware doubts directly while watching."
      />

      <div className="mx-auto max-w-6xl px-4 py-8">
        <GreetingHeader
          title="LearnByGenie AI Video Teacher"
          subtitle="Enter any topic. Get a pedagogically structured animated video lesson with integrated timestamp-aware doubt resolution."
        />

        {/* ═══════════ PROMPT CONFIGURATION FORM ═══════════ */}
        <form onSubmit={handleGenerate} className="mt-8 space-y-6 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-bento">
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
              What do you want to learn?
            </label>
            <div className="relative">
              <input
                type="text"
                value={topic}
                onChange={(e) => {
                  setTopic(e.target.value);
                  parseNaturalLanguagePrompt(e.target.value);
                }}
                placeholder="e.g. Teach Linked List to a B.Tech beginner in Hinglish in 5 minutes"
                className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-4 py-3.5 pr-10 text-base font-medium text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent-green)] focus:outline-none"
              />
              <Sparkles className="pointer-events-none absolute right-3.5 top-3.5 h-5 w-5 text-[var(--accent-green)]" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">Audience Level</label>
              <select value={level} onChange={(e) => setLevel(e.target.value)} className={selectClass}>
                {LEVEL_OPTIONS.map(lvl => <option key={lvl} value={lvl}>{lvl}</option>)}
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">Duration</label>
              <select value={duration} onChange={(e) => setDuration(e.target.value)} className={selectClass}>
                {DURATION_OPTIONS.map(d => <option key={d.val} value={d.val}>{d.label}</option>)}
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">Language</label>
              <select value={language} onChange={(e) => setLanguage(e.target.value)} className={selectClass}>
                {LANGUAGE_OPTIONS.map(l => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">Teaching Style</label>
              <select value={style} onChange={(e) => setStyle(e.target.value)} className={selectClass}>
                {STYLE_OPTIONS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </div>
          </div>

          <button
            type="submit"
            disabled={generating || !topic.trim()}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--accent-green)] py-3.5 text-sm font-bold text-white transition-all hover:bg-[var(--accent-green-hover)] disabled:opacity-50 shadow-md"
          >
            {generating ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Teaching in progress...</span>
              </>
            ) : (
              <>
                <Film className="h-5 w-5" />
                <span>Start Video Lesson</span>
              </>
            )}
          </button>
        </form>

        {/* ═══════════ GENERATION LOADER ═══════════ */}
        {generating && (
          <div className="mt-8 flex items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] py-12 shadow-bento">
            <Loader
              title="LearnByGenie is planning your lesson"
              subtitle="Constructing dynamic concept graph, rendering domain animations, and recording natural multilingual narration..."
              size="md"
            />
          </div>
        )}

        {/* ═══════════ ERROR ALERT ═══════════ */}
        {error && !generating && (
          <div role="alert" className="mt-8 flex items-start justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-5">
            <div className="flex items-start gap-3">
              <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-700" />
              <div>
                <h2 className="font-display text-base font-semibold text-red-900">Generation Notice</h2>
                <p className="mt-1 text-sm text-red-800">{error}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleGenerate}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-red-300 bg-red-100 px-3 py-1.5 text-xs font-semibold text-red-800 transition-colors hover:bg-red-200"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Retry Lesson</span>
            </button>
          </div>
        )}

        {/* ═══════════ INTERACTIVE VIDEO TEACHER RESULTS ═══════════ */}
        {storyboard && (
          <div ref={resultsRef} className="mb-10 mt-8 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-bento">

            {/* Video Header & Meta */}
            <div className="mb-6 flex flex-col gap-4 border-b border-[var(--border)] pb-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="mb-1.5 flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 rounded-md bg-[var(--accent-green-light)] px-2.5 py-0.5 text-xs font-semibold text-[var(--accent-green-text)]">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Interactive Lesson Ready
                  </span>
                  <span className="rounded-md border border-[var(--border)] bg-[var(--bg-secondary)] px-2 py-0.5 text-xs font-medium text-[var(--text-secondary)]">
                    {language} • {level}
                  </span>
                </div>
                <h2 className="font-display text-2xl font-bold text-[var(--text-primary)] sm:text-3xl">
                  {storyboard.topic}
                </h2>
              </div>

              {finalVideoUrl && (
                <a
                  href={finalVideoUrl}
                  download={`${storyboard.topic.replace(/[^a-zA-Z0-9]/g, '_')}.mp4`}
                  className="flex shrink-0 items-center justify-center gap-2 rounded-xl bg-[var(--accent-green)] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)] shadow-sm"
                >
                  <Download className="h-4 w-4" />
                  Download MP4
                </a>
              )}
            </div>

            {/* MAIN 16:9 INTERACTIVE VIDEO PLAYER */}
            <div className="relative mb-8 overflow-hidden rounded-2xl border border-[var(--border)] bg-black aspect-video w-full max-w-4xl mx-auto shadow-2xl">
              {finalVideoUrl ? (
                <video
                  ref={videoPlayerRef}
                  src={finalVideoUrl}
                  controls
                  playsInline
                  onTimeUpdate={handleTimeUpdate}
                  onPause={() => syncProgress(videoPlayerRef.current?.currentTime || 0, 'pause')}
                  onSeeked={() => syncProgress(videoPlayerRef.current?.currentTime || 0, 'seek')}
                  onEnded={() => syncProgress(videoPlayerRef.current?.currentTime || 0, 'complete')}
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="flex h-full w-full flex-col items-center justify-center bg-slate-900 text-white p-6">
                  <PlayCircle className="h-16 w-16 text-[var(--accent-green)] mb-3 opacity-90" />
                  <p className="text-base font-semibold">Video Ready to Stream</p>
                  <p className="text-xs text-slate-400 mt-1">Select any chapter below to begin playback.</p>
                </div>
              )}
            </div>

            {/* Quick Context Chip under player */}
            <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-4 py-3 text-xs">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[var(--accent-green)] text-[10px] font-bold text-white">
                  {activeSceneIndex + 1}
                </span>
                <span className="font-semibold text-[var(--text-primary)]">
                  Watching: {currentScene?.caption || currentScene?.purpose || 'Lesson'}
                </span>
                <span className="text-[var(--text-muted)]">
                  ({formatTimestamp(currentPlaybackTime)} / {formatTimestamp(storyboard.total_duration)})
                </span>

                {/* Concept Mastery Badge (Decision #1, #4) */}
                {currentScene && (
                  <div className="flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-2 py-0.5">
                    <span className="text-[10px] text-[var(--text-muted)]">Mastery:</span>
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                      masteryProfile?.concepts?.[currentScene.concept_id || currentScene.scene_id]?.state === 'MASTERED'
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : masteryProfile?.concepts?.[currentScene.concept_id || currentScene.scene_id]?.state === 'UNDERSTOOD'
                        ? 'bg-blue-500/20 text-blue-400'
                        : masteryProfile?.concepts?.[currentScene.concept_id || currentScene.scene_id]?.state === 'CONFUSED'
                        ? 'bg-amber-500/20 text-amber-400'
                        : masteryProfile?.concepts?.[currentScene.concept_id || currentScene.scene_id]?.state === 'PREREQUISITE_GAP'
                        ? 'bg-rose-500/20 text-rose-400'
                        : 'bg-slate-700/30 text-slate-300'
                    }`}>
                      {masteryProfile?.concepts?.[currentScene.concept_id || currentScene.scene_id]?.state || 'INTRODUCED'}
                    </span>
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2 text-[var(--text-muted)]">
                <Lightbulb className="h-3.5 w-3.5 text-amber-400" />
                <span>Have a doubt? Ask below — tutor knows exact scene context.</span>
              </div>
            </div>

            {/* Tab Navigation */}
            <div role="tablist" className="mb-6 flex items-center gap-2 overflow-x-auto border-b border-[var(--border)] pb-3">
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 whitespace-nowrap rounded-xl px-4 py-2 text-xs font-semibold transition-all ${
                    activeTab === tab.id
                      ? 'bg-[var(--accent-green-light)] text-[var(--accent-green-text)] shadow-sm'
                      : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'
                  }`}
                >
                  <tab.icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>

            {/* ═══════════ TAB: ASK YOUR DOUBT ═══════════ */}
            {activeTab === 'doubt' && (
              <div className="space-y-6">
                {/* Quick Query Prompts */}
                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                    Quick Clarifications for this scene
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {QUICK_DOUBT_BUTTONS.map((btn, bi) => (
                      <button
                        key={bi}
                        type="button"
                        onClick={() => handleAskDoubt(btn.query)}
                        disabled={askingDoubt}
                        className="rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] transition-colors hover:border-[var(--accent-green)] hover:bg-[var(--accent-green-light)] hover:text-[var(--accent-green-text)] disabled:opacity-50"
                      >
                        {btn.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Conversation Thread */}
                <div className="min-h-[220px] max-h-[480px] overflow-y-auto space-y-4 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
                  {doubtMessages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-10 text-center text-[var(--text-muted)]">
                      <MessageSquare className="h-10 w-10 mb-2 opacity-40" />
                      <p className="text-sm font-medium">No doubts asked yet</p>
                      <p className="text-xs max-w-sm mt-1">
                        Pause or play the video at any timestamp and ask questions like <em>"Ye step samajh nahi aaya"</em> or <em>"20.next ko 25 kyu kiya?"</em>.
                      </p>
                    </div>
                  ) : (
                    doubtMessages.map((msg) => (
                      <div key={msg.id} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
                        {/* Timestamp Chip */}
                        <span className="mb-1 text-[10px] text-[var(--text-muted)]">
                          {msg.sender === 'user' ? 'You' : 'LearnByGenie Tutor'} • At {formatTimestamp(msg.timestamp)}
                        </span>

                        {/* Message Box */}
                        <div className={`max-w-2xl rounded-2xl p-4 text-sm leading-relaxed ${
                          msg.sender === 'user'
                            ? 'bg-[var(--accent-green)] text-white'
                            : 'border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-primary)] shadow-sm'
                        }`}>
                          {msg.referential_anchor && (
                            <div className="mb-2 inline-flex items-center gap-1.5 rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700 border border-indigo-200">
                              <Sparkles className="h-3.5 w-3.5 text-indigo-600" />
                              <span>Referencing: {msg.referential_anchor.label || msg.referential_anchor.anchor_type}</span>
                            </div>
                          )}
                          <div className="whitespace-pre-wrap">{msg.text}</div>

                          {/* Mini Diagram (if present) */}
                          {msg.mini_diagram && (
                            <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-900 p-3 font-mono text-xs text-sky-300 border border-slate-700">
                              {msg.mini_diagram}
                            </pre>
                          )}

                          {/* Step Trace (if present) */}
                          {msg.step_trace && (
                            <div className="mt-3 space-y-1.5 border-t border-[var(--border)] pt-2.5">
                              <p className="text-xs font-semibold text-[var(--accent-green-text)]">Execution Trace:</p>
                              {msg.step_trace.map((st, si) => (
                                <div key={si} className="flex items-start gap-1.5 text-xs text-[var(--text-secondary)]">
                                  <CornerDownRight className="h-3.5 w-3.5 shrink-0 text-[var(--accent-green-text)] mt-0.5" />
                                  <span>{st}</span>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Quick Mastery Check Widget */}
                          {msg.mastery_check && (
                            <div className="mt-4 rounded-xl border border-[var(--accent-green)] bg-[var(--bg-secondary)] p-3.5">
                              <p className="text-xs font-bold text-[var(--accent-green-text)] uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                                <Sparkles className="h-3.5 w-3.5" /> Quick Mastery Check
                              </p>
                              <p className="text-xs font-semibold text-[var(--text-primary)] mb-2.5">
                                {msg.mastery_check.question}
                              </p>
                              <div className="space-y-1.5">
                                {msg.mastery_check.options.map((opt, oi) => {
                                  const isSelected = msg.mastery_check?.selected_index === oi;
                                  return (
                                    <button
                                      key={oi}
                                      type="button"
                                      disabled={msg.mastery_check?.evaluated}
                                      onClick={() => handleAnswerMasteryCheck(msg.id, msg.mastery_check!, oi)}
                                      className={`w-full rounded-lg border p-2 text-left text-xs font-medium transition-colors ${
                                        isSelected
                                          ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)] text-[var(--accent-green-text)]'
                                          : 'border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)]'
                                      }`}
                                    >
                                      {opt}
                                    </button>
                                  );
                                })}
                              </div>

                              {msg.mastery_check.evaluated && (
                                <p className={`mt-2.5 text-xs font-semibold ${msg.mastery_check.is_correct ? 'text-emerald-600' : 'text-amber-600'}`}>
                                  {msg.mastery_check.feedback}
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                  {askingDoubt && (
                    <div className="flex items-center gap-2 text-xs text-[var(--accent-green-text)] p-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Tutor is analyzing playback timestamp and resolving context...</span>
                    </div>
                  )}
                  <div ref={doubtBottomRef} />
                </div>

                {/* Input Bar */}
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleAskDoubt();
                  }}
                  className="flex items-center gap-2"
                >
                  <input
                    type="text"
                    value={currentDoubtInput}
                    onChange={(e) => setCurrentDoubtInput(e.target.value)}
                    placeholder="Ask about the part you're watching... (e.g. 20.next ko 25 kyu kiya?)"
                    className="flex-1 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-4 py-3 text-sm font-medium text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent-green)] focus:outline-none"
                  />
                  <button
                    type="submit"
                    disabled={!currentDoubtInput.trim() || askingDoubt}
                    className="flex shrink-0 items-center justify-center rounded-xl bg-[var(--accent-green)] px-5 py-3 text-sm font-bold text-white transition-colors hover:bg-[var(--accent-green-hover)] disabled:opacity-50"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </form>
              </div>
            )}

            {/* ═══════════ TAB: SCENES & TIMELINE ═══════════ */}
            {activeTab === 'studio' && (
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <div className="lg:col-span-1">
                  <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                    Chapters ({storyboard.scenes.length} Scenes)
                  </h3>
                  <ul className="max-h-[480px] space-y-2 overflow-y-auto pr-1">
                    {storyboard.scenes.map((s, i) => {
                      const isCurrent = i === activeSceneIndex;
                      return (
                        <li key={s.scene_id}>
                          <button
                            type="button"
                            onClick={() => seekToScene(i)}
                            className={`w-full rounded-xl border p-3 text-left transition-all ${
                              isCurrent
                                ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)] shadow-sm'
                                : 'border-[var(--border)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)]'
                            }`}
                          >
                            <div className="mb-1 flex items-center justify-between text-xs font-semibold">
                              <span className="truncate text-[var(--text-primary)]">
                                {i + 1}. {s.caption || s.purpose}
                              </span>
                              <span className="text-[10px] tabular-nums text-[var(--text-muted)]">
                                {s.duration}s
                              </span>
                            </div>
                            <span className="inline-block rounded border border-[var(--border)] bg-[var(--bg-card)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-secondary)]">
                              {s.visual_strategy || s.visual_type || 'archetype'}
                            </span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>

                {/* Active Scene Details */}
                <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5 lg:col-span-2">
                  {currentScene && (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-[var(--accent-green)] text-xs font-bold text-white">
                            {activeSceneIndex + 1}
                          </span>
                          <h3 className="font-display text-base font-bold text-[var(--text-primary)]">
                            {currentScene.caption || currentScene.purpose}
                          </h3>
                        </div>
                        <span className="rounded border border-[var(--border)] bg-[var(--bg-card)] px-2.5 py-1 text-xs font-medium text-[var(--text-secondary)]">
                          {currentScene.visual_strategy || currentScene.visual_type}
                        </span>
                      </div>

                      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4">
                        <h4 className="mb-1 text-xs font-bold uppercase text-[var(--text-secondary)]">Teacher Narration</h4>
                        <p className="text-sm leading-relaxed text-[var(--text-primary)]">{currentScene.narration}</p>
                      </div>

                      {currentScene.visual_spec && currentScene.visual_spec.bullets && (
                        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4">
                          <h4 className="mb-1.5 text-xs font-bold uppercase text-[var(--text-secondary)]">Visual Specifications</h4>
                          <ul className="list-disc space-y-1 pl-4 text-xs text-[var(--text-secondary)]">
                            {currentScene.visual_spec.bullets.map((b, bi) => <li key={bi}>{b}</li>)}
                          </ul>
                        </div>
                      )}

                      <button
                        type="button"
                        onClick={() => handleRegenerateScene(currentScene.scene_id)}
                        disabled={regeneratingScene}
                        className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-2 text-xs font-semibold text-[var(--text-primary)] hover:bg-[var(--bg-hover)] disabled:opacity-50"
                      >
                        {regeneratingScene ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5 text-[var(--accent-green-text)]" />}
                        <span>Regenerate this scene only</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ═══════════ TAB: TRANSCRIPT ═══════════ */}
            {activeTab === 'transcript' && (
              <div className="space-y-4">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-[var(--text-muted)]" />
                  <input
                    type="text"
                    value={transcriptSearch}
                    onChange={(e) => setTranscriptSearch(e.target.value)}
                    placeholder="Search words in transcript..."
                    className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] py-2.5 pl-10 pr-4 text-sm font-medium text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent-green)] focus:outline-none"
                  />
                </div>

                <ul className="max-h-[440px] space-y-2 overflow-y-auto">
                  {storyboard.scenes
                    .filter(s => !transcriptSearch || s.narration.toLowerCase().includes(transcriptSearch.toLowerCase()))
                    .map((s, i) => (
                      <li key={s.scene_id}>
                        <button
                          type="button"
                          onClick={() => {
                            seekToScene(i);
                            setActiveTab('doubt');
                          }}
                          className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3.5 text-left transition-colors hover:bg-[var(--bg-hover)]"
                        >
                          <span className="mb-1 flex items-center gap-2 text-xs font-semibold text-[var(--accent-green-text)]">
                            Scene {i + 1} • {s.duration}s
                          </span>
                          <p className="text-xs leading-relaxed text-[var(--text-primary)]">{s.narration}</p>
                        </button>
                      </li>
                    ))}
                </ul>
              </div>
            )}

            {/* ═══════════ TAB: NOTES ═══════════ */}
            {activeTab === 'notes' && (
              <div className="space-y-4 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5">
                <div>
                  <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">Learning Objectives</h3>
                  <ul className="list-disc space-y-1 pl-4 text-xs text-[var(--text-secondary)]">
                    {storyboard.learning_objectives.map((obj, i) => <li key={i}>{obj}</li>)}
                  </ul>
                </div>
                <div>
                  <h3 className="mb-1.5 text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">Educational Summary</h3>
                  <p className="text-xs leading-relaxed text-[var(--text-secondary)]">{storyboard.summary_notes}</p>
                </div>
              </div>
            )}

            {/* ═══════════ TAB: TELEMETRY & MASTERY AUDIT ═══════════ */}
            {activeTab === 'telemetry' && (
              <div className="space-y-6">
                {/* High-Level Lesson Metrics */}
                {metrics && (
                  <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {[
                      { label: 'Total Duration', value: `${metrics.total_duration_sec}s` },
                      { label: 'Visual Scenes', value: `${storyboard.scenes.length}` },
                      { label: 'Narration Chars', value: `${metrics.tts_characters}` },
                      { label: 'Total Time', value: `${metrics.render_time_sec}s` },
                    ].map((m) => (
                      <div key={m.label} className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
                        <dt className="mb-1 text-xs font-semibold uppercase text-[var(--text-secondary)]">{m.label}</dt>
                        <dd className="font-display text-lg font-bold text-[var(--text-primary)]">{m.value}</dd>
                      </div>
                    ))}
                  </dl>
                )}

                {/* Concept Mastery Evidence Breakdown (Decision #1, #8) */}
                <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5">
                  <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-[var(--text-primary)] flex items-center justify-between">
                    <span>Concept-Level Learner Mastery Profile</span>
                    <span className="text-[10px] text-[var(--text-muted)] font-normal">Evidence Required for Mastery (Decision #1)</span>
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-[var(--border)] text-[var(--text-muted)]">
                          <th className="pb-2 font-semibold">Concept</th>
                          <th className="pb-2 font-semibold">State</th>
                          <th className="pb-2 font-semibold">Watch %</th>
                          <th className="pb-2 font-semibold">Confusions</th>
                          <th className="pb-2 font-semibold">Mastery Evidence</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border)]">
                        {storyboard.scenes.map((s) => {
                          const cid = s.concept_id || s.scene_id;
                          const rec = masteryProfile?.concepts?.[cid];
                          const state = rec?.state || (activeSceneIndex >= s.order - 1 ? 'INTRODUCED' : 'NOT_SEEN');
                          const evidence = rec?.evidence_for_mastery || [];

                          return (
                            <tr key={s.scene_id} className="text-[var(--text-primary)]">
                              <td className="py-2.5 font-medium">{s.concept_name || s.caption || s.scene_id}</td>
                              <td className="py-2.5">
                                <span className={`inline-block rounded px-2 py-0.5 text-[10px] font-bold ${
                                  state === 'MASTERED'
                                    ? 'bg-emerald-500/20 text-emerald-400'
                                    : state === 'UNDERSTOOD'
                                    ? 'bg-blue-500/20 text-blue-400'
                                    : state === 'CONFUSED'
                                    ? 'bg-amber-500/20 text-amber-400'
                                    : state === 'PREREQUISITE_GAP'
                                    ? 'bg-rose-500/20 text-rose-400'
                                    : 'bg-slate-700/30 text-slate-300'
                                }`}>
                                  {state}
                                </span>
                              </td>
                              <td className="py-2.5 text-[var(--text-secondary)]">
                                {rec ? Math.round(rec.watch_progress_pct * 100) : (activeSceneIndex >= s.order - 1 ? 100 : 0)}%
                              </td>
                              <td className="py-2.5 text-[var(--text-secondary)]">{rec?.confusion_count || 0}</td>
                              <td className="py-2.5 text-[var(--text-secondary)]">
                                {evidence.length > 0 ? `${evidence.length} signals (${evidence.join(', ')})` : 'Awaiting check'}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Developer / Quality Audit Toggle (Decision #9, #10) */}
                <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
                        Quality Audit & Phase Telemetry
                      </h3>
                      <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
                        Internal pedagogical QA metrics and latency telemetry (Decision #9 & #10).
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowDevTelemetry(prev => !prev)}
                      className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
                    >
                      {showDevTelemetry ? 'Hide Details' : 'Show Details'}
                    </button>
                  </div>

                  {showDevTelemetry && (
                    <div className="mt-4 space-y-4 border-t border-[var(--border)] pt-4 text-xs">
                      {/* Teaching Quality Score (8 Dimensions) */}
                      {metrics?.quality_score && (
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-semibold text-[var(--text-primary)]">
                              Teaching Quality Score: {metrics.quality_score.total_score} / 100
                            </span>
                            <span className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                              metrics.quality_score.passed_gates
                                ? 'bg-emerald-500/20 text-emerald-400'
                                : 'bg-amber-500/20 text-amber-400'
                            }`}>
                              {metrics.quality_score.passed_gates ? 'ALL GATES PASSED' : 'REPAIR APPLIED'}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 text-[11px]">
                            <div className="rounded border border-[var(--border)] p-2">Concept Coverage: {metrics.quality_score.concept_coverage}/20</div>
                            <div className="rounded border border-[var(--border)] p-2">Prereq Order: {metrics.quality_score.prerequisite_order}/15</div>
                            <div className="rounded border border-[var(--border)] p-2">Visual Relevance: {metrics.quality_score.visual_relevance}/15</div>
                            <div className="rounded border border-[var(--border)] p-2">Example Quality: {metrics.quality_score.example_quality}/15</div>
                            <div className="rounded border border-[var(--border)] p-2">Misconceptions: {metrics.quality_score.misconception_handling}/10</div>
                            <div className="rounded border border-[var(--border)] p-2">Language Naturalness: {metrics.quality_score.language_naturalness}/10</div>
                            <div className="rounded border border-[var(--border)] p-2">Narration Sync: {metrics.quality_score.narration_visual_sync}/10</div>
                            <div className="rounded border border-[var(--border)] p-2">Doubt Readiness: {metrics.quality_score.doubt_context_readiness}/5</div>
                          </div>
                        </div>
                      )}

                      {/* Repair Log if applied */}
                      {metrics?.repair_log && (
                        <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 p-3">
                          <p className="font-semibold text-blue-400">
                            Surgical Repair: Pre-score {metrics.repair_log.pre_repair_score} → Post-score {metrics.repair_log.post_repair_score} (Δ {metrics.repair_log.score_delta > 0 ? `+${metrics.repair_log.score_delta}` : metrics.repair_log.score_delta})
                          </p>
                          <ul className="mt-1 list-disc pl-4 text-[11px] text-blue-300">
                            {metrics.repair_log.repair_actions.map((act: string, ai: number) => (
                              <li key={ai}>{act}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Granular Phase Latencies (Decision #9) */}
                      {metrics?.telemetry && (
                        <div>
                          <span className="font-semibold text-[var(--text-primary)] block mb-1">
                            Phase Latency Breakdown (ms)
                          </span>
                          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 text-[11px] text-[var(--text-secondary)]">
                            <div>Intent Parse: {metrics.telemetry.intent_parse_ms}ms</div>
                            <div>Domain Detection: {metrics.telemetry.domain_detection_ms}ms</div>
                            <div>Curriculum Graph: {metrics.telemetry.curriculum_ms}ms</div>
                            <div>Storyboard Comp: {metrics.telemetry.storyboard_ms}ms</div>
                            <div>Visual Render: {metrics.telemetry.visual_render_ms}ms</div>
                            <div>Neural TTS: {metrics.telemetry.tts_ms}ms</div>
                            <div>Composition: {metrics.telemetry.composition_ms}ms</div>
                            <div>QA & Repair: {metrics.telemetry.qa_ms + metrics.telemetry.repair_ms}ms</div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

          </div>
        )}

        {/* ═══════════ RECENT VIDEOS HISTORY ═══════════ */}
        {pastLessons.length > 0 && !generating && !lessonId && (
          <section className="mt-8 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-bento">
            <h2 className="mb-3 flex items-center gap-2 font-display text-base font-semibold text-[var(--text-primary)]">
              <Clock className="h-4 w-4 text-[var(--accent-green-text)]" />
              Recent Video Lessons ({pastLessons.length})
            </h2>
            <ul className="divide-y divide-[var(--border)]">
              {pastLessons.map((lesson) => (
                <li key={lesson.id} className="flex items-center justify-between gap-4 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-[var(--text-primary)]">{lesson.topic}</p>
                    <p className="text-xs text-[var(--text-secondary)]">
                      {lesson.level || 'B.Tech'}, {lesson.language || 'Hinglish'}, {new Date(lesson.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    {lesson.download_url && (
                      <a
                        href={lesson.download_url}
                        download
                        className="rounded-lg p-2 text-[var(--text-secondary)] hover:bg-[var(--accent-green-light)] hover:text-[var(--accent-green-text)]"
                      >
                        <Download className="h-4 w-4" />
                      </a>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDeleteLesson(lesson.id)}
                      className="rounded-lg p-2 text-[var(--text-secondary)] hover:bg-red-50 hover:text-red-700"
                    >
                      <Trash2 className="h-4 w-4" />
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
