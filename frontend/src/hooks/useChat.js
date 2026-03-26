import { useState, useCallback } from 'react';

const API_BASE = '/api';

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const sendMessage = useCallback(async (text, onNodesReferenced) => {
    const userMessage = { role: 'user', content: text };
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);
    setError(null);

    try {
      const history = messages.map(m => ({ role: m.role, content: m.content }));

      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history }),
      });

      if (!res.ok) throw new Error('Failed to send message');
      const data = await res.json();

      const assistantMessage = {
        role: 'assistant',
        content: data.answer,
        sql: data.sql,
        nodes_referenced: data.nodes_referenced || [],
        in_domain: data.in_domain,
        latency_ms: data.latency_ms,
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Trigger node highlighting
      if (data.nodes_referenced?.length > 0 && onNodesReferenced) {
        onNodesReferenced(data.nodes_referenced);
      }

      return data;
    } catch (err) {
      setError(err.message);
      const errMessage = {
        role: 'assistant',
        content: `Error: ${err.message}`,
        isError: true,
      };
      setMessages(prev => [...prev, errMessage]);
    } finally {
      setLoading(false);
    }
  }, [messages]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    loading,
    error,
    sendMessage,
    clearChat,
  };
}
