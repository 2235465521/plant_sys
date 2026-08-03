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
