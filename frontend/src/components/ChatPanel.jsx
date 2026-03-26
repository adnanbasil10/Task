import { useState, useRef, useEffect } from 'react';

export default function ChatPanel({ messages, loading, onSendMessage, onNodeChipClick }) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  return (
    <div className="flex flex-col h-full bg-[#1a1a1a] text-white border-l border-[#2a2a2a]">
      {/* Header */}
      <div className="shrink-0 px-6 pt-5 pb-4 border-b border-[#2a2a2a]">
        <h2 className="text-base font-bold text-white tracking-tight">Chat with Graph</h2>
        <p className="text-[11px] text-gray-500 mt-0.5">Order to Cash</p>
      </div>

      {/* Messages — scrollable area */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6 min-h-0">
        {/* Intro when empty */}
        {messages.length === 0 && (
          <div className="message-enter space-y-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-[#252525] border border-[#333] rounded-full flex items-center justify-center shrink-0">
                <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.94-.49-7-3.85-7-7.93s3.05-7.44 7-7.93v15.86zm2-15.86c1.03.13 2 .45 2.87.93H13v-.93zM13 7h5.24c.25.31.48.65.68 1H13V7zm0 3h6.74c.08.33.15.66.19 1H13v-1zm0 3h6.93c-.04.34-.11.67-.19 1H13v-1zm0 3h5.92c-.2.35-.43.69-.68 1H13v-1zm0 3h2.87c-.87.48-1.84.8-2.87.93V19z"/>
                </svg>
              </div>
              <div>
                <p className="text-sm font-bold text-white">ContextGraph AI</p>
                <p className="text-[11px] text-gray-500">Graph Agent</p>
              </div>
            </div>

            <p className="text-[13px] text-gray-300 leading-relaxed">
              Hi! I can help you analyze the <strong className="text-white">Order to Cash</strong> process.
            </p>

            <div className="space-y-2">
              {[
                'Which products are associated with the most invoices?',
                'Trace the full flow for order ORD-001',
                'Identify orders with broken or incomplete flows',
                'Top 5 customers by order amount',
              ].map((q, i) => (
                <button
                  key={i}
                  onClick={() => onSendMessage(q)}
                  className="block w-full text-left text-[12px] text-gray-400 hover:text-white bg-[#222] hover:bg-[#2a2a2a] px-4 py-3 rounded-xl transition-all border border-[#333] hover:border-[#444]"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message list */}
        {messages.map((msg, i) => (
          <div key={i} className="message-enter">
            {msg.role === 'user' && (
              <div className="flex justify-end mb-1">
                <div className="max-w-[85%]">
                  <div className="flex items-center gap-2 justify-end mb-1.5">
                    <span className="text-[11px] font-medium text-gray-500">You</span>
                    <div className="w-6 h-6 bg-[#444] rounded-full flex items-center justify-center">
                      <svg className="w-3 h-3 text-gray-300" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                      </svg>
                    </div>
                  </div>
                  <div className="bg-[#333] text-gray-100 text-[13px] px-4 py-3 rounded-2xl rounded-tr-md leading-relaxed">
                    {msg.content}
                  </div>
                </div>
              </div>
            )}

            {msg.role === 'assistant' && (
              <div className="space-y-2">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 bg-[#252525] border border-[#333] rounded-full flex items-center justify-center shrink-0">
                    <svg className="w-3.5 h-3.5 text-white" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.94-.49-7-3.85-7-7.93s3.05-7.44 7-7.93v15.86zm2-15.86c1.03.13 2 .45 2.87.93H13v-.93z"/>
                    </svg>
                  </div>
                  <div>
                    <p className="text-[11px] font-bold text-white">ContextGraph AI</p>
                    <p className="text-[9px] text-gray-600">Graph Agent</p>
                  </div>
                </div>

                <div className={`pl-[38px] text-[13px] leading-[1.7] ${
                  msg.isError || msg.in_domain === false ? 'text-red-400' : 'text-gray-300'
                }`}>
                  {msg.content}
                </div>

                {msg.sql && (
                  <div className="pl-[38px]"><SQLBlock sql={msg.sql} /></div>
                )}

                {msg.nodes_referenced?.length > 0 && (
                  <div className="pl-[38px] flex flex-wrap gap-1.5 pt-1">
                    {msg.nodes_referenced.slice(0, 8).map((nodeId, j) => (
                      <button
                        key={j}
                        onClick={() => onNodeChipClick?.(nodeId)}
                        className="text-[10px] px-2.5 py-1 bg-blue-900/30 text-blue-400 rounded-full hover:bg-blue-800/50 transition-colors border border-blue-800/30"
                      >
                        {nodeId}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-[#252525] border border-[#333] rounded-full flex items-center justify-center shrink-0">
              <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            </div>
            <div className="space-y-2 pt-0.5">
              <div className="skeleton-dark h-3 w-44 rounded" />
              <div className="skeleton-dark h-3 w-28 rounded" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Bottom input */}
      <div className="shrink-0 px-5 pb-4 pt-3 border-t border-[#252525]">
        <div className="flex items-center gap-2 mb-3">
          <span className="w-2 h-2 bg-green-500 rounded-full" />
          <span className="text-[10px] text-gray-500 font-medium">ContextGraph AI is awaiting instructions</span>
        </div>
        <div className="bg-[#222] rounded-xl border border-[#333] overflow-hidden">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder="Analyze anything"
            rows={2}
            className="w-full bg-transparent text-gray-200 text-[13px] resize-none outline-none placeholder:text-gray-600 leading-relaxed px-4 pt-3 pb-1"
            disabled={loading}
          />
          <div className="flex justify-end px-3 pb-2.5">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={loading || !input.trim()}
              className="px-4 py-1.5 bg-[#3a3a3a] hover:bg-[#484848] disabled:bg-[#282828] disabled:text-gray-700 text-gray-200 text-[12px] font-medium rounded-lg transition-colors"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function SQLBlock({ sql }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-1">
      <button
        onClick={() => setOpen(!open)}
        className="text-[10px] flex items-center gap-1.5 text-gray-500 hover:text-gray-300 transition-colors"
      >
        <svg className={`w-3 h-3 transition-transform ${open ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        {open ? 'Hide SQL' : 'View SQL'}
      </button>
      {open && (
        <pre className="mt-2 p-3 bg-[#111] rounded-lg text-[10px] text-green-400 font-mono overflow-x-auto border border-[#2a2a2a] leading-relaxed">
          {sql}
        </pre>
      )}
    </div>
  );
}
