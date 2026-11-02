import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ListChecks,
  CheckCircle2,
  AlertTriangle,
  ArrowDownCircle,
  HelpCircle,
  RefreshCw,
  Sparkles,
  GraduationCap,
  Info,
  ChevronRight,
  Shield,
  Layers,
  ArrowRight,
  History
} from 'lucide-react';
import AppLayout from '../components/AppLayout';
import { stepGraderApi } from '../lib/stepGraderApi';
import { soundFx } from '../lib/soundFx';
import type {
  StepGraderResult,
  GradedStep,
  CapabilityMatrixItem,
  TutorHandoffContext
} from '../types/stepGrader';

function playOutcome(result: StepGraderResult) {
  if (result.overall_outcome === 'ALL_STEPS_VALID') soundFx.playStepVerified();
  else if (result.overall_outcome === 'ROOT_ERROR_DETECTED') soundFx.playMistakeLogged();
}

const PRESET_EXAMPLES = [
  {
    name: 'Algebra Sign Transposition',
    subject: 'Mathematics',
    skill_id: 'MATH_LIN_EQ',
    question: 'Solve for x: 2x + 4 = 10',
    solution: '1. 2x + 4 = 10\n2. 2x = 10 + 4\n3. x = 7'
  },
  {
    name: 'Arithmetic Calculation Slip',
    subject: 'Mathematics',
    skill_id: 'MATH_LIN_EQ',
    question: 'Solve for x: 3x = 18 - 6',
    solution: '1. 3x = 18 - 6\n2. 3x = 15\n3. x = 5'
  },
  {
    name: 'Physics Unit Mismatch',
    subject: 'Physics',
    skill_id: 'PHY_NEWTON_LAWS',
    question: 'A mass of 2 kg accelerates at 5 m/s². Calculate the force applied.',
    solution: '1. F = m * a\n2. F = 2 * 5\n3. F = 10 Joules'
  },
  {
    name: 'Chemistry Stoichiometry',
    subject: 'Chemistry',
    skill_id: 'CHEM_STOICH',
    question: 'Calculate moles in 36 grams of H2O (Molar mass = 18 g/mol).',
    solution: '1. moles = mass / molar_mass\n2. moles = 36 / 18\n3. moles = 3'
  },
  {
    name: 'CS Loop Condition Boundary',
    subject: 'Computer Science',
    skill_id: 'CS_LOOP_INVARIANT',
    question: 'Process elements of a 0-indexed array of length n.',
    solution: '1. i = 0\n2. while i <= n:\n3.   print(arr[i])'
  }
];

