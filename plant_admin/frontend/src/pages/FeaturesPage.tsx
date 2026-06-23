import React, { useEffect, useState } from "react";
import {
  Card,
  Tabs,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Row,
  Col,
  Tag,
  Badge,
  Divider,
  Tooltip,
  Drawer,
  Spin,
  Empty,
  message,
  Popconfirm
} from "antd";
import { api, Plant, PlantRanking, PlantRegion, PlantConfusionGroup, PlantConfusionItem, getToken } from "../api";

const { TextArea } = Input;
const { Option } = Select;

// Simple JWT Decode helper
function decodeJwtPayload(token: string): { username?: string; role?: string } {
  try {
    const p = token.split(".")[1];
    return JSON.parse(atob(p.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return {};
  }
}

export default function FeaturesPage() {
  const [activeTab, setActiveTab] = useState<string>("habitats");
  
  // User info
  const token = getToken();
  const payload = token ? decodeJwtPayload(token) : {};
  const isAdmin = payload.role === "admin";

  // Shared Detail Drawer
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailPlant, setDetailPlant] = useState<Plant | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailActiveTab, setDetailActiveTab] = useState("morphology");

  const showPlantDetail = async (plantId: number) => {
    setDetailLoading(true);
    setDetailOpen(true);
    try {
      const res = await api.get<Plant>(`/plants/${plantId}`);
      setDetailPlant(res.data);
    } catch (e) {
      message.error("加载植物详情失败");
      setDetailOpen(false);
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-2xl border border-primary/20 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent p-6 shadow-sm">
        <h1 className="font-display-lg text-2xl font-bold text-primary flex items-center gap-2">
          <span className="material-symbols-outlined text-[28px]">dashboard</span>
          特色专区 & 聚合功能
        </h1>
        <p className="mt-1.5 font-body-md text-sm text-on-surface-variant max-w-2xl">
          查看场景分类分布、特色排行榜、道地药材区域组合，或通过易混淆专题进行植物的形态与药用特征的多维度对比。
        </p>
      </div>

      {/* Main Tabs */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        type="card"
        className="features-tabs-custom"
        items={[
          {
            key: "habitats",
            label: (
              <span className="flex items-center gap-1.5 px-1 py-0.5">
                <span className="material-symbols-outlined text-[18px]">nature_people</span>
                生境场景分类
              </span>
            ),
            children: <HabitatsTab showPlantDetail={showPlantDetail} />
          },
          {
            key: "rankings",
            label: (
              <span className="flex items-center gap-1.5 px-1 py-0.5">
                <span className="material-symbols-outlined text-[18px]">leaderboard</span>
                特色排行榜
              </span>
            ),
            children: <RankingsTab showPlantDetail={showPlantDetail} />
          },
          {
            key: "regions",
            label: (
              <span className="flex items-center gap-1.5 px-1 py-0.5">
                <span className="material-symbols-outlined text-[18px]">map</span>
                道地药材地图
              </span>
            ),
            children: <RegionsTab showPlantDetail={showPlantDetail} />
          },
          {
            key: "confusion",
            label: (
              <span className="flex items-center gap-1.5 px-1 py-0.5">
                <span className="material-symbols-outlined text-[18px]">difference</span>
                易混淆专题比对
              </span>
            ),
            children: <ConfusionTab isAdmin={isAdmin} showPlantDetail={showPlantDetail} />
          }
        ]}
      />

      {/* Shared Detail Drawer */}
      <Drawer
        title={detailPlant ? `${detailPlant.vernacular_name || ""} ${detailPlant.scientific_name || ""}` : "植物详情"}
        placement="right"
        width={720}
        onClose={() => {
          setDetailOpen(false);
          setDetailPlant(null);
        }}
        open={detailOpen}
        extra={
          detailPlant?.is_medicinal_food_homologous === "是" && (
            <Tag color="success" className="rounded-full">药食同源</Tag>
          )
        }
      >
        <Spin spinning={detailLoading}>
          {detailPlant && (
            <div className="space-y-6">
              {/* Taxonomy Summary */}
              <div className="rounded-xl bg-surface-container-low p-4 border border-outline-variant/30 flex flex-wrap gap-y-2 gap-x-6 text-sm text-on-surface-variant">
                <div><span className="font-semibold text-primary">门：</span>{detailPlant.division || "-"}</div>
                <div><span className="font-semibold text-primary">亚纲：</span>{detailPlant.subclass || "-"}</div>
                <div><span className="font-semibold text-primary">目：</span>{detailPlant.taxonomic_order || "-"}</div>
                <div><span className="font-semibold text-primary">科：</span>{detailPlant.family || "-"}</div>
                <div><span className="font-semibold text-primary">属：</span>{detailPlant.genus || "-"}</div>
              </div>

              {/* Images if any */}
              {detailPlant.image_url && (
                <div className="flex justify-center bg-surface-container-high rounded-xl p-3 border border-outline-variant/20">
                  <img
                    src={detailPlant.image_url}
                    alt={detailPlant.vernacular_name || ""}
                    className="max-h-[280px] rounded-lg object-contain shadow-sm"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src =
                        "https://placehold.co/400x300?text=" + encodeURIComponent(detailPlant.vernacular_name || "无图");
                    }}
                  />
                </div>
              )}

              {/* Tabs for details */}
              <Tabs
                activeKey={detailActiveTab}
                onChange={setDetailActiveTab}
                items={[
                  {
                    key: "morphology",
                    label: "形态与性状",
                    children: (
                      <div className="space-y-4 pt-2">
                        <div>
                          <h4 className="font-semibold text-primary text-sm flex items-center gap-1 mb-1">
                            <span className="material-symbols-outlined text-[16px]">menu_book</span>
                            形态特征
                          </h4>
                          <p className="text-on-surface text-sm leading-relaxed whitespace-pre-wrap">
                            {detailPlant.morphology_text || "无记录"}
                          </p>
                        </div>
                        <div>
                          <h4 className="font-semibold text-primary text-sm flex items-center gap-1 mb-1">
                            <span className="material-symbols-outlined text-[16px]">medical_services</span>
                            药用性状
                          </h4>
                          <p className="text-on-surface text-sm leading-relaxed whitespace-pre-wrap">
                            {detailPlant.medicinal_shape || "无记录"}
                          </p>
                        </div>
                      </div>
                    )
                  },
                  {
                    key: "distribution",
                    label: "生境分布",
                    children: (
                      <div className="space-y-4 pt-2">
                        <div>
                          <h4 className="font-semibold text-primary text-sm flex items-center gap-1 mb-1">
                            <span className="material-symbols-outlined text-[16px]">explore</span>
                            生境
                          </h4>
                          <p className="text-on-surface text-sm leading-relaxed">{detailPlant.habitat || "无记录"}</p>
                        </div>
                        <div>
                          <h4 className="font-semibold text-primary text-sm flex items-center gap-1 mb-1">
                            <span className="material-symbols-outlined text-[16px]">map</span>
                            国内分布
                          </h4>
                          <p className="text-on-surface text-sm leading-relaxed">{detailPlant.distribution_china || "无记录"}</p>
                        </div>
                        <div>
                          <h4 className="font-semibold text-primary text-sm flex items-center gap-1 mb-1">
                            <span className="material-symbols-outlined text-[16px]">public</span>
                            国外分布
                          </h4>
                          <p className="text-on-surface text-sm leading-relaxed">{detailPlant.distribution_abroad || "无记录"}</p>
                        </div>
                      </div>
                    )
                  },
                  {
                    key: "harvest",
                    label: "最佳采收",
                    children: (
                      <div className="space-y-4 pt-2">
                        <div>
                          <h4 className="font-semibold text-primary text-sm flex items-center gap-1 mb-1">
                            <span className="material-symbols-outlined text-[16px]">calendar_today</span>
                            适合采收月份
                          </h4>
                          <div className="flex flex-wrap gap-1 mb-2">
                            {detailPlant.harvest_months ? (
                              detailPlant.harvest_months.split(",").map(m => (
                                <Tag color="green" key={m} className="rounded-md font-semibold">{m}月</Tag>
                              ))
                            ) : (
                              <span className="text-on-surface-variant text-sm">暂无指定月份</span>
                            )}
                          </div>
                        </div>
                        <div>
                          <h4 className="font-semibold text-primary text-sm flex items-center gap-1 mb-1">
                            <span className="material-symbols-outlined text-[16px]">info</span>
                            采收及炮制详细说明 (AI 填充)
                          </h4>
                          <div className="rounded-xl bg-green-50/50 p-4 border border-green-100 text-on-surface text-sm leading-relaxed whitespace-pre-wrap">
                            {detailPlant.harvest_months_desc || "暂无说明，请在首页编辑该植物，点击一键 AI 智能填充。"}
                          </div>
                        </div>
                      </div>
                    )
                  },
                  {
                    key: "food_therapy",
                    label: "食疗入药",
                    children: (
                      <div className="space-y-4 pt-2">
                        <div>
                          <h4 className="font-semibold text-primary text-sm flex items-center gap-1 mb-1">
                            <span className="material-symbols-outlined text-[16px]">health_and_safety</span>
                            适合食疗/药膳月份
                          </h4>
                          <div className="flex flex-wrap gap-1 mb-2">
                            {detailPlant.food_therapy_months ? (
                              detailPlant.food_therapy_months.split(",").map(m => (
                                <Tag color="orange" key={m} className="rounded-md font-semibold">{m}月</Tag>
                              ))
                            ) : (
                              <span className="text-on-surface-variant text-sm">暂无指定月份</span>
                            )}
                          </div>
                        </div>
                        <div>
                          <h4 className="font-semibold text-primary text-sm flex items-center gap-1 mb-1">
                            <span className="material-symbols-outlined text-[16px]">security</span>
                            食疗用药安全及服用建议 (AI 填充)
                          </h4>
                          <div className="rounded-xl bg-orange-50/50 p-4 border border-orange-100 text-on-surface text-sm leading-relaxed whitespace-pre-wrap">
                            {detailPlant.food_therapy_months_desc || "暂无说明，请在首页编辑该植物，点击一键 AI 智能填充。"}
                          </div>
                        </div>
                      </div>
                    )
                  }
                ]}
              />
            </div>
          )}
        </Spin>
      </Drawer>
    </div>
  );
}

