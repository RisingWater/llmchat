import type { Conversation, ConversationDetail, ChatChunk } from "../types";

const BASE = "/api";

function headers(): Record<string, string> {
  const token = localStorage.getItem("token") || "";
  return {
    "Content-Type": "application/json",
    Authorization: token ? `Bearer ${token}` : "",
  };
}

// ---- 登录 ----
export async function login(password: string): Promise<string> {
  const res = await fetch(`${BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "登录失败" }));
    throw new Error(err.detail || "登录失败");
  }
  const data = await res.json();
  return data.token;
}

// ---- 会话 ----
export async function listConversations(): Promise<Conversation[]> {
  const res = await fetch(`${BASE}/conversations`, { headers: headers() });
  if (!res.ok) throw new Error("获取会话列表失败");
  return res.json();
}

export async function createConversation(): Promise<Conversation> {
  const res = await fetch(`${BASE}/conversations`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ title: "新的聊天" }),
  });
  if (!res.ok) throw new Error("创建会话失败");
  return res.json();
}

export async function createVideoConversation(
  file: File,
  title?: string
): Promise<Conversation> {
  const token = localStorage.getItem("token") || "";
  const fd = new FormData();
  fd.append("file", file);
  if (title) fd.append("title", title);
  const res = await fetch(`${BASE}/conversations/video`, {
    method: "POST",
    headers: { Authorization: token ? `Bearer ${token}` : "" },
    body: fd,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "创建失败" }));
    throw new Error(err.detail || "创建失败");
  }
  return res.json();
}

export async function getConversation(id: number): Promise<ConversationDetail> {
  const res = await fetch(`${BASE}/conversations/${id}`, { headers: headers() });
  if (!res.ok) throw new Error("获取会话失败");
  return res.json();
}

export async function updateConversation(
  id: number,
  data: {
    title?: string;
    system_prompt?: string;
    megapixels?: number;
    steps?: number;
    duration?: number;
  }
): Promise<Conversation> {
  const res = await fetch(`${BASE}/conversations/${id}`, {
    method: "PUT",
    headers: headers(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("更新会话失败");
  return res.json();
}

export async function deleteConversation(id: number): Promise<void> {
  await fetch(`${BASE}/conversations/${id}`, {
    method: "DELETE",
    headers: headers(),
  });
}

export async function clearConversationMessages(convId: number): Promise<void> {
  const res = await fetch(`${BASE}/conversations/${convId}/messages`, {
    method: "DELETE",
    headers: headers(),
  });
  if (!res.ok) throw new Error("清除失败");
}

// ---- 聊天 (SSE) ----
export function sendMessage(
  convId: number,
  content: string,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: string) => void
): AbortController {
  const controller = new AbortController();
  const token = localStorage.getItem("token") || "";

  fetch(`${BASE}/chat/${convId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
    },
    body: JSON.stringify({ content }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) throw new Error("请求失败");
      const reader = res.body?.getReader();
      if (!reader) throw new Error("无法读取流");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") {
              onDone();
              return;
            }
            try {
              const chunk: ChatChunk = JSON.parse(data);
              if (chunk.error) {
                onError(chunk.error);
                return;
              }
              if (chunk.content) {
                onChunk(chunk.content);
              }
            } catch {
              // ignore
            }
          }
        }
      }
      onDone();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err.message || "网络错误");
      }
    });

  return controller;
}

// ---- 图片生成 ----
export async function generateImage(
  conversationId: number,
  messageId: number
): Promise<{ image_url: string; prompt: string }> {
  const token = localStorage.getItem("token") || "";
  const res = await fetch(`${BASE}/images/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
    },
    body: JSON.stringify({ conversation_id: conversationId, message_id: messageId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "生成失败" }));
    throw new Error(err.detail || "生成失败");
  }
  return res.json();
}

// ---- 视频生成（图生视频会话）----
export async function generateVideo(
  conversationId: number,
  prompt: string
): Promise<{ video_url: string; prompt: string }> {
  const token = localStorage.getItem("token") || "";
  const res = await fetch(`${BASE}/videos/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
    },
    body: JSON.stringify({ conversation_id: conversationId, prompt }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "生成失败" }));
    throw new Error(err.detail || "生成失败");
  }
  return res.json();
}
