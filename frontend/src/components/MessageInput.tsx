import { useRef, useEffect } from "react";
import { Input, Button } from "antd";
import { SendOutlined, HighlightOutlined } from "@ant-design/icons";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  loading: boolean;
  placeholder?: string;
  // 图生视频模式：显示"润色"按钮，回车触发润色而非直接发送
  polishable?: boolean;
  onPolish?: () => void;
  polishLoading?: boolean;
}

export default function MessageInput({
  value,
  onChange,
  onSend,
  loading,
  placeholder,
  polishable,
  onPolish,
  polishLoading,
}: Props) {
  const inputRef = useRef<any>(null);

  // 发送/润色完成后自动聚焦
  useEffect(() => {
    if (!loading && !polishLoading && inputRef.current) {
      inputRef.current.focus();
    }
  }, [loading, polishLoading]);

  const handleSend = () => {
    if (!value.trim() || loading) return;
    onSend();
  };

  const handleEnter = () => {
    if (!value.trim() || loading) return;
    if (polishable) {
      onPolish?.();
    } else {
      onSend();
    }
  };

  return (
    <div
      style={{
        display: "flex",
        gap: 8,
        padding: "8px 12px",
        paddingBottom: "max(8px, env(safe-area-inset-bottom))",
        background: "#fff",
        borderTop: "1px solid #f0f0f0",
        flexShrink: 0,
      }}
    >
      <Input.TextArea
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onPressEnter={(e) => {
          if (!e.shiftKey) {
            e.preventDefault();
            handleEnter();
          }
        }}
        placeholder={placeholder || "输入消息... (Enter 发送, Shift+Enter 换行)"}
        autoSize={{ minRows: 1, maxRows: 4 }}
        style={{ flex: 1, borderRadius: 20, padding: "6px 12px" }}
        disabled={loading}
      />
      {polishable && (
        <Button
          icon={<HighlightOutlined />}
          onClick={onPolish}
          loading={polishLoading}
          disabled={!value.trim()}
          style={{ flexShrink: 0 }}
        >
          润色
        </Button>
      )}
      {polishable ? (
        <Button
          type="primary"
          onClick={handleSend}
          loading={loading}
          disabled={!value.trim()}
          style={{ flexShrink: 0 }}
        >
          开始制作
        </Button>
      ) : (
        <Button
          type="primary"
          shape="circle"
          icon={<SendOutlined />}
          onClick={handleSend}
          loading={loading}
          disabled={!value.trim()}
          style={{ flexShrink: 0 }}
        />
      )}
    </div>
  );
}