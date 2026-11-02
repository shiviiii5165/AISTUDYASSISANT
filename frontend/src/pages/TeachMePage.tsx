import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  GraduationCap, Sparkles, Globe, FileText, CheckCircle2, AlertCircle,
  Lightbulb, Download, Send, Loader2, Award, Target, Plus,
  BrainCircuit, Presentation, Video, X, ChevronUp, Settings2,
} from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { ILLUSTRATIONS } from '../lib/assets';
import { useAuthStore } from '../store/useAuthStore';
import { fetchPdfs, type PDFDocument } from '../lib/api';
import UpgradeModal from '../components/billing/UpgradeModal';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import HistorySidebar from '../components/HistorySidebar';
import { useSidebarCollapse } from '../hooks/useSidebarCollapse';

// ═══════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════

interface Concept {
  id: string;
  name: string;
  order: number;
  summary?: string;
  status: 'pending' | 'learning' | 'mastered';
  mastery_score: number;
  active_strategy?: string;
}

interface Checkpoint {
  enabled: boolean;
  type: string;
  question: string;
  expected_skill?: string;
  difficulty?: string;
  hint?: string;
}

interface MessageItem {
  id: string;
  role: 'teacher' | 'student';
  content: string;
  checkpoint?: Checkpoint;
  citations?: string[];
  evaluation?: {
    correctness: 'correct' | 'partial' | 'incorrect';
    score: number;
    feedback: string;
    misconception?: string;
  };
  timestamp: string;
}

const LEVEL_OPTIONS = [
  { value: 'school', label: 'School / K-12' },
  { value: 'beginner', label: 'Beginner / General' },
  { value: 'college', label: 'College / Undergrad' },
  { value: 'btech', label: 'B.Tech / Engineering' },
  { value: 'advanced', label: 'Advanced Graduate' },
  { value: 'professor', label: 'Research / Professor' },
];

const MODE_OPTIONS = [
  { value: 'interactive_teacher', label: 'Interactive Teacher', desc: 'Active explanation, micro-checks and adaptation' },
  { value: 'learn_from_source', label: 'Learn From Source', desc: 'Strictly grounded in your uploaded documents' },
  { value: 'socratic_teacher', label: 'Socratic Tutor', desc: 'Guided inquiry and thought-provoking clues' },
  { value: 'exam_coach', label: 'Exam Coach', desc: 'Definitions, formulas, scoring points and pitfalls' },
  { value: 'revision', label: 'Quick Revision', desc: 'High-speed intuition and recall checkpoints' },
  { value: 'deep_dive', label: 'Deep Dive', desc: 'Underlying mechanics and edge case trade-offs' },
];

const LANGUAGE_OPTIONS = [
  { value: 'english', label: 'English' },
  { value: 'hindi', label: 'Hindi' },
  { value: 'hinglish', label: 'Hinglish' },
];

const TOPIC_SUGGESTIONS = [
  'TCP Three-Way Handshake',
  'Database Normalization: 1NF to BCNF',
  'Raft Distributed Consensus',
  'Transformers & Self-Attention',
  'Virtual Memory & TLB',
];

const QUICK_COMMANDS: { label: string; cmd: string; primary?: boolean }[] = [
  { label: 'Explain again', cmd: 'explain_again' },
  { label: 'Make simpler', cmd: 'make_simpler' },
  { label: 'Go deeper', cmd: 'go_deeper' },
  { label: 'Give example', cmd: 'give_example' },
  { label: 'Show visually', cmd: 'show_visual' },
  { label: 'Explain it back', cmd: 'explain_it_back' },
  { label: 'Ask question', cmd: 'ask_question' },
  { label: 'Exam points', cmd: 'exam_points' },
  { label: 'Test me', cmd: 'test_me', primary: true },
  { label: 'Next concept', cmd: 'continue', primary: true },
];

// ═══════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

