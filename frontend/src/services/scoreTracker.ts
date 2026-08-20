import { supabase } from '../lib/supabase';
 
// ─── Types ────────────────────────────────────────────────────────────────────
 
export interface QuizScoreEntry {
  userId: string;
  pdfId: string;
  sessionId: string;
  questionId: string;
  topic: string;
  isCorrect: boolean;
}
 
export interface TopicSummary {
  topic: string;
  totalAttempts: number;
  correctAttempts: number;
  accuracyPct: number;
  isWeak: boolean;     // true if accuracy < 60%
  lastAttemptAt: string;
}
 
export interface WeakTopicAnalysis {
  weakTopics: TopicSummary[];
  strongTopics: TopicSummary[];
  overallAccuracy: number;
  totalQuestionsAttempted: number;
}
 
// ─── Save a single quiz answer ────────────────────────────────────────────────
 
export async function saveQuizScore(entry: QuizScoreEntry): Promise<void> {
  const { error } = await supabase.from("quiz_scores").insert({
    user_id: entry.userId,
    pdf_id: entry.pdfId,
    session_id: entry.sessionId,
    question_id: entry.questionId,
    topic: entry.topic,
    is_correct: entry.isCorrect,
    answered_at: new Date().toISOString(),
  });
 
  if (error) {
    console.error("[TeachGenie] Failed to save quiz score:", error.message);
    // Fail silently — don't break the student's quiz experience
  }
}
 
// ─── Fetch weak topic analysis for a user (across all PDFs) ──────────────────
 
export async function getWeakTopicAnalysis(
  userId: string,
  pdfId?: string          // optional: filter by specific PDF
): Promise<WeakTopicAnalysis> {
  let query = supabase
    .from("quiz_scores")
    .select("topic, is_correct, answered_at")
    .eq("user_id", userId)
    .order("answered_at", { ascending: false });
 
  if (pdfId) {
    query = query.eq("pdf_id", pdfId);
  }
 
  const { data, error } = await query;
 
  if (error || !data) {
    console.error("[TeachGenie] Failed to fetch quiz scores:", error?.message);
    return { weakTopics: [], strongTopics: [], overallAccuracy: 0, totalQuestionsAttempted: 0 };
  }
 
  // Aggregate per topic
  const topicMap: Record<string, { correct: number; total: number; lastAt: string }> = {};
  let totalCorrect = 0;
 
  for (const row of data) {
    if (!topicMap[row.topic]) {
      topicMap[row.topic] = { correct: 0, total: 0, lastAt: row.answered_at };
    }
    topicMap[row.topic].total += 1;
    if (row.is_correct) {
      topicMap[row.topic].correct += 1;
      totalCorrect += 1;
    }
    // Keep the most recent timestamp
    if (row.answered_at > topicMap[row.topic].lastAt) {
      topicMap[row.topic].lastAt = row.answered_at;
    }
  }
 
  const allTopics: TopicSummary[] = Object.entries(topicMap).map(([topic, stats]) => ({
    topic,
    totalAttempts: stats.total,
    correctAttempts: stats.correct,
    accuracyPct: Math.round((stats.correct / stats.total) * 100),
    isWeak: stats.correct / stats.total < 0.6,   // < 60% = weak
    lastAttemptAt: stats.lastAt,
  }));
 
  // Sort by accuracy ascending (weakest first)
  allTopics.sort((a, b) => a.accuracyPct - b.accuracyPct);
 
  return {
    weakTopics:  allTopics.filter((t) => t.isWeak),
    strongTopics: allTopics.filter((t) => !t.isWeak),
    overallAccuracy: data.length > 0
      ? Math.round((totalCorrect / data.length) * 100)
      : 0,
    totalQuestionsAttempted: data.length,
  };
}
 
// ─── Get topic score for a single PDF ────────────────────────────────────────
 
export async function getPdfTopicBreakdown(
  userId: string,
  pdfId: string
): Promise<TopicSummary[]> {
  const { weakTopics, strongTopics } = await getWeakTopicAnalysis(userId, pdfId);
  return [...weakTopics, ...strongTopics];
}
