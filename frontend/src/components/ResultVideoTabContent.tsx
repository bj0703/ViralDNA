import React, { useEffect, useMemo, useState } from 'react';

interface ResultVideoTabContentProps {
  currentJobId: string | null;
  editTimeline: Record<string, any> | null;
  slotMatches: Record<string, any> | null;
  resolvedGaps: Record<string, any> | null;
  finalVideoMeta: Record<string, any> | null;
  initialActiveVariantId?: string | null;
  onActiveVariantChange?: (variantId: string) => void;
}

interface VariantOption {
  id: string;
  label: string;
}

const VARIANT_ORDER = ['structure', 'beat', 'transition', 'rhythm'] as const;
const VARIANT_LABELS: Record<string, string> = {
  structure: '结构优先版',
  beat: '卡点优先版',
  transition: '转场优先版',
  rhythm: '节奏优先版',
};

const getVariantPayload = (data: Record<string, any> | null, variantId: string | null) => {
  if (!data) return null;
  const variants = data.variants;
  if (variants && typeof variants === 'object') {
    const selected = variantId ? variants[variantId] : null;
    if (selected && typeof selected === 'object') return selected as Record<string, any>;
    const defaultVariantId = typeof data.default_variant_id === 'string' ? data.default_variant_id : 'structure';
    const fallback = variants[defaultVariantId];
    if (fallback && typeof fallback === 'object') return fallback as Record<string, any>;
  }
  return data;
};

const getVariantOutputMeta = (finalVideoMeta: Record<string, any> | null, variantId: string | null) => {
  if (!finalVideoMeta) return null;
  const outputs = Array.isArray(finalVideoMeta.outputs) ? finalVideoMeta.outputs as Record<string, any>[] : [];
  if (outputs.length === 0) return finalVideoMeta;
  if (variantId) {
    const selected = outputs.find((item) => item.variant_id === variantId);
    if (selected) return selected;
  }
  const defaultVariantId = typeof finalVideoMeta.default_variant_id === 'string' ? finalVideoMeta.default_variant_id : 'structure';
  return outputs.find((item) => item.variant_id === defaultVariantId) ?? outputs[0] ?? finalVideoMeta;
};

const getOutputUrl = (currentJobId: string | null, finalVideoMeta: Record<string, any> | null, variantId: string | null) => {
  const activeOutput = getVariantOutputMeta(finalVideoMeta, variantId);
  if (!currentJobId || !activeOutput?.output_path) {
    return null;
  }
  if (typeof activeOutput.output_url === 'string' && activeOutput.output_url) {
    const token = activeOutput.rendered_at ? `?t=${encodeURIComponent(String(activeOutput.rendered_at))}` : '';
    return `${activeOutput.output_url}${token}`;
  }
  const outputPath = String(activeOutput.output_path);
  const filename = outputPath.split(/[/\\]/).pop();
  if (!filename) {
    return null;
  }
  const token = activeOutput.rendered_at ? `?t=${encodeURIComponent(String(activeOutput.rendered_at))}` : '';
  return `/api/orchestration/jobs/${currentJobId}/outputs/${filename}${token}`;
};

const formatSeconds = (value: unknown) => {
  const num = Number(value);
  if (!Number.isFinite(num)) return '--';
  return `${num.toFixed(1)}s`;
};

