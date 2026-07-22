"use client";

/**
 * WHY: Master Workspace Page (`page.tsx`) — exact layout hierarchy from `index (31).html`.
 * Arranges Title, Mobile Drawer Backdrop, Left Panel, Header (floating toolbar in row 5),
 * Center Panel (Chat Workspace), right resize-handle, and Right Panel (Map / Obsidian Graph View).
 */
import React, { useEffect, useState } from "react";
import { Header } from "../components/Header";
import { LeftPanel } from "../components/LeftPanel";
import { ChatPanel } from "../components/ChatPanel";
import { DataPanel } from "../components/DataPanel";
import { LoadScreen } from "../components/LoadScreen";
import { useApp } from "../context/AppContext";

export default function Home() {
  const { language, isReady } = useApp();
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  useEffect(() => {
    document.body.classList.toggle("mobile-sidebar-open", isMobileSidebarOpen);
    document.body.style.overflow = isMobileSidebarOpen ? "hidden" : "";
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsMobileSidebarOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.classList.remove("mobile-sidebar-open");
      document.body.style.overflow = "";
    };
  }, [isMobileSidebarOpen]);

  if (!isReady) {
    return <LoadScreen />;
  }

  const startResize = (e: React.MouseEvent, target: "left" | "right" = "right") => {
    const mainWindow = document.getElementById("mainWindow");
    if (target === "right" && mainWindow && mainWindow.classList.contains("right-panel-closed")) return;
    e.preventDefault();

    const startX = e.clientX;
    const targetPanel = document.getElementById(target === "left" ? "leftPanel" : "rightPanel");
    if (!targetPanel) return;
    const startWidth = targetPanel.getBoundingClientRect().width;
    const isRtl = language === "ar";

    const onMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = moveEvent.clientX - startX;
      const leftMin = 280;
      if (target === "left") {
        let newWidth = isRtl ? startWidth - deltaX : startWidth + deltaX;
        const maxAllowed = Math.min(420, Math.max(leftMin, window.innerWidth - 420));
        newWidth = Math.min(Math.max(newWidth, leftMin), maxAllowed);
        targetPanel.style.width = `${newWidth}px`;
        targetPanel.style.minWidth = `${newWidth}px`;
        targetPanel.style.maxWidth = `${newWidth}px`;
        document.documentElement.style.setProperty("--left-width", `${newWidth}px`);
        return;
      }

      let newWidth = isRtl ? startWidth + deltaX : startWidth - deltaX;
      const maxAllowed = Math.min(540, window.innerWidth - 320 - 240);
      newWidth = Math.min(Math.max(newWidth, 290), Math.max(290, maxAllowed));

      targetPanel.style.width = `${newWidth}px`;
      targetPanel.style.minWidth = `${newWidth}px`;
      targetPanel.style.maxWidth = `${newWidth}px`;
      document.documentElement.style.setProperty("--right-width", `${newWidth}px`);
    };

    const onMouseUp = () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  };

  return (
    <div className="main-window" id="mainWindow">
      {/* Title Bar (Row 1 / Col 1) */}
      <div className="app-title" id="appTitle">
        <div className="app-title-left">
          <button
            className="mobile-sidebar-btn"
            id="mobileSidebarBtn"
            aria-label="Toggle conversations menu"
            aria-expanded={isMobileSidebarOpen}
            aria-controls="leftPanel"
            type="button"
            onClick={() => setIsMobileSidebarOpen(prev => !prev)}
          >
            <svg viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16"/>
            </svg>
          </button>
          <span className="brand-name">GPR</span>
        </div>
      </div>

      {/* Mobile Drawer Backdrop */}
      <div
        className="mobile-backdrop"
        id="mobileBackdrop"
        aria-hidden={!isMobileSidebarOpen}
        onClick={() => setIsMobileSidebarOpen(false)}
      />

      {/* Left Panel — Sidebar (Row 3 / Col 1 on desktop, Drawer on mobile) */}
      <div className="panel panel-left" id="leftPanel" role="complementary" aria-label="Conversation history">
        <LeftPanel />
      </div>

      {/* Header Bar — floating buttons right below the left panel (Row 5 / Col 1) */}
      <Header />

      {/* Left Resize Handle — only side of left panel beside the middle panel */}
      <div
        className="resize-handle left-resize-handle"
        data-target="left"
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize conversation panel"
        onMouseDown={(event) => startResize(event, "left")}
      />

      {/* Center Panel — Chat Workspace (Row 1 / Col 3) */}
      <div className="panel panel-center" id="centerPanel" role="main" aria-label="AI chat workspace">
        <ChatPanel />
      </div>

      {/* Resize Handle (Row 1 / Col 4) */}
      <div
        className="resize-handle"
        data-target="right"
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize document panel"
        onMouseDown={(event) => startResize(event, "right")}
      />

      {/* Right Panel — Map / Knowledge Graph View (Row 1 / Col 5) */}
      <div className="panel panel-right" id="rightPanel" role="complementary" aria-label="Knowledge graph map">
        <DataPanel />
      </div>
    </div>
  );
}
