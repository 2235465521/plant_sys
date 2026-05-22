import {
  DeleteOutlined,
  DownOutlined,
  DownloadOutlined,
  EditOutlined,
  ExportOutlined,
  FileExcelOutlined,
  FileTextOutlined,
  TableOutlined,
} from "@ant-design/icons";
import axios from "axios";
import { Button, Checkbox, Dropdown, Form, Input, Modal, Pagination, Switch, Table, Tooltip, message } from "antd";
import type { MenuProps } from "antd";
import type { Key } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useOutletContext, useSearchParams, Link } from "react-router-dom";
import { api, Plant, getToken, serializeTaxonArrayParams } from "../api";

interface ListRes {
  items: Plant[];
  total: number;
  page: number;
  page_size: number;
}

type TaxonLevel = "division" | "subclass" | "taxonomic_order" | "family" | "genus";

type OutletCtx = { taxonLevel: TaxonLevel };

function taxParamKey(level: TaxonLevel): string {
  return level === "taxonomic_order" ? "torder" : level;
}

function pickSpeciesLabel(p: Plant): string {
  const v = p.vernacular_name?.trim() ?? "";
  if (v) return v;
  const alt = p.alternative_names_zh?.trim() ?? "";
  if (alt) {
    const parts = alt.split(/[,，;；\n/／|｜]/).map((s) => s.trim()).filter(Boolean);
    if (parts.length) return parts[0];
    return alt;
  }
  const sci = p.scientific_name?.trim() ?? "";
  if (sci) return sci;
  return `#${p.id}`;
}

function decodeJwtPayload(token: string): { role?: string } {
  try {
    const p = token.split(".")[1];
    return JSON.parse(atob(p.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return {};
  }
}

function BreadcrumbChevron() {
  return (
    <span className="material-symbols-outlined text-[16px] text-on-surface-variant">chevron_right</span>
  );
}

/** 仅返回浏览器可用的图片地址（http(s)、站内路径）；盘符路径无法在网页中显示 */
function plantMediaSrc(path: string | null | undefined): string | undefined {
  const s = path?.trim();
  if (!s) return undefined;
  if (/^https?:\/\//i.test(s)) return s;
  if (s.startsWith("/")) return s;
  return undefined;
}

function normalizeImageServerPaths(paths: string[] | null | undefined): string[] {
  if (!paths || !Array.isArray(paths)) return [];
  return paths.map(String).filter((x) => x.trim());
}

function bustApiMediaUrl(path: string, mediaVersion: number): string | undefined {
  const base = plantMediaSrc(path);
  if (!base) return undefined;
  if (base.startsWith("/api/media/plants/")) {
    return `${base}${base.includes("?") ? "&" : "?"}_=${mediaVersion}`;
  }
  return base;
}

function safeFilenameSegment(s: string, maxLen = 40): string {
  const t = s.replace(/[/\\:*?"<>|\s#\x00-\x1f]/g, "_").replace(/_+/g, "_").slice(0, maxLen);
  return t || "plant";
}

function basenameStemFromRawPath(raw: string): string {
  const stem = raw.split("?", 1)[0]?.trim().replace(/[/\\]+/g, "/") ?? "";
  const file = stem.split("/").pop() ?? "pic";
  return file.replace(/\.[^/.]+$/, "") || "pic";
}

function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  try {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}

async function bitmapToJpegBlob(bitmap: ImageBitmap): Promise<Blob> {
  const canvas = document.createElement("canvas");
  canvas.width = bitmap.width;
  canvas.height = bitmap.height;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("无法创建画布");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, bitmap.width, bitmap.height);
  ctx.drawImage(bitmap, 0, 0);
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (b) => (b ? resolve(b) : reject(new Error("JPEG 导出失败"))),
      "image/jpeg",
      0.92,
    );
  });
}

/** 抓取 URL 后为 JPG（PNG/WebP/GIF 等会铺白底再编码） */
async function fetchUrlAsJpegBlob(imageUrl: string): Promise<Blob> {
  const resp = await fetch(imageUrl);
  if (!resp.ok) throw new Error(`下载失败 (${resp.status})`);
  const bitmap = await createImageBitmap(await resp.blob());
  try {
    return await bitmapToJpegBlob(bitmap);
  } finally {
    bitmap.close?.();
  }
}

function jpegDownloadThrottle(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 350));
}

