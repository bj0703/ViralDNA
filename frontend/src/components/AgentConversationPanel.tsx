import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AgentNodeProgress } from './AgentNodeProgress';
import { useSSEEventSource } from '../hooks/useSSEEventSource';
import type {
  AgentMessage,
  AgentNode,
  AgentPhaseEntry,
  Message,
  SSEEventPayload,
  UploadedVideo,
} from '../types';
import { AGENT_CLASS_NAME_TO_DISPLAY } from '../types';

interface AgentConversationPanelProps {
  currentJobId: string | null;
  setCurrentJobId: (jobId: string | null) => void;
  videoList: UploadedVideo[];
  setVideoList: React.Dispatch<React.SetStateAction<UploadedVideo[]>>;
  selectedReferenceVideoId: string | null;
}

const PHASE_META: Record<AgentPhaseEntry['phase'], { label: string; color: string; icon: string }> = {
  think: { label: '思考', color: '#d97706', icon: '💡' },
  plan: { label: '规划', color: '#2563eb', icon: '🧭' },
  action: { label: '执行', color: '#7c3aed', icon: '⚡' },
  observation: { label: '观察', color: '#059669', icon: '👁' },
};

const buildPendingJobPayload = (
  prompt: string,
  videos: UploadedVideo[],
  selectedReferenceVideoId: string | null,
) => {
  const formData = new FormData();
  formData.append('intent', prompt);

  const localVideos = videos.filter((video) => video.localFile);
  const referenceFlags: string[] = [];
  const clientIds: string[] = [];

  for (const video of localVideos) {
    formData.append('files', video.localFile as File);
    referenceFlags.push(video.is_reference ? 'true' : 'false');
    clientIds.push(video.id);
  }

  formData.append('is_reference_flags', referenceFlags.join(','));
  formData.append('client_video_ids', clientIds.join(','));
  if (selectedReferenceVideoId) {
    formData.append('selected_reference_client_id', selectedReferenceVideoId);
  }
  return formData;
};

const createAgentMessage = (messageId: string, agentName: string, timestamp: number): AgentMessage => ({
  type: 'agent',
  id: messageId,
  agentName,
  phases: [],
  thinking: { isExpanded: false, content: '' },
  result: { content: '', cardType: 'overview' },
  status: 'running',
  timestamp,
});

const ensureAgentMessage = (
  messages: Message[],
  messageId: string,
  agentName: string,
  timestamp: number,
) => {
  const exists = messages.some((msg) => msg.type === 'agent' && msg.id === messageId);
  if (exists) {
    return messages;
  }
  return [...messages, createAgentMessage(messageId, agentName, timestamp)];
};

