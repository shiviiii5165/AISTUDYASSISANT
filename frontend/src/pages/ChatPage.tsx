import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { motion, AnimatePresence } from 'framer-motion';
import remarkGfm from 'remark-gfm';
import { Send, FileText, Loader2, ChevronDown, Sparkles } from 'lucide-react';
import { fetchPdfs, askQuestion, sendMessageV2 } from '../lib/api';
import type { PDFDocument, ChatMessage, ChatSource, PipelineOutput } from '../lib/api';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import VoiceInputButton from '../components/voice/VoiceInputButton';
import { useAuthStore } from '../store/useAuthStore';
import MCQCard from '../components/chat/MCQCard';
import ExamPredictorCard from '../components/chat/ExamPredictorCard';
import UpgradeModal from '../components/billing/UpgradeModal';
import GenieAvatar from '../components/GenieAvatar';
import ContentPollCard from '../components/chat/ContentPollCard';
import HistorySidebar from '../components/HistorySidebar';
import { useSidebarCollapse } from '../hooks/useSidebarCollapse';
import { ILLUSTRATIONS } from '../lib/assets';

interface DisplayMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatSource[];
  isV2?: boolean;
  pipelineOutput?: PipelineOutput;
}

/** Shared markdown styling. Was repeated verbatim five times. */
const PROSE =
  'prose prose-sm max-w-none whitespace-pre-wrap prose-headings:font-semibold prose-headings:text-[var(--text-primary)] ' +
  'prose-p:text-[var(--text-primary)] prose-strong:text-[var(--text-primary)] prose-li:text-[var(--text-primary)] ' +
  'prose-code:text-[var(--accent-green-text)] prose-code:bg-[var(--accent-green-light)] prose-code:px-1 ' +
  'prose-code:py-0.5 prose-code:rounded';

const ANSWER_MODES = [
  'Quick Answer',
  'Full Chapter Crux',
  'Formula Coverage',
  'Exam Shield Notes',
];