// =========================================================
// 3. HABITATS TAB
// =========================================================
function HabitatsTab({ showPlantDetail }: { showPlantDetail: (id: number) => void }) {
  const [summary, setSummary] = useState<any[]>([]);
  const [selectedHabitat, setSelectedHabitat] = useState<string | null>("森林");
  const [plants, setPlants] = useState<Plant[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [loading, setLoading] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(false);

  // Gradient styles for habitat cards
  const habitatStyles: Record<string, { bg: string; icon: string; title: string }> = {
    海洋: { bg: "from-blue-600 to-indigo-800", icon: "sailing", title: "海洋与滨海植物" },
    湿地: { bg: "from-cyan-600 to-teal-800", icon: "water", title: "湖泊与温地植物" },
    森林: { bg: "from-green-600 to-emerald-800", icon: "forest", title: "茂密森林与山地" },
    草原: { bg: "from-lime-600 to-green-700", icon: "grass", title: "辽阔草原与草甸" },
    荒漠: { bg: "from-amber-600 to-orange-800", icon: "landscape", title: "干旱荒漠与沙地" }
  };

  const loadSummary = async () => {
    setSummaryLoading(true);
    try {
      const res = await api.get("/features/habitats/summary");
      setSummary(res.data);
    } catch (e) {
      message.error("加载场景分类概况失败");
    } finally {
      setSummaryLoading(false);
    }
  };

  const loadPlants = async (habitat: string, currPage: number) => {
    setLoading(true);
    try {
      const res = await api.get("/features/habitats", {
        params: { habitat_type: habitat, page: currPage, page_size: pageSize }
      });
      setPlants(res.data.items);
      setTotal(res.data.total);
    } catch (e) {
      message.error("加载生境植物列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  useEffect(() => {
    if (selectedHabitat) {
      loadPlants(selectedHabitat, page);
    }
  }, [selectedHabitat, page]);

  return (
    <div className="space-y-6 pt-2">
      {/* 5 Cards */}
      <Spin spinning={summaryLoading}>
        <Row gutter={[16, 16]}>
          {["森林", "草原", "湿地", "荒漠", "海洋"].map((type) => {
            const sumItem = summary.find(s => s.habitat_type === type);
            const count = sumItem ? sumItem.count : 0;
            const style = habitatStyles[type] || { bg: "from-gray-600 to-slate-800", icon: "spa", title: type };
            const isSelected = selectedHabitat === type;

            return (
              <Col xs={24} sm={12} md={8} lg={4} key={type}>
                <div
                  onClick={() => {
                    setSelectedHabitat(type);
                    setPage(1);
                  }}
                  className={`relative overflow-hidden rounded-2xl p-5 text-white cursor-pointer transition-all duration-300 hover:scale-[1.03] hover:shadow-lg bg-gradient-to-br ${style.bg} ${
                    isSelected ? "ring-4 ring-offset-2 ring-primary scale-[1.03]" : "opacity-85 hover:opacity-100"
                  }`}
                >
                  <span className="material-symbols-outlined text-[36px] opacity-25 absolute right-4 top-4">
                    {style.icon}
                  </span>
                  <div className="text-xs uppercase tracking-wider font-semibold opacity-75">{style.title}</div>
                  <div className="mt-2 text-xl font-bold">{type}</div>
                  <div className="mt-4 flex items-baseline gap-1">
                    <span className="text-2xl font-bold">{count}</span>
                    <span className="text-xs opacity-75">株植物</span>
                  </div>
                </div>
              </Col>
            );
          })}
        </Row>
      </Spin>

      {/* Plants list */}
      {selectedHabitat && (
        <Card
          title={
            <span className="flex items-center gap-2 text-primary font-semibold">
              <span className="material-symbols-outlined">filter_list</span>
              {selectedHabitat} 场景植物列表
            </span>
          }
          className="rounded-2xl border border-outline-variant/30 shadow-sm"
        >
          <Table
            dataSource={plants}
            loading={loading}
            rowKey="id"
            size="middle"
            columns={[
              { title: "中文名称", dataIndex: "vernacular_name", render: (name, r) => <a onClick={() => showPlantDetail(r.id)} className="font-semibold text-primary">{name || "-"}</a> },
              { title: "拉丁名", dataIndex: "scientific_name", render: s => <span className="italic text-on-surface-variant">{s || "-"}</span> },
              { title: "科", dataIndex: "family", render: f => f || "-" },
              { title: "属", dataIndex: "genus", render: g => g || "-" },
              { title: "生境描述", dataIndex: "habitat", render: h => <span className="text-xs line-clamp-1 max-w-[280px]" title={h}>{h || "-"}</span> },
              { title: "最佳采收期", dataIndex: "harvest_months", render: m => m ? <Tag color="green">{m}月</Tag> : "-" },
              { title: "药食同源", dataIndex: "is_medicinal_food_homologous", render: v => v === "是" ? <Tag color="success">是</Tag> : "-" }
            ]}
            pagination={{
              current: page,
              pageSize: pageSize,
              total: total,
              onChange: setPage,
              showSizeChanger: false,
              size: "small"
            }}
          />
        </Card>
      )}
    </div>
  );
}

// =========================================================
// 4. RANKINGS TAB
// =========================================================
function RankingsTab({ showPlantDetail }: { showPlantDetail: (id: number) => void }) {
  const [summary, setSummary] = useState<any[]>([]);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [plants, setPlants] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // Friendly names for ranking types
  const typeMap: Record<string, { label: string; icon: string; desc: string }> = {
    sweetest: { label: "最甜植物", icon: "cookie", desc: "自然界中含甜味素或糖分极高的甜草类植物" },
    bitterest: { label: "最苦植物", icon: "mood_bad", desc: "常含有极高黄酮或生物碱的极苦中草药" },
    rarity: { label: "珍稀濒危物种", icon: "verified_user", desc: "国家一级保护或野外极难寻觅的重点保护植物" },
    growth_cycle: { label: "特殊生长周期", icon: "hourglass_empty", desc: "生长、开花或结果周期漫长而规律奇特的物种" }
  };

  const loadSummary = async () => {
    try {
      const res = await api.get("/features/rankings/summary");
      setSummary(res.data);
      if (res.data.length > 0) {
        setSelectedType(res.data[0].ranking_type);
      } else {
        // Fallback default
        setSelectedType("sweetest");
      }
    } catch (e) {
      message.error("加载排行榜类型失败");
    }
  };

  const loadRankings = async (type: string) => {
    setLoading(true);
    try {
      const res = await api.get(`/features/rankings?ranking_type=${type}`);
      setPlants(res.data);
    } catch (e) {
      message.error("加载榜单详情失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  useEffect(() => {
    if (selectedType) {
      loadRankings(selectedType);
    }
  }, [selectedType]);

  const activeMeta = selectedType ? (typeMap[selectedType] || { label: selectedType, icon: "award", desc: "特色分类榜单" }) : null;

  return (
    <div className="pt-2">
      <Row gutter={24}>
        {/* Left list of rankings */}
        <Col xs={24} md={8}>
          <Card title="特色榜单分类" className="rounded-2xl border border-outline-variant/30 shadow-sm">
            <div className="space-y-2">
              {["sweetest", "bitterest", "rarity", "growth_cycle"].map((type) => {
                const meta = typeMap[type] || { label: type, icon: "award", desc: "" };
                const isSelected = selectedType === type;
                const dbItem = summary.find(s => s.ranking_type === type);
                const count = dbItem ? dbItem.count : 0;

                return (
                  <div
                    key={type}
                    onClick={() => setSelectedType(type)}
                    className={`flex items-center gap-3 p-3.5 rounded-xl cursor-pointer transition-all border ${
                      isSelected
                        ? "bg-primary/5 border-primary shadow-sm"
                        : "bg-surface border-outline-variant/30 hover:bg-surface-container-low"
                    }`}
                  >
                    <div className={`p-2 rounded-lg flex items-center justify-center ${
                      isSelected ? "bg-primary text-on-primary" : "bg-surface-container text-on-surface-variant"
                    }`}>
                      <span className="material-symbols-outlined text-[20px]">{meta.icon}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-sm text-on-surface">{meta.label}</div>
                      <div className="text-xs text-on-surface-variant truncate">{meta.desc}</div>
                    </div>
                    <Badge count={count} showZero color={isSelected ? "green" : "grey"} />
                  </div>
                );
              })}
            </div>
          </Card>
        </Col>

        {/* Right leaderboard view */}
        <Col xs={24} md={16}>
          {activeMeta && (
            <Card
              title={
                <div className="py-1">
                  <div className="text-lg font-bold text-primary flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[22px]">{activeMeta.icon}</span>
                    {activeMeta.label}
                  </div>
                  <div className="text-xs text-on-surface-variant font-normal mt-0.5">{activeMeta.desc}</div>
                </div>
              }
              className="rounded-2xl border border-outline-variant/30 shadow-sm"
            >
              <Spin spinning={loading}>
                {plants.length === 0 ? (
                  <Empty description="该榜单暂无植物数据，请编辑植物详情添加排行榜分类" />
                ) : (
                  <div className="space-y-4">
                    {plants.map((item, idx) => {
                      const rank = idx + 1;
                      // Rank styling for Top 3
                      const badgeBg = rank === 1 ? "bg-amber-400 text-white font-bold" :
                                      rank === 2 ? "bg-slate-300 text-white font-bold" :
                                      rank === 3 ? "bg-amber-600 text-white font-bold" :
                                      "bg-surface-container-high text-on-surface-variant";

                      return (
                        <div
                          key={item.plant.id}
                          className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-xl border border-outline-variant/20 bg-surface-container-lowest hover:shadow-md transition-shadow"
                        >
                          <div className="flex items-center gap-4 flex-1 min-w-0">
                            {/* Rank circle */}
                            <div className={`h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0 text-sm ${badgeBg}`}>
                              {rank}
                            </div>
                            
                            {/* Plant details */}
                            <div className="min-w-0">
                              <div className="flex items-baseline gap-2 flex-wrap">
                                <a onClick={() => showPlantDetail(item.plant.id)} className="font-semibold text-primary text-base hover:underline">
                                  {item.plant.vernacular_name || "未知"}
                                </a>
                                <span className="text-xs italic text-on-surface-variant truncate max-w-[200px]">
                                  {item.plant.scientific_name}
                                </span>
                                <Tag color="blue" className="rounded-md scale-90">{item.plant.family} · {item.plant.genus}</Tag>
                              </div>
                              <div className="text-xs text-on-surface-variant mt-1 leading-relaxed line-clamp-2">
                                {item.description || "暂无本排名理由详细描述"}
                              </div>
                            </div>
                          </div>

                          {/* Ranking value */}
                          {item.ranking_value && (
                            <div className="mt-2 sm:mt-0 ml-12 sm:ml-4 text-right flex-shrink-0">
                              <span className="text-xs text-on-surface-variant block">指标数值</span>
                              <span className="font-display-md text-lg font-bold text-secondary">{item.ranking_value}</span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </Spin>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
}

// =========================================================
// 5. REGIONS TAB
// =========================================================
function RegionsTab({ showPlantDetail }: { showPlantDetail: (id: number) => void }) {
  const [summary, setSummary] = useState<any[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  const [selectedCombo, setSelectedCombo] = useState<string | null>(null);
  const [plants, setPlants] = useState<Plant[]>([]);
  const [loading, setLoading] = useState(false);

  // Daodi combos metadata
  const combosMeta = [
    { province: "浙江", combo: "浙八味", desc: "杭白菊、麦冬、玄参、温郁金、白术、延胡索、芍药、山茱萸" },
    { province: "河南", combo: "四大怀药", desc: "怀地黄、怀山药、怀牛膝、怀菊花" },
    { province: "四川", combo: "川药", desc: "川贝母、川芎、黄连、附子" },
    { province: "广东", combo: "广药", desc: "陈皮、砂仁、巴戟天、化橘红" },
    { province: "吉林", combo: "关药", desc: "人参、细辛、五味子、鹿茸" },
    { province: "云南", combo: "云药", desc: "三七、天麻、重楼、茯苓" }
  ];

  const loadSummary = async () => {
    try {
      const res = await api.get("/features/regions/summary");
      setSummary(res.data);
      // Default select first combo if exists, else Zhejiang
      setSelectedCombo("浙八味");
      setSelectedRegion("浙江");
    } catch (e) {
      message.error("加载道地药材汇总失败");
    }
  };

  const loadPlants = async (region: string | null, combo: string | null) => {
    setLoading(true);
    try {
      const res = await api.get("/features/regions", {
        params: { region_name: region, combo_name: combo }
      });
      setPlants(res.data);
    } catch (e) {
      message.error("加载道地药材列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  useEffect(() => {
    if (selectedRegion || selectedCombo) {
      loadPlants(selectedRegion, selectedCombo);
    }
  }, [selectedRegion, selectedCombo]);

  return (
    <div className="space-y-6 pt-2">
      {/* Provinces Grid / Combos */}
      <Row gutter={[16, 16]}>
        {combosMeta.map((item) => {
          const isSelected = selectedCombo === item.combo;
          const dbItem = summary.find(s => s.combo_name === item.combo);
          const count = dbItem ? dbItem.count : 0;

          return (
            <Col xs={24} sm={12} md={8} lg={4} key={item.combo}>
              <div
                onClick={() => {
                  setSelectedCombo(item.combo);
                  setSelectedRegion(item.province);
                }}
                className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between h-[135px] ${
                  isSelected
                    ? "bg-primary/5 border-primary shadow-sm ring-2 ring-primary"
                    : "bg-surface border-outline-variant/30 hover:bg-surface-container-low"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-surface-container text-primary">
                      {item.province}
                    </span>
                    <span className="text-xs text-on-surface-variant font-semibold">{count} 品种</span>
                  </div>
                  <h3 className="text-base font-bold text-on-surface mt-2">{item.combo}</h3>
                  <p className="text-xs text-on-surface-variant mt-1.5 line-clamp-2" title={item.desc}>
                    {item.desc}
                  </p>
                </div>
              </div>
            </Col>
          );
        })}
      </Row>

      {/* Daodi Table */}
      <Card
        title={
          <span className="flex items-center gap-2 text-primary font-semibold">
            <span className="material-symbols-outlined">verified</span>
            {selectedRegion}「{selectedCombo}」经典道地中药材物种
          </span>
        }
        className="rounded-2xl border border-outline-variant/30 shadow-sm"
      >
        <Table
          dataSource={plants}
          loading={loading}
          rowKey="id"
          size="middle"
          columns={[
            { title: "中文名称", dataIndex: "vernacular_name", render: (name, r) => <a onClick={() => showPlantDetail(r.id)} className="font-semibold text-primary">{name || "-"}</a> },
            { title: "拉丁名", dataIndex: "scientific_name", render: s => <span className="italic text-on-surface-variant">{s || "-"}</span> },
            { title: "科", dataIndex: "family", render: f => f || "-" },
            { title: "属", dataIndex: "genus", render: g => g || "-" },
            { title: "食疗入药月份", dataIndex: "food_therapy_months", render: m => m ? <Tag color="orange">{m}月</Tag> : "-" },
            {
              title: "药用分布/道地性",
              render: (_, r) => {
                const regInfo = r.regions?.find(x => x.combo_name === selectedCombo);
                return (
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <Tag color="success" className="rounded-md">道地地：{selectedRegion}</Tag>
                    {regInfo?.combo_name && <Tag color="blue" className="rounded-md">{regInfo.combo_name}</Tag>}
                  </div>
                );
              }
            }
          ]}
          pagination={false}
        />
      </Card>
    </div>
  );
}

// =========================================================
// 6. CONFUSION TAB
// =========================================================
function ConfusionTab({ isAdmin, showPlantDetail }: { isAdmin: boolean; showPlantDetail: (id: number) => void }) {
  const [groups, setGroups] = useState<PlantConfusionGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<PlantConfusionGroup | null>(null);
  const [loading, setLoading] = useState(false);

  // Modals for CRUD
  const [modalOpen, setModalOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<PlantConfusionGroup | null>(null);
  const [form] = Form.useForm();
  const [formItems, setFormItems] = useState<{ plant_id: number; distinguish_point: string; label: string }[]>([]);

  // Search plants in modal
  const [searchVal, setSearchVal] = useState("");
  const [searchResults, setSearchResults] = useState<Plant[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);

  const loadGroups = async () => {
    setLoading(true);
    try {
      const res = await api.get<PlantConfusionGroup[]>("/features/confusion-groups");
      setGroups(res.data);
      if (res.data.length > 0) {
        // Find if selectedGroup still exists in reload
        const current = selectedGroup ? res.data.find(x => x.id === selectedGroup.id) : null;
        setSelectedGroup(current || res.data[0]);
      } else {
        setSelectedGroup(null);
      }
    } catch (e) {
      message.error("加载易混淆专题失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGroups();
  }, []);

  // Search plants debounced
  useEffect(() => {
    if (!searchVal.trim()) {
      setSearchResults([]);
      return;
    }
    const t = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const res = await api.get("/plants", { params: { q: searchVal, page: 1, page_size: 15 } });
        setSearchResults(res.data.items || []);
      } catch (e) {
        message.error("搜索植物失败");
      } finally {
        setSearchLoading(false);
      }
    }, 400);
    return () => clearTimeout(t);
  }, [searchVal]);

  const handleAddPlantToForm = (plant: Plant) => {
    if (formItems.some(x => x.plant_id === plant.id)) {
      message.warning("该植物已添加");
      return;
    }
    setFormItems([...formItems, {
      plant_id: plant.id,
      distinguish_point: "",
      label: `${plant.vernacular_name} (${plant.scientific_name})`
    }]);
    setSearchVal("");
    setSearchResults([]);
  };

  const handleRemovePlantFromForm = (plantId: number) => {
    setFormItems(formItems.filter(x => x.plant_id !== plantId));
  };

  const handleSaveGroup = async () => {
    try {
      const values = await form.validateFields();
      if (formItems.length < 2) {
        message.error("对比专题至少需要包含 2 个植物");
        return;
      }
      const payload = {
        group_name: values.group_name,
        description: values.description,
        items: formItems.map(item => ({
          plant_id: item.plant_id,
          distinguish_point: item.distinguish_point
        }))
      };

      if (editingGroup?.id) {
        await api.put(`/features/confusion-groups/${editingGroup.id}`, payload);
        message.success("修改成功");
      } else {
        await api.post("/features/confusion-groups", payload);
        message.success("创建成功");
      }
      setModalOpen(false);
      loadGroups();
    } catch (e: any) {
      message.error(e.response?.data?.detail || "保存失败");
    }
  };

  const handleEditGroupClick = (group: PlantConfusionGroup) => {
    setEditingGroup(group);
    form.setFieldsValue({
      group_name: group.group_name,
      description: group.description
    });
    setFormItems(group.items.map(it => ({
      plant_id: it.plant_id,
      distinguish_point: it.distinguish_point || "",
      label: `${it.plant?.vernacular_name || "未知植物"} (${it.plant?.scientific_name || ""})`
    })));
    setModalOpen(true);
  };

  const handleDeleteGroup = async (groupId: number) => {
    try {
      await api.delete(`/features/confusion-groups/${groupId}`);
      message.success("删除成功");
      loadGroups();
    } catch (e: any) {
      message.error("删除失败");
    }
  };

  return (
    <div className="pt-2">
      <Row gutter={24}>
        {/* Left Side: Topic list */}
        <Col xs={24} md={7} lg={6}>
          <Card
            title="混淆专题"
            extra={
              isAdmin && (
                <Button
                  type="primary"
                  size="small"
                  className="flex items-center gap-0.5 rounded-lg text-xs"
                  onClick={() => {
                    setEditingGroup(null);
                    form.resetFields();
                    setFormItems([]);
                    setModalOpen(true);
                  }}
                >
                  <span className="material-symbols-outlined text-[14px]">add</span>
                  创建专题
                </Button>
              )
            }
            className="rounded-2xl border border-outline-variant/30 shadow-sm"
          >
            <Spin spinning={loading}>
              {groups.length === 0 ? (
                <Empty description="暂无易混淆专题" />
              ) : (
                <div className="space-y-2">
                  {groups.map((g) => {
                    const isSelected = selectedGroup?.id === g.id;
                    return (
                      <div
                        key={g.id}
                        onClick={() => setSelectedGroup(g)}
                        className={`p-3 rounded-xl border cursor-pointer transition-all ${
                          isSelected
                            ? "bg-primary/5 border-primary shadow-sm"
                            : "bg-surface border-outline-variant/30 hover:bg-surface-container-low"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-sm text-on-surface truncate pr-2">
                            {g.group_name}
                          </span>
                          <Tag className="rounded-md">{g.items?.length || 0} 株比对</Tag>
                        </div>
                        <p className="text-xs text-on-surface-variant mt-1.5 line-clamp-2">
                          {g.description || "暂无描述"}
                        </p>
                        
                        {isAdmin && isSelected && (
                          <div className="mt-2 flex items-center justify-end gap-2 border-t border-outline-variant/20 pt-2">
                            <Button
                              size="small"
                              type="text"
                              className="text-xs text-primary flex items-center gap-0.5"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleEditGroupClick(g);
                              }}
                            >
                              <span className="material-symbols-outlined text-[13px]">edit</span>
                              编辑
                            </Button>
                            <Popconfirm
                              title="确定要删除这个对比专题吗？"
                              onConfirm={(e) => {
                                e?.stopPropagation();
                                handleDeleteGroup(g.id!);
                              }}
                              onCancel={e => e?.stopPropagation()}
                            >
                              <Button
                                size="small"
                                type="text"
                                danger
                                className="text-xs flex items-center gap-0.5"
                                onClick={e => e.stopPropagation()}
                              >
                                <span className="material-symbols-outlined text-[13px]">delete</span>
                                删除
                              </Button>
                            </Popconfirm>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </Spin>
          </Card>
        </Col>

        {/* Right Side: Side-by-side Grid Compare */}
        <Col xs={24} md={17} lg={18}>
          {selectedGroup ? (
            <Card
              title={
                <div>
                  <h2 className="text-lg font-bold text-primary flex items-center gap-2">
                    <span className="material-symbols-outlined text-[22px]">compare_arrows</span>
                    专题对比：{selectedGroup.group_name}
                  </h2>
                  <p className="text-xs font-normal text-on-surface-variant mt-1">
                    {selectedGroup.description || "暂无专题详细说明。"}
                  </p>
                </div>
              }
              className="rounded-2xl border border-outline-variant/30 shadow-sm"
            >
              <div className="overflow-x-auto">
                <Row gutter={16} wrap={false} className="min-w-[680px]">
                  {selectedGroup.items.map((item) => {
                    const plant = item.plant;
                    if (!plant) return null;

                    return (
                      <Col span={24 / Math.max(selectedGroup.items.length, 1)} key={item.id}>
                        <div className="border border-outline-variant/30 rounded-2xl p-4 bg-surface-container-lowest h-full flex flex-col space-y-4">
                          {/* Image */}
                          <div className="flex justify-center bg-surface-container rounded-xl p-2 h-[180px]">
                            <img
                              src={plant.image_url || ""}
                              alt={plant.vernacular_name || ""}
                              className="max-h-full rounded-lg object-contain"
                              onError={(e) => {
                                (e.target as HTMLImageElement).src =
                                  "https://placehold.co/300x200?text=" + encodeURIComponent(plant.vernacular_name || "无图");
                              }}
                            />
                          </div>

                          {/* Titles */}
                          <div>
                            <h3 className="text-base font-bold text-primary flex items-baseline gap-1.5 flex-wrap">
                              <a onClick={() => showPlantDetail(plant.id)} className="hover:underline">
                                {plant.vernacular_name}
                              </a>
                              <span className="text-xs italic text-on-surface-variant font-normal">
                                {plant.scientific_name}
                              </span>
                            </h3>
                            <div className="text-xs text-on-surface-variant font-semibold mt-1">
                              {plant.family}科 · {plant.genus}属
                            </div>
                          </div>

                          {/* Distinguish Point Box */}
                          <div className="rounded-xl bg-amber-50 border border-amber-200/60 p-3.5">
                            <div className="flex items-center gap-1 text-xs font-bold text-amber-800 mb-1">
                              <span className="material-symbols-outlined text-[15px]">tips_and_updates</span>
                              辨析要点
                            </div>
                            <p className="text-xs text-amber-900 leading-relaxed">
                              {item.distinguish_point || "暂无辨析要点"}
                            </p>
                          </div>

                          {/* Morphology Brief */}
                          <div>
                            <div className="text-xs font-semibold text-primary mb-1">形态描述</div>
                            <p className="text-xs text-on-surface-variant leading-relaxed line-clamp-4" title={plant.morphology_text || ""}>
                              {plant.morphology_text || "无记录"}
                            </p>
                          </div>

                          {/* Medicinal Brief */}
                          <div>
                            <div className="text-xs font-semibold text-primary mb-1">药用与采收</div>
                            <p className="text-xs text-on-surface-variant leading-relaxed line-clamp-3" title={plant.medicinal_shape || ""}>
                              {plant.medicinal_shape || "无记录"}
                            </p>
                            {plant.harvest_months && (
                              <div className="mt-2 flex items-center gap-1">
                                <span className="text-[10px] text-on-surface-variant">采收月份：</span>
                                <Tag color="green" className="scale-90 origin-left">{plant.harvest_months}月</Tag>
                              </div>
                            )}
                          </div>
                        </div>
                      </Col>
                    );
                  })}
                </Row>
              </div>
            </Card>
          ) : (
            <Empty description="请在左侧选择或创建一个易混淆对比专题" />
          )}
        </Col>
      </Row>

      {/* CRUD MODAL */}
      <Modal
        title={editingGroup ? "编辑对比专题" : "创建对比专题"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSaveGroup}
        width={700}
        destroyOnClose
      >
        <Form form={form} layout="vertical" className="mt-4">
          <Form.Item
            name="group_name"
            label="专题名称"
            rules={[{ required: true, message: "请输入专题名称，如：五种胡" }]}
          >
            <Input placeholder="例如：五种胡、三七与人参辨析" />
          </Form.Item>
          
          <Form.Item name="description" label="专题描述">
            <TextArea rows={2} placeholder="简单描述这个对比专题，说明它们的相似性或辨析目的" />
          </Form.Item>
          
          <Divider>对比植物成员配置</Divider>

          {/* Plant Searcher */}
          <div className="mb-4 space-y-2">
            <label className="text-xs font-semibold text-on-surface-variant block">搜索并添加植物</label>
            <div className="relative">
              <Input
                placeholder="键入植物中文名称或学名进行模糊搜索"
                value={searchVal}
                onChange={(e) => setSearchVal(e.target.value)}
                prefix={<span className="material-symbols-outlined text-[18px] text-primary/60">search</span>}
              />
              
              {searchLoading && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <Spin size="small" />
                </div>
              )}

              {searchResults.length > 0 && (
                <div className="absolute left-0 right-0 top-full mt-1 bg-white border border-outline-variant/30 rounded-xl shadow-lg z-50 max-h-[220px] overflow-y-auto">
                  {searchResults.map((plant) => (
                    <div
                      key={plant.id}
                      onClick={() => handleAddPlantToForm(plant)}
                      className="p-3 hover:bg-surface-container-low cursor-pointer flex items-center justify-between border-b border-outline-variant/10 text-sm"
                    >
                      <div>
                        <span className="font-semibold text-primary">{plant.vernacular_name}</span>
                        <span className="text-xs italic text-on-surface-variant ml-2">{plant.scientific_name}</span>
                      </div>
                      <Tag color="blue">{plant.family} · {plant.genus}</Tag>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Added plants list */}
          <div className="space-y-4 max-h-[280px] overflow-y-auto pr-1">
            {formItems.length === 0 ? (
              <div className="text-xs text-on-surface-variant text-center py-4 bg-surface-container-low rounded-xl border border-dashed border-outline-variant/50">
                尚未添加对比植物，请使用上方搜索框添加至少 2 株植物。
              </div>
            ) : (
              formItems.map((item, idx) => (
                <div key={item.plant_id} className="p-3 rounded-xl border border-outline-variant/30 bg-surface-container-low/50 relative">
                  <div className="flex items-center justify-between mb-2 pr-6">
                    <span className="font-semibold text-sm text-primary">成员 {idx + 1}: {item.label}</span>
                    <Button
                      size="small"
                      type="text"
                      danger
                      onClick={() => handleRemovePlantFromForm(item.plant_id)}
                      className="flex items-center justify-center p-1 absolute right-2 top-2"
                      title="移除"
                    >
                      <span className="material-symbols-outlined text-[18px]">delete</span>
                    </Button>
                  </div>
                  <Form.Item label="辨析要点 (说明该物种与同组其他物种的主要形态区别)" required className="mb-0">
                    <TextArea
                      rows={2}
                      value={item.distinguish_point}
                      onChange={(e) => {
                        const updated = [...formItems];
                        updated[idx].distinguish_point = e.target.value;
                        setFormItems(updated);
                      }}
                      placeholder="例如：根部较粗，花期基生叶已完全展开，花瓣多呈淡紫色，与重叶莲主要区别在于..."
                    />
                  </Form.Item>
                </div>
              ))
            )}
          </div>
        </Form>
      </Modal>
    </div>
  );
}
