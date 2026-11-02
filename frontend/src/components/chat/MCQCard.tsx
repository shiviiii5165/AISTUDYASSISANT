import React, { useState } from "react";
import { ListChecks } from "lucide-react";
import { saveQuizScore } from "../../services/scoreTracker";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface MCQQuestion {
  id: string;
  question: string;
  options: { label: "A" | "B" | "C" | "D"; text: string }[];
  correctAnswer: "A" | "B" | "C" | "D";
  explanation: string;
  topic: string;        // e.g. "oxidation-reduction", "displacement-reaction"
  pageNumber?: number;
}

export interface MCQSession {
  sessionId: string;
  pdfId: string;
  questions: MCQQuestion[];
}

interface MCQCardProps {
  session: MCQSession;
  userId: string;
  onSessionComplete: (results: SessionResult) => void;
}

export interface SessionResult {
  sessionId: string;
  totalQuestions: number;
  correctCount: number;
  topicScores: Record<string, { correct: number; total: number }>;
}

// ─── Option styles ─────────────────────────────────────────────────────────────

type OptionState = "default" | "selected" | "correct" | "wrong";

function getOptionStyle(state: OptionState): React.CSSProperties {
  const base: React.CSSProperties = {
    display: "flex",
    alignItems: "flex-start",
    gap: "10px",
    padding: "10px 14px",
    borderRadius: "10px",
    border: "1px solid",
    cursor: "pointer",
    transition: "all 0.15s ease",
    marginBottom: "8px",
    background: "white",
  };
  const variants: Record<OptionState, React.CSSProperties> = {
    default:   { borderColor: "#e5e7eb", background: "white" },
    selected:  { borderColor: "#6366f1", background: "#eef2ff" },
    correct:   { borderColor: "#16a34a", background: "#f0fdf4", cursor: "default" },
    wrong:     { borderColor: "#D97706", background: "#fef2f2", cursor: "default" },
  };
  return { ...base, ...variants[state] };
}

function getLabelStyle(state: OptionState): React.CSSProperties {
  const base: React.CSSProperties = {
    width: "26px",
    height: "26px",
    borderRadius: "50%",
    border: "1.5px solid",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "12px",
    fontWeight: 500,
    flexShrink: 0,
  };
  const variants: Record<OptionState, React.CSSProperties> = {
    default:  { borderColor: "#d1d5db", color: "#6b7280" },
    selected: { borderColor: "#6366f1", color: "#6366f1" },
    correct:  { borderColor: "#16a34a", color: "#15803d", background: "#dcfce7" },
    wrong:    { borderColor: "#D97706", color: "#b91c1c", background: "#fee2e2" },
  };
  return { ...base, ...variants[state] };
}

// ─── Single Question Card ──────────────────────────────────────────────────────

interface SingleQuestionProps {
  question: MCQQuestion;
  questionNumber: number;
  totalQuestions: number;
  onAnswer: (selectedLabel: "A" | "B" | "C" | "D", isCorrect: boolean) => void;
}

