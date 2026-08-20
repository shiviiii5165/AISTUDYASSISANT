import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, ImagePlus, Loader2, CheckCircle2, FileText, X } from 'lucide-react';
import { uploadHandwrittenNote } from '../../lib/api';
import UpgradeModal from '../billing/UpgradeModal';

interface HandwrittenUploadProps {
  selectedSubject: string;
  onUploadSuccess?: () => void;
}

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/heic'];

const HandwrittenUpload: React.FC<HandwrittenUploadProps> = ({ selectedSubject, onUploadSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ noteId: string; extractedText: string; totalChunks: number } | null>(null);
  const [error, setError] = useState('');
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgradeMessage, setUpgradeMessage] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!ACCEPTED_TYPES.includes(file.type)) {
      setError('Please select a JPG, PNG, WEBP, or HEIC image.');
      return;
    }

    setError('');
    setSelectedFile(file);
    setResult(null);

    // Create preview
    const reader = new FileReader();
    reader.onload = (ev) => setPreview(ev.target?.result as string);
    reader.readAsDataURL(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setError('');

    try {
      const response = await uploadHandwrittenNote(selectedFile, selectedSubject);
      setResult({
        noteId: response.noteId,
        extractedText: response.extractedText,
        totalChunks: response.totalChunks,
      });
      onUploadSuccess?.();
    } catch (err: any) {
      console.error('Upload error:', err);
      if (err.response?.status === 403 && err.response?.data?.detail?.error) {
        setUpgradeMessage(err.response.data.detail.message);
        setShowUpgradeModal(true);
        setError('');
      } else {
        const serverError = err.response?.data?.detail;
        const fallback = err.message || 'Failed to process image. Please try again.';
        setError(serverError || `Error: ${fallback}`);
      }
    } finally {
      setUploading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreview(null);
    setResult(null);
    setError('');
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (cameraInputRef.current) cameraInputRef.current.value = '';
  };

  const handleStartChatting = () => {
    if (result) {
      navigate(`/chat?pdf=${result.noteId}`);
    }
  };

  return (
    <div className="space-y-4">
      {/* Hidden file inputs */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/heic"
        className="hidden"
        onChange={handleFileSelect}
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleFileSelect}
      />

      {!selectedFile && !result && (
        /* Upload buttons */
        <div className="border-2 border-dashed border-[var(--border)] rounded-2xl p-8 text-center hover:border-[var(--accent-indigo)] transition-colors">
          <div className="mx-auto w-14 h-14 bg-indigo-100 rounded-2xl flex items-center justify-center mb-4">
            <FileText className="w-7 h-7 text-[var(--accent-indigo)]" />
          </div>
          <h3 className="text-lg font-bold mb-1 text-[var(--text-primary)]">
            Upload Handwritten Notes
          </h3>
          <p className="text-[var(--text-secondary)] text-sm mb-5">
            Take a photo or upload an image of your handwritten notes
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-2 px-5 py-2.5 bg-[var(--accent-indigo)] text-white rounded-xl font-semibold text-sm hover:bg-indigo-700 transition-colors shadow-sm"
            >
              <ImagePlus className="w-4 h-4" />
              Upload Photo
            </button>
            <button
              onClick={() => cameraInputRef.current?.click()}
              className="flex items-center gap-2 px-5 py-2.5 bg-white border border-[var(--border)] text-[var(--text-primary)] rounded-xl font-semibold text-sm hover:bg-[var(--bg-hover)] transition-colors shadow-sm"
            >
              <Camera className="w-4 h-4" />
              Use Camera
            </button>
          </div>
          <p className="text-xs text-[var(--text-muted)] mt-3">
            Supports JPG, PNG, WEBP, HEIC
          </p>
        </div>
      )}

      {/* Image Preview & Upload */}
      {selectedFile && !result && (
        <div className="border border-[var(--border)] rounded-2xl p-5 bg-white shadow-sm">
          <div className="flex items-start gap-4">
            {preview && (
              <div className="relative shrink-0">
                <img
                  src={preview}
                  alt="Preview"
                  className="w-32 h-32 object-cover rounded-xl border border-[var(--border)]"
                />
                {!uploading && (
                  <button
                    onClick={handleReset}
                    className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition-colors shadow-sm"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <h4 className="font-bold text-[var(--text-primary)] truncate">{selectedFile.name}</h4>
              <p className="text-sm text-[var(--text-secondary)] mt-0.5">
                {(selectedFile.size / 1024).toFixed(0)} KB • {selectedSubject}
              </p>

              {uploading ? (
                <div className="flex items-center gap-2 mt-4 px-4 py-2.5 bg-indigo-50 rounded-xl">
                  <Loader2 className="w-4 h-4 text-[var(--accent-indigo)] animate-spin" />
                  <span className="text-sm font-medium text-[var(--accent-indigo)]">
                    Reading your handwriting...
                  </span>
                </div>
              ) : (
                <button
                  onClick={handleUpload}
                  className="mt-4 px-5 py-2.5 bg-[var(--accent-indigo)] text-white rounded-xl font-semibold text-sm hover:bg-indigo-700 transition-colors shadow-sm"
                >
                  Process Notes
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Success State */}
      {result && (
        <div className="border border-green-200 bg-green-50 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="w-5 h-5 text-green-600" />
            <h4 className="font-bold text-green-800">Notes Processed Successfully!</h4>
          </div>
          <p className="text-sm text-green-700 mb-1">
            Extracted {result.totalChunks} chunks from your handwriting.
          </p>
          <div className="bg-white border border-green-200 rounded-xl p-3 mt-3 mb-4">
            <p className="text-xs font-semibold text-[var(--text-muted)] mb-1">Extracted Text Preview:</p>
            <p className="text-sm text-[var(--text-primary)] leading-relaxed">
              {result.extractedText.slice(0, 300)}
              {result.extractedText.length > 300 ? '...' : ''}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleStartChatting}
              className="px-5 py-2.5 bg-[var(--accent-green)] text-white rounded-xl font-semibold text-sm hover:bg-green-700 transition-colors shadow-sm"
            >
              Looks good — Start Chatting
            </button>
            <button
              onClick={handleReset}
              className="px-4 py-2.5 text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            >
              Upload Another
            </button>
          </div>
        </div>
      )}

      {error && (
        <p className="text-[var(--accent-red)] text-sm font-medium px-1">{error}</p>
      )}
      <UpgradeModal 
        isOpen={showUpgradeModal} 
        onClose={() => setShowUpgradeModal(false)} 
        message={upgradeMessage} 
      />
    </div>
  );
};

export default HandwrittenUpload;
