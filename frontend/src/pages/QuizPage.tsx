import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Loader2, CheckCircle2, AlertTriangle, Edit2, Trash2, ArrowUp, ArrowDown,
  RefreshCw, Play, Save, Check, X, Clock, HelpCircle, ArrowLeft, ArrowRight, Users
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { ILLUSTRATIONS, GENIE } from '../lib/assets';
import {
  getQuiz, updateQuizStatus, editQuestion, deleteQuestion, reorderQuestions,
  regenerateQuestion, startAttempt, submitAttempt, getAttempt
} from '../lib/quizApi';

const QuizPage: React.FC = () => {
  const { quizId } = useParams<{ quizId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const attemptIdParam = searchParams.get('attempt');
  const navigate = useNavigate();

  const [quiz, setQuiz] = useState<any>(null);
  const [questions, setQuestions] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Editor states
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<any>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  // Take states
  const [attempt, setAttempt] = useState<any>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [timeLeft, setTimeLeft] = useState<number | null>(null);
  
  // Results
  const [results, setResults] = useState<any>(null);

  useEffect(() => {
    if (!quizId) return;
    loadQuiz();
  }, [quizId]);

  useEffect(() => {
    if (attemptIdParam) {
      loadAttempt(attemptIdParam);
    }
  }, [attemptIdParam]);

  useEffect(() => {
    let timer: any;
    if (attempt && !results && timeLeft !== null && timeLeft > 0) {
      timer = setInterval(() => {
        setTimeLeft(prev => prev !== null && prev > 0 ? prev - 1 : 0);
      }, 1000);
    } else if (timeLeft === 0 && !results && !submitting) {
      handleSubmitAttempt();
    }
    return () => clearInterval(timer);
  }, [timeLeft, attempt, results]);

  const loadQuiz = async () => {
    try {
      setLoading(true);
      const data = await getQuiz(quizId!);
      setQuiz(data.quiz);
      setQuestions(data.questions);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load quiz');
    } finally {
      setLoading(false);
    }
  };

  const loadAttempt = async (id: string) => {
    try {
      const data = await getAttempt(id);
      setAttempt(data);
      if (data.status === 'completed') {
        setResults(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handlePublish = async () => {
    try {
      setSavingId('publish');
      await updateQuizStatus(quizId!, { status: 'published' });
      setQuiz({ ...quiz, status: 'published' });
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to publish quiz');
    } finally {
      setSavingId(null);
    }
  };

  const startEdit = (q: any) => {
    setEditingQuestionId(q.id);
    setEditForm({
      question_text: q.question_text,
      options: [...(q.options || [])],
      correct_answer: Array.isArray(q.correct_answer) ? q.correct_answer[0] : q.correct_answer,
      explanation: q.explanation || '',
      difficulty: q.difficulty || 'medium',
    });
  };

  const saveEdit = async () => {
    if (!editForm.question_text || !editForm.correct_answer || editForm.options.some((o: string) => !o)) {
      alert("Please fill all fields and options.");
      return;
    }
    if (!editForm.options.includes(editForm.correct_answer)) {
      alert("Correct answer must be one of the options.");
      return;
    }
    try {
      setSavingId(editingQuestionId);
      await editQuestion(editingQuestionId!, {
        ...editForm,
        correct_answer: [editForm.correct_answer],
      });
      setQuestions(prev => prev.map(q => q.id === editingQuestionId ? { ...q, ...editForm, correct_answer: [editForm.correct_answer] } : q));
      setEditingQuestionId(null);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to save question');
    } finally {
      setSavingId(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this question?')) return;
    try {
      setSavingId(id);
      await deleteQuestion(id);
      setQuestions(prev => prev.filter(q => q.id !== id));
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete question');
    } finally {
      setSavingId(null);
    }
  };

  const handleRegenerate = async (id: string) => {
    try {
      setSavingId(id);
      await regenerateQuestion(id);
      await loadQuiz(); // reload to get the new question data easily
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to regenerate question');
    } finally {
      setSavingId(null);
    }
  };

  const handleReorder = async (index: number, direction: 'up' | 'down') => {
    const newQuestions = [...questions];
    if (direction === 'up' && index > 0) {
      [newQuestions[index - 1], newQuestions[index]] = [newQuestions[index], newQuestions[index - 1]];
    } else if (direction === 'down' && index < newQuestions.length - 1) {
      [newQuestions[index + 1], newQuestions[index]] = [newQuestions[index], newQuestions[index + 1]];
    } else {
      return;
    }
    setQuestions(newQuestions);
    try {
      await reorderQuestions(quizId!, newQuestions.map(q => q.id));
    } catch (err) {
      alert('Failed to reorder questions. Reverting.');
      loadQuiz();
    }
  };

  const handleStartAttempt = async () => {
    try {
      setSubmitting(true);
      const data = await startAttempt(quizId!);
      setAttempt(data);
      setSearchParams({ attempt: data.id });
      if (quiz.config?.timer_seconds) {
        setTimeLeft(quiz.config.timer_seconds);
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to start quiz');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitAttempt = async () => {
    try {
      setSubmitting(true);
      const payload = {
        attempt_id: attempt.id,
        answers: Object.entries(answers).map(([question_id, answer]) => ({
          question_id,
          answer
        }))
      };
      const res = await submitAttempt(payload);
      setResults(res);
      // Reload attempt to get full stats if needed
      loadAttempt(attempt.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit quiz');
    } finally {
      setSubmitting(false);
    }
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <AppLayout title="Quiz">
        <div className="flex h-[80vh] items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-[var(--accent-green)]" />
        </div>
      </AppLayout>
    );
  }

  if (error || !quiz) {
    return (
      <AppLayout title="Quiz">
        <div className="mx-auto mt-10 max-w-2xl rounded-xl border border-red-200 bg-red-50 p-6">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-6 w-6 text-red-600" />
            <h2 className="text-lg font-semibold text-red-900">Error Loading Quiz</h2>
          </div>
          <p className="mt-2 text-red-800">{error || 'Quiz not found'}</p>
        </div>
      </AppLayout>
    );
  }

  // Teacher Review/Edit View
  if (quiz.status === 'draft') {
    return (
      <AppLayout title="Edit Quiz">
        <SEO title="Edit Quiz | LearnByGenie" description="Review and edit your generated quiz." />
        <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="mb-6 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
            <div>
              <h1 className="font-display text-2xl font-bold text-[var(--text-primary)]">
                Review Quiz
              </h1>
              <p className="mt-1 text-sm text-[var(--text-secondary)]">
                Make any necessary adjustments before publishing.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handlePublish}
                disabled={savingId === 'publish'}
                className="flex items-center gap-2 rounded-xl bg-[var(--accent-green)] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)] disabled:opacity-50"
              >
                {savingId === 'publish' ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                Publish Quiz
              </button>
              <button
                onClick={() => navigate(`/quiz/${quizId}/live`)}
                className="flex items-center gap-2 rounded-xl bg-[var(--accent-royal)] px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-[var(--accent-royal)]/25 transition-colors hover:bg-[var(--accent-green-deep)]"
              >
                <Users className="h-4 w-4" />
                Start Live
              </button>
            </div>
          </div>

          <div className="space-y-6">
            {questions.map((q, index) => (
              <div key={q.id} className="relative rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-sm">
                
                {/* Reorder controls */}
                <div className="absolute left-[-16px] top-1/2 flex -translate-y-1/2 flex-col gap-1">
                  <button onClick={() => handleReorder(index, 'up')} disabled={index === 0} className="rounded-full border border-[var(--border)] bg-[var(--bg-card)] p-1 text-[var(--text-muted)] hover:text-[var(--accent-green)] disabled:opacity-30">
                    <ArrowUp className="h-3 w-3" />
                  </button>
                  <button onClick={() => handleReorder(index, 'down')} disabled={index === questions.length - 1} className="rounded-full border border-[var(--border)] bg-[var(--bg-card)] p-1 text-[var(--text-muted)] hover:text-[var(--accent-green)] disabled:opacity-30">
                    <ArrowDown className="h-3 w-3" />
                  </button>
                </div>

                {editingQuestionId === q.id ? (
                  <div className="space-y-4">
                    <div>
                      <label className="text-xs font-semibold text-[var(--text-secondary)]">Question Text</label>
                      <textarea
                        value={editForm.question_text}
                        onChange={(e) => setEditForm({ ...editForm, question_text: e.target.value })}
                        className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm focus:border-[var(--accent-green)] focus:outline-none"
                        rows={2}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-semibold text-[var(--text-secondary)]">Options</label>
                      {editForm.options.map((opt: string, i: number) => (
                        <div key={i} className="flex items-center gap-2">
                          <input
                            type="radio"
                            name={`correct-${q.id}`}
                            checked={editForm.correct_answer === opt && opt !== ''}
                            onChange={() => setEditForm({ ...editForm, correct_answer: opt })}
                            className="h-4 w-4 text-[var(--accent-green)] focus:ring-[var(--accent-green)]"
                          />
                          <input
                            type="text"
                            value={opt}
                            onChange={(e) => {
                              const newOpts = [...editForm.options];
                              newOpts[i] = e.target.value;
                              setEditForm({ ...editForm, options: newOpts, correct_answer: editForm.correct_answer === opt ? e.target.value : editForm.correct_answer });
                            }}
                            className="flex-1 rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2 text-sm focus:border-[var(--accent-green)] focus:outline-none"
                          />
                        </div>
                      ))}
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-[var(--text-secondary)]">Explanation</label>
                      <textarea
                        value={editForm.explanation}
                        onChange={(e) => setEditForm({ ...editForm, explanation: e.target.value })}
                        className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm focus:border-[var(--accent-green)] focus:outline-none"
                        rows={2}
                      />
                    </div>
                    <div className="flex items-center justify-end gap-2 pt-2">
                      <button onClick={() => setEditingQuestionId(null)} className="rounded-lg px-4 py-2 text-sm font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]">Cancel</button>
                      <button onClick={saveEdit} disabled={savingId === q.id} className="flex items-center gap-2 rounded-lg bg-[var(--accent-green)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--accent-green-hover)]">
                        {savingId === q.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-start justify-between gap-4">
                      <h3 className="font-semibold text-[var(--text-primary)]">
                        <span className="mr-2 text-[var(--text-muted)]">{index + 1}.</span>
                        {q.question_text}
                      </h3>
                      <div className="flex items-center gap-1 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100 sm:opacity-100">
                        <button onClick={() => startEdit(q)} className="rounded-lg p-1.5 text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"><Edit2 className="h-4 w-4" /></button>
                        <button onClick={() => handleRegenerate(q.id)} disabled={savingId === q.id} className="rounded-lg p-1.5 text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--accent-green)]">
                          {savingId === q.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                        </button>
                        <button onClick={() => handleDelete(q.id)} disabled={savingId === q.id} className="rounded-lg p-1.5 text-[var(--text-secondary)] hover:bg-red-50 hover:text-red-700">
                          {savingId === q.id ? <Loader2 className="h-4 w-4 animate-spin text-red-700" /> : <Trash2 className="h-4 w-4 text-red-700" />}
                        </button>
                      </div>
                    </div>
                    <div className="mt-4 grid gap-2 sm:grid-cols-2">
                      {q.options?.map((opt: string, i: number) => {
                        const isCorrect = Array.isArray(q.correct_answer) ? q.correct_answer.includes(opt) : q.correct_answer === opt;
                        return (
                          <div key={i} className={`rounded-lg border px-3 py-2 text-sm ${isCorrect ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)] font-medium text-[var(--accent-green-text)]' : 'border-[var(--border)] bg-[var(--bg-secondary)] text-[var(--text-secondary)]'}`}>
                            {opt}
                            {isCorrect && <Check className="float-right mt-0.5 h-4 w-4" />}
                          </div>
                        );
                      })}
                    </div>
                    {q.explanation && (
                      <p className="mt-4 rounded-lg bg-[var(--bg-secondary)] p-3 text-xs italic text-[var(--text-secondary)]">
                        <strong className="font-semibold text-[var(--text-primary)]">Explanation: </strong>
                        {q.explanation}
                      </p>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      </AppLayout>
    );
  }

  // Student Take View
  if (quiz.status === 'published' && !attempt && !results) {
    return (
      <AppLayout title="Quiz">
        <SEO title="Take Quiz | LearnByGenie" description="Test your knowledge." />
        <div className="mx-auto mt-12 max-w-lg text-center">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-[var(--accent-green-light)]">
            <HelpCircle className="h-10 w-10 text-[var(--accent-green-text)]" />
          </div>
          <h1 className="font-display text-3xl font-bold text-[var(--text-primary)]">Ready to begin?</h1>
          <p className="mt-3 text-[var(--text-secondary)]">
            This quiz contains {questions.length} questions.
            {quiz.config?.timer_seconds && ` You have ${Math.floor(quiz.config.timer_seconds / 60)} minutes to complete it.`}
          </p>
          <div className="mx-auto mt-8 flex flex-wrap items-center justify-center gap-4">
            <button
              onClick={handleStartAttempt}
              disabled={submitting}
              className="flex items-center gap-2 rounded-xl bg-[var(--accent-green)] px-8 py-3.5 font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)]"
            >
              {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <Play className="h-5 w-5" />}
              Take Quiz (Self-Paced)
            </button>
            <button
              onClick={() => navigate(`/quiz/${quizId}/live`)}
              className="flex items-center gap-2 rounded-xl bg-[var(--accent-royal)] px-8 py-3.5 font-semibold text-white shadow-lg shadow-[var(--accent-royal)]/25 transition-colors hover:bg-[var(--accent-green-deep)]"
            >
              <Users className="h-5 w-5" />
              Start Live Classroom
            </button>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (attempt && !results) {
    const q = questions[currentQuestionIndex];
    return (
      <AppLayout title="Taking Quiz">
        <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
          
          <div className="mb-8 flex items-center justify-between rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-sm">
            <div className="flex flex-col">
              <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">Progress</span>
              <span className="font-medium text-[var(--text-primary)]">Question {currentQuestionIndex + 1} of {questions.length}</span>
            </div>
            
            {timeLeft !== null && (
              <div className={`flex items-center gap-2 rounded-lg px-3 py-1.5 font-bold tabular-nums ${timeLeft < 60 ? 'animate-pulse bg-red-100 text-red-700' : 'bg-[var(--bg-secondary)] text-[var(--text-primary)]'}`}>
                <Clock className="h-4 w-4" />
                {formatTime(timeLeft)}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-sm md:p-8">
            <h2 className="mb-6 font-display text-xl font-medium text-[var(--text-primary)]">{q.question_text}</h2>
            
            <div className="grid gap-3 sm:grid-cols-1">
              {q.options?.map((opt: string, i: number) => {
                const isSelected = answers[q.id] === opt;
                return (
                  <button
                    key={i}
                    onClick={() => setAnswers(prev => ({ ...prev, [q.id]: opt }))}
                    className={`flex w-full items-center justify-between rounded-xl border p-4 text-left transition-colors ${isSelected ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)] ring-1 ring-[var(--accent-green)]' : 'border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)]'}`}
                  >
                    <span className={`text-sm font-medium ${isSelected ? 'text-[var(--accent-green-text)]' : 'text-[var(--text-primary)]'}`}>{opt}</span>
                    <div className={`flex h-5 w-5 items-center justify-center rounded-full border ${isSelected ? 'border-[var(--accent-green)] bg-[var(--accent-green)]' : 'border-[var(--border-strong)]'}`}>
                      {isSelected && <div className="h-2 w-2 rounded-full bg-white" />}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="mt-8 flex items-center justify-between">
            <button
              onClick={() => setCurrentQuestionIndex(prev => prev - 1)}
              disabled={currentQuestionIndex === 0}
              className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-5 py-2.5 text-sm font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)] disabled:opacity-50"
            >
              <ArrowLeft className="h-4 w-4" /> Previous
            </button>

            {currentQuestionIndex === questions.length - 1 ? (
              <button
                onClick={handleSubmitAttempt}
                disabled={submitting}
                className="flex items-center gap-2 rounded-xl bg-[var(--accent-green)] px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)] disabled:opacity-50"
              >
                {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />} Submit Quiz
              </button>
            ) : (
              <button
                onClick={() => setCurrentQuestionIndex(prev => prev + 1)}
                className="flex items-center gap-2 rounded-xl bg-[var(--text-primary)] px-6 py-2.5 text-sm font-semibold text-[var(--bg-primary)] transition-colors hover:opacity-90"
              >
                Next <ArrowRight className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </AppLayout>
    );
  }

  // Results View
  if (results) {
    const scorePct = typeof results.score === 'number'
      ? Math.round(results.score)
      : typeof results.score?.correct_count === 'number'
      ? Math.round((results.score.correct_count / (results.score.total_questions || 1)) * 100)
      : Math.round(((results.correct_count ?? 0) / (results.total_questions || 1)) * 100);

    const correctCount = results.correct_count ?? results.score?.correct_count ?? 0;
    const totalQ = results.total_questions ?? results.score?.total_questions ?? questions.length;
    const perQuestionMap = new Map<string, any>((results.per_question_results || []).map((r: any) => [r.question_id, r]));
    
    return (
      <AppLayout title="Quiz Results">
        <SEO title="Quiz Results | LearnByGenie" description="Review your quiz performance." />
        <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 lg:px-8">
          
          <div className="mb-10 flex flex-col items-center rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-8 text-center shadow-sm">
            <div className="relative mb-6">
              {scorePct >= 80 && (
                <motion.img
                  src={GENIE.celebrating}
                  alt="Celebrating"
                  className="h-24 w-24 object-contain"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1, transition: { type: "spring", stiffness: 300, damping: 20 } }}
                  onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                />
              )}
              <div className={`mb-4 flex h-24 w-24 items-center justify-center rounded-full border-4 ${scorePct >= 80 ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)]' : scorePct >= 50 ? 'border-amber-400 bg-amber-50' : 'border-red-400 bg-red-50'}`}>
                <span className={`text-3xl font-bold ${scorePct >= 80 ? 'text-[var(--accent-green-text)]' : scorePct >= 50 ? 'text-amber-700' : 'text-red-700'}`}>{scorePct}%</span>
              </div>
            </div>
            <img
              src={ILLUSTRATIONS.quizComplete}
              alt=""
              aria-hidden="true"
              className="mb-4 h-16 w-16 object-contain"
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
            />
            <h1 className="font-display text-2xl font-bold text-[var(--text-primary)]">
              {scorePct >= 80 ? 'Excellent work!' : scorePct >= 50 ? 'Good effort!' : 'Keep practicing!'}
            </h1>
            <p className="mt-2 text-[var(--text-secondary)]">
              You scored {correctCount} out of {totalQ} questions correctly.
            </p>
          </div>

          <div className="space-y-6">
            <h2 className="font-display text-xl font-bold text-[var(--text-primary)]">Question Review</h2>
            {questions.map((q, index) => {
              const qRes: any = perQuestionMap.get(q.id);
              const userAnswer = qRes ? qRes.given_answer : results.answers?.[q.id];
              const isCorrect = qRes ? qRes.is_correct : (Array.isArray(q.correct_answer) ? q.correct_answer.includes(userAnswer) : q.correct_answer === userAnswer);

              return (
                <div key={q.id} className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-sm">
                  <div className="mb-4 flex items-start justify-between gap-4">
                    <h3 className="font-medium text-[var(--text-primary)]">
                      <span className="mr-2 text-[var(--text-muted)]">{index + 1}.</span>
                      {q.question_text}
                    </h3>
                    {isCorrect ? (
                      <span className="flex items-center gap-1 rounded-full bg-[var(--accent-green-light)] px-2.5 py-1 text-xs font-semibold text-[var(--accent-green-text)]">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Correct
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-800">
                        <X className="h-3.5 w-3.5" /> Incorrect
                      </span>
                    )}
                  </div>

                  <div className="grid gap-2 sm:grid-cols-2">
                    {q.options?.map((opt: string, i: number) => {
                      const isCorrectAnswer = Array.isArray(q.correct_answer) ? q.correct_answer.includes(opt) : q.correct_answer === opt;
                      const isUserAnswer = userAnswer === opt;

                      let optClass = 'border-[var(--border)] bg-[var(--bg-secondary)] text-[var(--text-secondary)] opacity-70';
                      if (isCorrectAnswer) {
                        optClass = 'border-[var(--accent-green)] bg-[var(--accent-green-light)] font-medium text-[var(--accent-green-text)]';
                      } else if (isUserAnswer) {
                        optClass = 'border-red-200 bg-red-50 font-medium text-red-800';
                      }

                      return (
                        <div key={i} className={`flex items-center justify-between rounded-lg border px-3 py-2.5 text-sm ${optClass}`}>
                          {opt}
                          {isCorrectAnswer && <Check className="h-4 w-4" />}
                          {!isCorrectAnswer && isUserAnswer && <X className="h-4 w-4" />}
                        </div>
                      );
                    })}
                  </div>

                  {q.explanation && (
                    <div className="mt-5 rounded-lg bg-[var(--bg-secondary)] p-4 text-sm">
                      <strong className="mb-1 block font-semibold text-[var(--text-primary)]">Explanation</strong>
                      <span className="text-[var(--text-secondary)]">{q.explanation}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

        </div>
      </AppLayout>
    );
  }

  return null;
};

export default QuizPage;
