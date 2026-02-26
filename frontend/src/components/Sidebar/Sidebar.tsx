import React from 'react';
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
  onClose: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  open,
  chats,
  activeChatId,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  onClose,
}) => {
  return (
    <>
      {/* Overlay */}
      <div className={`sidebar-overlay ${open ? 'visible' : ''}`} onClick={onClose} />

      {/* Sidebar panel */}
      <aside className={`sidebar ${open ? 'open' : ''}`}>
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
              onClick={() => onSelectChat(chat.id)}
            >
              <svg className="sidebar-chat-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              <span className="sidebar-chat-title">{chat.title}</span>
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
          ))}
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
