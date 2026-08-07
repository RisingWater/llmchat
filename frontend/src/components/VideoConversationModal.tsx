import { useState } from "react";
import { Modal, Upload, Input, App, Spin } from "antd";
import { InboxOutlined } from "@ant-design/icons";
import type { UploadFile } from "antd";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreate: (file: File, title?: string) => Promise<void>;
}

export default function VideoConversationModal({ open, onClose, onCreate }: Props) {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [title, setTitle] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { message } = App.useApp();

  const handleOk = async () => {
    const file = fileList[0]?.originFileObj;
    if (!file) {
      message.warning("请先上传第一张图片");
      return;
    }
    setSubmitting(true);
    try {
      await onCreate(file, title.trim() || undefined);
      setFileList([]);
      setTitle("");
      onClose();
    } catch (err: any) {
      message.error(err.message || "创建失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    if (submitting) return;
    setFileList([]);
    setTitle("");
    onClose();
  };

  return (
    <Modal
      title="新建图生视频会话"
      open={open}
      onOk={handleOk}
      onCancel={handleClose}
      okText="创建"
      cancelText="取消"
      confirmLoading={submitting}
      destroyOnClose
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ color: "#666", fontSize: 13 }}>
          上传第一张图片作为起始画面，后续每段视频的最后一帧会自动作为下一次的输入
        </div>
        <Upload.Dragger
          accept="image/*"
          maxCount={1}
          fileList={fileList}
          beforeUpload={() => false}
          onChange={({ fileList: fl }) => setFileList(fl.slice(-1))}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽上传起始图片</p>
          <p className="ant-upload-hint">支持 PNG / JPG 等格式</p>
        </Upload.Dragger>
        <Input
          placeholder="会话名称（可选，默认：图生视频）"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={50}
        />
        {submitting && <Spin size="small" />}
      </div>
    </Modal>
  );
}
