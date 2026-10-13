import React from "react";
import { Slider, Radio, Space, Tag, Tooltip } from "antd";
import { TypographyConfig, DEFAULT_TYPOGRAPHY_CONFIG } from "../api";

interface TypographyStyleEditorProps {
  value: TypographyConfig;
  onChange: (val: TypographyConfig) => void;
  compact?: boolean;
}

const PRESET_TIAN: TypographyConfig = { ...DEFAULT_TYPOGRAPHY_CONFIG };

const PRESET_UPRIGHT: TypographyConfig = {
  slant_deg: 0,
  fill_hex: "#FFFFFF",
  outline_hex: "#101010",
  outline_width: 4,
  font_preset: "kaiti",
};

const PRESET_MODERN: TypographyConfig = {
  slant_deg: -5,
  fill_hex: "#FFD166",
  outline_hex: "#073B4C",
  outline_width: 3,
  font_preset: "sans",
};

const COMMON_FILL_COLORS = [
  { name: "爆款亮黄", color: "#FFEE14" },
  { name: "素雅纯白", color: "#FFFFFF" },
  { name: "琥珀金黄", color: "#FFB703" },
  { name: "古风朱红", color: "#EB2D37" },
  { name: "青翠碧绿", color: "#52C41A" },
];

const COMMON_OUTLINE_COLORS = [
  { name: "深褐黑", color: "#140F05" },
  { name: "纯黑", color: "#000000" },
  { name: "暗夜蓝", color: "#0A192F" },
  { name: "赤红褐", color: "#2E0808" },
];

