import React, { useState, useEffect } from 'react';
import {
  ListChecks,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  ArrowRight,
  ArrowDownCircle,
  Sparkles,
  Shield,
  RefreshCw,
  Info,
  ChevronRight,
  GraduationCap,
  X,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import {
  gradeMathSteps,
  getGradeLevelCapabilities,
  requestStepTutorContext,
} from '../lib/stepGraderApi';
import type {
  StepGraderSubmission,
  StepGraderResponse,
  StepCapabilityItem,
  TutorStepHandoffResponse,
  GradedStep,
} from '../types/stepGrader';
import { Button, Card, Badge } from '../components/ui';

interface PresetExample {
  name: string;
  question: string;
  steps: string;
}

const PRESET_EXAMPLES: PresetExample[] = [
  {
    name: 'Algebra Sign Error',
    question: 'Solve for x: 2x + 4 = 10',
    steps: '2x + 4 = 10\n2x = 10 + 4\n2x = 14\nx = 7',
  },
  {
    name: 'Order of Operations',
    question: 'Evaluate: 3 + 4 * 2',
    steps: '3 + 4 * 2\n7 * 2\n14',
  },
  {
    name: 'Valid Quadratic Factorization',
    question: 'Solve for x: x^2 - 5x + 6 = 0',
    steps: 'x^2 - 5x + 6 = 0\n(x - 2)(x - 3) = 0\nx = 2 or x = 3',
  },
];

export const StepCheckPage: React.FC = () => {
  const navigate = useNavigate();

  // Input Form State
  const [questionText, setQuestionText] = useState<string>(PRESET_EXAMPLES[0].question);
  const [rawInput, setRawInput] = useState<string>(PRESET_EXAMPLES[0].steps);
  const [subject, setSubject] = useState<string>('Mathematics');
  const [audienceLevel, setAudienceLevel] = useState<'young' | 'standard' | 'advanced'>('standard');

  // Execution State
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<StepGraderResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Capability Matrix Modal
  const [showCapabilityModal, setShowCapabilityModal] = useState<boolean>(false);
  const [capabilityMatrix, setCapabilityMatrix] = useState<StepCapabilityItem[]>([]);
  const [loadingMatrix, setLoadingMatrix] = useState<boolean>(false);

  // Tutor Handoff Modal
  const [tutorContext, setTutorContext] = useState<TutorStepHandoffResponse | null>(null);
  const [loadingTutorContext, setLoadingTutorContext] = useState<boolean>(false);

  const handleGrade = async () => {
    if (!rawInput.trim()) {
      setErrorMsg('Please enter at least one step of your solution.');
      return;
    }
    setErrorMsg(null);
    setSubmitting(true);

    try {
      const payload: StepGraderSubmission = {
        question_text: questionText.trim() || 'Solve the following expression',
        raw_input: rawInput,
        subject: subject,
        audience_level: audienceLevel,
        prior_attempt_sequence: result ? (result.attempt_sequence || 1) + 1 : 1,
      };

      const res = await gradeMathSteps(payload);
      setResult(res);
    } catch (err: any) {
      console.error('Failed to grade steps:', err);
      setErrorMsg(err?.response?.data?.detail || 'Step grading encountered an issue. Please verify and retry.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResetForNewQuestion = () => {
    setResult(null);
    setErrorMsg(null);
    setQuestionText('');
    setRawInput('');
    setTutorContext(null);
  };

  const loadPreset = (preset: PresetExample) => {
    setQuestionText(preset.question);
    setRawInput(preset.steps);
    setResult(null);
    setErrorMsg(null);
  };

  const handleOpenCapabilities = async () => {
    setShowCapabilityModal(true);
    if (capabilityMatrix.length === 0) {
      setLoadingMatrix(true);
      try {
        const data = await getGradeLevelCapabilities('Mathematics');
        setCapabilityMatrix(data);
      } catch (err) {
        console.error('Failed to load capabilities:', err);
      } finally {
        setLoadingMatrix(false);
      }
    }
  };

  const handleReviewWithGenie = async () => {
    const targetSessionId = result?.step_grader_session_id || result?.session_id || result?.attempt_id;
    if (!targetSessionId || result?.first_wrong_step === undefined) return;
    setLoadingTutorContext(true);
    try {
      const context = await requestStepTutorContext(
        targetSessionId,
        result.first_wrong_step
      );
      setTutorContext(context);
    } catch (err) {
      console.error('Failed to prepare tutor context:', err);
      setErrorMsg('Unable to initialize Socratic tutor context. Please retry.');
    } finally {
      setLoadingTutorContext(false);
    }
  };

  const launchTutorChat = () => {
    if (!tutorContext) return;
    const initialPrompt = `Hello Genie! I was working on: "${tutorContext.question_text}". At Step ${tutorContext.first_wrong_step_index} (${tutorContext.step_raw_text}), I encountered: ${tutorContext.feedback}. Can you guide me through this reasoning step?`;
    navigate(`/teach?topic=${encodeURIComponent(tutorContext.skill_name || 'Problem Solving')}&initial_prompt=${encodeURIComponent(initialPrompt)}`);
  };

  return (
    <AppLayout title="Step Check">
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-8 bg-[var(--bg-primary)]">
        {/* Header Hero Section: Pure White Elevated Card */}
        <Card variant="elevated" className="p-6 sm:p-8 relative overflow-hidden border border-[var(--border)]">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2 mb-2">
                <Badge tone="purple" icon={<ListChecks className="w-3.5 h-3.5" />}>
                  REASONING DIAGNOSTICS & STEP-GRADER
                </Badge>
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold font-display text-[var(--text-primary)]">
                Check My Steps
              </h1>
              <p className="text-sm text-[var(--text-muted)] mt-1 max-w-xl">
                Pinpoint exactly where your reasoning first needs attention, separating root errors from downstream steps.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2.5">
              <Button
                variant="secondary"
                size="sm"
                icon={<Shield className="w-3.5 h-3.5 text-[var(--brand-primary)]" />}
                onClick={handleOpenCapabilities}
              >
                Capability Matrix
              </Button>

              {/* Age / Audience Level Adaptor */}
              <div className="flex items-center bg-[var(--bg-subtle)] border border-[var(--border)] rounded-xl p-1 text-xs">
                {(['young', 'standard', 'advanced'] as const).map((lvl) => (
                  <button
                    key={lvl}
                    type="button"
                    onClick={() => setAudienceLevel(lvl)}
                    className={`px-3 py-1 rounded-lg font-semibold capitalize transition-all cursor-pointer ${
                      audienceLevel === lvl
                        ? 'bg-white text-[var(--brand-primary)] shadow-xs'
                        : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                    }`}
                  >
                    {lvl}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Quick Presets */}
          <div className="mt-5 pt-4 border-t border-[var(--border)] flex flex-wrap items-center gap-2">
            <span className="text-xs text-[var(--text-muted)] font-medium mr-1">Try an example:</span>
            {PRESET_EXAMPLES.map((preset) => (
              <button
                key={preset.name}
                type="button"
                onClick={() => loadPreset(preset)}
                className="px-3 py-1 text-xs rounded-lg bg-[var(--bg-subtle)] hover:bg-[var(--bg-hover)] text-[var(--text-secondary)] border border-[var(--border)] transition-colors cursor-pointer"
              >
                {preset.name}
              </button>
            ))}
          </div>
        </Card>

        {/* Input & Workspace Section */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-6 space-y-4">
            <Card variant="elevated" className="p-6 space-y-4 border border-[var(--border)]">
              <div>
                <label className="block text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-1.5">
                  Question / Problem Statement
                </label>
                <input
                  type="text"
                  value={questionText}
                  onChange={(e) => setQuestionText(e.target.value)}
                  placeholder="e.g. Solve for x: 2x + 4 = 10"
                  className="w-full px-4 py-2.5 bg-[var(--bg-subtle)] border border-[var(--border)] rounded-xl text-[var(--text-primary)] placeholder-[var(--text-muted)] text-sm focus:outline-none focus:border-[var(--brand-primary)] focus:bg-white transition-colors"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                    Your Step-by-Step Solution
                  </label>
                  <span className="text-xs text-[var(--text-muted)]">One step per line</span>
                </div>
                <textarea
                  rows={8}
                  value={rawInput}
                  onChange={(e) => setRawInput(e.target.value)}
                  placeholder="1. 2x + 4 = 10&#10;2. 2x = 10 + 4&#10;3. x = 7"
                  className="w-full font-mono px-4 py-3 bg-[var(--bg-subtle)] border border-[var(--border)] rounded-xl text-[var(--text-primary)] placeholder-[var(--text-muted)] text-sm focus:outline-none focus:border-[var(--brand-primary)] focus:bg-white transition-colors leading-relaxed"
                />
              </div>

              {errorMsg && (
                <div className="p-3 bg-[var(--accent-yellow-bg)] border border-[var(--accent-yellow-border)] rounded-xl text-[var(--accent-yellow-text)] text-xs flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-[var(--accent-yellow)]" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <div className="flex items-center justify-between pt-2">
                {result ? (
                  <button
                    type="button"
                    onClick={handleResetForNewQuestion}
                    className="text-xs font-semibold text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
                  >
                    New Problem
                  </button>
                ) : (
                  <span className="text-xs text-[var(--text-muted)]">Deterministic check first</span>
                )}

                <Button
                  variant="primary"
                  size="md"
                  loading={submitting}
                  disabled={submitting}
                  onClick={handleGrade}
                  icon={result ? <RefreshCw className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
                >
                  {submitting
                    ? 'Diagnosing Steps...'
                    : result
                    ? `Check Revised Steps (Attempt ${(result.attempt_sequence || 1) + 1})`
                    : 'Check My Steps'}
                </Button>
              </div>
            </Card>
          </div>

          {/* Results & Step Diagnosis Section */}
          <div className="lg:col-span-6 space-y-4">
            {!result ? (
              <Card variant="default" className="h-full min-h-[340px] p-8 flex flex-col items-center justify-center text-center border-dashed border-[var(--border-strong)] bg-white">
                <div className="w-14 h-14 rounded-2xl bg-[var(--brand-primary-light)] border border-[var(--brand-primary-soft)] flex items-center justify-center text-[var(--brand-primary)] mb-3 shadow-xs">
                  <ListChecks className="w-7 h-7" />
                </div>
                <h3 className="text-[var(--text-primary)] font-bold text-base mb-1 font-display">
                  Ready to Validate Reasoning
                </h3>
                <p className="text-xs text-[var(--text-muted)] max-w-sm leading-relaxed">
                  Enter your steps on the left and click "Check My Steps". We validate each transformation, find the first issue, and explain what happened without fake percentage scores.
                </p>
              </Card>
            ) : (
              <Card variant="elevated" className="p-6 space-y-5 border border-[var(--border)]">
                {/* Result Headline Banner */}
                <div className="flex items-start justify-between gap-3 pb-4 border-b border-[var(--border)]">
                  <div className="flex items-start space-x-3">
                    {result.overall_outcome === 'ALL_STEPS_VALID' ? (
                      <div className="w-10 h-10 rounded-xl bg-[var(--accent-green-bg)] border border-[var(--accent-green-border)] flex items-center justify-center text-[var(--accent-green)] shrink-0">
                        <CheckCircle2 className="w-5 h-5" />
                      </div>
                    ) : result.overall_outcome === 'ROOT_ERROR_DETECTED' ? (
                      <div className="w-10 h-10 rounded-xl bg-[var(--accent-yellow-bg)] border border-[var(--accent-yellow-border)] flex items-center justify-center text-[var(--accent-yellow)] shrink-0">
                        <AlertTriangle className="w-5 h-5" />
                      </div>
                    ) : (
                      <div className="w-10 h-10 rounded-xl bg-[var(--bg-subtle)] border border-[var(--border)] flex items-center justify-center text-[var(--text-muted)] shrink-0">
                        <HelpCircle className="w-5 h-5" />
                      </div>
                    )}

                    <div>
                      <h3 className="text-base font-bold font-display text-[var(--text-primary)]">
                        {result.overall_outcome === 'ALL_STEPS_VALID'
                          ? 'All reasoning steps are valid!'
                          : result.first_wrong_step
                          ? `First issue detected at Step ${result.first_wrong_step}`
                          : 'Ambiguous or unverified reasoning'}
                      </h3>
                      <p className="text-xs text-[var(--text-muted)] mt-0.5 leading-relaxed">
                        {result.feedback_summary}
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-col items-end shrink-0">
                    <Badge tone="neutral">
                      Attempt {result.attempt_sequence}
                    </Badge>
                    <span className="text-[10px] text-[var(--text-muted)] mt-1">
                      Confidence: {result.confidence}
                    </span>
                  </div>
                </div>

                {/* Step Diagnosis Cards */}
                <div className="space-y-2.5">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                    Step Inspection
                  </h4>
                  {result.validated_steps.map((step: GradedStep) => {
                    const isRoot = step.is_root_error || step.validation_status === 'ROOT_ERROR';
                    const isDownstream = step.validation_status === 'DOWNSTREAM_ERROR';

                    let cardClass = 'bg-white border-[var(--border)] text-[var(--text-secondary)]';
                    let icon = <CheckCircle2 className="w-4 h-4 text-[var(--accent-green)]" />;
                    let badgeTone: 'green' | 'yellow' | 'blue' | 'neutral' = 'green';
                    let badgeText = 'Valid transformation';

                    if (isRoot) {
                      cardClass = 'bg-[var(--accent-yellow-bg)]/40 border-[var(--accent-yellow-border)] text-[var(--accent-yellow-text)]';
                      icon = <AlertTriangle className="w-4 h-4 text-[var(--accent-yellow)]" />;
                      badgeTone = 'yellow';
                      badgeText = 'Needs another look';
                    } else if (isDownstream) {
                      cardClass = 'bg-[var(--brand-primary-light)]/40 border-[var(--brand-primary-soft)] text-[var(--text-secondary)]';
                      icon = <ArrowDownCircle className="w-4 h-4 text-[var(--brand-primary)]" />;
                      badgeTone = 'blue';
                      badgeText = `Follows from Step ${result.first_wrong_step}`;
                    } else if (step.validation_status === 'UNCERTAIN') {
                      cardClass = 'bg-[var(--bg-subtle)] border-[var(--border)] text-[var(--text-muted)]';
                      icon = <HelpCircle className="w-4 h-4 text-[var(--text-muted)]" />;
                      badgeTone = 'neutral';
                      badgeText = 'Ambiguous';
                    }

                    return (
                      <div
                        key={step.id || step.step_index}
                        className={`p-4 rounded-xl border transition-all ${cardClass}`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            {icon}
                            <span className="font-mono text-xs font-bold text-[var(--text-primary)]">
                              Step {step.step_index}
                            </span>
                          </div>
                          <Badge tone={badgeTone}>
                            {badgeText}
                          </Badge>
                        </div>

                        <div className="font-mono text-xs text-[var(--text-primary)] bg-white px-3 py-2 rounded-lg border border-[var(--border)] mb-2 overflow-x-auto shadow-xs">
                          {step.raw_text}
                        </div>

                        <p className="text-xs leading-relaxed text-[var(--text-secondary)]">
                          {step.feedback}
                        </p>

                        {isRoot && step.error_type && (
                          <div className="mt-2.5 pt-2 border-t border-[var(--accent-yellow-border)] flex items-center justify-between text-[11px] text-[var(--accent-yellow-text)]">
                            <span>Mistake Pattern: <strong>{step.error_type}</strong></span>
                            <span className="text-[10px] text-[var(--text-muted)]">Validator: {step.validator_type}</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Recommended Next Action */}
                <div className="p-4 rounded-xl bg-[var(--bg-subtle)] border border-[var(--border)] flex items-start space-x-3 text-xs">
                  <Info className="w-4 h-4 text-[var(--brand-primary)] shrink-0 mt-0.5" />
                  <div className="space-y-0.5">
                    <span className="font-semibold text-[var(--text-primary)]">Recommended Next Step:</span>
                    <p className="text-[var(--text-secondary)] leading-relaxed">{result.recommended_next_action}</p>
                  </div>
                </div>

                {/* Socratic Tutor Handoff Action */}
                {result.can_review_with_tutor && (
                  <div className="pt-2">
                    <Button
                      variant="ai"
                      size="md"
                      className="w-full"
                      loading={loadingTutorContext}
                      disabled={loadingTutorContext}
                      icon={<GraduationCap className="w-4 h-4" />}
                      onClick={handleReviewWithGenie}
                    >
                      {loadingTutorContext
                        ? 'Preparing Bounded Context...'
                        : `Review Step ${result.first_wrong_step} with Genie`}
                    </Button>
                  </div>
                )}
              </Card>
            )}
          </div>
        </div>

        {/* Bounded Socratic Tutor Review Modal */}
        {tutorContext && (
          <div className="fixed inset-0 z-50 bg-slate-900/30 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white border border-[var(--border)] rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4">
              <div className="flex items-center space-x-3 pb-3 border-b border-[var(--border)]">
                <div className="w-10 h-10 rounded-xl bg-[var(--accent-purple-bg)] border border-[var(--accent-purple-border)] flex items-center justify-center text-[var(--accent-purple)]">
                  <GraduationCap className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold font-display text-[var(--text-primary)]">
                    Bounded Tutor Review Session
                  </h3>
                  <p className="text-xs text-[var(--text-muted)]">
                    Genie receives only the context for Step {tutorContext.first_wrong_step_index}
                  </p>
                </div>
              </div>

              <div className="space-y-2.5 text-xs">
                <div className="p-3 bg-[var(--bg-subtle)] rounded-xl border border-[var(--border)]">
                  <span className="text-[var(--text-muted)] block mb-1">Target Reasoning Step:</span>
                  <div className="font-mono text-[var(--text-primary)] font-semibold">{tutorContext.step_raw_text}</div>
                </div>

                <div className="p-3 bg-[var(--bg-subtle)] rounded-xl border border-[var(--border)]">
                  <span className="text-[var(--text-muted)] block mb-1">Diagnosis:</span>
                  <div className="text-[var(--text-primary)] leading-relaxed">{tutorContext.feedback}</div>
                  <div className="mt-1 text-[11px] text-[var(--accent-purple-text)] font-medium">
                    Classified Pattern: {tutorContext.error_type}
                  </div>
                </div>

                {tutorContext.related_prerequisite && (
                  <div className="p-2.5 bg-[var(--brand-primary-light)] rounded-lg text-[var(--accent-blue-text)] text-[11px]">
                    Related Foundation: <span className="font-semibold">{tutorContext.related_prerequisite}</span>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-[var(--border)]">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setTutorContext(null)}
                >
                  Cancel
                </Button>
                <Button
                  variant="ai"
                  size="sm"
                  iconRight={<ArrowRight className="w-3.5 h-3.5" />}
                  onClick={launchTutorChat}
                >
                  Start Socratic Dialogue
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Capability Matrix Modal */}
        {showCapabilityModal && (
          <div className="fixed inset-0 z-50 bg-slate-900/30 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white border border-[var(--border)] rounded-2xl max-w-3xl w-full p-6 sm:p-8 shadow-xl space-y-4 max-h-[85vh] flex flex-col">
              <div className="flex items-center justify-between pb-3 border-b border-[var(--border)] shrink-0">
                <div className="flex items-center space-x-2">
                  <Shield className="w-5 h-5 text-[var(--brand-primary)]" />
                  <h3 className="text-base font-bold font-display text-[var(--text-primary)]">
                    Honest Capability Matrix
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setShowCapabilityModal(false)}
                  className="p-1 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] text-sm cursor-pointer"
                  aria-label="Close modal"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <p className="text-xs text-[var(--text-muted)] shrink-0 leading-relaxed">
                LearnByGenie distinguishes deterministic AST verification from rubric fallback. No fake claims of universal grading certainty.
              </p>

              <div className="overflow-y-auto flex-1 space-y-2 pr-1">
                {loadingMatrix ? (
                  <div className="py-12 text-center text-xs text-[var(--text-muted)] flex items-center justify-center space-x-2">
                    <RefreshCw className="w-4 h-4 animate-spin text-[var(--brand-primary)]" />
                    <span>Loading capabilities...</span>
                  </div>
                ) : (
                  <div className="divide-y divide-[var(--border)] border border-[var(--border)] rounded-xl overflow-hidden bg-white">
                    {capabilityMatrix.map((item, idx) => (
                      <div key={idx} className="p-4 text-xs space-y-1.5 hover:bg-[var(--bg-hover)] transition-colors">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-[var(--text-primary)]">
                            {item.subject} — {item.skill_name}
                          </span>
                          <Badge tone={item.confidence_capability === 'HIGH' ? 'green' : 'yellow'}>
                            {item.confidence_capability} CONFIDENCE
                          </Badge>
                        </div>
                        <div className="text-[11px] text-[var(--text-muted)]">
                          Primary Validator: <span className="text-[var(--text-primary)] font-mono font-medium">{item.validator_type}</span>
                          {item.deterministic_support && (
                            <span className="ml-2 text-[var(--accent-green-text)] font-semibold">✓ Deterministic</span>
                          )}
                          {item.rubric_support && (
                            <span className="ml-2 text-[var(--brand-primary)] font-semibold">✓ Rubric Supported</span>
                          )}
                        </div>
                        <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">{item.notes}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="pt-3 border-t border-[var(--border)] flex justify-end shrink-0">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowCapabilityModal(false)}
                >
                  Close
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
};

export default StepCheckPage;
