import React, { useState, useEffect } from 'react';
import {
  Compass,
  Target,
  Wrench,
  BookOpen,
  HelpCircle,
  Lightbulb,
  CheckCircle2,
  XCircle,
  ArrowRight,
  RefreshCw,
  Info,
  ChevronRight,
  GraduationCap,
  Sparkles,
  Layers,
  ArrowLeft,
  AlertTriangle,
  RotateCcw
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import { practiceApi } from '../lib/practiceApi';
import type {
  PracticeMode,
  DifficultyBand,
  PracticeSession,
  StudentPracticeItemView,
  PracticeFeedback,
  PracticeSelectionExplanation,
  SessionSummary
} from '../types/practice';

const SUBJECT_OPTIONS = [
  { id: 'Mathematics', name: 'Mathematics', stage: 'Class 3–12', icon: '📐' },
  { id: 'Physics', name: 'Physics', stage: 'Class 9–12 / JEE', icon: '⚡' },
  { id: 'Chemistry', name: 'Chemistry', stage: 'Class 9–12 / NEET', icon: '🧪' },
  { id: 'Biology', name: 'Biology', stage: 'Class 8–12 / NEET', icon: '🧬' },
  { id: 'Science', name: 'Integrated Science', stage: 'Class 3–8', icon: '🔬' },
  { id: 'Computer Science', name: 'Computer Science', stage: 'UG Coursework', icon: '💻' }
];

const MODE_CONFIGS = [
  {
    mode: 'ADAPTIVE' as PracticeMode,
    title: 'Adaptive Learning',
    description: 'Engine selects current concepts dynamically based on your readiness and mastery graph.',
    icon: Compass,
    accent: 'blue'
  },
  {
    mode: 'REPAIR' as PracticeMode,
    title: 'Repair & Strengthen',
    description: 'Prioritizes open mistake patterns and blocked prerequisite foundations.',
    icon: Wrench,
    accent: 'amber'
  },
  {
    mode: 'FOCUSED' as PracticeMode,
    title: 'Focused Topic',
    description: 'Deep dive into a specific topic or core syllabus chapter of your choice.',
    icon: Target,
    accent: 'emerald'
  },
  {
    mode: 'EXAM_PRACTICE' as PracticeMode,
    title: 'Exam Practice',
    description: 'Board and entrance-aligned question formats with rigorous conceptual calibration.',
    icon: GraduationCap,
    accent: 'purple'
  }
];

export const PracticePage: React.FC = () => {
  const navigate = useNavigate();

  // Session state
  const [session, setSession] = useState<PracticeSession | null>(null);
  const [currentItem, setCurrentItem] = useState<StudentPracticeItemView | null>(null);
  const [feedback, setFeedback] = useState<PracticeFeedback | null>(null);
  const [summary, setSummary] = useState<SessionSummary | null>(null);

  // Interaction state
  const [selectedAnswer, setSelectedAnswer] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Hints & Explainability modals
  const [revealedHints, setRevealedHints] = useState<string[]>([]);
  const [hintLoading, setHintLoading] = useState<boolean>(false);
  const [explanation, setExplanation] = useState<PracticeSelectionExplanation | null>(null);
  const [showExplainModal, setShowExplainModal] = useState<boolean>(false);

  // Setup options (before starting)
  const [selectedSubject, setSelectedSubject] = useState<string>('Mathematics');
  const [selectedMode, setSelectedMode] = useState<PracticeMode>('ADAPTIVE');
  const [questionBudget, setQuestionBudget] = useState<number>(10);
  const [juniorTone, setJuniorTone] = useState<boolean>(false);

  // Start a new practice session
  const handleStartSession = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await practiceApi.startSession({
        subject: selectedSubject,
        mode: selectedMode,
        question_budget: questionBudget,
        grade_band: juniorTone ? 'primary' : 'secondary'
      });
      setSession(res.session);
      setCurrentItem(res.current_item);
      setFeedback(null);
      setSummary(null);
      setSelectedAnswer('');
      setRevealedHints(res.current_item?.hints_revealed || []);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not start practice session. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Submit student response
  const handleSubmitAnswer = async () => {
    if (!session || !currentItem || !selectedAnswer.trim() || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const fb = await practiceApi.submitResponse(session.id, {
        item_id: currentItem.id,
        question_index: session.question_index,
        student_response: selectedAnswer.trim()
      });
      setFeedback(fb);

      if (fb.session_completed) {
        // Fetch session outcome summary
        const sumRes = await practiceApi.getSessionSummary(session.id);
        setSummary(sumRes);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to submit response. Please retry.');
    } finally {
      setSubmitting(false);
    }
  };

  // Move to next question
  const handleNextQuestion = async () => {
    if (!session) return;
    setLoading(true);
    setError(null);
    try {
      const nextItem = await practiceApi.getNextItem(session.id);
      if (!nextItem) {
        // Session complete
        const sumRes = await practiceApi.getSessionSummary(session.id);
        setSummary(sumRes);
        setCurrentItem(null);
      } else {
        // Updated session status
        const updatedSess = await practiceApi.getSession(session.id);
        setSession(updatedSess);
        setCurrentItem(nextItem);
        setFeedback(null);
        setSelectedAnswer('');
        setRevealedHints(nextItem.hints_revealed || []);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not load next item.');
    } finally {
      setLoading(false);
    }
  };

  // Request next progressive hint
  const handleRequestHint = async () => {
    if (!session || !currentItem || hintLoading) return;
    setHintLoading(true);
    try {
      const res = await practiceApi.requestHint(session.id, currentItem.id);
      setRevealedHints(prev => [...prev, res.hint]);
    } catch (err) {
      // Hints exhausted or error
    } finally {
      setHintLoading(false);
    }
  };

  // Query selection explainability
  const handleFetchExplanation = async () => {
    if (!session) return;
    try {
      const exp = await practiceApi.explainSelection(session.id);
      setExplanation(exp);
      setShowExplainModal(true);
    } catch (err) {
      // Explanation unavailable
    }
  };

  // Reset to setup view
  const handleResetSession = () => {
    setSession(null);
    setCurrentItem(null);
    setFeedback(null);
    setSummary(null);
    setSelectedAnswer('');
    setRevealedHints([]);
    setExplanation(null);
  };

  return (
    <AppLayout title="Adaptive Practice">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* ─── 1. SESSION SETUP VIEW ─────────────────────────────────────────── */}
        {!session && (
          <div className="space-y-8 animate-fade-in">
            {/* Header */}
            <div className="border-b border-border pb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
                  <span className="p-2.5 rounded-xl bg-blue-500/10 text-blue-500 border border-blue-500/20">
                    <Compass className="w-6 h-6" />
                  </span>
                  Adaptive Practice
                </h1>
                <p className="text-sm text-muted-foreground mt-2 max-w-xl">
                  Dynamic, skill-driven learning loop calibrated to your knowledge graph, prerequisite readiness, and repair memory.
                </p>
              </div>

              {/* Age / Tone Toggle */}
              <div className="flex items-center gap-2 bg-muted/40 p-1.5 rounded-lg border border-border text-xs">
                <button
                  type="button"
                  onClick={() => setJuniorTone(false)}
                  className={`px-3 py-1.5 rounded-md font-medium transition-all ${
                    !juniorTone ? 'bg-background shadow-xs text-foreground' : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Standard Mode
                </button>
                <button
                  type="button"
                  onClick={() => setJuniorTone(true)}
                  className={`px-3 py-1.5 rounded-md font-medium transition-all ${
                    juniorTone ? 'bg-background shadow-xs text-foreground' : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Junior (Class 3–5)
                </button>
              </div>
            </div>

            {error && (
              <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Subject Selector */}
            <div className="space-y-3">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Select Subject
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {SUBJECT_OPTIONS.map(subj => {
                  const isSelected = selectedSubject === subj.id;
                  return (
                    <button
                      key={subj.id}
                      type="button"
                      onClick={() => setSelectedSubject(subj.id)}
                      className={`p-4 rounded-xl border text-left transition-all flex items-start gap-3.5 ${
                        isSelected
                          ? 'border-blue-500/50 bg-blue-500/5 shadow-xs'
                          : 'border-border bg-card hover:border-border/80 hover:bg-muted/30'
                      }`}
                    >
                      <span className="text-2xl">{subj.icon}</span>
                      <div>
                        <div className="font-semibold text-sm text-foreground">{subj.name}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">{subj.stage}</div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Mode Selector */}
            <div className="space-y-3">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Practice Mode
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {MODE_CONFIGS.map(cfg => {
                  const isSelected = selectedMode === cfg.mode;
                  const Icon = cfg.icon;
                  return (
                    <button
                      key={cfg.mode}
                      type="button"
                      onClick={() => setSelectedMode(cfg.mode)}
                      className={`p-5 rounded-xl border text-left transition-all ${
                        isSelected
                          ? 'border-blue-500/60 bg-blue-500/5 shadow-xs ring-1 ring-blue-500/20'
                          : 'border-border bg-card hover:border-border/80 hover:bg-muted/20'
                      }`}
                    >
                      <div className="flex items-center gap-3 mb-2">
                        <div className={`p-2 rounded-lg ${isSelected ? 'bg-blue-500/20 text-blue-500' : 'bg-muted text-muted-foreground'}`}>
                          <Icon className="w-4 h-4" />
                        </div>
                        <span className="font-semibold text-sm text-foreground">{cfg.title}</span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {cfg.description}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Question Budget */}
            <div className="space-y-3">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Session Question Budget
              </label>
              <div className="flex gap-3">
                {[
                  { count: 5, label: 'Quick (5 Questions)' },
                  { count: 10, label: 'Standard (10 Questions)' },
                  { count: 15, label: 'Deep (15 Questions)' }
                ].map(b => (
                  <button
                    key={b.count}
                    type="button"
                    onClick={() => setQuestionBudget(b.count)}
                    className={`flex-1 py-3 px-4 rounded-xl border text-xs font-medium transition-all ${
                      questionBudget === b.count
                        ? 'border-blue-500 bg-blue-500/10 text-foreground font-semibold shadow-xs'
                        : 'border-border bg-card text-muted-foreground hover:bg-muted/30'
                    }`}
                  >
                    {b.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Start CTA */}
            <div className="pt-4">
              <button
                type="button"
                onClick={handleStartSession}
                disabled={loading}
                className="w-full py-4 px-6 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold flex items-center justify-center gap-2.5 transition-all shadow-md hover:shadow-lg disabled:opacity-50"
              >
                {loading ? (
                  <RefreshCw className="w-5 h-5 animate-spin" />
                ) : (
                  <>
                    <span>Start Practice Session</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* ─── 2. ACTIVE PRACTICE QUESTION VIEW ──────────────────────────────── */}
        {session && currentItem && !summary && (
          <div className="space-y-6 animate-fade-in">
            {/* Top Navigation Bar */}
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleResetSession}
                  className="p-1.5 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
                  title="Exit session"
                >
                  <ArrowLeft className="w-4 h-4" />
                </button>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-foreground">{session.subject}</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-500 border border-blue-500/20 font-medium">
                      {session.mode}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground border border-border font-medium">
                      {session.current_difficulty}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    Question {currentItem.sequence_number} of {currentItem.total_budget}
                  </div>
                </div>
              </div>

              {/* Explainability trigger (§41) */}
              <button
                type="button"
                onClick={handleFetchExplanation}
                className="flex items-center gap-1.5 text-xs text-blue-500 hover:text-blue-400 font-medium px-3 py-1.5 rounded-lg hover:bg-blue-500/10 transition-all border border-blue-500/20"
              >
                <HelpCircle className="w-3.5 h-3.5" />
                <span>Why this question?</span>
              </button>
            </div>

            {/* Discrete Progress Bar */}
            <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                style={{
                  width: `${Math.min(100, ((currentItem.sequence_number - 1) / currentItem.total_budget) * 100)}%`
                }}
              />
            </div>

            {error && (
              <div className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center gap-2.5">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Question Card */}
            <div className="p-6 md:p-8 rounded-2xl border border-border bg-card shadow-sm space-y-6">
              {/* Skill tag */}
              <div className="flex items-center justify-between text-xs text-muted-foreground border-b border-border/50 pb-3">
                <span className="font-mono text-[11px] bg-muted px-2 py-0.5 rounded">{currentItem.skill_id}</span>
                <span className="capitalize">{currentItem.grade_band} stage</span>
              </div>

              {/* Prompt Text */}
              <div className={`text-foreground leading-relaxed font-normal ${juniorTone ? 'text-xl' : 'text-lg'}`}>
                {currentItem.prompt}
              </div>

              {/* Options list (MCQ) */}
              {currentItem.options && currentItem.options.length > 0 ? (
                <div className="space-y-3 pt-2">
                  {currentItem.options.map((opt, idx) => {
                    const isSelected = selectedAnswer === opt;
                    const letter = String.fromCharCode(65 + idx);
                    return (
                      <button
                        key={idx}
                        type="button"
                        disabled={!!feedback}
                        onClick={() => setSelectedAnswer(opt)}
                        className={`w-full p-4 rounded-xl border text-left transition-all flex items-center gap-3.5 ${
                          isSelected
                            ? 'border-blue-500 bg-blue-500/10 text-foreground ring-1 ring-blue-500/30'
                            : 'border-border bg-background/50 hover:bg-muted/40 text-foreground'
                        } ${feedback ? 'cursor-default' : 'cursor-pointer'}`}
                      >
                        <span
                          className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-semibold shrink-0 border ${
                            isSelected
                              ? 'bg-blue-600 text-white border-blue-600'
                              : 'bg-muted/60 text-muted-foreground border-border'
                          }`}
                        >
                          {letter}
                        </span>
                        <span className="text-sm font-medium leading-relaxed">{opt}</span>
                      </button>
                    );
                  })}
                </div>
              ) : (
                /* Numeric / Short answer input */
                <div className="pt-2">
                  <label className="text-xs text-muted-foreground block mb-2 font-medium">Your Answer:</label>
                  <input
                    type="text"
                    disabled={!!feedback}
                    value={selectedAnswer}
                    onChange={e => setSelectedAnswer(e.target.value)}
                    placeholder="Enter numeric or exact value..."
                    className="w-full p-3.5 rounded-xl border border-border bg-background text-foreground text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/40"
                  />
                </div>
              )}

              {/* Progressive Hints Section */}
              {revealedHints.length > 0 && (
                <div className="space-y-2.5 pt-2 border-t border-border/60">
                  <div className="text-xs font-semibold text-amber-500 flex items-center gap-1.5 uppercase tracking-wider">
                    <Lightbulb className="w-3.5 h-3.5" />
                    <span>Hints Unlocked ({revealedHints.length})</span>
                  </div>
                  {revealedHints.map((h, i) => (
                    <div
                      key={i}
                      className="p-3.5 rounded-xl bg-amber-500/5 border border-amber-500/20 text-xs text-foreground leading-relaxed flex items-start gap-2.5"
                    >
                      <span className="font-semibold text-amber-600 shrink-0">#{i + 1}</span>
                      <span>{h}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Feedback Alert (Once Answered) */}
              {feedback && (
                <div
                  className={`p-5 rounded-xl border space-y-3 animate-fade-in ${
                    feedback.correctness
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-950 dark:text-emerald-100'
                      : 'bg-amber-500/10 border-amber-500/30 text-amber-950 dark:text-amber-100'
                  }`}
                >
                  <div className="flex items-center gap-2.5 font-semibold text-sm">
                    {feedback.correctness ? (
                      <>
                        <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
                        <span>Correct! Well reasoned.</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="w-5 h-5 text-amber-500 shrink-0" />
                        <span>Needs another look</span>
                      </>
                    )}
                    {feedback.assistance_level === 'HINT_ASSISTED' && (
                      <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-600 font-normal">
                        Hint-Assisted
                      </span>
                    )}
                  </div>

                  {feedback.authoritative_explanation && (
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {feedback.authoritative_explanation}
                    </p>
                  )}

                  {feedback.mistake_pattern_detected && (
                    <div className="text-xs text-amber-600 dark:text-amber-300 pt-1 flex items-center gap-1.5">
                      <Info className="w-3.5 h-3.5" />
                      <span>
                        Error categorized as {feedback.mistake_pattern_detected.replace('_', ' ').toLowerCase()}. The engine will tailor subsequent practice to this step.
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Actions Footer */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-4 border-t border-border">
                {/* Left controls: Hint & Ask Tutor */}
                <div className="flex items-center gap-2">
                  {!feedback && currentItem.hints_total > revealedHints.length && (
                    <button
                      type="button"
                      onClick={handleRequestHint}
                      disabled={hintLoading}
                      className="px-3.5 py-2 rounded-lg border border-border text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-all flex items-center gap-1.5"
                    >
                      <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
                      <span>{hintLoading ? 'Unlocking...' : 'Need a hint?'}</span>
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() => navigate('/chat')}
                    className="px-3.5 py-2 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-all flex items-center gap-1.5"
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    <span>Ask Tutor</span>
                  </button>
                </div>

                {/* Right CTA: Submit or Next */}
                <div>
                  {!feedback ? (
                    <button
                      type="button"
                      onClick={handleSubmitAnswer}
                      disabled={!selectedAnswer.trim() || submitting}
                      className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-all shadow-xs disabled:opacity-40"
                    >
                      {submitting ? 'Evaluating...' : 'Submit Answer'}
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={handleNextQuestion}
                      disabled={loading}
                      className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center justify-center gap-2 transition-all shadow-xs"
                    >
                      <span>{feedback.session_completed ? 'View Summary' : 'Next Question'}</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ─── 3. SESSION SUMMARY VIEW ───────────────────────────────────────── */}
        {summary && (
          <div className="space-y-8 animate-fade-in">
            {/* Header */}
            <div className="p-8 rounded-2xl border border-border bg-card shadow-sm text-center space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-blue-500/10 text-blue-500 border border-blue-500/20 flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h2 className="text-2xl font-bold text-foreground">Practice Session Complete</h2>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Pedagogical outcomes recorded in your Mastery Knowledge Graph. No arbitrary gamified ranks.
              </p>

              {/* Outcomes metrics */}
              <div className="grid grid-cols-3 gap-3 pt-4 max-w-lg mx-auto">
                <div className="p-4 rounded-xl bg-muted/30 border border-border text-center">
                  <div className="text-2xl font-bold text-foreground">{summary.total_questions}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">Attempted</div>
                </div>
                <div className="p-4 rounded-xl bg-muted/30 border border-border text-center">
                  <div className="text-2xl font-bold text-emerald-500">{summary.correct_count}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">Accurate</div>
                </div>
                <div className="p-4 rounded-xl bg-muted/30 border border-border text-center">
                  <div className="text-2xl font-bold text-blue-500">{summary.independent_correct_count}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">Independent</div>
                </div>
              </div>
            </div>

            {/* Concepts Practiced Rollup */}
            <div className="p-6 rounded-2xl border border-border bg-card space-y-4">
              <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                <Layers className="w-4 h-4 text-blue-500" />
                <span>Skills Exercised</span>
              </h3>

              <div className="space-y-3">
                {summary.skills_practiced.map((sk, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-xl border border-border/80 bg-background/50 flex items-center justify-between"
                  >
                    <div>
                      <div className="font-semibold text-sm text-foreground">{sk.skill_name}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {sk.correct} of {sk.attempted} correct ({sk.independent} without hints)
                      </div>
                    </div>
                    <span className="text-xs px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-500 border border-blue-500/20 font-medium">
                      Evidence Recorded
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Recommended Next Focus */}
            <div className="p-5 rounded-2xl bg-blue-500/5 border border-blue-500/20 flex items-start gap-3.5">
              <Sparkles className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-foreground">Next Educational Focus</h4>
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                  {summary.recommended_next_focus}
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button
                type="button"
                onClick={handleResetSession}
                className="flex-1 py-3.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-xs transition-all"
              >
                <RotateCcw className="w-4 h-4" />
                <span>Practice Another Topic</span>
              </button>
              <button
                type="button"
                onClick={() => navigate('/mastery')}
                className="flex-1 py-3.5 px-4 rounded-xl border border-border text-foreground hover:bg-muted font-semibold text-xs flex items-center justify-center gap-2 transition-all"
              >
                <Compass className="w-4 h-4" />
                <span>View Mastery Map</span>
              </button>
            </div>
          </div>
        )}

        {/* ─── 4. EXPLAINABILITY MODAL ───────────────────────────────────────── */}
        {showExplainModal && explanation && (
          <div className="fixed inset-0 bg-background/80 backdrop-blur-xs z-50 flex items-center justify-center p-4">
            <div className="bg-card border border-border rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4 animate-scale-in">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <HelpCircle className="w-4 h-4 text-blue-500" />
                  <span className="font-semibold text-sm text-foreground">Why Was This Question Selected?</span>
                </div>
                <button
                  type="button"
                  onClick={() => setShowExplainModal(false)}
                  className="text-muted-foreground hover:text-foreground text-xs px-2 py-1 rounded hover:bg-muted"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-3">
                <div className="p-3.5 rounded-xl bg-muted/40 border border-border text-xs leading-relaxed text-foreground">
                  {explanation.reason}
                </div>

                <div className="text-xs text-muted-foreground space-y-1">
                  <div><strong className="text-foreground">Category:</strong> {explanation.category.replace('_', ' ')}</div>
                  <div><strong className="text-foreground">Skill:</strong> {explanation.skill_name}</div>
                  <div><strong className="text-foreground">Operating Tier:</strong> {explanation.difficulty}</div>
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => setShowExplainModal(false)}
                  className="w-full py-2.5 rounded-xl bg-muted hover:bg-muted/80 text-foreground text-xs font-semibold"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
};

export default PracticePage;
