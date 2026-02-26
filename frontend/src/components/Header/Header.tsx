import React, { useState } from 'react';
import './Header.css';

interface HeaderProps {
  onToggleSidebar: () => void;
}

const Header: React.FC<HeaderProps> = ({ onToggleSidebar }) => {
  const [showInfo, setShowInfo] = useState(false);

  return (
    <header className="header">
      <div className="header-left">
        <button className="header-menu-btn" onClick={onToggleSidebar} aria-label="Menu">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
        <div className="header-logo">
        <svg className="header-logo-icon" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
          {/* Document */}
          <rect x="10" y="4" width="24" height="32" rx="3" fill="#4A90D9" stroke="#2B5EA7" strokeWidth="1.5" />
          <rect x="14" y="10" width="16" height="2" rx="1" fill="#ffffff" />
          <rect x="14" y="15" width="16" height="2" rx="1" fill="#ffffff" />
          <rect x="14" y="20" width="12" height="2" rx="1" fill="#ffffff" />
          <rect x="14" y="25" width="14" height="2" rx="1" fill="#ffffff" />
          {/* Pencil */}
          <g transform="translate(22, 18) rotate(25)">
            <rect x="0" y="0" width="6" height="26" rx="1.5" fill="#7C4DFF" stroke="#5C35CC" strokeWidth="1" />
            <polygon points="0,26 6,26 3,32" fill="#5C35CC" />
            <rect x="0" y="0" width="6" height="5" rx="1.5" fill="#9E7BFF" />
          </g>
        </svg>
        <div className="header-logo-text">
          <span className="header-title">AUTOEXAM</span>
          <span className="header-subtitle">KLAUSUR KORREKTUR</span>
        </div>
        </div>
      </div>

      <div
        className="header-info-wrapper"
        onMouseEnter={() => setShowInfo(true)}
        onMouseLeave={() => setShowInfo(false)}
      >
        <button className="header-info-btn" aria-label="Info">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="10" cy="10" r="9" stroke="currentColor" strokeWidth="1.5" />
            <text x="10" y="14.5" textAnchor="middle" fontSize="12" fontWeight="700" fill="currentColor">i</text>
          </svg>
        </button>
        {showInfo && (
          <div className="header-info-card">
            <h4>About AutoExam</h4>
            <p>AutoExam is an AI-powered exam correction assistant. Upload your exams and solution sheets, and let the AI grade them automatically.</p>
            <p className="info-version">Version 1.0.0 &middot; Team Project 2026</p>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;
