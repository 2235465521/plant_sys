# Context & Domain Glossary (`plant_sys`)

## Domain Terms

### 语义视频生成 (Semantic Video Generation)
根据用户输入的自然语言提示词（Prompt），利用 LLM 意图解析从植物数据库中筛选符合条件的植物，并自动合成视频的过程。

### 视频形态 (Video Modes)
- **单植物视频 (Single-Plant Video)**：针对单一植物名称或精准匹配生成的 20 秒独立短视频。
- **多植物合集视频 (Multi-Plant Collection Video)**：针对排行榜、地域特征或专题类需求（如“十大中药植物”、“浙八味”）检索到的 Top-N 植物，按章节与过渡幕自动拼接合成的专题合集视频。

### 异步生成任务 (Async Video Generation Task)
处理长耗时视频合成的后台任务模型，具有唯一 `task_id`，包含实时状态（`queued` / `processing` / `completed` / `failed`）、百分比进度（`progress_percentage`）、当前执行步骤说明（`current_step`）及最终产出 URL（`result_video_url`）。

### 意图控制指令 (Intent Schema)
DeepSeek 结合自然语言 Prompt 解析输出的结构化 JSON 控制对象，包含 `mode`（单植物/多植物合集）、`target_count`（目标生成数量）、`style_preset`（风格预设）及语义筛选字段（`harvest_months`, `habitats`, `rankings`, `regions`, `keywords`）。

### 柔性降级策略 (Graceful Fallback Policy)
当数据库匹配到的植物数量多于 `target_count` 时，按语义打分由高到低截取；当少于 `target_count` 时，不中断报错，而是自动利用全部可用匹配项生成视频并附带提示说明；当匹配为 0 时返回友好的关键词修改建议。

### 合集视频结构 (Collection Video Pipeline)
由“主题片头（Opening Curtain） + N个精简植物章节段（Chapter Segments，带序号角标与核心性状） + 章节转场动效（Transitions） + 专题片尾（Outro Curtain） + 统一长轨BGM”构成的自动化拼接与音视频压制流水线。

### AI 视频创作工坊 (AI Video Studio Component)
前端交互界面组件，包含自然语言 Prompt 输入框、快捷灵感标签（如`[十大中药]`、`[浙八味]`）、异步进度抽屉及在线预览下载器。

### 视频风格预设 (Video Style Presets)
- **草本趣闻风 (Modern Trivia Style, `style_modern_trivia`)**：对标短视频爆款（如《老王聊草本》）的现代科普风格。特征为冷白天蓝光斑背景、祥云立体抱字标牌、亮黄黑边圆润短视频字幕、白瓷药材盘扣图、动态星轨光环以及“故事化/趣闻物候”解说结构。
- **古风宣纸百科风 (Vintage Encyclopedia Style, `style_vintage_encyclopedia`)**：传统典雅宣纸纹理背景，带双线古风方框、艺术行楷标题及系统化学术科属名片排版。

### 趣闻脚本提炼器 (Trivia Script Generator)
专为 `style_modern_trivia` 设计的文案生成组件。通过 LLM（DeepSeek）将数据库中的生硬植物学长文本自动提炼并结构化转化为 4 段适合短视频网感口吻的精炼脚本（包含 `cover_badge` 药用简述、`morphology` 通俗特征、`trivia` 趣闻物候典故、`habitat` 适生范围）；当模型超时或离线时，自动按预设规则截取数据库原生字段（如 `plant_aliases.origin_desc`、`habitats`）平滑降级，确保 100% 稳定出片。

### 趣闻视觉组件库 (Trivia Visual Assets Pipeline)
专用于草本趣闻风的视觉基础设施与图层合成管线：
- **画布背景 (`trivia_bg.png`)**：1080x1920 冷白天蓝微渐变与下半部柔和虚化散景光斑（Soft Bokeh）。
- **祥云标牌 (`cloud_banner.png`)**：双侧对称如意祥云立体托底底模，支持文字居中内嵌与橙金渐变描边。
- **白瓷药材盘 (`porcelain_dish.png`)**：花瓣弧形高光瓷盘透明图层，通过 Alpha 蒙版将植物入药部位图片智能嵌入盘中并叠加内凹阴影。
- **透视星轨环 (`orbit_ring.png`)**：带立体微透视倾角的蓝色荧光粒子星轨，环绕点缀在别名与科属文字背后。

### 语音自适应对齐管线 (TTS-Adaptive Sync Pipeline)
草本趣闻风的音视频协同压制模型：
- 使用 Edge-TTS（默认 `zh-CN-YunxiNeural` 阳光活泼科普男声，+30% 紧凑快节奏语速）为各章节生成分段语音，内置 3 次重试机制应对网络波动。
- 视频编译时以实际音频毫秒数动态推算各 Slide 的帧停留时长，确保“音画同步、读完即翻”。
- 卡片转场采用丝滑卡片缩放淡入淡出（Smooth Scale & Cross-Fade）无缝融合光斑背景。
- 最终压制时通过 FFmpeg 滤镜链自动将解说语音（100% 音量）与轻柔民乐 BGM（22% 底噪垫音）平滑混流，并在结尾 1 秒执行平滑淡出。

### 20秒精准时长预算模型 (20s Duration Budget Model)
为满足短视频平台（抖音、视频号、小红书）快节奏完播率要求，单植物视频总时长严格锁定在 **20.0 秒（30 FPS 共 600 帧）**：
1. **转场帧预算**：5 幕之间共 4 次转场，每次 15 帧（0.5s），合计占用 60 帧（2.0s）。
2. **静态帧预算**：总静态显示帧固定为 `600 - 60 = 540 帧`（18.0s）。
3. **文案字符密度**：各幕文案严格控制在 12~16 字以内，解说语音总长压缩至 15.0~16.5 秒。
4. **比例权重分配**：保底满足各幕配音所需停留帧后，将剩余静态帧按各幕语音时长加权比例分配，最后一幕补齐余数，确保全片总帧数 100% 锁定在 600 帧，成片精确对齐 20.00 秒。





