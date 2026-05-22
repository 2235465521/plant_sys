import axios from "axios";

const TOKEN_KEY = "plant_admin_token";

export const api = axios.create({
  baseURL: "/api",
});

/** FastAPI list[str]：使用重复键，如 division=a&division=b */
export function serializeTaxonArrayParams(params: Record<string, unknown>): string {
  const u = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      for (const item of value) {
        const s = String(item).trim();
        if (s) u.append(key, s);
      }
      continue;
    }
    if (value === "") continue;
    u.append(key, String(value));
  }
  return u.toString();
}

api.interceptors.request.use((config) => {
  const t = localStorage.getItem(TOKEN_KEY);
  if (t) {
    config.headers.Authorization = `Bearer ${t}`;
  }
  return config;
});

export function setToken(t: string | null) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export type Role = "admin" | "user";

export interface LoginRes {
  access_token: string;
  token_type: string;
  role: Role;
  username: string;
}

export interface RegisterStatus {
  enabled: boolean;
  allow_admin: boolean;
}

export interface Plant {
  id: number;
  division: string | null;
  subclass: string | null;
  taxonomic_order: string | null;
  family: string | null;
  genus: string | null;
  vernacular_name: string | null;
  alternative_names_zh: string | null;
  scientific_name: string | null;
  taxonomic_provenance: string | null;
  synonyms: string | null;
  morphology_text: string | null;
  medicinal_shape: string | null;
  distribution_china: string | null;
  distribution_abroad: string | null;
  habitat: string | null;
  is_medicinal_food_homologous: string | null;
  image_url: string | null;
  /** 本站多图 URL 路径（与库中 JSON 数组一致） */
  image_server_paths: string[] | null;
}

export interface ExportLog {
  id: number;
  plant_id: number | null;
  plant_name: string | null;
  user_id: number;
  username: string;
  user_role: "admin" | "user" | null;
  export_format: string;
  created_at: string;
}

/** 主内容区「筛选」按钮触发，左侧分类栏短暂高亮 */
export const PLANT_SIDEBAR_FLASH_EVENT = "plant-focus-filter-sidebar";
