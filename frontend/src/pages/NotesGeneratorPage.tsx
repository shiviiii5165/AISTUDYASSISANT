import React, { useState, useEffect } from 'react';
import { useSearchParams, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText, Sparkles, BookOpen, Layers, CheckCircle2,
  AlertTriangle, Copy, Printer, Trash2, ArrowRight,
  HelpCircle, Lightbulb, Compass, Share2, Search,
  RefreshCw, Check, BookMarked, Eye, Flame, Award
} from 'lucide-react';
import AppLayout from '../components/AppLayout';
import HistorySidebar from '../components/HistorySidebar';
import { useSidebarCollapse } from '../hooks/useSidebarCollapse';
import SEO from '../components/SEO';
import Loader from '../components/Loader';
import {
  generateNotes, listMyNotes, getNote, deleteNote,
  getAvailableContextSources
} from '../lib/notesApi';
import type {
  NotesDocument, NoteSection, ContextSourcesResponse
} from '../lib/notesApi';

const CLASS_OPTIONS = [
  'Class 3', 'Class 4', 'Class 5', 'Class 6',
  'Class 7', 'Class 8', 'Class 9', 'Class 10',
  'Class 11', 'Class 12'
];

const CURRICULUM_OPTIONS = ['CBSE', 'ICSE', 'NCERT', 'State Board', 'IGCSE'];

const SUBJECT_OPTIONS = [
  'Science', 'Mathematics', 'Physics', 'Chemistry',
  'Biology', 'Social Science', 'Computer Science', 'English', 'General'
];

const FORMAT_OPTIONS = [
  { id: 'auto', label: 'Auto (Recommended)', desc: 'Engine automatically selects best hybrid structure' },
  { id: 'learning_notes', label: 'Learning Notes', desc: 'Step-by-step concept walkthrough with examples' },
  { id: 'quick_revision', label: 'Quick Revision', desc: 'High-yield key points for fast 5-minute review' },
  { id: 'exam_preparation', label: 'Exam Prep Notes', desc: 'Targeted definitions, formulas, and common exam questions' },
  { id: 'flowchart', label: 'Process Flowchart', desc: 'Visual sequential breakdown for cycles and mechanisms' },
  { id: 'formula_sheet', label: 'Formula Sheet', desc: 'Formulas, derivations, and units reference card' },
  { id: 'comparison_notes', label: 'Comparison Matrix', desc: 'Side-by-side contrast tables between entities' },
  { id: 'remedial_notes', label: 'Remedial Recap', desc: 'Clarifies misconceptions and foundation gaps' }
];

const NotesGeneratorPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const locState = (location.state as any) || {};
  const { collapsed: historyCollapsed, toggle: toggleHistory } = useSidebarCollapse('notes-history');

  // Input states
  const [mode, setMode] = useState<'topic' | 'lesson_context'>(
    searchParams.get('roadmap_id') || locState.roadmapId ? 'lesson_context' : 'topic'
  );
  const [topic, setTopic] = useState(searchParams.get('topic') || locState.topic || '');
  const [classLevel, setClassLevel] = useState(searchParams.get('class_level') || locState.classLevel || 'Class 10');
  const [subject, setSubject] = useState(searchParams.get('subject') || locState.subject || 'Science');
  const [curriculum, setCurriculum] = useState(locState.curriculum || 'CBSE');
  const [language, setLanguage] = useState(locState.language || 'english');
  const [selectedFormat, setSelectedFormat] = useState('auto');
  const [selectedDepth, setSelectedDepth] = useState('standard');
  const [userInstructions, setUserInstructions] = useState('');

  // Lesson context picker states
  const [contextSources, setContextSources] = useState<ContextSourcesResponse>({ roadmaps: [], teach_sessions: [], quizzes: [] });
  const [selectedRoadmapId, setSelectedRoadmapId] = useState(searchParams.get('roadmap_id') || locState.roadmapId || '');
  const [selectedStageId, setSelectedStageId] = useState(searchParams.get('stage_id') || locState.stageId || '');
  const [selectedTeachSessionId, setSelectedTeachSessionId] = useState(locState.teachSessionId || '');

  // Generation & Active Note states
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeNote, setActiveNote] = useState<NotesDocument | null>(null);
  const [notesHistory, setNotesHistory] = useState<any[]>([]);
  const [copied, setCopied] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load history and available context sources on mount
  useEffect(() => {
    loadNotesList();
    loadContextSources();
  }, []);

  // If URL has note ID, load it
  useEffect(() => {
    const noteIdParam = searchParams.get('id');
    if (noteIdParam) {
      loadSpecificNote(noteIdParam);
    }
  }, [searchParams]);

  const loadNotesList = async () => {
    try {
      const res = await listMyNotes();
      setNotesHistory(res.notes || []);
    } catch (err) {
      console.warn('Could not load notes history:', err);
    }
  };

  const loadContextSources = async () => {
    try {
      const res = await getAvailableContextSources();
      setContextSources(res);
    } catch (err) {
      console.warn('Could not load context sources:', err);
    }
  };

  const loadSpecificNote = async (id: string) => {
    try {
      setIsGenerating(true);
      const doc = await getNote(id);
      setActiveNote(doc);
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || 'Failed to load note');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleGenerate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!topic.trim()) {
      setErrorMessage('Please enter a topic to generate notes.');
      return;
    }

    setIsGenerating(true);
    setErrorMessage(null);

    try {
      const doc = await generateNotes({
        mode,
        topic: topic.trim(),
        class_level: classLevel,
        subject,
        curriculum,
        language,
        roadmap_id: selectedRoadmapId || undefined,
        stage_id: selectedStageId || undefined,
        teach_session_id: selectedTeachSessionId || undefined,
        requested_depth: selectedDepth,
        requested_format: selectedFormat !== 'auto' ? selectedFormat : undefined,
        user_instructions: userInstructions.trim() || undefined,
      });

      setActiveNote(doc);
      await loadNotesList();
    } catch (err: any) {
      console.error('Generation failed:', err);
      setErrorMessage(err?.response?.data?.detail || 'Failed to generate study notes. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDelete = async (noteId: string) => {
    if (!window.confirm('Are you sure you want to delete these notes?')) return;
    try {
      await deleteNote(noteId);
      if (activeNote?.id === noteId) {
        setActiveNote(null);
      }
      await loadNotesList();
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const handleCopyMarkdown = () => {
    if (!activeNote) return;
    let md = `# ${activeNote.title}\n**Subject:** ${activeNote.subject} | **Target:** ${activeNote.class_level} (${activeNote.curriculum})\n\n`;
    activeNote.sections.forEach((sec) => {
      md += `## ${sec.title}\n\n${sec.content}\n\n`;
      if (sec.key_points && sec.key_points.length > 0) {
        md += `### Key Takeaways\n` + sec.key_points.map((p) => `- ${p}`).join('\n') + '\n\n';
      }
      if (sec.callouts && sec.callouts.length > 0) {
        sec.callouts.forEach((c) => {
          md += `> **[${c.type.toUpperCase()}] ${c.title}**: ${c.text}\n\n`;
        });
      }
    });
    navigator.clipboard.writeText(md);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <AppLayout title="AI Study Notes">
      <SEO
        title="AI Notes Generator — Structured Study Notes for Class 3–12 | LearnByGenie"
        description="Generate curriculum-aligned, high-yield revision notes, flowcharts, and worked examples tailored for Class 3–12 students."
      />

      <div className="flex h-full w-full overflow-hidden">
        {/* ── Collapsible History Sidebar ── */}
        <HistorySidebar
          title="My Notes"
          items={notesHistory.map((n) => ({
            id: n.id,
            title: n.topic || n.title || 'Study Note',
            date: n.created_at || ''
          }))}
          selectedId={activeNote?.id || null}
          onSelect={(id) => loadSpecificNote(id)}
          onNew={() => { setActiveNote(null); setTopic(''); }}
          collapsed={historyCollapsed}
          onToggle={toggleHistory}
        />

        {/* ── Main Workspace Area ── */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 bg-[var(--bg-primary)]">
          <div className="mx-auto max-w-5xl space-y-6">

            {/* Error banner */}
            <AnimatePresence>
              {errorMessage && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="flex items-center justify-between rounded-xl bg-red-50 border border-red-200 p-4 text-xs text-red-700 dark:bg-red-950/40 dark:border-red-900"
                >
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 shrink-0 text-red-600" />
                    <span>{errorMessage}</span>
                  </div>
                  <button onClick={() => setErrorMessage(null)} className="text-red-500 hover:text-red-700 font-bold ml-4">✕</button>
                </motion.div>
              )}
            </AnimatePresence>

            {/* ── Input Card (Visible when creating or toggled) ── */}
            {(!activeNote || isGenerating) && (
              <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--border)] pb-4">
                  <div>
                    <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)] flex items-center gap-2">
                      <FileText className="h-5 w-5 text-[var(--accent-blue)]" />
                      AI Notes Generator
                    </h1>
                    <p className="text-xs text-[var(--text-secondary)] mt-1">
                      Generate curriculum-tailored, visual, and high-yield revision notes for Class 3–12 students.
                    </p>
                  </div>

                  {/* Mode Tabs */}
                  <div className="flex items-center rounded-xl bg-[var(--bg-primary)] p-1 border border-[var(--border)]">
                    <button
                      type="button"
                      onClick={() => setMode('topic')}
                      className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                        mode === 'topic'
                          ? 'bg-[var(--bg-card)] text-[var(--accent-blue)] shadow-sm'
                          : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                      }`}
                    >
                      Topic Mode
                    </button>
                    <button
                      type="button"
                      onClick={() => setMode('lesson_context')}
                      className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all flex items-center gap-1.5 ${
                        mode === 'lesson_context'
                          ? 'bg-[var(--bg-card)] text-[var(--accent-blue)] shadow-sm'
                          : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                      }`}
                    >
                      <Layers className="h-3.5 w-3.5" />
                      From Lesson Context
                    </button>
                  </div>
                </div>

                <form onSubmit={handleGenerate} className="mt-6 space-y-5">
                  {/* Lesson Context Selector */}
                  {mode === 'lesson_context' && (
                    <div className="rounded-xl bg-[var(--accent-blue-light)]/40 border border-[var(--accent-blue)]/30 p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-[var(--accent-blue-text)] flex items-center gap-1.5">
                          <Compass className="h-3.5 w-3.5" />
                          Link Existing Teaching Roadmap / Session
                        </span>
                        <span className="text-[10px] text-[var(--text-muted)]">Priority 2: Uses real teacher flow & objectives</span>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label className="text-[11px] font-semibold text-[var(--text-secondary)] block mb-1">
                            Lesson Planner Roadmap
                          </label>
                          <select
                            value={selectedRoadmapId}
                            onChange={(e) => {
                              setSelectedRoadmapId(e.target.value);
                              const r = contextSources.roadmaps.find((item) => item.id === e.target.value);
                              if (r) setTopic(r.topic);
                            }}
                            className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-xs text-[var(--text-primary)] focus:border-[var(--accent-blue)] focus:outline-none"
                          >
                            <option value="">-- Select Existing Roadmap (Optional) --</option>
                            {contextSources.roadmaps.map((r) => (
                              <option key={r.id} value={r.id}>
                                {r.topic} ({r.level})
                              </option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="text-[11px] font-semibold text-[var(--text-secondary)] block mb-1">
                            TeachMe Socratic Session
                          </label>
                          <select
                            value={selectedTeachSessionId}
                            onChange={(e) => {
                              setSelectedTeachSessionId(e.target.value);
                              const s = contextSources.teach_sessions.find((item) => item.id === e.target.value);
                              if (s && !topic) setTopic(s.topic);
                            }}
                            className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-xs text-[var(--text-primary)] focus:border-[var(--accent-blue)] focus:outline-none"
                          >
                            <option value="">-- Select TeachMe Session (Optional) --</option>
                            {contextSources.teach_sessions.map((s) => (
                              <option key={s.id} value={s.id}>
                                {s.topic} ({s.mode})
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Primary Topic Input */}
                  <div>
                    <label className="text-xs font-semibold text-[var(--text-primary)] block mb-1.5">
                      Subject Topic or Chapter Concept <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      placeholder="e.g. Photosynthesis, Newton's Laws of Motion, Fractions & Decimals..."
                      required
                      className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] px-4 py-3 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[var(--accent-blue)] focus:outline-none shadow-sm transition-all"
                    />
                  </div>

                  {/* Pedagogical Selectors Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div>
                      <label className="text-[11px] font-semibold text-[var(--text-secondary)] block mb-1">Class Level</label>
                      <select
                        value={classLevel}
                        onChange={(e) => setClassLevel(e.target.value)}
                        className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-xs text-[var(--text-primary)] focus:border-[var(--accent-blue)] focus:outline-none"
                      >
                        {CLASS_OPTIONS.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] font-semibold text-[var(--text-secondary)] block mb-1">Subject</label>
                      <select
                        value={subject}
                        onChange={(e) => setSubject(e.target.value)}
                        className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-xs text-[var(--text-primary)] focus:border-[var(--accent-blue)] focus:outline-none"
                      >
                        {SUBJECT_OPTIONS.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] font-semibold text-[var(--text-secondary)] block mb-1">Curriculum</label>
                      <select
                        value={curriculum}
                        onChange={(e) => setCurriculum(e.target.value)}
                        className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-xs text-[var(--text-primary)] focus:border-[var(--accent-blue)] focus:outline-none"
                      >
                        {CURRICULUM_OPTIONS.map((cur) => (
                          <option key={cur} value={cur}>{cur}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] font-semibold text-[var(--text-secondary)] block mb-1">Depth</label>
                      <select
                        value={selectedDepth}
                        onChange={(e) => setSelectedDepth(e.target.value)}
                        className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-xs text-[var(--text-primary)] focus:border-[var(--accent-blue)] focus:outline-none"
                      >
                        <option value="standard">Standard Depth</option>
                        <option value="brief">Brief / Quick</option>
                        <option value="detailed">Detailed Study</option>
                        <option value="comprehensive">Comprehensive Mastery</option>
                      </select>
                    </div>
                  </div>

                  {/* Note Structure Selector */}
                  <div>
                    <label className="text-xs font-semibold text-[var(--text-secondary)] block mb-1.5">
                      Target Note Format
                    </label>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      {FORMAT_OPTIONS.map((fmt) => (
                        <button
                          key={fmt.id}
                          type="button"
                          onClick={() => setSelectedFormat(fmt.id)}
                          className={`rounded-xl border p-2.5 text-left transition-all ${
                            selectedFormat === fmt.id
                              ? 'border-[var(--accent-blue)] bg-[var(--accent-blue-light)] text-[var(--accent-blue-text)] shadow-sm'
                              : 'border-[var(--border)] bg-[var(--bg-primary)] hover:border-[var(--text-muted)] text-[var(--text-secondary)]'
                          }`}
                        >
                          <div className="font-bold text-xs">{fmt.label}</div>
                          <div className="text-[10px] text-[var(--text-muted)] truncate mt-0.5">{fmt.desc}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Custom Prompt Instructions */}
                  <div>
                    <label className="text-xs font-semibold text-[var(--text-secondary)] block mb-1">
                      Additional Focus / Custom Teacher Instructions (Optional)
                    </label>
                    <input
                      type="text"
                      value={userInstructions}
                      onChange={(e) => setUserInstructions(e.target.value)}
                      placeholder="e.g. Include 2 numerical problems on acceleration, emphasize difference between mass and weight..."
                      className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-primary)] px-3 py-2 text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[var(--accent-blue)] focus:outline-none"
                    />
                  </div>

                  {/* Submit Button */}
                  <div className="flex justify-end pt-2">
                    <button
                      type="submit"
                      disabled={isGenerating || !topic.trim()}
                      className="flex items-center gap-2 rounded-xl bg-[var(--accent-blue)] px-6 py-3 text-xs font-bold text-white hover:bg-[var(--accent-blue-hover)] transition-all disabled:opacity-50 shadow-md hover:shadow-lg"
                    >
                      {isGenerating ? (
                        <>
                          <Loader size="sm" />
                          <span>Structuring & Generating Notes...</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-4 w-4" />
                          <span>Generate AI Study Notes</span>
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* ── Active Note Document Viewer ── */}
            {activeNote && !isGenerating && (
              <div className="space-y-6">
                {/* Note Document Action Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-sm">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="rounded-md bg-[var(--accent-blue-light)] px-2 py-0.5 text-[11px] font-bold text-[var(--accent-blue-text)]">
                        {activeNote.class_level} • {activeNote.curriculum}
                      </span>
                      <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-[11px] font-bold text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 flex items-center gap-1">
                        <Award className="h-3 w-3" />
                        {Math.round(activeNote.quality.score)}% Quality Score
                      </span>
                    </div>
                    <h2 className="text-lg font-bold text-[var(--text-primary)] mt-1">{activeNote.title}</h2>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setActiveNote(null)}
                      className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
                    >
                      Edit Input
                    </button>
                    <button
                      onClick={handleCopyMarkdown}
                      className="flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs font-semibold text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
                      title="Copy Markdown"
                    >
                      {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
                      <span>{copied ? 'Copied!' : 'Copy'}</span>
                    </button>
                    <button
                      onClick={handlePrint}
                      className="flex items-center gap-1.5 rounded-lg bg-[var(--accent-blue)] px-3.5 py-1.5 text-xs font-bold text-white hover:bg-[var(--accent-blue-hover)]"
                      title="Print or Save as PDF"
                    >
                      <Printer className="h-3.5 w-3.5" />
                      <span>Print / PDF</span>
                    </button>
                  </div>
                </div>

                {/* Document Sections Content */}
                <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 sm:p-8 space-y-8 shadow-sm">
                  {activeNote.sections.map((sec: NoteSection, idx: number) => (
                    <div key={sec.id || idx} className="space-y-4 border-b border-[var(--border)] pb-6 last:border-b-0 last:pb-0">
                      {/* Section Title */}
                      <div className="flex items-center gap-2">
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--accent-blue-light)] text-xs font-bold text-[var(--accent-blue-text)]">
                          {idx + 1}
                        </span>
                        <h3 className="text-base font-bold text-[var(--text-primary)]">{sec.title}</h3>
                      </div>

                      {/* Main Section Content */}
                      <div className="prose prose-sm dark:prose-invert max-w-none text-xs sm:text-sm text-[var(--text-primary)] leading-relaxed whitespace-pre-line">
                        {sec.content}
                      </div>

                      {/* Key Points */}
                      {sec.key_points && sec.key_points.length > 0 && (
                        <div className="rounded-xl bg-[var(--bg-primary)] p-4 border border-[var(--border)] space-y-2">
                          <span className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                            Key Takeaways
                          </span>
                          <ul className="list-disc list-inside space-y-1 text-xs text-[var(--text-secondary)]">
                            {sec.key_points.map((pt, pIdx) => (
                              <li key={pIdx}>{pt}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Visual Flowchart / Mind Map Spec */}
                      {sec.visual_spec && sec.visual_spec.nodes && sec.visual_spec.nodes.length > 0 && (
                        <div className="rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 space-y-3">
                          <span className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                            <Layers className="h-4 w-4 text-[var(--accent-blue)]" />
                            {sec.visual_spec.title || 'Process Sequence'}
                          </span>

                          <div className="flex flex-wrap items-center gap-3">
                            {sec.visual_spec.nodes.map((node, nIdx) => (
                              <React.Fragment key={node.id || nIdx}>
                                <div className="rounded-lg bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 p-3 shadow-xs">
                                  <div className="font-bold text-xs text-[var(--text-primary)]">{node.label}</div>
                                  {node.description && (
                                    <div className="text-[10px] text-[var(--text-muted)] mt-0.5 max-w-[180px]">{node.description}</div>
                                  )}
                                </div>
                                {nIdx < (sec.visual_spec?.nodes?.length || 0) - 1 && (
                                  <ArrowRight className="h-4 w-4 text-slate-400 shrink-0" />
                                )}
                              </React.Fragment>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Callout Boxes (Warning, Misconception, Exam Alert) */}
                      {sec.callouts && sec.callouts.length > 0 && (
                        <div className="space-y-2">
                          {sec.callouts.map((c, cIdx) => (
                            <div
                              key={cIdx}
                              className={`rounded-xl p-3.5 text-xs border flex items-start gap-2.5 ${
                                c.type === 'warning' || c.type === 'misconception'
                                  ? 'bg-amber-50 dark:bg-amber-950/30 border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200'
                                  : c.type === 'exam_alert'
                                  ? 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-900 text-red-900 dark:text-red-200'
                                  : 'bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-900 text-blue-900 dark:text-blue-200'
                              }`}
                            >
                              {c.type === 'warning' || c.type === 'misconception' ? (
                                <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
                              ) : c.type === 'exam_alert' ? (
                                <Flame className="h-4 w-4 shrink-0 text-red-600 mt-0.5" />
                              ) : (
                                <Lightbulb className="h-4 w-4 shrink-0 text-blue-600 mt-0.5" />
                              )}
                              <div>
                                <div className="font-bold">{c.title}</div>
                                <div className="mt-0.5 leading-relaxed">{c.text}</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Examples */}
                      {sec.examples && sec.examples.length > 0 && (
                        <div className="rounded-xl bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900 p-3.5 space-y-1.5">
                          <span className="text-xs font-bold text-emerald-900 dark:text-emerald-200 flex items-center gap-1.5">
                            <BookOpen className="h-3.5 w-3.5 text-emerald-600" />
                            Worked Example
                          </span>
                          {sec.examples.map((ex, exIdx) => (
                            <p key={exIdx} className="text-xs text-emerald-950 dark:text-emerald-300 leading-relaxed">
                              {ex}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Quality Auditor Report Footnote */}
                <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-xs text-[var(--text-secondary)] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    <span>Quality Audited: <strong>{activeNote.quality.score}/100</strong> across Accuracy, Curriculum Alignment, and Misconception Coverage.</span>
                  </div>
                  {activeNote.quality.feedback && activeNote.quality.feedback.length > 0 && (
                    <span className="text-[11px] text-[var(--text-muted)]">{activeNote.quality.feedback[0]}</span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

export default NotesGeneratorPage;
