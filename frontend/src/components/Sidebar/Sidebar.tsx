import React, { useState } from 'react';
import './Sidebar.css';

export interface ChatSummary {
  id: number;
  title: string;
}

interface SidebarProps {
  open: boolean;
  chats: ChatSummary[];
  activeChatId: number | null;
  onSelectChat: (id: number) => void;
  onNewChat: () => void;
  onDeleteChat: (id: number) => void;
  onRenameChat: (id: number, newTitle: string) => void;
  onToggleSidebar: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  open,
  chats,
  activeChatId,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  onRenameChat,
  onToggleSidebar,
}) => {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const startRenaming = (chat: ChatSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(chat.id);
    setEditTitle(chat.title);
  };

  const confirmRename = () => {
    if (editingId !== null && editTitle.trim()) {
      onRenameChat(editingId, editTitle.trim());
    }
    setEditingId(null);
    setEditTitle('');
  };

  const cancelRename = () => {
    setEditingId(null);
    setEditTitle('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      confirmRename();
    } else if (e.key === 'Escape') {
      cancelRename();
    }
  };

  return (
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      {/* Toggle sidebar button (hamburger) */}
      <button className="sidebar-toggle-btn" onClick={onToggleSidebar} aria-label="Sidebar umschalten">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      {/* New Chat button */}
      <button className="sidebar-new-chat" onClick={onNewChat}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        Neuer Chat
      </button>

      {/* Chat list */}
      <div className="sidebar-chats">
        {chats.length === 0 && (
          <p className="sidebar-empty">Keine vergangenen Chats</p>
        )}
        {chats.map((chat) => (
          <div
            key={chat.id}
            className={`sidebar-chat-item ${chat.id === activeChatId ? 'active' : ''}`}
            onClick={() => editingId !== chat.id && onSelectChat(chat.id)}
          >
            <svg className="sidebar-chat-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>

            {editingId === chat.id ? (
              <input
                className="sidebar-rename-input"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onKeyDown={handleKeyDown}
                onBlur={confirmRename}
                autoFocus
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <span className="sidebar-chat-title">{chat.title}</span>
            )}

            {editingId !== chat.id && (
              <div className="sidebar-chat-actions">
                <button
                  className="sidebar-chat-rename"
                  onClick={(e) => startRenaming(chat, e)}
                  title="Chat umbenennen"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                  </svg>
                </button>
                <button
                  className="sidebar-chat-delete"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteChat(chat.id);
                  }}
                  title="Chat löschen"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                    <path d="M10 11v6" />
                    <path d="M14 11v6" />
                  </svg>
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
};

export default Sidebar;
