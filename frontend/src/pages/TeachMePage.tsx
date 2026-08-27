import React, { useState, useEffect, useRef } from 'react';
import { 
  GraduationCap, Sparkles, Globe, FileText, BookOpen, 
  CheckCircle2, AlertCircle, ArrowRight, RotateCcw, Lightbulb,
  HelpCircle, ChevronRight, Download, Send, Loader2, PlayCircle, 
  Layers, Compass, Award, Target, MessageSquare, Plus, CheckSquare, 
  ExternalLink, BrainCircuit, Presentation
} from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { useAuthStore } from '../store/useAuthStore';
import { fetchPdfs, type PDFDocument } from '../lib/api';
import UpgradeModal from '../components/billing/UpgradeModal';

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
  { value: 'interactive_teacher', label: 'Interactive Teacher', desc: 'Active explanation, micro-checks & adaptation' },
  { value: 'learn_from_source', label: 'Learn From Source', desc: 'Strictly grounded in your uploaded documents' },
  { value: 'socratic_teacher', label: 'Socratic Tutor', desc: 'Guided inquiry & thought-provoking clues' },
  { value: 'exam_coach', label: 'Exam Coach', desc: 'Definitions, formulas, scoring points & pitfalls' },
  { value: 'revision', label: 'Quick Revision', desc: 'High-speed intuition & recall checkpoints' },
  { value: 'deep_dive', label: 'Deep Dive', desc: 'Underlying mechanics & edge case trade-offs' },
];

const LANGUAGE_OPTIONS = [
  { value: 'english', label: 'English' },
  { value: 'hindi', label: 'Hindi' },
  { value: 'hinglish', label: 'Hinglish' },
];

const DEPTH_OPTIONS = [
  { value: 'quick', label: 'Quick' },
  { value: 'normal', label: 'Normal' },
  { value: 'deep', label: 'Deep' },
  { value: 'exam', label: 'Exam Focused' },
];

const TOPIC_SUGGESTIONS = [
  'TCP Three-Way Handshake & Connection Teardown',
  'Database Normalization: 1NF to BCNF with Functional Dependencies',
  'Raft Distributed Consensus Algorithm',
  'Transformers & Multi-Head Self-Attention Mechanics',
  'Virtual Memory: Page Tables & TLB Translation',
];

