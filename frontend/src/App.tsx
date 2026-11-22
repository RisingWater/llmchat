import { useState, useEffect, useCallback, useRef } from "react";
import { App as AntApp } from "antd";
import type { Conversation, Message, ModelOption } from "./types";
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
  const [models, setModels] = useState<ModelOption[]>([]);
  const [currentId, setCurrentId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState("");
  const [loading, setLoading] = useState(false);
  const [videoGenerating, setVideoGenerating] = useState(false);
  const [videoModalOpen, setVideoModalOpen] = useState(false);

  // 当前流式请求的控制器与已收到内容（停止生成/切换会话时用）
  const abortRef = useRef<AbortController | null>(null);
  const streamedRef = useRef("");

  const abortStream = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    streamedRef.current = "";
  }, []);

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
    api.listModels().then(setModels).catch(() => setModels([]));
  }, [token]);

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
    abortStream();
    setLoading(false);
    setCurrentId(id);
    setStreaming("");
    try {
      const detail = await api.getConversation(id);
      setMessages(detail.messages);
    } catch {
      setMessages([]);
    }
  }, [abortStream]);

  const newConversation = useCallback(async () => {
    abortStream();
    setLoading(false);
    try {
      const conv = await api.createConversation();
      setConversations((prev) => [conv, ...prev]);
      setCurrentId(conv.id);
      setMessages([]);
      setStreaming("");
    } catch {
      // ignore
    }
  }, [abortStream]);

  const createVideoConversation = useCallback(async (file: File, title?: string) => {
    abortStream();
    setLoading(false);
    const conv = await api.createVideoConversation(file, title);
    setConversations((prev) => [conv, ...prev]);
    setCurrentId(conv.id);
    setMessages([]);
    setStreaming("");
  }, [abortStream]);

  // 从某条回答处分叉出新会话，并切换过去
  const forkConversation = useCallback(
    async (messageId: number) => {
      if (!currentId) throw new Error("没有当前会话");
      const conv = await api.forkConversation(currentId, messageId);
      setConversations((prev) => [conv, ...prev]);
      await selectConversation(conv.id);
    },
    [currentId, selectConversation]
  );

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

      const controller = api.sendMessage(
        currentId,
        content,
        (text) => {
          streamedContent += text;
          streamedRef.current = streamedContent;
          setStreaming(streamedContent);
        },
        () => {
          abortRef.current = null;
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
          abortRef.current = null;
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
      abortRef.current = controller;
    },
    [currentId, loadConversations]
  );

  // 停止生成：保留已收到的内容（后端在 SSE 断开时也会保存这部分）
  const stopGeneration = useCallback(() => {
    const partial = streamedRef.current.trim();
    abortStream();
    setLoading(false);
    setStreaming("");
    if (partial) {
      const partialMsg: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content: partial,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, partialMsg]);
    }
  }, [abortStream]);

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

  const updateConversationSettings = useCallback(
    async (systemPrompt: string, model: string, maxTokens: number) => {
      if (!currentId) return;
      await api.updateConversation(currentId, {
        system_prompt: systemPrompt,
        model,
        max_tokens: maxTokens,
      });
      setConversations((prev) =>
        prev.map((c) =>
          c.id === currentId
            ? { ...c, system_prompt: systemPrompt, model, max_tokens: maxTokens }
            : c
        )
      );
    },
    [currentId]
  );

  const updateVideoSettings = useCallback(
    async (megapixels: number, steps: number, duration: number, keepAudio: boolean) => {
      if (!currentId) return;
      await api.updateConversation(currentId, { megapixels, steps, duration, keep_audio: keepAudio });
      setConversations((prev) =>
        prev.map((c) =>
          c.id === currentId ? { ...c, megapixels, steps, duration, keep_audio: keepAudio } : c
        )
      );
    },
    [currentId]
  );

  // 回到上一步：删除最新片段，重新加载消息
  const handleUndoStep = useCallback(async () => {
    if (!currentId) return;
    setLoading(true);
    try {
      await api.undoVideoStep(currentId);
      const detail = await api.getConversation(currentId);
      setMessages(detail.messages);
      loadConversations().then(setConversations);
    } catch (err: any) {
      const errMsg: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content: `❌ ${err.message || "回退失败"}`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  }, [currentId, loadConversations]);

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
        models={models}
        streaming={streaming}
        loading={loading}
        videoGenerating={videoGenerating}
        onSelectConversation={selectConversation}
        onNewConversation={newConversation}
        onNewVideoConversation={() => setVideoModalOpen(true)}
        onDeleteConversation={deleteConversation}
        onClearAll={handleClearAll}
        onSendMessage={handleSend}
        onStopGeneration={stopGeneration}
        onUpdateSettings={updateConversationSettings}
        onUpdateVideoSettings={updateVideoSettings}
        onUndoStep={handleUndoStep}
        onFork={forkConversation}
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
