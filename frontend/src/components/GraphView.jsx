import { memo, useCallback, useMemo, useEffect } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
} from '@xyflow/react';

const CustomNode = memo(({ data }) => {
  const isHighlighted = data.isHighlighted;
  const isBroken = data.isBroken;
  const size = data.nodeType === 'CUSTOMER' || data.nodeType === 'PRODUCT' ? 8 : 6;

  return (
    <div
      className={`relative group cursor-pointer
        ${isHighlighted ? 'node-highlighted' : ''}
        ${isBroken ? 'node-broken' : ''}
      `}
      style={{ borderRadius: '50%' }}
    >
      <Handle type="target" position={Position.Top} style={{ background: 'transparent', border: 'none', width: 1, height: 1 }} />
      <div
        className="rounded-full transition-transform duration-200 group-hover:scale-[2]"
        style={{
          width: `${size}px`,
          height: `${size}px`,
          backgroundColor: data.color,
        }}
      />
      <div className="absolute left-1/2 -translate-x-1/2 -top-7 opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none whitespace-nowrap z-50">
        <span className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-white shadow-lg border border-gray-200 text-gray-700">
          {data.metadata?.id || data.id}
        </span>
      </div>
      <Handle type="source" position={Position.Bottom} style={{ background: 'transparent', border: 'none', width: 1, height: 1 }} />
    </div>
  );
});

// Set display name for better debugging
CustomNode.displayName = 'CustomNode';

const nodeTypes = { customNode: CustomNode };

export default function GraphView({
  graphNodes,
  graphEdges,
  loading,
  highlightedNodes,
  brokenFlowNodes,
  onNodeClick,
}) {
  const processedNodes = useMemo(() => {
    return graphNodes.map(n => ({
      ...n,
      data: {
        ...n.data,
        isHighlighted: highlightedNodes.has(n.id),
        isBroken: brokenFlowNodes.has(n.id),
      },
    }));
  }, [graphNodes, highlightedNodes, brokenFlowNodes]);

  const [nodes, setNodes, onNodesChange] = useNodesState(processedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(graphEdges);

  // Safely sync external state into internal xyflow state
  useEffect(() => {
    setNodes(processedNodes);
  }, [processedNodes, setNodes]);

  useEffect(() => {
    setEdges(graphEdges);
  }, [graphEdges, setEdges]);

  const handleNodeClick = useCallback((event, node) => {
    if (onNodeClick) onNodeClick(node.data);
  }, [onNodeClick]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-white">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-400 text-xs">Loading graph...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full bg-white">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.05}
        maxZoom={3}
        defaultEdgeOptions={{
          type: 'straight',
          style: { stroke: '#b8d4e8', strokeWidth: 1 },
        }}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#f1f3f5" gap={40} size={1} />
        <Controls
          showInteractive={false}
          position="bottom-left"
          style={{ left: 16, bottom: 40 }}
        />
      </ReactFlow>
    </div>
  );
}
