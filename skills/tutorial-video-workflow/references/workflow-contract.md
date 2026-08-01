# 工作流交付契约

## 项目目录

```text
project/
├── workflow/
│   ├── project.json
│   ├── preflight.json
│   ├── capcut_v1_validation.json
│   └── openchatcut_changes.json
├── work/
│   ├── transcripts/
│   ├── proxies/
│   ├── clips/
│   └── generated_assets/
├── previews/
└── deliverables/
    ├── capcut_v1_rough_cut/
    ├── openchatcut_project/
    └── capcut_v2_refined/
```

不要把原素材复制进上述目录，除非用户明确要求。默认在 `project.json` 中记录绝对来源路径。

## 时间线记录

每个片段至少记录：

- 稳定 ID；
- 角色：narration、screen、talking_head、broll、caption、motion；
- 来源文件绝对路径；
- 源入点和源出点；
- 输出时间线起点和时长；
- 速度；
- 音量；
- 匹配置信度；
- editable、preprocessed 或 baked 可编辑性级别；
- 生成原因或用户确认记录。

## 匹配策略

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

永不覆盖 `verified` 版本。每个剪映版本同时记录：生成时间、来源配置、静态验证报告、实际打开验证状态和已知损失。
