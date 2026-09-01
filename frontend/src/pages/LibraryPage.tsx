import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, Search, Loader2, Trash2, MessageSquare, ChevronDown, RefreshCw } from 'lucide-react';
import { fetchPdfs, uploadPdf, deletePdf, getPdfStatus } from '../lib/api';
import type { PDFDocument } from '../lib/api';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import HandwrittenUpload from '../components/library/HandwrittenUpload';
import UpgradeModal from '../components/billing/UpgradeModal';

const SUBJECTS = ['General', 'Physics', 'Chemistry', 'Biology', 'Maths', 'English', 'History', 'Computer Science', 'Economics'];

const SUBJECT_COLORS: Record<string, { bg: string; text: string }> = {
  Physics: { bg: 'bg-blue-100', text: 'text-blue-700' },
  Chemistry: { bg: 'bg-indigo-100', text: 'text-indigo-700' },
  Biology: { bg: 'bg-emerald-100', text: 'text-emerald-700' },
  Maths: { bg: 'bg-purple-100', text: 'text-purple-700' },
  English: { bg: 'bg-amber-100', text: 'text-amber-700' },
  History: { bg: 'bg-rose-100', text: 'text-rose-700' },
  'Computer Science': { bg: 'bg-cyan-100', text: 'text-cyan-700' },
  Economics: { bg: 'bg-orange-100', text: 'text-orange-700' },
  General: { bg: 'bg-gray-100', text: 'text-gray-700' },
};

