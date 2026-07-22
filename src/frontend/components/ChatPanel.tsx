"use client";

/**
 * WHY: Chat Workspace Panel (`ChatPanel.tsx`) — exact DOM structure from `index (31).html`.
 * Per Ahmed's exact instructions (`GAP-GPR-22`):
 * 1. Decodes live JSON tokens (`data: {"token": "..."}`) to guarantee zero truncation and zero connected characters.
 * 2. Displays a visible **Cycle Reasoning Log Card (`[ 🔄 TOC Navigation Steps ]`)** right inside the streaming bubble.
 * 3. Clicking inline citations (`[Source: Section X.Y]`) triggers `setInspectingNodeId(code)` to open our universal `CitationDrawer.tsx`.
 */
import React, { useState, useRef, useEffect } from "react";
import { useApp, ConversationTurn } from "../context/AppContext";
import { createSseParser } from "../utils/sseParser";

interface ExtendedTurn extends ConversationTurn {
  cycle_logs?: string[];
}

export const ChatPanel: React.FC = () => {
  const {
    conversations, activeConversationId, addTurnToConversation,
    savedApiKeys, activeApiKeyId, apiProvider, apiModel, language, selectedDocIds, setActiveGraphNodeIds, setInspectingNodeId, deviceId, workflowCycles, setIsSettingsOpen, t
  } = useApp();

  const [inputMessage, setInputMessage] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [activeSearchStatus, setActiveSearchStatus] = useState<string | null>(null);
  const [cycleLogs, setCycleLogs] = useState<string[]>([]);
  const [copyConvSuccess, setCopyConvSuccess] = useState(false);
  const [showCopyBtn, setShowCopyBtn] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const streamingContentRef = useRef("");
  const rafRef = useRef<number | null>(null);

  const activeConv = conversations.find(c => c.id === activeConversationId);
  const turns = activeConv ? (activeConv.turns as ExtendedTurn[]) : [];

  const scheduleStreamingPaint = () => {
    if (rafRef.current !== null) return;
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = null;
      setStreamingContent(streamingContentRef.current);
    });
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    if (turns.length > 0) setShowCopyBtn(true);
  };

  useEffect(() => {
    scrollToBottom();
  }, [turns, streamingContent, activeSearchStatus, cycleLogs]);

  useEffect(() => {
    if (showCopyBtn && !copyConvSuccess) {
      const timer = setTimeout(() => setShowCopyBtn(false), 3500);
      return () => clearTimeout(timer);
    }
  }, [showCopyBtn, copyConvSuccess]);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 40;
    if (isAtBottom && turns.length > 0) {
      setShowCopyBtn(true);
    }
  };

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputMessage.trim() || isStreaming) return;

    const activeProfileId = activeApiKeyId || (savedApiKeys && savedApiKeys.length > 0 ? savedApiKeys[0].id : null);
    if (!activeProfileId) {
      alert(language === "ar"
        ? "يرجى إضافة وتفعيل ملف مفتاح API مشفر أولاً من الإعدادات قبل إرسال الرسالة."
        : "Please add and activate an encrypted API key profile from Settings before sending a message."
      );
      setIsSettingsOpen(true);
      return;
    }

    const userText = inputMessage.trim();
    setInputMessage("");
    
    const userTurn: ConversationTurn = {
      id: `turn_u_${Date.now()}`,
      role: "user",
      content: userText,
      timestamp: new Date().toISOString()
    };
    addTurnToConversation(userTurn);

    setIsStreaming(true);
    streamingContentRef.current = "";
    setStreamingContent("");
    setCycleLogs([]);
    setActiveSearchStatus(language === "ar" ? "🔍 جاري تحليل السؤال ومراجعة الفهرس..." : "🔍 Analyzing query and examining TOC...");

    let accumulatedLogs: string[] = [];

    try {
      const response = await fetch("/api/v1/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-LLM-Profile-ID": activeProfileId,
          "X-LLM-Provider": apiProvider || "deepseek",
          "X-LLM-Model": apiModel || "deepseek-chat",
          "X-App-Language": language,
          "X-Device-ID": deviceId,
          "X-Workflow-Cycles": String(workflowCycles || 3)
        },
        body: JSON.stringify({
          message: userText,
          document_id: selectedDocIds.length > 0 ? selectedDocIds[0] : null,
          language: language,
          history: turns.slice(-6).map(turnItem => ({ role: turnItem.role, content: turnItem.content }))
        })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      let partialText = "";

      const parser = createSseParser((evt) => {
        const valStr = evt.data;
        if (evt.event === "agent_search") {
          try {
            const searchData = JSON.parse(valStr);
            if (searchData.active_node_ids && searchData.active_node_ids.length > 0) setActiveGraphNodeIds(searchData.active_node_ids);
            if (searchData.query) setActiveSearchStatus(language === "ar" ? `استرجاع في الخريطة: "${searchData.query}"` : `Graph querying: "${searchData.query}"`);
          } catch {}
        } else if (evt.event === "cycle_step" || evt.event === "status") {
          try {
            const stepObj = JSON.parse(valStr);
            if (stepObj.status) {
              setActiveSearchStatus(stepObj.status);
              accumulatedLogs.push(stepObj.status);
              setCycleLogs([...accumulatedLogs]);
            }
          } catch {}
        } else if (evt.event === "delta" || evt.event === "token" || evt.event === "message") {
          try {
            const obj = JSON.parse(valStr);
            partialText += obj.content ?? obj.token ?? "";
          } catch {
            partialText += valStr;
          }
          streamingContentRef.current = partialText;
          scheduleStreamingPaint();
        } else if (evt.event === "error") {
          try {
            const errObj = JSON.parse(valStr);
            throw new Error(errObj.error || errObj.message || "Streaming error");
          } catch (err) {
            if (err instanceof Error) throw err;
            throw new Error("Streaming error");
          }
        }
      });

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          parser.feed(decoder.decode(value, { stream: true }));
        }
        parser.feed(decoder.decode());
        parser.end();
        partialText = streamingContentRef.current;
        setStreamingContent(partialText);
      }

      const assistantTurn: ExtendedTurn = {
        id: `turn_a_${Date.now()}`,
        role: "assistant",
        content: partialText || (language === "ar" ? "تم استكمال الاسترجاع من الدليل." : "Retrieval completed from workspace manual."),
        timestamp: new Date().toISOString(),
        cycle_logs: accumulatedLogs
      };
      addTurnToConversation(assistantTurn);
    } catch (e: any) {
      const errTurn: ExtendedTurn = {
        id: `turn_err_${Date.now()}`,
        role: "assistant",
        content: language === "ar" ? `عذراً، حدث خطأ في الاتصال بخادم الاسترجاع: ${e.message}` : `Sorry, error connecting to retrieval backend: ${e.message}`,
        timestamp: new Date().toISOString()
      };
      addTurnToConversation(errTurn);
    } finally {
      setIsStreaming(false);
      setStreamingContent("");
      setActiveSearchStatus(null);
      setCycleLogs([]);
    }
  };

  const renderMarkdownContent = (text: string) => {
    if (!text) return null;
    // Basic structured markdown rendering for real-time output
    const lines = text.split("\n");
    const elements: React.ReactNode[] = [];
    let listItems: React.ReactNode[] = [];
    let listKey = 0;

    const flushList = () => {
      if (listItems.length > 0) {
        elements.push(<ul key={`ul_${listKey++}`} style={{ paddingLeft: "16px", margin: "6px 0", listStyle: "disc" }}>{listItems}</ul>);
        listItems = [];
      }
    };

    lines.forEach((line, i) => {
      // Heading
      if (line.startsWith("## ") || line.startsWith("# ")) {
        flushList();
        elements.push(<h3 key={`h_${i}`} style={{ fontWeight: 700, fontSize: "15px", margin: "10px 0 6px 0", color: "var(--text-primary)" }}>{line.replace(/^##? /, "")}</h3>);
        return;
      }
      // List item
      if (line.trim().startsWith("- ") || line.trim().startsWith("* ")) {
        const content = line.trim().slice(2);
        listItems.push(<li key={`li_${i}`} style={{ marginBottom: "4px", fontSize: "13px", lineHeight: 1.6 }}>{renderInlineMarkdown(content)}</li>);
        return;
      }
      // Empty line -> flush list and add break
      if (line.trim() === "") {
        flushList();
        elements.push(<div key={`br_${i}`} style={{ height: "6px" }} />);
        return;
      }
      flushList();
      elements.push(<p key={`p_${i}`} style={{ margin: "4px 0", fontSize: "13px", lineHeight: 1.65, color: "var(--text-body)", wordBreak: "break-word" }}>{renderInlineMarkdown(line)}</p>);
    });
    flushList();
    return <div style={{ whiteSpace: "pre-wrap" }}>{elements}</div>;
  };

  const renderInlineMarkdown = (text: string) => {
    // Split by bold (**text**) and italic (*text*) patterns
    const parts: React.ReactNode[] = [];
    let lastIdx = 0;
    const regex = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
    let match;
    let keyIdx = 0;
    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIdx) {
        parts.push(<span key={`t_${keyIdx++}`}>{text.slice(lastIdx, match.index)}</span>);
      }
      const token = match[0];
      if (token.startsWith("**") && token.endsWith("**")) {
        parts.push(<strong key={`b_${keyIdx++}`} style={{ fontWeight: 700 }}>{token.slice(2, -2)}</strong>);
      } else if (token.startsWith("*") && token.endsWith("*")) {
        parts.push(<em key={`i_${keyIdx++}`} style={{ fontStyle: "italic" }}>{token.slice(1, -1)}</em>);
      } else {
        parts.push(<span key={`t2_${keyIdx++}`}>{token}</span>);
      }
      lastIdx = match.index + token.length;
    }
    if (lastIdx < text.length) {
      parts.push(<span key={`t_${keyIdx++}`}>{text.slice(lastIdx)}</span>);
    }
    if (parts.length === 0) return text;
    return <span>{parts}</span>;
  };

  const renderContentWithCitations = (content: string) => {
    // Render structured markdown first, then handle citations
    const citationRegex = /\[(المصدر|Source):\s*(القسم|Section|جدول|Table)?\s*([0-9\.\w\-]+)\s*[\-\:]?\s*([^\]]+)?\]/g;
    const rawText = content;
    // Split by citations; render markdown for non-citation text, citation buttons for citations
    const parts: React.ReactNode[] = [];
    let lastIdx = 0;
    let match;
    let keyIdx = 0;

    while ((match = citationRegex.exec(rawText)) !== null) {
      if (match.index > lastIdx) {
        const segment = rawText.slice(lastIdx, match.index);
        parts.push(<span key={`md_${keyIdx++}`}>{renderMarkdownContent(segment)}</span>);
      }
      const code = match[3] || "1.0";
      parts.push(
        <button
          key={`cite_${keyIdx++}`}
          onClick={() => setInspectingNodeId(code)}
          className="source-chip"
          style={{ cursor: "pointer", border: "1px solid var(--border-soft)", outline: "none", margin: "0 4px", display: "inline-flex", alignItems: "center", gap: "4px", padding: "2px 8px", borderRadius: "9999px", background: "var(--color-blue-pale)", color: "var(--text-meta)", fontSize: "10px", fontWeight: 600 }}
          title={language === "ar" ? "انقر لفحص البطاقة وقراءة النص الكامل المحمي" : "Click to inspect exact node JSON from manual"}
        >
          <span>📄</span>
          <span>{code}</span>
        </button>
      );
      lastIdx = match.index + match[0].length;
    }

    if (lastIdx < rawText.length) {
      const segment = rawText.slice(lastIdx);
      parts.push(<span key={`md_final_${keyIdx++}`}>{renderMarkdownContent(segment)}</span>);
    }

    if (parts.length === 0) {
      return renderMarkdownContent(rawText);
    }
    return <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{parts}</div>;
  };

  return (
    <div className="chat-container">
      {/* Chat Messages Feed */}
      <div className="chat-messages scrollable" id="chatMessages" role="log" aria-live="polite" aria-atomic="true" onScroll={handleScroll}>
        {turns.length === 0 && !isStreaming ? (
          <div className="message" role="article" aria-label="Welcome message" style={{ alignSelf: "center", maxWidth: "90%", margin: "auto 0" }}>
            <div className="bubble" style={{ alignItems: "center", textAlign: "center", padding: "20px" }}>
              <span className="role-label" style={{ fontSize: "11px", marginBottom: "4px" }}>GPR Grounded Workspace v1.0</span>
              <div className="content" style={{ background: "transparent", border: "none" }}>
                <div style={{ fontSize: "32px", marginBottom: "8px" }}>◈</div>
                <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "6px" }}>
                  {language === "ar" ? "مرحباً بك في المساعد الداخلي المعتمد (GPR)" : "Welcome to GPR Grounded Assistant"}
                </h3>
              </div>
            </div>
          </div>
        ) : null}

        {turns.map(turn => (
          <div
            key={turn.id}
            className={`message ${turn.role === "user" ? "sent" : ""}`}
            role="article"
            aria-label={turn.role === "user" ? "Message from you" : "Message from assistant"}
          >
            <div className="bubble">
              <span className="role-label">
                {turn.role === "user" ? (language === "ar" ? "استفسار الموظف" : "Staff Query") : (language === "ar" ? "المساعد المعتمد (GPR)" : "GPR Grounded Assistant")}
              </span>
              <div className="content">
                {/* Render cycle logs card if saved for assistant turn and actual nodes were requested (`Point 9 & Point 10`) */}
                {turn.role === "assistant" && turn.cycle_logs && turn.cycle_logs.some(l => l.includes("Inspecting") || l.includes("Requested inspection") || l.includes("inspecting")) && (
                  <div style={{
                    background: "var(--color-slate)", border: "1px solid var(--border-soft)",
                    borderRadius: "var(--radius-sm)", padding: "8px 12px", marginBottom: "12px",
                    display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", color: "var(--text-meta)"
                  }}>
                    <div style={{ fontWeight: 700, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "6px" }}>
                      <span>{language === "ar" ? "سجل الاستقصاء والتفكير:" : "THINKING LOG:"}</span>
                    </div>
                    {turn.cycle_logs.map((logStr, lIdx) => (
                      <div key={lIdx} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span>•</span><span>{logStr}</span>
                      </div>
                    ))}
                  </div>
                )}

                {turn.role === "assistant" ? renderContentWithCitations(turn.content) : turn.content}
              </div>
              <span className="time">
                {new Date(turn.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
          </div>
        ))}

        {isStreaming ? (
          <div className="message" role="article" aria-label="Message from assistant">
            <div className="bubble">
              <span className="role-label">{language === "ar" ? "المساعد المعتمد (GPR)" : "GPR Grounded Assistant"}</span>
              <div className="content">
                {/* Live Status Feed during Streaming — always visible when streaming (`Point 5`) */}
                {isStreaming && (
                  <div style={{
                    background: "var(--color-slate)", border: "1px solid var(--border-soft)",
                    borderRadius: "var(--radius-sm)", padding: "8px 12px", marginBottom: "12px",
                    display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", color: "var(--text-meta)"
                  }}>
                    <div style={{ fontWeight: 700, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "6px" }}>
                      <span>{language === "ar" ? "سجل الاستقصاء والتفكير الجاري:" : "THINKING LOG:"}</span>
                    </div>
                    {cycleLogs.length > 0 ? (
                      cycleLogs.map((logStr, lIdx) => (
                        <div key={lIdx} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <span>•</span><span>{logStr}</span>
                        </div>
                      ))
                    ) : activeSearchStatus ? (
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span>•</span><span>{activeSearchStatus}</span>
                      </div>
                    ) : (
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", opacity: 0.7 }}>
                        <span>•</span><span>{language === "ar" ? "جارٍ معالجة الاستفسار..." : "Processing query..."}</span>
                      </div>
                    )}
                  </div>
                )}

                {activeSearchStatus && (
                  <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-accent)", marginBottom: "6px", opacity: 0.9 }}>
                    {activeSearchStatus}
                  </div>
                )}

                {streamingContent ? (
                  renderContentWithCitations(streamingContent)
                ) : (
                  <div className="typing-indicator" role="status" aria-label="Assistant is typing">
                    <span></span><span></span><span></span>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : null}

        {/* Small circular copy conversation button at the end of the chat page (`Point 11 - Auto-Fade visibility`) */}
        {turns.length > 0 && (
          <div style={{
            display: "flex", justifyContent: "center", margin: "12px 0 20px 0",
            opacity: showCopyBtn || copyConvSuccess ? 1 : 0,
            pointerEvents: showCopyBtn || copyConvSuccess ? "auto" : "none",
            transition: "opacity 0.35s ease"
          }}>
            <button
              type="button"
              onClick={() => {
                const fullConversationText = turns.map(t => `${t.role.toUpperCase()}: ${t.content}`).join("\n\n---\n\n");
                navigator.clipboard.writeText(fullConversationText);
                setCopyConvSuccess(true);
                setTimeout(() => setCopyConvSuccess(false), 2500);
              }}
              style={{
                width: "36px", height: "36px", borderRadius: "50%",
                background: "var(--color-stone)", border: "1px solid var(--border-med)",
                color: copyConvSuccess ? "var(--color-accent)" : "var(--text-meta)",
                cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                boxShadow: "var(--shadow-elevated)", transition: "all 0.2s ease"
              }}
              title={language === "ar" ? "نسخ المحادثة بأكملها (Copy entire chat)" : "Copy entire chat conversation"}
              aria-label="Copy entire conversation"
            >
              {copyConvSuccess ? (
                <svg viewBox="0 0 24 24" style={{ width: "18px", height: "18px", stroke: "currentColor", fill: "none", strokeWidth: 2.5 }}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/>
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" style={{ width: "16px", height: "16px", stroke: "currentColor", fill: "none", strokeWidth: 2 }}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                </svg>
              )}
            </button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input Area */}
      <div className="chat-input-area" id="chatInputArea">
        <div className="composer-row">
          <textarea
            ref={textareaRef}
            id="chatInput"
            className="chat-input"
            placeholder={selectedDocIds.length > 0 ? (language === "ar" ? `اسأل في نطاق المستند المعتمد...` : `Ask within scoped document...`) : t("ask_placeholder")}
            value={inputMessage}
            onChange={(e) => {
              setInputMessage(e.target.value);
              // Auto-grow height up to max-height
              const ta = e.target;
              ta.style.height = "auto";
              const scrollHeight = ta.scrollHeight;
              if (scrollHeight <= 120) {
                ta.style.height = `${scrollHeight}px`;
              } else {
                ta.style.height = "120px";
              }
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={isStreaming}
            aria-label="Type your question"
            autoComplete="off"
            rows={1}
          />
          <button
            className="send-btn"
            id="sendButton"
            onClick={handleSend}
            disabled={isStreaming || !inputMessage.trim()}
            aria-label="Send message"
            title={language === "ar" ? "إرسال الاستفسار" : "Send Query"}
            type="button"
            style={{ padding: "8px 12px", minWidth: "38px", borderRadius: "8px", justifyContent: "center" }}
          >
            <svg viewBox="0 0 24 24" style={{ width: "16px", height: "16px" }}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};