const TeachMePage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const presetBrief = location.state?.presetBrief;
  const { collapsed: historySidebarCollapsed, toggle: toggleHistorySidebar } = useSidebarCollapse('teach-history');

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isSetupOpen, setIsSetupOpen] = useState<boolean>(true);
  const [mobileRoadmapOpen, setMobileRoadmapOpen] = useState<boolean>(false);
  const [teachHistory, setTeachHistory] = useState<any[]>([]);

  // Setup Parameters
  const [topic, setTopic] = useState<string>(presetBrief?.topic || '');
  const [level, setLevel] = useState<string>(presetBrief?.level || 'btech');
  const [language, setLanguage] = useState<string>(presetBrief?.language || 'english');
  const [mode, setMode] = useState<string>('interactive_teacher');
  const [depth] = useState<string>('normal');
  const [sourceType, setSourceType] = useState<string>(presetBrief?.source_type || 'topic');
  const [selectedPdfId, setSelectedPdfId] = useState<string>('');
  const [youtubeUrl, setYoutubeUrl] = useState<string>('');

  // Data State
  const [userPdfs, setUserPdfs] = useState<PDFDocument[]>([]);
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [currentConceptId, setCurrentConceptId] = useState<string>('');
  const [overallMastery, setOverallMastery] = useState<number>(0.0);
  const [activeCommand, setActiveCommand] = useState<string | null>(null);
  const [misconceptions, setMisconceptions] = useState<string[]>([]);
  const [messages, setMessages] = useState<MessageItem[]>([]);

  // Input State
  const [studentInput, setStudentInput] = useState<string>('');
  const [checkpointAnswer, setCheckpointAnswer] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [exportingPpt, setExportingPpt] = useState<boolean>(false);
  const [pptDownloadUrl, setPptDownloadUrl] = useState<string | null>(null);
  const [showUpgradeModal, setShowUpgradeModal] = useState<boolean>(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const topicInputRef = useRef<HTMLInputElement>(null);

  const closeSetup = useCallback(() => setIsSetupOpen(false), []);

  // Load User PDFs + Teach History
  useEffect(() => {
    (async () => {
      try {
        const pdfs = await fetchPdfs();
        const ready = pdfs.filter(p => p.status === 'ready');
        setUserPdfs(ready);
        if (ready.length > 0) setSelectedPdfId(ready[0].id);
      } catch (e) {
        console.error('Failed to load user PDFs', e);
      }
    })();

    // Load teach session history
    (async () => {
      const token = useAuthStore.getState().session?.access_token;
      if (!token) return;
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/teach/sessions`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setTeachHistory(data.sessions || []);
        }
      } catch (e) {
        console.error('Failed to load teach history', e);
      }
    })();
  }, []);

  // Focus topic field when setup opens
  useEffect(() => {
    if (isSetupOpen) {
      setTimeout(() => topicInputRef.current?.focus(), 50);
    }
  }, [isSetupOpen]);

  // Auto-scroll on new message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Start Teaching Session
  const handleStartSession = async (e?: React.FormEvent, overridePayload?: any) => {
    if (e) e.preventDefault();
    if ((!topic.trim() && !overridePayload) || loading) return;

    setLoading(true);
    setIsSetupOpen(false);
    setMobileRoadmapOpen(false);
    setMessages([]);
    setPptDownloadUrl(null);
    setErrorBanner(null);

    const token = useAuthStore.getState().session?.access_token;
    const apiUrl = import.meta.env.VITE_API_URL || '';

    try {
      const sourceIds = (sourceType !== 'topic' && selectedPdfId) ? [selectedPdfId] : [];
      const payload = overridePayload || {
        topic: topic.trim(),
        level,
        language,
        depth,
        mode,
        source_type: sourceType,
        source_ids: sourceIds,
        youtube_url: youtubeUrl.trim() || null,
      };

      const res = await fetch(`${apiUrl}/api/teach/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        if (res.status === 403) {
          setShowUpgradeModal(true);
          setLoading(false);
          setIsSetupOpen(true);
          return;
        }
        const err = await res.json();
        throw new Error(err.detail || 'Failed to start lesson');
      }

      const data = await res.json();
      setSessionId(data.session_id);

      if (data.plan?.concepts) {
        setConcepts(data.plan.concepts);
        if (data.plan.concepts.length > 0) setCurrentConceptId(data.plan.concepts[0].id);
      }

      if (data.initial_turn) {
        const turn = data.initial_turn;
        setMessages([{
          id: 'turn_0',
          role: 'teacher',
          content: turn.explanation,
          checkpoint: turn.checkpoint,
          citations: turn.citations,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }]);
      }
    } catch (err: any) {
      console.error('Session start error:', err);
      setErrorBanner(`Error starting lesson: ${err.message}`);
      setIsSetupOpen(true);
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerSubmit = async () => {
    if (!sessionId || !checkpointAnswer.trim() || loading) return;
    setLoading(true);
    const token = useAuthStore.getState().session?.access_token;
    const apiUrl = import.meta.env.VITE_API_URL || '';
    const ansText = checkpointAnswer.trim();
    setCheckpointAnswer('');

    setMessages(prev => [...prev, {
      id: `student_${Date.now()}`,
      role: 'student',
      content: ansText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }]);

    try {
      const res = await fetch(`${apiUrl}/api/teach/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ session_id: sessionId, answer: ansText }),
      });
      if (!res.ok) throw new Error('Failed to evaluate answer');
      const data = await res.json();
      const evalData = data.evaluation;

      if (data.new_mastery_score !== undefined) {
        setOverallMastery(data.new_mastery_score);
        setConcepts(prev => prev.map(c =>
          c.id === currentConceptId
            ? { ...c, mastery_score: data.new_mastery_score, status: data.new_mastery_score >= 0.85 ? 'mastered' : 'learning' }
            : c
        ));
      }
      if (evalData.misconception) {
        setMisconceptions(prev => Array.from(new Set([...prev, evalData.misconception])));
      }
      setMessages(prev => [...prev, {
        id: `feedback_${Date.now()}`,
        role: 'teacher',
        content: evalData.feedback,
        evaluation: evalData,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }]);
      if (data.new_mastery_score >= 0.85) {
        setTimeout(() => handleCommand('continue'), 1500);
      }
    } catch (err: any) {
      console.error('Answer evaluation error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionId || !studentInput.trim() || loading) return;
    setLoading(true);
    const msgText = studentInput.trim();
    setStudentInput('');
    setMessages(prev => [...prev, {
      id: `msg_${Date.now()}`,
      role: 'student',
      content: msgText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }]);

    const token = useAuthStore.getState().session?.access_token;
    const apiUrl = import.meta.env.VITE_API_URL || '';
    try {
      const res = await fetch(`${apiUrl}/api/teach/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ session_id: sessionId, message: msgText }),
      });
      if (!res.ok) throw new Error('Failed to send message');
      const data = await res.json();
      setMessages(prev => [...prev, {
        id: `teacher_${Date.now()}`,
        role: 'teacher',
        content: data.explanation,
        checkpoint: data.checkpoint,
        citations: data.citations,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }]);
    } catch (err: any) {
      console.error('Message turn error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCommand = async (command: string) => {
    if (!sessionId || loading) return;
    if (command === 'test_me') {
      navigate('/quizzes', { state: { presetConfig: { topic, source_type: sourceType, teach_session_id: sessionId }, presetPdfId: selectedPdfId } });
      return;
    }
    setLoading(true);
    setActiveCommand(command);
    const token = useAuthStore.getState().session?.access_token;
    const apiUrl = import.meta.env.VITE_API_URL || '';
    try {
      const res = await fetch(`${apiUrl}/api/teach/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ session_id: sessionId, command }),
      });
      if (!res.ok) throw new Error('Command failed');
      const data = await res.json();
      if (data.action === 'advanced_concept' && data.concept) {
        setCurrentConceptId(data.concept.id);
        setConcepts(prev => prev.map(c => c.id === data.concept.id ? { ...c, status: 'learning' } : c));
      }
      const newMsg = data.turn || data.message
        ? {
            id: `cmd_${Date.now()}`,
            role: 'teacher' as const,
            content: data.turn ? data.turn.explanation : data.message,
            checkpoint: data.turn?.checkpoint,
            citations: data.turn?.citations,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          }
        : null;
      if (newMsg) setMessages(prev => [...prev, newMsg]);
    } catch (err: any) {
      console.error('Command dispatch error:', err);
    } finally {
      setLoading(false);
      setActiveCommand(null);
    }
  };

  const handleExportPpt = async () => {
    if (!sessionId || exportingPpt) return;
    setExportingPpt(true);
    setPptDownloadUrl(null);
    setErrorBanner(null);
    const token = useAuthStore.getState().session?.access_token;
    const apiUrl = import.meta.env.VITE_API_URL || '';
    try {
      const res = await fetch(`${apiUrl}/api/teach/export/ppt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ session_id: sessionId, slide_count: 12, design: 'academic', theme: 'blue_professional' }),
      });
      if (!res.ok) throw new Error('Failed to export presentation');
      const data = await res.json();
      if (data.download_url) setPptDownloadUrl(data.download_url);
    } catch (err: any) {
      console.error('PPT export error:', err);
      setErrorBanner('Could not export to PowerPoint. Please try again.');
    } finally {
      setExportingPpt(false);
    }
  };

  const evaluationStyle = (correctness: string) =>
    correctness === 'correct'
      ? 'bg-[var(--accent-green-light)] border-[var(--accent-green)] text-[var(--accent-green-deep)]'
      : correctness === 'partial'
      ? 'bg-[var(--accent-amber-light)] border-[var(--accent-amber)] text-[var(--text-primary)]'
      : 'bg-amber-50 border-amber-200 text-amber-900';

  // ─── Sub-components ────────────────────────────────────────────────────────

  const SetupCard = (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:py-14">
        {/* Header */}
        <div className="mb-8 flex items-center gap-4">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[var(--accent-green-light)]">
            <BrainCircuit className="h-6 w-6 text-[var(--accent-green-text)]" aria-hidden="true" />
          </span>
          <div>
            <h2 className="font-display text-2xl font-bold tracking-tight text-[var(--text-primary)]">
              {sessionId ? 'New lesson' : 'Start a lesson'}
            </h2>
            <p className="text-sm text-[var(--text-secondary)]">
              Configure your topic, source and teaching style.
            </p>
          </div>
          {sessionId && (
            <button
              type="button"
              onClick={closeSetup}
              aria-label="Cancel"
              className="ml-auto rounded-xl border border-[var(--border)] p-2 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            >
              <X className="h-5 w-5" aria-hidden="true" />
            </button>
          )}
        </div>

        <form onSubmit={handleStartSession} className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-8">
          {/* Left Column */}
          <div className="space-y-8">
            {/* 1. Topic */}
            <div>
            <label htmlFor="topic-input" className="mb-2 block text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
              Topic to master
            </label>
            <input
              id="topic-input"
              ref={topicInputRef}
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="E.g. Deadlocks in Operating Systems"
              required
              className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 text-sm font-medium text-[var(--text-primary)] placeholder:text-[var(--text-muted)] shadow-[var(--shadow-sm)] focus:border-[var(--accent-green)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-green)]"
            />
            <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
              {TOPIC_SUGGESTIONS.map((t, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setTopic(t)}
                  className="rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-2.5 py-1 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:border-[var(--accent-green)] hover:bg-[var(--accent-green-light)] hover:text-[var(--accent-green-text)]"
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* 2. Knowledge Source */}
          <fieldset>
            <legend className="mb-2 block text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
              Knowledge source
            </legend>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {[
                { id: 'topic', label: 'Topic only', icon: Globe },
                { id: 'pdf', label: 'My notes', icon: FileText },
                { id: 'youtube', label: 'YouTube', icon: Video },
                { id: 'web', label: 'Web', icon: Sparkles },
              ].map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setSourceType(s.id)}
                  aria-pressed={sourceType === s.id}
                  className={`flex flex-col items-center gap-2 rounded-xl border p-4 text-center text-xs font-semibold transition-colors ${
                    sourceType === s.id
                      ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)] text-[var(--accent-green-text)]'
                      : 'border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  <s.icon className="h-5 w-5" aria-hidden="true" />
                  <span>{s.label}</span>
                </button>
              ))}
            </div>

            {sourceType === 'pdf' && (
              <div className="mt-3 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
                <label htmlFor="source-pdf" className="mb-2 block text-xs font-semibold text-[var(--text-primary)]">
                  Select document
                </label>
                {userPdfs.length > 0 ? (
                  <select
                    id="source-pdf"
                    value={selectedPdfId}
                    onChange={(e) => setSelectedPdfId(e.target.value)}
                    className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-sm font-medium text-[var(--text-primary)] focus:border-[var(--accent-green)] focus:outline-none"
                  >
                    {userPdfs.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                ) : (
                  <p className="text-xs text-[var(--text-secondary)]">No documents ready. Upload one in Library first.</p>
                )}
              </div>
            )}

            {sourceType === 'youtube' && (
              <div className="mt-3 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
                <label htmlFor="youtube-url" className="mb-2 block text-xs font-semibold text-[var(--text-primary)]">
                  YouTube URL
                </label>
                <input
                  id="youtube-url"
                  type="url"
                  value={youtubeUrl}
                  onChange={(e) => setYoutubeUrl(e.target.value)}
                  placeholder="https://youtube.com/watch?v=..."
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-sm font-medium text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent-green)] focus:outline-none"
                />
              </div>
            )}
          </fieldset>
          </div>

          {/* Right Column */}
          <div className="space-y-8">
            {/* 3. Level & Language — side by side */}
            <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="level-select" className="mb-2 block text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                Level
              </label>
              <select
                id="level-select"
                value={level}
                onChange={(e) => setLevel(e.target.value)}
                className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2.5 text-sm font-medium text-[var(--text-primary)] shadow-[var(--shadow-sm)] focus:border-[var(--accent-green)] focus:outline-none"
              >
                {LEVEL_OPTIONS.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="language-select" className="mb-2 block text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                Language
              </label>
              <select
                id="language-select"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2.5 text-sm font-medium text-[var(--text-primary)] shadow-[var(--shadow-sm)] focus:border-[var(--accent-green)] focus:outline-none"
              >
                {LANGUAGE_OPTIONS.map(lang => <option key={lang.value} value={lang.value}>{lang.label}</option>)}
              </select>
            </div>
          </div>

          {/* 4. Teaching Mode — 2-column grid */}
          <fieldset>
            <legend className="mb-3 block text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
              Teaching mode
            </legend>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {MODE_OPTIONS.map(m => (
                <button
                  key={m.value}
                  type="button"
                  onClick={() => setMode(m.value)}
                  aria-pressed={mode === m.value}
                  className={`rounded-xl border p-3.5 text-left transition-colors ${
                    mode === m.value
                      ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)]'
                      : 'border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)]'
                  }`}
                >
                  <p className={`text-sm font-semibold ${mode === m.value ? 'text-[var(--accent-green-text)]' : 'text-[var(--text-primary)]'}`}>
                    {m.label}
                  </p>
                  <p className="mt-0.5 text-xs leading-relaxed text-[var(--text-secondary)]">{m.desc}</p>
                </button>
              ))}
            </div>
            </fieldset>

            {/* Submit */}
            <div className="pt-2">
            <button
              type="submit"
              disabled={!topic.trim() || loading}
              className="flex w-full items-center justify-center gap-2.5 rounded-xl bg-[var(--accent-green)] px-6 py-3.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--accent-green-hover)] active:translate-y-px disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <GraduationCap className="h-4 w-4" aria-hidden="true" />
              )}
              {loading ? 'Starting lesson…' : 'Start lesson'}
            </button>
          </div>
          </div>
        </form>
      </div>
    </div>
  );

  const RoadmapPanel = (
    <div className="flex h-full flex-col">
      {/* Panel header */}
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-[var(--border)] px-5 py-4">
        <div className="flex items-center gap-2.5 min-w-0">
          <GraduationCap className="h-4 w-4 shrink-0 text-[var(--accent-green-text)]" aria-hidden="true" />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-[var(--text-primary)]">
              {topic || 'Lesson roadmap'}
            </p>
            <p className="text-[11px] font-medium capitalize text-[var(--text-secondary)]">
              {LEVEL_OPTIONS.find(l => l.value === level)?.label || level}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setIsSetupOpen(true)}
          aria-label="Change lesson settings"
          className="flex shrink-0 items-center gap-1 rounded-lg border border-[var(--border)] px-2.5 py-1.5 text-xs font-semibold text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
        >
          <Settings2 className="h-3.5 w-3.5" aria-hidden="true" />
          Edit
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {/* Mastery */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
          <div className="mb-2 flex items-center justify-between text-xs font-semibold">
            <span className="flex items-center gap-1.5 text-[var(--text-primary)]">
              <Target className="h-3.5 w-3.5 text-[var(--accent-green-text)]" aria-hidden="true" />
              Topic mastery
            </span>
            <span className="tabular-nums text-[var(--accent-green-text)]">
              {Math.round(overallMastery * 100)}%
            </span>
          </div>
          <div
            className="h-2 w-full overflow-hidden rounded-full bg-[var(--border)]"
            role="progressbar"
            aria-valuenow={Math.round(overallMastery * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Topic mastery"
          >
            <div
              className="h-2 rounded-full bg-[var(--accent-green)] transition-all duration-500 ease-out"
              style={{ width: `${Math.max(4, overallMastery * 100)}%` }}
            />
          </div>
        </div>

        {/* Concepts */}
        {concepts.length > 0 && (
          <div>
            <h3 className="mb-2.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
              Lesson concepts
            </h3>
            <ol className="space-y-1.5">
              {concepts.map((c, i) => {
                const isCurrent = c.id === currentConceptId;
                const isMastered = c.status === 'mastered' || c.mastery_score >= 0.85;
                return (
                  <li
                    key={c.id}
                    aria-current={isCurrent ? 'step' : undefined}
                    className={`rounded-xl border p-3 text-xs font-medium transition-colors ${
                      isCurrent
                        ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)]'
                        : isMastered
                        ? 'border-[var(--border)] bg-[var(--bg-secondary)]'
                        : 'border-[var(--border)] bg-[var(--bg-card)]'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-semibold text-[var(--text-primary)] leading-snug">
                        {i + 1}. {c.name}
                      </span>
                      {isMastered ? (
                        <span className="flex shrink-0 items-center gap-1 text-[10px] font-semibold text-[var(--accent-green-text)]">
                          <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                          Done
                        </span>
                      ) : isCurrent ? (
                        <span className="shrink-0 rounded-md bg-[var(--accent-green)] px-1.5 py-0.5 text-[10px] font-semibold text-white">
                          Now
                        </span>
                      ) : (
                        <span className="shrink-0 text-[10px] text-[var(--text-muted)]">Next</span>
                      )}
                    </div>
                    {c.summary && (
                      <p className="mt-1 line-clamp-2 text-[11px] leading-snug text-[var(--text-secondary)]">
                        {c.summary}
                      </p>
                    )}
                  </li>
                );
              })}
            </ol>
          </div>
        )}

        {/* Misconceptions */}
        {misconceptions.length > 0 && (
          <div className="rounded-xl border border-[var(--accent-amber)] bg-[var(--accent-amber-light)] p-3.5">
            <h3 className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold text-[var(--text-primary)]">
              <AlertCircle className="h-3.5 w-3.5 text-[var(--accent-amber)]" aria-hidden="true" />
              Focus reminders
            </h3>
            <ul className="list-disc space-y-1 pl-4 text-[11px] text-[var(--text-secondary)]">
              {misconceptions.map((m, i) => <li key={i}>{m}</li>)}
            </ul>
          </div>
        )}
      </div>

      {/* Export — pinned at bottom */}
      <div className="shrink-0 border-t border-[var(--border)] p-4">
        {pptDownloadUrl ? (
          <a
            href={pptDownloadUrl}
            download={`${topic.replace(/[^a-zA-Z0-9]/g, '_')}_presentation.pptx`}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--accent-green)] px-3 py-2.5 text-xs font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)]"
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            Download lesson PPTX
          </a>
        ) : (
          <button
            type="button"
            onClick={handleExportPpt}
            disabled={exportingPpt || !sessionId}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2.5 text-xs font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)] disabled:opacity-50"
          >
            {exportingPpt ? (
              <><Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />Generating PPTX</>
            ) : (
              <><Presentation className="h-4 w-4 text-[var(--accent-green-text)]" aria-hidden="true" />Export to PPTX</>
            )}
          </button>
        )}
      </div>
    </div>
  );

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <AppLayout title="Teach Me">
      <SEO
        title="Teach Me, Interactive Adaptive AI Teacher | LearnByGenie"
        description="Experience an interactive university tutor that explains concepts, asks checkpoint questions, diagnoses misconceptions, adapts strategies, and tracks mastery."
      />

      {/* Full-height workspace */}
      <div className="flex h-full overflow-hidden">

        {/* ══ History sidebar — mirrors ChatPage pattern ══ */}
        <HistorySidebar
          title="Teach Sessions"
          items={teachHistory.map(s => ({ id: s.id, title: s.topic || s.title || 'Untitled', date: s.created_at }))}
          selectedId={sessionId}
          onSelect={async (id: string) => {
            const token = useAuthStore.getState().session?.access_token;
            if (!token) return;
            try {
              const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/teach/session/${id}`, {
                headers: { 'Authorization': `Bearer ${token}` }
              });
              if (res.ok) {
                const data = await res.json();
                setSessionId(data.session_id || id);
                setTopic(data.topic || '');
                setLevel(data.level || 'btech');
                setLanguage(data.language || 'english');
                setMode(data.mode || 'interactive_teacher');
                if (data.plan?.concepts) {
                  setConcepts(data.plan.concepts);
                  if (data.plan.concepts.length > 0) setCurrentConceptId(data.plan.concepts[0].id);
                }
                if (data.messages) {
                  setMessages(data.messages);
                }
                setIsSetupOpen(false);
              }
            } catch (e) {
              console.error('Failed to load teach session', e);
            }
          }}
          onNew={() => {
            setSessionId(null);
            setMessages([]);
            setConcepts([]);
            setCurrentConceptId('');
            setOverallMastery(0);
            setMisconceptions([]);
            setIsSetupOpen(true);
          }}
          collapsed={historySidebarCollapsed}
          onToggle={toggleHistorySidebar}
        />

        {/* ══ LEFT: Setup card OR chat thread ══ */}
        <div className="relative flex min-w-0 flex-1 flex-col bg-[var(--bg-primary)]">

          {/* ── Chat toolbar (only when session active and setup closed) ── */}
          {sessionId && !isSetupOpen && (
            <header className="flex shrink-0 items-center justify-between border-b border-[var(--border)] bg-[var(--bg-card)] px-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-[var(--text-primary)]">{topic}</p>
                <p className="text-[11px] capitalize text-[var(--text-secondary)]">
                  {LEVEL_OPTIONS.find(l => l.value === level)?.label} · {LANGUAGE_OPTIONS.find(l => l.value === language)?.label}
                </p>
              </div>
              {/* Mobile roadmap button */}
              <button
                type="button"
                onClick={() => setMobileRoadmapOpen(true)}
                className="lg:hidden ml-4 flex shrink-0 items-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2 text-xs font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)]"
              >
                <Target className="h-3.5 w-3.5 text-[var(--accent-green-text)]" aria-hidden="true" />
                Roadmap
              </button>
            </header>
          )}

          {isSetupOpen ? (
            /* ── Full-width centered setup card ── */
            SetupCard
          ) : (
            /* ── Chat thread ── */
            <>
              <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
                <div className="mx-auto max-w-3xl space-y-6">

                {errorBanner && (
                  <div
                    role="alert"
                    className="mx-auto flex max-w-3xl items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
                  >
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                    <span className="flex-1">{errorBanner}</span>
                    <button
                      type="button"
                      onClick={() => setErrorBanner(null)}
                      aria-label="Dismiss error"
                      className="rounded p-0.5 hover:bg-amber-100"
                    >
                      <X className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                )}

                {/* No messages yet */}
                {messages.length === 0 && !loading && (
                  <div className="mx-auto max-w-xl pt-16 text-center">
                    <img
                      src={ILLUSTRATIONS.teachMe}
                      alt=""
                      aria-hidden="true"
                      className="mx-auto mb-5 h-32 w-auto object-contain"
                      onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                    />
                    <h2 className="mb-2 font-display text-2xl font-bold text-[var(--text-primary)]">
                      Welcome to Teach Me
                    </h2>
                    <p className="mb-8 max-w-[44ch] mx-auto text-sm leading-relaxed text-[var(--text-secondary)]">
                      An adaptive tutor that explains, checks your understanding, and adjusts.
                      Pick a topic, your notes, or a video to begin.
                    </p>
                    <button
                      type="button"
                      onClick={() => setIsSetupOpen(true)}
                      className="inline-flex items-center gap-2 rounded-xl bg-[var(--accent-green)] px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)] active:translate-y-px"
                    >
                      <Plus className="h-4 w-4" aria-hidden="true" />
                      Start new lesson
                    </button>
                  </div>
                )}

                {/* Message thread */}
                <div aria-live="polite" aria-busy={loading} className="space-y-6">
                  <AnimatePresence initial={false}>
                    {messages.map((msg) => (
                      <motion.div
                        key={msg.id}
                        initial={{ opacity: 0, y: 20, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        transition={{ duration: 0.3, ease: 'easeOut' }}
                        className={`flex ${msg.role === 'student' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div className={`max-w-3xl rounded-3xl p-6 shadow-sm ${
                          msg.role === 'student'
                            ? 'rounded-br-sm bg-[var(--accent-royal)] text-white'
                            : 'rounded-bl-sm border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-primary)]'
                        }`}>

                          <div className="mb-3 flex items-center justify-between gap-4">
                            <span className={`text-[11px] font-bold uppercase tracking-wider ${
                              msg.role === 'student' ? 'text-white/80' : 'text-[var(--accent-royal)]'
                            }`}>
                              {msg.role === 'student' ? 'You' : 'Professor Genie'}
                            </span>
                            <span className={`text-[10px] font-medium tabular-nums ${
                              msg.role === 'student' ? 'text-white/60' : 'text-[var(--text-muted)]'
                            }`}>
                              {msg.timestamp}
                            </span>
                          </div>

                        <div className={`prose prose-sm max-w-none leading-relaxed ${
                          msg.role === 'student'
                            ? 'prose-invert'
                            : 'prose-p:text-[var(--text-primary)] prose-strong:text-[var(--text-primary)] prose-headings:text-[var(--text-primary)] prose-li:text-[var(--text-primary)]'
                        }`}>
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
                              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                            }}
                          >
                            {msg.content.replace(/\[([^\]]+?)\]/g, (match, p1) =>
                              p1.match(/^(Page|Slide|Note|Video|\d{1,2}:\d{2})/i) ? `**[${p1}]**` : match
                            )}
                          </ReactMarkdown>
                        </div>

                        {/* Citations */}
                        {msg.citations && msg.citations.length > 0 && (
                          <div className="mt-3.5 flex flex-wrap items-center gap-1.5 border-t border-[var(--border)] pt-3">
                            <span className="text-[11px] font-semibold text-[var(--text-secondary)]">Sources</span>
                            {msg.citations.map((cite, ci) => (
                              <span
                                key={ci}
                                className="inline-flex items-center rounded-md border border-[var(--border)] bg-[var(--bg-secondary)] px-2 py-0.5 text-[11px] font-medium text-[var(--text-secondary)]"
                              >
                                {cite}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Evaluation */}
                        {msg.evaluation && (
                          <div className={`mt-3 rounded-xl border p-3 text-xs font-medium ${evaluationStyle(msg.evaluation.correctness)}`}>
                            <p className="mb-1 flex items-center gap-2 font-semibold">
                              <Award className="h-4 w-4" aria-hidden="true" />
                              Assessment: {msg.evaluation.correctness} ({Math.round(msg.evaluation.score * 100)}%)
                            </p>
                            {msg.evaluation.misconception && (
                              <p className="mt-1 text-[11px]">
                                <strong>Note:</strong> {msg.evaluation.misconception}
                              </p>
                            )}
                          </div>
                        )}

                        {/* Checkpoint */}
                        {msg.checkpoint?.enabled && (
                          <div className="mt-5 rounded-2xl border border-[var(--border)] bg-white/50 p-5 backdrop-blur-sm">
                            <div className="mb-3 flex items-center justify-between gap-2">
                              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[var(--text-primary)]">
                                <Lightbulb className="h-4 w-4 text-[var(--accent-royal)]" aria-hidden="true" />
                                Quick check
                              </span>
                              <span className="rounded-full bg-[var(--accent-baby)]/30 px-2.5 py-1 text-[10px] font-bold uppercase text-[var(--accent-royal)]">
                                {msg.checkpoint.difficulty || 'Medium'}
                              </span>
                            </div>
                            <p className="mb-4 text-sm font-semibold text-[var(--text-primary)] leading-relaxed">
                              {msg.checkpoint.question}
                            </p>
                            <div className="flex items-center gap-2">
                              <label htmlFor={`checkpoint-${msg.id}`} className="sr-only">Your answer</label>
                              <input
                                id={`checkpoint-${msg.id}`}
                                type="text"
                                value={checkpointAnswer}
                                onChange={(e) => setCheckpointAnswer(e.target.value)}
                                placeholder="Type your answer"
                                onKeyDown={(e) => e.key === 'Enter' && handleAnswerSubmit()}
                                className="flex-1 rounded-xl border border-[var(--border)] bg-white px-4 py-2.5 text-sm font-medium text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent-royal)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-royal)] transition-all"
                              />
                              <button
                                type="button"
                                onClick={handleAnswerSubmit}
                                disabled={!checkpointAnswer.trim() || loading}
                                className="rounded-xl bg-[var(--accent-royal)] px-5 py-2.5 text-xs font-bold text-white transition-colors hover:bg-[var(--accent-royal)]/90 disabled:opacity-50"
                              >
                                Submit
                              </button>
                            </div>
                          </div>
                        )}

                      </div>
                    </motion.div>
                  ))}
                  </AnimatePresence>
                </div>

                {/* Loading skeleton */}
                {loading && (
                  <div className="flex justify-start">
                    <div className="max-w-2xl w-full space-y-4 rounded-3xl rounded-bl-sm border border-[var(--border)] bg-white/50 p-6 backdrop-blur-sm">
                      <div className="flex items-center gap-2.5">
                        <Loader2 className="h-5 w-5 shrink-0 animate-spin text-[var(--accent-royal)]" aria-hidden="true" />
                        <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                          {activeCommand ? 'Adapting explanation' : 'Thinking'}
                        </span>
                      </div>
                      <div className="space-y-3" aria-hidden="true">
                        <div className="h-4 w-3/4 animate-pulse rounded-full bg-[var(--bg-secondary)]" />
                        <div className="h-4 w-full animate-pulse rounded-full bg-[var(--bg-secondary)]" />
                        <div className="h-4 w-5/6 animate-pulse rounded-full bg-[var(--bg-secondary)]" />
                      </div>
                    </div>
                  </div>
                )}

                <div ref={chatEndRef} />
                </div>{/* /max-w-3xl */}
              </div>

              {/* ── Action bar + composer ── */}
              {sessionId && (
                <div className="shrink-0 border-t border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 sm:px-5">
                  {/* Quick commands */}
                  <div
                    className="scrollbar-thin mx-auto mb-3 flex max-w-3xl items-center gap-1.5 overflow-x-auto pb-1"
                    role="group"
                    aria-label="Lesson actions"
                  >
                    {QUICK_COMMANDS.map((act) => (
                      <button
                        key={act.cmd}
                        type="button"
                        onClick={() => handleCommand(act.cmd)}
                        disabled={loading}
                        className={`flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border px-4 py-2 text-xs font-bold transition-all disabled:opacity-50 ${
                          act.primary
                            ? 'border-[var(--accent-royal)] bg-[var(--accent-baby)]/20 text-[var(--accent-royal)] shadow-sm hover:bg-[var(--accent-royal)] hover:text-white'
                            : 'border-[var(--border)] bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:border-[var(--accent-royal)] hover:text-[var(--accent-royal)]'
                        }`}
                      >
                        {activeCommand === act.cmd && (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                        )}
                        {act.label}
                      </button>
                    ))}
                  </div>

                  {/* Input composer */}
                  <form onSubmit={handleSendMessage} className="mx-auto flex max-w-3xl items-center gap-2">
                    <label htmlFor="student-input" className="sr-only">Ask a question or explain your doubt</label>
                    <input
                      id="student-input"
                      type="text"
                      value={studentInput}
                      onChange={(e) => setStudentInput(e.target.value)}
                      placeholder="Ask a question or explain your doubt"
                      disabled={loading}
                      className="flex-1 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-4 py-3 text-sm font-medium text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:bg-[var(--bg-card)] focus:border-[var(--accent-royal)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-royal)] transition-colors"
                    />
                    <button
                      type="submit"
                      disabled={!studentInput.trim() || loading}
                      aria-label="Send message"
                      className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-royal)] text-white transition-colors hover:bg-[var(--accent-royal)]/90 active:translate-y-px disabled:opacity-50"
                    >
                      <Send className="h-5 w-5" aria-hidden="true" />
                    </button>
                  </form>
                </div>
              )}
            </>
          )}
        </div>

        {/* ══ RIGHT: Concept roadmap panel (desktop only) ══ */}
        {sessionId && !isSetupOpen && (
          <aside
            aria-label="Lesson roadmap"
            className="hidden w-72 shrink-0 border-l border-[var(--border)] bg-[var(--bg-secondary)] lg:flex lg:flex-col"
          >
            {RoadmapPanel}
          </aside>
        )}

      </div>

      {/* ══ Mobile roadmap bottom sheet ══ */}
      {mobileRoadmapOpen && sessionId && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm lg:hidden"
            onClick={() => setMobileRoadmapOpen(false)}
            aria-hidden="true"
          />
          {/* Sheet */}
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Lesson roadmap"
            className="fixed inset-x-0 bottom-0 z-50 flex max-h-[80vh] flex-col rounded-t-2xl border-t border-[var(--border)] bg-[var(--bg-card)] shadow-xl lg:hidden"
          >
            {/* Drag handle + close */}
            <div className="flex shrink-0 items-center justify-between px-5 py-3 border-b border-[var(--border)]">
              <div className="mx-auto mb-0 h-1 w-10 rounded-full bg-[var(--border)]" aria-hidden="true" />
              <button
                type="button"
                onClick={() => setMobileRoadmapOpen(false)}
                aria-label="Close roadmap"
                className="absolute right-4 rounded-lg p-1.5 text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
              >
                <ChevronUp className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              {RoadmapPanel}
            </div>
          </div>
        </>
      )}

      {showUpgradeModal && (
        <UpgradeModal isOpen={showUpgradeModal} onClose={() => setShowUpgradeModal(false)} />
      )}
    </AppLayout>
  );
};

export default TeachMePage;
