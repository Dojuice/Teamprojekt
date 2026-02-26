import React, { useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import { ChatMessageData } from '../../types';
import './Chat.css';

interface ChatProps {
  messages: ChatMessageData[];
}

const Chat: React.FC<ChatProps> = ({ messages }) => {
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="chat">
      <div className="chat-messages">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        <div ref={chatEndRef} />
      </div>
    </div>
  );
};

export default Chat;
