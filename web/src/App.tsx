import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { API_URL } from "./api";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
};

type Session = {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
};

const randomId = () => crypto.randomUUID();
const API_BASE = (import.meta.env.VITE_API_URL?.replace("/api/chat", "") as string) || "";

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<string | null>("Đang tải...");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionId, setSessionId] = useState(() => {
    let id = localStorage.getItem("chat_session_id");
    if (!id) {
      id = randomId();
      localStorage.setItem("chat_session_id", id);
    }
    return id;
  });
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const saved = localStorage.getItem('theme');
    if (saved === 'dark' || saved === 'light') return saved as 'dark' | 'light';
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'dark' : 'light';
  });

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (openMenuId && !(event.target as Element).closest('.session-menu-container')) {
        setOpenMenuId(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [openMenuId]);

  // Áp dụng theme vào thẻ html
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'));

  // Load sessions list
  const loadSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions`);
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch (error) {
      console.error("Failed to load sessions:", error);
    }
  }, []);

  // Load chat history when session changes
  useEffect(() => {
    const loadHistory = async () => {
      setStatus("Đang tải lịch sử...");
      try {
        const res = await fetch(`${API_BASE}/api/history/${sessionId}`);
        const data = await res.json();
        if (data.messages && data.messages.length > 0) {
          const historyMessages: Message[] = data.messages.map((msg: { role: string; content: string }) => ({
            id: randomId(),
            role: msg.role as "user" | "assistant",
            content: msg.content,
          }));
          setMessages(historyMessages);
          setStatus(`Đã tải ${historyMessages.length} tin nhắn`);
        } else {
          setMessages([]);
          setStatus("Sẵn sàng chat");
        }
        await loadSessions(); // Refresh sessions list
      } catch (error) {
        console.error("Failed to load history:", error);
        setStatus("Sẵn sàng chat");
      }
    };
    loadHistory();
  }, [sessionId, loadSessions]);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const createNewChat = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions`, { method: "POST" });
      const data = await res.json();
      const newSessionId = data.session_id;
      localStorage.setItem("chat_session_id", newSessionId);
      setSessionId(newSessionId);
      setMessages([]);
      setStatus("Cuộc trò chuyện mới");
      // Add new session to list immediately
      const newSession: Session = {
        id: newSessionId,
        title: "New Chat",
        created_at: Date.now() / 1000,
        updated_at: Date.now() / 1000,
        message_count: 0,
      };
      setSessions((prev) => [newSession, ...prev]);
      // Then refresh from server
      await loadSessions();
    } catch (error) {
      console.error("Failed to create session:", error);
      setStatus("Lỗi tạo cuộc trò chuyện mới");
    }
  };

  const switchSession = (newSessionId: string) => {
    localStorage.setItem("chat_session_id", newSessionId);
    setSessionId(newSessionId);
    setSessionId(newSessionId);
    setEditingSessionId(null);
    setSidebarOpen(false); // Close sidebar on mobile when switching
  };

  const deleteSession = async (targetSessionId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent switching to deleted session
    if (!confirm("Bạn có chắc muốn xóa cuộc trò chuyện này?")) {
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/sessions/${targetSessionId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        // If deleted session is current, switch to first available or create new
        if (targetSessionId === sessionId) {
          const remaining = sessions.filter((s) => s.id !== targetSessionId);
          if (remaining.length > 0) {
            switchSession(remaining[0].id);
          } else {
            await createNewChat();
          }
        }
        await loadSessions();
        setStatus("Đã xóa cuộc trò chuyện");
      }
    } catch (error) {
      console.error("Failed to delete session:", error);
      setStatus("Lỗi xóa cuộc trò chuyện");
    }
  };

  const startRename = (targetSessionId: string, currentTitle: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingSessionId(targetSessionId);
    setRenameValue(currentTitle);
    setOpenMenuId(null);
  };

  const cancelRename = () => {
    setEditingSessionId(null);
    setRenameValue("");
  };

  const saveRename = async (targetSessionId: string, e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (!renameValue.trim()) {
      cancelRename();
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/sessions/${targetSessionId}/rename`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: renameValue.trim() }),
      });
      if (res.ok) {
        await loadSessions();
        setEditingSessionId(null);
        setRenameValue("");
        setStatus("Đã đổi tên cuộc trò chuyện");
      }
    } catch (error) {
      console.error("Failed to rename session:", error);
      setStatus("Lỗi đổi tên cuộc trò chuyện");
    }
  };

  const sendMessage = useCallback(async () => {
    const question = input.trim();
    if (!question) return;

    const userMsg: Message = { id: randomId(), role: "user", content: question };
    const assistantMsg: Message = {
      id: randomId(),
      role: "assistant",
      content: "",
      streaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    try {
      setStatus("Đang gọi API...");
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question, session_id: sessionId }),
      });
      const json = await res.json();
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsg.id ? { ...msg, content: json.answer, streaming: false } : msg
        )
      );
      setStatus("Hoàn thành");
      await loadSessions(); // Refresh to update session title
    } catch (error) {
      setStatus(`Lỗi gọi API: ${(error as Error).message}`);
    }
  }, [input, sessionId, loadSessions]);

  const formatDate = (timestamp: number) => {
    // timestamp is in seconds, convert to milliseconds
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor(diff / (1000 * 60));

    if (minutes < 1) return "Vừa xong";
    if (hours < 1) return `${minutes} phút trước`;
    if (days === 0) return "Hôm nay";
    if (days === 1) return "Hôm qua";
    if (days < 7) return `${days} ngày trước`;
    return date.toLocaleDateString("vi-VN");
  };

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div style={{ padding: "20px", borderBottom: "1px solid #2d2d44" }}>
          <h2 style={{ margin: "0 0 15px 0", color: "#fff", fontSize: "18px" }}>Chatbot</h2>
          <button
            onClick={createNewChat}
            style={{
              width: "100%",
              padding: "10px",
              background: "#4a90e2",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "14px",
              fontWeight: "500",
            }}
          >
            + Cuộc trò chuyện mới
          </button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "10px" }}>
          {sessions.map((session) => (
            <div
              key={session.id}
              onClick={() => editingSessionId !== session.id && switchSession(session.id)}
              style={{
                padding: "12px",
                marginBottom: "8px",
                borderRadius: "6px",
                cursor: editingSessionId === session.id ? "default" : "pointer",
                background: session.id === sessionId ? "#2d2d44" : "transparent",
                border: session.id === sessionId ? "1px solid #4a90e2" : "1px solid transparent",
                transition: "all 0.2s",
                position: "relative",
              }}
              onMouseEnter={(e) => {
                if (session.id !== sessionId && editingSessionId !== session.id) {
                  e.currentTarget.style.background = "#252538";
                }
              }}
              onMouseLeave={(e) => {
                if (session.id !== sessionId && editingSessionId !== session.id) {
                  e.currentTarget.style.background = "transparent";
                }
              }}
            >
              {editingSessionId === session.id ? (
                <form
                  onSubmit={(e) => saveRename(session.id, e)}
                  onClick={(e) => e.stopPropagation()}
                  style={{ display: "flex", gap: "5px", alignItems: "center" }}
                >
                  <input
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Escape") {
                        e.preventDefault();
                        cancelRename();
                      }
                    }}
                    autoFocus
                    style={{
                      flex: 1,
                      padding: "6px 8px",
                      background: "#252538",
                      border: "1px solid #4a90e2",
                      borderRadius: "4px",
                      color: "#fff",
                      fontSize: "14px",
                    }}
                  />
                  <button
                    type="submit"
                    style={{
                      padding: "6px 10px",
                      background: "#4a90e2",
                      color: "white",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontSize: "12px",
                    }}
                  >
                    ✓
                  </button>
                  <button
                    type="button"
                    onClick={cancelRename}
                    style={{
                      padding: "6px 10px",
                      background: "#666",
                      color: "white",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontSize: "12px",
                    }}
                  >
                    ✕
                  </button>
                </form>
              ) : (
                <>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ color: "#fff", fontSize: "14px", fontWeight: "500", marginBottom: "4px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {session.title}
                      </div>
                      <div style={{ color: "#888", fontSize: "12px" }}>
                        {formatDate(session.updated_at)} • {session.message_count} tin nhắn
                      </div>
                    </div>

                    <div className="session-menu-container" style={{ position: "relative", marginLeft: "8px" }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setOpenMenuId(openMenuId === session.id ? null : session.id);
                        }}
                        style={{
                          background: "transparent",
                          border: "none",
                          color: "#888",
                          cursor: "pointer",
                          padding: "4px",
                          fontSize: "16px",
                          lineHeight: 1,
                          borderRadius: "4px",
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.color = "#fff"}
                        onMouseLeave={(e) => e.currentTarget.style.color = "#888"}
                      >
                        ⋮
                      </button>

                      {openMenuId === session.id && (
                        <div style={{
                          position: "absolute",
                          right: 0,
                          top: "100%",
                          background: "#1e1e2e",
                          border: "1px solid #2d2d44",
                          borderRadius: "6px",
                          boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
                          zIndex: 100,
                          minWidth: "120px",
                          overflow: "hidden",
                        }}>
                          <button
                            onClick={(e) => startRename(session.id, session.title, e)}
                            style={{
                              display: "block",
                              width: "100%",
                              textAlign: "left",
                              padding: "8px 12px",
                              background: "transparent",
                              border: "none",
                              color: "#e2e8f0",
                              cursor: "pointer",
                              fontSize: "13px",
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.background = "#2d2d44"}
                            onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                          >
                            ✏️ Đổi tên
                          </button>
                          <button
                            onClick={(e) => deleteSession(session.id, e)}
                            style={{
                              display: "block",
                              width: "100%",
                              textAlign: "left",
                              padding: "8px 12px",
                              background: "transparent",
                              border: "none",
                              color: "#ef4444",
                              cursor: "pointer",
                              fontSize: "13px",
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.background = "rgba(239, 68, 68, 0.1)"}
                            onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                          >
                            🗑️ Xóa
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </aside>

      {/* overlay for mobile sidebar */}
      <div className={`overlay ${sidebarOpen ? "show" : ""}`} onClick={() => setSidebarOpen(false)}></div>

      {/* Main Content */}
      <div className="main">
        <header className="header">
          <div className="header-content">
            <div className="title-group">
              <button className="mobile-toggle" onClick={() => setSidebarOpen((v) => !v)}>☰ Menu</button>
              <div>
                <h1 className="app-title">Customer Support Chatbot</h1>
                <p className="subtext">Copyright by Nguyen Van Ngon</p>
              </div>
            </div>
            <div className="header-right">
              <button className="mobile-toggle" onClick={toggleTheme} aria-label="Đổi theme">
                {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
              </button>
              {status && (
                <span className="status status-modern">
                  {status}
                </span>
              )}
            </div>
          </div>
        </header>

        <section className="chat-window" style={{ flex: 1, overflowY: "auto", padding: "20px" }}>
          {messages.length === 0 ? (
            <div style={{ textAlign: "center", color: "#888", marginTop: "50px" }}>
              <p>Chưa có tin nhắn nào. Bắt đầu cuộc trò chuyện!</p>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`bubble ${msg.role}`}>
                <div className="markdown-content">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content || (msg.streaming ? "Đang phản hồi..." : "")}
                  </ReactMarkdown>
                </div>
              </div>
            ))
          )}
        </section>

        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage();
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Chat tại đây ..."
            style={{ width: "100%" }}
          />
          <button type="submit">Gửi</button>
        </form>
      </div>
    </div>
  );
}

export default App;
