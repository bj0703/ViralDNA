import React, { useEffect, useRef, useState } from 'react';
import type { UploadedVideo } from '../types';

interface SampleVideoTabContentProps {
  currentJobId: string | null;
  activeVideo: UploadedVideo | null;
  videoList: UploadedVideo[];
  selectedReferenceVideoId: string | null;
  referenceAnalysis: Record<string, any> | null;
}

interface TimelineItem {
  id: string;
  role: string;
  title: string;
  startTime: number;
  endTime: number;
  duration: number;
  summary: string;
  source: Record<string, any>;
}

interface BeatMarker {
  id: string;
  time: number;
  label: string;
  color: string;
}

interface TransitionMarker {
  id: string;
  startTime: number;
  endTime: number;
  label: string;
  color: string;
}

interface TransitionEventItem {
  id: string;
  atTime: number;
  transitionType: string;
  fromShotId: string;
  toShotId: string;
  fromSummary: string;
  toSummary: string;
  strength: string;
  purpose: string;
}

const ROLE_COLOR: Record<string, string> = {
  hook: '#f97316',
  develop: '#2563eb',
  climax: '#dc2626',
  payoff: '#7c3aed',
  cta: '#059669',
  context_build: '#64748b',
  emotion_climax: '#0f766e',
};

const formatSeconds = (value: unknown) => {
  const num = Number(value);
  if (!Number.isFinite(num)) return '--';
  return `${num.toFixed(1)}s`;
};

const getRoleColor = (role: string) => ROLE_COLOR[role] ?? '#64748b';

const getRoleLabel = (role: string) => {
  if (role === 'hook') return 'Hook';
  if (role === 'develop') return 'Develop';
  if (role === 'climax') return 'Climax';
  if (role === 'payoff') return 'Payoff';
  if (role === 'cta') return 'CTA';
  if (role === 'context_build') return 'Context';
  if (role === 'emotion_climax') return 'Emotion';
  return role || 'Slot';
};

const getBeatLabel = (value: unknown) => {
  const beat = String(value ?? 'any');
  if (beat === 'first_strong_beat') return '首个强拍';
  if (beat === 'bar_change') return '小节切点';
  if (beat === 'phrase_release') return '乐句释放点';
  if (beat === 'transition_downbeat') return '转场落点';
  if (beat === 'any') return '自由贴点';
  return beat;
};

const getBeatColor = (value: unknown) => {
  const beat = String(value ?? 'any');
  if (beat === 'first_strong_beat') return '#ef4444';
  if (beat === 'bar_change') return '#f59e0b';
  if (beat === 'phrase_release') return '#0ea5e9';
  if (beat === 'transition_downbeat') return '#8b5cf6';
  return '#94a3b8';
};

const getTransitionTone = (value: unknown) => {
  const transition = String(value ?? 'cut');
  if (transition.includes('flash') || transition.includes('whip') || transition.includes('zoom') || transition.includes('spin')) return '#dc2626';
  if (transition.includes('blur') || transition.includes('dissolve') || transition.includes('overlay') || transition.includes('mask')) return '#7c3aed';
  if (transition.includes('pull') || transition.includes('slide')) return '#2563eb';
  if (transition.includes('cut')) return '#0f766e';
  return '#475569';
};

const getTransitionLabel = (value: unknown) => {
  const transition = String(value ?? 'cut');
  if (transition === 'cut') return '硬切';
  if (transition === 'flash_black') return '闪黑';
  if (transition === 'blur') return '模糊';
  if (transition === 'whip_pan') return '甩镜';
  if (transition === 'pull_down') return '下拉';
  if (transition === 'pull_up') return '上拉';
  if (transition === 'slide_left') return '左滑';
  if (transition === 'slide_right') return '右滑';
  if (transition === 'zoom_cut') return '变焦切';
  if (transition === 'dissolve') return '叠化';
  if (transition === 'overlay') return '叠加';
  if (transition === 'mask_reveal') return '遮罩揭示';
  if (transition === 'camera_spin') return '旋转切换';
  return transition;
};

const paceColor = (pace: string) => {
  if (pace.includes('fast') || pace.includes('快')) return '#fb7185';
  if (pace.includes('slow') || pace.includes('慢')) return '#38bdf8';
  return '#f59e0b';
};

