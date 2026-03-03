import React, { useState, useEffect } from 'react';
import { ChatMessageData, EvaluationResults } from '../../types';
import './ChatMessage.css';

interface ChatMessageProps {
  message: ChatMessageData;
  grouped?: boolean;
  groupIndex?: number;
}

/* ──────────────────── Evaluation Results Renderer ──────────────────── */
const EvaluationResultsView: React.FC<{ results: EvaluationResults }> = ({ results }) => {
  const { items, totalExams, successCount, averageScore, averageGrade, downloadAllUrl } = results;
  const isMultiple = totalExams > 1;
  const successItems = items.filter((it) => it.status === 'success');

  return (
    <div className="eval-results">
      {/* Part 1: Summary (only for multiple exams) */}
      {isMultiple && (
        <>
          <div className="eval-summary">
            <div className="eval-summary-title">✅ Alle Klausuren wurden erfolgreich korrigiert</div>
            <div className="eval-summary-stats">
              <div className="eval-stat">
                <span className="eval-stat-value">{successCount}/{totalExams}</span>
                <span className="eval-stat-label">Korrigiert</span>
              </div>
              <div className="eval-stat">
                <span className="eval-stat-value">{averageScore}%</span>
                <span className="eval-stat-label">Ø Punkte</span>
              </div>
              <div className="eval-stat">
                <span className="eval-stat-value">{averageGrade}</span>
                <span className="eval-stat-label">Ø Note</span>
              </div>
            </div>
          </div>
          <hr className="eval-divider" />
        </>
      )}

      {/* Part 2: Table with one row per exam */}
      <div className="eval-table-wrapper">
        <table className="eval-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Student</th>
              <th>Note</th>
              <th>Punkte</th>
              <th>PDF</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, index) => (
              <tr key={index} className={item.status !== 'success' ? 'eval-row-error' : ''}>
                <td className="eval-cell-num">{index + 1}</td>
                <td className="eval-cell-name">
                  {item.status === 'success' ? item.student_name : item.filename}
                </td>
                <td className="eval-cell-grade">
                  {item.status === 'success' ? (
                    <span className={`grade-badge grade-${gradeClass(item.overall_grade)}`}>
                      {item.overall_grade}
                    </span>
                  ) : (
                    <span className="grade-badge grade-error">Fehler</span>
                  )}
                </td>
                <td className="eval-cell-points">
                  {item.status === 'success'
                    ? `${item.total_points}/${item.max_points}`
                    : '–'}
                </td>
                <td className="eval-cell-download">
                  {item.status === 'success' ? (
                    <a
                      href={item.downloadUrl}
                      className="eval-download-icon"
                      download
                      target="_blank"
                      rel="noopener noreferrer"
                      title="Bewertung als PDF herunterladen"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="7 10 12 15 17 10" />
                        <line x1="12" y1="15" x2="12" y2="3" />
                      </svg>
                    </a>
                  ) : (
                    <span className="eval-no-download">–</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Part 3: Download all (only for multiple exams) */}
      {isMultiple && downloadAllUrl && (
        <>
          <hr className="eval-divider" />
          <div className="eval-download-all-section">
            <p className="eval-download-all-hint">Alle korrigierten Klausuren in einem Archiv herunterladen:</p>
            <a
              href={downloadAllUrl}
              className="eval-download-all-btn"
              download
              target="_blank"
              rel="noopener noreferrer"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              📦 Alle Bewertungen als ZIP herunterladen
            </a>
          </div>
        </>
      )}
    </div>
  );
};

/** Map a German grade to a CSS class for coloring */
function gradeClass(grade: string): string {
  const num = parseFloat(grade);
  if (isNaN(num)) return 'neutral';
  if (num <= 1.5) return 'excellent';
  if (num <= 2.5) return 'good';
  if (num <= 3.5) return 'ok';
  if (num <= 4.0) return 'pass';
  return 'fail';
}

/* ──────────────────── Chat Message Component ──────────────────── */
const ChatMessage: React.FC<ChatMessageProps> = ({ message, grouped = false, groupIndex }) => {
  const isBot = message.sender === 'bot';
  const shouldAnimate = isBot && message.isNew === true && !message.evaluationResults;
  const [displayedText, setDisplayedText] = useState<string>(shouldAnimate ? '' : message.text);
  const [isStreaming, setIsStreaming] = useState<boolean>(shouldAnimate);

  useEffect(() => {
    if (!shouldAnimate) {
      setDisplayedText(message.text);
      setIsStreaming(false);
      return;
    }

    let index = 0;
    setDisplayedText('');
    setIsStreaming(true);

    const interval = setInterval(() => {
      index++;
      if (index <= message.text.length) {
        setDisplayedText(message.text.slice(0, index));
      } else {
        setIsStreaming(false);
        clearInterval(interval);
      }
    }, 15);

    return () => clearInterval(interval);
  }, [message.text, shouldAnimate]);

  // When rendered inside a grouped container, skip the outer wrapper
  if (grouped) {
    return (
      <div className="grouped-message-item">
        <div className={`message-text ${message.isError ? 'error-message' : ''}`}>
          {message.evaluationResults ? (
            <EvaluationResultsView results={message.evaluationResults} />
          ) : (
            <>
              {displayedText}
              {isStreaming && <span className="streaming-cursor" />}
            </>
          )}
        </div>
        {renderDownloadButton(message)}
        {renderFiles(message)}
      </div>
    );
  }

  const animationClass = message.isNew !== false ? '' : 'no-animate';

  return (
    <div className={`chat-message ${isBot ? 'bot' : 'user'} ${animationClass}`}>
      <div className="message-avatar">
        {isBot ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="10" rx="2" />
            <circle cx="12" cy="5" r="2" />
            <path d="M12 7v4" />
            <line x1="8" y1="16" x2="8" y2="16" />
            <line x1="16" y1="16" x2="16" y2="16" />
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        )}
      </div>
      <div className="message-content">
        <div className={`message-text ${message.isError ? 'error-message' : ''}`}>
          {message.evaluationResults ? (
            <EvaluationResultsView results={message.evaluationResults} />
          ) : (
            <>
              {displayedText}
              {isStreaming && <span className="streaming-cursor" />}
            </>
          )}
        </div>
        {renderDownloadButton(message)}
        {renderFiles(message)}
      </div>
    </div>
  );
};

function renderDownloadButton(message: ChatMessageData) {
  if (!message.downloadUrl) return null;
  return (
    <a
      href={message.downloadUrl}
      className="download-button"
      download
      target="_blank"
      rel="noopener noreferrer"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="7 10 12 15 17 10" />
        <line x1="12" y1="15" x2="12" y2="3" />
      </svg>
      {message.downloadLabel || 'PDF herunterladen'}
    </a>
  );
}

function renderFiles(message: ChatMessageData) {
  if (!message.files || message.files.length === 0) return null;
  return (
    <div className="message-files">
      {message.files.map((file, index) => (
        <div key={index} className="file-tag">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          <span>{file.name}</span>
        </div>
      ))}
    </div>
  );
}

export default ChatMessage;
