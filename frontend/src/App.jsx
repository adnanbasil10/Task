import { useState, useEffect, useCallback } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import GraphView from './components/GraphView';
import ChatPanel from './components/ChatPanel';
import NodeDrawer from './components/NodeDrawer';
import DebugPanel from './components/DebugPanel';
import { useGraph } from './hooks/useGraph';
import { useChat } from './hooks/useChat';

const NODE_COLORS = {
  ORDER: '#228be6',
  DELIVERY: '#40c057',
  INVOICE: '#fab005',
  PAYMENT: '#7950f2',
  CUSTOMER: '#e64980',
  PRODUCT: '#15aabf',
};

export default function App() {
  const graph = useGraph();
  const chat = useChat();
  const [selectedNode, setSelectedNode] = useState(null);
  const [showDebug, setShowDebug] = useState(false);
  const [showChat, setShowChat] = useState(true);

  useEffect(() => {
    const handler = (e) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        setShowDebug(prev => !prev);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const handleNodeClick = useCallback((nodeData) => setSelectedNode(nodeData), []);
  const handleSendMessage = useCallback((text) => {
    chat.sendMessage(text, (nodeIds) => graph.highlightNodes(nodeIds));
    if (!showChat) setShowChat(true); // Open chat if they send from a suggested prompt elsewhere (unused for now)
  }, [chat, graph, showChat]);
  const handleNodeChipClick = useCallback((nodeId) => graph.highlightNodes([nodeId]), [graph]);

  return (
    <div className="h-screen flex flex-col bg-white text-gray-900 overflow-hidden">
      {/* Top Bar */}
      <header className="h-12 flex items-center justify-between px-5 bg-white border-b border-gray-200 shrink-0 z-20">
        <div className="flex items-center gap-3">
          {/* Hamburger Menu to toggle chat */}
          <button 
            onClick={() => setShowChat(!showChat)}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-500 hover:bg-gray-100 transition-colors"
            title="Toggle Chat Panel"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center shrink-0 ml-1">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div className="flex items-center gap-1.5 text-sm ml-1">
            <span className="text-gray-400 font-medium">Mapping</span>
            <span className="text-gray-300">/</span>
            <span className="font-bold text-gray-900">Order to Cash</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden lg:flex items-center gap-3">
            {Object.entries(NODE_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
                <span className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">{type}</span>
              </div>
            ))}
          </div>
          <div className="w-px h-5 bg-gray-200" />
          <button
            onClick={graph.toggleBrokenFlows}
            className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all border ${
              graph.showBrokenFlows
                ? 'bg-red-50 text-red-600 border-red-200 shadow-sm'
                : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
            }`}
          >
            {graph.showBrokenFlows ? '✕ Hide Broken' : '⚠ Broken Flows'}
          </button>
          
          {/* 3-dots Menu to explicitly open Debug Panel */}
          <button 
            onClick={() => setShowDebug(true)}
            className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500 hover:bg-gray-200 transition-colors shrink-0"
            title="System Statistics & Logs"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="5" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="12" cy="19" r="2"/>
            </svg>
          </button>
        </div>
      </header>

      {/* Main */}
      <div className="flex flex-1 min-h-0">
        {/* Graph */}
        <div className="flex-1 h-full relative bg-white min-w-0">
          <ReactFlowProvider>
            <GraphView
              graphNodes={graph.nodes}
              graphEdges={graph.edges}
              loading={graph.loading}
              highlightedNodes={graph.highlightedNodes}
              brokenFlowNodes={graph.brokenFlowNodes}
              onNodeClick={handleNodeClick}
            />
          </ReactFlowProvider>

          {/* Top-left overlay */}
          <div className="absolute top-4 left-4 flex gap-2 z-10">
            <button
              onClick={() => graph.fetchGraph()}
              className="text-xs px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 shadow-sm font-medium"
            >
              ↻ Refresh
            </button>
          </div>

          {/* Bottom-left stats — positioned ABOVE the controls */}
          {!graph.loading && (
            <div className="absolute bottom-2 left-14 z-10 pointer-events-none">
              <span className="text-[10px] text-gray-400 font-medium">
                {graph.nodes.length} nodes · {graph.edges.length} edges
              </span>
            </div>
          )}
        </div>

        {/* Chat — conditional visibility */}
        {showChat && (
          <div className="w-[380px] h-full shrink-0 border-l border-gray-200 shadow-xl z-10">
            <ChatPanel
              messages={chat.messages}
              loading={chat.loading}
              onSendMessage={handleSendMessage}
              onNodeChipClick={handleNodeChipClick}
            />
          </div>
        )}
      </div>

      {selectedNode && <NodeDrawer nodeData={selectedNode} onClose={() => setSelectedNode(null)} />}
      <DebugPanel visible={showDebug} onClose={() => setShowDebug(false)} />
    </div>
  );
}
