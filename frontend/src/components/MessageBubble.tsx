import { useState } from "react";
import { Typography, Button, Image, Spin, App } from "antd";
import { UserOutlined, RobotOutlined, CameraOutlined, DownOutlined, RightOutlined } from "@ant-design/icons";
import type { Message } from "../types";
import * as api from "../api";

interface Props {
  message: Message;
  conversationId: number;
}

// 解析 content 中的图片 markdown，返回 { text, images }
function parseContent(content: string): { text: string; images: { url: string; alt: string }[] } {
  const images: { url: string; alt: string }[] = [];
  const text = content.replace(/!\[(.*?)\]\((.*?)\)/g, (_, alt, url) => {
    images.push({ url, alt });
    return "";
  });
  return { text: text.trim(), images };
}

// 解析 content 中的 <video> 标签，返回 { text, videos }
function parseVideos(content: string): { text: string; videos: string[] } {
  const videos: string[] = [];
  const text = content.replace(/<video\s+src="([^"]+)"[^>]*>\s*<\/video>/gi, (_, src) => {
    videos.push(src);
    return "";
  });
  return { text: text.trim(), videos };
}

export default function MessageBubble({ message, conversationId }: Props) {
  const isUser = message.role === "user";
  const [genState, setGenState] = useState<{
    loading: boolean;
    imageUrl?: string;
    prompt?: string;
  }>({ loading: false });
  const [promptExpanded, setPromptExpanded] = useState(false);
  const { message: antMsg } = App.useApp();

  const { text, images } = parseContent(message.content);
  const { text: textNoVideos, videos } = parseVideos(text);
  const displayText = textNoVideos;

  const handleGenerate = async () => {
    setGenState({ loading: true });
    try {
      const result = await api.generateImage(conversationId, message.id);
      setGenState({ loading: false, imageUrl: result.image_url, prompt: result.prompt });
    } catch (err: any) {
      setGenState({ loading: false });
      antMsg.error(err.message || "生成失败");
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: isUser ? "row-reverse" : "row",
        alignItems: "flex-start",
        gap: 8,
        padding: "8px 16px",
      }}
    >
      <div
        style={{
          width: 36, height: 36, borderRadius: "50%",
          background: isUser ? "#1677ff" : "#52c41a",
          display: "flex", alignItems: "center", justifyContent: "center",
          color: "#fff", fontSize: 18, flexShrink: 0,
        }}
      >
        {isUser ? <UserOutlined /> : <RobotOutlined />}
      </div>

      <div style={{ maxWidth: "75%" }}>
        {/* 文本 */}
        {displayText && (
          <div
            style={{
              padding: "10px 14px", borderRadius: 12,
              background: isUser ? "#1677ff" : "#fff",
              color: isUser ? "#fff" : "#333",
              boxShadow: isUser ? undefined : "0 1px 3px rgba(0,0,0,0.08)",
              wordBreak: "break-word", whiteSpace: "pre-wrap", lineHeight: 1.6,
            }}
          >
            <Typography.Text style={{ color: "inherit", fontSize: 15 }}>
              {displayText}
            </Typography.Text>
          </div>
        )}

        {/* 视频（从 content 解析） */}
        {videos.map((src, i) => (
          <div key={i} style={{ marginTop: 6 }}>
            <video
              src={src}
              controls
              preload="metadata"
              style={{ maxWidth: "100%", maxHeight: 360, borderRadius: 8, background: "#000" }}
            />
          </div>
        ))}

        {/* 已保存的图片（从 content 解析） */}
        {images.map((img, i) => (
          <div key={i} style={{ marginTop: 6 }}>
            <Image
              src={img.url}
              alt={img.alt}
              style={{ maxWidth: "100%", maxHeight: 300, borderRadius: 8 }}
              placeholder
            />
            <div style={{ marginTop: 4 }}>
              <Button
                type="text"
                size="small"
                icon={promptExpanded ? <DownOutlined /> : <RightOutlined />}
                onClick={() => setPromptExpanded(!promptExpanded)}
                style={{ color: "#999", fontSize: 11, padding: 0 }}
              >
                提示词
              </Button>
              {promptExpanded && (
                <Typography.Paragraph
                  type="secondary"
                  style={{ fontSize: 11, margin: "4px 0 0 0", padding: "4px 8px",
                    background: "#fafafa", borderRadius: 4 }}
                >
                  {img.alt}
                </Typography.Paragraph>
              )}
            </div>
          </div>
        ))}

        {/* 生成按钮 + 刚生成的结果 — 仅 assistant 消息 */}
        {!isUser && (
          <div style={{ marginTop: 6 }}>
            {genState.loading ? (
              <Spin size="small" />
            ) : !genState.imageUrl ? (
              <Button
                type="text"
                size="small"
                icon={<CameraOutlined />}
                onClick={handleGenerate}
                style={{ color: "#999", fontSize: 12 }}
              >
                生成画面
              </Button>
            ) : null}

            {genState.imageUrl && (
              <div style={{ marginTop: 8 }}>
                <Image
                  src={genState.imageUrl}
                  alt={genState.prompt || "generated"}
                  style={{ maxWidth: "100%", maxHeight: 300, borderRadius: 8 }}
                  placeholder
                />
                {genState.prompt && (
                  <div style={{ marginTop: 4 }}>
                    <Button
                      type="text"
                      size="small"
                      icon={promptExpanded ? <DownOutlined /> : <RightOutlined />}
                      onClick={() => setPromptExpanded(!promptExpanded)}
                      style={{ color: "#999", fontSize: 11, padding: 0 }}
                    >
                      提示词
                    </Button>
                    {promptExpanded && (
                      <Typography.Paragraph
                        type="secondary"
                        style={{ fontSize: 11, margin: "4px 0 0 0", padding: "4px 8px",
                          background: "#fafafa", borderRadius: 4 }}
                      >
                        {genState.prompt}
                      </Typography.Paragraph>
                    )}
                  </div>
                )}
                <Button
                  type="text"
                  size="small"
                  icon={<CameraOutlined />}
                  onClick={handleGenerate}
                  style={{ color: "#999", fontSize: 12, marginTop: 4 }}
                >
                  重新生成
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
