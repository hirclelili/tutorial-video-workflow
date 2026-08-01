# 工作流交付契约

## 项目目录

```text
project/
├── workflow/
│   ├── project.json
│   ├── preflight.json
│   ├── capcut_v1_validation.json
│   ├── capcut_template.json
│   ├── reviews.json
│   └── openchatcut_changes.json
├── work/
│   ├── transcripts/
│   ├── proxies/
│   ├── clips/
│   └── generated_assets/
├── previews/           每阶段版本化预览
└── deliverables/
    ├── capcut_v1_rough_cut/
    ├── openchatcut_project/
    └── capcut_v2_refined/
```

工作区默认只记录原素材绝对路径，不修改原素材。正式剪映工程包必须把它引用的媒体复制到自身资源目录，使工程包不依赖临时目录或原素材路径。

## 时间线记录

`project.json` 必须先记录用户确认的请求：目标、主处理文件、经确认的辅助素材、输出数量和确认状态。默认输出数量为 1。

每个片段至少记录：

- 稳定 ID；
- 角色：primary 或按所选路线使用 narration、screen、talking_head、broll、caption、motion 等内部标签；
- 来源文件绝对路径；
- 源入点和源出点；
- 输出时间线起点和时长；
- 速度；
- 音量；
- 匹配置信度；
- editable、preprocessed 或 baked 可编辑性级别；
- 生成原因或用户确认记录。

## 匹配策略

仅在所选路线需要画面与语音匹配时应用本节。

综合口播语义、录屏界面文字、操作变化和时间限制进行匹配。不要仅凭文件名或单一关键词匹配。

- 高置信度：自动采用并在摘要中列出。
- 中置信度：生成候选对比，允许用户选择。
- 低置信度：保留真人讲解或占位，不强行匹配。

变速必须记录原始时长、目标时长和速度。超出自然可观看范围时优先切分录屏，而不是继续加速。

## 可编辑性等级

- `editable`：剪映中保持原生片段、字幕、位置、缩放或音量控制。
- `preprocessed`：已经切分、降噪或变速，但作为独立素材保留。
- `baked`：复杂动效已经渲染。必须保留源工程和独立输出文件。

## 版本规则

永不覆盖 `verified` 版本。每个剪映版本同时记录：生成时间、来源配置、目标剪映版本、原生模板副本来源、CapCut Mate 版本、结构验证报告、实际打开与重开验证状态和已知损失。

所有适用阶段都必须在 `reviews.json` 中留下明确的用户决定。用户要求修改后保留旧预览并递增版本。
