import { useState, useEffect, useCallback } from "react";
import { App as AntApp } from "antd";
import type { Conversation, Message } from "./types";
import * as api from "./api";
import LoginPage from "./components/LoginPage";
import AppLayout from "./components/AppLayout";
import VideoConversationModal from "./components/VideoConversationModal";

export default function App() {
  // 每次刷新页面清除旧的 token，强制重新输入密码
  useEffect(() => {
    localStorage.removeItem("token");
  }, []);

  const [token, setToken] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentId, setCurrentId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState("");
  const [loading, setLoading] = useState(false);
  const [videoGenerating, setVideoGenerating] = useState(false);
  const [videoModalOpen, setVideoModalOpen] = useState(false);

  const handleLogin = useCallback(async (password: string) => {
    const t = await api.login(password);
    localStorage.setItem("token", t);
    setToken(t);
  }, []);

  const handleLogout = useCallback(() => {
    localStorage.removeItem("token");
    setToken(null);
    setConversations([]);
    setCurrentId(null);
    setMessages([]);
  }, []);

  const loadConversations = useCallback(async () => {
    try {
      const list = await api.listConversations();
      setConversations(list);
      return list;
    } catch {
      return [];
    }
  }, []);

  useEffect(() => {
    if (!token) return;
    loadConversations().then((list) => {
      if (list.length > 0) {
        selectConversation(list[0].id);
      } else {
        newConversation();
      }
    });
  }, [token]);

  const selectConversation = useCallback(async (id: number) => {
    setCurrentId(id);
    setStreaming("");
    try {
      const detail = await api.getConversation(id);
      setMessages(detail.messages);
    } catch {
      setMessages([]);
    }
  }, []);

  const newConversation = useCallback(async () => {
    try {
      const conv = await api.createConversation();
      setConversations((prev) => [conv, ...prev]);
      setCurrentId(conv.id);
      setMessages([]);
      setStreaming("");
    } catch {
      // ignore
    }
  }, []);

  const createVideoConversation = useCallback(async (file: File, title?: string) => {
    const conv = await api.createVideoConversation(file, title);
    setConversations((prev) => [conv, ...prev]);
    setCurrentId(conv.id);
    setMessages([]);
    setStreaming("");
  }, []);

  const deleteConversation = useCallback(
    async (id: number) => {
      await api.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (currentId === id) {
        const remaining = conversations.filter((c) => c.id !== id);
        if (remaining.length > 0) {
          selectConversation(remaining[0].id);
        } else {
          newConversation();
        }
      }
    },
    [currentId, conversations, selectConversation, newConversation]
  );

  const handleClearAll = useCallback(async () => {
    if (!currentId) return;
    await api.clearConversationMessages(currentId);
    setMessages([]);
    setStreaming("");
  }, [currentId]);

  const sendMessage = useCallback(
    (content: string) => {
      if (!currentId) return;

      const userMsg: Message = {
        id: Date.now(),
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setStreaming("");
      setLoading(true);

      let streamedContent = "";

      api.sendMessage(
        currentId,
        content,
        (text) => {
          streamedContent += text;
          setStreaming(streamedContent);
        },
        () => {
          setLoading(false);
          const assistantMsg: Message = {
            id: Date.now() + 1,
            role: "assistant",
            content: streamedContent,
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, assistantMsg]);
          setStreaming("");
          loadConversations().then(setConversations);
        },
        (err) => {
          setLoading(false);
          setStreaming("");
          const errMsg: Message = {
            id: Date.now() + 1,
            role: "assistant",
            content: `❌ ${err}`,
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, errMsg]);
        }
      );
    },
    [currentId, loadConversations]
  );

  // 图生视频：输入提示词即触发视频生成，生成成功后刷新消息（视频由后端写入）
  const sendVideoPrompt = useCallback(
    async (content: string) => {
      if (!currentId) return;

      const userMsg: Message = {
        id: Date.now(),
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);
      setVideoGenerating(true);

      try {
        await api.generateVideo(currentId, content);
        const detail = await api.getConversation(currentId);
        setMessages(detail.messages);
        loadConversations().then(setConversations);
      } catch (err: any) {
        const errMsg: Message = {
          id: Date.now() + 1,
          role: "assistant",
          content: `❌ ${err.message || "视频生成失败"}`,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errMsg]);
      } finally {
        setLoading(false);
        setVideoGenerating(false);
      }
    },
    [currentId, loadConversations]
  );

  const handleSend = useCallback(
    (content: string) => {
      const conv = conversations.find((c) => c.id === currentId);
      if (conv?.conv_type === "video") {
        sendVideoPrompt(content);
      } else {
        sendMessage(content);
      }
    },
    [conversations, currentId, sendMessage, sendVideoPrompt]
  );

  const updateSystemPrompt = useCallback(
    async (systemPrompt: string) => {
      if (!currentId) return;
      await api.updateConversation(currentId, { system_prompt: systemPrompt });
      setConversations((prev) =>
        prev.map((c) =>
          c.id === currentId ? { ...c, system_prompt: systemPrompt } : c
        )
      );
    },
    [currentId]
  );

  const currentConv = conversations.find((c) => c.id === currentId) || null;

  if (!token) {
    return (
      <AntApp>
        <LoginPage onLogin={handleLogin} />
      </AntApp>
    );
  }

  return (
    <AntApp>
      <AppLayout
        conversations={conversations}
        currentConversation={currentConv}
        messages={messages}
        streaming={streaming}
        loading={loading}
        videoGenerating={videoGenerating}
        onSelectConversation={selectConversation}
        onNewConversation={newConversation}
        onNewVideoConversation={() => setVideoModalOpen(true)}
        onDeleteConversation={deleteConversation}
        onClearAll={handleClearAll}
        onSendMessage={handleSend}
        onUpdateSystemPrompt={updateSystemPrompt}
        onLogout={handleLogout}
      />
      <VideoConversationModal
        open={videoModalOpen}
        onClose={() => setVideoModalOpen(false)}
        onCreate={createVideoConversation}
      />
    </AntApp>
  );
}
