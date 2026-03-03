import React, { useState, useCallback, useEffect } from 'react';
import Header from './components/Header/Header';
import Sidebar from './components/Sidebar/Sidebar';
import Chat from './components/Chat/Chat';
import Prompt from './components/Prompt/Prompt';
import { ChatMessageData, FileAttachment, ChatSummary, UploadProgress, AIModel, EvalProgress, EvaluationResults } from './types';
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
  const [evalProgress, setEvalProgress] = useState<EvalProgress | null>(null);

  // Load welcome message for a fresh (unsaved) state
  const loadWelcome = useCallback(() => {
    fetch(`${API_URL}/api/welcome`)
      .then((res) => res.json())
      .then((data: { message: string }) => {
        setMessages([
          { id: Date.now(), sender: 'bot', text: data.message, files: [], streaming: false, isNew: true },
        ]);
      })
      .catch(() => {
        setMessages([
          {
            id: Date.now(),
            sender: 'bot',
            text: "Hallo! \uD83D\uDC4B\n\nIch bin AutoExam, Ihr KI-gestützter Klausur-Korrektur-Assistent.\n\nNutzen Sie die Buttons in der Eingabeleiste, um Klausuren und Musterlösungen hochzuladen, und senden Sie dann eine Nachricht, um zu starten!",
            files: [],
            streaming: false,
            isNew: true,
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

  // Parse evaluation results from persisted message text
  const parseEvalFromText = (text: string): { evalResults?: EvaluationResults; displayText: string } => {
    const EVAL_MARKER = '<!--EVAL_RESULTS-->';
    if (text.startsWith(EVAL_MARKER)) {
      try {
        const json = text.slice(EVAL_MARKER.length);
        const evalResults: EvaluationResults = JSON.parse(json);
        return { evalResults, displayText: text };
      } catch {
        return { displayText: text };
      }
    }
    return { displayText: text };
  };

  // Select an existing chat (loaded messages are NOT new → no animation)
  const handleSelectChat = async (id: number) => {
    try {
      const res = await fetch(`${API_URL}/api/chats/${id}`);
      if (res.ok) {
        const data = await res.json();
        const msgs: ChatMessageData[] = data.messages.map((m: any) => {
          const { evalResults, displayText } = parseEvalFromText(m.text);
          return {
            id: m.id,
            sender: m.sender as 'bot' | 'user',
            text: displayText,
            files: [],
            streaming: false,
            isNew: false,
            evaluationResults: evalResults,
          };
        });
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

  // Helper to compute German grade from percentage
  const computeGrade = (score: number): string => {
    if (score >= 95) return '1.0';
    if (score >= 90) return '1.3';
    if (score >= 85) return '1.7';
    if (score >= 80) return '2.0';
    if (score >= 75) return '2.3';
    if (score >= 70) return '2.7';
    if (score >= 65) return '3.0';
    if (score >= 60) return '3.3';
    if (score >= 55) return '3.7';
    if (score >= 50) return '4.0';
    return '5.0';
  };

  // Stream evaluation from backend
  const runStreamingEvaluation = async (
    chatId: number,
    text: string,
  ): Promise<{ evalData: any | null; error: string | null }> => {
    try {
      const evalRes = await fetch(
        `${API_URL}/api/chats/${chatId}/evaluate?additional_instructions=${encodeURIComponent(text)}&model=${encodeURIComponent(selectedModel)}`,
        { method: 'POST' }
      );

      if (!evalRes.ok) {
        const errData = await evalRes.json().catch(() => ({ detail: 'Bewertung fehlgeschlagen' }));
        return { evalData: null, error: errData.detail || 'Bewertung fehlgeschlagen' };
      }

      const reader = evalRes.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let finalResult: any = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop()!;

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const event = JSON.parse(line);
            if (event.type === 'progress') {
              setEvalProgress({
                step: event.step,
                label: event.label,
                current: event.current,
                total: event.total,
              });
            } else if (event.type === 'error') {
              return { evalData: null, error: event.message };
            } else if (event.type === 'result') {
              finalResult = event;
            }
          } catch {
            // skip unparseable lines
          }
        }
      }

      // Process remaining buffer
      if (buffer.trim()) {
        try {
          const event = JSON.parse(buffer);
          if (event.type === 'result') finalResult = event;
          if (event.type === 'error') return { evalData: null, error: event.message };
        } catch { /* skip */ }
      }

      setEvalProgress(null);
      return { evalData: finalResult, error: null };
    } catch {
      setEvalProgress(null);
      return { evalData: null, error: 'Verbindungsfehler bei der Bewertung. Bitte versuchen Sie es erneut.' };
    }
  };

  // Build structured evaluation result message
  const buildEvalMessage = (chatId: number, evalData: any): ChatMessageData => {
    const results = evalData.results || [];
    const successResults = results.filter((r: any) => r.status === 'success');
    const totalExams = evalData.total_exams || results.length;
    const successCount = evalData.successful || successResults.length;

    // Calculate averages
    let avgScore = 0;
    let avgGrade = '';
    if (successResults.length > 0) {
      const totalScore = successResults.reduce((sum: number, r: any) => {
        return sum + (r.evaluation?.overall_score || 0);
      }, 0);
      avgScore = Math.round(totalScore / successResults.length);
      avgGrade = computeGrade(avgScore);
    }

    const items = results.map((r: any, i: number) => ({
      filename: r.filename || `Klausur ${i + 1}`,
      student_name: r.evaluation?.student_name || 'Unbekannt',
      overall_grade: r.evaluation?.overall_grade || '–',
      overall_score: r.evaluation?.overall_score || 0,
      total_points: r.evaluation?.total_points ?? '–',
      max_points: r.evaluation?.max_points ?? '–',
      status: r.status,
      error: r.error,
      downloadUrl: `${API_URL}/api/chats/${chatId}/download/${i}`,
    }));

    const evalResults: EvaluationResults = {
      items,
      chatId,
      totalExams,
      successCount,
      averageScore: avgScore,
      averageGrade: avgGrade,
      downloadAllUrl: totalExams > 1 ? `${API_URL}/api/chats/${chatId}/download-all` : undefined,
    };

    // Persist evaluation results as JSON so we can reconstruct the view when loading old chats
    const persistText = `<!--EVAL_RESULTS-->${JSON.stringify(evalResults)}`;

    return {
      id: Date.now() + Math.random(),
      sender: 'bot',
      text: persistText,
      files: [],
      streaming: false,
      isNew: true,
      evaluationResults: evalResults,
    };
  };

  const handleSend = useCallback(
    async (text: string, files: FileAttachment[]) => {
      // Helper: append text to last bot message (compacts consecutive bot messages)
      const appendBotText = (newText: string, opts?: { isError?: boolean }) => {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.sender === 'bot' && !last.evaluationResults) {
            // Append to existing bot message
            return prev.map((m, i) =>
              i === prev.length - 1
                ? { ...m, text: m.text + '\n\n' + newText, isError: m.isError || opts?.isError, streaming: false, isNew: true }
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
              isNew: true,
            },
          ];
        });
      };

      const userText = text || (files.length > 0 ? 'Dateien hochgeladen' : '');
      const userMessage: ChatMessageData = {
        id: Date.now(),
        sender: 'user',
        text: userText,
        files,
        streaming: false,
        isNew: true,
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
        const examCount = files.filter((f) => f.type === 'exam').length;
        const solutionCount = files.filter((f) => f.type === 'solution').length;

        // If both exams and solutions are present, trigger evaluation
        if (examCount > 0 && solutionCount > 0) {
          setIsBotTyping(false);
          setEvalProgress({ step: 'init', label: 'Bewertung wird gestartet...', current: 0, total: examCount });

          const { evalData, error } = await runStreamingEvaluation(chatId, text);

          setEvalProgress(null);

          if (error) {
            const errText = `❌ ${error}`;
            appendBotText(errText, { isError: true });
            await persistMessage(chatId, 'bot', errText);
          } else if (evalData) {
            const evalMsg = buildEvalMessage(chatId, evalData);
            setMessages((prev) => [...prev, evalMsg]);
            await persistMessage(chatId, 'bot', evalMsg.text);
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

      // Text-only message – always ask user to upload files for a new correction
      setIsBotTyping(false);
      const hintText = '📎 Bitte laden Sie Klausuren und eine Musterlösung hoch, um eine neue Bewertung zu starten. Nutzen Sie den blauen Button für Klausuren und den grünen Button für die Musterlösung.';
      appendBotText(hintText);
      await persistMessage(chatId, 'bot', hintText);
    },
    [ensureChat, selectedModel]
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
      <Chat messages={messages} isBotTyping={isBotTyping} evalProgress={evalProgress} />
      <Prompt onSend={handleSend} uploadProgress={uploadProgress} selectedModel={selectedModel} onModelChange={setSelectedModel} />
    </div>
  );
};

export default App;
