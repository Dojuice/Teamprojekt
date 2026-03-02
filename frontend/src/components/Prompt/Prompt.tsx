import React, { useState, useRef, ChangeEvent, KeyboardEvent, DragEvent } from 'react';
import { FileAttachment, UploadProgress, AIModel, AIModelOption } from '../../types';
import './Prompt.css';

const MODEL_OPTIONS: AIModelOption[] = [
  { id: 'google/gemini-3-flash-preview', label: 'Gemini 3 Flash', description: 'Google – günstig', free: false },
  { id: 'google/gemini-3.1-pro-preview', label: 'Gemini 3.1 Pro', description: 'Google – leistungsstark', free: false },
  { id: 'openai/gpt-5.3-codex', label: 'GPT-5.3 Codex', description: 'OpenAI – neuestes Modell', free: false },
  { id: 'openai/gpt-5.2-codex', label: 'GPT-5.2 Codex', description: 'OpenAI', free: false },
  { id: 'openai/gpt-5.2', label: 'GPT-5.2 Thinking', description: 'OpenAI', free: false },
  { id: 'anthropic/claude-sonnet-4.6', label: 'Claude Sonnet 4.6', description: 'Anthropic', free: false },
  { id: 'anthropic/claude-opus-4.6', label: 'Claude Opus 4.6', description: 'Anthropic – stärkstes Modell', free: false },
];

interface PromptProps {
  onSend: (text: string, files: FileAttachment[]) => void;
  uploadProgress?: UploadProgress | null;
  selectedModel: AIModel;
  onModelChange: (model: AIModel) => void;
}