const LibraryPage: React.FC = () => {
  const [pdfs, setPdfs] = useState<PDFDocument[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSubject, setSelectedSubject] = useState('General');
  const [showSubjectDropdown, setShowSubjectDropdown] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [loadingPdfs, setLoadingPdfs] = useState(true);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgradeMessage, setUpgradeMessage] = useState('');
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const navigate = useNavigate();

  const loadPdfs = async () => {
    try {
      const data = await fetchPdfs();
      setPdfs(data);
    } catch (err) {
      console.error('Error fetching PDFs:', err);
    } finally {
      setLoadingPdfs(false);
    }
  };

  useEffect(() => {
    loadPdfs();
  }, []);

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
      const result = await uploadPdf(file, selectedSubject);

      // Add to list optimistically
      const newPdf: PDFDocument = {
        id: result.pdf_id,
        name: file.name,
        subject: selectedSubject,
        status: 'processing',
        page_count: 0,
        created_at: new Date().toISOString(),
        user_id: '',
      };
      
      setPdfs((prev) => [newPdf, ...prev]);
    } catch (err: any) {
      console.error('Upload error:', err);
      if (err.response?.status === 403 && err.response?.data?.detail?.error) {
        setUpgradeMessage(err.response.data.detail.message);
        setShowUpgradeModal(true);
        setError('');
      } else {
        const serverError = err.response?.data?.detail;
        const fallback = err.message || 'Failed to upload PDF. Please try again.';
        setError(serverError || `Error: ${fallback}`);
      }
    } finally {
      setUploading(false);
    }
  }, [selectedSubject]);

  const handleDelete = async (pdfId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this PDF?')) return;
    
    setDeletingId(pdfId);
    try {
      await deletePdf(pdfId);
      setPdfs((prev) => prev.filter(p => p.id !== pdfId));
    } catch (err) {
      console.error('Delete error:', err);
      setError('Failed to delete PDF.');
    } finally {
      setDeletingId(null);
    }
  };

  const handleChatClick = (pdf: PDFDocument) => {
    if (pdf.status === 'ready') {
      navigate(`/chat?pdf=${pdf.id}`);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1 
  });

  const filteredPdfs = pdfs.filter(pdf => 
    pdf.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <AppLayout title="My Library">
      <SEO 
        title="My Library" 
        description="Upload and manage your PDF study materials and handwritten notes in TeachGenie." 
      />
      <div className="p-4 md:p-6 lg:p-8 max-w-5xl mx-auto space-y-5 md:space-y-6">
        
        <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold">Study Materials</h1>
            <p className="text-[var(--text-secondary)] text-sm mt-0.5">Upload and manage your PDFs</p>
          </div>
          
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              onClick={loadPdfs}
              className="p-2 border border-[var(--border)] rounded-lg hover:bg-[var(--bg-hover)] transition-colors shrink-0"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4 text-[var(--text-secondary)]" />
            </button>
            <div className="relative flex-1 sm:flex-initial">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
              <input 
                type="text" 
                placeholder="Search notes..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-3 py-2 border border-[var(--border)] rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-[var(--accent-green)] focus:border-transparent w-full sm:w-56 shadow-[var(--shadow-sm)] text-sm"
              />
            </div>
          </div>
        </header>

        {/* Upload Dropzone */}
        <div className="bg-white rounded-xl border border-[var(--border)] p-4 md:p-5 shadow-[var(--shadow-sm)]">
          {/* Subject Selector */}
          <div className="flex items-center gap-3 mb-4">
            <span className="text-sm font-medium text-[var(--text-secondary)]">Subject:</span>
            <div className="relative">
              <button
                onClick={() => setShowSubjectDropdown(!showSubjectDropdown)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 border border-[var(--border)] rounded-lg text-xs font-medium hover:bg-[var(--bg-hover)] transition-colors"
              >
                <span className={`w-2 h-2 rounded-full ${SUBJECT_COLORS[selectedSubject]?.bg || 'bg-gray-300'}`} />
                {selectedSubject}
                <ChevronDown className="w-3.5 h-3.5 text-[var(--text-muted)]" />
              </button>
              {showSubjectDropdown && (
                <div className="absolute top-full left-0 mt-1 bg-white border border-[var(--border)] rounded-xl shadow-lg z-20 py-1 min-w-[160px]">
                  {SUBJECTS.map((subject) => (
                    <button
                      key={subject}
                      onClick={() => {
                        setSelectedSubject(subject);
                        setShowSubjectDropdown(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-sm hover:bg-[var(--bg-hover)] transition-colors flex items-center gap-2 ${
                        selectedSubject === subject ? 'font-semibold text-[var(--accent-green)]' : 'text-[var(--text-primary)]'
                      }`}
                    >
                      <span className={`w-2 h-2 rounded-full ${SUBJECT_COLORS[subject]?.bg || 'bg-gray-300'}`} />
                      {subject}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div 
            {...getRootProps()} 
            className={`border-2 border-dashed rounded-xl p-6 md:p-8 text-center cursor-pointer transition-all duration-200 ease-in-out
              ${isDragActive ? 'border-[var(--accent-green)] bg-green-50 scale-[1.01]' : 'border-[var(--border)] hover:border-[var(--accent-green)] hover:bg-green-50/50'}
              ${uploading ? 'opacity-50 pointer-events-none' : ''}
            `}
          >
            <input {...getInputProps()} />
            <div className="mx-auto w-11 h-11 bg-green-100 rounded-xl flex items-center justify-center mb-3">
              {uploading ? (
                <Loader2 className="w-7 h-7 text-[var(--accent-green)] animate-spin" />
              ) : (
                <Upload className="w-7 h-7 text-[var(--accent-green)]" />
              )}
            </div>
            <h3 className="text-sm font-bold mb-0.5 text-[var(--text-primary)]">
              {isDragActive ? "Drop your PDF here..." : "Drag & drop your PDF here"}
            </h3>
            <p className="text-[var(--text-muted)] text-xs">
              {uploading ? "Uploading and processing..." : "or click to browse • PDF files only"}
            </p>
            {error && <p className="text-[var(--accent-red)] mt-3 text-sm font-medium">{error}</p>}
          </div>
        </div>

        {/* Handwritten Notes Section */}
        <div className="bg-white rounded-xl border border-[var(--border)] p-4 md:p-5 shadow-[var(--shadow-sm)]">
          <h2 className="text-sm font-bold text-[var(--text-primary)] mb-0.5">Handwritten Notes</h2>
          <p className="text-xs text-[var(--text-secondary)] mb-3">Upload a photo of your handwritten notes — AI will read and convert them</p>
          <HandwrittenUpload selectedSubject={selectedSubject} onUploadSuccess={loadPdfs} />
        </div>

        {/* PDF Grid */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold">Your Uploads</h2>
            <span className="text-sm text-[var(--text-secondary)]">{filteredPdfs.length} document{filteredPdfs.length !== 1 ? 's' : ''}</span>
          </div>

          {loadingPdfs ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-8 h-8 text-[var(--accent-green)] animate-spin" />
            </div>
          ) : filteredPdfs.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-xl border border-[var(--border)] shadow-[var(--shadow-sm)]">
              <FileText className="w-10 h-10 text-[var(--border)] mx-auto mb-3" />
              <p className="text-[var(--text-secondary)] font-medium">
                {searchQuery ? 'No PDFs match your search.' : "You haven't uploaded any notes yet."}
              </p>
              <p className="text-[var(--text-muted)] text-sm mt-1">
                {searchQuery ? 'Try a different search term.' : 'Upload your first PDF to get started!'}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {filteredPdfs.map((pdf) => {
                const colors = SUBJECT_COLORS[pdf.subject] || SUBJECT_COLORS['General'];
                return (
                  <div 
                    key={pdf.id} 
                    onClick={() => handleChatClick(pdf)}
                    className={`bg-white p-4 rounded-xl shadow-[var(--shadow-sm)] border border-[var(--border)] transition-all group relative ${
                      pdf.status === 'ready' 
                        ? 'hover:shadow-md hover:border-[var(--accent-green)] cursor-pointer' 
                        : 'opacity-75'
                    }`}
                  >
                    {/* Actions */}
                    <div className="absolute top-3 right-3 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {pdf.status === 'ready' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/chat?pdf=${pdf.id}`);
                          }}
                          className="p-1.5 rounded-lg hover:bg-[var(--accent-indigo-light)] transition-colors"
                          title="Chat with this PDF"
                        >
                          <MessageSquare className="w-4 h-4 text-[var(--accent-indigo)]" />
                        </button>
                      )}
                      <button
                        onClick={(e) => handleDelete(pdf.id, e)}
                        disabled={deletingId === pdf.id}
                        className="p-1.5 rounded-lg hover:bg-red-50 transition-colors"
                        title="Delete PDF"
                      >
                        {deletingId === pdf.id ? (
                          <Loader2 className="w-4 h-4 text-red-500 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4 text-red-400" />
                        )}
                      </button>
                    </div>

                    <div className="w-12 h-12 bg-[var(--bg-secondary)] rounded-xl flex items-center justify-center mb-4 group-hover:scale-105 transition-transform">
                      {pdf.status === 'processing' ? (
                        <Loader2 className="w-6 h-6 text-[var(--accent-amber)] animate-spin" />
                      ) : (
                        <FileText className="w-6 h-6 text-[var(--accent-indigo)]" />
                      )}
                    </div>
                    <h3 className="font-bold text-[var(--text-primary)] mb-2 truncate pr-8" title={pdf.name}>
                      {pdf.name}
                    </h3>
                    <div className="flex items-center justify-between text-sm">
                      <span className={`px-2 py-0.5 rounded-md text-xs font-bold ${colors.bg} ${colors.text}`}>
                        {pdf.subject}
                      </span>
                      <div className="flex items-center gap-2">
                        {pdf.page_count ? (
                          <span className="text-[var(--text-muted)] text-xs">{pdf.page_count} pages</span>
                        ) : null}
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold
                          ${pdf.status === 'ready' ? 'bg-green-100 text-green-700' : ''}
                          ${pdf.status === 'processing' ? 'bg-amber-100 text-amber-700' : ''}
                          ${pdf.status === 'error' ? 'bg-red-100 text-red-700' : ''}
                        `}>
                          {pdf.status === 'ready' ? '● Ready' : pdf.status === 'processing' ? '◌ Processing' : '✕ Error'}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
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

export default LibraryPage;
