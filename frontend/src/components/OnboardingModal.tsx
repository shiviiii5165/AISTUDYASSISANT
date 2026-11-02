import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  GraduationCap, 
  BookOpen, 
  Target, 
  Languages, 
  Clock, 
  ArrowRight, 
  ArrowLeft, 
  Check, 
  Sparkles,
  X
} from 'lucide-react';
import type { AcademicConfig, LearnerProfile } from '../types/learner';
import { updateLearnerProfile } from '../lib/learnerApi';

interface OnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: AcademicConfig;
  initialProfile?: LearnerProfile | null;
  onCompleted: (updatedProfile: LearnerProfile) => void;
}

export const OnboardingModal: React.FC<OnboardingModalProps> = ({
  isOpen,
  onClose,
  config,
  initialProfile,
  onCompleted,
}) => {
  const [step, setStep] = useState(1);
  const totalSteps = 5;
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [level, setLevel] = useState('class_11');
  const [board, setBoard] = useState('CBSE');
  const [stream, setStream] = useState('science_pcm');
  const [exam, setExam] = useState('JEE');
  const [targetYear, setTargetYear] = useState(new Date().getFullYear() + 1);
  const [subjects, setSubjects] = useState<string[]>(['Physics', 'Chemistry', 'Mathematics']);
  const [language, setLanguage] = useState('hinglish');
  const [sessionMinutes, setSessionMinutes] = useState(30);

  useEffect(() => {
    if (initialProfile) {
      if (initialProfile.education_level) setLevel(initialProfile.education_level);
      if (initialProfile.board_or_curriculum) setBoard(initialProfile.board_or_curriculum);
      if (initialProfile.academic_stream) setStream(initialProfile.academic_stream);
      if (initialProfile.target_exam) setExam(initialProfile.target_exam);
      if (initialProfile.target_year) setTargetYear(initialProfile.target_year);
      if (initialProfile.subjects?.length) setSubjects(initialProfile.subjects);
      if (initialProfile.preferred_language) setLanguage(initialProfile.preferred_language);
      if (initialProfile.preferred_session_minutes) setSessionMinutes(initialProfile.preferred_session_minutes);
    }
  }, [initialProfile]);

  if (!isOpen) return null;

  const currentLevelObj = config.education_levels.find(l => l.id === level);
  const isSeniorSecondary = currentLevelObj?.stage === 'SENIOR_SECONDARY';
  const isUndergrad = currentLevelObj?.stage === 'UNDERGRADUATE';
  const hasStreams = currentLevelObj?.has_streams ?? false;

  const handleNext = () => {
    setError(null);
    if (step < totalSteps) {
      setStep(step + 1);
    } else {
      handleFinish();
    }
  };

  const handleBack = () => {
    setError(null);
    if (step > 1) setStep(step - 1);
  };

  const toggleSubject = (name: string) => {
    if (subjects.includes(name)) {
      if (subjects.length > 1) {
        setSubjects(subjects.filter(s => s !== name));
      }
    } else {
      setSubjects([...subjects, name]);
    }
  };

  const handleFinish = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const updated = await updateLearnerProfile({
        education_level: level,
        board_or_curriculum: board,
        academic_stream: hasStreams ? stream : 'general',
        target_exam: exam,
        target_year: targetYear,
        subjects,
        preferred_language: language,
        explanation_language_preference: language,
        preferred_session_minutes: sessionMinutes,
        onboarding_completed: true,
      });
      onCompleted(updated);
      onClose();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to save profile. Please check your selections.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="w-full max-w-xl rounded-2xl bg-[var(--bg-card)] border border-[var(--border)] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div className="border-b border-[var(--border)] px-6 py-4 flex items-center justify-between bg-[var(--bg-secondary)]/50">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--accent-royal)]">
              Step {step} of {totalSteps}
            </span>
            <h2 className="text-lg font-bold text-[var(--text-primary)]">
              {step === 1 && 'What are you currently studying?'}
              {step === 2 && 'Which curriculum or board do you follow?'}
              {step === 3 && 'Select your academic stream & subjects'}
              {step === 4 && 'What is your primary academic goal?'}
              {step === 5 && 'Learning language & time preferences'}
            </h2>
          </div>
          <button 
            type="button" 
            onClick={onClose}
            className="rounded-lg p-1.5 text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] hover:text-[var(--text-primary)] transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step Progress Bar */}
        <div className="w-full bg-[var(--bg-secondary)] h-1.5">
          <div 
            className="bg-[var(--accent-royal)] h-1.5 transition-all duration-300"
            style={{ width: `${(step / totalSteps) * 100}%` }}
          />
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {error && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
              {error}
            </div>
          )}

          {/* STEP 1: Education Level */}
          {step === 1 && (
            <div className="space-y-4">
              <p className="text-sm text-[var(--text-secondary)]">
                Select your current class or degree year. This sets the foundational curriculum level.
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                {config.education_levels.map((lvl) => (
                  <button
                    key={lvl.id}
                    type="button"
                    onClick={() => {
                      setLevel(lvl.id);
                      if (lvl.stage === 'PRIMARY' || lvl.stage === 'MIDDLE' || lvl.stage === 'SECONDARY') {
                        setStream('general');
                        setExam(lvl.stage === 'SECONDARY' ? 'BOARDS' : 'SCHOOL_EXAMS');
                      } else if (lvl.stage === 'SENIOR_SECONDARY') {
                        setStream('science_pcm');
                        setExam('JEE');
                      } else if (lvl.stage === 'UNDERGRADUATE') {
                        setStream('engineering_cs');
                        setExam('UG_SEMESTER');
                      }
                    }}
                    className={`p-3 rounded-xl border text-left transition flex items-center justify-between ${
                      level === lvl.id
                        ? 'border-[var(--accent-royal)] bg-[var(--accent-baby)]/20 font-semibold text-[var(--accent-royal)]'
                        : 'border-[var(--border)] hover:bg-[var(--bg-secondary)] text-[var(--text-primary)]'
                    }`}
                  >
                    <span className="text-sm">{lvl.name}</span>
                    {level === lvl.id && <Check className="w-4 h-4 text-[var(--accent-royal)] shrink-0" />}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* STEP 2: Curriculum / Board */}
          {step === 2 && (
            <div className="space-y-4">
              <p className="text-sm text-[var(--text-secondary)]">
                Choose the educational board or curriculum your syllabus is aligned with.
              </p>
              <div className="space-y-2">
                {config.curricula
                  .filter(c => isUndergrad ? c.id === 'UNIVERSITY' : c.id !== 'UNIVERSITY')
                  .map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => setBoard(c.id)}
                      className={`w-full p-3.5 rounded-xl border text-left transition flex items-center justify-between ${
                        board === c.id
                          ? 'border-[var(--accent-royal)] bg-[var(--accent-baby)]/20 font-semibold text-[var(--accent-royal)]'
                          : 'border-[var(--border)] hover:bg-[var(--bg-secondary)] text-[var(--text-primary)]'
                      }`}
                    >
                      <div>
                        <div className="text-sm font-semibold">{c.name}</div>
                        <div className="text-xs text-[var(--text-secondary)]">{c.full_name}</div>
                      </div>
                      {board === c.id && <Check className="w-4 h-4 text-[var(--accent-royal)] shrink-0" />}
                    </button>
                  ))}
              </div>
            </div>
          )}

          {/* STEP 3: Stream & Subjects */}
          {step === 3 && (
            <div className="space-y-4">
              {hasStreams && (
                <div className="space-y-2">
                  <label className="text-xs font-semibold uppercase text-[var(--text-secondary)]">
                    Academic Stream
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {config.academic_streams
                      .filter(st => isUndergrad ? st.stages.includes('UNDERGRADUATE') : st.stages.includes('SENIOR_SECONDARY'))
                      .map((st) => (
                        <button
                          key={st.id}
                          type="button"
                          onClick={() => {
                            setStream(st.id);
                            if (st.id === 'science_pcm') {
                              setSubjects(['Physics', 'Chemistry', 'Mathematics', 'English']);
                              setExam('JEE');
                            } else if (st.id === 'science_pcb') {
                              setSubjects(['Physics', 'Chemistry', 'Biology', 'English']);
                              setExam('NEET');
                            } else if (st.id === 'commerce') {
                              setSubjects(['Accountancy', 'Business Studies', 'Economics', 'English']);
                              setExam('BOARDS');
                            } else if (st.id === 'humanities') {
                              setSubjects(['History', 'Political Science', 'Economics', 'English']);
                              setExam('BOARDS');
                            }
                          }}
                          className={`p-3 rounded-xl border text-left transition ${
                            stream === st.id
                              ? 'border-[var(--accent-royal)] bg-[var(--accent-baby)]/20 font-semibold text-[var(--accent-royal)]'
                              : 'border-[var(--border)] hover:bg-[var(--bg-secondary)] text-[var(--text-primary)]'
                          }`}
                        >
                          <div className="text-xs font-semibold">{st.name}</div>
                        </button>
                      ))}
                  </div>
                </div>
              )}

              <div className="space-y-2 pt-2">
                <label className="text-xs font-semibold uppercase text-[var(--text-secondary)]">
                  Select Active Subjects ({subjects.length} selected)
                </label>
                <div className="flex flex-wrap gap-2">
                  {config.subjects.map((sub) => {
                    const isSelected = subjects.includes(sub.name);
                    return (
                      <button
                        key={sub.id}
                        type="button"
                        onClick={() => toggleSubject(sub.name)}
                        className={`px-3 py-1.5 rounded-full text-xs font-medium border transition ${
                          isSelected
                            ? 'border-[var(--accent-royal)] bg-[var(--accent-royal)] text-white'
                            : 'border-[var(--border)] bg-[var(--bg-secondary)] hover:bg-[var(--border)] text-[var(--text-primary)]'
                        }`}
                      >
                        {isSelected && <Check className="w-3 h-3 inline mr-1" />}
                        {sub.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* STEP 4: Goals & Exam Track */}
          {step === 4 && (
            <div className="space-y-4">
              <p className="text-sm text-[var(--text-secondary)]">
                What exam or learning milestone are you preparing for?
              </p>
              <div className="space-y-2">
                {config.exam_tracks
                  .filter(ex => {
                    if (isUndergrad) return ex.id === 'UG_SEMESTER' || ex.id === 'FOUNDATION';
                    if (isSeniorSecondary) return ex.id === 'JEE' || ex.id === 'NEET' || ex.id === 'BOARDS' || ex.id === 'FOUNDATION';
                    return ex.id === 'BOARDS' || ex.id === 'SCHOOL_EXAMS' || ex.id === 'FOUNDATION';
                  })
                  .map((ex) => (
                    <button
                      key={ex.id}
                      type="button"
                      onClick={() => setExam(ex.id)}
                      className={`w-full p-3 rounded-xl border text-left transition flex items-center justify-between ${
                        exam === ex.id
                          ? 'border-[var(--accent-royal)] bg-[var(--accent-baby)]/20 font-semibold text-[var(--accent-royal)]'
                          : 'border-[var(--border)] hover:bg-[var(--bg-secondary)] text-[var(--text-primary)]'
                      }`}
                    >
                      <div>
                        <div className="text-sm font-semibold">{ex.name}</div>
                        <div className="text-xs text-[var(--text-secondary)]">{ex.description}</div>
                      </div>
                      {exam === ex.id && <Check className="w-4 h-4 text-[var(--accent-royal)] shrink-0" />}
                    </button>
                  ))}
              </div>

              <div className="pt-2">
                <label className="text-xs font-semibold uppercase text-[var(--text-secondary)] block mb-1">
                  Target Exam / Completion Year
                </label>
                <div className="flex gap-2">
                  {[0, 1, 2, 3].map((offset) => {
                    const yr = new Date().getFullYear() + offset;
                    return (
                      <button
                        key={yr}
                        type="button"
                        onClick={() => setTargetYear(yr)}
                        className={`flex-1 py-2 rounded-xl text-xs font-semibold border transition ${
                          targetYear === yr
                            ? 'border-[var(--accent-royal)] bg-[var(--accent-royal)] text-white'
                            : 'border-[var(--border)] bg-[var(--bg-secondary)] text-[var(--text-primary)] hover:bg-[var(--border)]'
                        }`}
                      >
                        {yr}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* STEP 5: Language & Time Availability */}
          {step === 5 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase text-[var(--text-secondary)]">
                  Preferred Explanation Language
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {config.languages.map((lng) => (
                    <button
                      key={lng.id}
                      type="button"
                      onClick={() => setLanguage(lng.id)}
                      className={`p-2.5 rounded-xl border text-left transition ${
                        language === lng.id
                          ? 'border-[var(--accent-royal)] bg-[var(--accent-baby)]/20 font-semibold text-[var(--accent-royal)]'
                          : 'border-[var(--border)] hover:bg-[var(--bg-secondary)] text-[var(--text-primary)]'
                      }`}
                    >
                      <div className="text-xs font-semibold">{lng.name}</div>
                      <div className="text-[10px] text-[var(--text-secondary)]">{lng.native_label}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2 pt-2">
                <label className="text-xs font-semibold uppercase text-[var(--text-secondary)]">
                  Preferred AI Session Duration
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {config.session_durations_minutes.map((mins) => (
                    <button
                      key={mins}
                      type="button"
                      onClick={() => setSessionMinutes(mins)}
                      className={`py-3 rounded-xl border text-center transition ${
                        sessionMinutes === mins
                          ? 'border-[var(--accent-royal)] bg-[var(--accent-royal)] text-white font-bold'
                          : 'border-[var(--border)] bg-[var(--bg-secondary)] text-[var(--text-primary)] hover:bg-[var(--border)]'
                      }`}
                    >
                      <span className="text-sm">{mins}m</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer Navigation */}
        <div className="border-t border-[var(--border)] px-6 py-4 flex items-center justify-between bg-[var(--bg-secondary)]/50">
          {step > 1 ? (
            <button
              type="button"
              onClick={handleBack}
              disabled={submitting}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold border border-[var(--border)] hover:bg-[var(--bg-secondary)] transition text-[var(--text-primary)]"
            >
              <ArrowLeft className="w-4 h-4" /> Back
            </button>
          ) : (
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="text-xs text-[var(--text-secondary)] hover:underline"
            >
              Set up later
            </button>
          )}

          <button
            type="button"
            onClick={handleNext}
            disabled={submitting}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold bg-[var(--accent-royal)] text-white shadow hover:opacity-90 transition disabled:opacity-50"
          >
            {submitting ? (
              'Saving...'
            ) : step === totalSteps ? (
              <>Finish &amp; Start Learning <Sparkles className="w-4 h-4" /></>
            ) : (
              <>Continue <ArrowRight className="w-4 h-4" /></>
            )}
          </button>
        </div>
      </motion.div>
    </div>
  );
};
export default OnboardingModal;
