---
name: tutorial-video-workflow
description: Orchestrate editable tutorial-video production from segmented narration, product screen recordings, talking-head footage, and B-roll. Use when Codex must create or resume a tutorial/product-demo edit, clean speech, align screen recordings, generate captions or visual assets, deliver a verified editable JianYing/CapCut draft before optional OpenChatCut refinement, or synchronize reviewed OpenChatCut changes back into a new JianYing draft version.
---

# Tutorial Video Workflow

把 `video-editing`、`design-style`、`imagegen`、OpenChatCut 和剪映组织成一条可恢复的流程。始终把可编辑剪映工程作为核心交付，把 OpenChatCut 作为可视化精剪补充。

## 核心约束

1. 保持原素材只读；只在项目目录内创建派生文件。
2. 先生成并验证剪映 V1，再开始 OpenChatCut 交接。
3. 不因 OpenChatCut 不可用或回写失败而阻塞剪映 V1。
4. 保持字幕为可编辑文本，尽量保持视频、音频、录屏和画中画分轨。
5. 只烘焙剪映无法稳定表达的复杂 Remotion 动效，并将每个烘焙结果作为独立素材交付。
6. 不覆盖已验证版本；使用 `capcut_v1_rough_cut`、`capcut_v2_refined` 等递增目录。
7. 把内容判断交给 Codex，把文件结构、环境检查和草稿静态检查交给本 Skill 的脚本。

## 启动流程

在运行任何 Python 脚本前，先用当前系统的原生命令检查 Python 3。POSIX 系统优先运行不依赖 Python 的启动器：

```bash
scripts/bootstrap.sh --project <项目目录>
```

Windows PowerShell 先运行 `Get-Command python -ErrorAction SilentlyContinue` 和 `python --version`。不要在 Python 缺失时尝试运行 `preflight.py`。

如果缺少 Python 3，读取 [references/dependency-bootstrap.md](references/dependency-bootstrap.md)，说明用途和安装范围，向用户申请许可，再使用当前系统可用的软件包管理器安装。安装后验证版本并重新运行启动器；不要让用户自己复制多条安装命令。

Python 可用后运行：

```bash
python3 scripts/init_project.py --source <素材目录> --project <项目目录>
```

如果启动器选择的是 `python` 而不是 `python3`，后续使用同一解释器。读取生成的 `workflow/project.json` 和 `workflow/preflight.json`。不要因为缺少高级依赖而停止基础粗剪：

- 基础粗剪需要 Python、FFmpeg/ffprobe、Whisper 能力和 `video-editing` Skill。
- 复杂动效才需要 Node.js、Remotion 和 Chromium。
- OpenChatCut 仅在可用时启用；剪映 V1 不依赖它。
- 缺少 Skill 时，说明缺失项并在用户要求安装后使用 `skill-installer`。
- 不静默安装或升级系统软件；尽量把必需项汇总为一次许可请求。

## 阶段一：自动粗剪

读取已安装 `video-editing` Skill 的当前说明，不复制或猜测其命令。按以下顺序复用其能力：

1. 盘点分段口播、录屏、真人视频和补充画面。
2. 转写口播并保留词级时间戳。
3. 提议删除停顿、卡壳、重复表达；涉及语义删除时先让用户确认。
4. 以清理后的口播时间线为主轴匹配录屏。
5. 对录屏匹配记录来源片段、源入点、源出点、目标区间、速度和置信度。
6. 只自动接受高置信度匹配；集中展示低置信度匹配供用户确认。
7. 生成可编辑字幕、真人画中画和分离的补充画面轨道。
8. 需要开场、痛点画面或封面时使用 `design-style` 确定视觉方向，再使用 `imagegen` 生成必要素材。

把关键决定持续写入 `workflow/project.json`，不要只留在对话里。详细交付契约见 [references/workflow-contract.md](references/workflow-contract.md)。

## 阶段二：剪映 V1 门禁

使用 `video-editing` Skill 当前提供的剪映导出器生成 `deliverables/capcut_v1_rough_cut/`，然后运行：

```bash
python3 scripts/validate_capcut_draft.py \
  deliverables/capcut_v1_rough_cut \
  --report workflow/capcut_v1_validation.json
```

静态检查通过后，要求用户在目标剪映版本中实际打开工程。只有用户确认以下项目后，才把 V1 标记为 `verified`：

- 草稿出现在剪映项目列表并可打开；
- 素材没有丢失，时长和顺序正确；
- 字幕可以逐条修改；
- 录屏、真人画中画、音频和补充画面保持合理分轨；
- 切点、变速和同步关系正确；
- 工程可以保存、关闭并重新打开。

静态验证不等于剪映兼容性验证。不要声称未实际打开的工程“已通过”。

## 阶段三：OpenChatCut 精剪补充

仅在剪映 V1 已生成后启用。读取 [references/openchatcut-handoff.md](references/openchatcut-handoff.md)，再执行交接。

优先通过 OpenChatCut MCP 创建隔离编辑会话，以手动审批模式提交修改。让用户在工作台中预览、调整、撤销或批准。把每次批准后的操作摘要写入 `workflow/openchatcut_changes.json`。

不要让 OpenChatCut 成为唯一项目副本。保留：

- 已验证剪映 V1；
- OpenChatCut 项目导出；
- 修改操作记录；
- 审片 MP4。

## 阶段四：回到剪映

如果存在可靠的 OpenChatCut → 剪映转换器，生成 `capcut_v2_refined` 并重复完整剪映门禁。

如果不存在或转换失败：

1. 保留可用的剪映 V1，不修改或覆盖它。
2. 从 `openchatcut_changes.json` 中提取剪切、移动、字幕、音量、画中画和素材替换操作。
3. 将可表达的操作重新应用到统一剪辑配置。
4. 重新导出剪映 V2 并验证。
5. 将无法转换的操作写成带时间码的人工精剪清单。

## 完成条件

仅在以下条件满足时报告完成：

- 至少存在一个静态检查通过的剪映草稿版本；
- 用户已被明确要求在剪映中实际打开验证；
- 原素材未被修改；
- 所有烘焙素材独立可替换；
- OpenChatCut 失败不会破坏剪映保底版本；
- 项目状态足以让下一次 Codex 会话继续执行。