const buildConversationStateFromEvents = (events: SSEEventPayload[]) => {
  const nodes: AgentNode[] = [];
  const messages: Message[] = [];
  const currentMessageIdByAgent: Record<string, string> = {};

  const ensureReplayMessage = (messageId: string, agentName: string, timestamp: number) => {
    const exists = messages.some((msg) => msg.type === 'agent' && msg.id === messageId);
    if (!exists) {
      messages.push(createAgentMessage(messageId, agentName, timestamp));
    }
  };

  for (const evt of events) {
    if (evt.event_type === 'plan_ready') {
      const selectedNames = (evt.payload?.selected_agent_names as string[]) ?? [];
      nodes.length = 0;
      selectedNames.forEach((agentClassName, index) => {
        nodes.push({
          id: String(index + 1),
          agentClassName,
          name: AGENT_CLASS_NAME_TO_DISPLAY[agentClassName] ?? agentClassName,
          status: 'pending',
        });
      });
      continue;
    }

    if (!evt.agent_name) {
      continue;
    }

    const agentDisplayName = AGENT_CLASS_NAME_TO_DISPLAY[evt.agent_name] ?? evt.agent_name;
    const updateNodeStatus = (status: AgentNode['status']) => {
      const found = nodes.find((n) => n.agentClassName === evt.agent_name);
      if (found) {
        found.status = status;
      }
    };

    if (evt.event_type === 'step_start') {
      const messageId = `${evt.agent_name}-${evt.event_id}`;
      currentMessageIdByAgent[evt.agent_name] = messageId;
      ensureReplayMessage(messageId, agentDisplayName, evt.timestamp);
      updateNodeStatus('running');
      continue;
    }

    const messageId = currentMessageIdByAgent[evt.agent_name] ?? `${evt.agent_name}-${evt.event_id}`;
    ensureReplayMessage(messageId, agentDisplayName, evt.timestamp);
    const target = messages.find((msg) => msg.type === 'agent' && msg.id === messageId) as AgentMessage | undefined;
    if (!target) {
      continue;
    }

    if (evt.event_type === 'step_phase') {
      target.phases.push({
        id: evt.event_id,
        phase: String(evt.payload?.phase ?? 'observation') as AgentPhaseEntry['phase'],
        title: String(evt.payload?.title ?? '阶段更新'),
        detail: String(evt.payload?.detail ?? ''),
        streamText: '',
      });
      continue;
    }

    if (evt.event_type === 'step_delta') {
      const delta = String(evt.payload?.delta ?? '');
      const latest = target.phases[target.phases.length - 1];
      if (!latest || (latest.phase !== 'action' && latest.phase !== 'observation')) {
        target.phases.push({
          id: `${evt.event_id}-stream`,
          phase: 'observation',
          title: '流式输出',
          detail: '模型正在返回中间文本。',
          streamText: delta,
        });
      } else {
        latest.streamText = `${latest.streamText ?? ''}${delta}`;
      }
      target.result.content = `${target.result.content}${delta}`;
      continue;
    }

    if (evt.event_type === 'step_write') {
      updateNodeStatus('done');
      target.status = 'done';
      const resultPreview = String(evt.payload?.result_preview ?? evt.payload?.result_text ?? '');
      const resultType = String(evt.payload?.result_type ?? 'result');
      const resultTruncated = Boolean(evt.payload?.result_truncated);
      target.result.content = target.result.content || resultPreview;
      target.resultJson = resultPreview
        ? `${resultType} preview\n${resultPreview}${resultTruncated ? '\n\n[full result kept in shared memory]' : ''}`
        : undefined;
      continue;
    }

    if (evt.event_type === 'step_skip') {
      updateNodeStatus('skipped');
      continue;
    }

    if (evt.event_type === 'step_fail') {
      updateNodeStatus('error');
      target.status = 'error';
    }
  }

  return { nodes, messages, currentMessageIdByAgent };
};

