"use client";

/**
 * WHY: GPR Workspace Header (`Header.tsx`) — exact minimal monochrome floating toolbar (`Row 5 / Col 1`).
 * Per Ahmed's exact requirement (`GAP-GPR-18`), 100% of action buttons are universal SVG icons
 * with descriptive hover tooltips (`AR/EN`): Globe (Language), Sun/Moon (Theme), Gear (Settings Modal), Map Toggle.
 */
import React, { useState } from "react";
import { useApp } from "../context/AppContext";

export const Header: React.FC = () => {
  const { language, setLanguage, theme, setTheme, setIsSettingsOpen } = useApp();
  const [isRightPanelClosed, setIsRightPanelClosed] = useState(false);

  const toggleRightPanel = () => {
    const mainWindow = document.getElementById("mainWindow");
    if (!mainWindow) return;
    const closed = mainWindow.classList.toggle("right-panel-closed");
    setIsRightPanelClosed(closed);
  };

  return (
    <>
      <header className="app-header" id="appHeader" role="banner">
        <div className="header-tools" role="toolbar" aria-label="Workspace tools">
          
          {/* Language toggle (Globe SVG only) */}
          <button
            className="tool-btn"
            id="langSwitch"
            type="button"
            onClick={() => setLanguage(language === "ar" ? "en" : "ar")}
            aria-label="Switch language"
            title={language === "ar" ? "تغيير اللغة إلى الإنجليزية (Switch to English)" : "التبديل إلى العربية (Switch to Arabic)"}
          >
            <svg viewBox="0 0 24 24" style={{ width: "16px", height: "16px" }}>
              <circle cx="12" cy="12" r="10"/>
              <path strokeLinecap="round" d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
            </svg>
          </button>

          {/* Theme toggle: sun in light mode, moon in dark mode (SVG only) */}
          <button
            className="tool-btn"
            id="themeSwitch"
            type="button"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label="Switch theme"
            aria-pressed={theme === "dark"}
            title={theme === "dark" ? (language === "ar" ? "الوضع المضيء (Light Mode)" : "Switch to Light Mode") : (language === "ar" ? "الوضع الليلي (Dark Mode)" : "Switch to Dark Mode")}
          >
            <svg className="icon-sun" viewBox="0 0 24 24" style={{ width: "16px", height: "16px" }}>
              <circle cx="12" cy="12" r="4"/>
              <path strokeLinecap="round" d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>
            </svg>
            <svg className="icon-moon" viewBox="0 0 24 24" style={{ width: "16px", height: "16px" }}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          </button>

          {/* Settings Button (SVG Cog/Gear only + pulsing status dot) */}
          <button
            className="tool-btn"
            id="apiKeyBtn"
            type="button"
            onClick={() => setIsSettingsOpen(true)}
            aria-label="Settings and API models"
            title={language === "ar" ? "الإعدادات ومراحل الاسترجاع ومفاتيح API" : "Settings, Workflow Cycles & API Keys"}
            style={{ width: "36px", height: "36px", borderRadius: "10px", padding: 0, justifyContent: "center", gap: 0 }}
          >
            <svg viewBox="0 0 24 24" style={{ width: "16px", height: "16px" }}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </button>

          {/* Right Panel (Map) Toggle button (SVG only) */}
          <button
            className={`tool-btn ${isRightPanelClosed ? "active-closed" : ""}`}
            id="panelToggleBtn"
            type="button"
            onClick={toggleRightPanel}
            aria-label="Toggle right map panel"
            aria-pressed={isRightPanelClosed}
            title={isRightPanelClosed ? (language === "ar" ? "إظهار خريطة الترابط الدلالي" : "Open Right Panel (Mindmap)") : (language === "ar" ? "إخفاء خريطة الترابط الدلالي" : "Close Right Panel (Mindmap)")}
          >
            {isRightPanelClosed ? (
              <svg className="icon-panel-closed" viewBox="0 0 24 24" style={{ width: "16px", height: "16px" }}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zM9 3v18"/>
              </svg>
            ) : (
              <svg className="icon-panel-open" viewBox="0 0 24 24" style={{ width: "16px", height: "16px" }}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zM15 3v18"/>
              </svg>
            )}
          </button>

        </div>
      </header>

    </>
  );
};
