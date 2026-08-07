import { useState, useRef, useEffect } from "react";
import { Input, Button } from "antd";
import { SendOutlined } from "@ant-design/icons";

interface Props {
  onSend: (content: string) => void;
  loading: boolean;
}

export default function MessageInput({ onSend, loading }: Props) {
  const [value, setValue] = useState("");
  const inputRef = useRef<any>(null);

  // 发送后自动聚焦
  useEffect(() => {
    if (!loading && inputRef.current) {
      inputRef.current.focus();
    }
  }, [loading]);

  const handleSend = () => {
    const text = value.trim();
    if (!text || loading) return;
    onSend(text);
    setValue("");
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
        onChange={(e) => setValue(e.target.value)}
        onPressEnter={(e) => {
          if (!e.shiftKey) {
            e.preventDefault();
            handleSend();
          }
        }}
        placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
        autoSize={{ minRows: 1, maxRows: 4 }}
        style={{ flex: 1, borderRadius: 20, padding: "6px 12px" }}
        disabled={loading}
      />
      <Button
        type="primary"
        shape="circle"
        icon={<SendOutlined />}
        onClick={handleSend}
        loading={loading}
        disabled={!value.trim()}
        style={{ flexShrink: 0 }}
      />
    </div>
  );
}
