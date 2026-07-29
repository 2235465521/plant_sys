import {
  DeleteOutlined,
  DownOutlined,
  DownloadOutlined,
  EditOutlined,
  ExportOutlined,
  EyeOutlined,
  FileExcelOutlined,
  FileTextOutlined,
  TableOutlined,
  VideoCameraOutlined,
} from "@ant-design/icons";
import axios from "axios";
import { Button, Checkbox, Dropdown, Form, Input, Modal, Pagination, Switch, Table, Tooltip, Select, Tag, Spin, App as AntdApp } from "antd";
import type { MenuProps } from "antd";
import type { Key } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useOutletContext, useSearchParams, Link } from "react-router-dom";
import { api, Plant, getToken, serializeTaxonArrayParams, generatePlantVideo, GenerateVideoRes } from "../api";

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
  const { message } = AntdApp.useApp();
  const { taxonLevel } = useOutletContext<OutletCtx>();
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";
  const qMode = searchParams.get("q_mode") ?? "";
  const spStr = searchParams.toString();
  const harvestMonth = searchParams.get("harvest_month") ?? "";
  const foodTherapyMonth = searchParams.get("food_therapy_month") ?? "";
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
        qMode,
        harvestMonth,
        foodTherapyMonth,
        [...divisions].sort().join("\x01"),
        [...subclasses].sort().join("\x01"),
        [...torders].sort().join("\x01"),
        [...families].sort().join("\x01"),
        [...genera].sort().join("\x01"),
      ].join("\0"),
    [q, qMode, harvestMonth, foodTherapyMonth, divisions, subclasses, torders, families, genera],
  );

  const filterCrumbsWithLevel = useMemo(() => {
    const arr: { param: string; value: string }[] = [];
    divisions.forEach((v) => arr.push({ param: "division", value: v }));
    subclasses.forEach((v) => arr.push({ param: "subclass", value: v }));
    torders.forEach((v) => arr.push({ param: "torder", value: v }));
    families.forEach((v) => arr.push({ param: "family", value: v }));
    genera.forEach((v) => arr.push({ param: "genus", value: v }));
    return arr;
  }, [divisions, subclasses, torders, families, genera]);

  const filterCrumbs = useMemo(
    () => filterCrumbsWithLevel.map(c => c.value),
    [filterCrumbsWithLevel],
  );

  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<Plant[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(36);
  const [selected, setSelected] = useState<Plant | null>(null);
  const [detailTab, setDetailTab] = useState<"basic" | "morph" | "medicinal" | "harvest" | "food_therapy" | "habitat" | "medicinal_part">("basic");
  const [imageTab, setImageTab] = useState<"web" | "upload">("web");
  const [showTable, setShowTable] = useState(false);
  const [tableSelectedKeys, setTableSelectedKeys] = useState<Key[]>([]);
  const [previewModalVisible, setPreviewModalVisible] = useState(false);
  const [previewContent, setPreviewContent] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [cardMultiSelect, setCardMultiSelect] = useState(false);
  const lastCardClickIdx = useRef<number>(-1);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Plant | null>(null);
  const [form] = Form.useForm<any>();
  const [mediaVersion, setMediaVersion] = useState(0);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [deletingImage, setDeletingImage] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [galleryIdx, setGalleryIdx] = useState(0);
  const [downloadPick, setDownloadPick] = useState<Set<number>>(new Set());
  const [jpegDownloadMode, setJpegDownloadMode] = useState<"idle" | "current" | "batch">("idle");
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const tableExportSectionRef = useRef<HTMLElement>(null);

  const [videoLoading, setVideoLoading] = useState(false);
  const [videoModalOpen, setVideoModalOpen] = useState(false);
  const [videoResult, setVideoResult] = useState<GenerateVideoRes | null>(null);
  const [videoPlantName, setVideoPlantName] = useState<string>("");

  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [configPlant, setConfigPlant] = useState<Plant | null>(null);
  const [videoConfig, setVideoConfig] = useState<any>({
    transition_style: ["book_flip"],
    text_effect: "fade_in",
    sticker_effect: "none",
    voice_over: "none",
    bgm_type: "default"
  });

  const openVideoConfig = (plant: Plant) => {
    setConfigPlant(plant);
    setConfigModalOpen(true);
  };

  const handleGenerateVideo = async () => {
    if (!configPlant) return;
    const plant = configPlant;
    
    const name = pickSpeciesLabel(plant);
    setVideoPlantName(name);
    setVideoLoading(true);
    setVideoResult(null);

    try {
      const res = await generatePlantVideo(plant.id, videoConfig);
      setVideoResult(res);
      message.success(`「${name}」短视频生成成功！`);
    } catch (err: any) {
      console.error(err);
      message.error(err?.response?.data?.detail || "视频生成失败，请稍后重试");
    } finally {
      setVideoLoading(false);
    }
  };

  const handleDownloadVideo = async () => {
    if (!videoResult?.video_url) return;
    try {
      const response = await fetch(videoResult.video_url);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = videoResult.video_url.split('/').pop() || `video_${videoPlantName}.mp4`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      message.error("下载失败");
    }
  };

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

  async function selectPlant(p: Plant) {
    setSelected(p);
    try {
      const res = await api.get<Plant>(`/plants/${p.id}`);
      setSelected(res.data);
    } catch (e) {
      console.error(e);
    }
  }

  useEffect(() => {
    setPage(1);
  }, [filterKey]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    const url = qMode === "semantic" ? "/plants/semantic-search" : "/plants";
    api
      .get<ListRes>(url, {
        params: {
          page,
          page_size: pageSize,
          q: q || undefined,
          harvest_month: harvestMonth || undefined,
          food_therapy_month: foodTherapyMonth || undefined,
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
  }, [page, pageSize, q, qMode, harvestMonth, foodTherapyMonth, divisions, subclasses, torders, families, genera, reloadTick]);

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
    if (cardMultiSelect || showTable) {
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

  async function handlePreviewExportText() {
    let ids: number[];
    if (cardMultiSelect || showTable) {
      ids = tableSelectedKeys.map((k) => Number(k)).filter((n) => Number.isInteger(n) && n > 0);
      if (ids.length === 0) {
        message.warning("请先勾选要预览的标本");
        return;
      }
    } else {
      if (!selected) {
        message.warning("请先在物种列表中选一个标本");
        return;
      }
      ids = [selected.id];
    }

    setPreviewLoading(true);
    try {
      const res = await api.post(
        "/plants/export-batch",
        { ids, file_format: "txt" },
        { responseType: "blob" },
      );
      // Read Blob as text
      const text = await res.data.text();
      setPreviewContent(text);
      setPreviewModalVisible(true);
    } catch (e: unknown) {
      message.error("获取预览文本失败：" + String(e));
    } finally {
      setPreviewLoading(false);
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
    void selectPlant(p);
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

  async function openEdit(p: Plant) {
    setEditorOpen(true);
    setEditing(p);
    try {
      const res = await api.get<Plant>(`/plants/${p.id}`);
      const fullPlant = res.data;
      setEditing(fullPlant);
      const { image_server_paths: _omit, ...formValues } = fullPlant;
      form.setFieldsValue({
        ...formValues,
        aliases: formValues.aliases || undefined,
        habitats: fullPlant.habitats || [],
        rankings: fullPlant.rankings || [],
        regions: fullPlant.regions || [],
        harvest_months: formValues.harvest_months 
          ? formValues.harvest_months.split(",").map(m => m.trim()).filter(Boolean) 
          : [],
        food_therapy_months: formValues.food_therapy_months 
          ? formValues.food_therapy_months.split(",").map(m => m.trim()).filter(Boolean) 
          : [],
      });
    } catch (e) {
      const { image_server_paths: _omit, ...formValues } = p;
      form.setFieldsValue({
        ...formValues,
        aliases: formValues.aliases || undefined,
        habitats: p.habitats || [],
        rankings: p.rankings || [],
        regions: p.regions || [],
        harvest_months: formValues.harvest_months 
          ? formValues.harvest_months.split(",").map(m => m.trim()).filter(Boolean) 
          : [],
        food_therapy_months: formValues.food_therapy_months 
          ? formValues.food_therapy_months.split(",").map(m => m.trim()).filter(Boolean) 
          : [],
      });
    }
  }

  async function handleAiEnrich() {
    if (!editing) return;
    setAiLoading(true);
    try {
      const res = await api.post(`/plants/${editing.id}/ai-enrich`);
      const {
        harvest_months,
        harvest_months_desc,
        food_therapy_months,
        food_therapy_months_desc,
        medicinal_shape,
        habitats,
        rankings,
        regions,
        aliases,
        habitat,
        medicinal_part
      } = res.data;
      form.setFieldsValue({
        harvest_months: harvest_months 
          ? harvest_months.split(",").map((m: string) => m.trim()).filter(Boolean) 
          : [],
        harvest_months_desc: harvest_months_desc || "",
        food_therapy_months: food_therapy_months 
          ? food_therapy_months.split(",").map((m: string) => m.trim()).filter(Boolean) 
          : [],
        food_therapy_months_desc: food_therapy_months_desc || "",
        medicinal_shape: medicinal_shape || "",
        habitats: habitats || [],
        rankings: rankings || [],
        regions: regions || [],
        aliases: aliases || [],
        habitat: habitat || "",
        medicinal_part: medicinal_part || "",
      });
      message.success("AI 自动提取完成！已填入表单，请点击确定保存");
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || "AI 提取失败，请稍后重试");
    } finally {
      setAiLoading(false);
    }
  }

  async function save() {
    try {
      const v = await form.validateFields();
      const payload = {
        ...v,
        harvest_months: Array.isArray(v.harvest_months) ? v.harvest_months.join(",") : (v.harvest_months || null),
        food_therapy_months: Array.isArray(v.food_therapy_months) ? v.food_therapy_months.join(",") : (v.food_therapy_months || null),
      };
      if (editing) {
        await api.put(`/plants/${editing.id}`, payload);
        message.success("已保存");
      } else {
        await api.post("/plants", payload);
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
  const crumbsFromSelectedWithLevel = useMemo(() => {
    if (!selected) return [];
    const arr: { param: string; value: string }[] = [];
    if (selected.division) arr.push({ param: "division", value: selected.division });
    if (selected.subclass) arr.push({ param: "subclass", value: selected.subclass });
    if (selected.taxonomic_order) arr.push({ param: "torder", value: selected.taxonomic_order });
    if (selected.family) arr.push({ param: "family", value: selected.family });
    if (selected.genus) arr.push({ param: "genus", value: selected.genus });
    return arr;
  }, [selected]);

  const crumbsWithLevel = filterCrumbsWithLevel.length > 0 ? filterCrumbsWithLevel : crumbsFromSelectedWithLevel;
  const crumbs = crumbsWithLevel.map(c => c.value);

  function handleCrumbClick(index: number) {
    const next = new URLSearchParams(searchParams);
    const pathParams = ["division", "subclass", "torder", "family", "genus"];
    pathParams.forEach(p => next.delete(p));
    next.delete("level");
    
    for (let i = 0; i <= index; i++) {
      const c = crumbsWithLevel[i];
      next.append(c.param, c.value);
    }
    setSearchParams(next);
  }

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
        {crumbsWithLevel.length > 0 ? (
          crumbsWithLevel.map((c, i) => (
            <span key={`${c.value}-${i}`} className="flex items-center gap-2">
              {i > 0 && <BreadcrumbChevron />}
              <button
                type="button"
                onClick={() => handleCrumbClick(i)}
                className={i === crumbsWithLevel.length - 1 ? "font-semibold text-primary cursor-default" : "hover:text-primary hover:underline"}
              >
                {c.value}
              </button>
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
                  {q ? (qMode === "semantic" ? ` · AI 语义搜索「${q}」` : ` · 搜索「${q}」`) : ""}
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
                        : `预览已勾选的 ${tableSelectedKeys.length} 个标本的导出文本`
                      : selected
                        ? `预览当前标本「${pickSpeciesLabel(selected)}」的导出文本`
                        : "请先在物种列表中选一个标本"
                  }
                >
                  <Button
                    icon={<EyeOutlined />}
                    loading={previewLoading}
                    disabled={(cardMultiSelect ? tableSelectedKeys.length === 0 : !selected) || loading}
                    onClick={handlePreviewExportText}
                    className="font-label-sm"
                  >
                    预览
                  </Button>
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
                <Tooltip title={selected ? `为当前选中的标本「${pickSpeciesLabel(selected)}」自动生成20秒古风短视频` : "请先在列表中选择一个物种标本"}>
                  <Button
                    icon={<VideoCameraOutlined />}
                    disabled={!selected || loading}
                    onClick={() => selected && openVideoConfig(selected)}
                    className="font-label-sm bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-700 hover:to-amber-800 text-white border-none shadow-sm"
                  >
                    生成视频
                  </Button>
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

            {/* 功能一：时令药材筛选区 */}
            <div className="mb-4 flex flex-col gap-3 rounded bg-surface-container-low p-4 text-sm border border-outline-variant">
              <div className="flex items-center gap-3">
                <span className="font-semibold text-on-surface w-24 flex items-center gap-1"><span className="material-symbols-outlined text-[18px]">calendar_month</span>最佳采收月</span>
                <div className="flex flex-wrap gap-2">
                  {[...Array(12)].map((_, i) => {
                    const m = String(i + 1);
                    const active = harvestMonth === m;
                    return (
                      <button
                        key={`h-${m}`}
                        onClick={() => {
                          const u = new URLSearchParams(searchParams.toString());
                          if (active) u.delete("harvest_month");
                          else u.set("harvest_month", m);
                          setSearchParams(u);
                        }}
                        className={`px-3 py-1 rounded-full transition-all duration-200 border ${
                          active 
                            ? "bg-primary border-primary text-on-primary shadow-sm transform scale-105" 
                            : "bg-surface border-outline-variant hover:border-primary text-on-surface-variant hover:text-primary"
                        }`}
                      >
                        {m}月
                      </button>
                    );
                  })}
                  {harvestMonth && (
                    <button onClick={() => {
                      const u = new URLSearchParams(searchParams.toString());
                      u.delete("harvest_month");
                      setSearchParams(u);
                    }} className="px-2 text-xs text-outline hover:text-error transition-colors">清除</button>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-semibold text-on-surface w-24 flex items-center gap-1"><span className="material-symbols-outlined text-[18px]">restaurant_menu</span>食疗入药月</span>
                <div className="flex flex-wrap gap-2">
                  {[...Array(12)].map((_, i) => {
                    const m = String(i + 1);
                    const active = foodTherapyMonth === m;
                    return (
                      <button
                        key={`f-${m}`}
                        onClick={() => {
                          const u = new URLSearchParams(searchParams.toString());
                          if (active) u.delete("food_therapy_month");
                          else u.set("food_therapy_month", m);
                          setSearchParams(u);
                        }}
                        className={`px-3 py-1 rounded-full transition-all duration-200 border ${
                          active 
                            ? "bg-tertiary border-tertiary text-on-tertiary shadow-sm transform scale-105" 
                            : "bg-surface border-outline-variant hover:border-tertiary text-on-surface-variant hover:text-tertiary"
                        }`}
                      >
                        {m}月
                      </button>
                    );
                  })}
                  {foodTherapyMonth && (
                    <button onClick={() => {
                      const u = new URLSearchParams(searchParams.toString());
                      u.delete("food_therapy_month");
                      setSearchParams(u);
                    }} className="px-2 text-xs text-outline hover:text-error transition-colors">清除</button>
                  )}
                </div>
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
                  <div className="flex items-center gap-2">
                    <Dropdown menu={batchExportMenuProps} disabled={tableSelectedKeys.length === 0 || loading}>
                      <Button type="primary" icon={<ExportOutlined />} disabled={tableSelectedKeys.length === 0 || loading}>
                        导出 <DownOutlined />
                      </Button>
                    </Dropdown>
                    <Button
                      icon={<EyeOutlined />}
                      loading={previewLoading}
                      disabled={tableSelectedKeys.length === 0 || loading}
                      onClick={handlePreviewExportText}
                    >
                      预览
                    </Button>
                  </div>
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
                    void selectPlant(p);
                    setTableSelectedKeys((prev) => {
                      const key = p.id as Key;
                      return prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key];
                    });
                  },
                })}
                rowSelection={{
                  selectedRowKeys: tableSelectedKeys,
                  onChange: setTableSelectedKeys,
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
                  {
                    title: "短视频",
                    key: "video_action",
                    width: 100,
                    render: (_: unknown, p: Plant) => (
                      <Button
                        type="link"
                        size="small"
                        icon={<VideoCameraOutlined />}
                        onClick={(e) => {
                          e.stopPropagation();
                          openVideoConfig(p);
                        }}
                        className="text-amber-600 hover:text-amber-700 font-medium"
                      >
                        生成
                      </Button>
                    ),
                  },
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
                onClick={() => setDetailTab("basic")}
                className={`mr-8 py-4 font-label-sm text-label-sm ${
                  detailTab === "basic"
                    ? "border-b-2 border-primary font-semibold text-primary"
                    : "text-on-surface-variant hover:text-primary"
                }`}
              >
                基础信息
              </button>
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
                className={`mr-8 py-4 font-label-sm text-label-sm ${
                  detailTab === "medicinal"
                    ? "border-b-2 border-primary font-semibold text-primary"
                    : "text-on-surface-variant hover:text-primary"
                }`}
              >
                药用价值
              </button>
              <button
                type="button"
                onClick={() => setDetailTab("harvest")}
                className={`mr-8 py-4 font-label-sm text-label-sm ${
                  detailTab === "harvest"
                    ? "border-b-2 border-primary font-semibold text-primary"
                    : "text-on-surface-variant hover:text-primary"
                }`}
              >
                最佳采收
              </button>
              <button
                type="button"
                onClick={() => setDetailTab("food_therapy")}
                className={`mr-8 py-4 font-label-sm text-label-sm ${
                  detailTab === "food_therapy"
                    ? "border-b-2 border-primary font-semibold text-primary"
                    : "text-on-surface-variant hover:text-primary"
                }`}
              >
                食疗入药
              </button>
              <button
                type="button"
                onClick={() => setDetailTab("habitat")}
                className={`mr-8 py-4 font-label-sm text-label-sm ${
                  detailTab === "habitat"
                    ? "border-b-2 border-primary font-semibold text-primary"
                    : "text-on-surface-variant hover:text-primary"
                }`}
              >
                生长环境
              </button>
              <button
                type="button"
                onClick={() => setDetailTab("medicinal_part")}
                className={`py-4 font-label-sm text-label-sm ${
                  detailTab === "medicinal_part"
                    ? "border-b-2 border-primary font-semibold text-primary"
                    : "text-on-surface-variant hover:text-primary"
                }`}
              >
                入药部位
              </button>
            </div>
            <div className="p-6">
              {selected ? (
                <div className="max-w-none font-body-md leading-relaxed text-on-surface-variant">
                  {detailTab === "basic" ? (
                    <div className="flex flex-col gap-3 text-on-surface">
                      <p>
                        <span className="font-semibold text-on-surface-variant">拉丁学名：</span>
                        <span className="font-serif italic text-on-surface">{selected.scientific_name?.trim() || "无"}</span>
                      </p>
                      <p>
                        <span className="font-semibold text-on-surface-variant">学名异名：</span>
                        <span className="text-on-surface">{selected.synonyms?.trim() || "无"}</span>
                      </p>
                      <p>
                        <span className="font-semibold text-on-surface-variant">中文别名：</span>
                        <span className="text-on-surface">{selected.alternative_names_zh?.trim() || "无"}</span>
                      </p>
                      <div>
                        <span className="font-semibold text-on-surface-variant">分类别名系统：</span>
                        {selected.aliases && selected.aliases.length > 0 ? (
                          <div className="mt-2 flex flex-col gap-2">
                            {selected.aliases.map((a, i) => (
                              <div key={i} className="flex flex-col rounded bg-surface-container-high p-3 text-sm border border-outline-variant">
                                <div className="flex items-center gap-2">
                                  <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary border border-primary/20">{a.alias_type}</span>
                                  <span className="font-bold text-on-surface">{a.alias_name}</span>
                                </div>
                                {a.origin_desc && <span className="text-on-surface-variant mt-1.5 text-xs leading-relaxed">{a.origin_desc}</span>}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <span className="text-on-surface ml-2">无</span>
                        )}
                      </div>
                      <p>
                        <span className="font-semibold text-on-surface-variant">国内分布：</span>
                        <span className="text-on-surface">{selected.distribution_china?.trim() || "无"}</span>
                      </p>
                      <p>
                        <span className="font-semibold text-on-surface-variant">国外分布：</span>
                        <span className="text-on-surface">{selected.distribution_abroad?.trim() || "无"}</span>
                      </p>
                      {selected.regions && selected.regions.length > 0 && (
                        <div className="mt-1 flex flex-col gap-1.5">
                          <span className="font-semibold text-on-surface-variant">道地分布属性：</span>
                          <div className="flex flex-wrap gap-1.5">
                            {selected.regions.map((reg, i) => (
                              <Tag color="success" key={i} className="rounded-md font-medium m-0">
                                {reg.region_name}{reg.combo_name ? `（${reg.combo_name}）` : ""}
                              </Tag>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : detailTab === "morph" ? (
                    <div className="text-on-surface space-y-4">
                      <div className="whitespace-pre-wrap leading-relaxed">
                        {selected.morphology_text?.trim() || "暂无描述"}
                      </div>
                      {selected.habitats && selected.habitats.length > 0 && (
                        <div className="border-t border-outline-variant/30 pt-3">
                          <div className="text-xs font-semibold text-primary mb-1.5 flex items-center gap-1">
                            <span className="material-symbols-outlined text-[15px]">nature_people</span>
                            生境场景分类
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {selected.habitats.map((h, i) => (
                              <Tag color="cyan" key={i} className="rounded-md font-medium m-0">{h}</Tag>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : detailTab === "harvest" ? (
                    <div className="whitespace-pre-wrap text-on-surface leading-relaxed">
                      {selected.harvest_months_desc?.trim() || "暂无描述"}
                    </div>
                  ) : detailTab === "food_therapy" ? (
                    <div className="whitespace-pre-wrap text-on-surface leading-relaxed">
                      {selected.food_therapy_months_desc?.trim() || "暂无描述"}
                    </div>
                  ) : detailTab === "habitat" ? (
                    <div className="whitespace-pre-wrap text-on-surface leading-relaxed">
                      {selected.habitat?.trim() || "暂无生长环境描述"}
                    </div>
                  ) : detailTab === "medicinal_part" ? (
                    <div className="whitespace-pre-wrap text-on-surface leading-relaxed">
                      {selected.medicinal_part?.trim() || "暂无入药部位记载"}
                    </div>
                  ) : (
                    <div className="flex flex-col gap-4 text-on-surface">
                      <div>
                        <span className="font-semibold text-on-surface-variant block mb-1">药用形状与价值：</span>
                        <p className="text-on-surface whitespace-pre-wrap leading-relaxed m-0">
                          {selected.medicinal_shape?.trim() || "暂无记载"}
                        </p>
                      </div>
                      {selected.rankings && selected.rankings.length > 0 && (
                        <div className="border-t border-outline-variant/30 pt-3">
                          <div className="text-xs font-semibold text-primary mb-2 flex items-center gap-1">
                            <span className="material-symbols-outlined text-[16px]">emoji_events</span>
                            特色榜单荣誉
                          </div>
                          <div className="flex flex-col gap-2">
                            {selected.rankings.map((r, i) => {
                              const rankLabel = r.ranking_type === "sweetest" ? "最甜植物" :
                                                r.ranking_type === "bitterest" ? "最苦植物" :
                                                r.ranking_type === "rarity" ? "珍稀物种" : "特殊生长周期";
                              return (
                                <div key={i} className="rounded bg-amber-50/40 p-2.5 text-xs border border-amber-200/40 flex flex-col gap-1">
                                  <div className="flex items-center gap-1.5">
                                    <span className="rounded bg-amber-500/10 px-1.5 py-0.5 font-bold text-amber-700 border border-amber-500/20">{rankLabel}</span>
                                    {r.ranking_value && <span className="font-bold text-on-surface">值: {r.ranking_value}</span>}
                                  </div>
                                  {r.description && <span className="text-on-surface-variant leading-relaxed mt-0.5">{r.description}</span>}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
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
                              图片 {i + 1}
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
                      <button
                        type="button"
                        className="flex items-center justify-center border border-amber-600 bg-amber-50 px-3 py-2 font-label-sm text-label-sm text-amber-700 transition-colors hover:bg-amber-100 rounded"
                        onClick={() => openVideoConfig(selected)}
                      >
                        <VideoCameraOutlined className="mr-1" />
                        生成视频
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
          {editing && (
            <div className="mb-4 flex justify-end">
              <Button 
                type="primary" 
                onClick={handleAiEnrich} 
                loading={aiLoading} 
                className="bg-primary hover:bg-primary-container"
                icon={<span className="material-symbols-outlined text-[16px] align-middle">bolt</span>}
              >
                AI 一键智能填充（提取时令与描述）
              </Button>
            </div>
          )}
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
          <Form.Item name="habitat" label="生长环境">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="medicinal_part" label="入药部位">
            <Input placeholder="如：全草、根、叶、果实" />
          </Form.Item>
          <Form.Item name="image_url" label="网络图片链接">
            <Input />
          </Form.Item>
          <Form.Item name="harvest_months" label="最佳采收月（多选）">
            <Select
              mode="multiple"
              placeholder="选择最佳采收月份"
              allowClear
              options={[...Array(12)].map((_, i) => ({ label: `${i + 1}月`, value: String(i + 1) }))}
            />
          </Form.Item>
          <Form.Item name="food_therapy_months" label="适合食疗入药月（多选）">
            <Select
              mode="multiple"
              placeholder="选择适合食疗入药月份"
              allowClear
              options={[...Array(12)].map((_, i) => ({ label: `${i + 1}月`, value: String(i + 1) }))}
            />
          </Form.Item>
          <Form.Item name="harvest_months_desc" label="最佳采收详细说明">
            <Input.TextArea rows={3} placeholder="AI 提取或手动输入最佳采收依据和建议" />
          </Form.Item>
          <Form.Item name="food_therapy_months_desc" label="食疗入药详细说明">
            <Input.TextArea rows={3} placeholder="AI 提取或手动输入食疗安全与入药依据建议" />
          </Form.Item>

          {/* Feature 3: Habitats */}
          <Form.Item name="habitats" label="生境分类（多选）">
            <Select
              mode="multiple"
              placeholder="请选择适用的生境场景分类"
              allowClear
              options={[
                { label: "森林", value: "森林" },
                { label: "草原", value: "草原" },
                { label: "湿地", value: "湿地" },
                { label: "荒漠", value: "荒漠" },
                { label: "海洋", value: "海洋" }
              ]}
            />
          </Form.Item>

          {/* Feature 4: Rankings */}
          <div className="mb-2 mt-4 font-semibold text-on-surface">特色榜单配置</div>
          <Form.List name="rankings">
            {(fields, { add, remove }) => (
              <div className="flex flex-col gap-3">
                {fields.map(({ key, name, ...restField }) => (
                  <div key={key} className="flex gap-2 items-start bg-surface-container-low p-3 rounded border border-outline-variant relative group transition-colors hover:border-primary/50">
                    <div className="flex-1 flex flex-col gap-2">
                      <div className="flex gap-2">
                        <Form.Item
                          {...restField}
                          name={[name, 'ranking_type']}
                          className="mb-0 w-44"
                          rules={[{ required: true, message: '请选择排行榜类型' }]}
                        >
                          <Select placeholder="榜单类型" options={[
                            { label: "最甜植物 (sweetest)", value: "sweetest" },
                            { label: "最苦植物 (bitterest)", value: "bitterest" },
                            { label: "珍稀濒危物种 (rarity)", value: "rarity" },
                            { label: "特殊生长周期 (growth_cycle)", value: "growth_cycle" }
                          ]} />
                        </Form.Item>
                        <Form.Item
                          {...restField}
                          name={[name, 'ranking_value']}
                          className="mb-0 flex-1"
                        >
                          <Input placeholder="排行数值/指标 (选填，如：1st, 9.8)" />
                        </Form.Item>
                      </div>
                      <Form.Item
                        {...restField}
                        name={[name, 'description']}
                        className="mb-0"
                      >
                        <Input placeholder="上榜理由与描述说明" />
                      </Form.Item>
                    </div>
                    <Button 
                      type="text" 
                      danger 
                      className="opacity-0 group-hover:opacity-100 transition-opacity absolute right-1 top-1"
                      icon={<span className="material-symbols-outlined text-[18px]">close</span>} 
                      onClick={() => remove(name)} 
                    />
                  </div>
                ))}
                <Form.Item className="mb-0">
                  <Button type="dashed" onClick={() => add()} block icon={<span className="material-symbols-outlined text-[18px] align-middle">add</span>}>
                    添加特色上榜
                  </Button>
                </Form.Item>
              </div>
            )}
          </Form.List>

          {/* Feature 5: Regional Daodi */}
          <div className="mb-2 mt-4 font-semibold text-on-surface">道地药材地配置</div>
          <Form.List name="regions">
            {(fields, { add, remove }) => (
              <div className="flex flex-col gap-3">
                {fields.map(({ key, name, ...restField }) => (
                  <div key={key} className="flex gap-2 items-start bg-surface-container-low p-3 rounded border border-outline-variant relative group transition-colors hover:border-primary/50">
                    <div className="flex-1 flex gap-2">
                      <Form.Item
                        {...restField}
                        name={[name, 'region_name']}
                        className="mb-0 flex-1"
                        rules={[{ required: true, message: '请输入省份名称' }]}
                      >
                        <Input placeholder="省份名称，如：浙江, 河南, 四川" />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'combo_name']}
                        className="mb-0 flex-1"
                      >
                        <Input placeholder="经典道地药名组合 (选填，如：浙八味, 四大怀药)" />
                      </Form.Item>
                    </div>
                    <Button 
                      type="text" 
                      danger 
                      className="opacity-0 group-hover:opacity-100 transition-opacity absolute right-1 top-1"
                      icon={<span className="material-symbols-outlined text-[18px]">close</span>} 
                      onClick={() => remove(name)} 
                    />
                  </div>
                ))}
                <Form.Item className="mb-0">
                  <Button type="dashed" onClick={() => add()} block icon={<span className="material-symbols-outlined text-[18px] align-middle">add</span>}>
                    添加道地属性
                  </Button>
                </Form.Item>
              </div>
            )}
          </Form.List>

          <div className="mb-2 mt-4 font-semibold text-on-surface">分类别名配置</div>
          <Form.List name="aliases">
            {(fields, { add, remove }) => (
              <div className="flex flex-col gap-3">
                {fields.map(({ key, name, ...restField }) => (
                  <div key={key} className="flex gap-2 items-start bg-surface-container-low p-3 rounded border border-outline-variant relative group transition-colors hover:border-primary/50">
                    <div className="flex-1 flex flex-col gap-2">
                      <div className="flex gap-2">
                        <Form.Item
                          {...restField}
                          name={[name, 'alias_type']}
                          className="mb-0 w-40"
                          rules={[{ required: true, message: '请选择类型' }]}
                        >
                          <Select placeholder="选择类型" options={[
                            {label:'药典标准名', value:'药典标准名'},
                            {label:'古书古名', value:'古书古名'},
                            {label:'民间通用俗称', value:'民间通用俗称'},
                            {label:'各地方言名', value:'各地方言名'},
                            {label:'药房处方名', value:'药房处方名'},
                            {label:'市场商品名', value:'市场商品名'},
                            {label:'易混淆错用名', value:'易混淆错用名'},
                          ]} />
                        </Form.Item>
                        <Form.Item
                          {...restField}
                          name={[name, 'alias_name']}
                          className="mb-0 flex-1"
                          rules={[{ required: true, message: '请填写别名' }]}
                        >
                          <Input placeholder="输入别名内容" />
                        </Form.Item>
                      </div>
                      <Form.Item
                        {...restField}
                        name={[name, 'origin_desc']}
                        className="mb-0"
                      >
                        <Input placeholder="简单由来说明（选填）" />
                      </Form.Item>
                    </div>
                    <Button 
                      type="text" 
                      danger 
                      className="opacity-0 group-hover:opacity-100 transition-opacity absolute right-1 top-1"
                      icon={<span className="material-symbols-outlined text-[18px]">close</span>} 
                      onClick={() => remove(name)} 
                    />
                  </div>
                ))}
                <Form.Item className="mb-0">
                  <Button type="dashed" onClick={() => add()} block icon={<span className="material-symbols-outlined text-[18px] align-middle">add</span>}>
                    添加分类别名
                  </Button>
                </Form.Item>
              </div>
            )}
          </Form.List>
        </Form>
      </Modal>

      <Modal
        title="导出文本预览"
        open={previewModalVisible}
        onCancel={() => setPreviewModalVisible(false)}
        width={720}
        footer={[
          <Button key="close" type="primary" onClick={() => setPreviewModalVisible(false)}>
            关闭
          </Button>
        ]}
      >
        <div className="max-h-[60vh] overflow-y-auto rounded bg-surface-container p-4 font-mono text-[13px] leading-relaxed whitespace-pre-wrap text-on-surface">
          {previewContent}
        </div>
      </Modal>

      <Modal
        title={
          <div className="flex items-center gap-2 text-lg font-bold text-gray-100">
            <VideoCameraOutlined className="text-[#e2b062] text-xl" />
            <span>影视创作台：{configPlant ? pickSpeciesLabel(configPlant) : ""}</span>
          </div>
        }
        open={configModalOpen}
        onCancel={() => {
          setConfigModalOpen(false);
          if (!videoLoading) setVideoResult(null);
        }}
        footer={null}
        width={960}
        centered
        destroyOnHidden
        rootClassName="ios-glass-modal"
        styles={{
          body: { color: "#fff" }
        }}
      >
        <style>{`
          .dark-studio-form .ant-select { width: 100% !important; }
          .dark-studio-form .ant-form-item-label > label { color: #f3f4f6 !important; font-weight: 500; text-shadow: 0 1px 2px rgba(0,0,0,0.5); }
          .dark-studio-form .ant-select-selector { background-color: rgba(255, 255, 255, 0.08) !important; border: 1px solid rgba(255, 255, 255, 0.15) !important; backdrop-filter: blur(16px) !important; -webkit-backdrop-filter: blur(16px) !important; color: #f3f4f6 !important; border-radius: 12px !important; box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.1) !important; }
          .dark-studio-form .ant-select-selection-item { color: #fff !important; }
          .dark-studio-form .ant-select-multiple .ant-select-selection-item { background: rgba(255, 255, 255, 0.15) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; border-radius: 8px !important; margin-top: 2px !important; margin-bottom: 2px !important; padding: 0 8px !important; }
          .dark-studio-form .ant-select-selection-item-remove { color: rgba(255,255,255,0.7) !important; }
          .dark-studio-form .ant-select-selection-item-remove:hover { color: #fff !important; }
          .dark-studio-form .ant-select-arrow { color: rgba(255,255,255,0.6) !important; }
          .dark-studio-form .ant-select-focused .ant-select-selector { border-color: #e2b062 !important; box-shadow: 0 0 0 2px rgba(226, 176, 98, 0.2), inset 0 1px 2px rgba(255, 255, 255, 0.1) !important; }
          
          .ios-glass-modal .ant-modal-content {
            background-color: rgba(30, 30, 32, 0.6) !important;
            backdrop-filter: blur(40px) saturate(180%) !important;
            -webkit-backdrop-filter: blur(40px) saturate(180%) !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 28px !important;
            box-shadow: 0 32px 64px rgba(0, 0, 0, 0.5), inset 0 1px 1px rgba(255, 255, 255, 0.15) !important;
          }
          .ios-glass-modal .ant-modal-header {
            background: transparent !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
            padding-bottom: 16px;
            margin-bottom: 24px;
          }
          
          .ant-select-dropdown.ios-glass-dropdown {
            background-color: rgba(40, 40, 44, 0.65) !important;
            backdrop-filter: blur(40px) saturate(180%) !important;
            -webkit-backdrop-filter: blur(40px) saturate(180%) !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 16px !important;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.4), inset 0 1px 1px rgba(255, 255, 255, 0.1) !important;
            padding: 8px !important;
          }
          .ios-glass-dropdown .ant-select-item {
            color: rgba(255, 255, 255, 0.85) !important;
            border-radius: 10px !important;
            margin: 2px 0 !important;
            transition: all 0.2s ease !important;
          }
          .ios-glass-dropdown .ant-select-item-option-active,
          .ios-glass-dropdown .ant-select-item-option-selected {
            background-color: rgba(255, 255, 255, 0.2) !important;
            color: #fff !important;
          }
          @keyframes pageFlip { 
            0% { transform: perspective(800px) rotateY(-90deg); opacity: 0; } 
            100% { transform: perspective(800px) rotateY(0deg); opacity: 1; } 
          }
          @keyframes bookFlip { 
            0% { transform: perspective(800px) rotate3d(-1, 1, 0, 0deg); transform-origin: bottom right; opacity: 1; } 
            50% { opacity: 1; }
            100% { transform: perspective(800px) rotate3d(-1, 1, 0, -180deg); transform-origin: bottom right; opacity: 0; } 
          }
          @keyframes verticalFlip { 
            0% { transform: perspective(800px) rotateX(-90deg); opacity: 0; } 
            100% { transform: perspective(800px) rotateX(0deg); opacity: 1; } 
          }
          @keyframes flyInRight { 
            0% { transform: translateX(100%); opacity: 0; } 
            100% { transform: translateX(0); opacity: 1; } 
          }
          @keyframes flyUpImg { 
            0% { transform: translateY(100%); opacity: 0; } 
            100% { transform: translateY(0); opacity: 1; } 
          }
          @keyframes continuousZoom { 
            0% { transform: scale(1); } 
            100% { transform: scale(1.15); } 
          }
          @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
          
          /* text anims */
          @keyframes slideUp { from { opacity: 0; transform: translateY(40px); } to { opacity: 1; transform: translateY(0); } }
          @keyframes slideDown { from { opacity: 0; transform: translateY(-40px); } to { opacity: 1; transform: translateY(0); } }
          @keyframes slideLeft { from { opacity: 0; transform: translateX(60px); } to { opacity: 1; transform: translateX(0); } }
          @keyframes zoomIn { from { opacity: 0; transform: scale(0.8); } to { opacity: 1; transform: scale(1); } }
          @keyframes popIn { 0% { opacity: 0; transform: scale(0.5); } 70% { opacity: 1; transform: scale(1.1); } 100% { transform: scale(1); } }
        `}</style>
        
        <div className="grid grid-cols-12 gap-8 h-[460px]">
          {/* 左侧配置区 */}
          <div className="col-span-5 flex flex-col border-r border-[#333] pr-6">
            <Form layout="vertical" className="flex-1 overflow-y-auto pr-2 dark-studio-form">
              <Form.Item label="转场风格 (Transition Style)">
                <Select 
                  popupClassName="ios-glass-dropdown"
                  mode="multiple"
                  value={videoConfig.transition_style} 
                  onChange={v => setVideoConfig({...videoConfig, transition_style: v})}
                  options={[
                    {label: "随机混合 (Random)", value: "random"},
                    {label: "3D横向翻页 (Page Flip)", value: "page_flip"},
                    {label: "卷页效果 (Page Curl)", value: "book_flip"},
                    {label: "右侧飞入 (Fly In Right)", value: "fly_in_right"},
                    {label: "缩放融入 (Zoom)", value: "zoom"},
                    {label: "下方弹跳 (Fly Up)", value: "fly_up"},
                    {label: "3D纵向翻折 (Vertical Flip)", value: "vertical_flip"},
                    {label: "平滑淡入 (Crossfade)", value: "crossfade"}
                  ]}
                />
              </Form.Item>
              <Form.Item label="文字效果 (Text Effect)">
                <Select 
                  popupClassName="ios-glass-dropdown"
                  value={videoConfig.text_effect} 
                  onChange={v => setVideoConfig({...videoConfig, text_effect: v})}
                  options={[
                    {label: "经典淡入 (Fade In)", value: "fade_in"},
                    {label: "向上浮现 (Slide Up)", value: "slide_up"},
                    {label: "向下掉落 (Slide Down)", value: "slide_down"},
                    {label: "右侧滑入 (Slide Left)", value: "slide_left"},
                    {label: "缩放放大 (Zoom In)", value: "zoom_in"},
                    {label: "放大弹入 (Pop In)", value: "pop_in"}
                  ]}
                />
              </Form.Item>
              <Form.Item label="贴纸装饰 (Sticker Effect)">
                <Select 
                  popupClassName="ios-glass-dropdown"
                  value={videoConfig.sticker_effect} 
                  onChange={v => setVideoConfig({...videoConfig, sticker_effect: v})}
                  options={[
                    {label: "无装饰 (None)", value: "none"},
                    {label: "飘落花瓣 (Petals)", value: "petals"},
                    {label: "古风边框 (Vintage Border)", value: "vintage_border"},
                    {label: "暖阳漏光 (Light Leaks)", value: "light_leaks"},
                    {label: "秋日落叶 (Falling Leaves)", value: "falling_leaves"},
                    {label: "水墨点缀 (Ink Splatter)", value: "ink_splatter"}
                  ]}
                />
              </Form.Item>
              <Form.Item label="AI语音解说 (Voice Over)">
                <Select 
                  popupClassName="ios-glass-dropdown"
                  value={videoConfig.voice_over} 
                  onChange={v => setVideoConfig({...videoConfig, voice_over: v})}
                  options={[
                    {label: "无语音 (None)", value: "none"},
                    {label: "女声朗读 (Female)", value: "female"},
                    {label: "男声朗读 (Male)", value: "male"}
                  ]}
                />
              </Form.Item>
              <Form.Item label="背景音乐 (Background Music)" className="mb-0">
                <Select 
                  popupClassName="ios-glass-dropdown"
                  value={videoConfig.bgm_type} 
                  onChange={v => setVideoConfig({...videoConfig, bgm_type: v})}
                  options={[
                    {label: "默认古风 (Default)", value: "default"},
                    {label: "无音乐 (None)", value: "none"}
                  ]}
                />
              </Form.Item>
            </Form>
          </div>

          {/* 右侧播放区 */}
          <div className="col-span-7 flex flex-col items-center justify-center relative">
            <div className="w-[258px] aspect-[9/16] bg-black rounded-xl overflow-hidden shadow-[0_0_20px_rgba(0,0,0,0.5)] relative border-2 border-[#333] flex items-center justify-center">
              {videoLoading ? (
                 <div className="flex flex-col items-center gap-4 text-center p-4">
                   <Spin size="large" />
                   <p className="text-[#e2b062] font-semibold tracking-wide text-sm">正在合成高质量视频...</p>
                   <p className="text-[#888] text-xs">调用引擎渲染 · 压制MP4</p>
                 </div>
              ) : videoResult?.success ? (
                 <video 
                   src={videoResult.video_url} 
                   controls 
                   autoPlay 
                   className="w-full h-full object-contain bg-black" 
                 />
              ) : (
                 <div className="w-full h-full relative overflow-hidden bg-[#242426]">
                   {/* CSS Simulation Placeholder */}
                   <div className="absolute inset-0 opacity-40 bg-[url('https://www.transparenttextures.com/patterns/rice-paper-2.png')]"></div>
                   
                   {configPlant && (Boolean(configPlant.image_server_paths?.length) || Boolean(configPlant.image_url)) && (
                     <div className="absolute inset-0 flex items-center justify-center">
                       <div 
                         key={Array.isArray(videoConfig.transition_style) ? videoConfig.transition_style.join(',') : videoConfig.transition_style} 
                         className="relative w-[85%] aspect-[3/4] rounded-md shadow-xl bg-white p-2"
                         style={{ 
                           animation: (() => {
                             const st = Array.isArray(videoConfig.transition_style) 
                               ? (videoConfig.transition_style.length > 0 ? videoConfig.transition_style[0] : 'random')
                               : videoConfig.transition_style;
                             return st === 'page_flip' ? 'pageFlip 1.2s ease-out both' :
                               st === 'book_flip' ? 'bookFlip 1.2s ease-out both' :
                               st === 'vertical_flip' ? 'verticalFlip 1.2s ease-out both' :
                               st === 'fly_in_right' ? 'flyInRight 1.2s ease-out both' :
                               st === 'fly_up' ? 'flyUpImg 1.2s ease-out both' :
                               st === 'zoom' ? 'continuousZoom 4s linear both' :
                               st === 'crossfade' ? 'fadeIn 1.5s ease-out both' : 'none';
                           })()
                         }}
                       >
                         <div 
                           className="w-full h-full bg-cover bg-center rounded-sm"
                           style={{ backgroundImage: `url(${configPlant.image_server_paths?.[0] || configPlant.image_url || ""})` }}
                         ></div>
                       </div>
                     </div>
                   )}
                   
                   <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent pointer-events-none"></div>
                   
                   {videoConfig.sticker_effect === 'petals' && (
                     <div 
                       className="absolute inset-0 pointer-events-none opacity-60 mix-blend-screen" 
                       style={{ 
                         backgroundImage: 'radial-gradient(circle, rgba(255,180,200,0.8) 2px, transparent 4px)', 
                         backgroundSize: '40px 40px',
                         backgroundPosition: '0 0, 20px 20px'
                       }}
                     ></div>
                   )}
                   {videoConfig.sticker_effect === 'vintage_border' && (
                     <div className="absolute inset-0 border-[10px] border-[#e2b062]/20 pointer-events-none mix-blend-screen"></div>
                   )}

                   {configPlant && (
                     <div className="absolute bottom-6 left-5 right-5 text-white z-10">
                       <div 
                         key={videoConfig.text_effect + (Array.isArray(videoConfig.transition_style) ? videoConfig.transition_style.join(',') : videoConfig.transition_style)}
                         style={{
                           animation: 
                             videoConfig.text_effect === 'fade_in' ? 'fadeIn 1.2s ease-out both' :
                             videoConfig.text_effect === 'slide_up' ? 'slideUp 1.2s ease-out both' :
                             videoConfig.text_effect === 'slide_down' ? 'slideDown 1.2s ease-out both' :
                             videoConfig.text_effect === 'slide_left' ? 'slideLeft 1.2s ease-out both' :
                             videoConfig.text_effect === 'zoom_in' ? 'zoomIn 1.2s ease-out both' :
                             videoConfig.text_effect === 'pop_in' ? 'popIn 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275) both' : 'none',
                         }}
                       >
                         <h3 className="text-xl font-bold tracking-widest mb-1 drop-shadow-md">{pickSpeciesLabel(configPlant)}</h3>
                         <p className="text-[11px] opacity-80 drop-shadow-md line-clamp-3 leading-relaxed">
                           {configPlant.morphology_text || "一味珍贵的自然馈赠..."}
                         </p>
                       </div>
                     </div>
                   )}
                 </div>
              )}
            </div>
            
            {!videoResult && !videoLoading && (
               <div className="mt-4 px-4 py-2 bg-[#2a2a2c] rounded-md border border-[#444] text-[#aaa] text-xs shadow-md">
                 <span className="material-symbols-outlined text-[14px] align-middle mr-1 text-[#e2b062]">info</span>
                 左侧调整参数，上方为实时预览，点击右下方生成最终成片。
               </div>
            )}
          </div>
        </div>

        {/* 底部操作区 */}
        <div className="flex justify-end gap-3 mt-8 pt-4 border-t border-[#333]">
          <Button 
            onClick={() => {
              setConfigModalOpen(false);
              if (!videoLoading) setVideoResult(null);
            }} 
            style={{ color: '#aaa', borderColor: '#444', backgroundColor: 'transparent' }} 
            className="hover:!text-white hover:!border-gray-400 font-medium"
          >
            取消
          </Button>
          <Button 
            type="primary" 
            onClick={handleGenerateVideo} 
            loading={videoLoading}
            className="bg-[#e2b062] hover:!bg-[#c89849] border-none text-black font-bold px-6"
          >
            {videoResult ? "重新生成视频" : "生成预览视频"}
          </Button>
          {videoResult?.video_url && (
            <Button 
              type="primary" 
              onClick={handleDownloadVideo}
              className="bg-green-600 hover:!bg-green-500 border-none font-bold flex items-center justify-center gap-1.5 px-5 ml-2"
            >
              <span className="material-symbols-outlined text-[18px]">download</span>
              导出该视频
            </Button>
          )}
        </div>
      </Modal>
    </>
  );
}