export const StepCheckPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [questionText, setQuestionText] = useState(
    searchParams.get('question') || 'Solve for x: 2x + 4 = 10'
  );
  const [rawInput, setRawInput] = useState(
    searchParams.get('solution') || '1. 2x + 4 = 10\n2. 2x = 10 + 4\n3. x = 7'
  );
  const [subject, setSubject] = useState(searchParams.get('subject') || 'Mathematics');
  const [skillId, setSkillId] = useState(searchParams.get('skill_id') || 'MATH_LIN_EQ');
  const [audienceLevel, setAudienceLevel] = useState<'young' | 'standard' | 'advanced'>('standard');

  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<StepGraderResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Capability matrix modal state
  const [showCapabilityModal, setShowCapabilityModal] = useState(false);
  const [capabilityMatrix, setCapabilityMatrix] = useState<CapabilityMatrixItem[]>([]);
  const [loadingMatrix, setLoadingMatrix] = useState(false);

  // Tutor context dialog
  const [tutorContext, setTutorContext] = useState<TutorHandoffContext | null>(null);
  const [loadingTutorContext, setLoadingTutorContext] = useState(false);

  const handleGrade = async () => {
    if (!questionText.trim() || !rawInput.trim()) {
      setErrorMsg('Please enter both the question and your step-by-step solution.');
      return;
    }

    setSubmitting(true);
    setErrorMsg(null);

    try {
      if (result?.session_id) {
        // Resubmission versioning
        const res = await stepGraderApi.resubmitSolution({
          session_id: result.session_id,
          updated_raw_input: rawInput,
          audience_level: audienceLevel
        });
        setResult(res);
        playOutcome(res);
      } else {
        // Initial grading
        const res = await stepGraderApi.gradeSolution({
          question_text: questionText,
          raw_input: rawInput,
          subject,
          skill_id: skillId,
          audience_level: audienceLevel
        });
        setResult(res);
        playOutcome(res);
      }
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Grading temporarily unavailable. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResetForNewQuestion = () => {
    setResult(null);
    setTutorContext(null);
    setErrorMsg(null);
  };

  const loadPreset = (preset: typeof PRESET_EXAMPLES[0]) => {
    setQuestionText(preset.question);
    setRawInput(preset.solution);
    setSubject(preset.subject);
    setSkillId(preset.skill_id);
    setResult(null);
    setTutorContext(null);
    setErrorMsg(null);
  };

  const handleOpenCapabilities = async () => {
    setShowCapabilityModal(true);
    if (capabilityMatrix.length === 0) {
      setLoadingMatrix(true);
      try {
        const matrix = await stepGraderApi.getCapabilityMatrix();
        setCapabilityMatrix(matrix);
      } catch (err) {
        console.error('Failed to load capability matrix', err);
      } finally {
        setLoadingMatrix(false);
      }
    }
  };

  const handleReviewWithGenie = async () => {
    if (!result?.attempt_id) return;
    setLoadingTutorContext(true);
    try {
      const ctx = await stepGraderApi.getTutorContext(result.attempt_id);
      setTutorContext(ctx);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Could not fetch tutor review context.');
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
      <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        {/* Header Section */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2 text-indigo-400 text-sm font-semibold mb-1">
                <ListChecks className="w-4 h-4" />
                <span>REASONING DIAGNOSTICS & STEP-GRADER</span>
              </div>
              <h1 className="text-2xl font-bold text-slate-100">
                Check My Steps
              </h1>
              <p className="text-sm text-slate-400 mt-1">
                Pinpoint exactly where your reasoning first needs attention, separating root errors from downstream steps.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={handleOpenCapabilities}
                className="px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700/60 flex items-center space-x-1.5 transition-colors"
              >
                <Shield className="w-3.5 h-3.5 text-indigo-400" />
                <span>Capability Matrix</span>
              </button>

              {/* Age / Audience Level Adaptor */}
              <div className="flex items-center bg-slate-950/80 border border-slate-800 rounded-lg p-0.5 text-xs">
                {(['young', 'standard', 'advanced'] as const).map((lvl) => (
                  <button
                    key={lvl}
                    type="button"
                    onClick={() => setAudienceLevel(lvl)}
                    className={`px-2.5 py-1 rounded-md font-medium capitalize transition-all ${
                      audienceLevel === lvl
                        ? 'bg-indigo-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {lvl}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Quick Presets */}
          <div className="mt-4 pt-4 border-t border-slate-800/80">
            <span className="text-xs text-slate-400 font-medium mr-2">Try an example:</span>
            <div className="inline-flex flex-wrap gap-1.5 mt-2 sm:mt-0">
              {PRESET_EXAMPLES.map((preset) => (
                <button
                  key={preset.name}
                  type="button"
                  onClick={() => loadPreset(preset)}
                  className="px-2.5 py-1 text-xs rounded-md bg-slate-800/60 hover:bg-slate-800 text-slate-300 border border-slate-700/50 hover:border-indigo-500/50 transition-colors"
                >
                  {preset.name}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Input & Workspace Section */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-6 space-y-4">
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Question / Problem Statement
                </label>
                <input
                  type="text"
                  value={questionText}
                  onChange={(e) => setQuestionText(e.target.value)}
                  placeholder="e.g. Solve for x: 2x + 4 = 10"
                  className="w-full px-3.5 py-2.5 bg-slate-950/90 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Your Step-by-Step Solution
                  </label>
                  <span className="text-xs text-slate-500">One step per line</span>
                </div>
                <textarea
                  rows={8}
                  value={rawInput}
                  onChange={(e) => setRawInput(e.target.value)}
                  placeholder="1. 2x + 4 = 10&#10;2. 2x = 10 + 4&#10;3. x = 7"
                  className="w-full font-mono px-3.5 py-2.5 bg-slate-950/90 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-600 text-sm focus:outline-none focus:border-indigo-500 transition-colors leading-relaxed"
                />
              </div>

              {errorMsg && (
                <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-300 text-xs flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <div className="flex items-center justify-between pt-2">
                {result ? (
                  <button
                    type="button"
                    onClick={handleResetForNewQuestion}
                    className="px-3.5 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
                  >
                    New Problem
                  </button>
                ) : (
                  <span className="text-xs text-slate-500">Deterministic check first</span>
                )}

                <button
                  type="button"
                  onClick={handleGrade}
                  disabled={submitting}
                  className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 disabled:text-indigo-400 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-indigo-600/20 flex items-center space-x-2"
                >
                  {submitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Diagnosing Steps...</span>
                    </>
                  ) : result ? (
                    <>
                      <RefreshCw className="w-4 h-4" />
                      <span>Check Revised Steps (Attempt {(result.attempt_sequence || 1) + 1})</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      <span>Check My Steps</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Results & Step Diagnosis Section */}
          <div className="lg:col-span-6 space-y-4">
            {!result ? (
              <div className="h-full min-h-[320px] bg-slate-900/40 border border-dashed border-slate-800 rounded-2xl p-8 flex flex-col items-center justify-center text-center">
                <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-3">
                  <ListChecks className="w-6 h-6" />
                </div>
                <h3 className="text-slate-200 font-semibold text-base mb-1">
                  Ready to Validate Reasoning
                </h3>
                <p className="text-xs text-slate-400 max-w-sm leading-relaxed">
                  Enter your steps on the left and click "Check My Steps". We validate each transformation, find the first issue, and explain what happened without fake percentage scores.
                </p>
              </div>
            ) : (
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-5">
                {/* Result Headline Banner */}
                <div className="flex items-start justify-between gap-3 pb-4 border-b border-slate-800">
                  <div className="flex items-start space-x-3">
                    {result.overall_outcome === 'ALL_STEPS_VALID' ? (
                      <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
                        <CheckCircle2 className="w-5 h-5" />
                      </div>
                    ) : result.overall_outcome === 'ROOT_ERROR_DETECTED' ? (
                      <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 shrink-0">
                        <AlertTriangle className="w-5 h-5" />
                      </div>
                    ) : (
                      <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400 shrink-0">
                        <HelpCircle className="w-5 h-5" />
                      </div>
                    )}

                    <div>
                      <h3 className="text-base font-semibold text-slate-100">
                        {result.overall_outcome === 'ALL_STEPS_VALID'
                          ? 'All reasoning steps are valid!'
                          : result.first_wrong_step
                          ? `First issue detected at Step ${result.first_wrong_step}`
                          : 'Ambiguous or unverified reasoning'}
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {result.feedback_summary}
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-col items-end shrink-0">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                      Attempt {result.attempt_sequence}
                    </span>
                    <span className="text-[10px] text-slate-500 mt-1">
                      Confidence: {result.confidence}
                    </span>
                  </div>
                </div>

                {/* Step Diagnosis Cards */}
                <div className="space-y-2.5">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Step Inspection
                  </h4>
                  {result.validated_steps.map((step) => {
                    const isRoot = step.is_root_error || step.validation_status === 'ROOT_ERROR';
                    const isDownstream = step.validation_status === 'DOWNSTREAM_ERROR';
                    const isValid = step.validation_status === 'VALID_STEP';

                    let cardClass = 'bg-slate-950/60 border-slate-800 text-slate-300';
                    let icon = <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
                    let badgeText = 'Valid transformation';
                    let badgeClass = 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';

                    if (isRoot) {
                      cardClass = 'bg-amber-950/20 border-amber-500/30 text-amber-100';
                      icon = <AlertTriangle className="w-4 h-4 text-amber-400" />;
                      badgeText = 'Needs another look';
                      badgeClass = 'text-amber-400 bg-amber-500/10 border-amber-500/20';
                    } else if (isDownstream) {
                      cardClass = 'bg-indigo-950/20 border-indigo-500/30 text-slate-300';
                      icon = <ArrowDownCircle className="w-4 h-4 text-indigo-400" />;
                      badgeText = `Follows from Step ${result.first_wrong_step}`;
                      badgeClass = 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20';
                    } else if (step.validation_status === 'UNCERTAIN') {
                      cardClass = 'bg-slate-900 border-slate-800 text-slate-300';
                      icon = <HelpCircle className="w-4 h-4 text-slate-400" />;
                      badgeText = 'Ambiguous';
                      badgeClass = 'text-slate-400 bg-slate-800 border-slate-700';
                    }

                    return (
                      <div
                        key={step.id || step.step_index}
                        className={`p-3.5 rounded-xl border transition-all ${cardClass}`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center space-x-2">
                            {icon}
                            <span className="font-mono text-xs font-semibold text-slate-200">
                              Step {step.step_index}
                            </span>
                          </div>
                          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${badgeClass}`}>
                            {badgeText}
                          </span>
                        </div>

                        <div className="font-mono text-xs text-slate-100 bg-slate-950/80 px-2.5 py-1.5 rounded-lg border border-slate-800/80 mb-2 overflow-x-auto">
                          {step.raw_text}
                        </div>

                        <p className="text-xs leading-relaxed text-slate-300">
                          {step.feedback}
                        </p>

                        {isRoot && step.error_type && (
                          <div className="mt-2 pt-2 border-t border-amber-500/20 flex items-center justify-between text-[11px] text-amber-300">
                            <span>Mistake Pattern: <strong>{step.error_type}</strong></span>
                            <span className="text-[10px] text-amber-400/80">Validator: {step.validator_type}</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Recommended Next Action */}
                <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 flex items-start space-x-3 text-xs">
                  <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <div className="space-y-0.5">
                    <span className="font-semibold text-slate-200">Recommended Next Step:</span>
                    <p className="text-slate-400">{result.recommended_next_action}</p>
                  </div>
                </div>

                {/* Socratic Tutor Handoff Action */}
                {result.can_review_with_tutor && (
                  <div className="pt-2 flex flex-col sm:flex-row gap-2.5">
                    <button
                      type="button"
                      onClick={handleReviewWithGenie}
                      disabled={loadingTutorContext}
                      className="flex-1 px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl text-xs font-semibold transition-all flex items-center justify-center space-x-2 shadow-lg shadow-indigo-600/20"
                    >
                      {loadingTutorContext ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          <span>Preparing Bounded Context...</span>
                        </>
                      ) : (
                        <>
                          <GraduationCap className="w-4 h-4" />
                          <span>Review Step {result.first_wrong_step} with Genie</span>
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Bounded Socratic Tutor Review Modal */}
        {tutorContext && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
              <div className="flex items-center space-x-3 pb-3 border-b border-slate-800">
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                  <GraduationCap className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-100">
                    Bounded Tutor Review Session
                  </h3>
                  <p className="text-xs text-slate-400">
                    Genie receives only the context for Step {tutorContext.first_wrong_step_index}
                  </p>
                </div>
              </div>

              <div className="space-y-2 text-xs">
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <span className="text-slate-400 block mb-1">Target Reasoning Step:</span>
                  <div className="font-mono text-slate-200">{tutorContext.step_raw_text}</div>
                </div>

                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <span className="text-slate-400 block mb-1">Diagnosis:</span>
                  <div className="text-slate-200">{tutorContext.feedback}</div>
                  <div className="mt-1 text-[11px] text-indigo-400">
                    Classified Pattern: {tutorContext.error_type}
                  </div>
                </div>

                {tutorContext.related_prerequisite && (
                  <div className="p-2.5 bg-slate-950/60 rounded-lg text-slate-400 text-[11px]">
                    Related Foundation: <span className="text-slate-300 font-medium">{tutorContext.related_prerequisite}</span>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setTutorContext(null)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={launchTutorChat}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center space-x-1.5"
                >
                  <span>Start Socratic Dialogue</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Capability Matrix Modal */}
        {showCapabilityModal && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 shadow-2xl space-y-4 max-h-[85vh] flex flex-col">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800 shrink-0">
                <div className="flex items-center space-x-2">
                  <Shield className="w-5 h-5 text-indigo-400" />
                  <h3 className="text-base font-semibold text-slate-100">
                    Honest Capability Matrix
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setShowCapabilityModal(false)}
                  className="text-slate-400 hover:text-slate-200 text-sm"
                >
                  ✕
                </button>
              </div>

              <p className="text-xs text-slate-400 shrink-0">
                LearnByGenie distinguishes deterministic AST verification from rubric fallback. No fake claims of universal grading certainty.
              </p>

              <div className="overflow-y-auto flex-1 space-y-2 pr-1">
                {loadingMatrix ? (
                  <div className="py-12 text-center text-xs text-slate-400 flex items-center justify-center space-x-2">
                    <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
                    <span>Loading capabilities...</span>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-800/80 border border-slate-800 rounded-xl overflow-hidden">
                    {capabilityMatrix.map((item, idx) => (
                      <div key={idx} className="p-3.5 bg-slate-950/60 text-xs space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-200">
                            {item.subject} — {item.skill_name}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                            item.confidence_capability === 'HIGH'
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          }`}>
                            {item.confidence_capability} CONFIDENCE
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400">
                          Primary Validator: <span className="text-slate-300 font-mono">{item.validator_type}</span>
                          {item.deterministic_support && (
                            <span className="ml-2 text-emerald-400 font-medium">✓ Deterministic</span>
                          )}
                          {item.rubric_support && (
                            <span className="ml-2 text-indigo-400 font-medium">✓ Rubric Supported</span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-400 leading-relaxed">{item.notes}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="pt-3 border-t border-slate-800 flex justify-end shrink-0">
                <button
                  type="button"
                  onClick={() => setShowCapabilityModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-medium"
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

export default StepCheckPage;
