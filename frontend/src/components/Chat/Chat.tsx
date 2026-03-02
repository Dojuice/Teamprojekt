import React, { useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import { ChatMessageData } from '../../types';
import './Chat.css';

interface ChatProps {
  messages: ChatMessageData[];
  isBotTyping?: boolean;
}

const Chat: React.FC<ChatProps> = ({ messages, isBotTyping = false }) => {
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isBotTyping]);

  return (
    <div className="chat">
      <div className="chat-messages">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        {isBotTyping && (
          <div className="chat-message bot">
            <div className="message-avatar">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="10" rx="2" />
                <circle cx="12" cy="5" r="2" />
                <path d="M12 7v4" />
                <line x1="8" y1="16" x2="8" y2="16" />
                <line x1="16" y1="16" x2="16" y2="16" />
              </svg>
            </div>
            <div className="message-content">
              <span className="message-sender">AutoExam</span>
              <div className="message-text typing-indicator">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>
    </div>
  );
};

export default Chat;
