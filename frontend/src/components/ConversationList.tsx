import { Button, List, Popconfirm, Typography, Dropdown } from "antd";
import {
  PlusOutlined,
  DeleteOutlined,
  MessageOutlined,
  ClearOutlined,
  VideoCameraOutlined,
  BranchesOutlined,
} from "@ant-design/icons";
import type { Conversation } from "../types";

interface Props {
  conversations: Conversation[];
  currentId: number | null;
  onSelect: (id: number) => void;
  onNew: () => void;
  onNewVideo: () => void;
  onDelete: (id: number) => void;
  onClearAll: () => void;
}

export default function ConversationList({
  conversations,
  currentId,
  onSelect,
  onNew,
  onNewVideo,
  onDelete,
  onClearAll,
}: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ padding: 12 }}>
        <Dropdown
          menu={{
            items: [
              { key: "chat", label: "新建聊天", icon: <MessageOutlined /> },
              { key: "video", label: "新建图生视频", icon: <VideoCameraOutlined /> },
            ],
            onClick: ({ key }) => (key === "video" ? onNewVideo() : onNew()),
          }}
          placement="bottom"
          trigger={["click"]}
        >
          <Button type="primary" icon={<PlusOutlined />} block>
            新建会话
          </Button>
        </Dropdown>
      </div>

      <List
        style={{ flex: 1, overflow: "auto" }}
        dataSource={conversations}
        renderItem={(item) => (
          <List.Item
            onClick={() => onSelect(item.id)}
            style={{
              cursor: "pointer",
              padding: "12px 16px",
              background: item.id === currentId ? "#e6f4ff" : undefined,
              borderLeft: item.id === currentId ? "3px solid #1677ff" : "3px solid transparent",
            }}
            actions={[
              <Popconfirm
                key="delete"
                title="删除此会话？"
                onConfirm={(e) => { e?.stopPropagation(); onDelete(item.id); }}
                onCancel={(e) => e?.stopPropagation()}
              >
                <Button
                  type="text" size="small" danger
                  icon={<DeleteOutlined />}
                  onClick={(e) => e.stopPropagation()}
                />
              </Popconfirm>,
            ]}
          >
            <List.Item.Meta
              avatar={
                item.conv_type === "video" ? (
                  <VideoCameraOutlined style={{ fontSize: 18, color: "#722ed1" }} />
                ) : item.parent_conversation_id ? (
                  <BranchesOutlined style={{ fontSize: 18, color: "#1677ff" }} />
                ) : (
                  <MessageOutlined style={{ fontSize: 18, color: "#999" }} />
                )
              }
              title={
                <Typography.Text ellipsis style={{ fontSize: 14 }}>
                  {item.title}
                </Typography.Text>
              }
              description={
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {new Date(item.updated_at).toLocaleDateString()}
                </Typography.Text>
              }
            />
          </List.Item>
        )}
        locale={{ emptyText: "暂无会话" }}
      />

      {/* 清除所有 */}
      <div style={{ padding: 12, borderTop: "1px solid #f0f0f0" }}>
        <Popconfirm
          title="确定要清除所有聊天记录吗？此操作不可撤销。"
          onConfirm={onClearAll}
          okText="确定"
          cancelText="取消"
        >
          <Button danger icon={<ClearOutlined />} block>
            清除所有聊天
          </Button>
        </Popconfirm>
      </div>
    </div>
  );
}
