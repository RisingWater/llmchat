import { useState, useEffect } from "react";
import { InputNumber, Button, Switch, App } from "antd";

interface Props {
  megapixels: number;
  steps: number;
  duration: number;
  keepAudio: boolean;
  onSave: (megapixels: number, steps: number, duration: number, keepAudio: boolean) => void;
}

export default function VideoSettingsPanel({ megapixels, steps, duration, keepAudio, onSave }: Props) {
  const [mp, setMp] = useState(megapixels);
  const [st, setSt] = useState(steps);
  const [dur, setDur] = useState(duration);
  const [ka, setKa] = useState(keepAudio);
  const { message } = App.useApp();

  useEffect(() => {
    setMp(megapixels);
    setSt(steps);
    setDur(duration);
    setKa(keepAudio);
  }, [megapixels, steps, duration, keepAudio]);

  const handleSave = () => {
    onSave(mp || 0.8, st || 8, dur || 5, ka);
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
              onChange={(v) => setMp(v ?? 0.8)}
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
              onChange={(v) => setSt(v ?? 8)}
              style={{ width: "100%" }}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4, color: "#999", fontSize: 12 }}>
              视频时长（秒）
            </div>
            <InputNumber
              value={dur}
              min={5}
              max={60}
              step={1}
              onChange={(v) => setDur(v ?? 5)}
              style={{ width: "100%" }}
            />
          </div>
          <div
            style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "8px 12px", background: "#fafafa", borderRadius: 8,
            }}
          >
            <span style={{ color: "#666", fontSize: 13 }}>保留音频</span>
            <Switch checked={ka} onChange={setKa} size="small" />
          </div>
        </div>
      </div>
      <Button type="primary" onClick={handleSave} block>
        保存
      </Button>
    </div>
  );
}