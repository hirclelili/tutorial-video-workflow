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
请使用 skill-installer 从以下 GitHub 仓库安装 tutorial-video-workflow：
https://github.com/hirclelili/tutorial-video-workflow/tree/main/skills/tutorial-video-workflow
```

安装完成后，在新任务中使用：

```text
使用 $tutorial-video-workflow 处理这个素材文件夹。先检查环境和素材，保持原文件不变，第一轮先生成并验证可编辑的剪映 V1。
```

## 能力边界

本仓库提供编排、项目初始化、分层环境检查、剪映草稿静态验证和 OpenChatCut 交接规则。实际转写、自动粗剪、视觉生成和剪映草稿导出会按需调用相应 Skill 或本机工具。
