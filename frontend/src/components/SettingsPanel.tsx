import { useState, useEffect } from "react";
import { Input, InputNumber, Button, App, Segmented } from "antd";
import type { ModelOption } from "../types";

interface Props {
  systemPrompt: string;
  model: string;
  models: ModelOption[];
  maxTokens: number;
  onSave: (prompt: string, model: string, maxTokens: number) => void;
}

export default function SettingsPanel({
  systemPrompt,
  model,
  models,
  maxTokens,
  onSave,
}: Props) {
  const [value, setValue] = useState(systemPrompt);
  const [selectedModel, setSelectedModel] = useState(model);
  const [maxOutput, setMaxOutput] = useState(maxTokens);
  const { message } = App.useApp();

  useEffect(() => {
    setValue(systemPrompt);
  }, [systemPrompt]);

  useEffect(() => {
    setSelectedModel(model);
  }, [model]);

  useEffect(() => {
    setMaxOutput(maxTokens);
  }, [maxTokens]);

  const handleSave = () => {
    onSave(
      value.trim() || "You are a helpful assistant.",
      selectedModel,
      Math.max(1, Math.round(maxOutput || 10000))
    );
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
          最大输出
        </div>
        <InputNumber
          value={maxOutput}
          onChange={(v) => setMaxOutput(typeof v === "number" ? v : 10000)}
          min={1}
          step={1000}
          addonAfter="token"
          style={{ width: "100%" }}
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
