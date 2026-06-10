import React, { useEffect, useMemo, useRef, useState } from 'react';
import type { UploadedVideo } from '../types';

interface MaterialVideoTabContentProps {
  activeVideo: UploadedVideo | null;
  videoList: UploadedVideo[];
  assetIndex: Record<string, any> | null;
  slotMatches: Record<string, any> | null;
  resolvedGaps: Record<string, any> | null;
  editTimeline: Record<string, any> | null;
}

const formatSeconds = (value: unknown) => {
  const num = Number(value);
  if (!Number.isFinite(num)) return '--';
  return `${num.toFixed(1)}s`;
};

const scoreColor = (score: number) => {
  if (score >= 0.85) return '#166534';
  if (score >= 0.7) return '#92400e';
  return '#991b1b';
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

export const MaterialVideoTabContent: React.FC<MaterialVideoTabContentProps> = ({
  activeVideo,
  videoList,
  assetIndex,
  slotMatches,
  resolvedGaps,
  editTimeline,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const materialVideos = videoList.filter((video) => !video.is_reference);
  const playbackVideo = activeVideo && !activeVideo.is_reference ? activeVideo : (materialVideos[0] ?? null);
  const assets = Array.isArray(assetIndex?.assets) ? assetIndex.assets as Record<string, any>[] : [];

  const activeAsset = useMemo(() => {
    if (!playbackVideo) {
      return assets[0] ?? null;
    }
    return assets.find((asset) => (
      asset.asset_id === playbackVideo.filename
      || asset.material_id === playbackVideo.filename
      || asset.asset_id === playbackVideo.originalFilename
      || asset.material_id === playbackVideo.originalFilename
    )) ?? assets[0] ?? null;
  }, [assets, playbackVideo]);

  const assetKeys = useMemo(() => {
    const keys = new Set<string>();
    [activeAsset?.asset_id, activeAsset?.material_id, playbackVideo?.filename, playbackVideo?.originalFilename]
      .filter((value): value is string => typeof value === 'string' && value.length > 0)
      .forEach((value) => keys.add(value));
    return keys;
  }, [activeAsset?.asset_id, activeAsset?.material_id, playbackVideo?.filename, playbackVideo?.originalFilename]);

  const segments = Array.isArray(activeAsset?.segments) ? activeAsset.segments as Record<string, any>[] : [];
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(null);

  useEffect(() => {
    setSelectedSegmentId(segments[0]?.segment_id ?? null);
  }, [activeAsset, segments.length]);

  const selectedSegment = segments.find((segment) => segment.segment_id === selectedSegmentId) ?? segments[0] ?? null;
  const slotAssignments = Array.isArray(slotMatches?.slot_assignments) ? slotMatches.slot_assignments as Record<string, any>[] : [];
  const timelineSegments = Array.isArray(editTimeline?.timeline) ? editTimeline.timeline as Record<string, any>[] : [];
  const resolvedGapList = Array.isArray(resolvedGaps?.resolved_gaps) ? resolvedGaps.resolved_gaps as Record<string, any>[] : [];

  const matchedSlotsForAsset = useMemo(() => (
    slotAssignments.filter((assignment) => {
      const candidate = assignment.selected_candidate as Record<string, any> | undefined;
      const assetId = candidate?.asset_id;
      return typeof assetId === 'string' && assetKeys.has(assetId);
    })
  ), [assetKeys, slotAssignments]);

  const timelineUsage = useMemo(() => (
    timelineSegments.filter((segment) => {
      const assetId = segment.asset_id;
      const assetPath = segment.asset_full_path;
      return (typeof assetId === 'string' && assetKeys.has(assetId))
        || (typeof assetPath === 'string' && playbackVideo?.storagePath === assetPath);
    })
  ), [assetKeys, playbackVideo?.storagePath, timelineSegments]);

  const resolvedGapsForAsset = useMemo(() => (
    resolvedGapList.filter((gap) => {
      const assetId = gap.resolution?.asset_ref?.asset_id;
      return typeof assetId === 'string' && assetKeys.has(assetId);
    })
  ), [assetKeys, resolvedGapList]);

  const jumpToSegment = (start: number) => {
    if (!videoRef.current || !Number.isFinite(start)) return;
    videoRef.current.currentTime = Math.max(0, start);
    void videoRef.current.play().catch(() => undefined);
  };

  return (
    <div style={{ backgroundColor: 'var(--color-neutral-100)' }}>
      <div style={{ aspectRatio: '16 / 9', backgroundColor: '#1a1a2e' }}>
        {playbackVideo ? (
          <video
            ref={videoRef}
            controls
            src={playbackVideo.url}
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        ) : (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ color: 'white', fontSize: 18, opacity: 0.7 }}>等待选择素材视频</span>
          </div>
        )}
      </div>

      <div style={{ padding: '20px 24px', display: 'grid', gap: 18 }}>
        <section style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start', marginBottom: 14 }}>
            <div>
              <h3 style={{ margin: 0, marginBottom: 6 }}>素材索引结果</h3>
              <div style={{ fontSize: 13, color: 'var(--color-neutral-600)' }}>
                当前素材会展示整体描述、适用角色，以及可剪辑片段的详细结构化分析。
              </div>
            </div>
            <span
              style={{
                padding: '6px 12px',
                borderRadius: 999,
                backgroundColor: 'var(--color-primary-50)',
                color: 'var(--color-primary-500)',
                fontSize: 12,
                fontWeight: 700,
              }}
            >
              {String(activeAsset?.media_type ?? 'video')}
            </span>
          </div>

          {activeAsset ? (
            <div style={{ display: 'grid', gap: 12 }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#0f172a' }}>
                {String(activeAsset.asset_id ?? activeAsset.material_id ?? playbackVideo?.filename ?? '当前素材')}
              </div>
              <div style={{ fontSize: 14, color: '#475569', lineHeight: 1.7 }}>
                {String(activeAsset.global_description ?? activeAsset.visual_description ?? '暂无整体描述')}
              </div>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', fontSize: 12 }}>
                <span style={{ padding: '6px 10px', borderRadius: 999, backgroundColor: '#f8fafc', color: '#334155' }}>
                  时长：{formatSeconds(activeAsset.duration)}
                </span>
                <span style={{ padding: '6px 10px', borderRadius: 999, backgroundColor: '#f8fafc', color: '#334155' }}>
                  内容类型：{String(activeAsset.content_type ?? '-')}
                </span>
                <span style={{ padding: '6px 10px', borderRadius: 999, backgroundColor: '#f8fafc', color: '#334155' }}>
                  置信度：{String(activeAsset.confidence ?? '-')}
                </span>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {(Array.isArray(activeAsset.tags) ? activeAsset.tags : []).map((tag: string, index: number) => (
                  <span key={`${tag}-${index}`} style={{ padding: '6px 10px', borderRadius: 999, backgroundColor: '#eef2ff', color: '#4338ca', fontSize: 12 }}>
                    {tag}
                  </span>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {(Array.isArray(activeAsset.suggested_usage) ? activeAsset.suggested_usage : []).map((usage: string, index: number) => (
                  <span key={`${usage}-${index}`} style={{ padding: '6px 10px', borderRadius: 999, backgroundColor: '#ecfdf5', color: '#166534', fontSize: 12 }}>
                    适合 {usage}
                  </span>
                ))}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 10 }}>
                {[
                  { label: '匹配插槽', value: matchedSlotsForAsset.length },
                  { label: '上时间线', value: timelineUsage.length },
                  { label: '补口复用', value: resolvedGapsForAsset.length },
                ].map((item) => (
                  <div key={item.label} style={{ padding: 12, borderRadius: 12, backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{item.label}</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: '#0f172a' }}>{item.value}</div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--color-neutral-500)' }}>等待 AssetIndexer 输出素材索引。</div>
          )}
        </section>

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.25fr) minmax(320px, 1fr)', gap: 18, alignItems: 'start' }}>
          <section style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
            <h3 style={{ marginTop: 0, marginBottom: 14 }}>可剪辑片段</h3>
            {segments.length > 0 ? (
              <div style={{ display: 'grid', gap: 10 }}>
                {segments.map((segment) => {
                  const isSelected = segment.segment_id === selectedSegment?.segment_id;
                  return (
                    <button
                      key={String(segment.segment_id)}
                      type="button"
                      onClick={() => {
                        setSelectedSegmentId(String(segment.segment_id));
                        jumpToSegment(Number(segment.start ?? 0));
                      }}
                      style={{
                        border: isSelected ? '1px solid var(--color-primary-500)' : '1px solid var(--color-neutral-200)',
                        backgroundColor: isSelected ? 'var(--color-primary-50)' : 'white',
                        borderRadius: 14,
                        padding: '12px 14px',
                        textAlign: 'left',
                        cursor: 'pointer',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginBottom: 6 }}>
                        <div style={{ fontSize: 14, fontWeight: 700, color: '#0f172a' }}>
                          {String(segment.segment_id ?? 'segment')}
                        </div>
                        <div style={{ fontSize: 12, color: '#475569' }}>
                          {formatSeconds(segment.start)} - {formatSeconds(segment.end)}
                        </div>
                      </div>
                      <div style={{ fontSize: 13, color: '#334155', marginBottom: 4 }}>
                        {String(segment.content_type ?? '-')} · {String(segment.action ?? '暂无动作说明')}
                      </div>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        {(Array.isArray(segment.best_for_roles) ? segment.best_for_roles : []).map((role: string, index: number) => (
                          <span key={`${role}-${index}`} style={{ padding: '4px 8px', borderRadius: 999, backgroundColor: '#ecfdf5', color: '#166534', fontSize: 11 }}>
                            {role}
                          </span>
                        ))}
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div style={{ color: 'var(--color-neutral-500)' }}>当前素材暂无片段结果。</div>
            )}
          </section>

          <section style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
            <h3 style={{ marginTop: 0, marginBottom: 14 }}>片段详情</h3>
            {selectedSegment ? (
              <div style={{ display: 'grid', gap: 12 }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#0f172a' }}>
                  {String(selectedSegment.segment_id ?? '片段')}
                </div>
                <div style={{ fontSize: 14, color: '#475569' }}>
                  {String(selectedSegment.scene ?? '-') } · {String(selectedSegment.shot_size ?? '-') } · {String(selectedSegment.camera_motion ?? '-')}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 10 }}>
                  {[
                    { label: '视觉质量', value: Number(selectedSegment.visual_quality ?? 0) },
                    { label: '光线质量', value: Number(selectedSegment.lighting_quality ?? 0) },
                    { label: '主体清晰度', value: Number(selectedSegment.subject_clarity ?? 0) },
                  ].map((item) => (
                    <div key={item.label} style={{ padding: 12, borderRadius: 12, backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{item.label}</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: scoreColor(item.value) }}>
                        {item.value.toFixed(2)}
                      </div>
                    </div>
                  ))}
                </div>
                <div style={{ display: 'grid', gap: 8, fontSize: 14, color: '#334155' }}>
                  <div>主体：{Array.isArray(selectedSegment.subjects) ? selectedSegment.subjects.join(' / ') : '-'}</div>
                  <div>动作：{String(selectedSegment.action ?? '-')}</div>
                  <div>运动强度：{String(selectedSegment.motion_intensity ?? '-')}</div>
                  <div>竖屏适配：{String(selectedSegment.orientation_fit ?? '-')}</div>
                  <div>音频可用：{selectedSegment.audio_available ? '是' : '否'}</div>
                </div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', marginBottom: 6 }}>适合槽位</div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {(Array.isArray(selectedSegment.best_for_slot_types) ? selectedSegment.best_for_slot_types : []).map((type: string, index: number) => (
                      <span key={`${type}-${index}`} style={{ padding: '6px 10px', borderRadius: 999, backgroundColor: '#eef2ff', color: '#4338ca', fontSize: 12 }}>
                        {type}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', marginBottom: 6 }}>可复用方式</div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {(Array.isArray(selectedSegment.can_reuse_by) ? selectedSegment.can_reuse_by : []).map((mode: string, index: number) => (
                      <span key={`${mode}-${index}`} style={{ padding: '6px 10px', borderRadius: 999, backgroundColor: '#fefce8', color: '#854d0e', fontSize: 12 }}>
                        {mode}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', marginBottom: 6 }}>风险提示</div>
                  <div style={{ display: 'grid', gap: 6 }}>
                    {(Array.isArray(selectedSegment.risks) ? selectedSegment.risks : []).length > 0 ? (
                      (selectedSegment.risks as string[]).map((risk, index) => (
                        <div key={`${risk}-${index}`} style={{ padding: '8px 10px', borderRadius: 10, backgroundColor: '#fef2f2', color: '#991b1b', fontSize: 12 }}>
                          {risk}
                        </div>
                      ))
                    ) : (
                      <div style={{ color: '#94a3b8', fontSize: 12 }}>暂无明显风险</div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ color: 'var(--color-neutral-500)' }}>点击左侧片段可查看详情并跳转播放器。</div>
            )}
          </section>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 18, alignItems: 'start' }}>
          <section style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
            <h3 style={{ marginTop: 0, marginBottom: 14 }}>插槽匹配</h3>
            {matchedSlotsForAsset.length > 0 ? (
              <div style={{ display: 'grid', gap: 10 }}>
                {matchedSlotsForAsset.map((assignment, index) => (
                  <div key={String(assignment.slot_id ?? index)} style={{ padding: 12, borderRadius: 12, backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#0f172a' }}>
                      {String(assignment.slot_id ?? `slot_${index + 1}`)}
                    </div>
                    <div style={{ fontSize: 12, color: '#475569', marginTop: 4 }}>
                      {String(assignment.slot_role ?? '-')} | 匹配分 {String(assignment.match_score ?? '-')}
                    </div>
                    <div style={{ fontSize: 13, color: '#334155', marginTop: 6 }}>
                      {String(assignment.reason ?? '当前素材被选中用于该结构插槽。')}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: 'var(--color-neutral-500)' }}>当前素材还没有被 SlotMatcher 明确选中。</div>
            )}
          </section>

          <section style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
            <h3 style={{ marginTop: 0, marginBottom: 14 }}>时间线落位</h3>
            {timelineUsage.length > 0 ? (
              <div style={{ display: 'grid', gap: 10 }}>
                {timelineUsage.map((segment, index) => (
                  <div key={String(segment.clip_id ?? index)} style={{ padding: 12, borderRadius: 12, backgroundColor: '#eff6ff', border: '1px solid #bfdbfe' }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#1d4ed8' }}>
                      {String(segment.slot_id ?? segment.clip_id ?? `clip_${index + 1}`)}
                    </div>
                    <div style={{ fontSize: 12, color: '#1e3a8a', marginTop: 4 }}>
                      {formatSeconds(segment.start)} - {formatSeconds(segment.end)} | 源片段 {formatSeconds(segment.source_in)} - {formatSeconds(segment.source_out)}
                    </div>
                    <div style={{ fontSize: 13, color: '#334155', marginTop: 6 }}>
                      转场 {getTransitionLabel(segment.transition_out ?? 'cut')} | 运动 {String(segment.transform?.motion ?? 'none')}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: 'var(--color-neutral-500)' }}>EditPlanner 还没有把当前素材排进结果时间线。</div>
            )}
          </section>

          <section style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
            <h3 style={{ marginTop: 0, marginBottom: 14 }}>补口策略</h3>
            {resolvedGapsForAsset.length > 0 ? (
              <div style={{ display: 'grid', gap: 10 }}>
                {resolvedGapsForAsset.map((gap, index) => (
                  <div key={String(gap.slot_id ?? gap.slot ?? index)} style={{ padding: 12, borderRadius: 12, backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0' }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#166534' }}>
                      {String(gap.slot_id ?? gap.slot ?? `gap_${index + 1}`)}
                    </div>
                    <div style={{ fontSize: 12, color: '#166534', marginTop: 4 }}>
                      策略 {String(gap.chosen_strategy ?? gap.strategy ?? '-')} | 置信度 {String(gap.confidence ?? '-')}
                    </div>
                    <div style={{ fontSize: 13, color: '#334155', marginTop: 6 }}>
                      {String(gap.impact_on_template?.rhythm_change ?? '已使用当前素材参与补口。')}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: 'var(--color-neutral-500)' }}>当前素材还没有参与 GapResolver 的补口方案。</div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
};
