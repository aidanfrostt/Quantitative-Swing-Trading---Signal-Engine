import { useMemo } from "react";
import { Background, ReactFlow, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";

const nodes: Node[] = [
  { id: "polygon", position: { x: 20, y: 40 }, data: { label: "Polygon API" }, style: nodeStyle("#113b63") },
  { id: "perigon", position: { x: 20, y: 140 }, data: { label: "Perigon API" }, style: nodeStyle("#113b63") },
  { id: "jobs", position: { x: 270, y: 90 }, data: { label: "Batch jobs (01-09)" }, style: nodeStyle("#222f57") },
  { id: "extended", position: { x: 520, y: 90 }, data: { label: "10-12 Advanced engines" }, style: nodeStyle("#2f2155") },
  { id: "db", position: { x: 770, y: 40 }, data: { label: "PostgreSQL / Timescale" }, style: nodeStyle("#1f3f3a") },
  { id: "kafka", position: { x: 770, y: 150 }, data: { label: "Kafka / Redpanda" }, style: nodeStyle("#47361a") },
  { id: "api", position: { x: 1030, y: 90 }, data: { label: "Signal API + UI" }, style: nodeStyle("#354b18") },
];

function nodeStyle(bg: string) {
  return {
    background: bg,
    color: "#e2e8f0",
    border: "1px solid rgba(148,163,184,.4)",
    width: 170,
    borderRadius: 12,
    padding: 8,
    fontSize: 12,
  };
}

const edges: Edge[] = [
  { id: "e1", source: "polygon", target: "jobs", animated: true, style: { stroke: "#3ee6cf" } },
  { id: "e2", source: "perigon", target: "jobs", animated: true, style: { stroke: "#3ee6cf" } },
  { id: "e3", source: "jobs", target: "extended", animated: true, style: { stroke: "#818cf8" } },
  { id: "e4", source: "jobs", target: "db", animated: true, style: { stroke: "#34d399" } },
  { id: "e5", source: "jobs", target: "kafka", animated: true, style: { stroke: "#f8c15d" } },
  { id: "e6", source: "extended", target: "db", animated: true, style: { stroke: "#818cf8" } },
  { id: "e7", source: "db", target: "api", animated: true, style: { stroke: "#34d399" } },
];

export function PipelineDiagram() {
  const memoNodes = useMemo(() => nodes, []);
  const memoEdges = useMemo(() => edges, []);

  return (
    <div className="h-[340px] overflow-hidden rounded-xl border border-line bg-panel/60">
      <ReactFlow
        nodes={memoNodes}
        edges={memoEdges}
        fitView
        fitViewOptions={{ padding: 0.12 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        zoomOnScroll={false}
        panOnScroll={false}
      >
        <Background gap={20} size={1} color="#233051" />
      </ReactFlow>
    </div>
  );
}
