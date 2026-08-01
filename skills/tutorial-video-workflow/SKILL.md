---
name: tutorial-video-workflow
description: Orchestrate one editable video from arbitrary local media. Use when Codex must confirm the user's goal and one primary file, create an automatic rough cut, open a bundled browser workbench for manual rough cutting and word-level fine cutting, preserve separate basic video/audio/caption tracks, export a review video, and optionally deliver a self-contained editable JianYing/CapCut project package.
---

# Editable Video Workflow

把自动粗剪、Skill 内置工作台、审片导出和可选剪映工程组织成一条可恢复的单视频流程。不要假设素材类型或目录结构；先确认用户目标和一个主处理对象，再选择流程。

## 核心约束

1. 保持原素材只读；只在项目目录内创建派生文件。
2. 默认先自动粗剪，再让用户在内置工作台完成手动粗剪和逐字精剪。
3. 不要求安装 OpenChatCut。仅当用户主动要求高级外部工作台时，把它作为可选交接。
4. 保持字幕为可编辑文本，尽量保持视频、音频、录屏和画中画分轨。
5. 默认不制作复杂动效、调色、花字、关键帧或高级混音；将这些留给最终剪映精剪。
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
5. 内置工作台：用户完成手动粗剪、逐字精剪并确认当前时间线。
6. 剪映 V1：与草稿时间线一致的审片代理、结构验证报告和剪映实际打开门禁。
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
- 内置工作台不依赖 Node.js、Remotion、Chromium 或 OpenChatCut；使用 Python 本地服务和用户已有浏览器。
- 缺少 Skill 时，说明缺失项并在用户要求安装后使用 `skill-installer`。
- 不静默安装或升级系统软件；尽量把必需项汇总为一次许可请求。

## 阶段一：自动粗剪

读取已安装 `video-editing` Skill 的当前说明，不复制或猜测其命令。只运行所选路线需要的能力，不机械执行完整教程流程。

当路线包含口播或对话时才转写并处理停顿、卡壳或重复表达；涉及语义删除时先让用户确认。当路线包含录屏匹配时才记录来源片段、目标区间、速度和置信度。需要视觉素材时才使用 `design-style` 和 `imagegen`。

直接完成自动粗剪，不把检测结果做成工作台中的“建议”列表。把自动删除范围保存为 JSON 切除清单；打开工作台时通过 `--auto-cut-list` 载入，让用户看到的起点就是已经粗剪后的版本。语义不确定、可能改变原意的删除仍须先向用户确认。

把关键决定持续写入 `workflow/project.json`，不要只留在对话里。详细交付契约见 [references/workflow-contract.md](references/workflow-contract.md)。

## 阶段二：内置粗剪与逐字精剪工作台

读取 [references/builtin-workbench.md](references/builtin-workbench.md)。有逐字稿后创建工作台项目：

```bash
python3 scripts/create_workbench_project.py \
  --project <项目目录> \
  --media <主视频> \
  --media <经用户确认的其他视频，可重复> \
  --transcript <带字级时间戳的转写 JSON> \
  --auto-cut-list <可选，阶段一已经执行的自动粗剪 JSON> \
  --title "<项目标题>"
```

再启动固定工作台：

```bash
python3 scripts/workbench_server.py --project <项目目录> --port 8765 --open
```

工作台必须区分素材池和主时间线：多段视频先进入素材池，只有用户或已确认的自动粗剪结果明确选择后才加入成片。提供独立的“逐句粗剪”面板，每句话都能播放、删除和恢复；再提供逐字精剪。还要支持片段删除与恢复、播放位置拆分、按真实时长比例显示和拖动排序、字幕修改、基础视频/音频/字幕分轨、撤销、重做、自动保存、审片视频导出和剪映工程导出入口。初始视频和音频保持连续，不得为了显示每句话而预先切碎；逐句删除只记录非破坏性排除范围，导出时才形成真实媒体切点。所有操作写入 `workbench/project.json`；原素材保持只读。

用户点击“确认当前剪辑”后，读取最新工作台时间线并生成后续统一时间线。工作台状态未确认为 `confirmed` 时，不生成最终剪映工程。

