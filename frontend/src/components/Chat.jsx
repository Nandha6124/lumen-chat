import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

export default function Chat({ user, onLogout }) {
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  const refreshList = () => api.conversations().then(setConversations).catch((e) => setError(e.message));

  useEffect(() => {
    refreshList();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const open = async (id) => {
    setError("");
    setActiveId(id);
    try {
      setMessages((await api.conversation(id)).messages);
    } catch (e) {
      setError(e.message);
    }
  };

  const newChat = () => {
    setActiveId(null);
    setMessages([]);
    setError("");
  };

  const remove = async (id) => {
    await api.deleteConversation(id);
    if (id === activeId) newChat();
    refreshList();
  };

  const send = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setError("");
    setSending(true);
    // show the user's message immediately
    setMessages((m) => [...m, { id: `tmp-${Date.now()}`, role: "user", content: text }]);
    try {
      const res = await api.chat(text, activeId);
      setActiveId(res.conversation.id);
      setMessages((m) => [...m, res.reply]);
      refreshList();
    } catch (err) {
      setError(err.message);
      setMessages((m) => m.slice(0, -1));
      setInput(text);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="layout">
      <aside className="sidebar">
        <button onClick={newChat}>+ New chat</button>
        <ul>
          {conversations.map((c) => (
            <li key={c.id} className={c.id === activeId ? "active" : ""}>
              <span className="title" onClick={() => open(c.id)}>
                {c.title}
              </span>
              <button className="icon" title="Delete" onClick={() => remove(c.id)}>
                ×
              </button>
            </li>
          ))}
        </ul>
        <div className="account">
          <span className="muted">{user.email}</span>
          <button className="link" onClick={onLogout}>
            Log out
          </button>
        </div>
      </aside>

      <main className="chat">
        <div className="messages">
          {messages.length === 0 && <div className="empty muted">Ask Lumen anything to get started.</div>}
          {messages.map((m) => (
            <div key={m.id} className={`bubble ${m.role}`}>
              {m.content}
            </div>
          ))}
          {sending && <div className="bubble assistant muted">Thinking…</div>}
          <div ref={bottomRef} />
        </div>
        {error && <div className="error banner">{error}</div>}
        <form className="composer" onSubmit={send}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message…"
            maxLength={4000}
          />
          <button type="submit" disabled={sending || !input.trim()}>
            Send
          </button>
        </form>
      </main>
    </div>
  );
}
