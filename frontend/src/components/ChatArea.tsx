import { useRef, useEffect, useState } from "react";
import { Empty, Typography, Spin, Button, Modal, App } from "antd";
import { PlayCircleOutlined, UndoOutlined } from "@ant-design/icons";
import type { Message } from "../types";
import * as api from "../api";
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
  onUndoStep: () => void;
}

export default function ChatArea({ messages, streaming, loading, videoGenerating, conversationId, isVideo, onSend, onUndoStep }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const { message: antMsg } = App.useApp();
  const [mergedOpen, setMergedOpen] = useState(false);
  const [mergedUrl, setMergedUrl] = useState("");
  const [draft, setDraft] = useState("");
  const [polished, setPolished] = useState<string | null>(null);
  const [polishLoading, setPolishLoading] = useState(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming, polished]);

  useEffect(() => {
    setDraft("");
    setPolished(null);
  }, [conversationId]);

  const handlePolish = async () => {
    if (!conversationId || !draft.trim() || polishLoading) return;
    setPolishLoading(true);
    try {
      const result = await api.polishVideoPrompt(conversationId, draft.trim());
      setPolished(result);
      setDraft(result);
      antMsg.success("润色完成，可再次润色或开始制作");
    } catch (err: any) {
      antMsg.error(err.message || "润色失败");
    } finally {
      setPolishLoading(false);
    }
  };

  const handleSend = () => {
    const text = draft.trim();
    if (!text) return;
    onSend(text);
    setDraft("");
    setPolished(null);
  };

  const handleViewMerged = async () => {
    if (!conversationId) return;
    const url = api.mergedVideoUrl(conversationId);
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error("还没有成片");
      setMergedUrl(url);
      setMergedOpen(true);
    } catch (err: any) {
      antMsg.error(err.message || "查看成片失败");
    }
  };

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

        {polished && (
          <div style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "8px 16px" }}>
            <div style={{
              width: 36, height: 36, borderRadius: "50%", background: "#52c41a",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "#fff", fontSize: 18, flexShrink: 0,
            }}>🤖</div>
            <div style={{ maxWidth: "75%" }}>
              <div style={{ marginBottom: 4, color: "#999", fontSize: 12 }}>润色后的提示词</div>
              <div style={{
                padding: "10px 14px", borderRadius: 12,
                background: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
                wordBreak: "break-word", whiteSpace: "pre-wrap", lineHeight: 1.6,
                border: "1px solid #b7eb8f",
              }}>
                <Typography.Text style={{ fontSize: 15 }}>{polished}</Typography.Text>
              </div>
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

      {/* 图生视频：成片 / 回退操作条 */}
      {isVideo && (
        <div style={{
          display: "flex", gap: 8, padding: "6px 12px",
          background: "#fff", borderTop: "1px solid #f0f0f0", flexShrink: 0,
        }}>
          <Button size="small" icon={<PlayCircleOutlined />} onClick={handleViewMerged}>
            查看成片
          </Button>
          <Button size="small" icon={<UndoOutlined />} onClick={onUndoStep} disabled={loading}>
            回到上一步
          </Button>
        </div>
      )}

      <MessageInput
        value={draft}
        onChange={setDraft}
        onSend={handleSend}
        loading={loading}
        polishable={isVideo}
        onPolish={handlePolish}
        polishLoading={polishLoading}
        placeholder={isVideo ? "输入提示词，可先润色再开始制作..." : undefined}
      />

      <Modal
        title="最终成片"
        open={mergedOpen}
        onCancel={() => setMergedOpen(false)}
        footer={null}
        width={480}
        destroyOnClose
      >
        <video
          src={mergedUrl}
          controls
          autoPlay
          style={{ width: "100%", borderRadius: 8, background: "#000" }}
        />
      </Modal>
    </div>
  );
}