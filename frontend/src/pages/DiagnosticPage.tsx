import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import {
  startDiagnostic,
  submitDiagnosticAnswer,
  getDiagnosticHistory,
} from '../lib/diagnosticApi';
import { soundFx } from '../lib/soundFx';
import type {
  DiagnosticStepResponse,
  DiagnosticResult,
  StudentItemView,
} from '../types/diagnostic';
import {
  Compass,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  ArrowRight,
  RotateCcw,
  BookOpen,
  History,
  Layers,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { Button, Card, Badge, ProgressBar } from '../components/ui';
import { pageTransition, fadeUp, cardHover } from '../lib/motion';

const AVAILABLE_SUBJECTS = [
  'Mathematics',
  'Physics',
  'Chemistry',
  'Biology',
  'Science',
  'English',
  'Computer Science',
];

export const DiagnosticPage: React.FC = () => {
  const [selectedSubject, setSelectedSubject] = useState<string>('Mathematics');
  const [stepData, setStepData] = useState<DiagnosticStepResponse | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<DiagnosticResult[]>([]);
  const [viewHistory, setViewHistory] = useState<boolean>(false);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const res = await getDiagnosticHistory();
      setHistory(res);
    } catch {
      // Offline or mock fallback
    }
  };

  const handleStart = async (retake = false) => {
    setLoading(true);
    setError(null);
    try {
      const res = await startDiagnostic({ subject: selectedSubject, retake });
      setStepData(res);
      setSelectedAnswer('');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to start diagnostic. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitAnswer = async () => {
    if (!stepData?.session || !stepData.current_question || !selectedAnswer) return;

    setLoading(true);
    setError(null);
    try {
      const res = await submitDiagnosticAnswer(stepData.session.id, {
        item_id: stepData.current_question.id,
        student_response: selectedAnswer,
        response_time_ms: 5000,
      });
      setStepData(res);
      setSelectedAnswer('');
      if (res.is_completed) {
        soundFx.playSessionComplete();
        loadHistory();
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to submit response. Please retry.');
    } finally {
      setLoading(false);
    }
  };

  const renderActiveQuestion = (q: StudentItemView) => {
    const totalBudget = q.total_budget || 8;
    const progressPercent = Math.min(100, Math.round(((q.sequence_number - 1) / totalBudget) * 100));

    return (
      <motion.div
        key={q.id || q.sequence_number}
        initial={prefersReducedMotion ? false : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
        className="max-w-3xl mx-auto"
      >
        <Card variant="elevated" className="p-8 sm:p-10 space-y-6">
          {/* Header Metadata */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-[var(--border)]">
            <div className="flex items-center gap-2.5">
              <Badge tone="sky" icon={<Compass className="w-3.5 h-3.5" />}>
                Adaptive Diagnostic • {stepData?.session?.subject}
              </Badge>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-[var(--text-muted)] tracking-wider">
                Probe {q.sequence_number} of ~{totalBudget}
              </span>
              <div className="w-24">
                <ProgressBar value={progressPercent} tone="sky" size="sm" />
              </div>
            </div>
          </div>

          {/* Question Prompt */}
          <div className="py-2">
            <h3 className="text-xl sm:text-2xl font-medium font-display text-[var(--text-primary)] leading-relaxed">
              {q.prompt}
            </h3>
          </div>

          {/* Answer Options */}
          {q.options && q.options.length > 0 ? (
            <div className="space-y-3 pt-2">
              {q.options.map((opt, idx) => {
                const isSelected = selectedAnswer === opt;
                return (
                  <motion.button
                    key={idx}
                    type="button"
                    onClick={() => setSelectedAnswer(opt)}
                    {...(prefersReducedMotion ? {} : cardHover)}
                    className={`
                      w-full text-left p-4 sm:p-5 rounded-xl border text-sm font-medium
                      flex items-center justify-between transition-all duration-150 cursor-pointer
                      focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-sky)]
                      ${
                        isSelected
                          ? 'border-[var(--brand-primary)] bg-[var(--brand-primary-light)] text-[var(--accent-blue-text)] shadow-xs ring-1 ring-[var(--brand-primary)]'
                          : 'border-[var(--border)] bg-white text-[var(--text-primary)] hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] shadow-xs'
                      }
                    `}
                  >
                    <span className="leading-relaxed">{opt}</span>
                    <span
                      className={`
                        w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 ml-4 transition-colors
                        ${
                          isSelected
                            ? 'border-[var(--brand-primary)] bg-[var(--brand-primary)] text-white'
                            : 'border-[var(--border-strong)] bg-white'
                        }
                      `}
                    >
                      {isSelected && <span className="w-2 h-2 rounded-full bg-white" />}
                    </span>
                  </motion.button>
                );
              })}
            </div>
          ) : (
            <div className="pt-2">
              <input
                type="text"
                value={selectedAnswer}
                onChange={(e) => setSelectedAnswer(e.target.value)}
                placeholder="Enter your step-by-step solution..."
                className="w-full bg-[var(--bg-subtle)] border border-[var(--border)] rounded-xl px-4 py-3.5 text-base text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--brand-primary)] focus:bg-white transition-colors"
              />
            </div>
          )}

          {/* Submit Action */}
          <div className="flex items-center justify-end pt-4 border-t border-[var(--border)]">
            <Button
              variant="primary"
              size="md"
              loading={loading}
              disabled={!selectedAnswer || loading}
              onClick={handleSubmitAnswer}
              iconRight={<ArrowRight className="w-4 h-4" />}
            >
              {loading ? 'Submitting...' : 'Submit Response'}
            </Button>
          </div>
        </Card>
      </motion.div>
    );
  };

  const renderResult = (res: DiagnosticResult) => {
    const secureSkills = res.skill_results.filter((s) => s.diagnostic_state === 'SECURE');
    const developingSkills = res.skill_results.filter((s) => s.diagnostic_state === 'DEVELOPING');
    const repairSkills = res.skill_results.filter((s) => s.diagnostic_state === 'NEEDS_REPAIR');

    return (
      <motion.div
        initial={prefersReducedMotion ? false : { opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        className="max-w-4xl mx-auto space-y-8"
      >
        <Card variant="elevated" className="p-8 sm:p-10 space-y-8">
          <div>
            <div className="flex items-center gap-2 text-[var(--accent-green-text)] text-sm font-semibold mb-2">
              <CheckCircle2 className="w-5 h-5 text-[var(--accent-green)]" />
              Diagnostic Assessment Complete
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold font-display text-[var(--text-primary)]">
              Learning Starting Point: {res.subject}
            </h2>
            <p className="text-sm text-[var(--text-muted)] mt-1.5">
              Enrolled: Class {res.enrolled_grade} • Track: {res.exam_track}
            </p>
          </div>

          {/* Operating Level Focus Banner */}
          <div className="bg-[var(--accent-sky-bg)] border border-[var(--accent-sky-border)] rounded-2xl p-6">
            <div className="text-xs uppercase tracking-wider text-[var(--accent-sky-text)] font-bold mb-1">
              Recommended Focus Zone
            </div>
            <div className="text-xl font-bold font-display text-[var(--text-primary)]">
              {res.operating_level_band}
            </div>
            <div className="text-sm text-[var(--text-secondary)] mt-2 leading-relaxed">
              {res.summary}
            </div>
          </div>

          {/* 3-Column Conceptual Mastery Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Secure Foundations */}
            <div className="bg-white border border-[var(--border)] rounded-xl p-5 shadow-xs">
              <div className="flex items-center gap-2 text-[var(--accent-green-text)] font-semibold text-sm mb-3">
                <CheckCircle2 className="w-4 h-4 text-[var(--accent-green)]" />
                Secure Foundations ({secureSkills.length})
              </div>
              {secureSkills.length > 0 ? (
                <ul className="space-y-2.5">
                  {secureSkills.map((s, idx) => (
                    <li key={idx} className="text-xs">
                      <span className="font-semibold text-[var(--text-primary)]">{s.skill_name}</span>
                      <div className="text-[var(--text-muted)] capitalize mt-0.5">
                        {s.confidence_class.replace('_', ' ').toLowerCase()}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-xs text-[var(--text-muted)] italic">No skills classified secure in this probe set.</div>
              )}
            </div>

            {/* Developing Concepts */}
            <div className="bg-white border border-[var(--border)] rounded-xl p-5 shadow-xs">
              <div className="flex items-center gap-2 text-[var(--accent-yellow-text)] font-semibold text-sm mb-3">
                <HelpCircle className="w-4 h-4 text-[var(--accent-yellow)]" />
                Developing Concepts ({developingSkills.length})
              </div>
              {developingSkills.length > 0 ? (
                <ul className="space-y-2.5">
                  {developingSkills.map((s, idx) => (
                    <li key={idx} className="text-xs">
                      <span className="font-semibold text-[var(--text-primary)]">{s.skill_name}</span>
                      <div className="text-[var(--text-muted)] mt-0.5">{s.recommended_action}</div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-xs text-[var(--text-muted)] italic">No concepts currently developing.</div>
              )}
            </div>

            {/* Prerequisites Needing Repair */}
            <div className="bg-white border border-[var(--border)] rounded-xl p-5 shadow-xs">
              <div className="flex items-center gap-2 text-[var(--accent-red-text)] font-semibold text-sm mb-3">
                <AlertCircle className="w-4 h-4 text-[var(--accent-red)]" />
                Prerequisites Needing Repair ({repairSkills.length})
              </div>
              {repairSkills.length > 0 ? (
                <ul className="space-y-2.5">
                  {repairSkills.map((s, idx) => (
                    <li key={idx} className="text-xs">
                      <span className="font-semibold text-[var(--accent-red-text)]">{s.skill_name}</span>
                      <div className="text-[var(--text-muted)] mt-0.5">{s.recommended_action}</div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-xs text-[var(--text-muted)] italic">No critical prerequisite gaps identified.</div>
              )}
            </div>
          </div>

          {/* Action Footer */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-6 border-t border-[var(--border)]">
            <Button
              variant="secondary"
              size="sm"
              icon={<RotateCcw className="w-4 h-4" />}
              onClick={() => handleStart(true)}
            >
              Retake Diagnostic
            </Button>
            <Button
              variant="primary"
              size="md"
              onClick={() => {
                setStepData(null);
                setViewHistory(false);
              }}
            >
              Back to Overview
            </Button>
          </div>
        </Card>
      </motion.div>
    );
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] p-6 md:p-10">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[var(--border)]">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Badge tone="sky" icon={<Compass className="w-3.5 h-3.5" />}>
                Educational Readiness Assessment
              </Badge>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold font-display tracking-tight text-[var(--text-primary)]">
              Adaptive Subject Diagnostic
            </h1>
            <p className="text-sm text-[var(--text-muted)] mt-1 max-w-2xl">
              Determines foundational prerequisite readiness and the optimal learning starting point using Bayesian Knowledge Tracing.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="secondary"
              size="sm"
              icon={<History className="w-4 h-4 text-[var(--text-muted)]" />}
              onClick={() => setViewHistory(!viewHistory)}
            >
              {viewHistory ? 'Hide History' : 'Diagnostic History'}
            </Button>
          </div>
        </div>

        {error && (
          <div className="bg-[var(--accent-yellow-bg)] border border-[var(--accent-yellow-border)] rounded-xl p-4 text-xs text-[var(--accent-yellow-text)] flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* View History Drawer */}
        {viewHistory && (
          <motion.div
            initial={prefersReducedMotion ? false : { opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <Card variant="elevated" className="p-6">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
                <History className="w-4 h-4 text-[var(--accent-sky)]" />
                Historical Diagnostics ({history.length})
              </h3>
              {history.length > 0 ? (
                <div className="divide-y divide-[var(--border)]">
                  {history.map((h, i) => (
                    <div key={i} className="py-3 flex items-center justify-between text-xs">
                      <div>
                        <span className="font-semibold text-[var(--text-primary)]">{h.subject}</span>
                        <span className="text-[var(--text-muted)] ml-2">• Class {h.enrolled_grade} ({h.exam_track})</span>
                        <div className="text-[var(--text-secondary)] mt-0.5">{h.operating_level_band}</div>
                      </div>
                      <div className="text-right text-[var(--text-muted)]">
                        {h.created_at ? new Date(h.created_at).toLocaleDateString() : 'Recorded'}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-[var(--text-muted)] italic">No historical diagnostics recorded yet.</div>
              )}
            </Card>
          </motion.div>
        )}

        {/* Main Selection Body */}
        {!stepData && (
          <motion.div
            initial={prefersReducedMotion ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          >
            <Card variant="elevated" className="p-8 sm:p-12 max-w-2xl mx-auto text-center space-y-6">
              <div className="w-14 h-14 rounded-2xl bg-[var(--accent-sky-bg)] border border-[var(--accent-sky-border)] text-[var(--accent-sky)] flex items-center justify-center mx-auto shadow-xs">
                <Layers className="w-7 h-7" />
              </div>

              <div>
                <h2 className="text-xl sm:text-2xl font-bold font-display text-[var(--text-primary)] mb-2">
                  Select Diagnostic Subject
                </h2>
                <p className="text-xs sm:text-sm text-[var(--text-muted)] max-w-md mx-auto leading-relaxed">
                  Each diagnostic assesses 6–10 bounded conceptual probes tailored to your curriculum and grade band.
                </p>
              </div>

              <div className="flex flex-wrap justify-center gap-2.5 max-w-lg mx-auto py-2">
                {AVAILABLE_SUBJECTS.map((sub) => {
                  const isSelected = selectedSubject === sub;
                  return (
                    <button
                      key={sub}
                      type="button"
                      onClick={() => setSelectedSubject(sub)}
                      className={`
                        px-4 py-2.5 rounded-xl text-xs font-semibold transition-all duration-150 cursor-pointer
                        ${
                          isSelected
                            ? 'bg-[var(--accent-sky-bg)] text-[var(--accent-sky-text)] border border-[var(--accent-sky-border)] shadow-xs ring-1 ring-[var(--accent-sky)]'
                            : 'bg-white text-[var(--text-secondary)] border border-[var(--border)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]'
                        }
                      `}
                    >
                      {sub}
                    </button>
                  );
                })}
              </div>

              <div className="pt-2">
                <Button
                  variant="primary"
                  size="lg"
                  loading={loading}
                  disabled={loading}
                  onClick={() => handleStart(false)}
                  icon={<BookOpen className="w-4 h-4" />}
                >
                  {loading ? 'Initializing Diagnostic...' : `Begin ${selectedSubject} Diagnostic`}
                </Button>
              </div>
            </Card>
          </motion.div>
        )}

        {/* Active Question View */}
        {stepData && !stepData.is_completed && stepData.current_question && (
          renderActiveQuestion(stepData.current_question)
        )}

        {/* Completed Result View */}
        {stepData && stepData.is_completed && stepData.result && (
          renderResult(stepData.result)
        )}
      </div>
    </div>
  );
};

export default DiagnosticPage;
