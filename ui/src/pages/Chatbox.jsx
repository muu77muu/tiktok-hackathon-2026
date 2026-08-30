import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";

// Point this at your FastAPI backend (include the /api prefix your routers use).
const API_BASE = "http://localhost:8000/api";

function makeSessionId() {
  return "sess-" + Math.random().toString(36).slice(2, 10);
}

export default function ChatBox() {
  const [sessionId] = useState(makeSessionId);
  const [messages, setMessages] = useState([]); // { role: 'user' | 'bot', text, products, intent, status }
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    // Best-effort session creation. If your backend auto-creates sessions
    // on first /chat call, this isn't strictly required, but chat.py checks
    // sessions.exists() for limit enforcement, so it's safer to create it up front.
    fetch(`${API_BASE}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    }).catch(() => {
      // Non-fatal: /chat can still be tried even if this fails.
    });
  }, [sessionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  async function sendMessage() {
    const text = input.trim();
    if (!text || sending) return;

    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setSending(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);

      setMessages((m) => [
        ...m,
        {
          role: "bot",
          text: data.response || data.message || "",
          products: data.recommendations || [],
          intent: data.intent,
          status: data.status,
        },
      ]);
    } catch (e) {
      setError(e.message);
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="flex flex-col h-[600px] w-full max-w-md border border-gray-200 rounded-lg bg-white overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100">
        <p className="text-sm font-medium text-gray-900">Shopping Copilot</p>
        <p className="text-xs text-gray-400">session: {sessionId}</p>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && (
          <p className="text-sm text-gray-400 text-center mt-8">Say hello to get started.</p>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className="max-w-[80%]">
              <div
                className={`px-3 py-2 rounded-lg text-sm whitespace-pre-wrap ${
                  m.role === "user"
                    ? "bg-blue-600 text-white rounded-br-sm"
                    : "bg-gray-100 text-gray-900 rounded-bl-sm"
                }`}
              >
                {m.text || <span className="italic text-gray-400">(empty response)</span>}
              </div>

              {m.products?.length > 0 && (
                <div className="grid grid-cols-2 gap-2 mt-2">
                  {m.products.map((p, j) => (
                    <div key={j} className="border border-gray-200 rounded-md p-2">
                      <p className="text-xs text-gray-800 line-clamp-2">
                        {p.title || p.product_id}
                      </p>
                      {p.price != null && (
                        <p className="text-xs text-blue-600 mt-1">${p.price}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {m.role === "bot" && m.intent && (
                <p className="text-[10px] text-gray-300 mt-1">
                  intent: {m.intent} · status: {m.status}
                </p>
              )}
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg rounded-bl-sm px-3 py-2">
              <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="px-4 py-2 text-xs text-red-600 bg-red-50 border-t border-red-100">
          {error}
        </div>
      )}

      <div className="p-3 border-t border-gray-100 flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder="Type a message…"
          className="flex-1 resize-none border border-gray-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <button
          onClick={sendMessage}
          disabled={sending || !input.trim()}
          className="shrink-0 w-9 h-9 flex items-center justify-center rounded-md bg-blue-600 text-white disabled:opacity-40"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}