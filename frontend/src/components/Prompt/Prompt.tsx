import React, { useState, useRef, ChangeEvent, KeyboardEvent } from 'react';
import { FileAttachment } from '../../types';
import './Prompt.css';

interface PromptProps {
  onSend: (text: string, files: FileAttachment[]) => void;
}

const Prompt: React.FC<PromptProps> = ({ onSend }) => {
  const [text, setText] = useState<string>('');
  const [examFiles, setExamFiles] = useState<File[]>([]);
  const [solutionFiles, setSolutionFiles] = useState<File[]>([]);
  const examInputRef = useRef<HTMLInputElement>(null);
  const solutionInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleExamFiles = (e: ChangeEvent<HTMLInputElement>): void => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      setExamFiles((prev) => [...prev, ...files]);
    }
    e.target.value = '';
  };

  const handleSolutionFiles = (e: ChangeEvent<HTMLInputElement>): void => {
    const files = Array.from(e.target.files || []);
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

  return (
    <div className="prompt-wrapper">
      <div className="prompt">
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
            <button
              className="action-btn exam-btn"
              onClick={() => examInputRef.current?.click()}
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
              className={`send-btn ${text.trim() || hasAttachments ? 'active' : ''}`}
              onClick={handleSubmit}
              disabled={!text.trim() && !hasAttachments}
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
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={handleExamFiles}
          style={{ display: 'none' }}
        />
        <input
          ref={solutionInputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={handleSolutionFiles}
          style={{ display: 'none' }}
        />
      </div>
    </div>
  );
};

export default Prompt;
