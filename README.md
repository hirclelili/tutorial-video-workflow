# Tutorial Video Workflow

面向教程、产品演示和口播视频的 Codex 编排 Skill。它将自动粗剪、可编辑剪映草稿、OpenChatCut 可视化精剪和剪映人工交付组织成一条可恢复的工作流。

## 核心原则

- 保持原始素材不变。
- 先生成并验证可编辑剪映 V1，再进入 OpenChatCut。
- 保持字幕、录屏、音频和画中画尽可能可编辑、可分轨。
- OpenChatCut 回写失败时，仍保留可继续人工剪辑的剪映 V1。

## 安装

在 Codex 中发送：

```text
帮我安装这个 Skill：
https://github.com/hirclelili/tutorial-video-workflow/tree/main/skills/tutorial-video-workflow
```

`skill-installer` 是 Codex 自带的安装能力，用户无需提前安装或了解它。直接把上面的 GitHub 链接发给 Codex，并说明要安装即可。

安装完成后，在新任务中使用：

```text
使用 $tutorial-video-workflow 处理这个素材文件夹。先检查环境和素材，保持原文件不变，第一轮先生成并验证可编辑的剪映 V1。
```

## 能力边界

本仓库提供编排、项目初始化、分层环境检查、剪映草稿静态验证和 OpenChatCut 交接规则。实际转写、自动粗剪、视觉生成和剪映草稿导出会按需调用相应 Skill 或本机工具。

首次运行时会先检查 Python 3。用户没有安装 Python 时，Codex 会说明用途并申请许可，安装和验证后继续原视频任务；不会要求用户提前准备开发环境，也不会静默安装系统软件。
