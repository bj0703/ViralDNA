# Shared Memory Data Binding Specification

## 1. Overview
前后端核心数据类型契约，前端 Typescript 类型定义与后端 SessionSharedMemory 完全对齐，零字段转换直接映射。

## 2. Requirements

### 2.1 Core Types
在 `frontend/src/types/index.ts` 中新增以下类型：

```typescript
interface UploadedVideo {
  id: string
  filename: string
  url: string
  thumbnailUrl?: string
  duration: number
  is_reference: boolean
  createdAt: number
}

interface EditVersion {
  id: string
  versionLabel: string
  timestamp: number
  thumbnailUrl?: string
  snapshotId: string
}

interface AgentNode {
  name: string
  displayName: string
  status: 'idle' | 'running' | 'done' | 'error'
  startTime?: number
  endTime?: number
}

interface TimelineSegment {
  id: string
  trackId: string
  startInTimeline: number
  duration: number
  sourceVideoId?: string
  sourceStartTime?: number
  properties: Record<string, any>
}

interface EditTrack {
  id: string
  type: 'video' | 'audio' | 'caption'
  name: string
  segments: TimelineSegment[]
}

interface SessionSharedMemory {
  job_id: string
  inputs: {
    uploaded_videos: UploadedVideo[]
  }
  entries: {
    edit_timeline: {
      tracks: EditTrack[]
    }
  }
  version_history: {
    version: string
    timestamp: number
    snapshot_id: string
    thumbnail_url?: string
  }[]
}
```

### 2.2 Data Mapping
| Frontend State | Backend Redis Field | Transformation |
|---|---|---|
| videoList | `inputs.uploaded_videos` | 直接赋值，无转换 |
| versions | `version_history` → 映射 `version` → `versionLabel` (v2 → "V2.0") | 单字段字符串格式化 |
| timeline.tracks | `entries.edit_timeline.tracks` | 直接赋值，无转换 |
| agentNodes | SSE 事件流生成状态机 | 实时更新 |

## 3. Acceptance Criteria
- 所有字段名与后端 Python dataclass 100% 保持一致
- 版本号字符串格式化 `v3` → `V3.0` 正确展示
- TypeScript 无类型编译错误
