import React from 'react';
import { Sparkles, Target, ArrowUpRight } from 'lucide-react';
import type { ExamPrediction } from '../../lib/api';

interface ExamPredictorCardProps {
  predictions: ExamPrediction[];
  examType?: string;
  chapterSummary?: string;
  onGenerateMCQs?: (message: string) => void;
}

const LIKELIHOOD_STYLES: Record<string, { bg: string; text: string; dot: string }> = {
  High: { bg: 'bg-emerald-100', text: 'text-emerald-700', dot: 'bg-emerald-500' },
  Medium: { bg: 'bg-amber-100', text: 'text-amber-700', dot: 'bg-amber-500' },
  Low: { bg: 'bg-gray-100', text: 'text-gray-600', dot: 'bg-gray-400' },
};

const TYPE_STYLES: Record<string, { bg: string; text: string }> = {
  MCQ: { bg: 'bg-blue-100', text: 'text-blue-700' },
  'Short Answer': { bg: 'bg-purple-100', text: 'text-purple-700' },
  'Long Answer': { bg: 'bg-rose-100', text: 'text-rose-700' },
};

function kebabToReadable(slug: string): string {
  return slug
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

const ExamPredictorCard: React.FC<ExamPredictorCardProps> = ({
  predictions,
  examType,
  chapterSummary,
  onGenerateMCQs,
}) => {
  const highLikelihoodTopics = predictions
    .filter((p) => p.likelihood === 'High')
    .map((p) => kebabToReadable(p.topic));

  const handleGenerateMCQs = () => {
    if (onGenerateMCQs && highLikelihoodTopics.length > 0) {
      onGenerateMCQs(
        `Generate MCQs focused on ${highLikelihoodTopics.join(', ')}`
      );
    }
  };

  if (!predictions || predictions.length === 0) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-700">
        No predictions could be generated. Try uploading more content.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2 mb-1">
        <div className="w-7 h-7 rounded-lg bg-[var(--accent-green)] flex items-center justify-center">
          <Target className="w-3.5 h-3.5 text-white" />
        </div>
        <div>
          <h3 className="font-bold text-[var(--text-primary)] text-sm">
            Exam Question Predictions
            {examType && (
              <span className="ml-2 px-2 py-0.5 text-xs font-semibold bg-indigo-100 text-indigo-700 rounded-md">
                {examType}
              </span>
            )}
          </h3>
          {chapterSummary && (
            <p className="text-xs text-[var(--text-muted)] mt-0.5">{chapterSummary}</p>
          )}
        </div>
      </div>

      {/* Prediction Cards */}
      <div className="space-y-2.5">
        {predictions.map((prediction, idx) => {
          const likelihood = LIKELIHOOD_STYLES[prediction.likelihood] || LIKELIHOOD_STYLES.Low;
          const typeStyle = TYPE_STYLES[prediction.questionType] || TYPE_STYLES.MCQ;

          return (
            <div
              key={prediction.id || idx}
              className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl px-4 py-3 hover:border-[var(--accent-green)]/30 transition-colors"
            >
              {/* Question */}
              <p className="font-semibold text-sm text-[var(--text-primary)] leading-snug mb-2.5">
                {prediction.question}
              </p>

              {/* Badges Row */}
              <div className="flex items-center flex-wrap gap-2">
                {/* Topic */}
                <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded-md text-xs font-medium">
                  {kebabToReadable(prediction.topic)}
                </span>

                {/* Likelihood */}
                <span className={`flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold ${likelihood.bg} ${likelihood.text}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${likelihood.dot}`} />
                  {prediction.likelihood}
                </span>

                {/* Question Type */}
                <span className={`px-2 py-0.5 rounded-md text-xs font-semibold ${typeStyle.bg} ${typeStyle.text}`}>
                  {prediction.questionType}
                </span>
              </div>

              {/* Reason */}
              {prediction.reason && (
                <p className="text-xs text-[var(--text-muted)] mt-2 italic">
                  {prediction.reason}
                </p>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="pt-1 space-y-2">
        <p className="text-xs italic text-[var(--text-muted)]">
          Based on CBSE/JEE/NEET exam patterns
        </p>

        {highLikelihoodTopics.length > 0 && onGenerateMCQs && (
          <button
            onClick={handleGenerateMCQs}
            className="flex items-center gap-1.5 px-4 py-2 bg-[var(--accent-green)] text-white rounded-xl text-sm font-semibold hover:bg-[var(--accent-green-hover)] transition-colors shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Generate MCQs from these topics
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
};

export default ExamPredictorCard;
