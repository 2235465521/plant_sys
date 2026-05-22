import { Button, Card, Form, Input, Typography, message } from "antd";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { api, LoginRes, setToken } from "../api";

export default function LoginPage() {
  const nav = useNavigate();

  async function onFinish(v: { username: string; password: string }) {
    try {
      const { data } = await api.post<LoginRes>("/auth/login", v);
      setToken(data.access_token);
      nav("/plants", { replace: true });
    } catch (e: unknown) {
      if (axios.isAxiosError(e)) {
        const d = e.response?.data as { detail?: string } | undefined;
        message.error(typeof d?.detail === "string" ? d.detail : "登录失败");
      } else message.error(String(e));
    }
  }

  return (
    <div className="plant-auth-bg">
      <div className="plant-auth-left">
        <h1>中国植物库</h1>
        <p>
          分类与标本管理控制台：支持数据浏览、单条导出与权限区分。左侧为内部工具导航风格示意，登录后即可使用全套功能。
        </p>
      </div>
      <div className="plant-auth-right">
        <Card className="plant-auth-card" title="登录">
          <Typography.Paragraph type="secondary" style={{ marginTop: -8 }}>
            无账号可前往注册（若管理员已开放）。
          </Typography.Paragraph>
          <Form layout="vertical" onFinish={onFinish} size="large">
            <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
              <Input autoComplete="username" placeholder="登录用户名" />
            </Form.Item>
            <Form.Item name="password" label="密码" rules={[{ required: true }]}>
              <Input.Password autoComplete="current-password" placeholder="密码" />
            </Form.Item>
            <Button type="primary" htmlType="submit" block size="large">
              登录
            </Button>
            <div style={{ marginTop: 16, textAlign: "center" }}>
              <Link to="/register">注册账号</Link>
            </div>
          </Form>
        </Card>
      </div>
    </div>
  );
}
