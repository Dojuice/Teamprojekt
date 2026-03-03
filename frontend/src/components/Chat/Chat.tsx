import React, { useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import { ChatMessageData, EvalProgress } from '../../types';
import './Chat.css';

interface ChatProps {
  messages: ChatMessageData[];
  isBotTyping?: boolean;
  evalProgress?: EvalProgress | null;
}

interface MessageGroup {
  sender: 'bot' | 'user';
  messages: ChatMessageData[];
}

const Chat: React.FC<ChatProps> = ({ messages, isBotTyping = false, evalProgress = null }) => {
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isBotTyping, evalProgress]);

  // Group consecutive messages from the same sender
  const groups: MessageGroup[] = [];
  for (const msg of messages) {
    const lastGroup = groups[groups.length - 1];
    if (lastGroup && lastGroup.sender === msg.sender) {
      lastGroup.messages.push(msg);
    } else {
      groups.push({ sender: msg.sender, messages: [msg] });
    }
  }

  return (
    <div className="chat">
      <div className="chat-messages">
        {groups.map((group) => {
          if (group.sender === 'user') {
            // Render each user message individually
            return group.messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ));
          }
          // Bot messages: group consecutive ones in a single container
          if (group.messages.length === 1) {
            return <ChatMessage key={group.messages[0].id} message={group.messages[0]} />;
          }
          return (
            <div key={group.messages[0].id} className="chat-message bot grouped">
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
                {group.messages.map((message, idx) => (
                  <ChatMessage key={message.id} message={message} grouped groupIndex={idx} />
                ))}
              </div>
            </div>
          );
        })}

        {/* Evaluation progress indicator */}
        {evalProgress && (
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
              <div className="message-text eval-progress-box">
                <div className="eval-progress-label">
                  <span className="eval-spinner" />
                  {evalProgress.label}
                </div>
                {evalProgress.total > 0 && (
                  <div className="eval-progress-bar-wrapper">
                    <div className="eval-progress-bar">
                      <div
                        className="eval-progress-fill"
                        style={{
                          width: `${(evalProgress.current / evalProgress.total) * 100}%`,
                        }}
                      />
                    </div>
                    <span className="eval-progress-count">
                      {evalProgress.current}/{evalProgress.total}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

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