function SingleQuestion({
  question,
  questionNumber,
  totalQuestions,
  onAnswer,
}: SingleQuestionProps) {
  const [selected, setSelected] = useState<"A" | "B" | "C" | "D" | null>(null);
  const [revealed, setRevealed] = useState(false);

  const handleSelect = (label: "A" | "B" | "C" | "D") => {
    if (revealed) return;
    setSelected(label);
    setRevealed(true);
    const isCorrect = label === question.correctAnswer;
    onAnswer(label, isCorrect);
  };

  const getOptionState = (label: "A" | "B" | "C" | "D"): OptionState => {
    if (!revealed) return label === selected ? "selected" : "default";
    if (label === question.correctAnswer) return "correct";
    if (label === selected && label !== question.correctAnswer) return "wrong";
    return "default";
  };

  return (
    <div style={{ marginBottom: "20px" }}>
      {/* Question header */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
        <span style={{ fontSize: "11px", color: "#9ca3af", fontWeight: 500 }}>
          Q{questionNumber} of {totalQuestions}
        </span>
        <span style={{
          fontSize: "11px",
          padding: "2px 8px",
          borderRadius: "20px",
          background: "#f3f4f6",
          color: "#6b7280",
          fontWeight: 500,
        }}>
          {question.topic.replace(/-/g, " ")}
        </span>
        {question.pageNumber && (
          <span style={{ fontSize: "11px", color: "#9ca3af" }}>Page {question.pageNumber}</span>
        )}
      </div>

      {/* Question text */}
      <p style={{
        fontSize: "14px",
        color: "#111827",
        fontWeight: 500,
        lineHeight: 1.6,
        marginBottom: "12px",
      }}>
        {question.question}
      </p>

      {/* Options */}
      {question.options.map((opt) => {
        const state = getOptionState(opt.label);
        return (
          <div
            key={opt.label}
            onClick={() => handleSelect(opt.label)}
            style={getOptionStyle(state)}
          >
            <span style={getLabelStyle(state)}>{opt.label}</span>
            <span style={{
              fontSize: "13px",
              color: state === "wrong" ? "#b91c1c" : state === "correct" ? "#15803d" : "#374151",
              lineHeight: 1.5,
            }}>
              {opt.text}
            </span>
            {/* Tick / Cross icon */}
            {revealed && opt.label === question.correctAnswer && (
              <span style={{ marginLeft: "auto", color: "#16a34a", fontSize: "16px" }}>✓</span>
            )}
            {revealed && opt.label === selected && opt.label !== question.correctAnswer && (
              <span style={{ marginLeft: "auto", color: "#D97706", fontSize: "16px" }}>✗</span>
            )}
          </div>
        );
      })}

      {/* Explanation (shown after answer) */}
      {revealed && (
        <div style={{
          marginTop: "10px",
          padding: "10px 14px",
          background: "#f9fafb",
          borderLeft: "3px solid #16a34a",
          borderRadius: "0 8px 8px 0",
        }}>
          <span style={{ fontSize: "11px", fontWeight: 500, color: "#15803d" }}>Explanation</span>
          <p style={{ fontSize: "13px", color: "#374151", marginTop: "4px", lineHeight: 1.5 }}>
            {question.explanation}
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Session Results Banner ────────────────────────────────────────────────────

function SessionResultsBanner({
  results,
  onPracticeWeak,
}: {
  results: SessionResult;
  onPracticeWeak: (topic: string) => void;
}) {
  const pct = Math.round((results.correctCount / results.totalQuestions) * 100);

  // Find weak topics: score < 60%
  const weakTopics = Object.entries(results.topicScores)
    .filter(([, s]) => s.correct / s.total < 0.6)
    .map(([topic, s]) => ({
      topic,
      pct: Math.round((s.correct / s.total) * 100),
    }));

  const scoreColor = pct >= 80 ? "#15803d" : pct >= 60 ? "#b45309" : "#b91c1c";
  const scoreBg   = pct >= 80 ? "#f0fdf4" : pct >= 60 ? "#fffbeb" : "#fef2f2";

  return (
    <div style={{
      marginTop: "16px",
      padding: "16px",
      background: scoreBg,
      borderRadius: "12px",
      border: `1px solid ${scoreColor}30`,
    }}>
      {/* Score headline */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "12px" }}>
        <div style={{
          width: "52px",
          height: "52px",
          borderRadius: "50%",
          background: scoreColor,
          color: "white",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "18px",
          fontWeight: 600,
          flexShrink: 0,
        }}>
          {pct}%
        </div>
        <div>
          <div style={{ fontSize: "15px", fontWeight: 600, color: "#111827" }}>
            {results.correctCount}/{results.totalQuestions} correct
          </div>
          <div style={{ fontSize: "12px", color: "#6b7280", marginTop: "2px" }}>
            {pct >= 80 ? "Great job! Keep it up." : pct >= 60 ? "Good, but a few topics need work." : "Needs more practice."}
          </div>
        </div>
      </div>

      {/* Weak topics */}
      {weakTopics.length > 0 && (
        <div>
          <div style={{ fontSize: "12px", fontWeight: 500, color: "#b91c1c", marginBottom: "8px" }}>
            Weak topics, practice these:
          </div>
          {weakTopics.map(({ topic, pct: tPct }) => (
            <div key={topic} style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "8px 12px",
              background: "white",
              borderRadius: "8px",
              marginBottom: "6px",
              border: "1px solid #fee2e2",
            }}>
              <span style={{ fontSize: "13px", color: "#374151", textTransform: "capitalize" }}>
                {topic.replace(/-/g, " ")}
              </span>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "12px", color: "#b91c1c", fontWeight: 500 }}>{tPct}%</span>
                <button
                  onClick={() => onPracticeWeak(topic)}
                  style={{
                    fontSize: "11px",
                    padding: "3px 10px",
                    borderRadius: "20px",
                    border: "1px solid #D97706",
                    background: "transparent",
                    color: "#b91c1c",
                    cursor: "pointer",
                    fontWeight: 500,
                  }}
                >
                  Practice now
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {weakTopics.length === 0 && (
        <div style={{ fontSize: "13px", color: "#15803d" }}>
          No weak topics detected. You're strong across all areas in this chapter!
        </div>
      )}
    </div>
  );
}

// ─── Main MCQCard Component ────────────────────────────────────────────────────

export default function MCQCard({ session, userId, onSessionComplete }: MCQCardProps) {
  const [answers, setAnswers] = useState<
    Record<string, { selected: string; isCorrect: boolean }>
  >({});
  const [sessionResult, setSessionResult] = useState<SessionResult | null>(null);

  const handleAnswer = async (
    question: MCQQuestion,
    selectedLabel: "A" | "B" | "C" | "D",
    isCorrect: boolean
  ) => {
    const updatedAnswers = {
      ...answers,
      [question.id]: { selected: selectedLabel, isCorrect },
    };
    setAnswers(updatedAnswers);

    // Save score immediately when student answers
    await saveQuizScore({
      userId,
      pdfId: session.pdfId,
      sessionId: session.sessionId,
      questionId: question.id,
      topic: question.topic,
      isCorrect,
    });

    // Check if all questions answered
    const allAnswered = session.questions.every((q) => updatedAnswers[q.id]);
    if (allAnswered) {
      // Build per-topic score summary
      const topicScores: Record<string, { correct: number; total: number }> = {};
      session.questions.forEach((q) => {
        const ans = updatedAnswers[q.id];
        if (!topicScores[q.topic]) topicScores[q.topic] = { correct: 0, total: 0 };
        topicScores[q.topic].total += 1;
        if (ans?.isCorrect) topicScores[q.topic].correct += 1;
      });

      const correctCount = Object.values(updatedAnswers).filter((a) => a.isCorrect).length;
      const result: SessionResult = {
        sessionId: session.sessionId,
        totalQuestions: session.questions.length,
        correctCount,
        topicScores,
      };
      setSessionResult(result);
      onSessionComplete(result);
    }
  };

  const handlePracticeWeak = (topic: string) => {
    // This will trigger a new MCQ generation request in the parent chat
    const message = `I am weak in "${topic.replace(/-/g, " ")}". Please teach me this topic from basic to advanced so I can understand it fully. AFTER teaching, generate 5 MCQs on this topic so I can practice.`;
    // Dispatch to parent via custom event so ChatInterface can pick it up
    window.dispatchEvent(new CustomEvent("learnbygenie:practice-weak-topic", {
      detail: { topic, message },
    }));
  };

  return (
    <div style={{
      background: "white",
      border: "1px solid #e5e7eb",
      borderRadius: "14px",
      padding: "16px",
      marginTop: "8px",
      maxWidth: "640px",
    }}>
      {/* Header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        marginBottom: "16px",
        paddingBottom: "12px",
        borderBottom: "1px solid #f3f4f6",
      }}>
        <div style={{
          width: "28px",
          height: "28px",
          borderRadius: "8px",
          background: "#f0fdf4",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}>
          <ListChecks size={14} color="#166534" aria-hidden="true" />
        </div>
        <div>
          <div style={{ fontSize: "13px", fontWeight: 600, color: "#111827" }}>
            Quick quiz, {session.questions.length} questions
          </div>
          <div style={{ fontSize: "11px", color: "#9ca3af" }}>
            {Object.keys(answers).length} of {session.questions.length} answered
          </div>
        </div>
        {/* Progress bar */}
        <div style={{ marginLeft: "auto", width: "80px" }}>
          <div style={{ background: "#f3f4f6", borderRadius: "4px", height: "4px" }}>
            <div style={{
              width: `${(Object.keys(answers).length / session.questions.length) * 100}%`,
              background: "#16a34a",
              height: "4px",
              borderRadius: "4px",
              transition: "width 0.3s ease",
            }} />
          </div>
        </div>
      </div>

      {/* Questions */}
      {session.questions.map((q, idx) => (
        <SingleQuestion
          key={q.id}
          question={q}
          questionNumber={idx + 1}
          totalQuestions={session.questions.length}
          onAnswer={(label, isCorrect) => handleAnswer(q, label, isCorrect)}
        />
      ))}

      {/* Results banner (shows when all answered) */}
      {sessionResult && (
        <SessionResultsBanner
          results={sessionResult}
          onPracticeWeak={handlePracticeWeak}
        />
      )}
    </div>
  );
}
