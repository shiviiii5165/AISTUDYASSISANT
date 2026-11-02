import React, { useState, useEffect } from 'react';
import {
  startDiagnostic,
  submitDiagnosticAnswer,
  getDiagnosticSession,
  getDiagnosticHistory
} from '../lib/diagnosticApi';
import { soundFx } from '../lib/soundFx';
import type {
  DiagnosticStepResponse,
  DiagnosticResult,
  StudentItemView
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
  Layers
} from 'lucide-react';

const AVAILABLE_SUBJECTS = [
  'Mathematics',
  'Physics',
  'Chemistry',
  'Biology',
  'Science',
  'English',
  'Computer Science'
];

export const DiagnosticPage: React.FC = () => {
  const [selectedSubject, setSelectedSubject] = useState<string>('Mathematics');
  const [stepData, setStepData] = useState<DiagnosticStepResponse | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<DiagnosticResult[]>([]);
  const [viewHistory, setViewHistory] = useState<boolean>(false);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const res = await getDiagnosticHistory();
      setHistory(res);
    } catch {
      // Quiet fail if offline/mock
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
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 max-w-3xl mx-auto shadow-xl">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-400 mb-6 uppercase tracking-wider">
          <span className="flex items-center gap-2">
            <Compass className="w-4 h-4 text-emerald-400" />
            Adaptive Diagnostic • {stepData?.session?.subject}
          </span>
          <span className="bg-slate-800 px-3 py-1 rounded-full text-slate-300">
            Probe {q.sequence_number} of ~{q.total_budget}
          </span>
        </div>

        <h3 className="text-xl font-medium text-slate-100 mb-8 leading-relaxed">
          {q.prompt}
        </h3>

        {q.options && q.options.length > 0 ? (
          <div className="space-y-3 mb-8">
            {q.options.map((opt, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setSelectedAnswer(opt)}
                className={`w-full text-left p-4 rounded-xl border transition-all text-sm font-medium flex items-center justify-between ${
                  selectedAnswer === opt
                    ? 'border-emerald-500 bg-emerald-500/10 text-emerald-200'
                    : 'border-slate-800 bg-slate-950/60 text-slate-300 hover:border-slate-700 hover:bg-slate-800/40'
                }`}
              >
                <span>{opt}</span>
                <span className={`w-4 h-4 rounded-full border ${selectedAnswer === opt ? 'border-emerald-400 bg-emerald-400' : 'border-slate-700'}`} />
              </button>
            ))}
          </div>
        ) : (
          <div className="mb-8">
            <input
              type="text"
              value={selectedAnswer}
              onChange={(e) => setSelectedAnswer(e.target.value)}
              placeholder="Enter your solution..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-emerald-500"
            />
          </div>
        )}

        <div className="flex items-center justify-end">
          <button
            type="button"
            disabled={!selectedAnswer || loading}
            onClick={handleSubmitAnswer}
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-sm transition-all"
          >
            {loading ? 'Submitting...' : 'Submit Response'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  };

  const renderResult = (res: DiagnosticResult) => {
    const secureSkills = res.skill_results.filter((s) => s.diagnostic_state === 'SECURE');
    const developingSkills = res.skill_results.filter((s) => s.diagnostic_state === 'DEVELOPING');
    const repairSkills = res.skill_results.filter((s) => s.diagnostic_state === 'NEEDS_REPAIR');

    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 max-w-4xl mx-auto shadow-xl space-y-8">
        <div>
          <div className="flex items-center gap-2 text-emerald-400 text-sm font-medium mb-2">
            <CheckCircle2 className="w-4 h-4" />
            Diagnostic Assessment Complete
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">
            Learning Starting Point: {res.subject}
          </h2>
          <p className="text-slate-400 text-sm">
            Enrolled: Class {res.enrolled_grade} • Track: {res.exam_track}
          </p>
        </div>

        {/* Operating Level Banner */}
        <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-5">
          <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-1">
            Recommended Focus
          </div>
          <div className="text-lg font-semibold text-emerald-300">
            {res.operating_level_band}
          </div>
          <div className="text-sm text-slate-400 mt-2">
            {res.summary}
          </div>
        </div>

        {/* Conceptual Skill Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Secure */}
          <div className="bg-slate-950/50 border border-slate-800/80 rounded-xl p-5">
            <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm mb-4">
              <CheckCircle2 className="w-4 h-4" />
              Secure Foundations ({secureSkills.length})
            </div>
            {secureSkills.length > 0 ? (
              <ul className="space-y-3">
                {secureSkills.map((s, idx) => (
                  <li key={idx} className="text-xs text-slate-300">
                    <span className="font-medium text-slate-200">{s.skill_name}</span>
                    <div className="text-slate-500 mt-0.5">{s.confidence_class.replace('_', ' ').toLowerCase()}</div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-xs text-slate-500 italic">No skills classified secure in this session.</div>
            )}
          </div>

          {/* Developing */}
          <div className="bg-slate-950/50 border border-slate-800/80 rounded-xl p-5">
            <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm mb-4">
              <HelpCircle className="w-4 h-4" />
              Developing Concepts ({developingSkills.length})
            </div>
            {developingSkills.length > 0 ? (
              <ul className="space-y-3">
                {developingSkills.map((s, idx) => (
                  <li key={idx} className="text-xs text-slate-300">
                    <span className="font-medium text-slate-200">{s.skill_name}</span>
                    <div className="text-slate-500 mt-0.5">{s.recommended_action}</div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-xs text-slate-500 italic">No concepts in developing state.</div>
            )}
          </div>

          {/* Needs Repair */}
          <div className="bg-slate-950/50 border border-slate-800/80 rounded-xl p-5">
            <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm mb-4">
              <AlertCircle className="w-4 h-4" />
              Prerequisites Needing Repair ({repairSkills.length})
            </div>
            {repairSkills.length > 0 ? (
              <ul className="space-y-3">
                {repairSkills.map((s, idx) => (
                  <li key={idx} className="text-xs text-slate-300">
                    <span className="font-medium text-amber-300">{s.skill_name}</span>
                    <div className="text-slate-500 mt-0.5">{s.recommended_action}</div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-xs text-slate-500 italic">No critical prerequisite gaps identified.</div>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          <button
            type="button"
            onClick={() => handleStart(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-700 text-slate-300 hover:text-white hover:border-slate-600 text-xs font-medium transition-all"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Retake Diagnostic
          </button>
          <button
            type="button"
            onClick={() => {
              setStepData(null);
              setViewHistory(false);
            }}
            className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-all"
          >
            Back to Overview
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-12">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 uppercase tracking-widest mb-1">
              <Compass className="w-4 h-4" />
              Educational Readiness Assessment
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-white">
              Adaptive Subject Diagnostic
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Determines foundational prerequisite readiness and the optimal learning starting point.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setViewHistory(!viewHistory)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-800 bg-slate-900/60 text-slate-300 hover:text-white hover:border-slate-700 text-xs font-medium transition-all"
            >
              <History className="w-4 h-4 text-slate-400" />
              {viewHistory ? 'Hide History' : 'Diagnostic History'}
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-xs text-amber-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* View History Section */}
        {viewHistory && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
              <History className="w-4 h-4 text-emerald-400" />
              Historical Diagnostics ({history.length})
            </h3>
            {history.length > 0 ? (
              <div className="divide-y divide-slate-800">
                {history.map((h, i) => (
                  <div key={i} className="py-3 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-semibold text-slate-200">{h.subject}</span>
                      <span className="text-slate-500 ml-2">• Class {h.enrolled_grade} ({h.exam_track})</span>
                      <div className="text-slate-400 mt-0.5">{h.operating_level_band}</div>
                    </div>
                    <div className="text-right">
                      <span className="text-slate-500">{h.created_at ? new Date(h.created_at).toLocaleDateString() : 'Recorded'}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-slate-500 italic">No historical diagnostics recorded yet.</div>
            )}
          </div>
        )}

        {/* Main Body */}
        {!stepData && (
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-8 max-w-2xl mx-auto text-center space-y-6">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
              <Layers className="w-6 h-6" />
            </div>

            <div>
              <h2 className="text-xl font-bold text-white mb-2">
                Select Diagnostic Subject
              </h2>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Each diagnostic assesses 6–10 bounded conceptual probes tailored to your curriculum and grade band.
              </p>
            </div>

            <div className="flex flex-wrap justify-center gap-2 max-w-md mx-auto">
              {AVAILABLE_SUBJECTS.map((sub) => (
                <button
                  key={sub}
                  type="button"
                  onClick={() => setSelectedSubject(sub)}
                  className={`px-4 py-2 rounded-xl text-xs font-medium border transition-all ${
                    selectedSubject === sub
                      ? 'border-emerald-500 bg-emerald-500/10 text-emerald-300'
                      : 'border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                  }`}
                >
                  {sub}
                </button>
              ))}
            </div>

            <button
              type="button"
              disabled={loading}
              onClick={() => handleStart(false)}
              className="px-8 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition-all flex items-center gap-2 mx-auto"
            >
              <BookOpen className="w-4 h-4" />
              {loading ? 'Initializing Diagnostic...' : `Begin ${selectedSubject} Diagnostic`}
            </button>
          </div>
        )}

        {stepData && !stepData.is_completed && stepData.current_question && (
          renderActiveQuestion(stepData.current_question)
        )}

        {stepData && stepData.is_completed && stepData.result && (
          renderResult(stepData.result)
        )}
      </div>
    </div>
  );
};

export default DiagnosticPage;
