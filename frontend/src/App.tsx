import React, { useState, useCallback, useEffect } from 'react';
import Header from './components/Header/Header';
import Sidebar from './components/Sidebar/Sidebar';
import Chat from './components/Chat/Chat';
import Prompt from './components/Prompt/Prompt';
import { ChatMessageData, FileAttachment, ChatSummary, UploadProgress, AIModel } from './types';
import './App.css';

const API_URL: string = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const App: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [chatList, setChatList] = useState<ChatSummary[]>([]);
  const [activeChatId, setActiveChatId] = useState<number | null>(null);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [isBotTyping, setIsBotTyping] = useState(false);
  const [selectedModel, setSelectedModel] = useState<AIModel>('google/gemini-3-flash-preview');

  // Load welcome message for a fresh (unsaved) state
  const loadWelcome = useCallback(() => {
    fetch(`${API_URL}/api/welcome`)
      .then((res) => res.json())
      .then((data: { message: string }) => {
        setMessages([
          { id: Date.now(), sender: 'bot', text: data.message, files: [], streaming: false },
        ]);
      })
      .catch(() => {
        setMessages([
          {
            id: Date.now(),
            sender: 'bot',
            text: "Hello! \uD83D\uDC4B\n\nI'm AutoExam, your AI-powered exam correction assistant.\n\nUse the buttons in the input bar to upload exams and solutions, then send a message to begin!",
            files: [],
            streaming: false,
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
          streaming: false,
        }));
        setMessages(msgs);
        setActiveChatId(id);
      }
    } catch {
      // silently fail
    }
  };

  // New chat
  const handleNewChat = () => {
    setActiveChatId(null);
    loadWelcome();
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

  // Rename a chat
  const handleRenameChat = async (id: number, newTitle: string) => {
    try {
      const res = await fetch(`${API_URL}/api/chats/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle }),
      });
      if (res.ok) {
        setChatList((prev) =>
          prev.map((c) => (c.id === id ? { ...c, title: newTitle } : c))
        );
      }
    } catch {
      // silently fail
    }
  };

  // Upload files to backend
  const uploadFiles = async (chatId: number, files: FileAttachment[]): Promise<string[]> => {
    const errors: string[] = [];
    const examFiles = files.filter((f) => f.type === 'exam');
    const solutionFiles = files.filter((f) => f.type === 'solution');
    let uploaded = 0;
    const total = files.length;

    const uploadBatch = async (batch: FileAttachment[], fileType: string) => {
      if (batch.length === 0) return;
      const formData = new FormData();
      batch.forEach((f) => formData.append('files', f.file));

      setUploadProgress({
        total,
        uploaded,
        currentFile: batch.map((f) => f.name).join(', '),
        status: 'uploading',
        errors: [],
      });

      try {
        const res = await fetch(
          `${API_URL}/api/chats/${chatId}/upload?file_type=${fileType}`,
          { method: 'POST', body: formData }
        );
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: 'Upload fehlgeschlagen' }));
          errors.push(err.detail || 'Upload fehlgeschlagen');
        } else {
          const data = await res.json();
          if (data.errors && data.errors.length > 0) {
            errors.push(...data.errors);
          }
          uploaded += data.successful || 0;
        }
      } catch {
        errors.push(`Upload fehlgeschlagen für ${fileType}-Dateien`);
      }
    };

    await uploadBatch(examFiles, 'exam');
    await uploadBatch(solutionFiles, 'solution');

    setUploadProgress({
      total,
      uploaded,
      currentFile: '',
      status: errors.length > 0 ? 'error' : 'done',
      errors,
    });

    // Clear progress after a delay
    setTimeout(() => setUploadProgress(null), 3000);

    return errors;
  };

  const handleSend = useCallback(
    async (text: string, files: FileAttachment[]) => {
      // Helper: append text to last bot message (compacts consecutive bot messages)
      const appendBotText = (newText: string, opts?: { isError?: boolean }) => {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.sender === 'bot' && !last.downloadUrl) {
            // Append to existing bot message
            return prev.map((m, i) =>
              i === prev.length - 1
                ? { ...m, text: m.text + '\n\n' + newText, isError: m.isError || opts?.isError, streaming: false }
                : m
            );
          }
          // Create new bot message
          return [
            ...prev,
            {
              id: Date.now() + Math.random(),
              sender: 'bot' as const,
              text: newText,
              files: [],
              isError: opts?.isError,
              streaming: false,
            },
          ];
        });
      };

      // Helper: add a new bot message (always separate, e.g. for download buttons)
      const addBotMessage = (msg: Partial<ChatMessageData> & { text: string }) => {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now() + Math.random(),
            sender: 'bot' as const,
            files: [],
            streaming: false,
            ...msg,
          },
        ]);
      };

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
      if (chatId <= 0) {
        appendBotText('❌ Fehler: Chat konnte nicht erstellt werden. Bitte versuchen Sie es erneut.', { isError: true });
        return;
      }

      // Persist user message
      await persistMessage(chatId, 'user', userText);

      // Upload files if any
      let uploadErrors: string[] = [];
      if (files.length > 0) {
        uploadErrors = await uploadFiles(chatId, files);
      }

      // Show bot typing indicator
      setIsBotTyping(true);

      if (uploadErrors.length > 0) {
        // Report upload errors
        setIsBotTyping(false);
        const botText = `⚠️ Einige Dateien konnten nicht hochgeladen werden:\n\n${uploadErrors.map((e) => `• ${e}`).join('\n')}\n\nBitte stellen Sie sicher, dass nur PDF-Dateien hochgeladen werden.`;
        appendBotText(botText, { isError: true });
        await persistMessage(chatId, 'bot', botText);
        return;
      }

      if (files.length > 0) {
        // Acknowledge upload
        const examCount = files.filter((f) => f.type === 'exam').length;
        const solutionCount = files.filter((f) => f.type === 'solution').length;
        const parts: string[] = [];
        if (examCount > 0) parts.push(`${examCount} Klausur${examCount > 1 ? 'en' : ''}`);
        if (solutionCount > 0) parts.push(`${solutionCount} Musterlösung${solutionCount > 1 ? 'en' : ''}`);
        const ackText = `✅ ${parts.join(' und ')} erfolgreich hochgeladen!`;
        appendBotText(ackText);
        await persistMessage(chatId, 'bot', ackText);

        // If both exams and solutions are present, trigger evaluation
        if (examCount > 0 && solutionCount > 0) {
          const evalStartText = '🔄 Starte KI-Bewertung... Dies kann einen Moment dauern.';
          appendBotText(evalStartText);

          try {
            const evalRes = await fetch(
              `${API_URL}/api/chats/${chatId}/evaluate?additional_instructions=${encodeURIComponent(text)}&model=${encodeURIComponent(selectedModel)}`,
              { method: 'POST' }
            );

            setIsBotTyping(false);

            if (!evalRes.ok) {
              const errData = await evalRes.json().catch(() => ({ detail: 'Bewertung fehlgeschlagen' }));
              const errText = `❌ ${errData.detail || 'Bewertung fehlgeschlagen'}`;
              appendBotText(errText, { isError: true });
              await persistMessage(chatId, 'bot', errText);
            } else {
              const evalData = await evalRes.json();

              // Show results for each exam
              for (let i = 0; i < evalData.results.length; i++) {
                const result = evalData.results[i];
                const resultText = result.formatted_text || `❌ Fehler: ${result.error}`;

                if (result.status === 'success' && result.downloadUrl !== undefined || result.status === 'success') {
                  // Evaluation results with download buttons get their own message
                  addBotMessage({
                    text: resultText,
                    isError: false,
                    downloadUrl: `${API_URL}/api/chats/${chatId}/download/${i}`,
                    downloadLabel: '📄 Bewertung als PDF herunterladen',
                  });
                } else {
                  appendBotText(resultText, { isError: result.status !== 'success' });
                }
                await persistMessage(chatId, 'bot', resultText);
              }

              // Summary with batch download
              if (evalData.results.length > 1) {
                const successCount = evalData.successful;
                const summaryText = `📊 Bewertung abgeschlossen: ${successCount}/${evalData.total_exams} Klausuren erfolgreich bewertet.`;
                addBotMessage({
                  text: summaryText,
                  downloadUrl: `${API_URL}/api/chats/${chatId}/download-all`,
                  downloadLabel: '📦 Alle Bewertungen als ZIP herunterladen',
                });
                await persistMessage(chatId, 'bot', summaryText);
              }
            }
          } catch {
            setIsBotTyping(false);
            const errText = '❌ Verbindungsfehler bei der Bewertung. Bitte versuchen Sie es erneut.';
            appendBotText(errText, { isError: true });
            await persistMessage(chatId, 'bot', errText);
          }
          return;
        }

        // Only one type uploaded – remind user to upload the other
        setIsBotTyping(false);
        if (examCount > 0 && solutionCount === 0) {
          const hintText = '📎 Bitte laden Sie jetzt noch die Musterlösung hoch (grüner Button), dann starte ich die Bewertung.';
          appendBotText(hintText);
          await persistMessage(chatId, 'bot', hintText);
        } else if (solutionCount > 0 && examCount === 0) {
          const hintText = '📎 Bitte laden Sie jetzt noch die Klausuren hoch (blauer Button), dann starte ich die Bewertung.';
          appendBotText(hintText);
          await persistMessage(chatId, 'bot', hintText);
        }
        return;
      }

      // Text-only message – check if we can trigger evaluation
      try {
        const filesRes = await fetch(`${API_URL}/api/chats/${chatId}/files`);
        const chatFiles = await filesRes.json();
        const hasExams = chatFiles.exam && chatFiles.exam.length > 0;
        const hasSolutions = chatFiles.solution && chatFiles.solution.length > 0;

        if (hasExams && hasSolutions) {
          // Trigger evaluation with text as additional instructions
          const evalStartText = '🔄 Starte KI-Bewertung... Dies kann einen Moment dauern.';
          appendBotText(evalStartText);

          try {
            const evalRes = await fetch(
              `${API_URL}/api/chats/${chatId}/evaluate?additional_instructions=${encodeURIComponent(text)}&model=${encodeURIComponent(selectedModel)}`,
              { method: 'POST' }
            );

            setIsBotTyping(false);

            if (!evalRes.ok) {
              const errData = await evalRes.json().catch(() => ({ detail: 'Bewertung fehlgeschlagen' }));
              const errText = `❌ ${errData.detail || 'Bewertung fehlgeschlagen'}`;
              appendBotText(errText, { isError: true });
              await persistMessage(chatId, 'bot', errText);
            } else {
              const evalData = await evalRes.json();
              for (let i = 0; i < evalData.results.length; i++) {
                const result = evalData.results[i];
                const resultText = result.formatted_text || `❌ Fehler: ${result.error}`;

                if (result.status === 'success') {
                  addBotMessage({
                    text: resultText,
                    isError: false,
                    downloadUrl: `${API_URL}/api/chats/${chatId}/download/${i}`,
                    downloadLabel: '📄 Bewertung als PDF herunterladen',
                  });
                } else {
                  appendBotText(resultText, { isError: true });
                }
                await persistMessage(chatId, 'bot', resultText);
              }

              if (evalData.results.length > 1) {
                const summaryText = `📊 Bewertung abgeschlossen: ${evalData.successful}/${evalData.total_exams} Klausuren erfolgreich bewertet.`;
                addBotMessage({
                  text: summaryText,
                  downloadUrl: `${API_URL}/api/chats/${chatId}/download-all`,
                  downloadLabel: '📦 Alle Bewertungen als ZIP herunterladen',
                });
                await persistMessage(chatId, 'bot', summaryText);
              }
            }
          } catch {
            setIsBotTyping(false);
            const errText = '❌ Verbindungsfehler bei der Bewertung. Bitte versuchen Sie es erneut.';
            appendBotText(errText, { isError: true });
            await persistMessage(chatId, 'bot', errText);
          }
        } else {
          setIsBotTyping(false);
          let hintText: string;
          if (!hasExams && !hasSolutions) {
            hintText = '📎 Bitte laden Sie zuerst Klausuren (blauer Button) und eine Musterlösung (grüner Button) hoch.';
          } else if (!hasSolutions) {
            hintText = '📎 Bitte laden Sie noch die Musterlösung hoch (grüner Button), dann starte ich die Bewertung.';
          } else {
            hintText = '📎 Bitte laden Sie noch die Klausuren hoch (blauer Button), dann starte ich die Bewertung.';
          }
          appendBotText(hintText);
          await persistMessage(chatId, 'bot', hintText);
        }
      } catch {
        setIsBotTyping(false);
        const botText = 'Vielen Dank für Ihre Nachricht! Laden Sie Klausuren und Musterlösung hoch, um die Bewertung zu starten.';
        appendBotText(botText);
        await persistMessage(chatId, 'bot', botText);
      }
    },
    [ensureChat]
  );

  return (
    <div className={`app ${sidebarOpen ? 'sidebar-open' : ''}`}>
      <Sidebar
        open={sidebarOpen}
        chats={chatList}
        activeChatId={activeChatId}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        onRenameChat={handleRenameChat}
        onToggleSidebar={() => setSidebarOpen((v) => !v)}
      />
      <Header onToggleSidebar={() => setSidebarOpen((v) => !v)} sidebarOpen={sidebarOpen} />
      <Chat messages={messages} isBotTyping={isBotTyping} />
      <Prompt onSend={handleSend} uploadProgress={uploadProgress} selectedModel={selectedModel} onModelChange={setSelectedModel} />
    </div>
  );
};

export default App;