const buildTimelineItems = (referenceAnalysis: Record<string, any> | null): TimelineItem[] => {
  const slots = Array.isArray(referenceAnalysis?.structural_slots)
    ? referenceAnalysis.structural_slots as Record<string, any>[]
    : [];

  if (slots.length > 0) {
    return slots.map((slot, index) => ({
      id: String(slot.slot_id ?? `slot_${index + 1}`),
      role: String(slot.role ?? 'develop'),
      title: String(slot.slot_id ?? `slot_${index + 1}`),
      startTime: Number(slot.start_time ?? 0),
      endTime: Number(slot.end_time ?? 0),
      duration: Number(slot.duration ?? Math.max(0, Number(slot.end_time ?? 0) - Number(slot.start_time ?? 0))),
      summary: String(slot.information_function ?? slot.creative_function ?? '暂无描述'),
      source: slot,
    }));
  }

  const paragraphs = Array.isArray(referenceAnalysis?.script_structure?.paragraphs)
    ? referenceAnalysis.script_structure.paragraphs as Record<string, any>[]
    : [];

  return paragraphs.map((paragraph, index) => {
    const startTime = Number(paragraph.start_time ?? 0);
    const endTime = Number(paragraph.end_time ?? startTime);
    return {
      id: `paragraph_${index + 1}`,
      role: String(paragraph.type ?? 'develop'),
      title: String(paragraph.type ?? `slot_${index + 1}`),
      startTime,
      endTime,
      duration: Math.max(0, endTime - startTime),
      summary: String(paragraph.content_summary ?? '暂无摘要'),
      source: paragraph,
    };
  });
};

const buildBeatMarkers = (timelineItems: TimelineItem[]): BeatMarker[] => (
  timelineItems.map((item) => ({
    id: `beat_${item.id}`,
    time: item.startTime,
    label: getBeatLabel(item.source.audio_sync?.beat_position),
    color: getBeatColor(item.source.audio_sync?.beat_position),
  }))
);

const buildTransitionMarkers = (timelineItems: TimelineItem[]): TransitionMarker[] => (
  timelineItems.map((item) => ({
    id: `transition_${item.id}`,
    startTime: item.endTime,
    endTime: Math.min(item.endTime + Math.max(item.duration * 0.18, 0.3), item.endTime + 0.9),
    label: getTransitionLabel(item.source.transition_out),
    color: getTransitionTone(item.source.transition_out),
  }))
);

const buildTransitionEvents = (referenceAnalysis: Record<string, any> | null): TransitionEventItem[] => {
  const events = Array.isArray(referenceAnalysis?.transition_events)
    ? referenceAnalysis.transition_events as Record<string, any>[]
    : [];

  return events.map((event, index) => ({
    id: String(event.event_id ?? `transition_event_${index + 1}`),
    atTime: Number(event.at_time ?? 0),
    transitionType: String(event.transition_type ?? 'cut'),
    fromShotId: String(event.from_shot_id ?? '-'),
    toShotId: String(event.to_shot_id ?? '-'),
    fromSummary: String(event.from_summary ?? '-'),
    toSummary: String(event.to_summary ?? '-'),
    strength: String(event.strength ?? 'medium'),
    purpose: String(event.purpose ?? '-'),
  }));
};

interface ShotSegmentItem {
  id: string;
  startTime: number;
  endTime: number;
  duration: number;
  summary: string;
  pace: string;
  transitionIn: string;
  transitionOut: string;
}

const buildShotSegments = (referenceAnalysis: Record<string, any> | null): ShotSegmentItem[] => {
  const shots = Array.isArray(referenceAnalysis?.shot_segments)
    ? referenceAnalysis.shot_segments as Record<string, any>[]
    : [];

  return shots.map((shot, index) => ({
    id: String(shot.shot_id ?? `shot_${index + 1}`),
    startTime: Number(shot.start_time ?? 0),
    endTime: Number(shot.end_time ?? 0),
    duration: Math.max(0, Number(shot.end_time ?? 0) - Number(shot.start_time ?? 0)),
    summary: String(shot.summary ?? '暂无镜头描述'),
    pace: String(shot.pace ?? 'medium'),
    transitionIn: String(shot.transition_in ?? 'cut'),
    transitionOut: String(shot.transition_out ?? 'cut'),
  }));
};

