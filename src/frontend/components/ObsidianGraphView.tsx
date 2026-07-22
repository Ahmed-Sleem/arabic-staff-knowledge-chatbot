"use client";

/**
 * WHY: Obsidian Mindmap & Force-Directed Graph View (`ObsidianGraphView.tsx`).
 * Per Ahmed's exact instructions (`GAP-GPR-21`):
 * 1. Features an integrated search bar and pure SVG Reset View icon button aligned in one top row (`top: 12, left: 12, right: 12`).
 * 2. Anchors nodes around origin `(0, 0)` so the Reset View button (`centerAt(0, 0, 800) + zoom(1.85, 800)`) never points to empty space.
 * 3. Nodes glow brightly (`#22c55e`) when searched.
 * 4. Clicking any node on the canvas or from search results directly opens `CitationDrawer` (`setInspectingNodeId(node.id)`),
 *    displaying the exact JSON object from `7bf464.json` without any further analysis.
 */
import React, { useRef, useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { useApp } from "../context/AppContext";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

interface GraphNode {
  id: string;
  label: string;
  label_ar?: string;
  group: string;
  val: number;
  content_preview: string;
  content?: string;
  content_ar?: string;
  description?: string;
  description_ar?: string;
  aliases?: string[];
  keywords_ar?: string[];
  keywords_en?: string[];
  role_profile?: Record<string, unknown>;
  kpis?: Array<Record<string, unknown>>;
  answerable_questions?: string[];
  not_answered_here?: string[];
  approval_status?: string;
  last_verified?: string;
  confidence?: string;
  connections?: Array<Record<string, unknown> | string>;
  page_number?: number;
  x?: number;
  y?: number;
}

interface GraphLink {
  id: string;
  source: string | GraphNode;
  target: string | GraphNode;
  label: string;
  value: number;
}

export const ObsidianGraphView: React.FC = () => {
  const { selectedDocIds, activeGraphNodeIds, setActiveGraphNodeIds, language, theme, setInspectingNodeId, setInspectingNode } = useApp();
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; links: GraphLink[] }>({ nodes: [], links: [] });
  const [searchQuery, setSearchQuery] = useState("");
  const [hasInitialCentered, setHasInitialCentered] = useState(false);
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({ width: 500, height: 600 });
  const [isFlashingAll, setIsFlashingAll] = useState(false);
  const fgRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const nodeLabelText = (node: GraphNode) => (language === "ar" && node.label_ar ? node.label_ar : node.label);
  const searchableNodeText = (node: GraphNode) => [
    node.id,
    node.label,
    node.label_ar,
    node.content_preview,
    node.content,
    node.content_ar,
    node.description,
    node.description_ar,
    ...(node.aliases || []),
    ...(node.keywords_ar || []),
    ...(node.keywords_en || []),
    ...(node.answerable_questions || []),
    ...(node.kpis || []).flatMap((kpi) => Object.values(kpi || {}).map(String)),
    node.role_profile ? JSON.stringify(node.role_profile) : "",
  ].filter(Boolean).join(" ").toLowerCase();

  const handleDeselectAll = () => {
    setActiveGraphNodeIds([]);
    setInspectingNodeId(null);
    setInspectingNode(null);
    setSearchQuery("");
    setIsFlashingAll(true);
    setTimeout(() => {
      setIsFlashingAll(false);
      resetMapView();
    }, 450);
  };

  useEffect(() => {
    if (!containerRef.current) return;
    const updateDims = () => {
      if (containerRef.current) {
        const { clientWidth, clientHeight } = containerRef.current;
        if (clientWidth > 0 && clientHeight > 0) {
          setDimensions({ width: clientWidth, height: clientHeight });
        }
      }
    };
    updateDims();
    const observer = new ResizeObserver(updateDims);
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const loadGraph = async () => {
    try {
      const docParam = selectedDocIds.length > 0 ? `?document_id=${selectedDocIds[0]}` : "";
      const res = await fetch(`/api/v1/documents/graph${docParam}`);
      if (res.ok) {
        const data = await res.json();
        setGraphData(data);
        setHasInitialCentered(false);
      }
    } catch (e) {
      console.error("Failed to load Obsidian graph:", e);
    }
  };

  useEffect(() => {
    loadGraph();
  }, [selectedDocIds]);

  // Find the Main Hub Node (`the node with the biggest number of relations/links`) where most nodes cluster
  const getMainHubNode = () => {
    if (!graphData.nodes || graphData.nodes.length === 0) return null;
    const degreeMap: Record<string, number> = {};
    graphData.links.forEach(l => {
      const srcId = typeof l.source === "object" && l.source ? (l.source as any).id : l.source;
      const tgtId = typeof l.target === "object" && l.target ? (l.target as any).id : l.target;
      if (srcId) degreeMap[srcId] = (degreeMap[srcId] || 0) + 1;
      if (tgtId) degreeMap[tgtId] = (degreeMap[tgtId] || 0) + 1;
    });
    let maxDegree = -1;
    let hub: GraphNode | null = null;
    graphData.nodes.forEach(n => {
      const deg = degreeMap[n.id] || 0;
      if (deg > maxDegree && typeof n.x === "number" && typeof n.y === "number") {
        maxDegree = deg;
        hub = n;
      }
    });
    return hub;
  };

  // Calculate exact main hub centering & bounding fit across active nodes so camera never points to empty space (`Rule 21`, `Rule 26`)
  const resetMapView = () => {
    if (!fgRef.current || !graphData.nodes || graphData.nodes.length === 0) return;
    const hub = getMainHubNode();
    if (hub && typeof hub.x === "number" && typeof hub.y === "number") {
      fgRef.current.centerAt(hub.x, hub.y, 800);
      fgRef.current.zoom(2.0, 800);
    } else {
      try {
        fgRef.current.zoomToFit(800, 50);
      } catch (e) {
        let sumX = 0, sumY = 0, count = 0;
        graphData.nodes.forEach(n => {
          if (typeof n.x === "number" && typeof n.y === "number") {
            sumX += n.x;
            sumY += n.y;
            count++;
          }
        });
        if (count > 0) {
          fgRef.current.centerAt(sumX / count, sumY / count, 800);
          fgRef.current.zoom(1.85, 800);
        }
      }
    }
  };

  // Handle initial centering right where the main hub node settles & keep map always alive
  const handleEngineStop = () => {
    if (fgRef.current && typeof fgRef.current.d3ReheatSimulation === "function") {
      fgRef.current.d3ReheatSimulation();
    }
    if (hasInitialCentered || !fgRef.current || graphData.nodes.length === 0) return;
    resetMapView();
    setHasInitialCentered(true);
  };

  // Smoothly center and pan when the AI model accesses chunks (`activeGraphNodeIds` updates via SSE)
  useEffect(() => {
    if (fgRef.current && activeGraphNodeIds.length > 0 && graphData.nodes.length > 0) {
      const targetNodes = graphData.nodes.filter(n => activeGraphNodeIds.includes(n.id));
      if (targetNodes.length > 0 && typeof targetNodes[0].x === "number" && typeof targetNodes[0].y === "number") {
        fgRef.current.centerAt(targetNodes[0].x, targetNodes[0].y, 1200);
        fgRef.current.zoom(2.3, 1200);
      }
    }
  }, [activeGraphNodeIds, graphData]);

  // Filter nodes by live search query
  const searchResults = searchQuery.trim()
    ? graphData.nodes.filter(n => searchableNodeText(n).includes(searchQuery.trim().toLowerCase())).slice(0, 6)
    : [];

  const searchMatchIds = searchResults.map(n => n.id);

  // Automatically center smoothly on top matching search result (`searchResults[0]`) while typing
  useEffect(() => {
    if (searchQuery.trim() && searchResults.length > 0 && fgRef.current) {
      const topNode = searchResults[0];
      if (typeof topNode.x === "number" && typeof topNode.y === "number") {
        fgRef.current.centerAt(topNode.x, topNode.y, 800);
        fgRef.current.zoom(2.2, 800);
      }
    }
  }, [searchQuery]);

  const handleNodeClickOrSelect = (node: GraphNode) => {
    setSearchQuery("");
    if (fgRef.current && node.x !== undefined && node.y !== undefined) {
      fgRef.current.centerAt(node.x, node.y, 800);
      fgRef.current.zoom(2.2, 800);
    }
    setInspectingNode(node);
    setInspectingNodeId(node.id);
  };

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%", height: "100%", position: "relative",
        background: "transparent"
      }}
    >
      {/* Top Search Bar + SVG Deselect All + Reset View Row (`Point 5 & Point 6`) */}
      <div style={{
        position: "absolute", top: 12, left: 12, right: 12, zIndex: 10,
        display: "flex", flexDirection: "column", gap: "6px"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <div className="conversation-search" style={{ height: "34px", flex: 1, background: "var(--color-paper)" }}>
            <svg viewBox="0 0 24 24" style={{ width: "14px", height: "14px" }}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0z"/>
            </svg>
            <input
              type="text"
              placeholder={language === "ar" ? "البحث في خريطة الـ 80 عقدة (بالرمز أو الاسم)..." : "Search 80 mindmap nodes by code or title..."}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                style={{ background: "transparent", border: "none", color: "var(--text-meta)", cursor: "pointer", fontSize: "14px", padding: "0 6px" }}
              >
                ✕
              </button>
            )}
          </div>

          {/* Deselect All Nodes Button (`Point 5`) */}
          <button
            type="button"
            onClick={handleDeselectAll}
            className="tool-btn"
            id="deselectAllBtn"
            style={{ width: "34px", height: "34px", flex: "0 0 34px", justifyContent: "center", padding: 0, transition: "all 0.2s ease" }}
            title={language === "ar" ? "إلغاء تحديد جميع العقد وإعادة تهيئة المنظور" : "Deselect all nodes & clear highlights"}
          >
            <svg viewBox="0 0 24 24" style={{ width: "16px", height: "16px", stroke: "currentColor", strokeWidth: 2, fill: "none" }}>
              <circle cx="12" cy="12" r="9"/>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 9l-6 6M9 9l6 6"/>
            </svg>
          </button>

          {/* Pure SVG Reset View Button right next to search bar */}
          <button
            type="button"
            onClick={resetMapView}
            className="tool-btn"
            id="resetMapBtn"
            style={{ width: "34px", height: "34px", flex: "0 0 34px", justifyContent: "center", padding: 0 }}
            title={language === "ar" ? "إعادة ضبط المنظور لاحتواء جميع العقد بالخريطة في المنتصف" : "Fit all nodes in view centered"}
          >
            <svg viewBox="0 0 24 24" style={{ width: "16px", height: "16px" }}>
              <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>
            </svg>
          </button>
        </div>

        {/* Live Search Dropdown Results */}
        {searchResults.length > 0 && (
          <div style={{
            background: "var(--color-paper)", border: "1px solid var(--border-med)",
            borderRadius: "var(--radius-sm)", padding: "6px", boxShadow: "var(--shadow-elevated)",
            display: "flex", flexDirection: "column", gap: "4px", maxHeight: "200px", overflowY: "auto"
          }}>
            {searchResults.map(resNode => (
              <div
                key={resNode.id}
                onClick={() => handleNodeClickOrSelect(resNode)}
                style={{
                  padding: "8px 10px", borderRadius: "4px", background: "var(--color-stone)",
                  border: "1px solid var(--border-soft)", cursor: "pointer", display: "flex",
                  justifyContent: "space-between", alignItems: "center"
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "2px", minWidth: 0, flex: 1 }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)", lineClamp: 1, overflow: "hidden", textOverflow: "ellipsis" }}>
                    [{resNode.id}] {nodeLabelText(resNode)}
                  </span>
                  <span style={{ fontSize: "10px", color: "var(--text-meta)", lineClamp: 1, overflow: "hidden", textOverflow: "ellipsis" }}>
                    {resNode.content_preview}
                  </span>
                </div>
                <span style={{ fontSize: "10px", color: "var(--color-accent)", fontWeight: 700, flexShrink: 0, marginLeft: "8px" }}>
                  📍 {language === "ar" ? "فحص البطاقة" : "Inspect"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <ForceGraph2D
        ref={fgRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={graphData}
        nodeLabel="label"
        d3AlphaDecay={0.015}
        d3AlphaMin={0.005}
        d3VelocityDecay={0.48}
        warmupTicks={80}
        cooldownTicks={Infinity}
        onEngineStop={handleEngineStop}
        enableNodeDrag={true}
        nodeRelSize={4}
        linkColor={() => theme === "dark" ? "rgba(255, 255, 255, 0.18)" : "rgba(0, 0, 0, 0.18)"}
        linkWidth={(link: any) => activeGraphNodeIds.includes(typeof link.source === "object" ? link.source.id : link.source) ? 2.5 : 1}
        linkDirectionalParticles={(link: any) => activeGraphNodeIds.includes(typeof link.source === "object" ? link.source.id : link.source) ? 4 : 0}
        linkDirectionalParticleSpeed={0.008}
        onNodeClick={(node: any) => handleNodeClickOrSelect(node)}
        nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          const isActive = activeGraphNodeIds.includes(node.id);
          const isSearched = searchMatchIds.includes(node.id);
          const size = isActive || isSearched ? 8 : (node.group === "heading" ? 5 : 3.5);

          // Glowing ring when node is searched or active
          if (isActive || isSearched) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, size + 6, 0, 2 * Math.PI);
            ctx.fillStyle = theme === "dark" ? "rgba(34, 197, 94, 0.5)" : "rgba(22, 163, 74, 0.4)";
            ctx.fill();
          }

          ctx.beginPath();
          ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
          ctx.fillStyle = isActive || isSearched
            ? (theme === "dark" ? "#22c55e" : "#16a34a")
            : (node.group === "heading" ? (theme === "dark" ? "#FFFFFF" : "#1A1A1A") : (theme === "dark" ? "#888888" : "#666666"));
          ctx.fill();

          if (globalScale > 1.6 || isActive || isSearched) {
            const label = nodeLabelText(node) || "";
            const fontSize = Math.max(10 / globalScale, 2.8);
            ctx.font = `${isActive || isSearched ? "bold " : ""}${fontSize}px sans-serif`;
            ctx.fillStyle = isActive || isSearched
              ? (theme === "dark" ? "#22c55e" : "#16a34a")
              : (theme === "dark" ? "#EEEEEE" : "#222222");
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.fillText(label, node.x, node.y + size + 2);
          }
        }}
      />
    </div>
  );
};