const ChatPage: React.FC = () => {
  const { collapsed: historySidebarCollapsed, toggle: toggleHistorySidebar } = useSidebarCollapse('chat-history');
  const [searchParams, setSearchParams] = useSearchParams();
  const initialPdfId = searchParams.get('pdf') || '';
  const initialV2 = searchParams.get('v2') === 'true';
  const { user: currentUser } = useAuthStore();

  const [useV2, setUseV2] = useState(initialV2);

  const [pdfs, setPdfs] = useState<PDFDocument[]>([]);
  const [selectedPdfId, setSelectedPdfId] = useState(initialPdfId);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [selectedMode, setSelectedMode] = useState('Quick Answer');
  const [loading, setLoading] = useState(false);
  const [loadingPdfs, setLoadingPdfs] = useState(true);
  const [pdfsError, setPdfsError] = useState<string | null>(null);
  const [showPdfDropdown, setShowPdfDropdown] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgradeMessage, setUpgradeMessage] = useState('');
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load PDFs list
  useEffect(() => {
    (async () => {
      try {
        const data = await fetchPdfs();
        const readyPdfs = data.filter(p => p.status === 'ready');
        setPdfs(readyPdfs);
        setPdfsError(null);

        // Auto-correct invalid or missing PDF selection
        if (!initialPdfId || initialPdfId === 'undefined' || !readyPdfs.find(p => p.id === initialPdfId)) {
          if (readyPdfs.length > 0) {
            setSelectedPdfId(readyPdfs[0].id);
            setSearchParams(prev => { prev.set('pdf', readyPdfs[0].id); return prev; });
          } else {
            setSelectedPdfId('');
          }
        }
      } catch (err: any) {
        console.error('Error loading PDFs:', err);
        // Surface a clear error instead of silently leaving the composer usable
        // with a stale document selection (which would then fail on send).
        setSelectedPdfId('');
        setPdfsError(
          err?.response?.status === 401
            ? 'Your session has expired. Please sign in again to load your documents.'
            : 'Failed to load documents. Please check your connection and try again.'
        );
      } finally {
        setLoadingPdfs(false);
      }
    })();

    // Load chat history
    (async () => {
      const token = useAuthStore.getState().session?.access_token;
      if (!token) return;
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/chat/`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setChatHistory(data.sessions || []);
        }
      } catch (e) {
        console.error('Failed to load chat history', e);
      }
    })();
  }, [initialPdfId, setSearchParams]);

  const loadChat = async (id: string) => {
    const token = useAuthStore.getState().session?.access_token;
    if (!token) return;
    try {
      setLoading(true);
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/chat/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSessionId(data.session.id);
        if (data.session.pdf_id) {
            setSelectedPdfId(data.session.pdf_id);
        }
        setMessages(data.messages.map((m: any) => ({
            role: m.role,
            content: m.content,
            sources: m.sources,
            isV2: false // For loaded history we treat as v1 plain text unless we store output payload
        })));
      }
    } catch (e) {
      console.error('Failed to load chat', e);
    } finally {
      setLoading(false);
    }
  };

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Focus input on PDF selection
  useEffect(() => {
    if (selectedPdfId) {
      inputRef.current?.focus();
    }
  }, [selectedPdfId]);

  const selectedPdf = pdfs.find(p => p.id === selectedPdfId);

  const handleSend = async (overrideQuestion?: string) => {
    // If overrideQuestion is a string, use it. Otherwise use inputValue.
    const q = typeof overrideQuestion === 'string' ? overrideQuestion.trim() : inputValue.trim();
    if (!q || !selectedPdfId || selectedPdfId === 'undefined' || loading) return;

    const userMessage: DisplayMessage = { role: 'user', content: q };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsVoiceActive(false);
    setLoading(true);

    try {
      // Build chat history for context (only role + content)
      const apiHistory: ChatMessage[] = messages.map(m => ({
        role: m.role,
        content: m.content,
      }));

      if (useV2) {
        const response = await sendMessageV2({
          message: q,
          pdf_id: selectedPdfId || undefined,
          session_id: sessionId || undefined,
          history: apiHistory
        });

        if (response.session_id && !sessionId) {
            setSessionId(response.session_id);
            setChatHistory(prev => [{ id: response.session_id, title: q, created_at: new Date().toISOString() }, ...prev]);
        }
        
        const assistantMessage: DisplayMessage = {
          role: 'assistant',
          content: response.message || '',
          isV2: true,
          pipelineOutput: response
        };
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        const response = await askQuestion({
          pdf_id: selectedPdfId,
          question: q,
          mode: selectedMode,
          session_id: sessionId || undefined,
          history: apiHistory,
        });

        if (response.session_id && !sessionId) {
            setSessionId(response.session_id);
            setChatHistory(prev => [{ id: response.session_id, title: q, created_at: new Date().toISOString() }, ...prev]);
        }
        
        const assistantMessage: DisplayMessage = {
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
        };
        setMessages(prev => [...prev, assistantMessage]);
      }
    } catch (err: any) {
      if (err.response?.status === 403 && err.response?.data?.detail?.error) {
        setUpgradeMessage(err.response.data.detail.message);
        setShowUpgradeModal(true);
        // Remove the user message from UI since it failed
        setMessages(prev => prev.slice(0, -1));
      } else {
        const errorMessage: DisplayMessage = {
          role: 'assistant',
          content: 'Sorry, something went wrong answering that. Please try again.',
        };
        setMessages(prev => [...prev, errorMessage]);
        console.error('Chat error:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSendRef = useRef(handleSend);
  useEffect(() => { handleSendRef.current = handleSend; });
  useEffect(() => {
    const handler = (e: CustomEvent) => {
      const { message } = e.detail;
      handleSendRef.current(message);
    };
    window.addEventListener("teachgenie:practice-weak-topic", handler as EventListener);
    return () => window.removeEventListener("teachgenie:practice-weak-topic", handler as EventListener);
  }, []);

  function renderMessage(msg: DisplayMessage) {
    if (msg.isV2 && msg.pipelineOutput) {
      const out = msg.pipelineOutput;

      if (out.response_type === 'direct_message') {
        return (
          <div className={PROSE}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {msg.content}
            </ReactMarkdown>
          </div>
        );
      }

      if (out.response_type === 'tutor_turn' && out.tutor_data) {
        return (
          <div className="space-y-2">
            <div className={PROSE}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {out.tutor_data.message}
              </ReactMarkdown>
            </div>
            {out.tutor_data.understanding_level && (
              <p className="mt-2 inline-block rounded-full border border-[var(--border)] bg-[var(--bg-secondary)] px-2 py-0.5 text-[11px] font-medium text-[var(--text-secondary)]">
                State: {out.tutor_data.understanding_level.replace('_', ' ')}
              </p>
            )}
          </div>
        );
      }

      if (out.response_type === 'content' && out.content_data) {
        return <ContentPollCard initialData={out.content_data} />;
      }
    }

    // Detect if the response contains an MCQ JSON block (V1 logic)
    const mcqMatch = msg.content.match(/```json\n([\s\S]*?)\n```/);

    if (mcqMatch && currentUser && selectedPdfId) {
      try {
        const parsed = JSON.parse(mcqMatch[1]);

        // Check if this is an exam predictor response
        if (parsed.predictions && Array.isArray(parsed.predictions)) {
          const textBeforeJson = msg.content.split('```json')[0].trim();
          return (
            <div className="space-y-4">
              {textBeforeJson && (
                <div className={PROSE}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {textBeforeJson}
                  </ReactMarkdown>
                </div>
              )}
              <ExamPredictorCard
                predictions={parsed.predictions}
                examType={parsed.examType}
                chapterSummary={parsed.chapterSummary}
                onGenerateMCQs={(message) => handleSend(message)}
              />
            </div>
          );
        }

        // Otherwise it's an MCQ session
        const session = parsed;
        session.pdfId = selectedPdfId;

        const textBeforeJson = msg.content.split('```json')[0].trim();

        return (
          <div className="space-y-4">
            {textBeforeJson && (
              <div className={PROSE}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {textBeforeJson}
                </ReactMarkdown>
              </div>
            )}
            <MCQCard
              session={session}
              userId={currentUser.id}
              onSessionComplete={(results) => {
                console.log("Quiz complete:", results);
              }}
            />
          </div>
        );
      } catch {
        // JSON parsing failed, fall through and render as plain text
      }
    }

    return (
      <div className={PROSE}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {msg.content}
        </ReactMarkdown>
      </div>
    );
  }

  return (
    <AppLayout title="Study Assistant">
      <SEO
        title="AI Chat | TeachGenie"
        description="Chat directly with your documents. Get instant answers, summaries, and personalized learning support."
      />
      <div className="flex h-full w-full">
        <HistorySidebar
          title="Chat Sessions"
          items={chatHistory.map(s => ({ id: s.id, title: s.title, date: s.created_at }))}
          selectedId={sessionId}
          onSelect={loadChat}
          onNew={() => { setSessionId(null); setMessages([]); }}
          collapsed={historySidebarCollapsed}
          onToggle={toggleHistorySidebar}
        />

        <div className="flex flex-1 flex-col overflow-hidden bg-[var(--bg-primary)]">
          {/* Top Bar */}
          <div className="flex shrink-0 items-center justify-between border-b border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 sm:px-6">
            <div className="flex items-center gap-2 md:gap-3">
              <FileText
                className="hidden h-4 w-4 shrink-0 text-[var(--text-secondary)] sm:block"
                aria-hidden="true"
              />
              <span className="hidden text-xs font-medium text-[var(--text-secondary)] sm:block">
                Chatting with
              </span>
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setShowPdfDropdown(!showPdfDropdown)}
                  aria-expanded={showPdfDropdown}
                  aria-haspopup="listbox"
                  className="flex min-w-[140px] items-center gap-2 rounded-lg border border-[var(--border)] px-2.5 py-1.5 text-left text-xs font-semibold transition-colors hover:bg-[var(--bg-hover)] md:min-w-[200px]"
                  disabled={loadingPdfs}
                >
                  {loadingPdfs ? (
                    <span className="text-[var(--text-secondary)]">Loading documents</span>
                  ) : selectedPdf ? (
                    <span className="truncate">{selectedPdf.name}</span>
                  ) : (
                    <span className="text-[var(--text-secondary)]">Select a document</span>
                  )}
                  <ChevronDown
                    className="ml-auto h-3.5 w-3.5 shrink-0 text-[var(--text-muted)]"
                    aria-hidden="true"
                  />
                </button>

                {showPdfDropdown && (
                  <>
                    <div className="fixed inset-0 z-20" onClick={() => setShowPdfDropdown(false)} />
                    <ul
                      role="listbox"
                      aria-label="Your documents"
                      className="absolute left-0 top-full z-30 mt-1 max-h-64 min-w-[280px] overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--bg-card)] py-1 shadow-[var(--shadow-lg)]"
                    >
                      {pdfs.length === 0 ? (
                        <li className="px-4 py-3 text-sm text-[var(--text-secondary)]">
                          No documents ready. Upload one first.
                        </li>
                      ) : (
                        pdfs.map((pdf) => (
                          <li key={pdf.id} role="option" aria-selected={selectedPdfId === pdf.id}>
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedPdfId(pdf.id);
                                setShowPdfDropdown(false);
                                setMessages([]);
                              }}
                              className={`flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors hover:bg-[var(--bg-hover)] ${
                                selectedPdfId === pdf.id
                                  ? 'bg-[var(--accent-green-light)] font-semibold'
                                  : ''
                              }`}
                            >
                              <FileText
                                className="h-4 w-4 shrink-0 text-[var(--text-secondary)]"
                                aria-hidden="true"
                              />
                              <span className="min-w-0 truncate">
                                <span className="block truncate font-medium">{pdf.name}</span>
                                <span className="block text-xs text-[var(--text-secondary)]">
                                  {pdf.subject}, {pdf.page_count || '?'} pages
                                </span>
                              </span>
                            </button>
                          </li>
                        ))
                      )}
                    </ul>
                  </>
                )}
              </div>
            </div>

            <div className="ml-auto flex items-center gap-4">
              <label className="flex cursor-pointer items-center gap-2">
                <span className="text-xs font-semibold text-[var(--text-secondary)]">V2 Pipeline</span>
                <span className="relative inline-flex">
                  <input
                    type="checkbox"
                    className="peer sr-only"
                    checked={useV2}
                    onChange={(e) => {
                      const checked = e.target.checked;
                      setUseV2(checked);
                      setSearchParams(prev => {
                        if (checked) prev.set('v2', 'true');
                        else prev.delete('v2');
                        return prev;
                      });
                    }}
                  />
                  <span
                    aria-hidden="true"
                    className={`block h-6 w-10 rounded-full transition-colors peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-[var(--accent-green-text)] ${
                      useV2 ? 'bg-[var(--accent-green)]' : 'bg-[var(--border-strong)]'
                    }`}
                  />
                  <span
                    aria-hidden="true"
                    className={`absolute left-1 top-1 h-4 w-4 rounded-full bg-white transition-transform ${
                      useV2 ? 'translate-x-4' : ''
                    }`}
                  />
                </span>
              </label>

              {messages.length > 0 && (
                <button
                  type="button"
                  onClick={() => setMessages([])}
                  className="rounded text-xs font-medium text-[var(--text-secondary)] transition-colors hover:text-red-700"
                >
                  Clear chat
                </button>
              )}
            </div>
          </div>

          {/* Main Layout Area */}
          <div className="relative flex flex-1 flex-col overflow-hidden">
            {/* If there are messages, render the scrollable message list */}
            {messages.length > 0 && (
              <div className="flex-1 overflow-y-auto px-4 py-4 md:px-6 md:py-6">
                <div
                  className="mx-auto max-w-3xl space-y-6"
                  aria-live="polite"
                  aria-busy={loading}
                >
                  {messages.map((message, index) => (
                    <div
                      key={index}
                      className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      {message.role === 'assistant' && (
                        <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--accent-baby)] border border-[var(--accent-periwinkle)]/30">
                          <Sparkles
                            className="h-4 w-4 text-[var(--accent-royal)]"
                            aria-hidden="true"
                          />
                          <span className="sr-only">TeachGenie</span>
                        </span>
                      )}
                      <div
                        className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 md:max-w-[75%] md:px-4 md:py-3 ${
                          message.role === 'user'
                            ? 'rounded-br-md bg-[var(--accent-royal)] text-white shadow-md shadow-[var(--accent-royal)]/20'
                            : 'rounded-bl-md border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-primary)] shadow-sm'
                        }`}
                      >
                        {message.role === 'assistant' ? (
                          renderMessage(message)
                        ) : (
                          <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
                        )}

                        {/* Source citations */}
                        {message.sources && message.sources.length > 0 && (
                          <div className="mt-3 border-t border-[var(--border)] pt-3">
                            <h3 className="mb-2 text-xs font-semibold text-[var(--text-secondary)]">
                              Sources
                            </h3>
                            <ul className="space-y-1.5">
                              {message.sources.map((source, i) => (
                                <li
                                  key={i}
                                  className="rounded-lg bg-[var(--bg-secondary)] px-2.5 py-1.5 text-xs text-[var(--text-secondary)]"
                                >
                                  <span className="font-semibold text-[var(--accent-green-text)]">
                                    {source.page === 'Note' ? 'Note' : `Page ${source.page}`}
                                  </span>
                                  <span className="mx-1.5 text-[var(--border-strong)]" aria-hidden="true">
                                    |
                                  </span>
                                  <span>{source.text}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {/* Typing indicator inline */}
                  {loading && (
                    <div className="flex justify-start gap-3">
                      <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--accent-baby)] border border-[var(--accent-periwinkle)]/30">
                        <Sparkles className="h-4 w-4 text-[var(--accent-royal)]" aria-hidden="true" />
                      </span>
                      <div className="rounded-2xl rounded-bl-md border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 shadow-sm">
                        <span className="sr-only">Thinking</span>
                        <span className="flex items-center gap-1.5" aria-hidden="true">
                          <span className="typing-dot h-2 w-2 rounded-full bg-[var(--accent-royal)]" style={{ animationDelay: '0ms' }} />
                          <span className="typing-dot h-2 w-2 rounded-full bg-[var(--accent-periwinkle)]" style={{ animationDelay: '150ms' }} />
                          <span className="typing-dot h-2 w-2 rounded-full bg-[var(--accent-baby)]" style={{ animationDelay: '300ms' }} />
                        </span>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </div>
            )}

            {/* Empty States / Centered Content */}
            {messages.length === 0 && !loading && (
              <AnimatePresence>
                <div className="flex-1 h-full w-full flex flex-col items-center justify-center px-4" key="empty-state">
                  {pdfsError ? (
                    <>
                      <GenieAvatar size="md" />
                      <h2 className="font-display text-xl font-semibold text-[var(--text-primary)] mt-3">
                        We couldn't load your documents
                      </h2>
                      <p className="max-w-md text-sm text-[var(--text-secondary)] mt-1 mb-8 text-center">{pdfsError}</p>
                    </>
                  ) : !selectedPdfId ? (
                    <>
                      <motion.img
                        src={ILLUSTRATIONS.emptyChat}
                        onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                        alt=""
                        aria-hidden="true"
                        className="mx-auto mb-6 h-32 w-32 rounded-xl object-cover shadow-sm"
                        animate={{ y: [0, -10, 0] }}
                        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                      />
                      <h2 className="font-display text-xl font-semibold text-[var(--text-primary)] mt-3">
                        Start a conversation
                      </h2>
                      <p className="max-w-md text-sm text-[var(--text-secondary)] mt-1 mb-8 text-center">
                        Upload a document and ask any question about its content.
                      </p>
                    </>
                  ) : (
                    <div className="flex flex-col items-center gap-6 w-full max-w-2xl">
                      {/* Heading with animation */}
                      <motion.h2
                        layoutId="greeting-title"
                        className="font-display max-w-lg text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-6 text-center tracking-tight"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20, transition: { duration: 0.2, ease: "easeIn" } }}
                      >
                        What do you want to learn today?
                      </motion.h2>

                      {/* Quick-action pills */}
                      <div className="flex flex-wrap gap-2">
                        {ANSWER_MODES.map((mode) => (
                          <button
                            key={mode}
                            type="button"
                            onClick={() => setSelectedMode(mode)}
                            aria-pressed={selectedMode === mode}
                            className={`shrink-0 rounded-full border px-4 py-1.5 text-xs font-semibold shadow-sm transition-all ${
                              selectedMode === mode
                                ? 'border-[var(--accent-blue)] bg-[var(--accent-blue)] text-white'
                                : 'border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:border-[var(--accent-blue)] hover:text-[var(--accent-blue)]'
                            }`}
                          >
                            {mode}
                          </button>
                        ))}
                      </div>

                      {/* Input bar */}
                      <div className="w-full bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl shadow-[var(--shadow-lg)] p-3">
                        <div className="mx-auto flex max-w-3xl items-end gap-2">
                          <div className="relative flex-1">
                            <label htmlFor="chat-input" className="sr-only">
                              Ask a question about your document
                            </label>
                            <textarea
                              id="chat-input"
                              ref={inputRef}
                              value={inputValue}
                              onChange={(e) => setInputValue(e.target.value)}
                              onKeyDown={handleKeyDown}
                              placeholder={
                                isVoiceActive ? 'Listening, speak your question' : 'Ask a question about your document...'
                              }
                              rows={1}
                              disabled={loading}
                              className="max-h-32 w-full resize-none overflow-y-auto rounded-xl border-none bg-transparent px-2 py-3 text-sm leading-relaxed text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-0 disabled:opacity-50"
                              style={{ minHeight: '44px', color: isVoiceActive ? 'var(--accent-blue)' : 'inherit' }}
                              onInput={(e) => {
                                const target = e.target as HTMLTextAreaElement;
                                target.style.height = 'auto';
                                target.style.height = Math.min(target.scrollHeight, 128) + 'px';
                              }}
                            />
                          </div>

                          <VoiceInputButton
                            onResult={(text) => {
                              setInputValue(text);
                              setIsVoiceActive(false);
                            }}
                            onInterim={(text) => {
                              setInputValue(text);
                              setIsVoiceActive(true);
                            }}
                            disabled={loading}
                            className="mb-1"
                          />

                          <button
                            type="button"
                            onClick={() => handleSend()}
                            disabled={!inputValue.trim() || loading}
                            aria-label="Send question"
                            className="flex h-[40px] w-[40px] shrink-0 items-center justify-center rounded-xl bg-[var(--text-primary)] text-white transition-colors hover:bg-black active:translate-y-px disabled:cursor-not-allowed disabled:opacity-40 mb-1 mr-1"
                          >
                            {loading ? (
                              <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
                            ) : (
                              <Send className="h-4 w-4" aria-hidden="true" />
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </AnimatePresence>
            )}

            {/* Composer */}
            {selectedPdfId && messages.length > 0 && (
              <motion.div
                layout="position"
                initial={false}
                transition={{ type: "spring", stiffness: 200, damping: 20, mass: 0.8 }}
                className={`shrink-0 z-10 flex flex-col w-full ${
                  messages.length === 0 && !loading
                    ? 'max-w-3xl mx-auto my-auto px-4 md:px-0'
                    : 'sticky bottom-0 border-t border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 md:px-6'
                }`}
              >
                <div className="mx-auto mb-2 flex max-w-3xl gap-2 overflow-x-auto pb-1 px-4 md:px-0">
                  {ANSWER_MODES.map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => setSelectedMode(mode)}
                      aria-pressed={selectedMode === mode}
                      className={`shrink-0 rounded-full border px-4 py-1.5 text-xs font-semibold shadow-sm transition-all ${
                        selectedMode === mode
                          ? 'border-[var(--accent-blue)] bg-[var(--accent-blue)] text-white'
                          : 'border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:border-[var(--accent-blue)] hover:text-[var(--accent-blue)]'
                      }`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>

                <div className={`w-full ${messages.length === 0 && !loading ? 'bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl shadow-[var(--shadow-lg)] p-3' : ''}`}>

                  <div className="mx-auto flex max-w-3xl items-end gap-2">
                    <div className="relative flex-1">
                      <label htmlFor="chat-input" className="sr-only">
                        Ask a question about your document
                      </label>
                      <textarea
                        id="chat-input"
                        ref={inputRef}
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={
                          isVoiceActive ? 'Listening, speak your question' : 'Ask a question about your document...'
                        }
                        rows={1}
                        disabled={loading}
                        className="max-h-32 w-full resize-none overflow-y-auto rounded-xl border-none bg-transparent px-2 py-3 text-sm leading-relaxed text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-0 disabled:opacity-50"
                        style={{ minHeight: '44px', color: isVoiceActive ? 'var(--accent-blue)' : 'inherit' }}
                        onInput={(e) => {
                          const target = e.target as HTMLTextAreaElement;
                          target.style.height = 'auto';
                          target.style.height = Math.min(target.scrollHeight, 128) + 'px';
                        }}
                      />
                    </div>

                    <VoiceInputButton
                      onResult={(text) => {
                        setInputValue(text);
                        setIsVoiceActive(false);
                      }}
                      onInterim={(text) => {
                        setInputValue(text);
                        setIsVoiceActive(true);
                      }}
                      disabled={loading}
                      className="mb-1"
                    />

                    <button
                      type="button"
                      onClick={() => handleSend()}
                      disabled={!inputValue.trim() || loading}
                      aria-label="Send question"
                      className="flex h-[40px] w-[40px] shrink-0 items-center justify-center rounded-xl bg-[var(--text-primary)] text-white transition-colors hover:bg-black active:translate-y-px disabled:cursor-not-allowed disabled:opacity-40 mb-1 mr-1"
                    >
                      {loading ? (
                        <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
                      ) : (
                        <Send className="h-4 w-4" aria-hidden="true" />
                      )}
                    </button>
                  </div>
                </div>

                

                {messages.length > 0 && (
                  <p className="mx-auto mt-2 max-w-3xl text-center text-xs text-[var(--text-muted)]">
                    Answers come from your document content only. English, Hindi and Hinglish all work.
                  </p>
                )}
              </motion.div>
            )}
          </div>
        </div>
      </div>
      <UpgradeModal
        isOpen={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
        message={upgradeMessage}
      />
    </AppLayout>
  );
};

export default ChatPage;
