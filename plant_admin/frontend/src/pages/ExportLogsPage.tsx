import { Table, Typography } from "antd";
import { useCallback, useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { api, ExportLog } from "../api";

interface ListRes {
  items: ExportLog[];
  total: number;
  page: number;
  page_size: number;
}

type OutletCtx = { taxonLevel?: string };

export default function ExportLogsPage() {
  useOutletContext<OutletCtx>();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ExportLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data: res } = await api.get<ListRes>("/export-logs", {
        params: { page, page_size: pageSize },
      });
      setData(res.items);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="rounded-lg border border-outline-variant bg-surface-container-lowest p-6">
      <div className="mb-6 flex flex-col gap-1 border-b border-outline-variant pb-4">
        <div className="font-label-sm text-label-sm text-on-surface-variant">首页 / 归档</div>
        <Typography.Title level={4} className="!mb-0 !text-h3 !font-semibold text-on-surface">
          导出记录
        </Typography.Title>
        <Typography.Text type="secondary" className="text-body-md">
          导出物种文本（TXT）、本站图片 JPG 下载等操作的审计留痕，共 {total} 条
        </Typography.Text>
      </div>
      <Table<ExportLog>
        rowKey="id"
        loading={loading}
        dataSource={data}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          onChange: (p, ps) => {
            setPage(p);
            setPageSize(ps);
          },
        }}
        columns={[
          { title: "时间", dataIndex: "created_at", width: 180 },
          { title: "用户", dataIndex: "username", width: 120 },
          {
            title: "用户类型",
            dataIndex: "user_role",
            width: 100,
            render: (v: ExportLog["user_role"]) =>
              v === "admin" ? "管理员" : v === "user" ? "普通用户" : "—",
          },
          { title: "物种 ID", dataIndex: "plant_id", width: 100 },
          { title: "中文名快照", dataIndex: "plant_name", ellipsis: true },
          { title: "格式", dataIndex: "export_format", width: 80 },
        ]}
      />
    </div>
  );
}