export default function PlantsPage() {
  const { taxonLevel } = useOutletContext<OutletCtx>();
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";
  const spStr = searchParams.toString();
  const divisions = useMemo(() => {
    const u = new URLSearchParams(spStr);
    return u.getAll("division").map((s) => s.trim()).filter(Boolean);
  }, [spStr]);
  const subclasses = useMemo(() => {
    const u = new URLSearchParams(spStr);
    return u.getAll("subclass").map((s) => s.trim()).filter(Boolean);
  }, [spStr]);
  const torders = useMemo(() => {
    const u = new URLSearchParams(spStr);
    return u.getAll("torder").map((s) => s.trim()).filter(Boolean);
  }, [spStr]);
  const families = useMemo(() => {
    const u = new URLSearchParams(spStr);
    return u.getAll("family").map((s) => s.trim()).filter(Boolean);
  }, [spStr]);
  const genera = useMemo(() => {
    const u = new URLSearchParams(spStr);
    return u.getAll("genus").map((s) => s.trim()).filter(Boolean);
  }, [spStr]);

  const filterKey = useMemo(
    () =>
      [
        q,
        [...divisions].sort().join("\x01"),
        [...subclasses].sort().join("\x01"),
        [...torders].sort().join("\x01"),
        [...families].sort().join("\x01"),
        [...genera].sort().join("\x01"),
      ].join("\0"),
    [q, divisions, subclasses, torders, families, genera],
  );

  const filterCrumbs = useMemo(
    () => [...divisions, ...subclasses, ...torders, ...families, ...genera],
    [divisions, subclasses, torders, families, genera],
  );

  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<Plant[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(36);
  const [selected, setSelected] = useState<Plant | null>(null);
  const [detailTab, setDetailTab] = useState<"morph" | "medicinal">("morph");
  const [imageTab, setImageTab] = useState<"web" | "upload">("web");
  const [showTable, setShowTable] = useState(false);
  const [tableSelectedKeys, setTableSelectedKeys] = useState<Key[]>([]);
  const [cardMultiSelect, setCardMultiSelect] = useState(false);
  const lastCardClickIdx = useRef<number>(-1);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Plant | null>(null);
  const [form] = Form.useForm<Plant>();
  const [mediaVersion, setMediaVersion] = useState(0);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [deletingImage, setDeletingImage] = useState(false);
  const [galleryIdx, setGalleryIdx] = useState(0);
  const [downloadPick, setDownloadPick] = useState<Set<number>>(new Set());
  const [jpegDownloadMode, setJpegDownloadMode] = useState<"idle" | "current" | "batch">("idle");
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const tableExportSectionRef = useRef<HTMLElement>(null);

  const role = useMemo(() => {
    const t = getToken();
    if (!t) return "user";
    return (decodeJwtPayload(t).role as string) || "user";
  }, []);
  const isAdmin = role === "admin";

  const [reloadTick, setReloadTick] = useState(0);

  function bumpPlantListReload() {
    setReloadTick((t) => t + 1);
  }

  useEffect(() => {
    setPage(1);
  }, [filterKey]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api
      .get<ListRes>("/plants", {
        params: {
          page,
          page_size: pageSize,
          q: q || undefined,
          division: divisions,
          subclass: subclasses,
          torder: torders,
          family: families,
          genus: genera,
        },
        paramsSerializer: { serialize: serializeTaxonArrayParams },
      })
      .then(({ data: res }) => {
        if (!alive) return;
        setData(res.items);
        setTotal(res.total);
      })
      .catch((e) => {
        if (!alive) return;
        if (axios.isAxiosError(e)) {
          if (e.code === "ECONNABORTED" || /timeout/i.test(String(e.message))) {
            message.error("请求超时：请确认后端已启动（端口 8000），并通过 npm run dev 访问");
          } else if (!e.response) {
            message.error("无法连接后端：请先启动 uvicorn，再用 npm run dev 打开本站");
          } else {
            const detail = (e.response.data as { detail?: string } | undefined)?.detail;
            message.error(`HTTP ${e.response.status}：${String(detail ?? e.message)}`);
          }
        } else {
          message.error(String(e));
        }
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [page, pageSize, q, divisions, subclasses, torders, families, genera, reloadTick]);

  useEffect(() => {
    if (searchParams.get("add") === "1" && isAdmin) {
      setEditing(null);
      form.resetFields();
      setEditorOpen(true);
      const next = new URLSearchParams(searchParams);
      next.delete("add");
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams, isAdmin, form]);

  useEffect(() => {
    if (data.length === 0) {
      setSelected(null);
      return;
    }
    setSelected((prev) => {
      if (prev && data.some((x) => x.id === prev.id)) return prev;
      return data[0];
    });
  }, [data]);

  useEffect(() => {
    if (!showTable) setTableSelectedKeys([]);
  }, [showTable]);

  useEffect(() => {
    setTableSelectedKeys((keys) => keys.filter((k) => data.some((d) => d.id === k)));
  }, [data]);

  useEffect(() => {
    setGalleryIdx(0);
  }, [selected?.id]);

  async function uploadPlantImages(p: Plant, fileList: FileList | File[]) {
    const files = Array.from(fileList);
    if (!files.length) return;
    if (!getToken()) {
      message.warning("请先登录后再上传");
      return;
    }
    setUploadingImage(true);
    try {
      const body = new FormData();
      for (const f of files) {
        body.append("files", f);
      }
      const { data: updated } = await api.post<Plant>(`/plants/${p.id}/upload-images`, body);
      setSelected(updated);
      setData((rows) => rows.map((r) => (r.id === updated.id ? updated : r)));
      setMediaVersion((ver) => ver + 1);
      const cnt = normalizeImageServerPaths(updated.image_server_paths ?? null).length;
      setGalleryIdx(Math.max(0, cnt - 1));
      message.success(`已上传 ${files.length} 张，库中本站图共 ${cnt} 张（image_server_paths）`);
    } catch (e: unknown) {
      const ax = e as { response?: { data?: { detail?: unknown } } };
      const d = ax.response?.data?.detail;
      const msg =
        typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => String(x)).join("; ") : String(e);
      message.error(msg);
    } finally {
      setUploadingImage(false);
      if (uploadInputRef.current) uploadInputRef.current.value = "";
    }
  }

  function confirmDeleteServerImage(canonicalPath: string | undefined) {
    const path = canonicalPath?.split("?", 1)[0]?.trim();
    if (!selected || !path || !isAdmin || !getToken()) {
      message.warning("仅管理员可删除本站图");
      return;
    }
    Modal.confirm({
      title: "删除这张本站图片？",
      content: (
        <div className="font-body-md text-body-md leading-relaxed text-on-surface-variant">
          <p className="mb-2">
            将从<strong>磁盘</strong>与<strong> image_server_paths </strong>
            中移除（不可撤销）。
          </p>
          <p className="break-all font-mono-data text-mono-data text-on-surface">{path}</p>
        </div>
      ),
      okText: "删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      async onOk() {
        setDeletingImage(true);
        try {
          const { data: updated } = await api.post<Plant>(`/plants/${selected.id}/delete-server-image`, {
            path,
          });
          setSelected(updated);
          setData((rows) => rows.map((r) => (r.id === updated.id ? updated : r)));
          setMediaVersion((v) => v + 1);
          const nextN = normalizeImageServerPaths(updated.image_server_paths ?? null).filter((p) =>
            plantMediaSrc(p),
          ).length;
          setGalleryIdx((i) => (nextN === 0 ? 0 : Math.min(i, nextN - 1)));
          message.success("已从本站移除");
        } catch (e: unknown) {
          const ax = e as { response?: { data?: { detail?: unknown } } };
          const d = ax.response?.data?.detail;
          const msg =
            typeof d === "string"
              ? d
              : Array.isArray(d)
                ? d.map((x) => String(x)).join("; ")
                : String(e);
          message.error(msg);
          throw e;
        } finally {
          setDeletingImage(false);
        }
      },
    });
  }

  async function exportTableSelection(fileFormat: "txt" | "xlsx") {
    let ids: number[];
    if (cardMultiSelect) {
      ids = tableSelectedKeys.map((k) => Number(k)).filter((n) => Number.isInteger(n) && n > 0);
      if (ids.length === 0) {
        message.warning("请先勾选要导出的标本");
        return;
      }
    } else {
      if (!selected) {
        message.warning("请先在物种列表中选一个标本");
        return;
      }
      ids = [selected.id];
    }
    try {
      const res = await api.post(
        "/plants/export-batch",
        { ids, file_format: fileFormat },
        { responseType: "blob" },
      );
      const cd = res.headers["content-disposition"] as string | undefined;
      let filename =
        fileFormat === "xlsx" ? `plants_export_${ids.length}.xlsx` : `plants_export_${ids.length}.txt`;
      if (cd?.includes("filename=")) {
        const m = cd.match(/filename="([^"]+)"/);
        if (m) filename = m[1];
      }
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      const label = fileFormat === "xlsx" ? "Excel" : "文本";
      message.success(`已导出 ${ids.length} 条（${label}），并已记入导出记录`);
    } catch (e: unknown) {
      message.error(String(e));
    }
  }

  const batchExportMenuProps: MenuProps = {
    items: [
      { key: "txt", label: "文本（.txt）", icon: <FileTextOutlined /> },
      { key: "xlsx", label: "Excel（.xlsx）", icon: <FileExcelOutlined /> },
    ],
    onClick: (info) => {
      void exportTableSelection(info.key as "txt" | "xlsx");
    },
  };

  function handleCardClick(e: React.MouseEvent<HTMLButtonElement>, p: Plant, idx: number) {
    setSelected(p);
    if (!cardMultiSelect) return;
    const key = p.id as Key;
    if (e.shiftKey && lastCardClickIdx.current >= 0) {
      const start = Math.min(lastCardClickIdx.current, idx);
      const end = Math.max(lastCardClickIdx.current, idx);
      const rangeKeys = data.slice(start, end + 1).map((item) => item.id as Key);
      setTableSelectedKeys((prev) => Array.from(new Set([...prev, ...rangeKeys])));
    } else if (e.ctrlKey || e.metaKey) {
      setTableSelectedKeys((prev) =>
        prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
      );
    } else {
      setTableSelectedKeys((prev) =>
        prev.length === 1 && prev[0] === key ? [] : [key],
      );
    }
    lastCardClickIdx.current = idx;
  }

  function openEdit(p: Plant) {
    setEditing(p);
    const { image_server_paths: _omit, ...formValues } = p;
    form.setFieldsValue(formValues);
    setEditorOpen(true);
  }

  async function save() {
    try {
      const v = await form.validateFields();
      if (editing) {
        await api.put(`/plants/${editing.id}`, v);
        message.success("已保存");
      } else {
        await api.post("/plants", v);
        message.success("已新增");
      }
      setEditorOpen(false);
      bumpPlantListReload();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || String(e));
    }
  }

  async function remove(p: Plant) {
    Modal.confirm({
      title: "确认删除？",
      content: pickSpeciesLabel(p),
      onOk: async () => {
        await api.delete(`/plants/${p.id}`);
        message.success("已删除");
        bumpPlantListReload();
      },
    });
  }

  const levelLabel = { division: "门", subclass: "亚纲", taxonomic_order: "目", family: "科", genus: "属" }[
    taxonLevel
  ];
  const crumbsFromSelected = selected
    ? [
        selected.division,
        selected.subclass,
        selected.taxonomic_order,
        selected.family,
        selected.genus,
      ].filter(Boolean)
    : [];

  const crumbs = filterCrumbs.length > 0 ? filterCrumbs : crumbsFromSelected;

  const pickedForTitle = searchParams.getAll(taxParamKey(taxonLevel)).filter(Boolean);
  const titleTaxon =
    pickedForTitle.length === 1
      ? pickedForTitle[0]
      : pickedForTitle.length > 1
        ? `「${levelLabel}」等 ${pickedForTitle.length} 项`
        : filterCrumbs.length > 0
          ? `组合筛选 · ${filterCrumbs.length} 项`
          : (selected
              ? (
                  {
                    division: selected.division,
                    subclass: selected.subclass,
                    taxonomic_order: selected.taxonomic_order,
                    family: selected.family,
                    genus: selected.genus,
                  } as Record<TaxonLevel, string | null | undefined>
                )[taxonLevel]?.trim()
              : null) || "全部标本";

  const rawPaths = useMemo(() => normalizeImageServerPaths(selected?.image_server_paths ?? null), [selected]);

  const playableRawPaths = useMemo(() => rawPaths.filter((p) => plantMediaSrc(p)), [rawPaths]);

  useEffect(() => {
    setDownloadPick(new Set());
  }, [selected?.id, playableRawPaths]);

  const playablePreviewUrls = useMemo(
    () =>
      playableRawPaths
        .map((path) => bustApiMediaUrl(path, mediaVersion))
        .filter((url): url is string => Boolean(url)),
    [playableRawPaths, mediaVersion],
  );

  const hasUnplayablePaths = rawPaths.length > 0 && playablePreviewUrls.length === 0;

  useEffect(() => {
    setGalleryIdx((idx) =>
      playablePreviewUrls.length === 0 ? 0 : Math.min(idx, playablePreviewUrls.length - 1),
    );
  }, [playablePreviewUrls.length]);

  const previewSrc = playablePreviewUrls[galleryIdx];

  const imageFilename = useMemo(() => {
    if (!selected) return "—";
    const n = playablePreviewUrls.length;
    if (n >= 1) {
      const raw = playableRawPaths[Math.min(galleryIdx, playableRawPaths.length - 1)] ?? "";
      const base = raw.replace(/[/\\]+/g, "/").split("/").pop() || `img_${selected.id}`;
      return n > 1 ? `${galleryIdx + 1}/${n} · ${base}` : base;
    }
    if (hasUnplayablePaths) return `路径无法在网页显示（${rawPaths.length} 条）`;
    if (selected.image_url?.trim()) return "待上传本站图";
    return `IMG_${selected.id}`;
  }, [
    galleryIdx,
    hasUnplayablePaths,
    playablePreviewUrls.length,
    playableRawPaths,
    rawPaths,
    selected,
  ]);

  function galleryPrev() {
    const n = playablePreviewUrls.length;
    if (n <= 1) return;
    setGalleryIdx((i) => (i - 1 + n) % n);
  }

  function galleryNext() {
    const n = playablePreviewUrls.length;
    if (n <= 1) return;
    setGalleryIdx((i) => (i + 1) % n);
  }

  async function downloadCurrentPreviewJpeg() {
    if (!selected || !previewSrc) return;
    setJpegDownloadMode("current");
    try {
      const jpeg = await fetchUrlAsJpegBlob(previewSrc);
      const slug = safeFilenameSegment(pickSpeciesLabel(selected));
      const idx = galleryIdx + 1;
      const stem = basenameStemFromRawPath(playableRawPaths[galleryIdx] ?? "");
      triggerBlobDownload(jpeg, `${slug}_${idx}_${stem}.jpg`);
      message.success("已开始下载当前图（JPG）");
      void logPlantImageDownload(selected, "current", 1);
    } catch (e: unknown) {
      message.error(String(e));
    } finally {
      setJpegDownloadMode("idle");
    }
  }

  async function downloadPickedImagesAsJpeg() {
    if (!selected) return;
    const indices = [...downloadPick].sort((a, b) => a - b);
    if (indices.length === 0) {
      message.warning("请至少勾选一张本站图片");
      return;
    }
    setJpegDownloadMode("batch");
    try {
      const slug = safeFilenameSegment(pickSpeciesLabel(selected));
      let nOk = 0;
      for (let k = 0; k < indices.length; k++) {
        const i = indices[k];
        const raw = playableRawPaths[i];
        const src = bustApiMediaUrl(raw, mediaVersion);
        if (!src) continue;
        const jpeg = await fetchUrlAsJpegBlob(src);
        const stem = basenameStemFromRawPath(raw);
        triggerBlobDownload(jpeg, `${slug}_${i + 1}_${stem}.jpg`);
        nOk++;
        if (k < indices.length - 1) await jpegDownloadThrottle();
      }
      message.success(`已触发 ${nOk} 个 JPG 下载（若被拦截请在浏览器下载设置中允许）`);
      if (nOk > 0) void logPlantImageDownload(selected, "batch", nOk);
    } catch (e: unknown) {
      message.error(String(e));
    } finally {
      setJpegDownloadMode("idle");
    }
  }

  function toggleDownloadPick(idx: number) {
    setDownloadPick((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }

  function selectAllDownloadPicks() {
    setDownloadPick(new Set(playableRawPaths.map((_, i) => i)));
  }

  function clearDownloadPicks() {
    setDownloadPick(new Set());
  }

  async function logPlantImageDownload(p: Plant, mode: "current" | "batch", imageCount: number) {
    try {
      await api.post(`/plants/${p.id}/log-image-download`, {
        mode,
        image_count: imageCount,
      });
    } catch {
      /* 下载已成功时不打断用户 */
    }
  }

  return (
    <>
      <nav className="mb-6 flex flex-wrap items-center gap-2 font-label-sm text-label-sm text-on-surface-variant">
        {crumbs.length > 0 ? (
          crumbs.map((c, i) => (
            <span key={`${c}-${i}`} className="flex items-center gap-2">
              {i > 0 && <BreadcrumbChevron />}
              <span className={i === crumbs.length - 1 ? "font-semibold text-primary" : ""}>{c}</span>
            </span>
          ))
        ) : (
          <>
            <span>数据浏览</span>
            <BreadcrumbChevron />
            <span className="font-semibold text-primary">全部标本</span>
          </>
        )}
      </nav>

      <div className="grid grid-cols-12 gap-gutter">
        <div className="col-span-12 flex flex-col gap-gutter lg:col-span-8">
          <section className="rounded-lg border border-outline-variant bg-surface-container-lowest p-6">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
              <div className="flex flex-col gap-1">
                <h2 className="font-h3 text-h3 text-on-surface">
                  {levelLabel}内物种列表: {titleTaxon}
                </h2>
                <span className="font-label-sm text-label-sm text-on-surface-variant">
                  共 {total} 个物种
                  {q ? ` · 搜索「${q}」` : ""}
                  {loading ? " · 加载中…" : ""}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Tooltip
                  title={
                    cardMultiSelect
                      ? "点击标签：单选（清除其他）；Ctrl/⌘+点击：追加/取消单个；Shift+点击：范围选中"
                      : "开启后可在物种标签上直接框选，支持 Shift 范围选、Ctrl 单独勾选"
                  }
                >
                  <label className="flex cursor-pointer items-center gap-1.5 rounded border border-outline-variant px-3 py-1.5 font-label-sm text-label-sm text-on-surface-variant select-none">
                    <Switch
                      size="small"
                      checked={cardMultiSelect}
                      onChange={(v) => {
                        setCardMultiSelect(v);
                        if (!v) {
                          setTableSelectedKeys([]);
                          lastCardClickIdx.current = -1;
                        }
                      }}
                    />
                    勾选模式
                    {cardMultiSelect && tableSelectedKeys.length > 0 && (
                      <span className="ml-1 font-semibold text-primary">
                        · {tableSelectedKeys.length} 已选
                      </span>
                    )}
                  </label>
                </Tooltip>
                <Tooltip
                  title={
                    cardMultiSelect
                      ? tableSelectedKeys.length === 0
                        ? "请先勾选标本"
                        : `导出已勾选的 ${tableSelectedKeys.length} 个标本`
                      : selected
                        ? `导出当前标本「${pickSpeciesLabel(selected)}」`
                        : "请先在物种列表中选一个标本"
                  }
                >
                  <Dropdown
                    menu={batchExportMenuProps}
                    disabled={(cardMultiSelect ? tableSelectedKeys.length === 0 : !selected) || loading}
                  >
                    <Button
                      icon={<ExportOutlined />}
                      loading={loading}
                      disabled={(cardMultiSelect ? tableSelectedKeys.length === 0 : !selected) || loading}
                      className="font-label-sm"
                    >
                      导出 <DownOutlined />
                    </Button>
                  </Dropdown>
                </Tooltip>
                <Tooltip title="切换为表格视图，支持列排序与批量勾选导出">
                  <button
                    type="button"
                    onClick={() => setShowTable((v) => !v)}
                    className={`flex items-center gap-2 rounded border border-outline-variant px-3 py-1.5 font-label-sm text-label-sm transition-colors ${
                      showTable
                        ? "bg-primary-container text-on-primary-container"
                        : "text-on-surface-variant hover:bg-surface-container"
                    }`}
                  >
                    <TableOutlined />
                    表格视图
                  </button>
                </Tooltip>
              </div>
            </div>
            {!showTable && (
              <div className="grid grid-cols-3 gap-gutter sm:grid-cols-6">
                {data.map((p, idx) => {
                  const active = selected?.id === p.id;
                  const checked = cardMultiSelect && tableSelectedKeys.includes(p.id as Key);
                  const label = pickSpeciesLabel(p);
                  return (
                    <button
                      key={p.id}
                      type="button"
                      title={label}
                      onClick={(e) => handleCardClick(e, p, idx)}
                      className={`relative flex h-12 w-full min-w-0 cursor-pointer items-center justify-center rounded border px-2 py-0 text-center font-label-sm text-label-sm font-medium transition-all ${
                        checked
                          ? "border-primary bg-primary/20 font-semibold text-primary ring-1 ring-primary"
                          : active
                            ? "border-primary bg-primary/10 font-semibold text-primary"
                            : "border-outline-variant bg-surface-container-low text-on-surface-variant hover:border-primary hover:bg-primary/10 hover:text-primary"
                      }`}
                    >
                      {checked && (
                        <span className="material-symbols-outlined absolute right-0.5 top-0.5 text-[12px] text-primary"
                          style={{ fontVariationSettings: "'FILL' 1" }}>
                          check_circle
                        </span>
                      )}
                      <span className="block w-full truncate">{label}</span>
                    </button>
                  );
                })}
              </div>
            )}
            <div className="mt-6 flex justify-end">
              <Pagination
                current={page}
                pageSize={pageSize}
                total={total}
                showSizeChanger={false}
                onChange={(p) => setPage(p)}
                disabled={loading}
              />
            </div>
          </section>

          {showTable && (
            <section
              ref={tableExportSectionRef}
              className="rounded-lg border border-outline-variant bg-surface-container-lowest p-4"
            >
              <div className="mb-3 flex flex-col gap-2 border-b border-outline-variant pb-3">
                <p className="font-label-sm text-label-sm text-on-surface-variant">
                  表格视图：<span className="text-on-surface">先勾选左侧行</span>，再点「导出」选择
                  <strong className="text-on-surface"> 文本（.txt） </strong>或
                  <strong className="text-on-surface"> Excel（.xlsx） </strong>。
                </p>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <Dropdown menu={batchExportMenuProps} disabled={tableSelectedKeys.length === 0 || loading}>
                    <Button type="primary" icon={<ExportOutlined />} disabled={tableSelectedKeys.length === 0 || loading}>
                      导出 <DownOutlined />
                    </Button>
                  </Dropdown>
                  <span className="font-label-sm text-on-surface-variant">
                    已选 <span className="font-semibold text-on-surface">{tableSelectedKeys.length}</span> 条 · 本页共{" "}
                    {data.length} 条（表头可多选 / 全选本页 / 反选）
                  </span>
                </div>
              </div>
              <Table<Plant>
                size="small"
                rowKey="id"
                loading={loading}
                dataSource={data}
                pagination={false}
                scroll={{ x: isAdmin ? 820 : 700 }}
                rowClassName={(p) =>
                  selected?.id === p.id ? "ant-table-row-selected cursor-pointer" : "cursor-pointer"
                }
                onRow={(p) => ({
                  onClick: (e) => {
                    // Don't double-fire when clicking the checkbox cell itself
                    if ((e.target as HTMLElement).closest(".ant-checkbox-wrapper")) return;
                    setSelected(p);
                    setTableSelectedKeys((prev) => {
                      const key = p.id as Key;
                      return prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key];
                    });
                  },
                })}
                rowSelection={{
                  selectedRowKeys: tableSelectedKeys,
                  onChange: setTableSelectedKeys,
                  selections: [Table.SELECTION_ALL, Table.SELECTION_INVERT, Table.SELECTION_NONE],
                }}
                columns={[
                  { title: "ID", dataIndex: "id", width: 64 },
                  {
                    title: "中文名",
                    dataIndex: "vernacular_name",
                    width: 120,
                    render: (_, r) => pickSpeciesLabel(r as Plant),
                  },
                  { title: "拉丁名", dataIndex: "scientific_name", ellipsis: true },
                  { title: "属", dataIndex: "genus", width: 80 },
                  { title: "科", dataIndex: "family", width: 80 },
                  ...(isAdmin
                    ? [
                        {
                          title: "操作",
                          key: "actions",
                          width: 120,
                          render: (_: unknown, p: Plant) => (
                            <>
                              <Button type="link" size="small" onClick={() => openEdit(p)}>
                                编辑
                              </Button>
                              <Button type="link" size="small" danger onClick={() => remove(p)}>
                                删
                              </Button>
                            </>
                          ),
                        },
                      ]
                    : []),
                ]}
              />
            </section>
          )}

          <section className="flex flex-1 flex-col rounded-lg border border-outline-variant bg-surface-container-lowest">
            <div className="flex border-b border-outline-variant px-6">
              <button
                type="button"
                onClick={() => setDetailTab("morph")}
                className={`mr-8 py-4 font-label-sm text-label-sm ${
                  detailTab === "morph"
                    ? "border-b-2 border-primary font-semibold text-primary"
                    : "text-on-surface-variant hover:text-primary"
                }`}
              >
                一般形状
              </button>
              <button
                type="button"
                onClick={() => setDetailTab("medicinal")}
                className={`py-4 font-label-sm text-label-sm ${
                  detailTab === "medicinal"
                    ? "border-b-2 border-primary font-semibold text-primary"
                    : "text-on-surface-variant hover:text-primary"
                }`}
              >
                药用价值
              </button>
            </div>
            <div className="p-6">
              {selected ? (
                <div className="max-w-none font-body-md leading-relaxed text-on-surface-variant">
                  {detailTab === "morph" ? (
                    <div className="whitespace-pre-wrap text-on-surface">
                      {selected.morphology_text?.trim() || "暂无描述"}
                    </div>
                  ) : (
                    <p className="mb-4">
                      <span className="font-semibold text-on-surface">药用形状：</span>{" "}
                      {selected.medicinal_shape?.trim() || "暂无记载"}
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-on-surface-variant">请选择上方标签中的物种</p>
              )}
            </div>
          </section>
        </div>

        <div className="col-span-12 flex flex-col gap-gutter lg:col-span-4">
          <section className="relative flex h-full min-h-[480px] flex-col overflow-visible rounded-lg border border-outline-variant bg-surface-container-lowest">
            <Link
              to="/export-logs"
              className="absolute right-2 top-0 z-20 flex max-w-[min(100%-1rem,20rem)] -translate-y-[calc(100%+10px)] items-center gap-2 rounded-lg border border-primary/50 bg-surface-container-lowest/95 px-3 py-2 font-body-md text-body-md font-semibold text-primary shadow-md backdrop-blur-sm transition-colors hover:border-primary hover:bg-primary-container/25 sm:px-4 sm:py-2.5"
            >
              <span className="material-symbols-outlined shrink-0 text-[22px] sm:text-[24px]">
                download_for_offline
              </span>
              <span className="truncate">查看导出记录</span>
            </Link>
            <div className="flex border-b border-outline-variant">
              <button
                type="button"
                onClick={() => setImageTab("web")}
                className={`flex-1 py-4 text-center font-label-sm text-label-sm ${
                  imageTab === "web"
                    ? "border-b-2 border-primary font-semibold text-primary"
                    : "text-on-surface-variant hover:bg-surface-container"
                }`}
              >
                网络图片链接
              </button>
              <button
                type="button"
                onClick={() => setImageTab("upload")}
                className={`flex-1 py-4 text-center font-label-sm text-label-sm ${
                  imageTab === "upload"
                    ? "border-b-2 border-primary font-semibold text-primary"
                    : "text-on-surface-variant hover:bg-surface-container"
                }`}
              >
                上传至服务器
              </button>
            </div>
            <div className="border-b border-outline-variant bg-surface-container px-4 py-2.5">
              {selected?.image_url?.trim() ? (
                <div className="flex flex-col gap-1">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">图片参考链接（image_url）</span>
                  <a
                    href={selected.image_url.trim()}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="break-all font-body-md text-body-md font-semibold text-primary underline decoration-2 underline-offset-2 hover:text-primary/80"
                  >
                    {selected.image_url.trim()}
                  </a>
                </div>
              ) : (
                <p className="font-label-sm text-label-sm text-on-surface-variant">
                  暂无网络图片链接。需由管理员通过「编辑元数据」填写 image_url。
                </p>
              )}
            </div>
            <div className="flex flex-1 flex-col gap-4 p-6">
              {imageTab === "upload" && (
                <div className="flex flex-col gap-3 rounded-sm border border-outline-variant bg-surface-container-high p-4">
                  <input
                    ref={uploadInputRef}
                    type="file"
                    multiple
                    accept="image/jpeg,image/jpg,image/png,image/webp,image/gif"
                    className="hidden"
                    title="上传图片文件，可多选"
                    onChange={(ev) => {
                      const fs = ev.target.files;
                      if (fs?.length && selected) void uploadPlantImages(selected, fs);
                    }}
                  />
                  <Button
                    type="primary"
                    loading={uploadingImage}
                    disabled={!selected}
                    onClick={() => uploadInputRef.current?.click()}
                  >
                    选择一张或多张图片上传到服务器
                  </Button>
                </div>
              )}
              <div className="relative mb-6 aspect-[3/4] w-full overflow-hidden rounded-sm border border-outline-variant bg-surface-container-high">
                {previewSrc ? (
                  <>
                    <img
                      key={previewSrc}
                      alt={selected ? pickSpeciesLabel(selected) : ""}
                      className="h-full w-full object-cover"
                      src={previewSrc}
                    />
                    {playablePreviewUrls.length > 1 && (
                      <>
                        <button
                          type="button"
                          aria-label="上一张"
                          onClick={galleryPrev}
                          className="absolute left-2 top-1/2 z-10 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-on-surface/75 text-white shadow-md backdrop-blur-sm transition-colors hover:bg-on-surface/90"
                        >
                          <span className="material-symbols-outlined text-[28px]">chevron_left</span>
                        </button>
                        <button
                          type="button"
                          aria-label="下一张"
                          onClick={galleryNext}
                          className="absolute right-2 top-1/2 z-10 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-on-surface/75 text-white shadow-md backdrop-blur-sm transition-colors hover:bg-on-surface/90"
                        >
                          <span className="material-symbols-outlined text-[28px]">chevron_right</span>
                        </button>
                        <div className="pointer-events-none absolute left-1/2 top-3 z-10 -translate-x-1/2 rounded-full bg-on-surface/80 px-3 py-1 font-label-sm text-label-sm text-white backdrop-blur-sm">
                          {galleryIdx + 1} / {playablePreviewUrls.length}
                        </div>
                      </>
                    )}
                  </>
                ) : (
                  <div className="flex h-full flex-col items-center justify-center gap-2 px-4 text-center font-label-sm text-on-surface-variant">
                    <span>
                      {hasUnplayablePaths
                        ? "当前库中记录的路径无法在浏览器直接使用（常为磁盘路径）。请切换到「上传至服务器」在本页上传以生成可用的 /api/media/… 路径。"
                        : "服务器上暂无该物种的图片。请切换到「上传至服务器」上传，或由管理员补齐数据。"}
                    </span>
                  </div>
                )}
                <div className="absolute bottom-4 left-4 rounded bg-on-surface/80 px-3 py-1 font-label-sm text-label-sm text-white backdrop-blur-sm">
                  {imageFilename}
                </div>
              </div>
              {selected && playableRawPaths.length > 0 && (
                <div className="rounded-sm border border-outline-variant bg-surface-container-high p-3">
                  <div className="mb-2 font-label-sm text-label-sm font-semibold text-on-surface">
                    本站图片（勾选后可批量下载为 JPG）
                  </div>
                  <div className="mb-2 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={selectAllDownloadPicks}
                      className="rounded border border-outline-variant px-2 py-1 font-label-sm text-label-sm text-on-surface-variant hover:bg-surface-container"
                    >
                      全选
                    </button>
                    <button
                      type="button"
                      onClick={clearDownloadPicks}
                      className="rounded border border-outline-variant px-2 py-1 font-label-sm text-label-sm text-on-surface-variant hover:bg-surface-container"
                    >
                      清空
                    </button>
                    <Button
                      type="primary"
                      size="small"
                      icon={<DownloadOutlined />}
                      loading={jpegDownloadMode === "batch"}
                      disabled={
                        jpegDownloadMode !== "idle" || downloadPick.size === 0
                      }
                      onClick={() => void downloadPickedImagesAsJpeg()}
                    >
                      下载所选（JPG）
                    </Button>
                    <span className="font-label-sm text-label-sm text-on-surface-variant self-center">
                      已选 {downloadPick.size} / {playableRawPaths.length}
                    </span>
                  </div>
                  <div className="max-h-44 overflow-y-auto">
                    <ul className="flex flex-col gap-2">
                      {playableRawPaths.map((raw, i) => {
                        const thumb = playablePreviewUrls[i];
                        return (
                          <li
                            key={`${raw}_${i}`}
                            className="flex items-center gap-3 rounded border border-transparent px-1 py-0.5 hover:border-outline-variant/60"
                          >
                            <Checkbox
                              checked={downloadPick.has(i)}
                              onChange={() => toggleDownloadPick(i)}
                              disabled={jpegDownloadMode !== "idle"}
                            />
                            <button
                              type="button"
                              className="h-11 w-11 shrink-0 overflow-hidden rounded border border-outline-variant bg-surface-container"
                              onClick={() => setGalleryIdx(i)}
                              aria-label={`预览第 ${i + 1} 张`}
                            >
                              {thumb ? (
                                <img alt="" src={thumb} className="h-full w-full object-cover" />
                              ) : null}
                            </button>
                            <span className="min-w-0 flex-1 break-all font-mono-data text-[11px] text-on-surface-variant">
                              {raw}
                            </span>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                </div>
              )}
              <div className="mt-auto flex flex-wrap gap-2">
                  {isAdmin && selected && (
                    <>
                      <button
                        type="button"
                        onClick={() => openEdit(selected)}
                        className="flex flex-1 items-center justify-center border border-primary py-2 font-label-sm text-label-sm text-primary transition-colors hover:bg-primary/5 rounded"
                      >
                        编辑元数据
                      </button>
                      <button
                        type="button"
                        onClick={() => remove(selected)}
                        className="rounded border border-error px-2 py-2 font-label-sm text-label-sm text-error transition-colors hover:bg-error-container/40"
                        aria-label="删除"
                      >
                        删除
                      </button>
                      <button
                        type="button"
                        className="material-symbols-outlined rounded border border-outline-variant p-2 text-on-surface-variant transition-colors hover:bg-surface-container"
                        aria-label="全屏查看"
                        onClick={() => previewSrc && window.open(previewSrc, "_blank", "noopener,noreferrer")}
                        disabled={!previewSrc}
                      >
                        fullscreen
                      </button>
                    </>
                  )}
                  {isAdmin && selected && getToken() && playableRawPaths[galleryIdx] && (
                    <Button
                      danger
                      loading={deletingImage}
                      disabled={deletingImage || !previewSrc}
                      onClick={() => confirmDeleteServerImage(playableRawPaths[galleryIdx])}
                      className="font-label-sm"
                    >
                      删除当前本站图
                    </Button>
                  )}
                  {selected && previewSrc && (
                    <button
                      type="button"
                      disabled={jpegDownloadMode !== "idle"}
                      onClick={() => void downloadCurrentPreviewJpeg()}
                      className="inline-flex items-center gap-1 rounded border border-outline-variant px-3 py-2 font-label-sm text-label-sm text-on-surface-variant transition-colors hover:bg-surface-container disabled:opacity-50"
                    >
                      <DownloadOutlined />
                      {jpegDownloadMode === "current" ? "处理中…" : "下载当前图（JPG）"}
                    </button>
                  )}
                </div>
              </div>
            </section>
          </div>
      </div>

      <Modal
        title={editing ? "编辑植物" : "新增植物"}
        open={editorOpen}
        onCancel={() => setEditorOpen(false)}
        onOk={save}
        width={720}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item name="vernacular_name" label="植物中文名">
            <Input />
          </Form.Item>
          <Form.Item name="scientific_name" label="拉丁名">
            <Input />
          </Form.Item>
          <Form.Item name="division" label="门">
            <Input />
          </Form.Item>
          <Form.Item name="subclass" label="亚纲">
            <Input />
          </Form.Item>
          <Form.Item name="taxonomic_order" label="目">
            <Input />
          </Form.Item>
          <Form.Item name="family" label="科">
            <Input />
          </Form.Item>
          <Form.Item name="genus" label="属">
            <Input />
          </Form.Item>
          <Form.Item name="morphology_text" label="一般形状">
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item name="medicinal_shape" label="药用形状">
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item name="distribution_china" label="国内分布">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="distribution_abroad" label="国外分布">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="habitat" label="生境">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="image_url" label="网络图片链接">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
