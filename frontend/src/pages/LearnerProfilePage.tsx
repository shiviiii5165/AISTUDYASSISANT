import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  GraduationCap,
  BookOpen,
  Target,
  Languages,
  Clock,
  CheckCircle2,
  AlertCircle,
  Save,
  RotateCcw,
  Sparkles,
  Compass,
  Sliders,
  Layers
} from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { 
  fetchAcademicConfig, 
  fetchLearnerProfile, 
  updateLearnerProfile 
} from '../lib/learnerApi';
import type { AcademicConfig, LearnerProfile, LearnerProfileUpdate } from '../types/learner';
import OnboardingModal from '../components/OnboardingModal';

export const LearnerProfilePage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState<AcademicConfig | null>(null);
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [showGuidedModal, setShowGuidedModal] = useState(false);

  // Form fields
  const [level, setLevel] = useState('class_11');
  const [board, setBoard] = useState('CBSE');
  const [stream, setStream] = useState('science_pcm');
  const [targetExam, setTargetExam] = useState('JEE');
  const [targetYear, setTargetYear] = useState<number>(new Date().getFullYear() + 1);
  const [subjects, setSubjects] = useState<string[]>(['Physics', 'Chemistry', 'Mathematics']);
  
  const [shortTermGoal, setShortTermGoal] = useState('');
  const [longTermGoal, setLongTermGoal] = useState('');
  
  const [language, setLanguage] = useState('hinglish');
  const [explanationLang, setExplanationLang] = useState('hinglish');
  const [difficulty, setDifficulty] = useState('standard');
  const [sessionMinutes, setSessionMinutes] = useState(30);
  const [weeklyHours, setWeeklyHours] = useState(10.0);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setFeedbackMsg(null);
    try {
      const [cfgData, profData] = await Promise.all([
        fetchAcademicConfig(),
        fetchLearnerProfile(),
      ]);
      setConfig(cfgData);
      setProfile(profData);
      populateForm(profData);
    } catch (err: any) {
      console.error('Failed to load profile data:', err);
      setFeedbackMsg({
        type: 'error',
        text: 'Failed to load profile settings from server. Check connection.'
      });
    } finally {
      setLoading(false);
    }
  };

  const populateForm = (prof: LearnerProfile) => {
    if (prof.education_level) setLevel(prof.education_level);
    if (prof.board_or_curriculum) setBoard(prof.board_or_curriculum);
    if (prof.academic_stream) setStream(prof.academic_stream);
    if (prof.target_exam) setTargetExam(prof.target_exam);
    if (prof.target_year) setTargetYear(prof.target_year);
    if (prof.subjects) setSubjects(prof.subjects);
    if (prof.short_term_goal) setShortTermGoal(prof.short_term_goal);
    if (prof.long_term_goal) setLongTermGoal(prof.long_term_goal);
    if (prof.preferred_language) setLanguage(prof.preferred_language);
    if (prof.explanation_language_preference) setExplanationLang(prof.explanation_language_preference);
    if (prof.content_difficulty_preference) setDifficulty(prof.content_difficulty_preference);
    if (prof.preferred_session_minutes) setSessionMinutes(prof.preferred_session_minutes);
    if (prof.weekly_study_availability_hours) setWeeklyHours(prof.weekly_study_availability_hours);
  };

  const currentLevelObj = config?.education_levels.find(l => l.id === level);
  const isUndergrad = currentLevelObj?.stage === 'UNDERGRADUATE';
  const hasStreams = currentLevelObj?.has_streams ?? false;

  const toggleSubject = (name: string) => {
    if (subjects.includes(name)) {
      if (subjects.length > 1) {
        setSubjects(subjects.filter(s => s !== name));
      }
    } else {
      setSubjects([...subjects, name]);
    }
  };

  const handleSave = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSaving(true);
    setFeedbackMsg(null);

    const updates: LearnerProfileUpdate = {
      education_level: level,
      board_or_curriculum: board,
      academic_stream: hasStreams ? stream : 'general',
      target_exam: targetExam,
      target_year: targetYear,
      subjects: subjects,
      short_term_goal: shortTermGoal.trim() || undefined,
      long_term_goal: longTermGoal.trim() || undefined,
      preferred_language: language,
      explanation_language_preference: explanationLang,
      content_difficulty_preference: difficulty,
      preferred_session_minutes: sessionMinutes,
      weekly_study_availability_hours: weeklyHours,
      onboarding_completed: true,
    };

    try {
      const updated = await updateLearnerProfile(updates);
      setProfile(updated);
      populateForm(updated);
      setFeedbackMsg({
        type: 'success',
        text: 'Learning preferences updated successfully.'
      });
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to update preferences.';
      setFeedbackMsg({
        type: 'error',
        text: typeof msg === 'string' ? msg : JSON.stringify(msg)
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <AppLayout title="Learning Profile">
        <div className="flex h-[60vh] items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-3 border-[var(--accent-royal)] border-t-transparent rounded-full animate-spin" />
            <span className="text-sm font-medium text-[var(--text-secondary)]">Loading academic profile...</span>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Learning Profile">
      <SEO
        title="Learning Profile & Academic Context"
        description="Configure your academic stage, target exams, subjects, and personalized learning preferences on LearnByGenie."
      />
      <div className="mx-auto max-w-4xl space-y-6 p-4 md:p-6 lg:p-8">
        
        {/* Header with Version & Guided Flow button */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
              Student Profile &amp; Preferences
            </h1>
            <p className="text-sm text-[var(--text-secondary)] mt-1">
              Configure your canonical academic context. All AI tutors, practice engines, and simulations use these preferences.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowGuidedModal(true)}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold border border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)] text-[var(--text-primary)] transition shadow-sm"
            >
              <Compass className="w-3.5 h-3.5 text-[var(--accent-royal)]" />
              Guided Onboarding
            </button>
          </div>
        </div>

        {/* Deterministic Profile Completeness Card */}
        {profile && (
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-bento">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border)]">
              <div className="flex items-center gap-2.5">
                {profile.completeness.is_complete ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-amber-600 shrink-0" />
                )}
                <div>
                  <div className="text-sm font-bold text-[var(--text-primary)]">
                    {profile.completeness.status}
                  </div>
                  <div className="text-xs text-[var(--text-secondary)]">
                    Profile Version {profile.profile_version} · Last updated {profile.updated_at ? new Date(profile.updated_at).toLocaleDateString() : 'recently'}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold text-[var(--text-secondary)]">
                  Completeness: {profile.completeness.completion_percentage}%
                </span>
                <div className="w-24 bg-[var(--bg-secondary)] h-2 rounded-full overflow-hidden">
                  <div 
                    className="bg-[var(--accent-royal)] h-2 transition-all duration-500 rounded-full"
                    style={{ width: `${profile.completeness.completion_percentage}%` }}
                  />
                </div>
              </div>
            </div>

            {profile.completeness.missing_fields.length > 0 && (
              <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-amber-700">
                <span className="font-semibold">Recommended to configure:</span>
                {profile.completeness.missing_fields.map(field => (
                  <span key={field} className="px-2 py-0.5 rounded-md bg-amber-100/70 border border-amber-200">
                    {field.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Toast Feedback */}
        {feedbackMsg && (
          <div className={`p-4 rounded-xl text-sm font-medium border flex items-center justify-between ${
            feedbackMsg.type === 'success' 
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800' 
              : 'bg-amber-50 border-amber-200 text-amber-900'
          }`}>
            <span>{feedbackMsg.text}</span>
            <button 
              type="button" 
              onClick={() => setFeedbackMsg(null)}
              className="text-xs opacity-70 hover:opacity-100 underline ml-2"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Form Container */}
        <form onSubmit={handleSave} className="space-y-6">
          
          {/* SECTION 1: Academic Foundation */}
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-bento space-y-5">
            <div className="flex items-center gap-2 text-[var(--accent-royal)] border-b border-[var(--border)] pb-3">
              <GraduationCap className="w-5 h-5" />
              <h2 className="text-base font-bold text-[var(--text-primary)]">Academic Foundation</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Education Level */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase text-[var(--text-secondary)]">
                  Current Class / Education Level
                </label>
                <select
                  value={level}
                  onChange={(e) => {
                    const nextLvl = e.target.value;
                    setLevel(nextLvl);
                    const lvlObj = config?.education_levels.find(l => l.id === nextLvl);
                    if (lvlObj?.stage === 'PRIMARY' || lvlObj?.stage === 'MIDDLE' || lvlObj?.stage === 'SECONDARY') {
                      setStream('general');
                    }
                  }}
                  className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] px-3.5 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-royal)]"
                >
                  {config?.education_levels.map((lvl) => (
                    <option key={lvl.id} value={lvl.id}>
                      {lvl.name} ({lvl.stage.replace('_', ' ')})
                    </option>
                  ))}
                </select>
              </div>

              {/* Curriculum / Board */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase text-[var(--text-secondary)]">
                  Curriculum / Board
                </label>
                <select
                  value={board}
                  onChange={(e) => setBoard(e.target.value)}
                  className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] px-3.5 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-royal)]"
                >
                  {config?.curricula.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} — {c.full_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Stream (if applicable) */}
              {hasStreams && (
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold uppercase text-[var(--text-secondary)]">
                    Academic Stream
                  </label>
                  <select
                    value={stream}
                    onChange={(e) => setStream(e.target.value)}
                    className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] px-3.5 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-royal)]"
                  >
                    {config?.academic_streams
                      .filter(st => isUndergrad ? st.stages.includes('UNDERGRADUATE') : st.stages.includes('SENIOR_SECONDARY'))
                      .map((st) => (
                        <option key={st.id} value={st.id}>
                          {st.name}
                        </option>
                      ))}
                  </select>
                </div>
              )}

              {/* Target Exam */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase text-[var(--text-secondary)]">
                  Primary Target Exam
                </label>
                <select
                  value={targetExam}
                  onChange={(e) => setTargetExam(e.target.value)}
                  className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] px-3.5 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-royal)]"
                >
                  {config?.exam_tracks.map((ex) => (
                    <option key={ex.id} value={ex.id}>
                      {ex.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* SECTION 2: Goals & Timeline */}
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-bento space-y-5">
            <div className="flex items-center gap-2 text-[var(--accent-royal)] border-b border-[var(--border)] pb-3">
              <Target className="w-5 h-5" />
              <h2 className="text-base font-bold text-[var(--text-primary)]">Academic Goals &amp; Horizon</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1.5 md:col-span-2">
                <label className="text-xs font-semibold uppercase text-[var(--text-secondary)]">
                  Short-Term Goal (Next 1–3 months)
                </label>
                <input
                  type="text"
                  value={shortTermGoal}
                  onChange={(e) => setShortTermGoal(e.target.value)}
                  placeholder="e.g. Master Kinematics, Thermodynamics and organic reactions"
                  className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] px-3.5 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-royal)]"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase text-[var(--text-secondary)]">
                  Target Exam Year
                </label>
                <input
                  type="number"
                  value={targetYear}
                  onChange={(e) => setTargetYear(parseInt(e.target.value) || new Date().getFullYear())}
                  min={new Date().getFullYear() - 1}
                  max={new Date().getFullYear() + 8}
                  className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] px-3.5 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-royal)]"
                />
              </div>

              <div className="space-y-1.5 md:col-span-3">
                <label className="text-xs font-semibold uppercase text-[var(--text-secondary)]">
                  Long-Term Milestone
                </label>
                <input
                  type="text"
                  value={longTermGoal}
                  onChange={(e) => setLongTermGoal(e.target.value)}
                  placeholder="e.g. Rank under 2,000 in JEE Advanced or 95%+ in Class 12 Boards"
                  className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] px-3.5 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-royal)]"
                />
              </div>
            </div>
          </div>

          {/* SECTION 3: Subject Selection */}
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-bento space-y-4">
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
              <div className="flex items-center gap-2 text-[var(--accent-royal)]">
                <BookOpen className="w-5 h-5" />
                <h2 className="text-base font-bold text-[var(--text-primary)]">Active Subjects</h2>
              </div>
              <span className="text-xs font-semibold text-[var(--text-secondary)]">
                {subjects.length} selected
              </span>
            </div>

            <p className="text-xs text-[var(--text-secondary)]">
              Click to toggle subjects. These subjects focus your Library, AI Tutor sessions, and practice problems.
            </p>

            <div className="flex flex-wrap gap-2.5 pt-1">
              {config?.subjects.map((sub) => {
                const isSelected = subjects.includes(sub.name);
                return (
                  <button
                    key={sub.id}
                    type="button"
                    onClick={() => toggleSubject(sub.name)}
                    className={`px-3.5 py-2 rounded-xl text-xs font-medium border transition flex items-center gap-1.5 ${
                      isSelected
                        ? 'border-[var(--accent-royal)] bg-[var(--accent-royal)] text-white shadow-sm font-semibold'
                        : 'border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)]'
                    }`}
                  >
                    {isSelected && <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />}
                    <span>{sub.name}</span>
                    <span className={`text-[10px] px-1.5 py-0.2 rounded ${
                      isSelected ? 'bg-white/20 text-white' : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)]'
                    }`}>
                      {sub.category}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* SECTION 4: Language & Interaction Style */}
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-bento space-y-5">
            <div className="flex items-center gap-2 text-[var(--accent-royal)] border-b border-[var(--border)] pb-3">
              <Languages className="w-5 h-5" />
              <h2 className="text-base font-bold text-[var(--text-primary)]">Language &amp; Interaction</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Primary Language */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase text-[var(--text-secondary)]">
                  Primary Language
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] px-3.5 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-royal)]"
                >
                  {config?.languages.map((lng) => (
                    <option key={lng.id} value={lng.id}>
                      {lng.name} ({lng.native_label})
                    </option>
                  ))}
                </select>
              </div>

              {/* Explanation Language */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase text-[var(--text-secondary)]">
                  AI Explanation Language
                </label>
                <select
                  value={explanationLang}
                  onChange={(e) => setExplanationLang(e.target.value)}
                  className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] px-3.5 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-royal)]"
                >
                  {config?.languages.map((lng) => (
                    <option key={lng.id} value={lng.id}>
                      {lng.name} ({lng.native_label})
                    </option>
                  ))}
                </select>
              </div>

              {/* Content Difficulty */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase text-[var(--text-secondary)]">
                  Explanation Depth / Difficulty
                </label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-primary)] px-3.5 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-royal)]"
                >
                  <option value="foundational">Foundational (Step-by-step from zero)</option>
                  <option value="standard">Standard (Exam-balanced depth)</option>
                  <option value="advanced">Advanced (Rigorous problem-solving)</option>
                </select>
              </div>
            </div>
          </div>

          {/* SECTION 5: Study Availability */}
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-bento space-y-5">
            <div className="flex items-center gap-2 text-[var(--accent-royal)] border-b border-[var(--border)] pb-3">
              <Clock className="w-5 h-5" />
              <h2 className="text-base font-bold text-[var(--text-primary)]">Study Availability</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase text-[var(--text-secondary)]">
                  Preferred Session Length
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {[15, 30, 45, 60].map((mins) => (
                    <button
                      key={mins}
                      type="button"
                      onClick={() => setSessionMinutes(mins)}
                      className={`py-2.5 rounded-xl border text-sm font-semibold transition ${
                        sessionMinutes === mins
                          ? 'border-[var(--accent-royal)] bg-[var(--accent-royal)] text-white shadow-sm'
                          : 'border-[var(--border)] bg-[var(--bg-primary)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)]'
                      }`}
                    >
                      {mins}m
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase text-[var(--text-secondary)]">
                  Weekly Study Hours Availability: {weeklyHours} hrs
                </label>
                <input
                  type="range"
                  min="2"
                  max="40"
                  step="1"
                  value={weeklyHours}
                  onChange={(e) => setWeeklyHours(parseFloat(e.target.value))}
                  className="w-full accent-[var(--accent-royal)] py-2"
                />
                <div className="flex justify-between text-[10px] text-[var(--text-secondary)]">
                  <span>2 hrs/week</span>
                  <span>20 hrs/week</span>
                  <span>40 hrs/week</span>
                </div>
              </div>
            </div>
          </div>

          {/* Action Bar */}
          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={loadData}
              disabled={saving}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold border border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)] text-[var(--text-secondary)] transition"
            >
              <RotateCcw className="w-4 h-4" /> Reset Changes
            </button>

            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold bg-[var(--accent-royal)] text-white shadow-lg hover:opacity-90 transition disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving Preferences...' : 'Save Profile Preferences'}
            </button>
          </div>

        </form>

        {/* Guided Onboarding Modal */}
        {config && (
          <OnboardingModal
            isOpen={showGuidedModal}
            onClose={() => setShowGuidedModal(false)}
            config={config}
            initialProfile={profile}
            onCompleted={(updated) => {
              setProfile(updated);
              populateForm(updated);
              setFeedbackMsg({
                type: 'success',
                text: 'Guided academic profile setup completed!'
              });
            }}
          />
        )}

      </div>
    </AppLayout>
  );
};
export default LearnerProfilePage;
