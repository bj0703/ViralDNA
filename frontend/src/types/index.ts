export type CardType = 'overview' | 'script' | 'timeline' | 'assets' | 'report';
export type AgentStatus = 'pending' | 'running' | 'done' | 'error' | 'skipped';
export type MessageStatus = 'running' | 'done' | 'error';
export type AgentPhaseType = 'think' | 'plan' | 'action' | 'observation';

export const AGENT_CLASS_NAME_TO_DISPLAY: Record<string, string> = {
  ReferenceAnalyzerAgent: '参考分析',
  AssetIndexerAgent: '资产索引',
  SlotMatcherAgent: '插槽匹配',
  GapResolverAgent: '间隙解析',
  GeneratedAssetBuilderAgent: '资源生成',
  EditPlannerAgent: '编辑规划',
  FinalVideoRendererAgent: '最终渲染',
};

export interface AgentNode {
  id: string;
  name: string;
  agentClassName: string;
  status: AgentStatus;
}

export interface UploadedVideo {
  id: string;
  filename: string;
  url: string;
  thumbnailUrl?: string;
  duration: number;
  is_reference: boolean;
  createdAt: number;
  localFile?: File;
  storagePath?: string;
  originalFilename?: string;
  savedFilename?: string;
  isPending?: boolean;
}

export interface SharedMemorySnapshot {
  session_id: string;
  version: number;
  created_at: number;
  inputs: {
    user_prompt: string;
    uploaded_videos: Array<Record<string, unknown>>;
    selected_reference_video_id?: string | null;
  };
  entries: Record<string, { data: Record<string, unknown>; meta: Record<string, unknown>; is_ready: boolean }>;
  event_log: SSEEventPayload[];
}

export interface EditVersion {
  id: string;
  versionLabel: string;
  timestamp: number;
  thumbnailUrl?: string;
  snapshotId: string;
}

export interface TimelineSegment {
  id: string;
  trackId: string;
  startInTimeline: number;
  duration: number;
  sourceVideoId?: string;
  sourceStartTime?: number;
  properties: Record<string, unknown>;
}

export interface EditTrack {
  id: string;
  type: 'video' | 'audio' | 'caption';
  name: string;
  segments: TimelineSegment[];
}

export interface SSEEventPayload {
  event_id: string;
  event_type:
    | 'plan_ready'
    | 'step_start'
    | 'step_phase'
    | 'step_delta'
    | 'step_write'
    | 'step_skip'
    | 'step_fail'
    | 'resource_updated'
    | 'timeline_updated';
  agent_name?: string;
  payload: Record<string, unknown>;
  timestamp: number;
}

export interface AgentPhaseEntry {
  id: string;
  phase: AgentPhaseType;
  title: string;
  detail: string;
  streamText?: string;
}

export interface ResultCard {
  id: string;
  emoji: string;
  cardType: CardType;
  title: string;
  agentName: string;
  timestamp: number;
  content: Record<string, unknown>;
}

export interface UserMessage {
  type: 'user';
  id: string;
  content: string;
  timestamp: number;
}

export interface AgentMessage {
  type: 'agent';
  id: string;
  agentName: string;
  agentIcon?: string;
  phases: AgentPhaseEntry[];
  thinking: {
    isExpanded: boolean;
    content: string;
  };
  result: {
    content: string;
    cardType: CardType;
  };
  resultJson?: string;
  status: MessageStatus;
  timestamp: number;
}

export type Message = UserMessage | AgentMessage;

export * from './videoResource';
export * from './centerWorkbench';
