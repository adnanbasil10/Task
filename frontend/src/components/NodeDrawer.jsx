import { useState, useEffect } from 'react';

export default function NodeDrawer({ nodeData, onClose }) {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!nodeData) return;
    setLoading(true);
    fetch(`https://dodgeai-yh1n.onrender.com/api/node/${nodeData.nodeType}/${nodeData.metadata?.id || nodeData.id}`)
      .then(res => res.json())
      .then(data => { setDetails(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [nodeData]);

  if (!nodeData) return null;

  const color = nodeData.color || '#228be6';
  const meta = nodeData.metadata || {};

  return (
    <div className="fixed inset-0 z-50" onClick={onClose}>
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 tooltip-enter"
        onClick={e => e.stopPropagation()}
      >
        <div className="bg-white rounded-xl shadow-xl border border-gray-200 w-[340px] max-h-[420px] overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-gray-900">{meta.name || meta.id || nodeData.id}</h3>
              <p className="text-[10px] font-medium uppercase tracking-wider mt-0.5" style={{ color }}>
                {nodeData.nodeType}
              </p>
            </div>
            <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="px-4 py-3 overflow-y-auto max-h-[320px] space-y-2">
            {loading ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => <div key={i} className="skeleton h-4 w-full" />)}
              </div>
            ) : (
              <>
                {Object.entries(meta).map(([key, value]) => (
                  <div key={key} className="flex text-xs">
                    <span className="text-gray-400 w-[45%] shrink-0 font-medium capitalize">
                      {key.replace(/_/g, ' ')}:
                    </span>
                    <span className="text-gray-900 font-medium">{String(value)}</span>
                  </div>
                ))}

                {/* Additional fields hidden note */}
                {details?.connected_nodes?.length > 0 && (
                  <div className="pt-2 mt-2 border-t border-gray-100">
                    <p className="text-[10px] text-gray-400 italic">
                      Connections: {details.connected_nodes.length}
                    </p>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
