import { Alert, Button, Card, Form, Input, Select, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { api, type LoginRes, type RegisterStatus, setToken } from "../api";

function errMsg(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const d = e.response?.data as { detail?: string | Array<{ msg?: string }> } | undefined;
    if (typeof d?.detail === "string") return d.detail;
    if (Array.isArray(d?.detail)) return d.detail.map((x) => x.msg).filter(Boolean).join("; ") || "请求无效";
  }
  return String(e);
}

function RegisterForm({
  status,
  onFinish,
}: {
  status: RegisterStatus;
  onFinish: (v: {
    username: string;
    password: string;
    password_confirm: string;
    role?: "admin" | "user";
  }) => void;
}) {
  return (
    <Card className="plant-auth-card" title="注册账号">
      <Typography.Paragraph type="secondary" style={{ marginTop: -8 }}>
        填写登录用户名即可注册，初始密码默认为 <strong>zkbz2026</strong>。
      </Typography.Paragraph>
      <Form layout="vertical" onFinish={onFinish} initialValues={{ role: "user" }} size="large">

        <Form.Item
          name="username"
          label="登录用户名"
          extra="至少 2 个字符，用于以后登录。"
          rules={[{ required: true, min: 2, max: 64 }]}
        >
          <Input autoComplete="username" placeholder="例如 zhangsan" />
        </Form.Item>

        <Button type="primary" htmlType="submit" block size="large">
          注册并登录
        </Button>
        <div style={{ marginTop: 16, textAlign: "center" }}>
          <Link to="/login">已有账号？去登录</Link>
        </div>
      </Form>
    </Card>
  );
}

export default function RegisterPage() {
  const nav = useNavigate();
  const [status, setStatus] = useState<RegisterStatus | null>(null);

  useEffect(() => {
    api
      .get<RegisterStatus>("/auth/register-status")
      .then((r) => setStatus(r.data))
      .catch(() => setStatus({ enabled: false, allow_admin: false }));
  }, []);

  async function onFinish(v: {
    username: string;
    role?: "admin" | "user";
  }) {
    if (!status) return;
    try {
      const { data } = await api.post<LoginRes>("/auth/register", {
        username: v.username,
        password: "zkbz2026",
        password_confirm: "zkbz2026",
        role: status.allow_admin ? ((v.role ?? "user") as "admin" | "user") : "user",
      });
      setToken(data.access_token);
      message.success("注册成功");
      nav("/plants", { replace: true });
    } catch (e: unknown) {
      message.error(errMsg(e));
    }
  }

  if (status === null) {
    return (
      <div className="plant-auth-bg">
        <div className="plant-auth-left">
          <h1>中国植物库</h1>
          <p>正在加载注册配置…</p>
        </div>
        <div className="plant-auth-right">
          <Card className="plant-auth-card">加载中…</Card>
        </div>
      </div>
    );
  }

  if (!status.enabled) {
    return (
      <div className="plant-auth-bg">
        <div className="plant-auth-left">
          <h1>中国植物库</h1>
          <p>注册入口暂时关闭时，请联系管理员在后台创建账号。</p>
        </div>
        <div className="plant-auth-right">
          <Card className="plant-auth-card" title="注册">
            <Alert type="warning" message="注册功能已关闭" showIcon style={{ marginBottom: 16 }} />
            <Link to="/login">返回登录</Link>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="plant-auth-bg">
      <div className="plant-auth-left">
        <h1>中国植物库</h1>
        <p>创建管理控制台普通用户账号。请输入您的用户名进行注册，初始密码默认为 zkbz2026，注册成功后将自动进入系统。</p>
      </div>
      <div className="plant-auth-right">
        <RegisterForm status={status} onFinish={onFinish} />
      </div>
    </div>
  );
}