“导出剪映工程”按钮必须先检查确认状态、当前剪映版本的原生空白模板和兼容导出器。条件不足时保存 `workflow/jianying_export_request.json` 并在界面说明下一步；不得调用已知与目标版本不兼容的旧导出器，也不得显示虚假的成功状态。

## 阶段三：可编辑剪映工程包 V1（可选）

读取 [references/capcut-project-package.md](references/capcut-project-package.md) 并按其中的低自由度流程交付。正式交付不是一组待导入素材，也不是单个合成 MP4，而是一个自包含的可编辑剪映工程包：素材已经按时间线匹配，视频、音频、字幕、录屏、画中画和可替换动效保持合理分轨。

核心工具关系固定为：

1. Whisper 生成带时间戳的口播文字。
2. FFmpeg/ffprobe 切分、变速、提取和标准化媒体，生成独立可替换的分段素材。
3. Remotion 只把复杂开场或讲解动效渲染为独立 MP4 素材。
4. Python 读取统一时间线配置、组织素材与轨道、调用 CapCut Mate、重写包内路径并完成打包。
5. CapCut Mate 生成与目标剪映结构匹配的草稿文件，包括时间线、轨道、素材位置、缩放、音量和字幕等信息。

不得凭空生成通用 `draft_content.json` 并把它当成兼容工程。优先让用户选择一个由其当前剪映版本新建的空白工程作为原生模板；复制模板后再注入时间线，绝不修改原模板。若 `video-editing` Skill 或 CapCut Mate 明确支持并已验证当前目标版本，可使用其版本化模板代替用户空白模板。

生成 `deliverables/capcut_v1_rough_cut/` 后运行：

```bash
python3 scripts/validate_capcut_draft.py \
  deliverables/capcut_v1_rough_cut \
  --report workflow/capcut_v1_validation.json
```

结构检查通过后，要求用户把整个工程包放入剪映草稿目录（或使用当前版本支持的导入方式），在目标剪映版本中实际打开。只有用户确认以下项目后，才把 V1 标记为 `verified`：

- 草稿出现在剪映项目列表并可打开；
- 素材没有丢失，时长和顺序正确；
- 字幕可以逐条修改；
- 录屏、真人画中画、音频和补充画面保持合理分轨；
- 切点、变速和同步关系正确；
- 工程可以保存、关闭并重新打开。

在要求用户打开剪映前，先提供与 V1 时间线一致的低码率审片代理。代理通过不等于草稿兼容性通过，两项都要记录。

结构验证不等于剪映兼容性验证。报告中使用“工程包结构检查通过”，不要写“剪映草稿已生成并可打开”或“兼容性通过”。用户实际打开、保存、关闭并重新打开后，才能称为“可用的可编辑剪映工程包”。如果打不开，保留失败包和报告，回到原生模板/版本匹配步骤修复；不要退化成普通素材包并宣称完成。

## 可选：OpenChatCut 高级交接

仅在用户明确要求内置工作台范围之外的高级外部编辑能力时启用。读取 [references/openchatcut-handoff.md](references/openchatcut-handoff.md)，再执行交接。

优先通过 OpenChatCut MCP 创建隔离编辑会话，以手动审批模式提交修改。让用户在工作台中预览、调整、撤销或批准。把每次批准后的操作摘要写入 `workflow/openchatcut_changes.json`。

不要让 OpenChatCut 成为唯一项目副本。保留：

- 已验证剪映 V1；
- OpenChatCut 项目导出；
- 修改操作记录；
- 审片 MP4。

## 阶段四：剪映最终精剪

用户要求剪映交付时，直接从已确认的 `workbench/project.json` 转换统一时间线，再生成分轨剪映工程包。不要通过 OpenChatCut 中转。工作台负责前期粗剪和逐字精剪，剪映负责用户后续的最终包装。

## 完成条件

仅在以下条件满足时报告工作台阶段完成：

- 工作台状态为 `confirmed`，自动保存版本仍可读取；
- 与确认时间线一致的审片视频已经导出并由用户批准；
- 原素材未被修改；
- 项目状态足以让下一次 Codex 会话继续执行。
- 所有适用的阶段预览均已由用户批准，不适用阶段已记录跳过原因。

如果用户同时要求剪映交付，还必须存在一个结构检查通过、自包含且素材已匹配的剪映工程包，并由用户在目标剪映版本中完成打开、保存、关闭和重新打开验证。
