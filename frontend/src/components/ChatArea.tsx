import { useRef, useEffect } from "react";
import { Empty, Typography, Spin } from "antd";
import type { Message } from "../types";
import MessageBubble from "./MessageBubble";
import MessageInput from "./MessageInput";

interface Props {
  messages: Message[];
  streaming: string;
  loading: boolean;
  videoGenerating: boolean;
  conversationId: number | null;
  isVideo: boolean;
  onSend: (content: string) => void;
}

export default function ChatArea({ messages, streaming, loading, videoGenerating, conversationId, isVideo, onSend }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0, background: "#f5f5f5" }}>
      <div className="scroll-area" style={{ flex: 1, minHeight: 0, paddingTop: 8, overflowY: "auto" }}>
        {messages.length === 0 && !streaming && (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
            <Empty description={isVideo ? "上传起始画面后，输入提示词开始生成视频" : "开始聊天吧"} />
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} conversationId={conversationId ?? 0} />
        ))}

        {streaming && (
          <div style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "8px 16px" }}>
            <div style={{
              width: 36, height: 36, borderRadius: "50%", background: "#52c41a",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "#fff", fontSize: 18, flexShrink: 0,
            }}>🤖</div>
            <div style={{
              maxWidth: "75%", padding: "10px 14px", borderRadius: 12,
              background: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
              wordBreak: "break-word", whiteSpace: "pre-wrap", lineHeight: 1.6,
            }}>
              <Typography.Text style={{ fontSize: 15 }}>
                {streaming}
                <span style={{ display: "inline-block", width: 2, height: 16,
                  background: "#1677ff", marginLeft: 2, verticalAlign: "text-bottom" }} />
              </Typography.Text>
            </div>
          </div>
        )}

        {videoGenerating && (
          <div style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "8px 16px" }}>
            <div style={{
              width: 36, height: 36, borderRadius: "50%", background: "#52c41a",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "#fff", fontSize: 18, flexShrink: 0,
            }}>🤖</div>
            <div style={{
              padding: "10px 14px", borderRadius: 12,
              background: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
              display: "flex", alignItems: "center", gap: 8,
            }}>
              <Spin size="small" />
              <Typography.Text style={{ fontSize: 14, color: "#666" }}>正在生成视频，请稍候...</Typography.Text>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <MessageInput onSend={onSend} loading={loading} placeholder={isVideo ? "输入提示词，Enter 发送并开始生成视频..." : undefined} />
    </div>
  );
}
