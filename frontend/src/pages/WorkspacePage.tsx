import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  Send, FileText, Loader2, Sparkles, 
  Upload, BookOpen, Plus
} from 'lucide-react';
import { fetchPdfs, askQuestion, uploadPdf, getPdfStatus } from '../lib/api';
import type { PDFDocument, ChatMessage } from '../lib/api';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import VoiceInputButton from '../components/voice/VoiceInputButton';
import { useAuthStore } from '../store/useAuthStore';
import MCQCard from '../components/chat/MCQCard';
import ExamPredictorCard from '../components/chat/ExamPredictorCard';
import UpgradeModal from '../components/billing/UpgradeModal';
import GenieAvatar from '../components/GenieAvatar';

interface DisplayMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatSource[];
}

const WorkspacePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialPdfId = searchParams.get('pdf') || '';
  const intent = searchParams.get('intent');
  
  const { user: currentUser } = useAuthStore();

  const [pdfs, setPdfs] = useState<PDFDocument[]>([]);
  const [loadingPdfs, setLoadingPdfs] = useState(true);
  const [selectedPdfId, setSelectedPdfId] = useState(initialPdfId);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [justReadyPdf, setJustReadyPdf] = useState<string | null>(null);

  // Chat State
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [selectedMode, setSelectedMode] = useState('Quick Answer');
  const [loadingChat, setLoadingChat] = useState(false);
  
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgradeMessage, setUpgradeMessage] = useState('');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const activePdf = pdfs.find(p => p.id === selectedPdfId);

  // Load PDFs list
  const loadPdfs = async () => {
    try {
      const data = await fetchPdfs();
      setPdfs(data);
    } catch (err) {
      console.error('Error loading PDFs:', err);
    } finally {
      setLoadingPdfs(false);
    }
  };

  useEffect(() => {
    loadPdfs();
  }, []);

  // Sync URL state
  useEffect(() => {
    if (selectedPdfId) {
      setSearchParams({ pdf: selectedPdfId }, { replace: true });
    } else {
      setSearchParams({}, { replace: true });
    }
  }, [selectedPdfId, setSearchParams]);

  // Open intent upload
  useEffect(() => {
    if (intent === 'upload' && !loadingPdfs) {
      // Simulate click on the dropzone if possible, 
      // or we just let the empty state handle it.
      // Since it's dropzone, we can't programmatically open it easily without ref.
      // The user will see the empty state and can click it.
    }
  }, [intent, loadingPdfs]);

  // Poll for processing PDFs
  useEffect(() => {
    const processingPdfs = pdfs.filter(p => p.status === 'processing');
    
    if (processingPdfs.length > 0) {
      pollingRef.current = setInterval(async () => {
        let anyUpdated = false;
        for (const pdf of processingPdfs) {
          try {
            const status = await getPdfStatus(pdf.id);
            if (status.status !== 'processing') {
              anyUpdated = true;
              if (status.status === 'ready') {
                setJustReadyPdf(pdf.id);
                setTimeout(() => setJustReadyPdf(null), 2000);
              }
            }
          } catch {
            // ignore
          }
        }
        if (anyUpdated) {
          await loadPdfs();
        }
      }, 5000);
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [pdfs]);

  // Auto-scroll chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loadingChat]);

  // Clear chat when PDF changes
  useEffect(() => {
    setMessages([]);
    setInputValue('');
  }, [selectedPdfId]);

  // Upload Logic
  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;
    if (file.type !== 'application/pdf') {
      setError('Please upload a PDF file.');
      return;
    }
    setUploading(true);
    setError('');
    try {
      // Default subject to General for quick upload
      const result = await uploadPdf(file, 'General');
      // Optimistic update
      const newPdf: PDFDocument = {
        id: result.pdf_id,
        name: file.name,
        subject: 'General',
        page_count: 0,
        status: 'processing',
        created_at: new Date().toISOString(),
        user_id: currentUser?.id || ''
      };
      setPdfs(prev => [newPdf, ...prev]);
      setSelectedPdfId(result.pdf_id);
    } catch (err: any) {
      if (err.response?.status === 403 && err.response?.data?.detail?.error) {
        setUpgradeMessage(err.response.data.detail.message);
        setShowUpgradeModal(true);
      } else {
        setError('Failed to upload PDF. Please try again.');
      }
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive, open: openDropzone } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    noClick: activePdf ? true : false, // Disable click to upload if we are in chat mode (unless using the specific button)
  });

  // Chat Logic
  const handleSend = async (overrideQuestion?: string) => {
    const question = typeof overrideQuestion === 'string' ? overrideQuestion.trim() : inputValue.trim();
    if (!question || !selectedPdfId || loadingChat) return;

    const userMessage: DisplayMessage = { role: 'user', content: question };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsVoiceActive(false);
    setLoadingChat(true);

    try {
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
        setMessages(prev => prev.slice(0, -1));
      } else {
        const errorMessage: DisplayMessage = {
          role: 'assistant',
          content: '⚠️ Sorry, I encountered an error processing your question. Please try again.',
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } finally {
      setLoadingChat(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  function renderMessage(msg: DisplayMessage) {
    const mcqMatch = msg.content.match(/```json\n([\s\S]*?)\n```/);
    if (mcqMatch && currentUser && selectedPdfId) {
      try {
        const parsed = JSON.parse(mcqMatch[1]);
        if (parsed.predictions && Array.isArray(parsed.predictions)) {
          const textBeforeJson = msg.content.split('```json')[0].trim();
          return (
            <div className="space-y-4">
              {textBeforeJson && (
                <div className="prose prose-sm max-w-none prose-headings:font-bold prose-headings:text-[var(--text-primary)] prose-p:text-[var(--text-primary)] prose-strong:text-[var(--text-primary)] prose-li:text-[var(--text-primary)] prose-code:text-[var(--accent-indigo)] prose-code:bg-[var(--accent-indigo-light)] prose-code:px-1 prose-code:py-0.5 prose-code:rounded">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{textBeforeJson}</ReactMarkdown>
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

        const session = parsed;
        session.pdfId = selectedPdfId;
        const textBeforeJson = msg.content.split('```json')[0].trim();
        
        return (
          <div className="space-y-4">
            {textBeforeJson && (
              <div className="prose prose-sm max-w-none prose-headings:font-bold prose-headings:text-[var(--text-primary)] prose-p:text-[var(--text-primary)] prose-strong:text-[var(--text-primary)] prose-li:text-[var(--text-primary)] prose-code:text-[var(--accent-indigo)] prose-code:bg-[var(--accent-indigo-light)] prose-code:px-1 prose-code:py-0.5 prose-code:rounded">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{textBeforeJson}</ReactMarkdown>
              </div>
            )}
            <MCQCard
              session={session}
              userId={currentUser.id}
              onSessionComplete={() => {}}
            />
          </div>
        );
      } catch {
        // Fallback
      }
    }

    return (
      <div className="space-y-3">
        <div className="prose prose-sm max-w-none prose-headings:font-bold prose-headings:text-[var(--text-primary)] prose-p:text-[var(--text-primary)] prose-strong:text-[var(--text-primary)] prose-li:text-[var(--text-primary)] prose-code:text-[var(--accent-indigo)] prose-code:bg-[var(--accent-indigo-light)] prose-code:px-1 prose-code:py-0.5 prose-code:rounded">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
        </div>
        {msg.sources && msg.sources.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2 pt-2 border-t border-[var(--border)]">
            {msg.sources.map((src, i) => (
              <div key={i} className="flex items-center gap-1 text-[10px] bg-[var(--bg-secondary)] text-[var(--text-secondary)] px-2 py-1 rounded-md border border-[var(--border)]">
                <FileText className="w-3 h-3" />
                <span>Page {src.page}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Render Sidebar Content (The Rail)
  const renderSidebar = () => {
    return (
      <div className="flex flex-col h-full bg-[var(--bg-card)] w-60 border-r border-[var(--border)] shrink-0 pb-4">
        {/* Top Header */}
        <div className="px-5 py-5 border-b border-[var(--border)] mb-2">
          <div className="flex items-center gap-3 text-xl font-bold text-[var(--text-primary)]">
            <img src="/logo.png" alt="TeachGenie Logo" className="w-10 h-10 object-contain drop-shadow-sm" />
            TeachGenie
          </div>
        </div>

        {/* Upload Button */}
        <div className="px-3 mb-4">
          <button
            onClick={openDropzone}
            disabled={uploading}
            className="w-full btn-gold py-2.5 rounded-xl flex items-center justify-center gap-2 font-medium shadow-sm"
          >
            {uploading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
            Upload PDF
          </button>
        </div>

        {/* Library List */}
        <div className="flex-1 overflow-y-auto px-2 space-y-1">
          <div className="px-3 mb-2 text-[11px] font-bold text-[var(--text-muted)] uppercase tracking-wider">
            Your Library
          </div>
          {loadingPdfs ? (
            <div className="p-4 text-center flex justify-center">
              <Loader2 className="w-5 h-5 animate-spin text-[var(--text-muted)]" />
            </div>
          ) : pdfs.length === 0 ? (
            <div className="px-3 py-4 text-center text-sm text-[var(--text-secondary)]">
              No PDFs yet.
            </div>
          ) : (
            pdfs.map(pdf => (
              <button
                key={pdf.id}
                onClick={() => setSelectedPdfId(pdf.id)}
                className={`w-full flex flex-col text-left px-3 py-2.5 rounded-lg transition-colors ${
                  selectedPdfId === pdf.id 
                    ? 'bg-[var(--accent-green-light)] border border-[var(--accent-green)]/20' 
                    : 'hover:bg-[var(--bg-hover)] border border-transparent'
                }`}
              >
                <div className="flex items-center gap-2 mb-1 w-full overflow-hidden">
                  {pdf.status === 'processing' ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--accent-amber)] shrink-0" />
                  ) : (
                    <BookOpen className={`w-3.5 h-3.5 shrink-0 ${selectedPdfId === pdf.id ? 'text-[var(--accent-green)]' : 'text-[var(--text-muted)]'}`} />
                  )}
                  <span className={`text-sm font-medium truncate ${selectedPdfId === pdf.id ? 'text-[var(--accent-green)]' : 'text-[var(--text-primary)]'}`}>
                    {pdf.name}
                  </span>
                </div>
                <div className="flex items-center justify-between pl-5">
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--bg-secondary)] text-[var(--text-secondary)] font-medium">
                    {pdf.subject || 'General'}
                  </span>
                  {pdf.page_count ? (
                    <span className="text-[10px] text-[var(--text-muted)]">{pdf.page_count}p</span>
                  ) : null}
                </div>
              </button>
            ))
          )}
        </div>

        {/* Stats Strip */}
        <div className="px-3 mt-4 pt-4 border-t border-[var(--border)]">
          <div className="grid grid-cols-2 gap-2">
            <div className="card-storybook p-2 flex flex-col items-center justify-center">
              <span className="text-[10px] text-[var(--text-muted)] font-bold uppercase">PDFs</span>
              <span className="text-lg font-bold text-[var(--text-primary)]">{pdfs.length}</span>
            </div>
            <div className="card-storybook p-2 flex flex-col items-center justify-center">
              <span className="text-[10px] text-[var(--text-muted)] font-bold uppercase">Streak</span>
              <span className="text-lg font-bold text-orange-500">1🔥</span>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <AppLayout 
      title={<span className="font-semibold text-[var(--text-secondary)]">Workspace {activePdf ? <span className="text-[var(--text-primary)]">/ {activePdf.name}</span> : ''}</span>}
      sidebarOverride={renderSidebar()}
    >
      <SEO title="Study Workspace" description="Upload your PDFs and chat with TeachGenie." />
      
      {/* Invisible Dropzone Container */}
      <div {...getRootProps()} className="h-full flex flex-col outline-none">
        <input {...getInputProps()} />
        
        {isDragActive && (
          <div className="absolute inset-0 z-50 bg-[var(--accent-green-light)]/90 backdrop-blur-sm border-4 border-dashed border-[var(--accent-green)] m-4 rounded-3xl flex flex-col items-center justify-center">
            <div className="bg-white p-6 rounded-full shadow-xl mb-4 animate-bounce">
              <Upload className="w-12 h-12 text-[var(--accent-green)]" />
            </div>
            <p className="text-2xl font-bold text-[var(--accent-green)] text-shadow-sm">Drop your notes here!</p>
          </div>
        )}

        <div className="flex-1 flex flex-col h-full bg-[var(--bg-primary)]">
          {error && (
            <div className="bg-red-50 border-b border-red-100 text-red-600 p-3 text-sm flex items-center justify-center">
              {error}
            </div>
          )}

          {!activePdf ? (
            /* STATE 1: Empty / Dropzone */
            <div className="flex-1 flex flex-col items-center justify-center p-6 text-center animate-fadeIn">
              <GenieAvatar size="lg" />
              <h2 className="text-3xl font-bold mt-6 mb-2 tracking-tight text-[var(--text-primary)]">
                Ask anything about your notes
              </h2>
              <p className="text-[var(--text-secondary)] mb-8 max-w-md">
                Upload a textbook chapter, class notes, or a past paper. I'll read it and answer any questions you have.
              </p>
              
              <button 
                onClick={(e) => { e.stopPropagation(); openDropzone(); }}
                className="card-storybook border-2 border-dashed border-[var(--accent-amber)] hover:border-[var(--accent-green)] p-10 flex flex-col items-center justify-center gap-4 transition-all hover:shadow-md cursor-pointer w-full max-w-lg group"
              >
                <div className="w-16 h-16 bg-[var(--bg-secondary)] group-hover:bg-[var(--accent-green-light)] rounded-2xl flex items-center justify-center transition-colors">
                  <Upload className="w-8 h-8 text-[var(--accent-amber)] group-hover:text-[var(--accent-green)]" />
                </div>
                <div>
                  <p className="font-bold text-[var(--text-primary)] text-lg">Click to Upload PDF</p>
                  <p className="text-sm text-[var(--text-muted)] mt-1">or drag and drop it here</p>
                </div>
              </button>
            </div>
          ) : activePdf.status === 'processing' ? (
            /* STATE 2: Parsing */
            <div className="flex-1 flex flex-col items-center justify-center p-6 text-center animate-fadeIn">
              <GenieAvatar size="lg" isGenerating={true} />
              <h3 className="text-2xl font-bold mt-6 text-[var(--text-primary)] animate-pulse">
                Reading your PDF...
              </h3>
              <p className="text-[var(--text-secondary)] mt-2">
                Extracting knowledge from {activePdf.name}. This usually takes a few seconds.
              </p>
            </div>
          ) : (
            /* STATE 3: Chat */
            <div className="flex-1 flex flex-col h-full relative" onClick={(e) => e.stopPropagation()}>
              
              {/* Messages Area */}
              <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center max-w-2xl mx-auto space-y-8 pb-10">
                    <GenieAvatar size="lg" isSuccess={justReadyPdf === activePdf.id} />
                    <div className="space-y-2">
                      <h2 className="text-3xl tracking-tight text-[var(--text-primary)]">
                        I've read <span className="font-bold text-[var(--accent-green)]">{activePdf.name}</span>.
                      </h2>
                      <p className="text-[var(--text-secondary)] text-lg">What would you like to know?</p>
                    </div>
                  </div>
                ) : (
                  <div className="max-w-4xl mx-auto space-y-6 pb-20">
                    {messages.map((msg, i) => (
                      <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slideUp`} style={{ animationDelay: '0.05s' }}>
                        <div className={`max-w-[85%] md:max-w-[75%] rounded-2xl p-4 shadow-sm ${
                          msg.role === 'user'
                            ? 'bg-[var(--accent-green-light)] text-[var(--accent-green-dark)] border border-[var(--accent-green)]/20'
                            : 'card-storybook'
                        }`}>
                          {msg.role === 'assistant' && (
                            <div className="flex items-center gap-2 mb-3 pb-2 border-b border-[var(--border)]">
                              <GenieAvatar size="sm" isSuccess={i === messages.length - 1} />
                              <span className="font-bold text-[var(--text-primary)] text-sm">TeachGenie</span>
                            </div>
                          )}
                          {msg.role === 'user' ? (
                            <p className="whitespace-pre-wrap">{msg.content}</p>
                          ) : (
                            renderMessage(msg)
                          )}
                        </div>
                      </div>
                    ))}
                    {loadingChat && (
                      <div className="flex justify-start animate-fadeIn">
                        <div className="card-storybook rounded-2xl p-4 flex items-center gap-3">
                          <GenieAvatar size="sm" isGenerating={true} />
                          <div className="flex gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-[var(--accent-amber)] animate-bounce" style={{ animationDelay: '0s' }} />
                            <span className="w-2 h-2 rounded-full bg-[var(--accent-amber)] animate-bounce" style={{ animationDelay: '0.15s' }} />
                            <span className="w-2 h-2 rounded-full bg-[var(--accent-amber)] animate-bounce" style={{ animationDelay: '0.3s' }} />
                          </div>
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </div>

              {/* Input Area */}
              <div className="p-4 bg-[var(--bg-primary)]/80 backdrop-blur-md border-t border-[var(--border)] sticky bottom-0">
                <div className="max-w-4xl mx-auto">
                  {/* Mode Selector */}
                  <div className="flex overflow-x-auto pb-3 gap-2 hide-scrollbar">
                    {['Quick Answer', 'Full Chapter Crux', 'No Fact Miss', 'Formula Coverage', 'Exam Shield Notes', 'Generate MCQs', 'Predicted Exam Questions', 'Kid Mode', 'Professor Mode'].map((mode) => {
                      const isSelected = selectedMode === mode;
                      return (
                        <button
                          key={mode}
                          onClick={() => setSelectedMode(mode)}
                          className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all border ${
                            isSelected
                              ? 'bg-[var(--accent-amber)] text-white border-transparent shadow-sm transform scale-105'
                              : 'bg-[var(--bg-card)] text-[var(--text-secondary)] border-[var(--border)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]'
                          }`}
                        >
                          {isSelected && <Sparkles className="w-3 h-3" />}
                          {mode}
                        </button>
                      );
                    })}
                  </div>

                  <div className="relative group">
                    <div className="absolute -inset-1 bg-gradient-to-r from-[var(--accent-green)] to-[var(--accent-indigo)] rounded-2xl opacity-10 group-focus-within:opacity-30 group-focus-within:animate-[borderGlow_3s_infinite] transition-all blur-sm" />
                    <div className="relative bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl shadow-sm flex items-end p-2 transition-all group-focus-within:border-[var(--accent-green)]/50 group-focus-within:shadow-md">
                      <VoiceInputButton 
                        onResult={(text) => {
                          setInputValue(prev => prev ? `${prev} ${text}` : text);
                          if (inputRef.current) {
                            inputRef.current.focus();
                            inputRef.current.style.height = 'auto';
                            inputRef.current.style.height = inputRef.current.scrollHeight + 'px';
                          }
                        }}
                      />
                      
                      <textarea
                        ref={inputRef}
                        value={inputValue}
                        onChange={(e) => {
                          setInputValue(e.target.value);
                          e.target.style.height = 'auto';
                          e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
                        }}
                        onKeyDown={handleKeyDown}
                        placeholder={isVoiceActive ? "Listening..." : "Ask TeachGenie about this document..."}
                        className="flex-1 bg-transparent border-none focus:ring-0 text-[var(--text-primary)] placeholder:text-[var(--text-muted)] resize-none py-3 px-3 max-h-[200px] min-h-[48px]"
                        rows={1}
                      />
                      
                      <button
                        onClick={() => handleSend()}
                        disabled={!inputValue.trim() || loadingChat}
                        className={`p-3 rounded-xl flex items-center justify-center transition-all ${
                          inputValue.trim() && !loadingChat
                            ? 'bg-[var(--accent-green)] text-white hover:bg-[#2e7a50] shadow-sm transform hover:scale-105 active:scale-95'
                            : 'bg-[var(--bg-secondary)] text-[var(--text-muted)] cursor-not-allowed'
                        }`}
                      >
                        <Send className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {showUpgradeModal && (
        <UpgradeModal
          isOpen={showUpgradeModal}
          onClose={() => setShowUpgradeModal(false)}
          message={upgradeMessage}
        />
      )}
    </AppLayout>
  );
};

export default WorkspacePage;
