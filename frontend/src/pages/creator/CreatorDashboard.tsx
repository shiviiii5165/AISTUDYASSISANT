import React, { useEffect, useState } from 'react';
import { 
  FileEdit, BookOpen, Layers, CheckCircle2, Plus, 
  RefreshCw, ListChecks, HelpCircle, Sparkles, Filter 
} from 'lucide-react';
import CreatorLayout from '../../components/layout/CreatorLayout';
import { 
  fetchCreatorDashboard, 
  createPracticeItem 
} from '../../lib/portalsApi';
import type { CreatorDashboardSummary } from '../../lib/portalsApi';

export default function CreatorDashboard() {
  const [data, setData] = useState<CreatorDashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Author Question Modal State
  const [showAuthorModal, setShowAuthorModal] = useState(false);
  const [skillId, setSkillId] = useState('MATH_LIN_EQ');
  const [promptText, setPromptText] = useState('');
  const [questionType, setQuestionType] = useState('MCQ');
  const [correctAnswer, setCorrectAnswer] = useState('');
  const [optionsStr, setOptionsStr] = useState('Option A, Option B, Option C, Option D');
  const [hint, setHint] = useState('');
  const [explanation, setExplanation] = useState('');
  const [authoring, setAuthoring] = useState(false);
  const [authorMsg, setAuthorMsg] = useState<{ text: string; error: boolean } | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchCreatorDashboard();
      setData(res);
    } catch (err: any) {
      console.error('Failed to load creator dashboard:', err);
      setError(err?.response?.data?.detail || err.message || 'Failed to load creator dashboard.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAuthorItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!promptText.trim() || !correctAnswer.trim()) return;

    try {
      setAuthoring(true);
      setAuthorMsg(null);
      const options = optionsStr.split(',').map((o) => o.trim()).filter(Boolean);
      await createPracticeItem({
        skill_id: skillId,
        prompt_text: promptText.trim(),
        question_type: questionType,
        correct_answer: correctAnswer.trim(),
        options: options.length > 0 ? options : undefined,
        hints: hint.trim() ? [hint.trim()] : [],
        explanation: explanation.trim() || undefined,
        difficulty_tier: 'CORE_FOUNDATIONAL',
      });
      setAuthorMsg({ text: 'Question authored and verified successfully!', error: false });
      setPromptText('');
      setCorrectAnswer('');
      setHint('');
      setExplanation('');
      await loadData();
      setTimeout(() => setShowAuthorModal(false), 1200);
    } catch (err: any) {
      setAuthorMsg({
        text: err?.response?.data?.detail || err.message || 'Failed to author question item.',
        error: true,
      });
    } finally {
      setAuthoring(false);
    }
  };

  return (
    <CreatorLayout title="Content Creator Workbench">
      <div className="max-w-6xl mx-auto p-4 md:p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--border)] pb-5">
          <div>
            <div className="flex items-center gap-2 text-sm text-[var(--accent-royal)] font-semibold uppercase tracking-wider">
              <FileEdit className="w-4 h-4" />
              Content Creator Workbench
            </div>
            <h1 className="text-2xl md:text-3xl font-display font-bold text-[var(--text-primary)] mt-1">
              Curriculum & Question Authoring
            </h1>
            <p className="text-[var(--text-secondary)] text-sm mt-1">
              Author, calibrate, and verify pedagogical question items, distractor rubrics, and curriculum blueprints.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowAuthorModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[var(--accent-royal)] text-white text-sm font-semibold hover:bg-opacity-90 shadow-sm transition"
            >
              <Plus className="w-4 h-4" />
              Author Question Item
            </button>
            <button
              onClick={loadData}
              disabled={loading}
              className="p-2.5 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition"
              title="Refresh"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Loading */}
        {loading && !data && (
          <div className="flex flex-col items-center justify-center p-16 space-y-3">
            <div className="w-8 h-8 border-3 border-[var(--accent-royal)] border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-[var(--text-secondary)]">Loading item bank inventory...</span>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-sm">
            {error}
          </div>
        )}

        {/* Content */}
        {data && (
          <>
            {/* Stats Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)]">
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>Total Item Bank</span>
                  <HelpCircle className="w-4 h-4 text-blue-400" />
                </div>
                <div className="text-2xl font-bold text-[var(--text-primary)] mt-1">
                  {data.item_bank_stats.total_items}
                </div>
                <div className="text-[11px] text-emerald-400 mt-0.5 font-medium">
                  {data.item_bank_stats.verified_items_count} Verified & Live
                </div>
              </div>

              <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)]">
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>Multiple Choice (MCQ)</span>
                  <ListChecks className="w-4 h-4 text-purple-400" />
                </div>
                <div className="text-2xl font-bold text-purple-400 mt-1">
                  {data.item_bank_stats.mcq_count}
                </div>
                <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                  With distractor diagnosis
                </div>
              </div>

              <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)]">
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>Numeric Input Items</span>
                  <Sparkles className="w-4 h-4 text-amber-400" />
                </div>
                <div className="text-2xl font-bold text-amber-400 mt-1">
                  {data.item_bank_stats.numeric_count}
                </div>
                <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                  Tolerance checked
                </div>
              </div>

              <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)]">
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>Step Derivations</span>
                  <Layers className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-2xl font-bold text-emerald-400 mt-1">
                  {data.item_bank_stats.derivation_count}
                </div>
                <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                  Multi-step evaluated
                </div>
              </div>
            </div>

            {/* Published Modules & Curriculum Coverage */}
            <div className="space-y-3">
              <h3 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-[var(--accent-royal)]" />
                Published Curriculum Modules ({data.recent_curriculum_modules.length})
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {data.recent_curriculum_modules.map((mod) => (
                  <div
                    key={mod.id}
                    className="p-5 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] space-y-3 shadow-sm hover:border-[var(--accent-royal)] transition"
                  >
                    <div className="flex items-center justify-between">
                      <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {mod.domain}
                      </span>
                      <span className="text-xs text-[var(--text-secondary)] font-mono">
                        {mod.skills_count} Skills
                      </span>
                    </div>
                    <h4 className="text-base font-bold text-[var(--text-primary)]">
                      {mod.name}
                    </h4>
                    <p className="text-xs text-[var(--text-secondary)]">
                      Module ID: <span className="font-mono">{mod.id}</span>
                    </p>
                    <div className="pt-2 flex items-center gap-2 text-xs text-emerald-400">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Aligned to CBSE / NCERT standard</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Author Question Modal */}
        {showAuthorModal && (
          <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="w-full max-w-lg bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-[var(--text-primary)]">
                  Author Question Item
                </h3>
                <button
                  onClick={() => setShowAuthorModal(false)}
                  className="text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleAuthorItem} className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                      Skill ID
                    </label>
                    <select
                      value={skillId}
                      onChange={(e) => setSkillId(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-royal)]"
                    >
                      <option value="MATH_LIN_EQ">MATH_LIN_EQ (Linear Equations)</option>
                      <option value="MATH_QUAD_EQ">MATH_QUAD_EQ (Quadratic Equations)</option>
                      <option value="MATH_NUM_OPS">MATH_NUM_OPS (Numeric Operations)</option>
                      <option value="MATH_RATIOS">MATH_RATIOS (Ratios & Proportions)</option>
                      <option value="MATH_EXPONENTS">MATH_EXPONENTS (Exponents & Powers)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                      Question Type
                    </label>
                    <select
                      value={questionType}
                      onChange={(e) => setQuestionType(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-royal)]"
                    >
                      <option value="MCQ">Multiple Choice (MCQ)</option>
                      <option value="NUMERIC">Numeric Input</option>
                      <option value="DERIVATION_STEP">Step Derivation</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                    Question Prompt (Markdown / LaTeX supported)
                  </label>
                  <textarea
                    rows={3}
                    value={promptText}
                    onChange={(e) => setPromptText(e.target.value)}
                    placeholder="e.g. Solve for x: 3x - 7 = 14"
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-royal)]"
                    required
                  />
                </div>

                {questionType === 'MCQ' && (
                  <div>
                    <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                      Options (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={optionsStr}
                      onChange={(e) => setOptionsStr(e.target.value)}
                      placeholder="e.g. 7, -7, 21, 5"
                      className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-royal)]"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                    Correct Answer
                  </label>
                  <input
                    type="text"
                    value={correctAnswer}
                    onChange={(e) => setCorrectAnswer(e.target.value)}
                    placeholder="e.g. 7"
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-royal)]"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                    Socratic Hint (optional)
                  </label>
                  <input
                    type="text"
                    value={hint}
                    onChange={(e) => setHint(e.target.value)}
                    placeholder="e.g. Add 7 to both sides first."
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-royal)]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                    Pedagogical Explanation
                  </label>
                  <textarea
                    rows={2}
                    value={explanation}
                    onChange={(e) => setExplanation(e.target.value)}
                    placeholder="Explain the step-by-step logic."
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-royal)]"
                  />
                </div>

                {authorMsg && (
                  <div
                    className={`p-3 rounded-xl text-xs ${
                      authorMsg.error
                        ? 'bg-rose-500/10 border border-rose-500/20 text-rose-300'
                        : 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-300'
                    }`}
                  >
                    {authorMsg.text}
                  </div>
                )}

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAuthorModal(false)}
                    className="px-4 py-2 rounded-xl text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={authoring}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-[var(--accent-royal)] text-white hover:bg-opacity-90 disabled:opacity-50"
                  >
                    {authoring ? 'Authoring...' : 'Save & Publish Item'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </CreatorLayout>
  );
}
