import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, Search, Loader2, Trash2, MessageSquare, ChevronDown, RefreshCw } from 'lucide-react';
import { fetchPdfs, uploadPdf, deletePdf, getPdfStatus } from '../lib/api';
import type { PDFDocument } from '../lib/api';
import { SUBJECTS, subjectStyle } from '../lib/subjects';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import HandwrittenUpload from '../components/library/HandwrittenUpload';
import UpgradeModal from '../components/billing/UpgradeModal';

const STATUS_STYLES: Record<string, string> = {
  ready: 'bg-green-100 text-green-800',
  processing: 'bg-amber-100 text-amber-800',
  error: 'bg-red-100 text-red-800',
};

const STATUS_LABELS: Record<string, string> = {
  ready: 'Ready',
  processing: 'Processing',
  error: 'Failed',
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
    // Native confirm is kept deliberately: the delete guarantee must stay
    // exactly as reliable as before. Restyling it is not worth weakening it.
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
      <div className="mx-auto max-w-5xl space-y-6 p-4 md:p-6 lg:p-8">

        {/* Toolbar. The page heading lives in the topbar, so this row carries
            controls only rather than repeating the title. */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-[var(--text-secondary)]">
            Upload PDFs and handwritten notes, then ask questions about them.
          </p>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={loadPdfs}
              aria-label="Refresh document list"
              className="shrink-0 rounded-lg border border-[var(--border)] p-2 transition-colors hover:bg-[var(--bg-hover)]"
            >
              <RefreshCw className="h-4 w-4 text-[var(--text-secondary)]" aria-hidden="true" />
            </button>
            <div className="relative flex-1 sm:flex-initial">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]"
                aria-hidden="true"
              />
              <label htmlFor="library-search" className="sr-only">Search documents</label>
              <input
                id="library-search"
                type="text"
                placeholder="Search documents"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] py-2 pl-9 pr-3 text-sm placeholder:text-[var(--text-muted)] focus:border-[var(--accent-green)] focus:outline-none sm:w-56"
              />
            </div>
          </div>
        </div>

        {/* Upload */}
        <section className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4 md:p-5">
          <div className="mb-4 flex items-center gap-3">
            <span className="text-sm font-medium text-[var(--text-secondary)]">Subject</span>
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowSubjectDropdown(!showSubjectDropdown)}
                aria-expanded={showSubjectDropdown}
                aria-haspopup="listbox"
                className="flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-2.5 py-1.5 text-xs font-medium transition-colors hover:bg-[var(--bg-hover)]"
              >
                <span
                  aria-hidden="true"
                  className={`h-2 w-2 rounded-full ${subjectStyle(selectedSubject).dot}`}
                />
                {selectedSubject}
                <ChevronDown className="h-3.5 w-3.5 text-[var(--text-muted)]" aria-hidden="true" />
              </button>
              {showSubjectDropdown && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setShowSubjectDropdown(false)} />
                  <ul
                    role="listbox"
                    aria-label="Subject"
                    className="absolute left-0 top-full z-20 mt-1 min-w-[170px] rounded-xl border border-[var(--border)] bg-[var(--bg-card)] py-1 shadow-[var(--shadow-lg)]"
                  >
                    {SUBJECTS.map((subject) => (
                      <li key={subject} role="option" aria-selected={selectedSubject === subject}>
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedSubject(subject);
                            setShowSubjectDropdown(false);
                          }}
                          className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-[var(--bg-hover)] ${
                            selectedSubject === subject
                              ? 'font-semibold text-[var(--accent-green-text)]'
                              : 'text-[var(--text-primary)]'
                          }`}
                        >
                          <span
                            aria-hidden="true"
                            className={`h-2 w-2 rounded-full ${subjectStyle(subject).dot}`}
                          />
                          {subject}
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          </div>

          <div
            {...getRootProps()}
            className={`cursor-pointer rounded-xl border-2 border-dashed p-6 text-center transition-colors md:p-8 ${
              isDragActive
                ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)]'
                : 'border-[var(--border-strong)] hover:border-[var(--accent-green)] hover:bg-[var(--bg-hover)]'
            } ${uploading ? 'pointer-events-none opacity-60' : ''}`}
          >
            <input {...getInputProps()} />
            <span className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--accent-green-light)]">
              {uploading ? (
                <Loader2 className="h-6 w-6 animate-spin text-[var(--accent-green-text)]" aria-hidden="true" />
              ) : (
                <Upload className="h-6 w-6 text-[var(--accent-green-text)]" aria-hidden="true" />
              )}
            </span>
            <p className="font-display text-sm font-semibold text-[var(--text-primary)]">
              {isDragActive ? 'Drop your PDF here' : 'Drag and drop your PDF here'}
            </p>
            <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
              {uploading ? 'Uploading and processing' : 'or click to browse. PDF files only.'}
            </p>
          </div>

          {error && (
            <p role="alert" className="mt-3 text-sm font-medium text-red-700">
              {error}
            </p>
          )}
        </section>

        {/* Handwritten notes */}
        <section className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4 md:p-5">
          <h2 className="font-display text-sm font-semibold text-[var(--text-primary)]">
            Handwritten notes
          </h2>
          <p className="mb-3 mt-0.5 text-xs text-[var(--text-secondary)]">
            Upload a photo of your handwritten notes and they will be read and converted.
          </p>
          <HandwrittenUpload selectedSubject={selectedSubject} onUploadSuccess={loadPdfs} />
        </section>

        {/* Documents */}
        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-display text-base font-semibold text-[var(--text-primary)]">
              Your uploads
            </h2>
            <span className="text-sm tabular-nums text-[var(--text-secondary)]">
              {filteredPdfs.length} document{filteredPdfs.length !== 1 ? 's' : ''}
            </span>
          </div>

          {loadingPdfs ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4"
                  aria-hidden="true"
                >
                  <div className="mb-4 h-12 w-12 animate-pulse rounded-xl bg-[var(--bg-secondary)]" />
                  <div className="mb-3 h-4 w-3/4 animate-pulse rounded bg-[var(--bg-secondary)]" />
                  <div className="h-5 w-24 animate-pulse rounded bg-[var(--bg-secondary)]" />
                </div>
              ))}
              <span className="sr-only">Loading documents</span>
            </div>
          ) : filteredPdfs.length === 0 ? (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-6 py-12 text-center">
              <FileText className="mx-auto mb-3 h-8 w-8 text-[var(--text-muted)]" aria-hidden="true" />
              <p className="font-display text-base font-semibold text-[var(--text-primary)]">
                {searchQuery ? 'No documents match your search' : 'No documents yet'}
              </p>
              <p className="mt-1 text-sm text-[var(--text-secondary)]">
                {searchQuery
                  ? 'Try a different search term.'
                  : 'Upload your first PDF above to get started.'}
              </p>
            </div>
          ) : (
            <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredPdfs.map((pdf) => {
                const colors = subjectStyle(pdf.subject);
                const isReady = pdf.status === 'ready';
                return (
                  <li key={pdf.id}>
                    <div
                      onClick={() => handleChatClick(pdf)}
                      className={`group relative h-full rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4 transition-colors ${
                        isReady ? 'cursor-pointer hover:border-[var(--accent-green)]' : 'opacity-75'
                      }`}
                    >
                      {/* Actions. Visible on hover for pointer users, and always
                          present in the tab order for keyboard users. */}
                      <div className="absolute right-3 top-3 flex items-center gap-1 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
                        {isReady && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/chat?pdf=${pdf.id}`);
                            }}
                            aria-label={`Chat with ${pdf.name}`}
                            className="rounded-lg p-1.5 transition-colors hover:bg-[var(--accent-green-light)]"
                          >
                            <MessageSquare
                              className="h-4 w-4 text-[var(--accent-green-text)]"
                              aria-hidden="true"
                            />
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={(e) => handleDelete(pdf.id, e)}
                          disabled={deletingId === pdf.id}
                          aria-label={`Delete ${pdf.name}`}
                          className="rounded-lg p-1.5 transition-colors hover:bg-red-50"
                        >
                          {deletingId === pdf.id ? (
                            <Loader2 className="h-4 w-4 animate-spin text-red-700" aria-hidden="true" />
                          ) : (
                            <Trash2 className="h-4 w-4 text-red-700" aria-hidden="true" />
                          )}
                        </button>
                      </div>

                      <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--bg-secondary)]">
                        {pdf.status === 'processing' ? (
                          <Loader2
                            className="h-5 w-5 animate-spin text-[var(--text-secondary)]"
                            aria-hidden="true"
                          />
                        ) : (
                          <FileText className="h-5 w-5 text-[var(--text-secondary)]" aria-hidden="true" />
                        )}
                      </span>

                      <h3 className="mb-3 truncate pr-16 text-sm font-semibold text-[var(--text-primary)]">
                        {/* The title is the keyboard-reachable control for the
                            card. The wrapper stays clickable for pointer users,
                            so behaviour is unchanged. */}
                        {isReady ? (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/chat?pdf=${pdf.id}`);
                            }}
                            title={pdf.name}
                            className="block max-w-full truncate text-left hover:underline"
                          >
                            {pdf.name}
                          </button>
                        ) : (
                          <span title={pdf.name}>{pdf.name}</span>
                        )}
                      </h3>

                      <div className="flex items-center justify-between gap-2 text-xs">
                        <span
                          className={`rounded px-2 py-0.5 font-semibold ${colors.bg} ${colors.text}`}
                        >
                          {pdf.subject}
                        </span>
                        <div className="flex items-center gap-2">
                          {pdf.page_count ? (
                            <span className="tabular-nums text-[var(--text-muted)]">
                              {pdf.page_count} pages
                            </span>
                          ) : null}
                          <span
                            className={`rounded-full px-2 py-0.5 font-semibold ${
                              STATUS_STYLES[pdf.status] || STATUS_STYLES.error
                            }`}
                          >
                            {STATUS_LABELS[pdf.status] || 'Failed'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

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
