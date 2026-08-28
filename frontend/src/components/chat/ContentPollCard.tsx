import React, { useState, useEffect, useRef } from 'react';
import { getContentStatus } from '../../lib/api';
import type { ContentCreatorOutput } from '../../lib/api';
import { Loader2, CheckCircle, XCircle, FileText, Video, Play, ExternalLink } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ContentPollCardProps {
  initialData: ContentCreatorOutput;
}

const ContentPollCard: React.FC<ContentPollCardProps> = ({ initialData }) => {
  const [data, setData] = useState<ContentCreatorOutput>(initialData);
  const [attempts, setAttempts] = useState(0);
  const maxAttempts = 60; // 5 minutes max (assuming 5s interval)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    // If it's already complete or failed, don't poll
    if (data.status !== 'processing') return;

    pollIntervalRef.current = setInterval(async () => {
      try {
        const result = await getContentStatus(data.job_id);
        setData(result);
        setAttempts((prev) => prev + 1);

        if (result.status !== 'processing') {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        }
      } catch (err) {
        console.error('Failed to poll status', err);
        // Continue polling unless we hit max attempts
        setAttempts((prev) => prev + 1);
      }
    }, 5000); // 5 seconds interval

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [data.job_id, data.status]);

  // Enforce timeout
  useEffect(() => {
    if (attempts >= maxAttempts && data.status === 'processing') {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      setData((prev) => ({
        ...prev,
        status: 'failed',
        error_message: 'Task took too long and timed out.',
      }));
    }
  }, [attempts, data.status, maxAttempts]);

  const renderIcon = () => {
    if (data.status === 'processing') return <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />;
    if (data.status === 'failed') return <XCircle className="w-6 h-6 text-red-500" />;
    return data.content_type === 'ppt' ? (
      <FileText className="w-6 h-6 text-purple-600" />
    ) : (
      <Video className="w-6 h-6 text-pink-600" />
    );
  };

  return (
    <div className="bg-white border border-[var(--border)] rounded-xl p-4 shadow-sm my-2 w-full max-w-sm">
      <div className="flex items-center gap-3 mb-2">
        {renderIcon()}
        <div>
          <h4 className="font-semibold text-[var(--text-primary)] capitalize">{data.content_type} Generation</h4>
          <p className="text-xs text-[var(--text-muted)] capitalize">{data.status} • Job ID: {data.job_id.slice(0, 8)}</p>
        </div>
      </div>
      
      {data.status === 'processing' && (
        <div className="text-sm text-[var(--text-secondary)] mt-3 animate-pulse">
          Crafting your {data.content_type}... please wait.
        </div>
      )}

      {data.status === 'failed' && (
        <div className="text-sm text-red-600 mt-3">
          Error: {data.error_message || 'Something went wrong.'}
        </div>
      )}

      {data.status === 'complete' && data.content_type !== 'flashcards' && (
        <div className="mt-4">
          <a
            href={data.output_url_or_path || '#'}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 justify-center w-full px-4 py-2 bg-[var(--accent-indigo)] text-white rounded-lg hover:bg-[#2A4A6E] transition-colors text-sm font-medium"
          >
            {data.content_type === 'ppt' ? <FileText className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            View Generated {data.content_type.toUpperCase()}
            <ExternalLink className="w-4 h-4 ml-1 opacity-70" />
          </a>
        </div>
      )}

      {data.status === 'complete' && data.content_type === 'flashcards' && data.flashcards_data && (
        <div className="mt-4 space-y-3">
          <h5 className="font-medium text-sm text-[var(--text-primary)]">Flashcards Ready:</h5>
          <ul className="list-disc pl-4 text-sm text-[var(--text-secondary)] space-y-2">
            {(data.flashcards_data.cards || data.flashcards_data.flashcards || []).map((card: any, idx: number) => (
              <li key={idx}>
                <strong className="text-[var(--accent-indigo)]">Q:</strong> {card.front || card.question}
                <br />
                <em>A:</em> {card.back || card.answer}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default ContentPollCard;