export const SampleVideoTabContent: React.FC<SampleVideoTabContentProps> = ({
  currentJobId,
  activeVideo,
  videoList,
  selectedReferenceVideoId,
  referenceAnalysis,
}) => {
  const [isSavingToKB, setIsSavingToKB] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const selectedReferenceVideo = videoList.find((video) => video.id === selectedReferenceVideoId)
    ?? videoList.find((video) => video.is_reference)
    ?? activeVideo;

  const basicInfo = referenceAnalysis?.video_basic_info as Record<string, any> | undefined;
  const rhythmCurve = Array.isArray(referenceAnalysis?.rhythm_curve)
    ? referenceAnalysis.rhythm_curve as Record<string, any>[]
    : [];
  const timelineItems = buildTimelineItems(referenceAnalysis);
  const beatMarkers = buildBeatMarkers(timelineItems);
  const transitionMarkers = buildTransitionMarkers(timelineItems);
  const transitionEvents = buildTransitionEvents(referenceAnalysis);
  const shotSegments = buildShotSegments(referenceAnalysis);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(timelineItems[0]?.id ?? null);
  const [selectedTransitionEventId, setSelectedTransitionEventId] = useState<string | null>(transitionEvents[0]?.id ?? null);
  const [selectedShotId, setSelectedShotId] = useState<string | null>(shotSegments[0]?.id ?? null);

  useEffect(() => {
    setSelectedNodeId(timelineItems[0]?.id ?? null);
  }, [selectedReferenceVideo?.id, referenceAnalysis, timelineItems.length]);

  useEffect(() => {
    setSelectedTransitionEventId(transitionEvents[0]?.id ?? null);
  }, [selectedReferenceVideo?.id, referenceAnalysis, transitionEvents.length]);

  useEffect(() => {
    setSelectedShotId(shotSegments[0]?.id ?? null);
  }, [selectedReferenceVideo?.id, referenceAnalysis, shotSegments.length]);

  const selectedNode = timelineItems.find((item) => item.id === selectedNodeId) ?? timelineItems[0] ?? null;
  const selectedTransitionEvent = transitionEvents.find((item) => item.id === selectedTransitionEventId) ?? transitionEvents[0] ?? null;
  const totalDuration = Number(
    basicInfo?.core_content_effective_duration_seconds
    ?? basicInfo?.file_total_duration_seconds
    ?? selectedReferenceVideo?.duration
    ?? 0,
  );

  const jumpToTime = (seconds: number) => {
    if (!videoRef.current || !Number.isFinite(seconds)) return;
    videoRef.current.currentTime = Math.max(0, seconds);
    void videoRef.current.play().catch(() => undefined);
  };

  const handleTimeUpdate = () => {
    if (!videoRef.current || timelineItems.length === 0) return;
    const currentTime = videoRef.current.currentTime;
    const activeNode = timelineItems.find((item) => currentTime >= item.startTime && currentTime <= item.endTime);
    if (activeNode && activeNode.id !== selectedNodeId) {
      setSelectedNodeId(activeNode.id);
    }
  };

  return (
    <div style={{ backgroundColor: 'var(--color-neutral-100)' }}>
      <div style={{ aspectRatio: '16 / 9', backgroundColor: '#1a1a2e' }}>
        {selectedReferenceVideo ? (
          <video
            ref={videoRef}
            controls
            src={selectedReferenceVideo.url}
            onTimeUpdate={handleTimeUpdate}
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        ) : (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ color: 'white', fontSize: 18, opacity: 0.7 }}>等待选择样例视频</span>
          </div>
        )}
      </div>

      <div style={{ padding: '20px 24px', display: 'grid', gap: 18 }}>
        <section style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start', marginBottom: 16, flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <h3 style={{ margin: 0, marginBottom: 6 }}>多维参考时间线</h3>
                <div style={{ fontSize: 13, color: 'var(--color-neutral-600)' }}>
                  将参考视频拆成多条观察维度：结构槽位、BGM卡点、转场切换、节奏热度。这样后续素材匹配不必只盯一条时间线。
                </div>
              </div>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                <span style={{ color: 'var(--color-neutral-600)', fontSize: 12 }}>类型：{String(basicInfo?.type_label ?? '-')}</span>
                <span style={{ color: 'var(--color-neutral-600)', fontSize: 12 }}>总时长：{formatSeconds(basicInfo?.file_total_duration_seconds)}</span>
                <span style={{ color: 'var(--color-neutral-600)', fontSize: 12 }}>有效时长：{formatSeconds(basicInfo?.core_content_effective_duration_seconds)}</span>
                <span style={{ color: 'var(--color-neutral-600)', fontSize: 12 }}>槽位数：{timelineItems.length}</span>
                {referenceAnalysis && timelineItems.length > 0 ? (
                  <button
                    onClick={async () => {
                      if (!currentJobId) {
                        alert("请先创建任务");
                        return;
                      }
                      setIsSavingToKB(true);
                      try {
                        const res = await fetch(`/api/orchestration/jobs/${currentJobId}/save-to-knowledge-base`, {
                          method: "POST",
                        });
                        const data = await res.json();
                        if (data.success) {
                          alert(`✅ 已成功沉淀到知识库！\nstyle_id: ${data.style_id}\n模板文件: ${data.target_file}`);
                        } else {
                          alert(`❌ 沉淀失败: ${data.detail || JSON.stringify(data)}`);
                        }
                      } catch (err) {
                        console.error('[SampleVideoTab] save to kb failed:', err);
                        alert(`❌ 沉淀失败: ${err}`);
                      } finally {
                        setIsSavingToKB(false);
                      }
                    }}
                    disabled={isSavingToKB || !currentJobId}
                    style={{
                      padding: '7px 14px',
                      borderRadius: 10,
                      border: 'none',
                      backgroundColor: isSavingToKB ? 'var(--color-primary-200)' : 'var(--color-primary-500)',
                      color: 'white',
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: isSavingToKB ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {isSavingToKB ? '⏳ 沉淀中...' : '💾 沉淀该样例到知识库'}
                  </button>
                ) : null}
              </div>
            </div>

          {timelineItems.length > 0 && totalDuration > 0 ? (
            <div style={{ display: 'grid', gap: 18 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--color-neutral-500)' }}>
                <span>0.0s</span>
                <span>{formatSeconds(totalDuration)}</span>
              </div>

              <div style={{ display: 'grid', gap: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#475569' }}>结构槽位线</div>
                <div style={{ position: 'relative', minHeight: 120, borderRadius: 18, padding: '14px 8px 8px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                  <div style={{ position: 'absolute', left: 12, right: 12, top: 24, height: 6, borderRadius: 999, backgroundColor: '#e5e7eb' }} />
                  {timelineItems.map((item) => {
                    const left = `${Math.min(100, Math.max(0, (item.startTime / totalDuration) * 100))}%`;
                    const width = `${Math.max(10, (Math.max(item.duration, 0.35) / totalDuration) * 100)}%`;
                    const isActive = selectedNode?.id === item.id;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => {
                          setSelectedNodeId(item.id);
                          jumpToTime(item.startTime);
                        }}
                        style={{
                          position: 'absolute',
                          left,
                          top: isActive ? 36 : 46,
                          width,
                          minWidth: 104,
                          transform: 'translateX(-6px)',
                          border: isActive ? '2px solid #0f172a' : '1px solid rgba(15, 23, 42, 0.08)',
                          borderRadius: 16,
                          padding: '10px 10px 8px',
                          backgroundColor: isActive ? '#fff' : '#ffffff',
                          boxShadow: isActive ? '0 10px 24px rgba(15, 23, 42, 0.12)' : 'none',
                          cursor: 'pointer',
                          textAlign: 'left',
                        }}
                      >
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                          <span style={{ width: 10, height: 10, borderRadius: 999, backgroundColor: getRoleColor(item.role), display: 'inline-block' }} />
                          <span style={{ fontSize: 11, fontWeight: 700, color: '#0f172a' }}>{getRoleLabel(item.role)}</span>
                        </div>
                        <div style={{ fontSize: 12, fontWeight: 700, color: '#111827', marginBottom: 4 }}>{item.title}</div>
                        <div style={{ fontSize: 11, color: '#64748b' }}>{formatSeconds(item.startTime)} - {formatSeconds(item.endTime)}</div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div style={{ display: 'grid', gap: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#475569' }}>BGM卡点线</div>
                <div style={{ position: 'relative', height: 76, borderRadius: 18, padding: '10px 12px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                  <div style={{ position: 'absolute', left: 12, right: 12, top: 37, height: 2, borderRadius: 999, backgroundColor: '#dbe4ef' }} />
                  {beatMarkers.map((marker, index) => {
                    const left = `${Math.min(100, Math.max(0, (marker.time / totalDuration) * 100))}%`;
                    return (
                      <button
                        key={marker.id}
                        type="button"
                        onClick={() => jumpToTime(marker.time)}
                        style={{
                          position: 'absolute',
                          left,
                          top: 16 + (index % 2) * 20,
                          transform: 'translateX(-50%)',
                          border: 'none',
                          backgroundColor: 'transparent',
                          cursor: 'pointer',
                          padding: 0,
                        }}
                      >
                        <div style={{ width: 12, height: 12, borderRadius: 999, backgroundColor: marker.color, border: '2px solid white', boxShadow: '0 2px 6px rgba(15, 23, 42, 0.12)', margin: '0 auto 6px' }} />
                        <div style={{ whiteSpace: 'nowrap', fontSize: 10, fontWeight: 700, color: marker.color }}>{marker.label}</div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div style={{ display: 'grid', gap: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#475569' }}>转场切换线</div>
                <div style={{ position: 'relative', height: 72, borderRadius: 18, padding: '12px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                  <div style={{ position: 'absolute', left: 12, right: 12, top: 32, height: 8, borderRadius: 999, backgroundColor: '#e5e7eb' }} />
                  {transitionMarkers.map((marker) => {
                    const left = `${Math.min(100, Math.max(0, (marker.startTime / totalDuration) * 100))}%`;
                    const width = `${Math.max(3, ((Math.max(marker.endTime - marker.startTime, 0.15)) / totalDuration) * 100)}%`;
                    return (
                      <div
                        key={marker.id}
                        title={marker.label}
                        style={{
                          position: 'absolute',
                          left,
                          top: 24,
                          width,
                          minWidth: 20,
                          height: 24,
                          transform: 'translateX(-4px)',
                          borderRadius: 999,
                          backgroundColor: marker.color,
                          opacity: 0.9,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: 'white',
                          fontSize: 10,
                          fontWeight: 700,
                          padding: '0 8px',
                        }}
                      >
                        {marker.label}
                      </div>
                    );
                  })}
                </div>
              </div>

              {shotSegments.length > 0 && (
                <div style={{ display: 'grid', gap: 12 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#475569' }}>原始镜头切分线</div>
                  <div style={{ position: 'relative', minHeight: 120, borderRadius: 18, padding: '14px 8px 8px', backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0' }}>
                    <div style={{ position: 'absolute', left: 12, right: 12, top: 24, height: 6, borderRadius: 999, backgroundColor: '#dcfce7' }} />
                    {shotSegments.map((item) => {
                      const left = `${Math.min(100, Math.max(0, (item.startTime / totalDuration) * 100))}%`;
                      const width = `${Math.max(10, (Math.max(item.duration, 0.35) / totalDuration) * 100)}%`;
                      const isActive = selectedShotId === item.id;
                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => {
                            setSelectedShotId(item.id);
                            jumpToTime(item.startTime);
                          }}
                          style={{
                            position: 'absolute',
                            left,
                            top: isActive ? 36 : 46,
                            width,
                            minWidth: 104,
                            transform: 'translateX(-6px)',
                            border: isActive ? '2px solid #15803d' : '1px solid rgba(22, 163, 74, 0.12)',
                            borderRadius: 16,
                            padding: '10px 10px 8px',
                            backgroundColor: isActive ? '#ecfdf5' : '#ffffff',
                            boxShadow: isActive ? '0 10px 24px rgba(22, 163, 74, 0.12)' : 'none',
                            cursor: 'pointer',
                            textAlign: 'left',
                          }}
                        >
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                            <span style={{ width: 10, height: 10, borderRadius: 999, backgroundColor: paceColor(item.pace), display: 'inline-block' }} />
                            <span style={{ fontSize: 11, fontWeight: 700, color: '#0f172a' }}>{item.id}</span>
                          </div>
                          <div style={{ fontSize: 12, fontWeight: 700, color: '#111827', marginBottom: 4 }}>{item.pace === 'fast' ? '快节奏' : item.pace === 'slow' ? '慢节奏' : item.pace}</div>
                          <div style={{ fontSize: 11, color: '#64748b' }}>{formatSeconds(item.startTime)} - {formatSeconds(item.endTime)}</div>
                        </button>
                      );
                    })}
                  </div>
                  <div style={{ padding: 14, borderRadius: 14, backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0' }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', marginBottom: 8 }}>镜头详情</div>
                    {shotSegments.find(s => s.id === selectedShotId) ? (
                      <div style={{ display: 'grid', gap: 8, fontSize: 13, color: '#334155' }}>
                        <div>镜头ID：{selectedShotId}</div>
                        <div>时间范围：{formatSeconds(shotSegments.find(s => s.id === selectedShotId)?.startTime)} - {formatSeconds(shotSegments.find(s => s.id === selectedShotId)?.endTime)}</div>
                        <div>节奏：{shotSegments.find(s => s.id === selectedShotId)?.pace === 'fast' ? '快节奏' : shotSegments.find(s => s.id === selectedShotId)?.pace === 'slow' ? '慢节奏' : shotSegments.find(s => s.id === selectedShotId)?.pace}</div>
                        <div>入转场：{getTransitionLabel(shotSegments.find(s => s.id === selectedShotId)?.transitionIn)}</div>
                        <div>出转场：{getTransitionLabel(shotSegments.find(s => s.id === selectedShotId)?.transitionOut)}</div>
                        <div>镜头摘要：{shotSegments.find(s => s.id === selectedShotId)?.summary}</div>
                      </div>
                    ) : (
                      <div style={{ fontSize: 13, color: '#94a3b8' }}>暂无选中镜头详情。</div>
                    )}
                  </div>
                </div>
              )}

              {transitionEvents.length > 0 && (
                <div style={{ display: 'grid', gap: 12 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#475569' }}>逐次转场事件</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(300px, 1fr)', gap: 12 }}>
                    <div style={{ display: 'grid', gap: 10 }}>
                      {transitionEvents.map((event) => {
                        const isActive = event.id === selectedTransitionEvent?.id;
                        return (
                          <button
                            key={event.id}
                            type="button"
                            onClick={() => {
                              setSelectedTransitionEventId(event.id);
                              jumpToTime(event.atTime);
                            }}
                            style={{
                              border: isActive ? '1px solid #111827' : '1px solid #e2e8f0',
                              backgroundColor: isActive ? '#f8fafc' : 'white',
                              borderRadius: 14,
                              padding: '12px 14px',
                              textAlign: 'left',
                              cursor: 'pointer',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 6 }}>
                              <div style={{ fontSize: 14, fontWeight: 700, color: getTransitionTone(event.transitionType) }}>
                                {getTransitionLabel(event.transitionType)}
                              </div>
                              <div style={{ fontSize: 12, color: '#64748b' }}>{formatSeconds(event.atTime)}</div>
                            </div>
                            <div style={{ fontSize: 12, color: '#334155', marginBottom: 4 }}>
                              {event.fromShotId} {'->'} {event.toShotId}
                            </div>
                            <div style={{ fontSize: 12, color: '#64748b' }}>
                              强度 {event.strength} | {event.purpose}
                            </div>
                          </button>
                        );
                      })}
                    </div>

                    <div style={{ padding: 14, borderRadius: 14, backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', marginBottom: 8 }}>转场事件详情</div>
                      {selectedTransitionEvent ? (
                        <div style={{ display: 'grid', gap: 8, fontSize: 13, color: '#334155' }}>
                          <div>时间点：{formatSeconds(selectedTransitionEvent.atTime)}</div>
                          <div>转场方式：{getTransitionLabel(selectedTransitionEvent.transitionType)}</div>
                          <div>前镜头：{selectedTransitionEvent.fromShotId}</div>
                          <div>后镜头：{selectedTransitionEvent.toShotId}</div>
                          <div>强度：{selectedTransitionEvent.strength}</div>
                          <div>用途：{selectedTransitionEvent.purpose}</div>
                          <div>前画面摘要：{selectedTransitionEvent.fromSummary}</div>
                          <div>后画面摘要：{selectedTransitionEvent.toSummary}</div>
                        </div>
                      ) : (
                        <div style={{ fontSize: 13, color: '#94a3b8' }}>暂无转场事件详情。</div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {rhythmCurve.length > 0 && (
                <div style={{ display: 'grid', gap: 10 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#475569' }}>节奏热度线</div>
                  <div style={{ position: 'relative', height: 36, borderRadius: 999, backgroundColor: '#eef2ff', overflow: 'hidden' }}>
                    {rhythmCurve.map((segment, index) => {
                      const timeRange = Array.isArray(segment.time_range) ? segment.time_range : [0, 0];
                      const start = Number(timeRange[0] ?? 0);
                      const end = Number(timeRange[1] ?? start);
                      const left = `${Math.min(100, Math.max(0, (start / totalDuration) * 100))}%`;
                      const width = `${Math.max(6, (Math.max(end - start, 0.3) / totalDuration) * 100)}%`;
                      const pace = String(segment.pace ?? 'medium');
                      return (
                        <div
                          key={`${pace}-${index}`}
                          title={`${pace} | ${String(segment.purpose ?? '')}`}
                          style={{
                            position: 'absolute',
                            left,
                            top: 0,
                            bottom: 0,
                            width,
                            backgroundColor: paceColor(pace),
                            opacity: 0.85,
                          }}
                        />
                      );
                    })}
                  </div>
                  <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', fontSize: 12, color: '#64748b' }}>
                    {rhythmCurve.map((segment, index) => (
                      <span key={`legend-${index}`}>
                        {formatSeconds(segment.time_range?.[0])} - {formatSeconds(segment.time_range?.[1])}: {String(segment.pace ?? 'medium')} / {String(segment.purpose ?? '-')}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <span style={{ color: 'var(--color-neutral-500)' }}>等待参考分析结果，生成多维时间线。</span>
          )}
        </section>

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.5fr) minmax(320px, 1fr)', gap: 18, alignItems: 'start' }}>
          <section style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
            <h3 style={{ margin: 0, marginBottom: 14 }}>槽位详情</h3>
            {selectedNode ? (
              <div style={{ display: 'grid', gap: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                  <div>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <span style={{ width: 10, height: 10, borderRadius: 999, backgroundColor: getRoleColor(selectedNode.role), display: 'inline-block' }} />
                      <span style={{ fontSize: 12, color: '#475569', fontWeight: 700 }}>{getRoleLabel(selectedNode.role)}</span>
                    </div>
                    <div style={{ fontSize: 22, fontWeight: 700, color: '#0f172a' }}>{selectedNode.title}</div>
                    <div style={{ marginTop: 6, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <span style={{ padding: '4px 8px', borderRadius: 999, backgroundColor: '#eff6ff', color: '#1d4ed8', fontSize: 11, fontWeight: 700 }}>
                        卡点 {getBeatLabel(selectedNode.source.audio_sync?.beat_position)}
                      </span>
                      <span style={{ padding: '4px 8px', borderRadius: 999, backgroundColor: '#f8fafc', color: getTransitionTone(selectedNode.source.transition_out), fontSize: 11, fontWeight: 700 }}>
                        转场 {getTransitionLabel(selectedNode.source.transition_out ?? '-')}
                      </span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => jumpToTime(selectedNode.startTime)}
                    style={{
                      border: 'none',
                      backgroundColor: '#111827',
                      color: 'white',
                      borderRadius: 999,
                      padding: '10px 14px',
                      cursor: 'pointer',
                      fontSize: 12,
                      fontWeight: 700,
                    }}
                  >
                    跳到 {formatSeconds(selectedNode.startTime)}
                  </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 10 }}>
                  {[
                    { label: '开始', value: formatSeconds(selectedNode.startTime) },
                    { label: '结束', value: formatSeconds(selectedNode.endTime) },
                    { label: '时长', value: formatSeconds(selectedNode.duration) },
                    { label: '重要度', value: String(selectedNode.source.importance ?? '-') },
                  ].map((item) => (
                    <div key={item.label} style={{ padding: 12, borderRadius: 12, backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{item.label}</div>
                      <div style={{ fontSize: 15, fontWeight: 700, color: '#0f172a' }}>{item.value}</div>
                    </div>
                  ))}
                </div>

                <div style={{ display: 'grid', gap: 12 }}>
                  <div style={{ padding: 14, borderRadius: 14, backgroundColor: '#fff7ed', border: '1px solid #fed7aa' }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#9a3412', marginBottom: 6 }}>创作目标</div>
                    <div style={{ fontSize: 14, color: '#7c2d12', marginBottom: 6 }}>
                      {String(selectedNode.source.creative_function ?? selectedNode.summary ?? '-')}
                    </div>
                    <div style={{ fontSize: 13, color: '#9a3412' }}>
                      {String(selectedNode.source.information_function ?? '-')}
                    </div>
                  </div>

                  <div style={{ padding: 14, borderRadius: 14, backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#334155', marginBottom: 8 }}>画面要求</div>
                    <div style={{ display: 'grid', gap: 8, fontSize: 14, color: '#334155' }}>
                      <div>视觉类型：{Array.isArray(selectedNode.source.required_visual_type) ? selectedNode.source.required_visual_type.join(' / ') : String(selectedNode.source.required_visual_type ?? '-')}</div>
                      <div>镜头运动：{String(selectedNode.source.required_motion ?? '-')}</div>
                      <div>景别：{String(selectedNode.source.shot_size ?? '-')}</div>
                    </div>
                  </div>

                  <div style={{ padding: 14, borderRadius: 14, backgroundColor: '#f5f3ff', border: '1px solid #ddd6fe' }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#5b21b6', marginBottom: 8 }}>字幕与声音</div>
                    <div style={{ display: 'grid', gap: 8, fontSize: 14, color: '#5b21b6' }}>
                      <div>字幕需求：{selectedNode.source.caption_requirement?.need_caption ? '需要' : '可选/无'}</div>
                      <div>字幕样式：{String(selectedNode.source.caption_requirement?.style ?? '-')}</div>
                      <div>字幕位置：{String(selectedNode.source.caption_requirement?.position ?? '-')}</div>
                      <div>语义角色：{String(selectedNode.source.caption_requirement?.semantic_role ?? '-')}</div>
                      <div>卡点位置：{getBeatLabel(selectedNode.source.audio_sync?.beat_position)}</div>
                      <div>SFX：{String(selectedNode.source.audio_sync?.sfx ?? '-')}</div>
                    </div>
                  </div>

                  <div style={{ padding: 14, borderRadius: 14, backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0' }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#166534', marginBottom: 8 }}>转场与迁移风险</div>
                    <div style={{ display: 'grid', gap: 8, fontSize: 14, color: '#166534' }}>
                      <div>转场方式：{getTransitionLabel(selectedNode.source.transition_out ?? '-')}</div>
                      <div>迁移风险：{String(selectedNode.source.copy_risk ?? '-')}</div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <span style={{ color: 'var(--color-neutral-500)' }}>暂无槽位详情。</span>
            )}
          </section>

          <section style={{ display: 'grid', gap: 14 }}>
            <div style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
              <h3 style={{ margin: 0, marginBottom: 12 }}>全局风格摘要</h3>
              <div style={{ display: 'grid', gap: 12 }}>
                <div style={{ padding: 12, borderRadius: 12, backgroundColor: '#f8fafc' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', marginBottom: 6 }}>脚本摘要</div>
                  <div style={{ fontSize: 14, color: '#0f172a' }}>{String(referenceAnalysis?.script_structure?.summary ?? '暂无')}</div>
                </div>
                <div style={{ padding: 12, borderRadius: 12, backgroundColor: '#fefce8' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#854d0e', marginBottom: 6 }}>字幕风格</div>
                  <div style={{ fontSize: 13, color: '#854d0e' }}>
                    {String(referenceAnalysis?.caption_style_template?.subtitle_density ?? '-')} / {String(referenceAnalysis?.caption_style_template?.font_style ?? '-')}
                  </div>
                </div>
                <div style={{ padding: 12, borderRadius: 12, backgroundColor: '#eef2ff' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#3730a3', marginBottom: 6 }}>转场风格</div>
                  <div style={{ fontSize: 13, color: '#3730a3', marginBottom: 4 }}>
                    {Array.isArray(referenceAnalysis?.transition_style_template?.main_transition_types)
                      ? referenceAnalysis.transition_style_template.main_transition_types.map((item: unknown) => getTransitionLabel(item)).join(' / ')
                      : '-'}
                  </div>
                  <div style={{ fontSize: 12, color: '#4338ca' }}>{String(referenceAnalysis?.transition_style_template?.usage_rule ?? '暂无说明')}</div>
                </div>
                <div style={{ padding: 12, borderRadius: 12, backgroundColor: '#ecfdf5' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#166534', marginBottom: 6 }}>包装风格</div>
                  <div style={{ fontSize: 13, color: '#166534', marginBottom: 4 }}>
                    {Array.isArray(referenceAnalysis?.packaging_style_template?.stickers)
                      ? referenceAnalysis.packaging_style_template.stickers.join(' / ')
                      : '-'}
                  </div>
                  <div style={{ fontSize: 12, color: '#15803d' }}>{String(referenceAnalysis?.packaging_style_template?.cover_style ?? '暂无说明')}</div>
                </div>
              </div>
            </div>

            <div style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
              <h3 style={{ margin: 0, marginBottom: 12 }}>迁移规则</h3>
              <div style={{ display: 'grid', gap: 12 }}>
                {[
                  { title: '必须保留', items: referenceAnalysis?.transfer_rules?.must_keep },
                  { title: '可以适配', items: referenceAnalysis?.transfer_rules?.can_adapt },
                  { title: '禁止照搬', items: referenceAnalysis?.transfer_rules?.must_not_copy },
                ].map((group) => (
                  <div key={group.title}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', marginBottom: 6 }}>{group.title}</div>
                    <div style={{ display: 'grid', gap: 6 }}>
                      {Array.isArray(group.items) && group.items.length > 0 ? group.items.map((item: string, index: number) => (
                        <div key={`${group.title}-${index}`} style={{ fontSize: 13, color: '#0f172a', padding: '8px 10px', borderRadius: 10, backgroundColor: '#f8fafc' }}>
                          {item}
                        </div>
                      )) : (
                        <span style={{ fontSize: 13, color: '#94a3b8' }}>暂无</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
              <h3 style={{ margin: 0, marginBottom: 12 }}>迁移建议与风险</h3>
              <div style={{ display: 'grid', gap: 10 }}>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', marginBottom: 6 }}>迁移建议</div>
                  <div style={{ display: 'grid', gap: 6 }}>
                    {Array.isArray(referenceAnalysis?.migration_suggestion) && referenceAnalysis.migration_suggestion.length > 0 ? referenceAnalysis.migration_suggestion.map((item: string, index: number) => (
                      <div key={`suggestion-${index}`} style={{ fontSize: 13, color: '#0f172a', padding: '8px 10px', borderRadius: 10, backgroundColor: '#f8fafc' }}>
                        {item}
                      </div>
                    )) : (
                      <span style={{ fontSize: 13, color: '#94a3b8' }}>暂无</span>
                    )}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', marginBottom: 6 }}>风险提示</div>
                  <div style={{ display: 'grid', gap: 6 }}>
                    {Array.isArray(referenceAnalysis?.risk_notes) && referenceAnalysis.risk_notes.length > 0 ? referenceAnalysis.risk_notes.map((item: string, index: number) => (
                      <div key={`risk-${index}`} style={{ fontSize: 13, color: '#7f1d1d', padding: '8px 10px', borderRadius: 10, backgroundColor: '#fef2f2' }}>
                        {item}
                      </div>
                    )) : (
                      <span style={{ fontSize: 13, color: '#94a3b8' }}>暂无风险提示</span>
                    )}
                  </div>
                </div>
                <div style={{ fontSize: 12, color: '#64748b' }}>模型置信度：{String(referenceAnalysis?.confidence ?? '-')}</div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};
