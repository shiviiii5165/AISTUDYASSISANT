import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, FileText, Loader2, ChevronDown, Sparkles, ArrowDown } from 'lucide-react';
import { fetchPdfs, askQuestion } from '../lib/api';
import type { PDFDocument, ChatMessage, ChatSource } from '../lib/api';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import VoiceInputButton from '../components/voice/VoiceInputButton';
import { useAuthStore } from '../store/useAuthStore';
import MCQCard from '../components/chat/MCQCard';
import ExamPredictorCard from '../components/chat/ExamPredictorCard';
import UpgradeModal from '../components/billing/UpgradeModal';
import { Lock } from 'lucide-react';
import GenieAvatar from '../components/GenieAvatar';

interface DisplayMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatSource[];
}

const ChatPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialPdfId = searchParams.get('pdf') || '';
  const { user: currentUser } = useAuthStore();

  const [pdfs, setPdfs] = useState<PDFDocument[]>([]);
  const [selectedPdfId, setSelectedPdfId] = useState(initialPdfId);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [selectedMode, setSelectedMode] = useState('Quick Answer');
  const [loading, setLoading] = useState(false);
  const [loadingPdfs, setLoadingPdfs] = useState(true);
  const [showPdfDropdown, setShowPdfDropdown] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgradeMessage, setUpgradeMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const PRO_MODES = [
    'Full Chapter Crux',
    'No Fact Miss',
    'Formula Coverage',
    'Exam Shield Notes',
    'Generate MCQs',
    'Predicted Exam Questions'
  ];

  // Load PDFs list
  useEffect(() => {
    (async () => {
      try {
        const data = await fetchPdfs();
        setPdfs(data.filter(p => p.status === 'ready'));
      } catch (err) {
        console.error('Error loading PDFs:', err);
      } finally {
        setLoadingPdfs(false);
      }
    })();
  }, []);

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
    const question = typeof overrideQuestion === 'string' ? overrideQuestion.trim() : inputValue.trim();
    if (!question || !selectedPdfId || loading) return;

    const userMessage: DisplayMessage = { role: 'user', content: question };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsVoiceActive(false);
    setLoading(true);

    try {
      // Build chat history for context (only role + content)
      const history: ChatMessage[] = messages.map(m => ({
        role: m.role,
        content: m.content,
      }));

      const response = await askQuestion(selectedPdfId, question, selectedMode, history);

      const assistantMessage: DisplayMessage = {
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (err: any) {
      if (err.response?.status === 403 && err.response?.data?.detail?.error) {
        setUpgradeMessage(err.response.data.detail.message);
        setShowUpgradeModal(true);
        // Remove the user message from UI since it failed
        setMessages(prev => prev.slice(0, -1));
      } else {
        const errorMessage: DisplayMessage = {
          role: 'assistant',
          content: '⚠️ Sorry, I encountered an error processing your question. Please try again.',
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
    // Detect if the response contains an MCQ JSON block
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
                <div className="prose prose-sm max-w-none prose-headings:font-bold prose-headings:text-[var(--text-primary)] prose-p:text-[var(--text-primary)] prose-strong:text-[var(--text-primary)] prose-li:text-[var(--text-primary)] prose-code:text-[var(--accent-indigo)] prose-code:bg-[var(--accent-indigo-light)] prose-code:px-1 prose-code:py-0.5 prose-code:rounded">
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
              <div className="prose prose-sm max-w-none prose-headings:font-bold prose-headings:text-[var(--text-primary)] prose-p:text-[var(--text-primary)] prose-strong:text-[var(--text-primary)] prose-li:text-[var(--text-primary)] prose-code:text-[var(--accent-indigo)] prose-code:bg-[var(--accent-indigo-light)] prose-code:px-1 prose-code:py-0.5 prose-code:rounded">
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
        // JSON parsing failed — fall through and render as plain text
      }
    }

    return (
      <div className="prose prose-sm max-w-none prose-headings:font-bold prose-headings:text-[var(--text-primary)] prose-p:text-[var(--text-primary)] prose-strong:text-[var(--text-primary)] prose-li:text-[var(--text-primary)] prose-code:text-[var(--accent-indigo)] prose-code:bg-[var(--accent-indigo-light)] prose-code:px-1 prose-code:py-0.5 prose-code:rounded">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {msg.content}
        </ReactMarkdown>
      </div>
    );
  }

  return (
    <AppLayout title="AI Chat">
      <SEO 
        title={selectedPdf ? `Chat with ${selectedPdf.name}` : "AI Chat"} 
        description="Ask questions, generate MCQs, and understand complex topics directly from your uploaded study materials." 
      />
      <div className="flex flex-col h-full">
        {/* PDF Selector Bar */}
        <div className="px-4 md:px-6 py-2.5 border-b border-[var(--border)] bg-white flex items-center gap-2 md:gap-3 shrink-0 flex-wrap">
          <FileText className="w-4 h-4 text-[var(--accent-indigo)] shrink-0 hidden sm:block" />
          <span className="text-xs font-medium text-[var(--text-muted)] hidden sm:block">Chatting with:</span>
          <div className="relative">
            <button
              onClick={() => setShowPdfDropdown(!showPdfDropdown)}
              className="flex items-center gap-2 px-2.5 py-1.5 border border-[var(--border)] rounded-lg text-xs font-semibold hover:bg-[var(--bg-hover)] transition-colors min-w-[140px] md:min-w-[200px] text-left"
              disabled={loadingPdfs}
            >
              {loadingPdfs ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : selectedPdf ? (
                <span className="truncate">{selectedPdf.name}</span>
              ) : (
                <span className="text-[var(--text-muted)]">Select a PDF...</span>
              )}
              <ChevronDown className="w-3.5 h-3.5 text-[var(--text-muted)] ml-auto shrink-0" />
            </button>

            {showPdfDropdown && (
              <div className="absolute top-full left-0 mt-1 bg-white border border-[var(--border)] rounded-xl shadow-lg z-30 py-1 min-w-[280px] max-h-64 overflow-y-auto">
                {pdfs.length === 0 ? (
                  <div className="px-4 py-3 text-sm text-[var(--text-muted)]">
                    No PDFs ready. Upload one first.
                  </div>
                ) : (
                  pdfs.map((pdf) => (
                    <button
                      key={pdf.id}
                      onClick={() => {
                        setSelectedPdfId(pdf.id);
                        setShowPdfDropdown(false);
                        setMessages([]);
                      }}
                      className={`w-full text-left px-4 py-2.5 text-sm hover:bg-[var(--bg-hover)] transition-colors flex items-center gap-3 ${
                        selectedPdfId === pdf.id ? 'bg-[var(--accent-green)]/5 font-semibold' : ''
                      }`}
                    >
                      <FileText className="w-4 h-4 text-[var(--accent-indigo)] shrink-0" />
                      <div className="truncate">
                        <div className="truncate font-medium">{pdf.name}</div>
                        <div className="text-xs text-[var(--text-muted)]">{pdf.subject} • {pdf.page_count || '?'} pages</div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          {messages.length > 0 && (
            <button
              onClick={() => setMessages([])}
              className="ml-auto text-xs text-[var(--text-muted)] hover:text-[var(--accent-red)] transition-colors"
            >
              Clear chat
            </button>
          )}
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-4 md:px-6 py-4 md:py-6">
          {!selectedPdfId ? (
            /* Empty state: no PDF selected */
            <div className="flex flex-col items-center justify-center h-full text-center space-y-4 animate-fadeIn">
              <GenieAvatar size="md" />
              <h3 className="text-2xl font-bold text-[var(--text-primary)] mt-2">
                Select a PDF to start chatting
              </h3>
              <p className="text-[var(--text-secondary)] text-sm max-w-md">
                Choose one of your uploaded PDFs from the dropdown above, then ask any question about its content.
              </p>
            </div>
          ) : messages.length === 0 && !loading ? (
            /* Empty state: PDF selected but no messages */
            <div className="flex flex-col items-center justify-center h-full text-center space-y-4 animate-fadeIn">
              <GenieAvatar size="md" />
              <h3 className="text-2xl font-bold text-[var(--text-primary)] mt-2">
                Ask anything about "{selectedPdf?.name}"
              </h3>
              <p className="text-[var(--text-secondary)] text-sm max-w-md mb-6">
                I'll answer from the content of your PDF with page citations. Try questions in Hindi or English!
              </p>
              <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                {[
                  'Summarize the key concepts',
                  'Explain the first chapter',
                  'What are the important formulas?',
                  'List all definitions',
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => {
                      setInputValue(suggestion);
                      inputRef.current?.focus();
                    }}
                    className="px-4 py-2 text-xs font-semibold bg-[var(--bg-card)] border border-[var(--border)] rounded-full text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:shadow-md hover:text-[var(--text-primary)] hover:-translate-y-0.5 transition-all"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Chat messages */
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.map((message, index) => (
                <div key={index} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {message.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-full bg-[var(--accent-indigo-light)] flex items-center justify-center shrink-0 mt-1 border border-[var(--border)] shadow-sm">
                      <Sparkles className="w-4 h-4 text-[var(--accent-indigo)]" />
                    </div>
                  )}
                  <div
                    className={`max-w-[85%] md:max-w-[75%] rounded-2xl px-3.5 py-2.5 md:px-4 md:py-3 ${
                      message.role === 'user'
                        ? 'bg-[var(--text-primary)] text-white rounded-br-md shadow-sm'
                        : 'bg-[var(--bg-card)] border border-[var(--border)] text-[var(--text-primary)] rounded-bl-md shadow-sm'
                    }`}
                  >
                    {message.role === 'assistant' ? (
                      renderMessage(message)
                    ) : (
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
                    )}

                    {/* Source citations */}
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-[var(--border)]">
                        <p className="text-xs font-semibold text-[var(--text-muted)] mb-2 flex items-center gap-1">
                          <ArrowDown className="w-3 h-3" />
                          Sources
                        </p>
                        <div className="space-y-1.5">
                          {message.sources.map((source, i) => (
                            <div key={i} className="text-xs text-[var(--text-secondary)] bg-[var(--bg-secondary)] rounded-lg px-2.5 py-1.5">
                              <span className="font-bold text-[var(--accent-indigo)]">
                                {source.page === 'Note' ? 'Note' : `Page ${source.page}`}
                              </span>
                              <span className="mx-1.5 text-[var(--border-strong)]">•</span>
                              <span className="opacity-80">{source.text}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Typing indicator */}
              {loading && (
                <div className="flex gap-3 justify-start animate-fadeIn">
                  <div className="w-8 h-8 rounded-full bg-[var(--accent-indigo-light)] flex items-center justify-center shrink-0 mt-1 border border-[var(--border)] shadow-sm">
                    <Sparkles className="w-4 h-4 text-[var(--accent-indigo)]" />
                  </div>
                  <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 bg-[var(--accent-indigo)] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-[var(--accent-indigo)] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-[var(--accent-indigo)] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Bar */}
        {selectedPdfId && (
          <div className="px-4 md:px-6 py-3 border-t border-[var(--border)] bg-white shrink-0">
            <div className="max-w-3xl mx-auto mb-2 overflow-x-auto pb-1.5 scrollbar-thin flex gap-1.5">
              {[
                'Quick Answer',
                'Full Chapter Crux',
                'No Fact Miss',
                'Formula Coverage',
                'Exam Shield Notes',
                'Generate MCQs',
                'Predicted Exam Questions',
                'Kid Mode',
                'Professor Mode'
              ].map((mode) => {
                const isLocked = false; // Plan requirement removed
                
                return (
                  <button
                    key={mode}
                    onClick={() => {
                      if (isLocked) {
                        setUpgradeMessage(`Unlock ${mode} with TeachGenie Pro.`);
                        setShowUpgradeModal(true);
                      } else {
                        setSelectedMode(mode);
                      }
                    }}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap transition-all flex items-center gap-1 border ${
                      selectedMode === mode
                        ? 'bg-gradient-to-r from-[var(--accent-indigo)] to-[#2A4A6E] text-white border-transparent shadow-md'
                        : isLocked
                        ? 'bg-[var(--bg-secondary)] border-transparent text-[var(--text-muted)] hover:bg-gray-200'
                        : 'bg-[var(--bg-card)] border-[var(--border)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:shadow-sm'
                    }`}
                  >
                    {isLocked && <Lock className="w-2.5 h-2.5" />}
                    {mode}
                  </button>
                );
              })}
            </div>
            <div className="max-w-3xl mx-auto flex items-end gap-2 relative group">
              <div className="absolute -inset-1 bg-gradient-to-r from-[var(--accent-green)] to-[var(--accent-indigo)] rounded-xl opacity-0 group-focus-within:opacity-20 group-focus-within:animate-[borderGlow_3s_infinite] transition-all blur-sm pointer-events-none" />
              <div className="flex-1 relative">
                <textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={isVoiceActive ? "Listening... speak your question" : "Ask a question about your PDF..."}
                  rows={1}
                  disabled={loading}
                  className="w-full resize-none px-4 py-3 border border-[var(--border)] rounded-xl focus:outline-none focus:ring-1 focus:ring-[var(--accent-amber)] focus:border-[var(--accent-amber)] bg-[var(--bg-card)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] text-sm leading-relaxed disabled:opacity-50 max-h-32 overflow-y-auto shadow-inner relative z-10"
                  style={{ minHeight: '44px', color: isVoiceActive ? 'var(--accent-green)' : 'inherit' }}
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
                onClick={() => handleSend()}
                disabled={!inputValue.trim() || loading}
                className="btn-gold p-3 rounded-xl flex items-center justify-center shrink-0 disabled:opacity-40 disabled:cursor-not-allowed shadow-md relative z-10 w-[44px] h-[44px]"
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
            <p className="text-center text-xs text-[var(--text-muted)] mt-2 max-w-3xl mx-auto">
              TeachGenie answers from your PDF content only. Ask in Hindi or English.
            </p>
          </div>
        )}
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
