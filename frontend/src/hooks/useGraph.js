import { useState, useCallback, useEffect } from 'react';

const API_BASE = '/api';

export function useGraph() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [highlightedNodes, setHighlightedNodes] = useState(new Set());
  const [brokenFlowNodes, setBrokenFlowNodes] = useState(new Set());
  const [showBrokenFlows, setShowBrokenFlows] = useState(false);

  const NODE_COLORS = {
    ORDER: '#228be6',
    DELIVERY: '#40c057',
    INVOICE: '#fab005',
    PAYMENT: '#7950f2',
    CUSTOMER: '#e64980',
    PRODUCT: '#15aabf',
  };

  // Fetch full graph
  const fetchGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/graph`);
      if (!res.ok) throw new Error('Failed to fetch graph');
      const data = await res.json();

      // Transform to React Flow format with force-directed layout
      const nodeTypeCount = {};
      const rfNodes = data.nodes.map((n, i) => {
        const type = n.type || 'ORDER';
        nodeTypeCount[type] = (nodeTypeCount[type] || 0) + 1;
        const typeIndex = Object.keys(NODE_COLORS).indexOf(type);
        const angle = (i / data.nodes.length) * 2 * Math.PI;
        const radius = 200 + typeIndex * 180;

        return {
          id: n.id,
          type: 'customNode',
          position: {
            x: 600 + radius * Math.cos(angle) + (Math.random() - 0.5) * 100,
            y: 400 + radius * Math.sin(angle) + (Math.random() - 0.5) * 100,
          },
          data: {
            ...n,
            label: n.label,
            nodeType: type,
            color: n.color || NODE_COLORS[type] || '#6B7280',
            metadata: n.metadata || {},
          },
        };
      });

      const rfEdges = data.edges.map((e, i) => ({
        id: `edge-${i}`,
        source: e.source,
        target: e.target,
        type: 'straight',
        animated: false,
        style: { stroke: '#b8d4e8', strokeWidth: 1 },
      }));

      setNodes(rfNodes);
      setEdges(rfEdges);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch node details
  const fetchNodeDetails = useCallback(async (type, id) => {
    const res = await fetch(`${API_BASE}/node/${type}/${id}`);
    if (!res.ok) throw new Error('Failed to fetch node details');
    return await res.json();
  }, []);

  // Fetch broken flows
  const fetchBrokenFlows = useCallback(async () => {
    const res = await fetch(`${API_BASE}/broken-flows`);
    if (!res.ok) throw new Error('Failed to fetch broken flows');
    const data = await res.json();
    const brokenIds = new Set();
    data.flows.forEach(f => {
      brokenIds.add(f.order_id);
    });
    setBrokenFlowNodes(brokenIds);
    return data;
  }, []);

  // Highlight nodes from chat (5-second glow)
  const highlightNodes = useCallback((nodeIds) => {
    setHighlightedNodes(new Set(nodeIds));
    setTimeout(() => {
      setHighlightedNodes(new Set());
    }, 5000);
  }, []);

  // Toggle broken flows highlight
  const toggleBrokenFlows = useCallback(async () => {
    if (showBrokenFlows) {
      setShowBrokenFlows(false);
      setBrokenFlowNodes(new Set());
    } else {
      await fetchBrokenFlows();
      setShowBrokenFlows(true);
    }
  }, [showBrokenFlows, fetchBrokenFlows]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  return {
    nodes,
    edges,
    setNodes,
    setEdges,
    loading,
    error,
    highlightedNodes,
    brokenFlowNodes,
    showBrokenFlows,
    fetchGraph,
    fetchNodeDetails,
    fetchBrokenFlows,
    highlightNodes,
    toggleBrokenFlows,
    NODE_COLORS,
  };
}