export const TypographyStyleEditor: React.FC<TypographyStyleEditorProps> = ({
  value,
  onChange,
  compact = false,
}) => {
  const isTian =
    value.slant_deg === PRESET_TIAN.slant_deg &&
    value.fill_hex.toUpperCase() === PRESET_TIAN.fill_hex.toUpperCase() &&
    value.font_preset === PRESET_TIAN.font_preset;

  const isUpright =
    value.slant_deg === PRESET_UPRIGHT.slant_deg &&
    value.fill_hex.toUpperCase() === PRESET_UPRIGHT.fill_hex.toUpperCase() &&
    value.font_preset === PRESET_UPRIGHT.font_preset;

  const isModern =
    value.slant_deg === PRESET_MODERN.slant_deg &&
    value.fill_hex.toUpperCase() === PRESET_MODERN.fill_hex.toUpperCase() &&
    value.font_preset === PRESET_MODERN.font_preset;

  return (
    <div className="space-y-4 text-xs">
      {/* 预设方案切换 */}
      <div>
        <div className="text-gray-300 font-semibold mb-2 flex items-center justify-between">
          <span>排版风格预设</span>
          <span className="text-[11px] text-amber-400 font-normal">
            当前倾斜: {value.slant_deg > 0 ? `+${value.slant_deg}°` : `${value.slant_deg}°`}
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onChange({ ...PRESET_TIAN })}
            className={`px-3 py-1.5 rounded-lg border text-xs transition-all flex items-center gap-1.5 ${
              isTian
                ? "bg-amber-500/20 border-amber-400 text-amber-300 font-bold shadow-sm"
                : "bg-white/5 border-white/10 text-gray-300 hover:border-white/30"
            }`}
          >
            <span>🌿</span> 爆款行楷 (-10°)
          </button>
          <button
            type="button"
            onClick={() => onChange({ ...PRESET_UPRIGHT })}
            className={`px-3 py-1.5 rounded-lg border text-xs transition-all flex items-center gap-1.5 ${
              isUpright
                ? "bg-blue-500/20 border-blue-400 text-blue-300 font-bold shadow-sm"
                : "bg-white/5 border-white/10 text-gray-300 hover:border-white/30"
            }`}
          >
            <span>📜</span> 端庄正楷 (0°)
          </button>
          <button
            type="button"
            onClick={() => onChange({ ...PRESET_MODERN })}
            className={`px-3 py-1.5 rounded-lg border text-xs transition-all flex items-center gap-1.5 ${
              isModern
                ? "bg-emerald-500/20 border-emerald-400 text-emerald-300 font-bold shadow-sm"
                : "bg-white/5 border-white/10 text-gray-300 hover:border-white/30"
            }`}
          >
            <span>⚡</span> 现代微倾 (-5°)
          </button>
        </div>
      </div>

      {/* 倾斜角度滑块 */}
      <div>
        <div className="flex justify-between text-gray-300 mb-1">
          <span>字体倾斜度 (Slant Angle)</span>
          <span className="font-mono text-amber-300">
            {value.slant_deg === 0
              ? "0° (直立)"
              : value.slant_deg < 0
              ? `${value.slant_deg}° (向右前倾)`
              : `+${value.slant_deg}° (向左后倾)`}
          </span>
        </div>
        <Slider
          min={-20}
          max={10}
          step={1}
          value={value.slant_deg}
          onChange={(v) => onChange({ ...value, slant_deg: Number(v) })}
          marks={{
            "-15": { style: { color: "#9ca3af", fontSize: "10px" }, label: "大倾斜" },
            "-10": { style: { color: "#fbbf24", fontSize: "10px", fontWeight: "bold" }, label: "-10°爆款" },
            "-5": { style: { color: "#9ca3af", fontSize: "10px" }, label: "-5°" },
            "0": { style: { color: "#60a5fa", fontSize: "10px" }, label: "0°直立" },
          }}
        />
      </div>

      {/* 字体颜色与描边色彩 */}
      <div className="grid grid-cols-2 gap-4 pt-1">
        <div>
          <label className="text-gray-300 block mb-1.5">字体填充色彩</label>
          <div className="flex items-center gap-1.5 mb-1.5">
            {COMMON_FILL_COLORS.map((c) => (
              <Tooltip key={c.color} title={c.name}>
                <button
                  type="button"
                  onClick={() => onChange({ ...value, fill_hex: c.color })}
                  className={`w-6 h-6 rounded-full border-2 transition-transform ${
                    value.fill_hex.toUpperCase() === c.color.toUpperCase()
                      ? "scale-110 border-white shadow-md ring-2 ring-amber-400"
                      : "border-transparent opacity-80 hover:opacity-100"
                  }`}
                  style={{ backgroundColor: c.color }}
                />
              </Tooltip>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={value.fill_hex}
              onChange={(e) => onChange({ ...value, fill_hex: e.target.value })}
              className="w-7 h-7 rounded border border-white/20 cursor-pointer bg-transparent"
            />
            <span className="font-mono text-[11px] text-gray-300">{value.fill_hex}</span>
          </div>
        </div>

        <div>
          <label className="text-gray-300 block mb-1.5">描边颜色与粗细</label>
          <div className="flex items-center gap-1.5 mb-1.5">
            {COMMON_OUTLINE_COLORS.map((c) => (
              <Tooltip key={c.color} title={c.name}>
                <button
                  type="button"
                  onClick={() => onChange({ ...value, outline_hex: c.color })}
                  className={`w-6 h-6 rounded-full border-2 transition-transform ${
                    value.outline_hex.toUpperCase() === c.color.toUpperCase()
                      ? "scale-110 border-white shadow-md ring-2 ring-amber-400"
                      : "border-transparent opacity-80 hover:opacity-100"
                  }`}
                  style={{ backgroundColor: c.color }}
                />
              </Tooltip>
            ))}
          </div>
          <div className="flex items-center gap-2 mb-2">
            <input
              type="color"
              value={value.outline_hex}
              onChange={(e) => onChange({ ...value, outline_hex: e.target.value })}
              className="w-7 h-7 rounded border border-white/20 cursor-pointer bg-transparent"
            />
            <span className="font-mono text-[11px] text-gray-300">{value.outline_hex}</span>
          </div>
          <div>
            <div className="flex justify-between items-center text-[11px] text-gray-300 mb-0.5">
              <span>描边粗细:</span>
              <span className="font-mono text-amber-300">{value.outline_width}px</span>
            </div>
            <Slider
              min={0}
              max={8}
              step={1}
              value={value.outline_width}
              onChange={(v) => onChange({ ...value, outline_width: Number(v) })}
              className="!my-1"
            />
          </div>
        </div>
      </div>

      {/* 字体形态选择 */}
      <div>
        <label className="text-gray-300 block mb-1.5">书法字体形态</label>
        <Radio.Group
          value={value.font_preset}
          onChange={(e) => onChange({ ...value, font_preset: e.target.value })}
          size="small"
          className="w-full flex gap-2"
        >
          <Radio.Button value="calligraphy" className="flex-1 text-center !bg-white/5 !border-white/10 !text-gray-300">
            行楷书法
          </Radio.Button>
          <Radio.Button value="kaiti" className="flex-1 text-center !bg-white/5 !border-white/10 !text-gray-300">
            端庄楷体
          </Radio.Button>
          <Radio.Button value="sans" className="flex-1 text-center !bg-white/5 !border-white/10 !text-gray-300">
            现代黑体
          </Radio.Button>
        </Radio.Group>
      </div>

      {/* 实时所见即所得 CSS 动态预览条 */}
      <div className="mt-3 p-3 bg-neutral-900/90 rounded-xl border border-white/10 shadow-inner overflow-hidden">
        <div className="text-[10px] text-gray-400 mb-1 flex items-center justify-between">
          <span>✨ 实时排版所见即所得预览 (Live CSS Preview)</span>
          <span className="text-amber-400 font-mono">
            skewX({value.slant_deg}deg)
          </span>
        </div>
        <div className="py-2 px-1 flex items-center justify-center bg-black/40 rounded-lg overflow-hidden">
          <span
            style={{
              ...getTypographyCss(value),
              fontWeight: "bold",
              fontSize: "17px",
              letterSpacing: "2px",
            }}
          >
            每日认识一种植物 · 药用价值与形态特征
          </span>
        </div>
      </div>
    </div>
  );
};

export function getTypographyCss(typography?: TypographyConfig): React.CSSProperties {
  const t = typography || DEFAULT_TYPOGRAPHY_CONFIG;
  return {
    transform: `skewX(${t.slant_deg}deg)`,
    color: t.fill_hex,
    textShadow:
      t.outline_width > 0
        ? `0 0 ${t.outline_width}px ${t.outline_hex}, 0 2px 4px rgba(0,0,0,0.8)`
        : "0 2px 4px rgba(0,0,0,0.8)",
    WebkitTextStroke:
      t.outline_width > 0
        ? `${Math.min(t.outline_width, 2)}px ${t.outline_hex}`
        : "none",
    fontFamily:
      t.font_preset === "calligraphy"
        ? '"STXingkai", "华文行楷", cursive'
        : t.font_preset === "kaiti"
        ? '"STKaiti", "楷体", serif'
        : 'system-ui, -apple-system, sans-serif',
    display: "inline-block",
    transition: "transform 0.15s ease-out, color 0.15s ease-out",
  };
}