const formatBytes = (value: unknown) => {
  const num = Number(value);
  if (!Number.isFinite(num) || num <= 0) return '--';
  if (num < 1024 * 1024) return `${(num / 1024).toFixed(1)} KB`;
  return `${(num / (1024 * 1024)).toFixed(2)} MB`;
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

const yesNo = (value: unknown) => value ? '是' : '否';

const safeArray = (value: unknown) => Array.isArray(value) ? value : [];

const scoreTone = (score: number) => {
  if (score >= 0.85) return { bg: '#ecfdf5', fg: '#166534' };
  if (score >= 0.7) return { bg: '#fefce8', fg: '#854d0e' };
  return { bg: '#fef2f2', fg: '#991b1b' };
};

export const ResultVideoTabContent: React.FC<ResultVideoTabContentProps> = ({
  currentJobId,
  editTimeline,
  slotMatches,
  resolvedGaps,
  finalVideoMeta,
  initialActiveVariantId,
  onActiveVariantChange,
}) => {
  const [playbackError, setPlaybackError] = useState<string | null>(null);
  const [isRenderingVariant, setIsRenderingVariant] = useState(false);
  const [renderFeedback, setRenderFeedback] = useState<string | null>(null);
  const variantOptions = useMemo(() => {
    const options: VariantOption[] = [];
    const seen = new Set<string>();
    const outputs = Array.isArray(finalVideoMeta?.outputs) ? finalVideoMeta.outputs as Record<string, any>[] : [];

    if (outputs.length > 0) {
      outputs.forEach((output) => {
        const variantId = String(output.variant_id ?? '');
        if (!variantId || seen.has(variantId) || !output.output_path) return;
        seen.add(variantId);
        options.push({
          id: variantId,
          label: typeof output.label === 'string' ? output.label : (VARIANT_LABELS[variantId] ?? variantId),
        });
      });
    }

    if (options.length > 0) {
      return options.sort((a, b) => {
        const aIndex = VARIANT_ORDER.indexOf(a.id as typeof VARIANT_ORDER[number]);
        const bIndex = VARIANT_ORDER.indexOf(b.id as typeof VARIANT_ORDER[number]);
        return (aIndex === -1 ? Number.MAX_SAFE_INTEGER : aIndex) - (bIndex === -1 ? Number.MAX_SAFE_INTEGER : bIndex);
      });
    }

    const collect = (source: Record<string, any> | null) => {
      const variants = source?.variants;
      if (!variants || typeof variants !== 'object') return;
      Object.entries(variants).forEach(([variantId, payload]) => {
        if (seen.has(variantId)) return;
        seen.add(variantId);
        options.push({
          id: variantId,
          label: typeof (payload as Record<string, any>)?.label === 'string'
            ? String((payload as Record<string, any>).label)
            : (VARIANT_LABELS[variantId] ?? variantId),
        });
      });
    };
    collect(editTimeline);
    collect(slotMatches);
    collect(resolvedGaps);
    if (options.length === 0) {
      options.push({ id: 'structure', label: VARIANT_LABELS.structure });
    }
    return options.sort((a, b) => {
      const aIndex = VARIANT_ORDER.indexOf(a.id as typeof VARIANT_ORDER[number]);
      const bIndex = VARIANT_ORDER.indexOf(b.id as typeof VARIANT_ORDER[number]);
      return (aIndex === -1 ? Number.MAX_SAFE_INTEGER : aIndex) - (bIndex === -1 ? Number.MAX_SAFE_INTEGER : bIndex);
    });
  }, [editTimeline, slotMatches, resolvedGaps, finalVideoMeta]);
  const [activeVariantId, setActiveVariantId] = useState<string>(initialActiveVariantId ?? variantOptions[0]?.id ?? 'structure');
  useEffect(() => {
    if (!variantOptions.some((option) => option.id === activeVariantId)) {
      setActiveVariantId(variantOptions[0]?.id ?? 'structure');
    }
  }, [activeVariantId, variantOptions]);
  useEffect(() => {
    if (initialActiveVariantId && variantOptions.some((option) => option.id === initialActiveVariantId) && initialActiveVariantId !== activeVariantId) {
      setActiveVariantId(initialActiveVariantId);
    }
  }, [activeVariantId, initialActiveVariantId, variantOptions]);
  useEffect(() => {
    onActiveVariantChange?.(activeVariantId);
  }, [activeVariantId, onActiveVariantChange]);

  const activeEditTimeline = (getVariantPayload(editTimeline, activeVariantId) ?? {}) as Record<string, any>;
  const activeSlotMatches = (getVariantPayload(slotMatches, activeVariantId) ?? {}) as Record<string, any>;
  const activeResolvedGaps = (getVariantPayload(resolvedGaps, activeVariantId) ?? {}) as Record<string, any>;
  const activeOutputMeta = getVariantOutputMeta(finalVideoMeta, activeVariantId);
  const segments = useMemo(() => (
    Array.isArray(activeEditTimeline?.timeline) ? activeEditTimeline.timeline as Record<string, any>[] : []
  ), [activeEditTimeline]);
  const timelineMeta = (activeEditTimeline?.timeline_meta ?? {}) as Record<string, any>;
  const validation = (activeEditTimeline?.validation ?? {}) as Record<string, any>;
  const outputUrl = getOutputUrl(currentJobId, finalVideoMeta, activeVariantId);
  const slotAssignments = safeArray(activeSlotMatches?.slot_assignments) as Record<string, any>[];
  const lowConfidenceSlots = safeArray(activeSlotMatches?.low_confidence_slots) as Record<string, any>[];
  const unfilledSlots = safeArray(activeSlotMatches?.unfilled_slots) as Record<string, any>[];
  const resolvedGapList = safeArray(activeResolvedGaps?.resolved_gaps) as Record<string, any>[];
  const stillUnresolved = safeArray(activeResolvedGaps?.still_unresolved) as Record<string, any>[];
  const matchedCount = slotAssignments.length;
  const totalDuration = Number(timelineMeta.duration ?? segments[segments.length - 1]?.end ?? 0);
  const [selectedClipId, setSelectedClipId] = useState<string | null>(segments[0]?.clip_id ?? null);

  useEffect(() => {
    setSelectedClipId(segments[0]?.clip_id ?? null);
  }, [activeVariantId, segments.length, segments[0]?.clip_id]);

  const selectedSegment = segments.find((seg) => String(seg.clip_id) === selectedClipId) ?? segments[0] ?? null;
  const selectedAssignment = slotAssignments.find((assignment) => assignment.slot_id === selectedSegment?.slot_id) ?? null;
  const selectedGapResolution = resolvedGapList.find((gap) => (
    gap.slot_id === selectedSegment?.slot_id || gap.slot === selectedSegment?.slot_id
  )) ?? null;

  const renderStatus = useMemo(() => {
    if (!activeOutputMeta) return '等待渲染';
    if (activeOutputMeta.success && outputUrl) return '渲染完成';
    if (activeOutputMeta.success) return '结果已生成';
    return '渲染未完成';
  }, [activeOutputMeta, outputUrl]);

  const summaryCards = [
    { label: '成片时长', value: formatSeconds(timelineMeta.duration ?? activeOutputMeta?.duration_seconds) },
    { label: '片段数', value: String(activeOutputMeta?.rendered_segment_count ?? segments.length ?? 0) },
    { label: '已匹配插槽', value: String(matchedCount) },
    { label: '补口数', value: String(resolvedGapList.length) },
    { label: '结构保真度', value: String(validation.structure_fidelity_score ?? '--') },
  ];

  const handleRenderVariant = async () => {
    if (!currentJobId || !activeVariantId || isRenderingVariant) return;
    setIsRenderingVariant(true);
    setRenderFeedback(null);
    try {
      const res = await fetch(`/api/orchestration/jobs/${currentJobId}/timeline/re-render`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requested_variant_id: activeVariantId }),
      });
      if (!res.ok) {
        throw new Error(`re-render failed: ${res.status}`);
      }
      setRenderFeedback(`已提交 ${VARIANT_LABELS[activeVariantId] ?? activeVariantId} 的渲染请求`);
    } catch (error) {
      const message = error instanceof Error ? error.message : 're-render failed';
      setRenderFeedback(message);
    } finally {
      setIsRenderingVariant(false);
    }
  };

  return (
    <div style={{ backgroundColor: 'var(--color-neutral-100)' }}>
      <div style={{ aspectRatio: '16 / 9', backgroundColor: '#1a1a2e' }}>
        {outputUrl ? (
          <video
            key={outputUrl}
            controls
            src={outputUrl}
            onLoadedData={() => setPlaybackError(null)}
            onError={() => setPlaybackError('结果文件已写入元数据，但播放器暂时无法加载该视频文件。')}
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        ) : (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ color: 'white', fontSize: 18, opacity: 0.7 }}>等待最终渲染结果</span>
          </div>
        )}
      </div>

      <div style={{ padding: '20px 24px', display: 'grid', gap: 18 }}>
        <section style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <div>
              <h3 style={{ margin: 0, marginBottom: 4 }}>版本切换</h3>
              <div style={{ fontSize: 13, color: '#64748b' }}>四个版本共享同一参考解析，但在匹配和剪辑偏好上分别强调结构、卡点、转场和节奏。</div>
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
              {variantOptions.map((option) => {
                const isActive = option.id === activeVariantId;
                return (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => setActiveVariantId(option.id)}
                    style={{
                      borderRadius: 999,
                      border: '2px solid',
                      borderColor: isActive ? '#111827' : 'transparent',
                      backgroundColor: isActive ? '#f8fafc' : 'white',
                      padding: '10px 14px',
                      fontSize: 12,
                      fontWeight: 700,
                      color: '#0f172a',
                      cursor: 'pointer',
                      boxShadow: isActive ? '0 0 0 1px #111827 inset' : '0 0 0 1px #dbe2ea inset',
                      opacity: 1,
                    }}
                  >
                    {option.label}
                  </button>
                );
              })}
              <button
                type="button"
                onClick={handleRenderVariant}
                disabled={!currentJobId || isRenderingVariant}
                style={{
                  borderRadius: 999,
                  border: '1px solid #2563eb',
                  backgroundColor: '#eff6ff',
                  color: '#1d4ed8',
                  padding: '10px 14px',
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: !currentJobId || isRenderingVariant ? 'not-allowed' : 'pointer',
                  opacity: !currentJobId || isRenderingVariant ? 0.6 : 1,
                }}
              >
                {isRenderingVariant ? '渲染中...' : '渲染当前版本'}
              </button>
            </div>
          </div>
          {renderFeedback && (
            <div style={{ marginTop: 12, fontSize: 12, color: '#475569' }}>{renderFeedback}</div>
          )}
        </section>

        <section style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: 12 }}>
          {summaryCards.map((card) => (
            <div key={card.label} style={{ backgroundColor: 'white', borderRadius: 14, padding: 16, border: '1px solid var(--color-neutral-200)' }}>
              <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6 }}>{card.label}</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#0f172a' }}>{card.value}</div>
            </div>
          ))}
        </section>

        <section style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
          <h3 style={{ marginTop: 0, marginBottom: 12 }}>最终渲染信息</h3>
          <div style={{ fontSize: 13, color: 'var(--color-neutral-700)', display: 'grid', gap: 8 }}>
            <div>状态：{renderStatus}</div>
            <div>当前版本：{String(activeOutputMeta?.label ?? activeVariantId)}</div>
            <div>输出路径：{String(activeOutputMeta?.output_path ?? '-')}</div>
            <div>输出文件：{String(activeOutputMeta?.output_filename ?? '-')}</div>
            <div>文件大小：{formatBytes(activeOutputMeta?.file_size_bytes)}</div>
            <div>渲染片段数：{String(activeOutputMeta?.rendered_segment_count ?? '-')}</div>
            {playbackError && (
              <div style={{ color: '#991b1b', backgroundColor: '#fef2f2', padding: '8px 10px', borderRadius: 10 }}>
                {playbackError}
              </div>
            )}
          </div>
        </section>

        <section style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 14 }}>
            <div>
              <h3 style={{ margin: 0, marginBottom: 4 }}>成片时间线</h3>
              <div style={{ fontSize: 13, color: '#64748b' }}>点击片段查看该段素材来源、插槽归属和补口策略。</div>
            </div>
            <div style={{ fontSize: 12, color: '#64748b' }}>总时长 {formatSeconds(totalDuration)}</div>
          </div>
          {segments.length > 0 && totalDuration > 0 ? (
            <div style={{ position: 'relative', paddingTop: 22, paddingBottom: 10 }}>
              <div style={{ position: 'absolute', left: 0, right: 0, top: 56, height: 8, borderRadius: 999, backgroundColor: '#e5e7eb' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#94a3b8', marginBottom: 18 }}>
                <span>0.0s</span>
                <span>{formatSeconds(totalDuration)}</span>
              </div>
              <div style={{ position: 'relative', height: 110 }}>
                {segments.map((segment, index) => {
                  const left = `${Math.min(100, Math.max(0, (Number(segment.start ?? 0) / totalDuration) * 100))}%`;
                  const width = `${Math.max(10, ((Math.max(Number(segment.end ?? 0) - Number(segment.start ?? 0), 0.3)) / totalDuration) * 100)}%`;
                  const isActive = String(segment.clip_id) === selectedClipId;
                  return (
                    <button
                      key={String(segment.clip_id ?? index)}
                      type="button"
                      onClick={() => setSelectedClipId(String(segment.clip_id ?? index))}
                      style={{
                        position: 'absolute',
                        left,
                        top: isActive ? 10 : 18,
                        width,
                        minWidth: 94,
                        transform: 'translateX(-6px)',
                        border: isActive ? '2px solid #0f172a' : '1px solid rgba(15, 23, 42, 0.08)',
                        borderRadius: 14,
                        padding: '10px 10px 8px',
                        backgroundColor: isActive ? '#fff' : '#f8fafc',
                        boxShadow: isActive ? '0 10px 24px rgba(15, 23, 42, 0.12)' : 'none',
                        cursor: 'pointer',
                        textAlign: 'left',
                      }}
                    >
                      <div style={{ fontSize: 11, fontWeight: 700, color: '#2563eb', marginBottom: 4 }}>
                        {String(segment.slot_id ?? segment.clip_id ?? `clip_${index + 1}`)}
                      </div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: '#0f172a', marginBottom: 4 }}>
                        {String(segment.asset_id ?? '未绑定素材')}
                      </div>
                      <div style={{ fontSize: 11, color: '#64748b' }}>
                        {formatSeconds(segment.start)} - {formatSeconds(segment.end)}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            <span style={{ color: 'var(--color-neutral-500)' }}>等待 EditPlanner 输出时间线。</span>
          )}
        </section>

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(340px, 1fr)', gap: 18, alignItems: 'start' }}>
          <section style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
            <h3 style={{ marginTop: 0, marginBottom: 14 }}>当前片段详情</h3>
            {selectedSegment ? (
              <div style={{ display: 'grid', gap: 14 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 10 }}>
                  {[
                    { label: '插槽', value: String(selectedSegment.slot_id ?? '-') },
                    { label: '角色', value: String(selectedSegment.role ?? '-') },
                    { label: '时间', value: `${formatSeconds(selectedSegment.start)} - ${formatSeconds(selectedSegment.end)}` },
                    { label: '源片段', value: `${formatSeconds(selectedSegment.source_in)} - ${formatSeconds(selectedSegment.source_out)}` },
                  ].map((item) => (
                    <div key={item.label} style={{ padding: 12, borderRadius: 12, backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{item.label}</div>
                      <div style={{ fontSize: 14, fontWeight: 700, color: '#0f172a' }}>{item.value}</div>
                    </div>
                  ))}
                </div>

                <div style={{ padding: 14, borderRadius: 14, backgroundColor: '#eff6ff', border: '1px solid #bfdbfe' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#1d4ed8', marginBottom: 8 }}>素材与转场</div>
                  <div style={{ display: 'grid', gap: 8, fontSize: 14, color: '#1e3a8a' }}>
                    <div>素材：{String(selectedSegment.asset_id ?? '-')}</div>
                    <div>素材片段：{String(selectedSegment.segment_id ?? '-')}</div>
                    <div>转场：{getTransitionLabel(selectedSegment.transition_out ?? 'cut')}</div>
                  </div>
                </div>

                <div style={{ padding: 14, borderRadius: 14, backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#334155', marginBottom: 8 }}>编辑参数</div>
                  <div style={{ display: 'grid', gap: 8, fontSize: 14, color: '#334155' }}>
                    <div>裁切：{String(selectedSegment.transform?.crop ?? '-')}</div>
                    <div>速度：{String(selectedSegment.transform?.speed ?? '-')}</div>
                    <div>运动：{String(selectedSegment.transform?.motion ?? '-')}</div>
                    <div>缩放：{String(selectedSegment.transform?.scale ?? '-')}</div>
                  </div>
                </div>

                <div style={{ padding: 14, borderRadius: 14, backgroundColor: '#f5f3ff', border: '1px solid #ddd6fe' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#5b21b6', marginBottom: 8 }}>包装叠加</div>
                  {safeArray(selectedSegment.overlays).length > 0 ? (
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      {safeArray(selectedSegment.overlays).map((overlay, index) => (
                        <span key={`${String(overlay)}-${index}`} style={{ padding: '6px 10px', borderRadius: 999, backgroundColor: '#ede9fe', color: '#6d28d9', fontSize: 12 }}>
                          {typeof overlay === 'string' ? overlay : JSON.stringify(overlay)}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div style={{ fontSize: 13, color: '#7c3aed' }}>当前片段没有额外 overlays。</div>
                  )}
                </div>
              </div>
            ) : (
              <span style={{ color: 'var(--color-neutral-500)' }}>暂无片段详情。</span>
            )}
          </section>

          <section style={{ display: 'grid', gap: 18 }}>
            <div style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
              <h3 style={{ marginTop: 0, marginBottom: 12 }}>插槽匹配与补口说明</h3>
              <div style={{ display: 'grid', gap: 12 }}>
                {selectedAssignment ? (
                  <div style={{ padding: 12, borderRadius: 12, backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
                      <div style={{ fontSize: 14, fontWeight: 700, color: '#0f172a' }}>{String(selectedAssignment.slot_id ?? '-')}</div>
                      <span style={{ padding: '4px 8px', borderRadius: 999, fontSize: 11, fontWeight: 700, ...scoreTone(Number(selectedAssignment.match_score ?? 0)) }}>
                        匹配分 {String(selectedAssignment.match_score ?? '-')}
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                      {String(selectedAssignment.selected_candidate?.asset_id ?? '-')} / {String(selectedAssignment.selected_candidate?.segment_id ?? '-')}
                    </div>
                    <div style={{ fontSize: 13, color: '#334155', marginTop: 8 }}>
                      {String(selectedAssignment.reason ?? '当前插槽由该素材片段承担。')}
                    </div>
                  </div>
                ) : (
                  <div style={{ fontSize: 13, color: '#64748b' }}>当前片段没有直接命中的 slot assignment。</div>
                )}

                {selectedGapResolution ? (
                  <div style={{ padding: 12, borderRadius: 12, backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0' }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#166534' }}>
                      补口策略：{String(selectedGapResolution.chosen_strategy ?? selectedGapResolution.strategy ?? '-')}
                    </div>
                    <div style={{ fontSize: 12, color: '#15803d', marginTop: 4 }}>
                      置信度 {String(selectedGapResolution.confidence ?? '-')} / 人工复核 {yesNo(selectedGapResolution.requires_human_review)}
                    </div>
                    <div style={{ fontSize: 13, color: '#166534', marginTop: 8 }}>
                      {String(selectedGapResolution.impact_on_template?.rhythm_change ?? '当前片段参与了缺口补齐。')}
                    </div>
                  </div>
                ) : (
                  <div style={{ fontSize: 13, color: '#64748b' }}>当前片段没有对应的 GapResolver 补口记录。</div>
                )}
              </div>
            </div>

            <div style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
              <h3 style={{ marginTop: 0, marginBottom: 12 }}>整体结果摘要</h3>
              <div style={{ display: 'grid', gap: 10 }}>
                <div style={{ fontSize: 13, color: '#334155' }}>低置信插槽：{String(lowConfidenceSlots.length)}</div>
                <div style={{ fontSize: 13, color: '#334155' }}>未填充插槽：{String(unfilledSlots.length)}</div>
                <div style={{ fontSize: 13, color: '#334155' }}>已解决缺口：{String(resolvedGapList.length)}</div>
                <div style={{ fontSize: 13, color: '#334155' }}>未解决缺口：{String(stillUnresolved.length)}</div>
              </div>
            </div>
          </section>
        </div>

        <section style={{ backgroundColor: 'white', borderRadius: 16, padding: 18, border: '1px solid var(--color-neutral-200)' }}>
          <h3 style={{ marginTop: 0, marginBottom: 14 }}>校验与风险</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: 10, marginBottom: 14 }}>
            {[
              { label: '插槽填满', value: yesNo(validation.all_slots_filled) },
              { label: '素材完整', value: yesNo(validation.no_missing_assets) },
              { label: '时间线无重叠', value: yesNo(validation.no_timeline_overlap) },
              { label: '源区间合法', value: yesNo(validation.source_ranges_valid) },
              { label: '接近样例时长', value: yesNo(validation.duration_close_to_reference) },
            ].map((item) => (
              <div key={item.label} style={{ padding: 12, borderRadius: 12, backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{item.label}</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#0f172a' }}>{item.value}</div>
              </div>
            ))}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 14 }}>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', marginBottom: 8 }}>低置信插槽</div>
              <div style={{ display: 'grid', gap: 8 }}>
                {lowConfidenceSlots.length > 0 ? lowConfidenceSlots.map((slot, index) => (
                  <div key={String(slot.slot_id ?? index)} style={{ padding: '8px 10px', borderRadius: 10, backgroundColor: '#fefce8', color: '#854d0e', fontSize: 12 }}>
                    {String(slot.slot_id ?? `slot_${index + 1}`)}：{String(slot.reason ?? '置信度偏低')}
                  </div>
                )) : (
                  <div style={{ color: '#94a3b8', fontSize: 12 }}>暂无低置信插槽。</div>
                )}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', marginBottom: 8 }}>未解决缺口</div>
              <div style={{ display: 'grid', gap: 8 }}>
                {stillUnresolved.length > 0 ? stillUnresolved.map((gap, index) => (
                  <div key={String(gap.slot_id ?? gap.slot ?? index)} style={{ padding: '8px 10px', borderRadius: 10, backgroundColor: '#fef2f2', color: '#991b1b', fontSize: 12 }}>
                    {String(gap.slot_id ?? gap.slot ?? `gap_${index + 1}`)}：{String(gap.reason ?? gap.need ?? '仍需补口')}
                  </div>
                )) : (
                  <div style={{ color: '#94a3b8', fontSize: 12 }}>暂无未解决缺口。</div>
                )}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};
