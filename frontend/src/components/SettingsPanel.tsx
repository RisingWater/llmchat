import { useState, useEffect } from "react";
import { Input, Button, App } from "antd";

interface Props {
  systemPrompt: string;
  onSave: (prompt: string) => void;
}

export default function SettingsPanel({ systemPrompt, onSave }: Props) {
  const [value, setValue] = useState(systemPrompt);
  const { message } = App.useApp();

  useEffect(() => {
    setValue(systemPrompt);
  }, [systemPrompt]);

  const handleSave = () => {
    onSave(value.trim() || "You are a helpful assistant.");
    message.success("已保存");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <div style={{ marginBottom: 8, fontWeight: 500, color: "#666" }}>
          系统角色设定
        </div>
        <Input.TextArea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="设定 AI 的角色..."
          autoSize={{ minRows: 4, maxRows: 12 }}
        />
      </div>
      <Button type="primary" onClick={handleSave} block>
        保存
      </Button>
    </div>
  );
}
