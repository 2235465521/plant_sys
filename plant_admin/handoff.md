# Handoff: Plant Admin System (`plant_sys`)

## Project Context
`plant_sys` is a Plant Administration and Semantic Video Studio web application with a FastAPI backend and Vite/React frontend. Recent work focused on implementing the Semantic AI Video Studio, refining video layouts/transitions, and diagnosing & fixing critical deployment/rendering bugs.

## What Was Accomplished in This Session
1. **Semantic AI Video Studio & Dual-Mode Generation**:
   - Implemented dual-mode video generation: single-plant overview vs. multi-plant top-N collection videos.
   - Added asynchronous task queue (`POST /api/video-automation/semantic-generate` and `GET /api/video-automation/task-status/{task_id}`).
   - Integrated Pro model toggle: switch between `deepseek-v4-flash` (Flash) and `deepseek-reasoner` (Pro).
   - Created title curtain (3s), condensed chapter slides with `NO.01/08` badges, and outro curtain (3s).

2. **Video Layout & Transition Enhancements**:
   - Photo card dimensions standardized to **880x680** with double antique borders.
   - Lowered photo position (`y=360`) to leave clear breathing room for top titles.
   - Smart cover/fill cropping algorithm for vertical images to eliminate whitespace gaps on sides.
   - Extended page-flip transition duration to **1.6s (48 frames)** with a cubic ease-in-out S-curve for physical page inertia and 3D lighting/shadows.

3. **Critical Bug Fixes (Diagnosed via `/diagnosing-bugs`)**:
   - **Zero Plant Match for Conversational Prompts**: Added `clean_search_keywords` stop-word filtering and a robust multi-stage fallback search in `search_plants_for_video` so conversational prompts (e.g., "做一条关于十大中药植物介绍视频") always match plants reliably.
   - **Server White Screen (`text/html` MIME error)**: Resolved missing JS bundle issue on deployment server by committing built assets and documenting server recovery commands.
   - **Linux Tofu Square / `XXXX` Font Render Bug**: Updated `get_system_font` in `frame_renderer.py` to prioritize repo-bundled TrueType fonts (`data/video_assets/fonts/1.ttf` and `2.ttf`), eliminating tofu square rendering on Linux servers.
   - **Missing Plant Photo Cards (Blank Center)**: Updated `resolve_local_img_path` to map Web API URLs (`/api/media/plants/...`) to physical disk paths (`data/plant_images/...`).

4. **Modern Trivia Video Pipeline (对标《老王聊草本》1:1 风格复刻 & 严格 20 秒压缩)**:
   - 完成标杆参考视频《天葵》的逐帧反编译分析与设计质询（`/grill-with-docs` 全部分支对齐）。
   - 创建 [`docs/adr/0002-modern-trivia-video-style-pipeline.md`](file:///e:/plant_admin/plant_admin/docs/adr/0002-modern-trivia-video-style-pipeline.md) 固化架构决策。
   - 实现了 [`backend/app/video_automation/trivia_script.py`](file:///e:/plant_admin/plant_admin/backend/app/video_automation/trivia_script.py)：DeepSeek 4 幕趣味科普脚本结构化提炼器 + 离线原生数据库字段平滑降级（各字段严格压缩至 12~16 字以内）。
   - 实现了 [`backend/app/video_automation/trivia_renderer.py`](file:///e:/plant_admin/plant_admin/backend/app/video_automation/trivia_renderer.py)：1080x1920 冷白天蓝光斑底图、祥云抱字大标牌、白瓷花瓣药材盘抠图、带声调拼音光晕、透视星轨环与亮黄黑描边短视频正文。
   - 实现了 [`backend/app/video_automation/trivia_compiler.py`](file:///e:/plant_admin/plant_admin/backend/app/video_automation/trivia_compiler.py)：
     - **20.0 秒精准时长预算引擎**：30 FPS 下锁定 600 帧（4 次转场 60 帧 + 5 幕静态 540 帧）。
     - Edge-TTS 阳光科普男声配音合成（+30% 紧凑快节奏语速，带 3 次重试机制）。
     - 丝滑卡片缩放与交叉淡入淡出（Smooth Scale & Cross-Fade）彻底解决暗角黑块。
     - FFmpeg 精准时间戳双轨混音：人声 100%、轻柔 BGM 22% 并在第 19~20 秒柔和淡出。
   - 路由与前端集成：在 `main_router.py` 挂载 `modern_trivia` 预设，在 `FeaturesPage.tsx` 中设为默认风格并增添一键灵感标签。
   - 成功生成测试样片 `backend/data/test_tiankui_trivia.mp4`，时长精准锁定为 **00:00:20.00**，音画完全同步、视觉效果细腻。

## Key Files & ADRs
- [`CONTEXT.md`](file:///e:/plant_admin/plant_admin/CONTEXT.md): Ubiquitous domain terminology and module responsibilities.
- [`docs/adr/0001-semantic-multi-plant-video-generation.md`](file:///e:/plant_admin/plant_admin/docs/adr/0001-semantic-multi-plant-video-generation.md): ADR for semantic video generation.
- [`docs/adr/0002-modern-trivia-video-style-pipeline.md`](file:///e:/plant_admin/plant_admin/docs/adr/0002-modern-trivia-video-style-pipeline.md): ADR for modern trivia video pipeline.
- [`backend/app/video_automation/trivia_script.py`](file:///e:/plant_admin/plant_admin/backend/app/video_automation/trivia_script.py): Trivia script generator with fallback.
- [`backend/app/video_automation/trivia_renderer.py`](file:///e:/plant_admin/plant_admin/backend/app/video_automation/trivia_renderer.py): Visual slide card compositor.
- [`backend/app/video_automation/trivia_compiler.py`](file:///e:/plant_admin/plant_admin/backend/app/video_automation/trivia_compiler.py): Edge-TTS + FFmpeg dual-audio compiler.
- [`backend/app/video_automation/main_router.py`](file:///e:/plant_admin/plant_admin/backend/app/video_automation/main_router.py): Video automation endpoints and task queue.
- [`frontend/src/pages/FeaturesPage.tsx`](file:///e:/plant_admin/plant_admin/frontend/src/pages/FeaturesPage.tsx): AI Video Studio UI with style selector.

## Current State & Next Steps
- Backend server is running locally on port `8002`.
- Frontend server is running locally on port `5174`.
- **Server Deployment Instructions**:
  On the live server (`47.106.104.48`), run:
  ```bash
  cd /path/to/plant_admin
  git checkout -- .
  git pull origin main
  pm2 restart plant-frontend
  pm2 restart plant-backend
  ```
- **Next Session Focus**:
  - Verify live server deployment and test video generation on production.
  - Review generated video results with user feedback.

*Note: No sensitive API keys or credentials have been included.*

