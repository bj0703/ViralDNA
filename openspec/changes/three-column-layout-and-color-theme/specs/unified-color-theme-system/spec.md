## ADDED Requirements

### Requirement: 系统提供浅色优先柔熏衣紫主题
系统 SHALL 默认以浅色模式作为全站唯一默认主题， SHALL 采用 Soft Lavender 清新紫蓝主色调体系，参考 NexusAI 现代 SaaS AI 产品视觉风格。

#### Scenario: 页面加载时自动应用浅色主题
- **WHEN** 页面首次加载完成
- **THEN** 全站自动应用浅色主题，页面背景色为 #F5F5F5

### Requirement: 系统定义完整中性色色板系统
系统 SHALL 提供 10 级中性色板，所有颜色通过 CSS 变量统一导出。

#### Scenario: 中性色语义映射正确
- **WHEN** 访问 CSS 变量系统
- **THEN** --color-neutral-50: #F5F5F5, --color-neutral-100: #FFFFFF, --color-neutral-200: #E5E7EB, --color-neutral-300: #D1D5DB, --color-neutral-400: #9CA3AF, --color-neutral-500: #6B7280, --color-neutral-600: #4B5563, --color-neutral-700: #374151, --color-neutral-800: #1F2937, --color-neutral-900: #111827

### Requirement: 系统定义完整紫蓝主色色板系统
系统 SHALL 提供 7 级紫蓝主色色板，主强调色为 #6366F1。

#### Scenario: 紫蓝主色语义映射正确
- **WHEN** 访问 CSS 变量系统
- **THEN** --color-primary-50: #EDE9FE, --color-primary-100: #DDD6FE, --color-primary-200: #C4B5FD, --color-primary-300: #A78BFA, --color-primary-400: #818CF8, --color-primary-500: #6366F1, --color-primary-600: #4F46E5

### Requirement: 系统定义完整语义色板系统
系统 SHALL 提供成功、警告、错误、信息四个语义色，用于状态反馈。

#### Scenario: 语义色语义映射正确
- **WHEN** 访问 CSS 变量系统
- **THEN** --color-success: #10B981, --color-warning: #F59E0B, --color-error: #EF4444, --color-info: #06B6D4

### Requirement: 系统保证文本对比度符合可访问性标准
系统 SHALL 保证所有正文文本的颜色对比度不低于 WCAG AA 的 4.5:1 标准。

#### Scenario: 常规正文文本对比度校验
- **WHEN** 校验 Neutral 600 (#4B5563) 文本在 Neutral 50 (#F5F5F5) 背景上
- **THEN** 对比度 ≥ 4.5:1，满足可访问性要求
