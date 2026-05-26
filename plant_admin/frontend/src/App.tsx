import { Modal, Table, Button, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import {
  Link,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import ExportLogsPage from "./pages/ExportLogsPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import PlantsPage from "./pages/PlantsPage";
import { PLANT_SIDEBAR_FLASH_EVENT, api, getToken, setToken } from "./api";

type TaxonBucketDto = { value: string; count: number };

type TaxonLevel = "division" | "subclass" | "taxonomic_order" | "family" | "genus";

const LEVEL_ORDER: TaxonLevel[] = ["division", "subclass", "taxonomic_order", "family", "genus"];
const LEVEL_PARAM: Record<TaxonLevel, string> = {
  division: "division",
  subclass: "subclass",
  taxonomic_order: "torder",
  family: "family",
  genus: "genus",
};
const LEVEL_LABELS: Record<TaxonLevel, string> = {
  division: "门",
  subclass: "亚纲",
  taxonomic_order: "目",
  family: "科",
  genus: "属",
};

function decodeJwtPayload(token: string): { username?: string; role?: string; sub?: number } {
  try {
    const p = token.split(".")[1];
    return JSON.parse(atob(p.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return {};
  }
}

function UserManagementModal({ open, onCancel, currentUserId }: { open: boolean; onCancel: () => void; currentUserId?: number }) {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      setLoading(true);
      api.get("/auth/users")
        .then(res => setUsers(res.data))
        .catch(e => message.error(String(e)))
        .finally(() => setLoading(false));
    }
  }, [open]);

  const toggleRole = async (u: any) => {
    const nextRole = u.role === "admin" ? "user" : "admin";
    try {
      await api.put(`/auth/users/${u.id}/role`, { role: nextRole });
      message.success("修改成功");
      setUsers(users.map(x => x.id === u.id ? { ...x, role: nextRole } : x));
    } catch(e: any) {
      message.error(e.response?.data?.detail || "修改失败");
    }
  };

  return (
    <Modal title="用户管理" open={open} onCancel={onCancel} footer={null} width={600}>
      <Table 
        dataSource={users} 
        loading={loading} 
        rowKey="id" 
        pagination={false}
        size="small"
        columns={[
          { title: "ID", dataIndex: "id", width: 60 },
          { title: "用户名", dataIndex: "username" },
          { title: "角色", dataIndex: "role", render: r => r === "admin" ? "管理员" : "普通用户" },
          { 
            title: "操作", 
            render: (_, u) => (
              <Button size="small" onClick={() => toggleRole(u)} disabled={u.id === currentUserId}>
                {u.role === "admin" ? "降级为普通用户" : "设为管理员"}
              </Button>
            )
          }
        ]}
      />
    </Modal>
  );
}

function AppShell() {
  const loc = useLocation();
  const nav = useNavigate();
  const [sp] = useSearchParams();
  const onPlantsPage = loc.pathname === "/plants";
  const [sidebarFlash, setSidebarFlash] = useState(false);
  const [userModalOpen, setUserModalOpen] = useState(false);

  // Tree path: each level's selected value (empty string = not selected)
  const treeDiv = onPlantsPage ? (sp.get("division") ?? "") : "";
  const treeSub = onPlantsPage ? (sp.get("subclass") ?? "") : "";
  const treeOrd = onPlantsPage ? (sp.get("torder") ?? "") : "";
  const treeFam = onPlantsPage ? (sp.get("family") ?? "") : "";
  const treeGen = onPlantsPage ? (sp.get("genus") ?? "") : "";

  // Next level to display: one position after the LAST set level in the URL.
  // Using "last set + 1" (not "first gap") correctly handles skipped null levels.
  // e.g. ?division=蕨类植物&family=金星蕨科 → lastSetIdx=3 → display "genus"
  const urlDerivedDisplayLevel: TaxonLevel = (() => {
    const lastSetIdx = Math.max(
      treeDiv ? 0 : -1,
      treeSub ? 1 : -1,
      treeOrd ? 2 : -1,
      treeFam ? 3 : -1,
      treeGen ? 4 : -1,
    );
    return (LEVEL_ORDER[
      lastSetIdx === -1 ? 0 : Math.min(lastSetIdx + 1, LEVEL_ORDER.length - 1)
    ] ?? "division") as TaxonLevel;
  })();

  // Deepest selected level – forwarded to PlantsPage via OutletCtx for its title
  const taxonLevel: TaxonLevel = treeGen
    ? "genus"
    : treeFam
      ? "family"
      : treeOrd
        ? "taxonomic_order"
        : treeSub
          ? "subclass"
          : "division";

  // Ordered array of selected ancestors for the sidebar breadcrumb
  const treeSelectedPath = useMemo(() => {
    const path: { level: TaxonLevel; value: string }[] = [];
    if (treeDiv) path.push({ level: "division", value: treeDiv });
    if (treeSub) path.push({ level: "subclass", value: treeSub });
    if (treeOrd) path.push({ level: "taxonomic_order", value: treeOrd });
    if (treeFam) path.push({ level: "family", value: treeFam });
    if (treeGen) path.push({ level: "genus", value: treeGen });
    return path;
  }, [treeDiv, treeSub, treeOrd, treeFam, treeGen]);

  const q = onPlantsPage ? sp.get("q") ?? "" : "";
  const [draft, setDraft] = useState(q);
  const [taxonItems, setTaxonItems] = useState<TaxonBucketDto[]>([]);
  const [taxonLoading, setTaxonLoading] = useState(false);
  const [taxonSidebarSearch, setTaxonSidebarSearch] = useState("");
  // When intermediate levels contain all-NULL data, auto-advance to the next non-empty level;
  // this override records which level was actually surfaced so the sidebar header and click
  // handlers use the right level name instead of the URL-derived one.
  const [displayLevelOverride, setDisplayLevelOverride] = useState<TaxonLevel | null>(null);
  const activeDisplayLevel: TaxonLevel = displayLevelOverride ?? urlDerivedDisplayLevel;

  useEffect(() => {
    setTaxonSidebarSearch("");
  }, [activeDisplayLevel]);

  useEffect(() => {
    setDraft(q);
  }, [q]);

  useEffect(() => {
    const onFlash = () => setSidebarFlash(true);
    window.addEventListener(PLANT_SIDEBAR_FLASH_EVENT, onFlash);
    return () => window.removeEventListener(PLANT_SIDEBAR_FLASH_EVENT, onFlash);
  }, []);

  useEffect(() => {
    if (!sidebarFlash) return;
    const t = window.setTimeout(() => setSidebarFlash(false), 2200);
    return () => window.clearTimeout(t);
  }, [sidebarFlash]);

  // Load children for the next display level; if a level returns all-NULL (0 items),
  // automatically advance to the next level until data is found.
  useEffect(() => {
    if (!onPlantsPage) {
      setTaxonItems([]);
      setDisplayLevelOverride(null);
      return;
    }
    let cancelled = false;
    // Determine the starting level index (one past the deepest set ancestor)
    const lastSetIdx = Math.max(
      treeDiv ? 0 : -1,
      treeSub ? 1 : -1,
      treeOrd ? 2 : -1,
      treeFam ? 3 : -1,
      treeGen ? 4 : -1,
    );
    const startIdx = lastSetIdx === -1 ? 0 : Math.min(lastSetIdx + 1, LEVEL_ORDER.length - 1);
    setTaxonLoading(true);
    (async () => {
      try {
        for (let idx = startIdx; idx < LEVEL_ORDER.length; idx++) {
          const level = LEVEL_ORDER[idx] as TaxonLevel;
          const params: Record<string, string> = { field: level };
          if (treeDiv) params.division = treeDiv;
          if (treeSub) params.subclass = treeSub;
          if (treeOrd) params.torder = treeOrd;
          if (treeFam) params.family = treeFam;
          const res = await api.get<{ items: TaxonBucketDto[] }>("/plants/taxonomy/distinct", {
            params,
          });
          if (cancelled) return;
          const items = res.data.items ?? [];
          if (items.length > 0 || idx === LEVEL_ORDER.length - 1) {
            setTaxonItems(items);
            // Record override only when we actually skipped levels
            setDisplayLevelOverride(idx > startIdx ? level : null);
            return;
          }
          // Empty at this level → try the next one
        }
      } catch {
        if (!cancelled) setTaxonItems([]);
      } finally {
        if (!cancelled) setTaxonLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [onPlantsPage, treeDiv, treeSub, treeOrd, treeFam, treeGen]);

  // If a sub-level value appears in the URL without ancestors, auto-resolve the full path
  useEffect(() => {
    if (!onPlantsPage || treeDiv) return;
    let deepestLevel: TaxonLevel | null = null;
    let deepestValue = "";
    if (treeGen) {
      deepestLevel = "genus";
      deepestValue = treeGen;
    } else if (treeFam) {
      deepestLevel = "family";
      deepestValue = treeFam;
    } else if (treeOrd) {
      deepestLevel = "taxonomic_order";
      deepestValue = treeOrd;
    } else if (treeSub) {
      deepestLevel = "subclass";
      deepestValue = treeSub;
    }
    if (!deepestLevel || !deepestValue) return;
    api
      .get<{ division?: string; subclass?: string; taxonomic_order?: string; family?: string }>(
        "/plants/taxonomy/resolve-path",
        { params: { level: deepestLevel, value: deepestValue } },
      )
      .then((res) => {
        const d = res.data;
        if (!d.division) return;
        const next = new URLSearchParams(sp);
        if (d.division) next.set("division", d.division);
        if (d.subclass) next.set("subclass", d.subclass);
        if (d.taxonomic_order) next.set("torder", d.taxonomic_order);
        if (d.family) next.set("family", d.family);
        next.delete("level");
        nav({ pathname: "/plants", search: `?${next.toString()}`, replace: true });
      })
      .catch(() => {});
    // sp and nav are stable; tree vars cover all relevant URL changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onPlantsPage, treeDiv, treeSub, treeOrd, treeFam, treeGen]);

  const filteredTaxonItems = useMemo(() => {
    const needle = taxonSidebarSearch.trim();
    if (!needle) return taxonItems;
    const lower = needle.toLowerCase();
    return taxonItems.filter(
      (item) => item.value.includes(needle) || item.value.toLowerCase().includes(lower),
    );
  }, [taxonItems, taxonSidebarSearch]);

  const token = getToken();
  const payload = token ? decodeJwtPayload(token) : {};
  const displayName = payload.username ?? "用户";
  const isAdmin = payload.role === "admin";

  function submitSearch() {
    const next = new URLSearchParams(loc.pathname === "/plants" ? loc.search : "");
    if (draft.trim()) next.set("q", draft.trim());
    else next.delete("q");
    const s = next.toString();
    nav({ pathname: "/plants", search: s ? `?${s}` : "" });
  }

  function selectTreeValue(level: TaxonLevel, value: string) {
    const next = new URLSearchParams(sp);
    const param = LEVEL_PARAM[level];
    const idx = LEVEL_ORDER.indexOf(level);
    if (next.get(param) === value) {
      // Toggle off: clear this level and everything deeper
      for (let i = idx; i < LEVEL_ORDER.length; i++) {
        next.delete(LEVEL_PARAM[LEVEL_ORDER[i]]);
      }
    } else {
      // Drill down: set this level, clear all deeper levels
      next.set(param, value);
      for (let i = idx + 1; i < LEVEL_ORDER.length; i++) {
        next.delete(LEVEL_PARAM[LEVEL_ORDER[i]]);
      }
    }
    next.delete("level");
    const s = next.toString();
    nav({ pathname: "/plants", search: s ? `?${s}` : "" });
  }

  function goBackToLevel(level: TaxonLevel) {
    const next = new URLSearchParams(sp);
    const idx = LEVEL_ORDER.indexOf(level);
    for (let i = idx; i < LEVEL_ORDER.length; i++) {
      next.delete(LEVEL_PARAM[LEVEL_ORDER[i]]);
    }
    next.delete("level");
    const s = next.toString();
    nav({ pathname: "/plants", search: s ? `?${s}` : "" });
  }

  function clearAllTree() {
    const next = new URLSearchParams(sp);
    LEVEL_ORDER.forEach((l) => next.delete(LEVEL_PARAM[l]));
    next.delete("level");
    const s = next.toString();
    nav({ pathname: "/plants", search: s ? `?${s}` : "" });
  }

  return (
    <div className="min-h-screen bg-background font-body-md text-body-md text-on-background">
      {/* Sidebar */}
      <aside
        id="plant-sidebar"
        className={`fixed left-0 top-0 z-40 flex h-screen w-sidebar flex-col border-r border-outline-variant bg-surface py-unit transition-shadow duration-300 ${
          sidebarFlash ? "shadow-[inset_0_0_0_2px] shadow-primary ring-2 ring-inset ring-primary/60" : ""
        }`}
      >
        <div className="flex flex-shrink-0 flex-col gap-1 px-6 py-4">
          <span className="font-h3 text-h3 font-semibold text-primary">分类探索器</span>
          <span className="font-label-sm text-label-sm text-on-surface-variant">管理控制台</span>
        </div>
        {/* Tree breadcrumb – shows selected ancestors; clicking navigates back */}
        {onPlantsPage && (
          <div className="mt-3 flex-shrink-0 px-3">
            {treeSelectedPath.length > 0 ? (
              <div className="flex flex-wrap items-center gap-x-0.5 gap-y-1 rounded-lg bg-surface-container-low px-2 py-1.5">
                <button
                  type="button"
                  onClick={clearAllTree}
                  className="font-label-sm text-label-sm text-primary hover:underline"
                >
                  全部
                </button>
                {treeSelectedPath.map((item) => (
                  <span key={item.level} className="flex items-center gap-0.5">
                    <span className="material-symbols-outlined text-[13px] text-on-surface-variant">
                      chevron_right
                    </span>
                    <button
                      type="button"
                      title={item.value}
                      onClick={() => goBackToLevel(item.level)}
                      className="max-w-[88px] truncate font-label-sm text-label-sm text-primary hover:underline"
                    >
                      {item.value}
                    </button>
                  </span>
                ))}
              </div>
            ) : (
              <p className="px-1 font-label-sm text-label-sm text-on-surface-variant">
                点击分类逐层钻取筛选
              </p>
            )}
          </div>
        )}
        {onPlantsPage && (
          <div className="mt-2 flex min-h-0 flex-1 flex-col px-2">
            {/* Current level header */}
            <div className="flex-shrink-0 px-2 pb-1.5 font-label-sm text-label-sm font-semibold text-on-surface">
              {LEVEL_LABELS[activeDisplayLevel]}
              {treeSelectedPath.length > 0 && (
                <span className="ml-1 font-normal text-on-surface-variant">
                  （{treeSelectedPath[treeSelectedPath.length - 1].value} 下）
                </span>
              )}
            </div>
            <div className="flex-shrink-0 px-2 pb-2">
              <div className="relative">
                <span className="material-symbols-outlined pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant">
                  search
                </span>
                <input
                  className="w-full rounded-lg border border-outline-variant bg-surface-container-low py-1.5 pl-8 pr-2 font-label-sm text-label-sm text-on-background outline-none transition-all placeholder:text-on-surface-variant/70 focus:border-primary focus:ring-0"
                  placeholder={`筛选${LEVEL_LABELS[activeDisplayLevel]}…`}
                  type="search"
                  value={taxonSidebarSearch}
                  onChange={(e) => setTaxonSidebarSearch(e.target.value)}
                  aria-label="筛选当前层级分类列表"
                />
              </div>
              {!taxonLoading && taxonItems.length > 0 ? (
                <div className="mt-1 px-1 font-label-sm text-label-sm text-on-surface-variant">
                  {filteredTaxonItems.length === taxonItems.length
                    ? `共 ${taxonItems.length} 项`
                    : `显示 ${filteredTaxonItems.length} / ${taxonItems.length}`}
                </div>
              ) : null}
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto pr-1">
              {taxonLoading && (
                <div className="px-4 py-2 font-label-sm text-label-sm text-on-surface-variant">加载中…</div>
              )}
              {!taxonLoading && taxonItems.length === 0 && (
                <div className="px-4 py-2 font-label-sm text-label-sm text-on-surface-variant">暂无分类数据</div>
              )}
              {!taxonLoading && taxonItems.length > 0 && filteredTaxonItems.length === 0 && (
                <div className="px-4 py-2 font-label-sm text-label-sm text-on-surface-variant">
                  无匹配项，请修改关键词
                </div>
              )}
              {!taxonLoading &&
                filteredTaxonItems.map((item) => {
                  const v = item.value;
                  const isSelected = sp.get(LEVEL_PARAM[activeDisplayLevel]) === v;
                  const isLeaf = activeDisplayLevel === "genus";
                  return (
                    <button
                      key={v}
                      type="button"
                      title={v}
                      onClick={() => selectTreeValue(activeDisplayLevel, v)}
                      className={`mb-0.5 flex w-full items-center gap-2 rounded px-3 py-2 text-left font-label-sm text-label-sm transition-colors ${
                        isSelected
                          ? "bg-primary-container/20 font-semibold text-primary"
                          : "text-on-surface-variant hover:bg-primary/5"
                      }`}
                    >
                      <span
                        className="material-symbols-outlined flex-shrink-0 text-[16px]"
                        style={isSelected ? { fontVariationSettings: "'FILL' 1" } : undefined}
                      >
                        {isSelected ? "check_circle" : isLeaf ? "circle" : "chevron_right"}
                      </span>
                      <span className="min-w-0 flex-1 break-words">
                        {v}
                        <span className="ml-1 whitespace-nowrap font-normal text-on-surface-variant">
                          ({item.count})
                        </span>
                      </span>
                    </button>
                  );
                })}
            </div>
          </div>
        )}
        <div className="mt-auto flex flex-shrink-0 flex-col gap-2 px-4 pb-4 pt-2">
          {isAdmin && (
            <button
              type="button"
              onClick={() => nav("/plants?add=1")}
              className="flex w-full items-center justify-center gap-2 rounded bg-primary px-4 py-3 font-label-sm text-label-sm text-on-primary transition-colors hover:bg-primary-container"
            >
              <span className="material-symbols-outlined text-[18px]">add_circle</span>
              添加标本
            </button>
          )}
        </div>
      </aside>

      {/* Top bar */}
      <header className="fixed left-0 top-0 z-30 ml-0 flex h-16 w-full items-center justify-between border-b border-outline-variant bg-surface-container-lowest pl-sidebar pr-margin">
        <div className="flex items-center gap-8 pl-gutter">
          <h1 className="font-h3 text-h3 font-semibold text-primary whitespace-nowrap">中国植物库</h1>
          <div className="flex max-w-[40vw] w-[380px] items-center gap-2">
            <div className="relative min-w-0 flex-1">
              <span className="material-symbols-outlined pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[20px] text-on-surface-variant">
                search
              </span>
              <input
                className="w-full rounded-lg border border-outline-variant bg-surface-container-low py-2 pl-10 pr-10 font-body-md text-body-md text-on-background outline-none transition-all placeholder:text-on-surface-variant/70 focus:border-primary focus:ring-0"
                placeholder="搜索标本、科属或ID"
                type="text"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submitSearch()}
              />
              {draft && (
                <button
                  type="button"
                  className="absolute right-2 top-1/2 -translate-y-1/2 flex h-6 w-6 items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                  onClick={() => {
                    setDraft("");
                    const next = new URLSearchParams(loc.pathname === "/plants" ? loc.search : "");
                    next.delete("q");
                    nav({ pathname: "/plants", search: next.toString() ? `?${next.toString()}` : "" });
                  }}
                  title="清空搜索"
                >
                  <span className="material-symbols-outlined text-[16px]">close</span>
                </button>
              )}
            </div>
            <button
              type="button"
              onClick={submitSearch}
              className="flex-shrink-0 rounded-lg border border-primary bg-primary px-3 py-2 font-label-sm text-label-sm text-on-primary transition-colors hover:bg-primary-container"
            >
              搜索
            </button>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <nav className="mr-6 hidden items-center gap-6 md:flex">
            <Link
              to="/plants"
              className={`border-b-2 py-5 font-label-sm text-label-sm ${
                loc.pathname === "/plants"
                  ? "border-primary font-semibold text-primary"
                  : "border-transparent text-on-surface-variant hover:bg-secondary-container/10 px-2"
              }`}
            >
              首页
            </Link>
            <a
              href="https://www.plantplus.cn/"
              target="_blank"
              rel="noreferrer"
              className="py-5 px-2 font-label-sm text-label-sm text-on-surface-variant transition-colors hover:bg-secondary-container/10"
            >
              中国植物志
            </a>
          </nav>
          <div className="flex items-center gap-2">
            <span className="hidden rounded-full border border-outline-variant bg-surface-container-high px-3 py-1 font-label-sm text-label-sm text-on-surface-variant sm:inline">
              {isAdmin ? "管理员" : "用户"} · {displayName}
            </span>
            <button
              type="button"
              className="material-symbols-outlined rounded-full p-2 text-on-surface-variant transition-colors hover:bg-secondary-container/10"
              aria-label="通知"
            >
              notifications
            </button>
            <button
              type="button"
              className="material-symbols-outlined rounded-full p-2 text-on-surface-variant transition-colors hover:bg-secondary-container/10"
              aria-label="帮助"
            >
              help
            </button>
            {isAdmin && (
              <button
                type="button"
                onClick={() => setUserModalOpen(true)}
                className="material-symbols-outlined rounded-full p-2 text-on-surface-variant transition-colors hover:bg-secondary-container/10"
                aria-label="用户管理"
                title="用户管理"
              >
                manage_accounts
              </button>
            )}
            <div className="ml-2 flex h-8 w-8 items-center justify-center overflow-hidden rounded-full border border-outline-variant bg-primary-container text-xs font-semibold text-on-primary">
              {displayName.slice(0, 1).toUpperCase()}
            </div>
            <button
              type="button"
              onClick={() => {
                setToken(null);
                window.location.href = "/login";
              }}
              className="ml-2 font-label-sm text-label-sm text-on-surface-variant hover:text-primary"
            >
              退出
            </button>
          </div>
        </div>
      </header>

      <main className="min-h-screen pl-sidebar pt-16">
        <div className="mx-auto max-w-container p-margin">
          <Outlet context={{ taxonLevel }} />
        </div>
      </main>
      
      {isAdmin && (
        <UserManagementModal 
          open={userModalOpen} 
          onCancel={() => setUserModalOpen(false)} 
          currentUserId={payload.sub ? Number(payload.sub) : undefined}
        />
      )}
    </div>
  );
}

function RequireAuth() {
  if (!getToken()) {
    return <Navigate to="/login" replace />;
  }
  return <AppShell />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<RequireAuth />}>
        <Route path="/plants" element={<PlantsPage />} />
        <Route path="/export-logs" element={<ExportLogsPage />} />
      </Route>
      <Route path="/" element={<Navigate to="/plants" replace />} />
      <Route path="*" element={<Navigate to="/plants" replace />} />
    </Routes>
  );
}
