import { useState, useEffect } from 'react';

export default function DebugPanel({ visible, onClose }) {
  const [logs, setLogs] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!visible) return;
    setLoading(true);
    Promise.all([
      fetch('https://dodgeai-yh1n.onrender.com/api/debug/logs').then(r => r.json()),
      fetch('https://dodgeai-yh1n.onrender.com/api/debug/summary').then(r => r.json()),
    ])
      .then(([logsData, summaryData]) => { setLogs(logsData.logs || []); setSummary(summaryData); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [visible]);

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-black/20 backdrop-blur-sm flex items-center justify-center" onClick={onClose}>
      <div 
        className="bg-white border border-gray-200 rounded-xl shadow-2xl w-[640px] max-h-[75vh] overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-900">Debug Panel</span>
            <span className="text-[9px] px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded font-mono">Ctrl+Shift+D</span>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="overflow-y-auto max-h-[calc(75vh-48px)] p-5 space-y-5">
          {loading ? (
            <div className="space-y-2">{[...Array(4)].map((_, i) => <div key={i} className="skeleton h-10 w-full" />)}</div>
          ) : (
            <>
              {summary && (
                <div>
                  <h4 className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-2">Data Summary</h4>
                  <div className="grid grid-cols-3 gap-2">
                    {Object.entries(summary.table_counts || {}).map(([table, count]) => (
                      <div key={table} className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                        <div className="text-[9px] uppercase text-gray-400 font-medium">{table}</div>
                        <div className="text-base font-bold text-gray-900">{count}</div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-2 flex gap-4 text-xs text-gray-500">
                    <span>Nodes: <strong className="text-gray-900">{summary.total_nodes}</strong></span>
                    <span>Broken: <strong className="text-red-500">{summary.broken_flows_count}</strong></span>
                  </div>
                </div>
              )}

              <div>
                <h4 className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-2">Recent Queries ({logs.length})</h4>
                {logs.length === 0 ? (
                  <p className="text-xs text-gray-400 text-center py-4">No queries logged yet</p>
                ) : (
                  <div className="space-y-1.5">
                    {logs.slice().reverse().map((log, i) => (
                      <div key={i} className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                        <div className="flex items-center justify-between mb-0.5">
                          <span className="text-xs text-gray-700 font-medium truncate max-w-[65%]">{log.query}</span>
                          <div className="flex items-center gap-2">
                            <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${log.in_domain ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-500'}`}>
                              {log.in_domain ? 'IN-DOMAIN' : 'REJECTED'}
                            </span>
                            <span className="text-[9px] text-gray-400">{Math.round(log.latency_ms)}ms</span>
                          </div>
                        </div>
                        {log.sql_generated && (
                          <pre className="text-[9px] text-gray-400 font-mono truncate">{log.sql_generated}</pre>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
