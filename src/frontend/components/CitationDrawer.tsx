"use client";

/**
 * WHY: Sleek centered node inspection modal.
 * Displays the exact graph node content plus enriched bilingual metadata from Ahmed's
 * curated JSON: aliases, keywords, structured role profile, KPIs, relations, and
 * approval/confidence fields.
 */
import React, { useState, useEffect } from "react";
import ReactDOM from "react-dom";
import { useApp } from "../context/AppContext";

interface CitationDrawerProps {
  isOpen: boolean;
  citationCode: string | null;
  citationTitle: string | null;
  onClose: () => void;
}

const valueList = (value: unknown): string[] => {
  if (!value) return [];
  if (Array.isArray(value)) return value.map(String).filter(Boolean);
  return [String(value)];
};

export const CitationDrawer: React.FC<CitationDrawerProps> = ({
  isOpen, citationCode, citationTitle, onClose
}) => {
  const { language, inspectingNode } = useApp();
  const [chunkData, setChunkData] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen || !citationCode) {
      setChunkData(null);
      return;
    }

    if (inspectingNode) {
      setChunkData(inspectingNode);
      setLoading(false);
      return;
    }

    const fetchChunkDetails = async () => {
      setLoading(true);
      try {
        const res = await fetch("/api/v1/documents/graph");
        if (res.ok) {
          const data = await res.json();
          const nodes = data.nodes || [];
          const matched = nodes.find((n: any) =>
            n.id === citationCode ||
            n.label?.toLowerCase().includes(citationCode.toLowerCase()) ||
            n.label_ar?.toLowerCase().includes(citationCode.toLowerCase()) ||
            n.id?.toLowerCase().includes(citationCode.toLowerCase()) ||
            (citationTitle && n.label?.toLowerCase() === citationTitle.toLowerCase())
          );
          setChunkData(matched || null);
        }
      } catch {
        setChunkData(null);
      } finally {
        setLoading(false);
      }
    };

    void fetchChunkDetails();
  }, [isOpen, citationCode, citationTitle, inspectingNode]);

  if (!isOpen || !citationCode) return null;

  const title = language === "ar" && chunkData?.label_ar ? chunkData.label_ar : (chunkData?.label || citationTitle || (language === "ar" ? "بطاقة المعرفة" : "Knowledge Card"));
  const description = language === "ar" && chunkData?.description_ar ? chunkData.description_ar : chunkData?.description;
  const fullText = language === "ar" && chunkData?.content_ar ? chunkData.content_ar : (chunkData?.content || chunkData?.content_preview || citationTitle || "");
  const aliases = valueList(chunkData?.aliases);
  const keywords = language === "ar" ? valueList(chunkData?.keywords_ar) : valueList(chunkData?.keywords_en);
  const roleProfile = chunkData?.role_profile;
  const kpis = Array.isArray(chunkData?.kpis) ? chunkData.kpis : [];
  const connections = Array.isArray(chunkData?.connections) ? chunkData.connections : [];

  const renderList = (items: string[]) => items.length > 0 ? (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
      {items.map((item, idx) => (
        <span key={`${item}_${idx}`} style={{ fontSize: "10px", padding: "3px 7px", borderRadius: "999px", border: "1px solid var(--border-soft)", background: "var(--color-paper)", color: "var(--text-meta)", fontWeight: 600 }}>
          {item}
        </span>
      ))}
    </div>
  ) : null;

  return ReactDOM.createPortal(
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0,
        background: "rgba(0, 0, 0, 0.78)", backdropFilter: "blur(8px)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999,
        pointerEvents: "auto"
      }}
    >
      <div
        onClick={(event) => event.stopPropagation()}
        style={{
          background: "var(--color-paper)", border: "1px solid var(--border-med)",
          borderRadius: "var(--radius-xl)", padding: "26px", width: "760px", maxWidth: "94vw",
          maxHeight: "88vh", display: "flex", flexDirection: "column", gap: "14px",
          boxShadow: "var(--shadow-elevated)"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--border-soft)", paddingBottom: "14px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: 0 }}>
            <span style={{ background: "var(--color-accent)", color: "var(--color-accent-contrast)", padding: "4px 10px", borderRadius: "var(--radius-xs)", fontWeight: 700, fontSize: "12px" }}>
              {citationCode}
            </span>
            <span style={{ background: "var(--color-slate-raised)", color: "var(--text-meta)", padding: "3px 8px", borderRadius: "var(--radius-xs)", fontWeight: 700, fontSize: "11px" }}>
              {(chunkData?.group || "semantic chunk").toUpperCase()}
            </span>
            {chunkData?.approval_status && (
              <span style={{ fontSize: "10px", color: "#22c55e", fontWeight: 700 }}>
                {chunkData.approval_status} {chunkData.confidence ? `• ${chunkData.confidence}` : ""}
              </span>
            )}
          </div>
          <button onClick={onClose} style={{ background: "transparent", border: "none", color: "var(--text-meta)", fontSize: "20px", cursor: "pointer", padding: "2px 6px" }} aria-label="Close node details">
            ✕
          </button>
        </div>

        <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.4 }}>{title}</h3>
        {description && <p style={{ fontSize: "12px", color: "var(--text-meta)", lineHeight: 1.6 }}>{description}</p>}

        <div className="scrollable" style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "12px" }}>
          {loading ? (
            <div style={{ textAlign: "center", padding: "30px", color: "var(--text-meta)" }}>
              {language === "ar" ? "جاري تحميل البطاقة..." : "Loading card details..."}
            </div>
          ) : (
            <>
              <div style={{ background: "var(--color-stone)", border: "1px solid var(--border-soft)", borderRadius: "var(--radius-md)", padding: "18px", fontSize: "13px", lineHeight: 1.8, color: "var(--text-body)", whiteSpace: "pre-wrap" }}>
                {fullText}
              </div>

              {(aliases.length > 0 || keywords.length > 0) && (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {aliases.length > 0 && <><strong style={{ fontSize: "11px" }}>{language === "ar" ? "الأسماء البديلة" : "Aliases"}</strong>{renderList(aliases)}</>}
                  {keywords.length > 0 && <><strong style={{ fontSize: "11px" }}>{language === "ar" ? "كلمات البحث" : "Keywords"}</strong>{renderList(keywords)}</>}
                </div>
              )}

              {roleProfile && (
                <div style={{ background: "var(--color-stone)", border: "1px solid var(--border-soft)", borderRadius: "var(--radius-md)", padding: "14px", display: "flex", flexDirection: "column", gap: "8px" }}>
                  <strong style={{ fontSize: "12px" }}>{language === "ar" ? "الملف الوظيفي المنظم" : "Structured role profile"}</strong>
                  {Object.entries(roleProfile).map(([key, value]) => (
                    <div key={key} style={{ fontSize: "11px", color: "var(--text-body)", lineHeight: 1.6 }}>
                      <strong>{key.replace(/_/g, " ")}: </strong>{Array.isArray(value) ? value.join("; ") : String(value || "")}
                    </div>
                  ))}
                </div>
              )}

              {kpis.length > 0 && (
                <div style={{ background: "var(--color-stone)", border: "1px solid var(--border-soft)", borderRadius: "var(--radius-md)", padding: "14px", display: "flex", flexDirection: "column", gap: "8px" }}>
                  <strong style={{ fontSize: "12px" }}>{language === "ar" ? "مؤشرات الأداء" : "KPIs"}</strong>
                  {kpis.map((kpi: any, idx: number) => (
                    <div key={`${kpi?.name || idx}`} style={{ border: "1px solid var(--border-soft)", borderRadius: "var(--radius-sm)", padding: "10px", background: "var(--color-paper)", fontSize: "11px", lineHeight: 1.6 }}>
                      <strong>{kpi?.name || `KPI ${idx + 1}`}</strong>
                      {kpi?.formula && <div><strong>Formula:</strong> {kpi.formula}</div>}
                      {kpi?.target && <div><strong>Target:</strong> {kpi.target}</div>}
                      {kpi?.frequency && <div><strong>Frequency:</strong> {kpi.frequency}</div>}
                    </div>
                  ))}
                </div>
              )}

              {connections.length > 0 && (
                <div style={{ background: "var(--color-stone)", border: "1px solid var(--border-soft)", borderRadius: "var(--radius-md)", padding: "14px", display: "flex", flexDirection: "column", gap: "8px" }}>
                  <strong style={{ fontSize: "12px" }}>{language === "ar" ? "العلاقات" : "Connections"}</strong>
                  {connections.slice(0, 12).map((conn: any, idx: number) => (
                    <div key={idx} style={{ fontSize: "11px", color: "var(--text-body)", lineHeight: 1.5 }}>
                      {typeof conn === "string" ? conn : `[${conn.target_id}] ${conn.relation_type || "related"}${conn.reason ? ` — ${conn.reason}` : ""}`}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--border-soft)", paddingTop: "12px", gap: "10px" }}>
          <span style={{ fontSize: "10px", color: "var(--text-meta)" }}>
            {chunkData?.last_verified ? `${language === "ar" ? "آخر تحقق" : "Last verified"}: ${chunkData.last_verified}` : ""}
          </span>
          <button onClick={onClose} className="send-btn" title={language === "ar" ? "إغلاق" : "Close Card"} style={{ padding: "6px 14px", height: "34px", display: "flex", alignItems: "center", gap: "6px" }}>
            <svg viewBox="0 0 24 24" style={{ width: "16px", height: "16px" }}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/></svg>
            <span>{language === "ar" ? "حسناً" : "Done"}</span>
          </button>
        </div>
      </div>
    </div>,
    document.body
  ) as unknown as React.ReactElement;
};
