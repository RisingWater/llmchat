import { useState } from "react";
import { Layout, Button, Typography, Drawer } from "antd";
import {
  MenuOutlined,
  SettingOutlined,
  LogoutOutlined,
} from "@ant-design/icons";
import type { Conversation, Message } from "../types";
import ConversationList from "./ConversationList";
import ChatArea from "./ChatArea";
import SettingsPanel from "./SettingsPanel";
import VideoSettingsPanel from "./VideoSettingsPanel";

const { Header, Content } = Layout;

interface Props {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  streaming: string;
  loading: boolean;
  videoGenerating: boolean;
  onSelectConversation: (id: number) => void;
  onNewConversation: () => void;
  onNewVideoConversation: () => void;
  onDeleteConversation: (id: number) => void;
  onClearAll: () => void;
  onSendMessage: (content: string) => void;
  onUpdateSystemPrompt: (prompt: string) => void;
  onUpdateVideoSettings: (megapixels: number, steps: number, duration: number) => void;
  onLogout: () => void;
}

export default function AppLayout({
  conversations,
  currentConversation,
  messages,
  streaming,
  loading,
  videoGenerating,
  onSelectConversation,
  onNewConversation,
  onNewVideoConversation,
  onDeleteConversation,
  onClearAll,
  onSendMessage,
  onUpdateSystemPrompt,
  onUpdateVideoSettings,
  onLogout,
}: Props) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <Layout style={{ height: "100dvh", display: "flex", flexDirection: "column", minHeight: 0 }}>
      <Header
        style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "0 12px", background: "#fff", borderBottom: "1px solid #f0f0f0",
          height: 48, lineHeight: "48px", flexShrink: 0,
        }}
      >
        <Button type="text" icon={<MenuOutlined />} onClick={() => setDrawerOpen(true)} />
        <Typography.Text
          ellipsis
          style={{ flex: 1, textAlign: "center", margin: "0 12px", fontSize: 16, fontWeight: 500 }}
        >
          {currentConversation?.title || "LLM Chat"}
        </Typography.Text>
        <div style={{ display: "flex", gap: 4 }}>
          <Button type="text" icon={<SettingOutlined />} onClick={() => setSettingsOpen(true)} />
          <Button type="text" icon={<LogoutOutlined />} onClick={onLogout} danger />
        </div>
      </Header>

      <Content style={{ flex: 1, minHeight: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <ChatArea
          messages={messages}
          streaming={streaming}
          loading={loading}
          videoGenerating={videoGenerating}
          conversationId={currentConversation?.id ?? null}
          isVideo={currentConversation?.conv_type === "video"}
          onSend={onSendMessage}
        />
      </Content>

      <Drawer
        title="会话列表" placement="left" open={drawerOpen}
        onClose={() => setDrawerOpen(false)} width={280}
        styles={{ body: { padding: 0 } }}
      >
        <ConversationList
          conversations={conversations}
          currentId={currentConversation?.id || null}
          onSelect={(id) => { onSelectConversation(id); setDrawerOpen(false); }}
          onNew={() => { onNewConversation(); setDrawerOpen(false); }}
          onNewVideo={() => { onNewVideoConversation(); setDrawerOpen(false); }}
          onDelete={onDeleteConversation}
          onClearAll={onClearAll}
        />
      </Drawer>

      <Drawer
        title="会话设置" placement="right" open={settingsOpen}
        onClose={() => setSettingsOpen(false)} width={300}
      >
        {currentConversation?.conv_type === "video" ? (
          <VideoSettingsPanel
            megapixels={currentConversation?.megapixels ?? 0.4}
            steps={currentConversation?.steps ?? 16}
            duration={currentConversation?.duration ?? 5}
            onSave={(mp, st, dur) => { onUpdateVideoSettings(mp, st, dur); setSettingsOpen(false); }}
          />
        ) : (
          <SettingsPanel
            systemPrompt={currentConversation?.system_prompt || ""}
            onSave={(prompt) => { onUpdateSystemPrompt(prompt); setSettingsOpen(false); }}
          />
        )}
      </Drawer>
    </Layout>
  );
}