const Prompt: React.FC<PromptProps> = ({ onSend, uploadProgress, selectedModel, onModelChange }) => {
  const [text, setText] = useState<string>('');
  const [examFiles, setExamFiles] = useState<File[]>([]);
  const [solutionFiles, setSolutionFiles] = useState<File[]>([]);
  const examInputRef = useRef<HTMLInputElement>(null);
  const examFolderInputRef = useRef<HTMLInputElement>(null);
  const solutionInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const dragCounterRef = useRef(0);
  const [showExamMenu, setShowExamMenu] = useState(false);
  const examMenuRef = useRef<HTMLDivElement>(null);
  const [showModelMenu, setShowModelMenu] = useState(false);
  const modelMenuRef = useRef<HTMLDivElement>(null);

  const validateFiles = (files: File[]): File[] => {
    return files.filter((f) => {
      const ext = f.name.toLowerCase().split('.').pop();
      return ext === 'pdf';
    });
  };

  const handleExamFiles = (e: ChangeEvent<HTMLInputElement>): void => {
    const files = validateFiles(Array.from(e.target.files || []));
    if (files.length > 0) {
      setExamFiles((prev) => [...prev, ...files]);
    }
    e.target.value = '';
  };

  const handleExamFolder = (e: ChangeEvent<HTMLInputElement>): void => {
    const files = validateFiles(Array.from(e.target.files || []));
    if (files.length > 0) {
      setExamFiles((prev) => [...prev, ...files]);
    }
    e.target.value = '';
  };

  const handleSolutionFiles = (e: ChangeEvent<HTMLInputElement>): void => {
    const files = validateFiles(Array.from(e.target.files || []));
    if (files.length > 0) {
      setSolutionFiles((prev) => [...prev, ...files]);
    }
    e.target.value = '';
  };

  const removeExamFile = (index: number): void => {
    setExamFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const removeSolutionFile = (index: number): void => {
    setSolutionFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = (): void => {
    if (!text.trim() && examFiles.length === 0 && solutionFiles.length === 0) return;

    const allFiles: FileAttachment[] = [
      ...examFiles.map((f) => ({ name: f.name, type: 'exam' as const, file: f })),
      ...solutionFiles.map((f) => ({ name: f.name, type: 'solution' as const, file: f })),
    ];

    onSend(text.trim(), allFiles);
    setText('');
    setExamFiles([]);
    setSolutionFiles([]);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>): void => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleTextChange = (e: ChangeEvent<HTMLTextAreaElement>): void => {
    setText(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
  };

  const hasAttachments = examFiles.length > 0 || solutionFiles.length > 0;

  // Drag & Drop handlers
  const handleDragEnter = (e: DragEvent<HTMLDivElement>): void => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current++;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>): void => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) {
      setIsDragging(false);
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>): void => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>): void => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    dragCounterRef.current = 0;

    const droppedFiles = Array.from(e.dataTransfer.files);
    const pdfFiles = validateFiles(droppedFiles);
    if (pdfFiles.length > 0) {
      // Default to exam type for drag & drop
      setExamFiles((prev) => [...prev, ...pdfFiles]);
    }
  };

  const isUploading = uploadProgress?.status === 'uploading';

  // Close exam menu when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (examMenuRef.current && !examMenuRef.current.contains(e.target as Node)) {
        setShowExamMenu(false);
      }
    };
    if (showExamMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showExamMenu]);

  // Close model menu when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modelMenuRef.current && !modelMenuRef.current.contains(e.target as Node)) {
        setShowModelMenu(false);
      }
    };
    if (showModelMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showModelMenu]);

  const currentModel = MODEL_OPTIONS.find((m) => m.id === selectedModel) || MODEL_OPTIONS[0];

  return (
    <div
      className={`prompt-wrapper ${isDragging ? 'dragging' : ''}`}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {isDragging && (
        <div className="drag-overlay">
          <div className="drag-overlay-content">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span>PDF-Dateien hier ablegen</span>
          </div>
        </div>
      )}

      {/* Upload progress bar */}
      {uploadProgress && (
        <div className={`upload-progress ${uploadProgress.status}`}>
          <div className="upload-progress-bar">
            <div
              className="upload-progress-fill"
              style={{
                width: uploadProgress.total > 0
                  ? `${(uploadProgress.uploaded / uploadProgress.total) * 100}%`
                  : '0%',
              }}
            />
          </div>
          <div className="upload-progress-text">
            {uploadProgress.status === 'uploading' && (
              <>
                <span className="upload-spinner" />
                Lade hoch: {uploadProgress.currentFile}
              </>
            )}
            {uploadProgress.status === 'done' && (
              <>✅ {uploadProgress.uploaded} von {uploadProgress.total} Dateien hochgeladen</>
            )}
            {uploadProgress.status === 'error' && (
              <>⚠️ {uploadProgress.uploaded} von {uploadProgress.total} Dateien hochgeladen (Fehler aufgetreten)</>
            )}
          </div>
        </div>
      )}

      <div className="prompt">
        {/* Model selector */}
        <div className="model-selector-row">
          <div className="model-selector-wrapper" ref={modelMenuRef}>
            <button
              className="model-selector-btn"
              onClick={() => setShowModelMenu((v) => !v)}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3" />
                <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
              </svg>
              <span>{currentModel.label}</span>
              {currentModel.free && <span className="model-badge free">Kostenlos</span>}
              <svg className="model-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>
            {showModelMenu && (
              <div className="model-dropdown">
                {MODEL_OPTIONS.map((option) => (
                  <button
                    key={option.id}
                    className={`model-dropdown-item ${selectedModel === option.id ? 'active' : ''}`}
                    onClick={() => {
                      onModelChange(option.id);
                      setShowModelMenu(false);
                    }}
                  >
                    <div className="model-dropdown-item-info">
                      <span className="model-dropdown-item-label">
                        {option.label}
                        {option.free && <span className="model-badge free">Kostenlos</span>}
                      </span>
                      <span className="model-dropdown-item-desc">{option.description}</span>
                    </div>
                    {selectedModel === option.id && (
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Attached files preview */}
        {hasAttachments && (
          <div className="prompt-attachments">
            {examFiles.map((file, index) => (
              <div key={`exam-${index}`} className="attachment-chip exam">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                <span className="attachment-name">{file.name}</span>
                <button className="attachment-remove" onClick={() => removeExamFile(index)} title="Entfernen">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            ))}
            {solutionFiles.map((file, index) => (
              <div key={`sol-${index}`} className="attachment-chip solution">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 11l3 3L22 4" />
                  <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
                </svg>
                <span className="attachment-name">{file.name}</span>
                <button className="attachment-remove" onClick={() => removeSolutionFile(index)} title="Entfernen">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Input row */}
        <div className="prompt-input-row">
          {/* Text input */}
          <textarea
            ref={textareaRef}
            className="prompt-textarea"
            placeholder="Nachricht eingeben..."
            value={text}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            rows={1}
          />

          {/* Right-side action buttons */}
          <div className="prompt-actions">
            <div className="exam-btn-wrapper" ref={examMenuRef}>
              <button
                className="action-btn exam-btn"
                onClick={() => setShowExamMenu((v) => !v)}
              >
                <span className="tooltip">Klausuren hochladen</span>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="12" y1="18" x2="12" y2="12" />
                  <line x1="9" y1="15" x2="12" y2="12" />
                  <line x1="15" y1="15" x2="12" y2="12" />
                </svg>
              </button>
              {showExamMenu && (
                <div className="exam-dropdown">
                  <button
                    className="exam-dropdown-item"
                    onClick={() => {
                      setShowExamMenu(false);
                      examInputRef.current?.click();
                    }}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>
                    Dateien auswählen
                  </button>
                  <button
                    className="exam-dropdown-item"
                    onClick={() => {
                      setShowExamMenu(false);
                      examFolderInputRef.current?.click();
                    }}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                    </svg>
                    Ordner auswählen
                  </button>
                </div>
              )}
            </div>
            <button
              className="action-btn solution-btn"
              onClick={() => solutionInputRef.current?.click()}
            >
              <span className="tooltip">Musterlösungen hochladen</span>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 11l3 3L22 4" />
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
              </svg>
            </button>

            {/* Send button */}
            <button
              className={`send-btn ${(text.trim() || hasAttachments) && !isUploading ? 'active' : ''}`}
              onClick={handleSubmit}
              disabled={(!text.trim() && !hasAttachments) || isUploading}
              title="Senden"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>

        {/* Hidden file inputs */}
        <input
          ref={examInputRef}
          type="file"
          multiple
          accept=".pdf"
          onChange={handleExamFiles}
          style={{ display: 'none' }}
        />
        <input
          ref={examFolderInputRef}
          type="file"
          accept=".pdf"
          onChange={handleExamFolder}
          style={{ display: 'none' }}
          {...({ webkitdirectory: '', directory: '' } as any)}
        />
        <input
          ref={solutionInputRef}
          type="file"
          multiple
          accept=".pdf"
          onChange={handleSolutionFiles}
          style={{ display: 'none' }}
        />
      </div>
    </div>
  );
};

export default Prompt;
