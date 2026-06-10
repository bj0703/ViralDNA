## Why

之前的分析工作台设计参考了旧的变更记录，现在我们想要从零开始，全新定义 emo_transfer 前端的基础布局体系和视觉色彩主题。参考 NexusAI 现代 AI SaaS 产品风格，采用浅色优先清新紫蓝主题，这是整个前端界面的地基，需要独立、清晰地定义三栏分区的职责边界和统一的设计语言，为后续所有页面打下基础。

## What Changes

- 从零设计三栏分区布局系统，明确定义每一栏的定位、默认宽度、可调整范围和边界交互。
- 定义一套完整的浅色优先的 UI 色彩主题，采用 Soft Lavender 柔熏衣紫主色调系统，参考 NexusAI 现代 AI SaaS 产品风格。
- 建立基础布局约束、分栏拖拽机制和全局视觉一致性规范。

## Capabilities

### New Capabilities
- `three-column-workbench-layout`: 定义 emo_transfer 工作台的三栏分区布局系统，包含左中右三栏的职责划分、默认尺寸、分栏拖拽和响应式行为。
- `unified-color-theme-system`: 定义全站统一的浅色优先清新紫蓝色彩主题系统，包含色板、语义映射、透明度规范和使用规则。

### Modified Capabilities

## Impact

- 将作为整个前端项目的基础布局层和设计 token 层，后续所有页面组件都将在此之上构建。
- 不依赖之前的 build-analysis-workbench-ui 变更的任何设计假设，完全独立演进。
