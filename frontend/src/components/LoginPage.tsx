import { useState } from "react";
import { Form, Input, Button, Card, Typography, App } from "antd";
import { LockOutlined } from "@ant-design/icons";

interface Props {
  onLogin: (password: string) => Promise<void>;
}

export default function LoginPage({ onLogin }: Props) {
  const [loading, setLoading] = useState(false);
  const { message } = App.useApp();

  const handleSubmit = async (values: { password: string }) => {
    setLoading(true);
    try {
      await onLogin(values.password);
    } catch (err: any) {
      message.error(err.message || "密码错误");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        padding: 24,
      }}
    >
      <Card style={{ width: "100%", maxWidth: 360, borderRadius: 12 }}>
        <Typography.Title level={3} style={{ textAlign: "center", marginBottom: 24 }}>
          LLM Chat
        </Typography.Title>
        <Form onFinish={handleSubmit} size="large">
          <Form.Item
            name="password"
            rules={[{ required: true, message: "请输入密码" }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="登录密码"
              autoFocus
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
