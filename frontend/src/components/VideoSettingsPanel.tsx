import { useState, useEffect } from "react";
import { InputNumber, Button, App } from "antd";

interface Props {
  megapixels: number;
  steps: number;
  onSave: (megapixels: number, steps: number) => void;
}

export default function VideoSettingsPanel({ megapixels, steps, onSave }: Props) {
  const [mp, setMp] = useState(megapixels);
  const [st, setSt] = useState(steps);
  const { message } = App.useApp();

  useEffect(() => {
    setMp(megapixels);
    setSt(steps);
  }, [megapixels, steps]);

  const handleSave = () => {
    onSave(mp || 0.4, st || 16);
    message.success("已保存");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <div style={{ marginBottom: 8, color: "#666", fontSize: 13 }}>
          视频生成参数
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <div style={{ marginBottom: 4, color: "#999", fontSize: 12 }}>
              分辨率（百万像素）
            </div>
            <InputNumber
              value={mp}
              min={0.1}
              max={16}
              step={0.1}
              onChange={(v) => setMp(v ?? 0.4)}
              style={{ width: "100%" }}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4, color: "#999", fontSize: 12 }}>
              采样步数
            </div>
            <InputNumber
              value={st}
              min={1}
              max={100}
              step={1}
              onChange={(v) => setSt(v ?? 16)}
              style={{ width: "100%" }}
            />
          </div>
        </div>
      </div>
      <Button type="primary" onClick={handleSave} block>
        保存
      </Button>
    </div>
  );
}