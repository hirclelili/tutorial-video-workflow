---
name: tutorial-video-workflow
description: Orchestrate a single editable video project from an arbitrary mixed folder of video, audio, image, subtitle, or existing project files. Use when Codex must first ask the user's goal, confirm one exact primary media file, choose a fitting workflow such as talking-head cleanup, tutorial, montage, interview, podcast, long-to-short, voice-over, or existing-project refinement, and deliver a verified editable JianYing/CapCut draft with optional OpenChatCut refinement.
---

# Editable Video Workflow

把 `video-editing`、`design-style`、`imagegen`、OpenChatCut 和剪映组织成一条可恢复的单视频流程。不要假设素材类型或目录结构；先确认用户目标和一个主处理对象，再选择流程。

## 核心约束

1. 保持原素材只读；只在项目目录内创建派生文件。
2. 先生成并验证剪映 V1，再开始 OpenChatCut 交接。
3. 不因 OpenChatCut 不可用或回写失败而阻塞剪映 V1。
4. 保持字幕为可编辑文本，尽量保持视频、音频、录屏和画中画分轨。
5. 只烘焙剪映无法稳定表达的复杂 Remotion 动效，并将每个烘焙结果作为独立素材交付。
6. 不覆盖已验证版本；使用 `capcut_v1_rough_cut`、`capcut_v2_refined` 等递增目录。
7. 把内容判断交给 Codex，把文件结构、环境检查和草稿静态检查交给本 Skill 的脚本。
8. 默认一次只处理一个主媒体文件并生成一条成片；其他文件必须经用户确认后才能作为辅助素材。
9. 不要求用户改名、分类、预剪或创建 `口播/录屏/真人出镜/补充素材` 等目录。
10. 每个适用阶段都生成可直接打开的预览；用户批准前不进入下一项会改变内容或时间线的阶段。

## 用户意图与主文件门禁

在安装依赖、创建项目、转写或剪辑前，只读扫描用户提供的位置，并完成以下门禁：

1. 列出检测到的媒体文件；有现成工具时显示时长和分辨率，没有时只显示路径和类型，不为此安装依赖。
2. 询问用户想做成什么视频，包括内容目标、平台或画幅、期望时长和最终交付形式；只询问会改变结果的必要信息。
3. 要求用户确认一个确切的主处理文件。不要把文件夹里的所有视频自动纳入处理范围。
4. 将其他文件列为可选辅助素材，只有用户明确确认后才使用。
5. 复述“主文件、目标、辅助素材、默认一条输出”，等待用户确认。

如果用户明确要求多个输出，为每个输出建立独立项目；不要在同一次默认流程中批量处理。没有确认主文件和目标时停止，不运行后续阶段。

## 自动选择流程

门禁通过后读取 [references/workflow-routing.md](references/workflow-routing.md)，根据用户目标和实际素材选择最小流程。教程只是其中一种路由，不是默认路由。告诉用户选择了什么流程及原因，然后继续；只有路线会显著改变内容时才再次请求确认。

## 阶段预览门禁

读取 [references/preview-gates.md](references/preview-gates.md)。为所选路线的每个适用阶段产出轻量、可直接打开的预览，并明确提供三个选择：通过、要求修改、停止。

至少覆盖以下适用阶段：

1. 内容与剪辑方案：素材范围、目标、结构和预计处理清单。
2. 文字或内容清理：可同步播放的转写校稿页，或带时间码的保留/删除建议。
3. 粗剪：低码率完整审片 MP4；必要时附时间线图、波形或切点对比。
4. 画面与视觉：录屏匹配表、分镜、关键帧、封面候选或带画中画/动效的代理视频。
5. 剪映 V1：与草稿时间线一致的审片代理、静态验证报告和剪映实际打开门禁。
6. OpenChatCut：使用手动审批会话，让用户在工作台内预览提案。
7. 剪映 V2：再次生成审片代理并重复草稿验证。

使用 `video-editing` Skill 已有的 `transcript_review.py`、`review_proxy.py`、`timeline_view.py`、`edit_compare.py` 或 `review_dashboard.py`，只调用当前阶段需要的工具。在 Codex App 中用可点击的绝对文件链接展示 HTML、报告和视频，并直接渲染适合内联查看的图片或媒体；不要只报告文件路径。

用户要求修改时生成 `v2`、`v3` 等新预览，不覆盖已审阅版本。用户做出决定后运行：

```bash
python3 scripts/record_review.py \
  --project <项目目录> \
  --stage <阶段> \
  --status approved|changes_requested|skipped \
  --preview <预览文件> \
  --note "<用户反馈或跳过原因>"
```

阶段不适用时标记 `skipped` 并记录原因。适用阶段没有 `approved` 时不得宣称项目完成。

## 环境启动

仅在用户意图与主文件门禁通过后检查环境。在运行任何 Python 脚本前，先用当前系统的原生命令检查 Python 3。POSIX 系统优先运行不依赖 Python 的启动器：

```bash
scripts/bootstrap.sh --project <项目目录>
```

Windows PowerShell 先运行 `Get-Command python -ErrorAction SilentlyContinue` 和 `python --version`。不要在 Python 缺失时尝试运行 `preflight.py`。

如果缺少 Python 3，读取 [references/dependency-bootstrap.md](references/dependency-bootstrap.md)，说明用途和安装范围，向用户申请许可，再使用当前系统可用的软件包管理器安装。安装后验证版本并重新运行启动器；不要让用户自己复制多条安装命令。

Python 可用后运行：

```bash
python3 scripts/init_project.py \
  --source <素材目录> \
  --project <项目目录> \
  --goal "<用户确认的目标>" \
  --primary <用户确认的主文件> \
  --supporting <经确认的辅助素材>
```

如果启动器选择的是 `python` 而不是 `python3`，后续使用同一解释器。读取生成的 `workflow/project.json` 和 `workflow/preflight.json`。不要因为缺少高级依赖而停止基础粗剪：

- 基础粗剪需要 Python、FFmpeg/ffprobe、Whisper 能力和 `video-editing` Skill。
- 复杂动效才需要 Node.js、Remotion 和 Chromium。
- OpenChatCut 仅在可用时启用；剪映 V1 不依赖它。
- 缺少 Skill 时，说明缺失项并在用户要求安装后使用 `skill-installer`。
- 不静默安装或升级系统软件；尽量把必需项汇总为一次许可请求。

## 阶段一：执行所选流程

读取已安装 `video-editing` Skill 的当前说明，不复制或猜测其命令。只运行所选路线需要的能力，不机械执行完整教程流程。

当路线包含口播或对话时才转写并处理停顿、卡壳或重复表达；涉及语义删除时先让用户确认。当路线包含录屏匹配时才记录来源片段、目标区间、速度和置信度。需要视觉素材时才使用 `design-style` 和 `imagegen`。

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

在要求用户打开剪映前，先提供与 V1 时间线一致的低码率审片代理。代理通过不等于草稿兼容性通过，两项都要记录。

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
- 所有适用的阶段预览均已由用户批准，不适用阶段已记录跳过原因。
