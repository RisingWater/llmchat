import { useState, useEffect } from "react";
import { Input, Button, App, Segmented } from "antd";
import type { ModelOption } from "../types";

interface Props {
  systemPrompt: string;
  model: string;
  models: ModelOption[];
  onSave: (prompt: string, model: string) => void;
}

export default function SettingsPanel({ systemPrompt, model, models, onSave }: Props) {
  const [value, setValue] = useState(systemPrompt);
  const [selectedModel, setSelectedModel] = useState(model);
  const { message } = App.useApp();

  useEffect(() => {
    setValue(systemPrompt);
  }, [systemPrompt]);

  useEffect(() => {
    setSelectedModel(model);
  }, [model]);

  const handleSave = () => {
    onSave(value.trim() || "You are a helpful assistant.", selectedModel);
    message.success("已保存");
  };

  const options = models.length
    ? models.map((m) => ({
        value: m.id,
        label: `${m.label} ${Math.round(m.context / 1000)}K`,
      }))
    : [{ value: "deepseek", label: "DeepSeek 200K" }];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <div style={{ marginBottom: 8, fontWeight: 500, color: "#666" }}>
          模型
        </div>
        <Segmented
          block
          value={selectedModel}
          onChange={(v) => setSelectedModel(String(v))}
          options={options}
        />
      </div>
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
