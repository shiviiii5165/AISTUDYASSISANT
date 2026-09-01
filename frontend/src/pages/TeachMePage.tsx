import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  GraduationCap, Sparkles, Globe, FileText, CheckCircle2, AlertCircle,
  Lightbulb, Download, Send, Loader2, Award, Target, Plus,
  BrainCircuit, Presentation, Video, X,
} from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { useAuthStore } from '../store/useAuthStore';
import { fetchPdfs, type PDFDocument } from '../lib/api';
import UpgradeModal from '../components/billing/UpgradeModal';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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
  'TCP Three-Way Handshake & Connection Teardown',
  'Database Normalization: 1NF to BCNF with Functional Dependencies',
  'Raft Distributed Consensus Algorithm',
  'Transformers & Multi-Head Self-Attention Mechanics',
  'Virtual Memory: Page Tables & TLB Translation',
];

/** Command values are unchanged; only the visible labels lost their emoji. */
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
  { label: 'Continue to next concept', cmd: 'continue', primary: true },
];

const TeachMePage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const presetBrief = location.state?.presetBrief;

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isSetupOpen, setIsSetupOpen] = useState<boolean>(true);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState<boolean>(false);

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
  /* Replaces two window.alert() calls. Same trigger, same message, rendered
     inline so it is announced by screen readers instead of blocking. */
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  const closeSetup = useCallback(() => setIsSetupOpen(false), []);


  // Load User PDFs
  useEffect(() => {
    const loadPdfs = async () => {
      try {
        const pdfs = await fetchPdfs();
        const ready = pdfs.filter(p => p.status === 'ready');
        setUserPdfs(ready);
        if (ready.length > 0) setSelectedPdfId(ready[0].id);
      } catch (e) {
        console.error('Failed to load user PDFs', e);
      }
    };
    loadPdfs();
  }, []);

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
    setMobileSidebarOpen(false);
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
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
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

      if (data.plan && data.plan.concepts) {
        setConcepts(data.plan.concepts);
        if (data.plan.concepts.length > 0) {
          setCurrentConceptId(data.plan.concepts[0].id);
        }
      }

      // Add initial teacher turn
      if (data.initial_turn) {
        const turn = data.initial_turn;
        setMessages([
          {
            id: 'turn_0',
            role: 'teacher',
            content: turn.explanation,
            checkpoint: turn.checkpoint,
            citations: turn.citations,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          }
        ]);
      }

    } catch (err: any) {
      console.error('Session start error:', err);
      setErrorBanner(`Error starting lesson: ${err.message}`);
      setIsSetupOpen(true);
    } finally {
      setLoading(false);
    }
  };

  // Submit Answer to Active Checkpoint
  const handleAnswerSubmit = async () => {
    if (!sessionId || !checkpointAnswer.trim() || loading) return;

    setLoading(true);
    const token = useAuthStore.getState().session?.access_token;
    const apiUrl = import.meta.env.VITE_API_URL || '';

    // Optimistically add student's answer to messages
    const studentMsgId = `student_${Date.now()}`;
    const ansText = checkpointAnswer.trim();
    setCheckpointAnswer('');

    setMessages(prev => [
      ...prev,
      {
        id: studentMsgId,
        role: 'student',
        content: ansText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
    ]);

    try {
      const res = await fetch(`${apiUrl}/api/teach/answer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: sessionId,
          answer: ansText,
        }),
      });

      if (!res.ok) throw new Error('Failed to evaluate answer');
      const data = await res.json();
      const evalData = data.evaluation;

      // Update mastery score
      if (data.new_mastery_score !== undefined) {
        setOverallMastery(data.new_mastery_score);
        setConcepts(prev => prev.map(c => {
          if (c.id === currentConceptId) {
            return {
              ...c,
              mastery_score: data.new_mastery_score,
              status: data.new_mastery_score >= 0.85 ? 'mastered' : 'learning',
            };
          }
          return c;
        }));
      }

      if (evalData.misconception) {
        setMisconceptions(prev => Array.from(new Set([...prev, evalData.misconception])));
      }

      // Add feedback message
      setMessages(prev => [
        ...prev,
        {
          id: `feedback_${Date.now()}`,
          role: 'teacher',
          content: evalData.feedback,
          evaluation: evalData,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }
      ]);

      // If mastered, offer to advance
      if (data.new_mastery_score >= 0.85) {
        setTimeout(() => {
          handleCommand('continue');
        }, 1500);
      }

    } catch (err: any) {
      console.error('Answer evaluation error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Send Student Conversational Question
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionId || !studentInput.trim() || loading) return;

    setLoading(true);
    const msgText = studentInput.trim();
    setStudentInput('');

    setMessages(prev => [
      ...prev,
      {
        id: `msg_${Date.now()}`,
        role: 'student',
        content: msgText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
    ]);

    const token = useAuthStore.getState().session?.access_token;
    const apiUrl = import.meta.env.VITE_API_URL || '';

    try {
      const res = await fetch(`${apiUrl}/api/teach/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: msgText,
        }),
      });

      if (!res.ok) throw new Error('Failed to send message');
      const data = await res.json();

      setMessages(prev => [
        ...prev,
        {
          id: `teacher_${Date.now()}`,
          role: 'teacher',
          content: data.explanation,
          checkpoint: data.checkpoint,
          citations: data.citations,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }
      ]);
    } catch (err: any) {
      console.error('Message turn error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Quick Command Dispatcher
  const handleCommand = async (command: string) => {
    if (!sessionId || loading) return;

    if (command === 'test_me') {
      const presetConfig = {
        topic: topic,
        source_type: sourceType,
        teach_session_id: sessionId,
      };
      navigate('/quizzes', { state: { presetConfig, presetPdfId: selectedPdfId } });
      return;
    }

    setLoading(true);
    setActiveCommand(command);
    const token = useAuthStore.getState().session?.access_token;
    const apiUrl = import.meta.env.VITE_API_URL || '';

    try {
      const res = await fetch(`${apiUrl}/api/teach/command`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: sessionId,
          command,
        }),
      });

      if (!res.ok) throw new Error('Command failed');
      const data = await res.json();

      if (data.action === 'advanced_concept' && data.concept) {
        setCurrentConceptId(data.concept.id);
        setConcepts(prev => prev.map(c => c.id === data.concept.id ? { ...c, status: 'learning' } : c));
      }

      if (data.turn) {
        setMessages(prev => [
          ...prev,
          {
            id: `cmd_${Date.now()}`,
            role: 'teacher',
            content: data.turn.explanation,
            checkpoint: data.turn.checkpoint,
            citations: data.turn.citations,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          }
        ]);
      } else if (data.message) {
        setMessages(prev => [
          ...prev,
          {
            id: `completion_${Date.now()}`,
            role: 'teacher',
            content: data.message,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          }
        ]);
      }

    } catch (err: any) {
      console.error('Command dispatch error:', err);
    } finally {
      setLoading(false);
      setActiveCommand(null);
    }
  };

  // Export to PPT
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
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: sessionId,
          slide_count: 12,
          design: 'academic',
          theme: 'blue_professional',
        }),
      });

      if (!res.ok) throw new Error('Failed to export presentation');
      const data = await res.json();
      if (data.download_url) {
        setPptDownloadUrl(data.download_url);
      }
    } catch (err: any) {
      console.error('PPT export error:', err);
      setErrorBanner('Could not export to PowerPoint. Please try again.');
    } finally {
      setExportingPpt(false);
    }
  };

  const evaluationStyle = (correctness: string) =>
    correctness === 'correct'
      ? 'bg-green-100 border-green-200 text-green-800'
      : correctness === 'partial'
      ? 'bg-amber-100 border-amber-200 text-amber-800'
      : 'bg-red-100 border-red-200 text-red-800';

  return (
    <AppLayout title="Teach Me">
      <SEO
        title="Teach Me, Interactive Adaptive AI Teacher | TeachGenie"
        description="Experience an interactive university tutor that explains concepts, asks checkpoint questions, diagnoses misconceptions, adapts strategies, and tracks mastery."
      />

      <div className="flex h-full overflow-hidden bg-[var(--bg-primary)]">

        {/* ══════════════ LEFT ROADMAP & MASTERY PANEL ══════════════ */}
        {/* Mobile Backdrop */}
        {mobileSidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm lg:hidden"
            onClick={() => setMobileSidebarOpen(false)}
          />
        )}

        <aside
          className={`shrink-0 flex-col justify-between bg-[var(--bg-card)] lg:static lg:z-auto lg:flex lg:w-80 lg:border-r lg:border-[var(--border)] lg:shadow-none ${
            mobileSidebarOpen
              ? 'fixed bottom-0 left-0 top-0 z-50 flex w-[85vw] max-w-sm border-r border-[var(--border)] shadow-xl'
              : 'hidden'
          }`}
        >
          {(!sessionId || isSetupOpen) ? (
            <div className="overflow-y-auto p-5">
              <div className="mb-6 flex items-center gap-3 border-b border-[var(--border)] pb-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-green-light)]">
                  <BrainCircuit className="h-5 w-5 text-[var(--accent-green-text)]" aria-hidden="true" />
                </span>
                <div>
                  <h2 className="font-display text-base font-bold text-[var(--text-primary)]">
                    Configure lesson
                  </h2>
                </div>
                {sessionId && (
                  <button
                    type="button"
                    onClick={closeSetup}
                    aria-label="Cancel setup"
                    className="ml-auto shrink-0 rounded-lg p-1.5 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                  >
                    <X className="h-4 w-4" aria-hidden="true" />
                  </button>
                )}
              </div>

              <form onSubmit={handleStartSession}>
                {/* 1. Topic */}
                <div className="mb-6">
                  <label htmlFor="topic-input" className="mb-2 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                    Topic to master
                  </label>
                  <input
                    id="topic-input"
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="E.g. Deadlocks"
                    required
                    className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2.5 text-xs font-medium text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:bg-[var(--bg-card)] focus:border-[var(--accent-green)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-green)]"
                  />
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    {TOPIC_SUGGESTIONS.slice(0, 2).map((t, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => setTopic(t)}
                        className="rounded-md bg-[var(--bg-secondary)] px-2 py-0.5 text-[10px] text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] max-w-full truncate"
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>

                {/* 2. Knowledge Source */}
                <fieldset className="mb-6">
                  <legend className="mb-2 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                    Knowledge Source
                  </legend>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { id: 'topic', label: 'Topic only', icon: Globe },
                      { id: 'pdf', label: 'Notes', icon: FileText },
                      { id: 'youtube', label: 'YouTube', icon: Video },
                      { id: 'web', label: 'Web', icon: Sparkles },
                    ].map((s) => (
                      <button
                        key={s.id}
                        type="button"
                        onClick={() => setSourceType(s.id)}
                        aria-pressed={sourceType === s.id}
                        className={`flex flex-col items-center gap-1.5 rounded-xl border p-3 text-center text-xs font-semibold transition-colors ${
                          sourceType === s.id
                            ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)] text-[var(--accent-green-text)]'
                            : 'border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'
                        }`}
                      >
                        <s.icon className="h-4 w-4" aria-hidden="true" />
                        <span>{s.label}</span>
                      </button>
                    ))}
                  </div>

                  {sourceType === 'pdf' && (
                    <div className="mt-3 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3">
                      <label htmlFor="source-pdf" className="mb-1 block text-[11px] font-semibold text-[var(--text-primary)]">
                        Select document
                      </label>
                      {userPdfs.length > 0 ? (
                        <select
                          id="source-pdf"
                          value={selectedPdfId}
                          onChange={(e) => setSelectedPdfId(e.target.value)}
                          className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-2.5 py-1.5 text-xs font-medium text-[var(--text-primary)] focus:border-[var(--accent-green)] focus:outline-none"
                        >
                          {userPdfs.map(p => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                          ))}
                        </select>
                      ) : (
                        <p className="text-[10px] text-[var(--text-secondary)]">No documents. Upload in Library.</p>
                      )}
                    </div>
                  )}

                  {sourceType === 'youtube' && (
                    <div className="mt-3 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3">
                      <label htmlFor="youtube-url" className="mb-1 block text-[11px] font-semibold text-[var(--text-primary)]">
                        YouTube URL
                      </label>
                      <input
                        id="youtube-url"
                        type="url"
                        value={youtubeUrl}
                        onChange={(e) => setYoutubeUrl(e.target.value)}
                        placeholder="https://youtube.com/..."
                        className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-2.5 py-1.5 text-xs font-medium text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent-green)] focus:outline-none"
                      />
                    </div>
                  )}
                </fieldset>

                {/* 3. Level & Language */}
                <div className="mb-6 grid grid-cols-1 gap-4">
                  <div>
                    <label htmlFor="level-select" className="mb-2 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                      Level
                    </label>
                    <select
                      id="level-select"
                      value={level}
                      onChange={(e) => setLevel(e.target.value)}
                      className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2 text-xs font-medium text-[var(--text-primary)] focus:border-[var(--accent-green)] focus:outline-none"
                    >
                      {LEVEL_OPTIONS.map(l => (
                        <option key={l.value} value={l.value}>{l.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="language-select" className="mb-2 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                      Language
                    </label>
                    <select
                      id="language-select"
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2 text-xs font-medium text-[var(--text-primary)] focus:border-[var(--accent-green)] focus:outline-none"
                    >
                      {LANGUAGE_OPTIONS.map(lang => (
                        <option key={lang.value} value={lang.value}>{lang.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* 4. Learning Mode */}
                <fieldset className="mb-6">
                  <legend className="mb-2 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                    Teaching mode
                  </legend>
                  <div className="grid grid-cols-1 gap-2">
                    {MODE_OPTIONS.map(m => (
                      <button
                        key={m.value}
                        type="button"
                        onClick={() => setMode(m.value)}
                        aria-pressed={mode === m.value}
                        className={`rounded-xl border p-3 text-left transition-colors ${
                          mode === m.value
                            ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)]'
                            : 'border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)]'
                        }`}
                      >
                        <p className="text-xs font-semibold text-[var(--text-primary)]">{m.label}</p>
                        <p className="mt-0.5 text-[10px] leading-relaxed text-[var(--text-secondary)]">{m.desc}</p>
                      </button>
                    ))}
                  </div>
                </fieldset>

                <div className="pt-2">
                  <button
                    type="submit"
                    disabled={!topic.trim() || loading}
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--accent-green)] px-4 py-2.5 text-xs font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)] active:translate-y-px disabled:opacity-50"
                  >
                    {loading ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <GraduationCap className="h-4 w-4" aria-hidden="true" />
                    )}
                    <span>Start lesson</span>
                  </button>
                </div>
              </form>
            </div>
          ) : (
            <>
            <div className="overflow-y-auto p-5">

              <div className="mb-4 flex items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-green-light)]">
                    <GraduationCap className="h-5 w-5 text-[var(--accent-green-text)]" aria-hidden="true" />
                  </span>
                  <div className="min-w-0">
                    <h2 className="truncate font-display text-sm font-semibold text-[var(--text-primary)]">
                      {topic || 'Lesson roadmap'}
                    </h2>
                    <span className="text-[11px] font-medium capitalize text-[var(--text-secondary)]">
                      {level} level
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => { setIsSetupOpen(true); setMobileSidebarOpen(true); }}
                  aria-label="Change topic or settings"
                  className="rounded-lg p-1.5 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                >
                  <Plus className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>

              {/* Mastery Progress */}
              <div className="mb-5 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3.5">
                <div className="mb-1.5 flex items-center justify-between text-xs font-semibold">
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
                    style={{ width: `${Math.max(5, overallMastery * 100)}%` }}
                  />
                </div>
              </div>

              {/* Concepts Checklist */}
              <div className="mb-5">
                <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
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
                        className={`rounded-xl border p-2.5 text-xs font-medium transition-colors ${
                          isCurrent
                            ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)] text-[var(--text-primary)]'
                            : isMastered
                            ? 'border-[var(--border)] bg-[var(--bg-secondary)] text-[var(--text-primary)]'
                            : 'border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)]'
                        }`}
                      >
                        <div className="mb-1 flex items-center justify-between gap-2">
                          <span className="truncate font-semibold">{i + 1}. {c.name}</span>
                          {/* Status is never colour-only: each state carries a word or a labelled icon. */}
                          {isMastered ? (
                            <span className="flex shrink-0 items-center gap-1 text-[10px] font-semibold text-[var(--accent-green-text)]">
                              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                              Mastered
                            </span>
                          ) : isCurrent ? (
                            <span className="shrink-0 text-[10px] font-semibold text-[var(--accent-green-text)]">
                              Current
                            </span>
                          ) : (
                            <span className="shrink-0 text-[10px] text-[var(--text-muted)]">Pending</span>
                          )}
                        </div>
                        {c.summary && (
                          <p className="line-clamp-1 text-[11px] text-[var(--text-secondary)]">{c.summary}</p>
                        )}
                      </li>
                    );
                  })}
                </ol>
              </div>

              {/* Detected Misconceptions */}
              {misconceptions.length > 0 && (
                <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3">
                  <h3 className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold text-amber-900">
                    <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" />
                    Focus reminders
                  </h3>
                  <ul className="list-disc space-y-1 pl-4 text-[11px] text-amber-900">
                    {misconceptions.map((m, i) => (
                      <li key={i}>{m}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Export to PPT */}
            <div className="border-t border-[var(--border)] bg-[var(--bg-secondary)] p-4">
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
                  className="flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2.5 text-xs font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)] disabled:opacity-50"
                >
                  {exportingPpt ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                      Generating PPTX
                    </>
                  ) : (
                    <>
                      <Presentation className="h-4 w-4 text-[var(--accent-green-text)]" aria-hidden="true" />
                      Export lesson to PPTX
                    </>
                  )}
                </button>
              )}
            </div>

            </>
          )}
        </aside>

        {/* ══════════════ CENTER TEACHING STUDIO ══════════════ */}
        <main className="relative flex min-w-0 flex-1 flex-col bg-[var(--bg-primary)]">
          {/* Mobile Header */}
          <header className="flex shrink-0 items-center justify-between border-b border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 lg:hidden">
            <div className="min-w-0 flex-1">
              <h2 className="truncate font-display text-sm font-semibold text-[var(--text-primary)]">
                {sessionId ? topic || 'Lesson active' : 'Teach Me'}
              </h2>
            </div>
            <button
              type="button"
              onClick={() => {
                 if (!sessionId) setIsSetupOpen(true);
                 setMobileSidebarOpen(true);
              }}
              className="ml-4 flex shrink-0 items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-1.5 text-xs font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)]"
            >
              {sessionId ? (
                 <>
                   <Target className="h-3.5 w-3.5 text-[var(--accent-green-text)]" />
                   Roadmap
                 </>
              ) : (
                 <>
                   <Plus className="h-3.5 w-3.5 text-[var(--accent-green-text)]" />
                   Configure
                 </>
              )}
            </button>
          </header>

          <div className="flex-1 space-y-6 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">

            {errorBanner && (
              <div
                role="alert"
                className="mx-auto flex max-w-3xl items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
              >
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                <span className="flex-1">{errorBanner}</span>
                <button
                  type="button"
                  onClick={() => setErrorBanner(null)}
                  aria-label="Dismiss error"
                  className="rounded p-0.5 hover:bg-red-100"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
            )}

            {messages.length === 0 && !loading && (
              <div className="mx-auto max-w-xl pt-12 text-center">
                <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--accent-green-light)]">
                  <BrainCircuit className="h-7 w-7 text-[var(--accent-green-text)]" aria-hidden="true" />
                </span>
                <h2 className="mb-2 font-display text-xl font-semibold text-[var(--text-primary)]">
                  Welcome to Teach Me
                </h2>
                <p className="mb-6 text-sm text-[var(--text-secondary)]">
                  An adaptive tutor that explains, checks your understanding and adjusts. Pick a
                  topic, your notes, or a video to begin.
                </p>
                <button
                  type="button"
                  onClick={() => { setIsSetupOpen(true); setMobileSidebarOpen(true); }}
                  className="inline-flex items-center gap-2 rounded-xl bg-[var(--accent-green)] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)] active:translate-y-px"
                >
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  Start new lesson
                </button>
              </div>
            )}

            <div aria-live="polite" aria-busy={loading} className="space-y-6">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${msg.role === 'student' ? 'items-end' : 'items-start'}`}
                >
                  <div className={`max-w-3xl rounded-2xl p-5 ${
                    msg.role === 'student'
                      ? 'rounded-br-none bg-[var(--accent-green-deep)] text-white'
                      : 'rounded-bl-none border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-primary)]'
                  }`}>

                    <div className="mb-2 flex items-center justify-between gap-3">
                      <span className={`text-[11px] font-semibold uppercase tracking-wider ${
                        msg.role === 'student'
                          ? 'text-[var(--accent-green-light)]'
                          : 'text-[var(--accent-green-text)]'
                      }`}>
                        {msg.role === 'student' ? 'You' : 'Professor Genie'}
                      </span>
                      <span className={`text-[10px] tabular-nums ${
                        msg.role === 'student'
                          ? 'text-[var(--accent-green-light)]'
                          : 'text-[var(--text-muted)]'
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
                        {/* Bracketed citations such as [Page 4] or [04:12] are
                            bolded so they stand out from the body text. */}
                        {msg.content.replace(/\[([^\]]+?)\]/g, (match, p1) => {
                          if (p1.match(/^(Page|Slide|Note|Video|\d{1,2}:\d{2})/i)) {
                            return `**[${p1}]**`;
                          }
                          return match;
                        })}
                      </ReactMarkdown>
                    </div>

                    {/* Source Citations */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-3.5 flex flex-wrap items-center gap-1.5 border-t border-[var(--border)] pt-3">
                        <span className="text-[11px] font-semibold text-[var(--text-secondary)]">
                          Sources
                        </span>
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

                    {/* Evaluation Result */}
                    {msg.evaluation && (
                      <div className={`mt-3 rounded-xl border p-3 text-xs font-medium ${evaluationStyle(msg.evaluation.correctness)}`}>
                        <p className="mb-1 flex items-center gap-2 font-semibold">
                          <Award className="h-4 w-4" aria-hidden="true" />
                          <span>
                            Assessment: {msg.evaluation.correctness} ({Math.round(msg.evaluation.score * 100)}%)
                          </span>
                        </p>
                        {msg.evaluation.misconception && (
                          <p className="mt-1 text-[11px]">
                            <strong>Note:</strong> {msg.evaluation.misconception}
                          </p>
                        )}
                      </div>
                    )}

                    {/* Checkpoint */}
                    {msg.checkpoint && msg.checkpoint.enabled && (
                      <div className="mt-4 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
                        <div className="mb-2 flex items-center justify-between gap-2">
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--text-primary)]">
                            <Lightbulb
                              className="h-3.5 w-3.5 text-[var(--accent-green-text)]"
                              aria-hidden="true"
                            />
                            Quick understanding check
                          </span>
                          <span className="rounded-md bg-[var(--bg-card)] px-2 py-0.5 text-[10px] font-semibold uppercase text-[var(--text-secondary)]">
                            {msg.checkpoint.difficulty || 'Medium'}
                          </span>
                        </div>

                        <p className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
                          {msg.checkpoint.question}
                        </p>

                        <div className="flex items-center gap-2">
                          <label htmlFor={`checkpoint-${msg.id}`} className="sr-only">
                            Your answer
                          </label>
                          <input
                            id={`checkpoint-${msg.id}`}
                            type="text"
                            value={checkpointAnswer}
                            onChange={(e) => setCheckpointAnswer(e.target.value)}
                            placeholder="Type your answer"
                            onKeyDown={(e) => e.key === 'Enter' && handleAnswerSubmit()}
                            className="flex-1 rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3.5 py-2 text-xs font-medium text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent-green)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-green)]"
                          />
                          <button
                            type="button"
                            onClick={handleAnswerSubmit}
                            disabled={!checkpointAnswer.trim() || loading}
                            className="rounded-lg bg-[var(--accent-green)] px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)] disabled:opacity-50"
                          >
                            Submit
                          </button>
                        </div>
                      </div>
                    )}

                  </div>
                </div>
              ))}
            </div>

            {loading && (
              <div className="flex items-start gap-4">
                <div className="w-full max-w-2xl space-y-4 rounded-2xl rounded-bl-none border border-[var(--border)] bg-[var(--bg-card)] p-5">
                  <div className="mb-2 flex items-center gap-3">
                    <Loader2
                      className="h-4 w-4 shrink-0 animate-spin text-[var(--accent-green-text)]"
                      aria-hidden="true"
                    />
                    <span className="text-xs font-semibold text-[var(--text-secondary)]">
                      {activeCommand ? 'Adapting the explanation' : 'Thinking'}
                    </span>
                  </div>
                  <div className="space-y-3" aria-hidden="true">
                    <div className="h-4 w-3/4 animate-pulse rounded bg-[var(--bg-secondary)]" />
                    <div className="h-4 w-full animate-pulse rounded bg-[var(--bg-secondary)]" />
                    <div className="h-4 w-5/6 animate-pulse rounded bg-[var(--bg-secondary)]" />
                  </div>
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* ══════════════ BOTTOM ACTION & INPUT BAR ══════════════ */}
          {sessionId && (
            <div className="shrink-0 border-t border-[var(--border)] bg-[var(--bg-card)] p-3 sm:p-4">

              <div
                className="scrollbar-thin mb-2.5 flex items-center gap-1.5 overflow-x-auto pb-2 text-xs"
                role="group"
                aria-label="Lesson actions"
              >
                {QUICK_COMMANDS.map((act) => (
                  <button
                    key={act.cmd}
                    type="button"
                    onClick={() => handleCommand(act.cmd)}
                    disabled={loading}
                    className={`flex items-center gap-1.5 whitespace-nowrap rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors disabled:opacity-50 ${
                      act.primary
                        ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)] text-[var(--accent-green-text)] hover:bg-[var(--accent-green)] hover:text-white'
                        : 'border-[var(--border)] bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]'
                    }`}
                  >
                    {activeCommand === act.cmd ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                    ) : null}
                    {act.label}
                  </button>
                ))}
              </div>

              <form onSubmit={handleSendMessage} className="flex items-center gap-2">
                <label htmlFor="student-input" className="sr-only">
                  Ask a question or explain your doubt
                </label>
                <input
                  id="student-input"
                  type="text"
                  value={studentInput}
                  onChange={(e) => setStudentInput(e.target.value)}
                  placeholder="Ask a question or explain your doubt"
                  disabled={loading}
                  className="flex-1 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-4 py-3 text-sm font-medium text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:bg-[var(--bg-card)] focus:border-[var(--accent-green)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-green)]"
                />
                <button
                  type="submit"
                  disabled={!studentInput.trim() || loading}
                  aria-label="Send message"
                  className="rounded-xl bg-[var(--accent-green)] p-3 text-white transition-colors hover:bg-[var(--accent-green-hover)] active:translate-y-px disabled:opacity-50"
                >
                  <Send className="h-4 w-4" aria-hidden="true" />
                </button>
              </form>
            </div>
          )}

        </main>
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

export default TeachMePage;
