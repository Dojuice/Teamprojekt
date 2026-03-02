import React, { useState, useEffect } from 'react';
import { ChatMessageData } from '../../types';
import './ChatMessage.css';

interface ChatMessageProps {
  message: ChatMessageData;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isBot = message.sender === 'bot';
  const shouldStream = isBot && message.streaming === true;
  const [displayedText, setDisplayedText] = useState<string>(
    shouldStream ? '' : message.text
  );
  const [isStreaming, setIsStreaming] = useState<boolean>(shouldStream);

  useEffect(() => {
    if (!shouldStream) {
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
  }, [message.text, shouldStream]);

  return (
    <div className={`chat-message ${isBot ? 'bot' : 'user'}`}>
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
          {displayedText}
          {isStreaming && <span className="streaming-cursor" />}
        </div>
        {message.downloadUrl && (
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
        )}
        {message.files && message.files.length > 0 && (
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
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
