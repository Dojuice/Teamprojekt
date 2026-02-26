import React, { useState, useCallback, useEffect } from 'react';
import Header from './components/Header/Header';
import Sidebar from './components/Sidebar/Sidebar';
import Chat from './components/Chat/Chat';
import Prompt from './components/Prompt/Prompt';
import { ChatMessageData, FileAttachment, ChatSummary } from './types';
import './App.css';

const API_URL: string = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const App: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [chatList, setChatList] = useState<ChatSummary[]>([]);
  const [activeChatId, setActiveChatId] = useState<number | null>(null);

  // Load welcome message for a fresh (unsaved) state
  const loadWelcome = useCallback(() => {
    fetch(`${API_URL}/api/welcome`)
      .then((res) => res.json())
      .then((data: { message: string }) => {
        setMessages([
          { id: Date.now(), sender: 'bot', text: data.message, files: [] },
        ]);
      })
      .catch(() => {
        setMessages([
          {
            id: Date.now(),
            sender: 'bot',
            text: "Hello! 👋\n\nI'm AutoExam, your AI-powered exam correction assistant.\n\nUse the buttons in the input bar to upload exams and solutions, then send a message to begin!",
            files: [],
          },
        ]);
      });
  }, []);

  // Initial load
  useEffect(() => {
    loadWelcome();
    fetchChatList();
  }, [loadWelcome]);

  // Fetch all chats for sidebar
  const fetchChatList = async () => {
    try {
      const res = await fetch(`${API_URL}/api/chats`);
      if (res.ok) {
        const data: ChatSummary[] = await res.json();
        setChatList(data);
      }
    } catch {
      // silently fail
    }
  };

  // Create a new chat in DB (or start fresh if no messages yet)
  const ensureChat = useCallback(async (): Promise<number> => {
    if (activeChatId) return activeChatId;
    try {
      const res = await fetch(`${API_URL}/api/chats`, { method: 'POST' });
      const chat: ChatSummary = await res.json();
      setActiveChatId(chat.id);
      fetchChatList();
      return chat.id;
    } catch {
      return -1;
    }
  }, [activeChatId]);

  // Persist a message to the DB
  const persistMessage = async (chatId: number, sender: string, text: string) => {
    try {
      await fetch(`${API_URL}/api/chats/${chatId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sender, text }),
      });
      // Refresh sidebar to pick up auto-title
      fetchChatList();
    } catch {
      // silently fail
    }
  };

  // Select an existing chat
  const handleSelectChat = async (id: number) => {
    try {
      const res = await fetch(`${API_URL}/api/chats/${id}`);
      if (res.ok) {
        const data = await res.json();
        const msgs: ChatMessageData[] = data.messages.map((m: any) => ({
          id: m.id,
          sender: m.sender as 'bot' | 'user',
          text: m.text,
          files: [],
        }));
        setMessages(msgs);
        setActiveChatId(id);
        setSidebarOpen(false);
      }
    } catch {
      // silently fail
    }
  };

  // New chat
  const handleNewChat = () => {
    setActiveChatId(null);
    loadWelcome();
    setSidebarOpen(false);
  };

  // Delete a chat
  const handleDeleteChat = async (id: number) => {
    try {
      await fetch(`${API_URL}/api/chats/${id}`, { method: 'DELETE' });
      setChatList((prev) => prev.filter((c) => c.id !== id));
      if (activeChatId === id) {
        setActiveChatId(null);
        loadWelcome();
      }
    } catch {
      // silently fail
    }
  };

  const handleSend = useCallback(
    async (text: string, files: FileAttachment[]) => {
      const userText = text || (files.length > 0 ? 'Dateien hochgeladen' : '');
      const userMessage: ChatMessageData = {
        id: Date.now(),
        sender: 'user',
        text: userText,
        files,
        streaming: false,
      };

      setMessages((prev) => [...prev, userMessage]);

      // Ensure chat exists in DB
      const chatId = await ensureChat();
      if (chatId > 0) {
        await persistMessage(chatId, 'user', userText);
      }

      // Simulate bot response
      setTimeout(async () => {
        const botText =
          'Vielen Dank! Ich habe Ihre Nachricht erhalten. Die Verarbeitung wird in Kürze implementiert.';
        const botMessage: ChatMessageData = {
          id: Date.now() + 1,
          sender: 'bot',
          text: botText,
          files: [],
        };
        setMessages((prev) => [...prev, botMessage]);
        if (chatId > 0) {
          await persistMessage(chatId, 'bot', botText);
        }
      }, 800);
    },
    [ensureChat]
  );

  return (
    <div className="app">
      <Sidebar
        open={sidebarOpen}
        chats={chatList}
        activeChatId={activeChatId}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        onClose={() => setSidebarOpen(false)}
      />
      <Header onToggleSidebar={() => setSidebarOpen((v) => !v)} />
      <Chat messages={messages} />
      <Prompt onSend={handleSend} />
    </div>
  );
};

export default App;