export const AgentConversationPanel: React.FC<AgentConversationPanelProps> = ({
  currentJobId,
  setCurrentJobId,
  videoList,
  setVideoList,
  selectedReferenceVideoId,
}) => {
  const [agentNodes, setAgentNodes] = useState<AgentNode[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draftBoxExpanded, setDraftBoxExpanded] = useState(false);
  const [inputText, setInputText] = useState('');
  const [errorText, setErrorText] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const currentMessageIdByAgentRef = useRef<Record<string, string>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const appendPhaseToMessage = useCallback((
    messageId: string,
    phase: AgentPhaseEntry,
    timestamp: number,
    agentDisplayName: string,
  ) => {
    setMessages((prev) => {
      const base = ensureAgentMessage(prev, messageId, agentDisplayName, timestamp);
      return base.map((msg) => {
        if (msg.type !== 'agent' || msg.id !== messageId) {
          return msg;
        }
        return {
          ...msg,
          phases: [...msg.phases, phase],
        };
      });
    });
  }, []);

  const updateLatestPhase = useCallback((
    messageId: string,
    updater: (phase: AgentPhaseEntry) => AgentPhaseEntry,
    timestamp: number,
    agentDisplayName: string,
  ) => {
    setMessages((prev) => {
      const base = ensureAgentMessage(prev, messageId, agentDisplayName, timestamp);
      return base.map((msg) => {
        if (msg.type !== 'agent' || msg.id !== messageId) {
          return msg;
        }
        if (msg.phases.length === 0) {
          return msg;
        }
        const nextPhases = [...msg.phases];
        nextPhases[nextPhases.length - 1] = updater(nextPhases[nextPhases.length - 1]);
        return { ...msg, phases: nextPhases };
      });
    });
  }, []);

  const onSSEEvent = useCallback((evt: SSEEventPayload) => {
    if (evt.event_type === 'plan_ready') {
      const selectedNames = (evt.payload?.selected_agent_names as string[]) ?? [];
      const newNodes: AgentNode[] = selectedNames.map((agentClassName, index) => ({
        id: String(index + 1),
        agentClassName,
        name: AGENT_CLASS_NAME_TO_DISPLAY[agentClassName] ?? agentClassName,
        status: 'pending',
      }));
      setAgentNodes(newNodes);
    }

    if (evt.event_type === 'step_start' && evt.agent_name) {
      const agentName = evt.agent_name;
      const messageId = `${agentName}-${evt.event_id}`;
      const agentDisplayName = AGENT_CLASS_NAME_TO_DISPLAY[agentName] ?? agentName;
      currentMessageIdByAgentRef.current[agentName] = messageId;
      setAgentNodes((prev) => prev.map((n) => (
        n.agentClassName === agentName ? { ...n, status: 'running' } : n
      )));
      setMessages((prev) => ensureAgentMessage(prev, messageId, agentDisplayName, evt.timestamp));
    }

    if (evt.event_type === 'step_phase' && evt.agent_name) {
      const messageId = currentMessageIdByAgentRef.current[evt.agent_name];
      const phase = String(evt.payload?.phase ?? 'observation') as AgentPhaseEntry['phase'];
      const title = String(evt.payload?.title ?? '阶段更新');
      const detail = String(evt.payload?.detail ?? '');
      const agentDisplayName = AGENT_CLASS_NAME_TO_DISPLAY[evt.agent_name] ?? evt.agent_name;
      if (messageId) {
        appendPhaseToMessage(messageId, {
          id: evt.event_id,
          phase,
          title,
          detail,
          streamText: '',
        }, evt.timestamp, agentDisplayName);
      }
    }

    if (evt.event_type === 'step_delta' && evt.agent_name) {
      const messageId = currentMessageIdByAgentRef.current[evt.agent_name];
      const delta = String(evt.payload?.delta ?? '');
      const agentDisplayName = AGENT_CLASS_NAME_TO_DISPLAY[evt.agent_name] ?? evt.agent_name;
      if (messageId && delta) {
        setMessages((prev) => {
          const base = ensureAgentMessage(prev, messageId, agentDisplayName, evt.timestamp);
          return base.map((msg) => {
            if (msg.type !== 'agent' || msg.id !== messageId) {
              return msg;
            }

            const nextPhases = [...msg.phases];
            const latest = nextPhases[nextPhases.length - 1];
            if (!latest || (latest.phase !== 'action' && latest.phase !== 'observation')) {
              nextPhases.push({
                id: `${evt.event_id}-stream`,
                phase: 'observation',
                title: '流式输出',
                detail: '模型正在返回中间文本。',
                streamText: delta,
              });
            } else {
              nextPhases[nextPhases.length - 1] = {
                ...latest,
                streamText: `${latest.streamText ?? ''}${delta}`,
              };
            }

            return {
              ...msg,
              phases: nextPhases,
              result: {
                ...msg.result,
                content: `${msg.result.content}${delta}`,
              },
            };
          });
        });
      }
    }

    if (evt.event_type === 'step_write' && evt.agent_name) {
      const agentDisplayName = AGENT_CLASS_NAME_TO_DISPLAY[evt.agent_name] ?? evt.agent_name;
      const messageId = currentMessageIdByAgentRef.current[evt.agent_name];
      const resultText = String(evt.payload?.result_text ?? '');
      const resultPreview = String(evt.payload?.result_preview ?? resultText);
      const resultType = String(evt.payload?.result_type ?? 'result');
      const resultTruncated = Boolean(evt.payload?.result_truncated);
      setAgentNodes((prev) => prev.map((n) => (
        n.agentClassName === evt.agent_name ? { ...n, status: 'done' } : n
      )));
      setMessages((prev) => {
        const safeMessageId = messageId ?? evt.event_id;
        const base = ensureAgentMessage(prev, safeMessageId, agentDisplayName, evt.timestamp);
        return base.map((msg) => {
          if (msg.type !== 'agent' || msg.id !== safeMessageId) {
            return msg;
          }
          return {
            ...msg,
            status: 'done',
            result: {
              ...msg.result,
              content: msg.result.content || resultPreview,
            },
            resultJson: resultPreview
              ? `${resultType} preview\n${resultPreview}${resultTruncated ? '\n\n[full result kept in shared memory]' : ''}`
              : undefined,
          };
        });
      });
    }

    if (evt.event_type === 'step_skip' && evt.agent_name) {
      setAgentNodes((prev) => prev.map((n) => (
        n.agentClassName === evt.agent_name ? { ...n, status: 'skipped' } : n
      )));
    }

    if (evt.event_type === 'step_fail' && evt.agent_name) {
      const messageId = currentMessageIdByAgentRef.current[evt.agent_name];
      const agentDisplayName = AGENT_CLASS_NAME_TO_DISPLAY[evt.agent_name] ?? evt.agent_name;
      setAgentNodes((prev) => prev.map((n) => (
        n.agentClassName === evt.agent_name ? { ...n, status: 'error' } : n
      )));
      if (messageId) {
        updateLatestPhase(
          messageId,
          (phase) => ({
            ...phase,
            detail: `${phase.detail}${phase.detail ? ' ' : ''}执行失败。`,
          }),
          evt.timestamp,
          agentDisplayName,
        );
        setMessages((prev) => prev.map((msg) => (
          msg.type === 'agent' && msg.id === messageId
            ? { ...msg, status: 'error' }
            : msg
        )));
      }
    }

    window.setTimeout(scrollToBottom, 50);
  }, [appendPhaseToMessage, scrollToBottom, updateLatestPhase]);

  const { isConnected } = useSSEEventSource({
    jobId: currentJobId,
    onEvent: onSSEEvent,
  });

  const handleSubmit = useCallback(async () => {
    const prompt = inputText.trim();
    if (!prompt || isSubmitting) return;

    const userMsg: Message = {
      type: 'user',
      id: Date.now().toString(),
      content: prompt,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setErrorText(null);
    setIsSubmitting(true);

    try {
      if (!currentJobId) {
        const formData = buildPendingJobPayload(prompt, videoList, selectedReferenceVideoId);
        const res = await fetch('/api/orchestration/jobs', {
          method: 'POST',
          body: formData,
        });
        if (!res.ok) {
          throw new Error(`create job failed: ${res.status}`);
        }
        const data = await res.json();
        setCurrentJobId(data.job_id);
        setVideoList((prev) => prev.map((video) => ({ ...video, isPending: false })));
      } else {
        const res = await fetch(`/api/orchestration/jobs/${currentJobId}/re-submit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            new_user_prompt: prompt,
            selected_reference_video_id: selectedReferenceVideoId,
          }),
        });
        if (!res.ok) {
          throw new Error(`re-submit failed: ${res.status}`);
        }
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : 'request failed';
      setErrorText(message);
    } finally {
      setIsSubmitting(false);
    }
  }, [currentJobId, inputText, isSubmitting, selectedReferenceVideoId, setCurrentJobId, setVideoList, videoList]);

  const loadHistoryEvents = useCallback(async () => {
    if (!currentJobId) return;
    try {
      const res = await fetch(`/api/orchestration/jobs/${currentJobId}/trace`);
      const data = await res.json();
      const events: SSEEventPayload[] = data.event_log ?? [];
      const replayState = buildConversationStateFromEvents(events);
      currentMessageIdByAgentRef.current = replayState.currentMessageIdByAgent;
      setAgentNodes(replayState.nodes);
      setMessages(replayState.messages);
    } catch (e) {
      console.error('[Load History] failed:', e);
    }
  }, [currentJobId]);

  useEffect(() => {
    if (!currentJobId) {
      setAgentNodes([]);
      setMessages([]);
      currentMessageIdByAgentRef.current = {};
      return;
    }
    void loadHistoryEvents();
  }, [currentJobId, loadHistoryEvents]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 16px',
        borderBottom: '1px solid var(--color-neutral-200)',
      }}>
        <span style={{ fontSize: 13, color: 'var(--color-neutral-600)' }}>
          {isConnected ? '实时连接中' : currentJobId ? '等待连接' : '等待创建任务'}
        </span>
        <button
          onClick={() => {
            setDraftBoxExpanded(!draftBoxExpanded);
            if (!draftBoxExpanded) loadHistoryEvents();
          }}
          style={{
            padding: '4px 12px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--color-neutral-300)',
            backgroundColor: 'white',
            fontSize: 12,
            cursor: 'pointer',
          }}
        >
          {draftBoxExpanded ? '收起草稿箱' : '草稿箱'}
        </button>
      </div>

      {agentNodes.length > 0 && <AgentNodeProgress nodes={agentNodes} />}

      <div style={{ flex: 1, padding: 20, overflowY: 'auto' }}>
        {messages.length === 0 && agentNodes.length === 0 && (
          <p style={{ color: 'var(--color-neutral-500)', textAlign: 'center', marginTop: 40 }}>
            先上传样例和素材，然后直接发送第一条需求即可创建任务。
          </p>
        )}
        {messages.map((msg) => (
          <div key={msg.id} style={{ marginBottom: 16 }}>
            {msg.type === 'user' && (
              <div style={{
                marginLeft: 'auto',
                maxWidth: '70%',
                padding: '10px 16px',
                borderRadius: 16,
                backgroundColor: 'var(--color-primary-500)',
                color: 'white',
              }}>
                {msg.content}
              </div>
            )}
            {msg.type === 'agent' && (
              <div style={{
                marginRight: 'auto',
                maxWidth: '92%',
                padding: '14px 16px',
                borderRadius: 16,
                backgroundColor: 'white',
                border: '1px solid var(--color-neutral-200)',
                boxShadow: '0 10px 30px rgba(15, 23, 42, 0.04)',
              }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-neutral-800)', marginBottom: 10 }}>
                  {msg.agentName}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {msg.phases.map((phase, index) => {
                    const meta = PHASE_META[phase.phase];
                    return (
                      <div
                        key={phase.id}
                        style={{
                          border: '1px solid var(--color-neutral-200)',
                          borderLeft: `4px solid ${meta.color}`,
                          borderRadius: 12,
                          padding: '10px 12px',
                          backgroundColor: '#fafafa',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                          <span style={{ fontSize: 12, color: meta.color, fontWeight: 700 }}>
                            STEP {index + 1}
                          </span>
                          <span style={{ fontSize: 12 }}>{meta.icon}</span>
                          <span style={{ fontSize: 16, fontWeight: 700, color: '#111827' }}>
                            {meta.label}
                          </span>
                        </div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: '#1f2937', marginBottom: 4 }}>
                          {phase.title}
                        </div>
                        {phase.detail && (
                          <div style={{ fontSize: 13, lineHeight: 1.6, color: '#4b5563' }}>
                            {phase.detail}
                          </div>
                        )}
                        {phase.streamText && (
                          <div style={{
                            marginTop: 8,
                            padding: '10px 12px',
                            borderRadius: 10,
                            backgroundColor: '#f8fafc',
                            border: '1px solid #e2e8f0',
                          }}>
                            <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6 }}>中间输出</div>
                            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12, color: '#0f172a' }}>
                              {phase.streamText}
                            </pre>
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {msg.resultJson && (
                      <div style={{
                        border: '1px solid #dbeafe',
                        backgroundColor: '#eff6ff',
                        borderRadius: 12,
                        padding: '10px 12px',
                      }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: '#1d4ed8', marginBottom: 6 }}>
                        结果预览
                        </div>
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12, color: '#1e3a8a' }}>
                        {msg.resultJson}
                      </pre>
                    </div>
                  )}

                  {msg.status === 'running' && msg.phases.length === 0 && (
                    <div style={{ fontSize: 12, color: 'var(--color-neutral-500)' }}>等待阶段信息...</div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
        {errorText && (
          <div
            style={{
              marginTop: 12,
              padding: '10px 12px',
              borderRadius: 10,
              backgroundColor: '#fff1f2',
              color: '#be123c',
              fontSize: 12,
            }}
          >
            {errorText}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div style={{ padding: 16, borderTop: '1px solid var(--color-neutral-200)' }}>
        <div style={{ display: 'flex', gap: 10 }}>
          <input
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            style={{
              flex: 1,
              height: 42,
              borderRadius: 'var(--radius-xl)',
              border: '1px solid var(--color-neutral-200)',
              paddingLeft: 14,
              outline: 'none',
              backgroundColor: 'var(--color-neutral-50)',
            }}
            placeholder={currentJobId ? '继续输入增量指令...' : '输入首条需求并创建任务...'}
          />
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            style={{
              padding: '0 20px',
              height: 42,
              borderRadius: 'var(--radius-xl)',
              border: 'none',
              backgroundColor: 'var(--color-primary-500)',
              color: 'white',
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              opacity: isSubmitting ? 0.6 : 1,
            }}
          >
            {isSubmitting ? '发送中' : currentJobId ? '发送' : '开始'}
          </button>
        </div>
      </div>
    </div>
  );
};