const TeachMePage: React.FC = () => {
  const { user: currentUser } = useAuthStore();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isSetupOpen, setIsSetupOpen] = useState<boolean>(true);
  
  // Setup Parameters
  const [topic, setTopic] = useState<string>('');
  const [level, setLevel] = useState<string>('btech');
  const [language, setLanguage] = useState<string>('english');
  const [mode, setMode] = useState<string>('interactive_teacher');
  const [depth, setDepth] = useState<string>('normal');
  const [sourceType, setSourceType] = useState<string>('topic');
  const [selectedPdfId, setSelectedPdfId] = useState<string>('');
  const [youtubeUrl, setYoutubeUrl] = useState<string>('');
  
  // Data State
  const [userPdfs, setUserPdfs] = useState<PDFDocument[]>([]);
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [currentConceptId, setCurrentConceptId] = useState<string>('');
  const [overallMastery, setOverallMastery] = useState<number>(0.0);
  const [misconceptions, setMisconceptions] = useState<string[]>([]);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  
  // Input State
  const [studentInput, setStudentInput] = useState<string>('');
  const [checkpointAnswer, setCheckpointAnswer] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [exportingPpt, setExportingPpt] = useState<boolean>(false);
  const [pptDownloadUrl, setPptDownloadUrl] = useState<string | null>(null);
  const [showUpgradeModal, setShowUpgradeModal] = useState<boolean>(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

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
  const handleStartSession = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!topic.trim() || loading) return;

    setLoading(true);
    setIsSetupOpen(false);
    setMessages([]);
    setPptDownloadUrl(null);

    const token = useAuthStore.getState().session?.access_token;
    const apiUrl = import.meta.env.VITE_API_URL || '';

    try {
      const sourceIds = (sourceType !== 'topic' && selectedPdfId) ? [selectedPdfId] : [];
      
      const payload = {
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
      alert(`Error starting lesson: ${err.message}`);
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

    setLoading(true);
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
    }
  };

  // Export to PPT
  const handleExportPpt = async () => {
    if (!sessionId || exportingPpt) return;
    setExportingPpt(true);
    setPptDownloadUrl(null);

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
      alert('Could not export to PowerPoint. Please try again.');
    } finally {
      setExportingPpt(false);
    }
  };

  const getMasteryBadgeColor = (score: number) => {
    if (score >= 0.85) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    if (score >= 0.50) return 'bg-blue-50 text-blue-700 border-blue-200';
    return 'bg-amber-50 text-amber-700 border-amber-200';
  };

  return (
    <AppLayout title="Teach Me — Adaptive AI University Tutor">
      <SEO 
        title="Teach Me — Interactive Adaptive AI Teacher | TeachGenie" 
        description="Experience an interactive university tutor that explains concepts, asks checkpoint questions, diagnoses misconceptions, adapts strategies, and tracks mastery."
      />

      <div className="flex h-[calc(100vh-64px)] bg-[#F8FAFC] overflow-hidden">
        
        {/* ══════════════ LEFT ROADMAP & MASTERY PANEL ══════════════ */}
        <aside className="w-80 border-r border-slate-200 bg-white hidden lg:flex flex-col shrink-0 justify-between">
          <div className="p-5 overflow-y-auto">
            
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 font-bold">
                  <GraduationCap className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 truncate max-w-[170px]">{topic || 'Lesson Roadmap'}</h3>
                  <span className="text-[11px] text-slate-500 font-medium capitalize">{level} Level</span>
                </div>
              </div>
              <button
                onClick={() => setIsSetupOpen(true)}
                className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold cursor-pointer"
                title="Change Topic or Settings"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>

            {/* Mastery Progress */}
            <div className="p-3.5 bg-slate-50 border border-slate-200/80 rounded-xl mb-5">
              <div className="flex items-center justify-between text-xs font-bold mb-1.5">
                <span className="text-slate-700 flex items-center gap-1.5">
                  <Target className="w-3.5 h-3.5 text-blue-600" /> Topic Mastery
                </span>
                <span className="text-blue-700">{Math.round(overallMastery * 100)}%</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out" 
                  style={{ width: `${Math.max(5, overallMastery * 100)}%` }}
                />
              </div>
            </div>

            {/* Concepts Checklist */}
            <div className="mb-5">
              <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Lesson Concepts</h4>
              <div className="space-y-1.5">
                {concepts.map((c, i) => {
                  const isCurrent = c.id === currentConceptId;
                  const isMastered = c.status === 'mastered' || c.mastery_score >= 0.85;

                  return (
                    <div
                      key={c.id}
                      className={`p-2.5 rounded-xl border text-xs font-medium transition-all ${
                        isCurrent
                          ? 'border-blue-600 bg-blue-50/60 text-blue-900 shadow-xs'
                          : isMastered
                          ? 'border-emerald-200 bg-emerald-50/40 text-slate-700'
                          : 'border-slate-100 bg-white text-slate-500'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold truncate max-w-[180px]">{i + 1}. {c.name}</span>
                        {isMastered ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                        ) : isCurrent ? (
                          <span className="w-2 h-2 rounded-full bg-blue-600 animate-ping" />
                        ) : (
                          <span className="text-[10px] text-slate-400">Pending</span>
                        )}
                      </div>
                      {c.summary && <p className="text-[11px] text-slate-500 line-clamp-1">{c.summary}</p>}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Detected Misconceptions */}
            {misconceptions.length > 0 && (
              <div className="p-3 bg-amber-50/80 border border-amber-200 rounded-xl mb-4">
                <h5 className="text-[11px] font-bold text-amber-900 flex items-center gap-1.5 mb-1.5">
                  <AlertCircle className="w-3.5 h-3.5 text-amber-600" /> Focus Reminders
                </h5>
                <ul className="text-[11px] text-amber-800 space-y-1 list-disc pl-4">
                  {misconceptions.map((m, i) => (
                    <li key={i}>{m}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Export to PPT / Quick Actions */}
          <div className="p-4 border-t border-slate-100 bg-slate-50/50">
            {pptDownloadUrl ? (
              <a
                href={pptDownloadUrl}
                download={`${topic.replace(/[^a-zA-Z0-9]/g, '_')}_presentation.pptx`}
                className="w-full py-2.5 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs shadow-xs flex items-center justify-center gap-2 transition-colors cursor-pointer"
              >
                <Download className="w-4 h-4" /> Download Lesson PPTX
              </a>
            ) : (
              <button
                onClick={handleExportPpt}
                disabled={exportingPpt || !sessionId}
                className="w-full py-2.5 px-3 bg-white hover:bg-slate-100 border border-slate-200 text-slate-800 rounded-xl font-bold text-xs shadow-xs flex items-center justify-center gap-2 transition-colors cursor-pointer disabled:opacity-50"
              >
                {exportingPpt ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-blue-600" /> Generating PPTX...
                  </>
                ) : (
                  <>
                    <Presentation className="w-4 h-4 text-blue-600" /> Export Lesson to PPTX
                  </>
                )}
              </button>
            )}
          </div>
        </aside>

        {/* ══════════════ CENTER INTERACTIVE TEACHING STUDIO ══════════════ */}
        <main className="flex-1 flex flex-col min-w-0 bg-[#F8FAFC] relative">
          
          {/* Main Conversational Feed */}
          <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
            
            {messages.length === 0 && !loading && (
              <div className="max-w-xl mx-auto text-center pt-20">
                <div className="w-14 h-14 rounded-2xl bg-blue-100/70 border border-blue-200 flex items-center justify-center text-blue-700 mx-auto mb-4">
                  <BrainCircuit className="w-7 h-7" />
                </div>
                <h2 className="text-xl font-bold text-slate-900 mb-2">Welcome to Teach Me</h2>
                <p className="text-sm text-slate-600 mb-6">
                  Your personalized adaptive university tutor. Pick a topic, notes, or YouTube video to begin interactive learning.
                </p>
                <button
                  onClick={() => setIsSetupOpen(true)}
                  className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-sm shadow-xs cursor-pointer inline-flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" /> Start New Lesson
                </button>
              </div>
            )}

            {messages.map((msg) => (
              <div key={msg.id} className={`flex flex-col ${msg.role === 'student' ? 'items-end' : 'items-start'}`}>
                
                {/* Message Container */}
                <div className={`max-w-3xl rounded-2xl p-5 shadow-xs transition-all ${
                  msg.role === 'student'
                    ? 'bg-blue-600 text-white rounded-br-none'
                    : 'bg-white border border-slate-200/90 text-slate-900 rounded-bl-none'
                }`}>
                  
                  {/* Role Header */}
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <span className={`text-[11px] font-bold uppercase tracking-wider ${msg.role === 'student' ? 'text-blue-100' : 'text-blue-600'}`}>
                      {msg.role === 'student' ? 'You (Student)' : '🎓 Professor Genie'}
                    </span>
                    <span className={`text-[10px] ${msg.role === 'student' ? 'text-blue-200' : 'text-slate-400'}`}>
                      {msg.timestamp}
                    </span>
                  </div>

                  {/* Body Text */}
                  <div className="text-sm sm:text-base leading-relaxed whitespace-pre-wrap font-normal">
                    {msg.content}
                  </div>

                  {/* Source Citations */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-3.5 pt-3 border-t border-slate-100 flex flex-wrap items-center gap-1.5">
                      <span className="text-[11px] font-semibold text-slate-400">Sources:</span>
                      {msg.citations.map((cite, ci) => (
                        <span key={ci} className="inline-flex items-center px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 text-[11px] font-medium border border-slate-200">
                          {cite}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Evaluation Result if present */}
                  {msg.evaluation && (
                    <div className={`mt-3 p-3 rounded-xl border text-xs font-medium ${
                      msg.evaluation.correctness === 'correct'
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                        : msg.evaluation.correctness === 'partial'
                        ? 'bg-blue-50 border-blue-200 text-blue-900'
                        : 'bg-amber-50 border-amber-200 text-amber-900'
                    }`}>
                      <div className="flex items-center gap-2 font-bold mb-1">
                        <Award className="w-4 h-4" />
                        <span>Assessment: {msg.evaluation.correctness.toUpperCase()} ({Math.round(msg.evaluation.score * 100)}%)</span>
                      </div>
                      {msg.evaluation.misconception && (
                        <p className="text-[11px] mt-1 opacity-90">
                          <strong>Note:</strong> {msg.evaluation.misconception}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Checkpoint Embedded Card */}
                  {msg.checkpoint && msg.checkpoint.enabled && (
                    <div className="mt-4 p-4 bg-blue-50/70 border border-blue-200 rounded-xl">
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className="inline-flex items-center gap-1 text-xs font-bold text-blue-900">
                          <Lightbulb className="w-3.5 h-3.5 text-blue-600" /> Quick Understanding Check
                        </span>
                        <span className="text-[10px] font-semibold uppercase px-2 py-0.5 bg-blue-100 text-blue-800 rounded-md">
                          {msg.checkpoint.difficulty || 'Medium'}
                        </span>
                      </div>
                      
                      <p className="text-sm font-semibold text-slate-900 mb-3">
                        {msg.checkpoint.question}
                      </p>

                      {/* Interactive Answer Input */}
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={checkpointAnswer}
                          onChange={(e) => setCheckpointAnswer(e.target.value)}
                          placeholder="Type your answer to verify understanding..."
                          onKeyDown={(e) => e.key === 'Enter' && handleAnswerSubmit()}
                          className="flex-1 px-3.5 py-2 bg-white border border-blue-200 rounded-lg text-xs font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <button
                          onClick={handleAnswerSubmit}
                          disabled={!checkpointAnswer.trim() || loading}
                          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold text-xs shadow-xs cursor-pointer disabled:opacity-50"
                        >
                          Submit
                        </button>
                      </div>
                    </div>
                  )}

                </div>
              </div>
            ))}

            {loading && (
              <div className="flex items-center gap-3 p-4 bg-white border border-slate-200 rounded-2xl max-w-sm shadow-xs animate-pulse">
                <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
                <span className="text-xs font-semibold text-slate-700">Professor Genie is thinking & adapting...</span>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* ══════════════ BOTTOM ACTION & INPUT BAR ══════════════ */}
          {sessionId && (
            <div className="border-t border-slate-200 bg-white p-3 sm:p-4 shrink-0 shadow-xs">
              
              {/* Quick Action Pills */}
              <div className="flex items-center gap-1.5 overflow-x-auto pb-2 mb-2.5 text-xs">
                {[
                  { label: '🔄 Explain Again', cmd: 'explain_again' },
                  { label: '✨ Make Simpler', cmd: 'make_simpler' },
                  { label: '🔬 Go Deeper', cmd: 'go_deeper' },
                  { label: '💡 Give Example', cmd: 'give_example' },
                  { label: '📊 Show Visually', cmd: 'show_visual' },
                  { label: '🗣️ Explain It Back', cmd: 'explain_it_back' },
                  { label: '❓ Ask Question', cmd: 'ask_question' },
                  { label: '📋 Exam Points', cmd: 'exam_points' },
                  { label: '➡️ Continue Next Concept', cmd: 'continue', primary: true },
                ].map((act, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => handleCommand(act.cmd)}
                    disabled={loading}
                    className={`px-3 py-1.5 rounded-lg border font-semibold whitespace-nowrap transition-colors cursor-pointer text-xs ${
                      act.primary
                        ? 'border-blue-600 bg-blue-50 text-blue-700 hover:bg-blue-100'
                        : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    {act.label}
                  </button>
                ))}
              </div>

              {/* Message Input Box */}
              <form onSubmit={handleSendMessage} className="flex items-center gap-2">
                <input
                  type="text"
                  value={studentInput}
                  onChange={(e) => setStudentInput(e.target.value)}
                  placeholder="Ask a question or explain your doubt..."
                  disabled={loading}
                  className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="submit"
                  disabled={!studentInput.trim() || loading}
                  className="p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold shadow-xs cursor-pointer disabled:opacity-50"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </div>
          )}

        </main>
      </div>

      {/* ══════════════ SETUP MODAL ══════════════ */}
      {isSetupOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 sm:p-8 shadow-xl border border-slate-200">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                  <BrainCircuit className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-900">Configure Your Lesson</h2>
                  <p className="text-xs text-slate-500">Choose your study material, level, and learning mode.</p>
                </div>
              </div>
              {sessionId && (
                <button onClick={() => setIsSetupOpen(false)} className="text-slate-400 hover:text-slate-600 text-lg p-1">✕</button>
              )}
            </div>

            <form onSubmit={handleStartSession}>
              {/* 1. Topic */}
              <div className="mb-5">
                <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider mb-1.5">
                  Topic or Concept to Master
                </label>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. Operating System Deadlocks & Banker's Algorithm"
                  required
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />

                <div className="mt-2 flex flex-wrap gap-1.5 items-center">
                  <span className="text-[11px] text-slate-400 font-medium">Quick Ideas:</span>
                  {TOPIC_SUGGESTIONS.slice(0, 3).map((t, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setTopic(t)}
                      className="text-[11px] px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 hover:bg-slate-200 cursor-pointer"
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              {/* 2. Knowledge Source */}
              <div className="mb-5">
                <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">
                  Knowledge Grounding Source
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { id: 'topic', label: 'Topic Only', icon: Globe },
                    { id: 'pdf', label: 'Uploaded Notes', icon: FileText },
                    { id: 'youtube', label: 'YouTube Video', icon: Youtube },
                    { id: 'web', label: 'Topic + Web', icon: Sparkles },
                  ].map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => setSourceType(s.id)}
                      className={`p-3 rounded-xl border text-center font-bold text-xs flex flex-col items-center gap-1.5 cursor-pointer transition-colors ${
                        sourceType === s.id
                          ? 'border-blue-600 bg-blue-50/70 text-blue-900 ring-1 ring-blue-600'
                          : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      <s.icon className={`w-4 h-4 ${sourceType === s.id ? 'text-blue-600' : 'text-slate-400'}`} />
                      <span>{s.label}</span>
                    </button>
                  ))}
                </div>

                {/* PDF Dropdown */}
                {sourceType === 'pdf' && (
                  <div className="mt-3 p-3 bg-slate-50 border border-slate-200 rounded-xl">
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Select Document from Library:</label>
                    {userPdfs.length > 0 ? (
                      <select
                        value={selectedPdfId}
                        onChange={(e) => setSelectedPdfId(e.target.value)}
                        className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      >
                        {userPdfs.map(p => (
                          <option key={p.id} value={p.id}>📄 {p.name} ({p.page_count || 1} pages)</option>
                        ))}
                      </select>
                    ) : (
                      <p className="text-xs text-slate-500">No uploaded documents found. You can upload in your Library or learn with Topic Only.</p>
                    )}
                  </div>
                )}

                {/* YouTube Input */}
                {sourceType === 'youtube' && (
                  <div className="mt-3 p-3 bg-red-50/60 border border-red-200 rounded-xl">
                    <label className="block text-xs font-semibold text-red-900 mb-1">Enter Public YouTube Video URL:</label>
                    <input
                      type="url"
                      value={youtubeUrl}
                      onChange={(e) => setYoutubeUrl(e.target.value)}
                      placeholder="https://www.youtube.com/watch?v=..."
                      className="w-full px-3 py-2 bg-white border border-red-200 rounded-lg text-xs font-medium text-slate-900 focus:outline-none focus:ring-1 focus:ring-red-500"
                    />
                  </div>
                )}
              </div>

              {/* 3. Level & Language */}
              <div className="grid grid-cols-2 gap-3 mb-5">
                <div>
                  <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider mb-1.5">Academic Level</label>
                  <select
                    value={level}
                    onChange={(e) => setLevel(e.target.value)}
                    className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    {LEVEL_OPTIONS.map(l => (
                      <option key={l.value} value={l.value}>{l.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider mb-1.5">Language</label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    {LANGUAGE_OPTIONS.map(lang => (
                      <option key={lang.value} value={lang.value}>{lang.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* 4. Learning Mode */}
              <div className="mb-6">
                <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">Teaching Style Mode</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {MODE_OPTIONS.map(m => (
                    <button
                      key={m.value}
                      type="button"
                      onClick={() => setMode(m.value)}
                      className={`p-3 rounded-xl border text-left transition-colors cursor-pointer ${
                        mode === m.value
                          ? 'border-blue-600 bg-blue-50/70 ring-1 ring-blue-600'
                          : 'border-slate-200 bg-white hover:bg-slate-50'
                      }`}
                    >
                      <p className="text-xs font-bold text-slate-900">{m.label}</p>
                      <p className="text-[11px] text-slate-500">{m.desc}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={!topic.trim() || loading}
                className="w-full py-3.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-sm shadow-xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <GraduationCap className="w-5 h-5" />}
                <span>Start Interactive Lesson</span>
              </button>
            </form>
          </div>
        </div>
      )}

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
