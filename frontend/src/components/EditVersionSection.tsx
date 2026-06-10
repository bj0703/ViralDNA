import React, { useEffect, useMemo, useState } from 'react';
import type { EditVersion } from '../types';
import { CollapsibleSectionHeader } from './CollapsibleSectionHeader';

const STORAGE_KEY = 'emo_transfer_edit_version_expanded';
const VARIANT_ORDER = ['structure', 'beat', 'transition', 'rhythm'] as const;
const VARIANT_LABELS: Record<string, string> = {
  structure: '结构优先版',
  beat: '卡点优先版',
  transition: '转场优先版',
  rhythm: '节奏优先版',
};

interface EditVersionSectionProps {
  currentJobId: string | null;
  finalVideoMeta: Record<string, any> | null;
  sharedMemoryVersion?: number;
  onPreviewResult?: (variantId?: string) => void;
}

const buildVersions = (
  currentJobId: string | null,
  finalVideoMeta: Record<string, any> | null,
  sharedMemoryVersion?: number,
): EditVersion[] => {
  if (!currentJobId || !finalVideoMeta) {
    return [];
  }

  const outputs = Array.isArray(finalVideoMeta.outputs) ? finalVideoMeta.outputs as Record<string, any>[] : [];
  if (outputs.length > 0) {
    return outputs
      .filter((output) => output && output.output_path)
      .sort((a, b) => {
        const aIndex = VARIANT_ORDER.indexOf(String(a.variant_id ?? '') as typeof VARIANT_ORDER[number]);
        const bIndex = VARIANT_ORDER.indexOf(String(b.variant_id ?? '') as typeof VARIANT_ORDER[number]);
        return (aIndex === -1 ? Number.MAX_SAFE_INTEGER : aIndex) - (bIndex === -1 ? Number.MAX_SAFE_INTEGER : bIndex);
      })
      .map((output, index) => {
        const outputPath = String(output.output_path ?? '');
        const filename = outputPath.split(/[/\\]/).pop() ?? `final_rendered_${index + 1}.mp4`;
        const versionMatch = filename.match(/_v(\d+)(?:_[^.]+)?\.mp4$/i);
        const versionNumber = versionMatch?.[1] ?? String(sharedMemoryVersion ?? 1);
        const timestamp = Number(output.rendered_at ?? finalVideoMeta.rendered_at ?? Date.now());
        const variantId = String(output.variant_id ?? `variant_${index + 1}`);
        const variantLabel = typeof output.label === 'string' ? output.label : (VARIANT_LABELS[variantId] ?? variantId);
        return {
          id: `${currentJobId}-${filename}`,
          versionLabel: `V${versionNumber} · ${variantLabel}`,
          timestamp,
          snapshotId: variantId,
        };
      });
  }

  if (!finalVideoMeta.output_path || !finalVideoMeta.success) {
    return [];
  }

  const outputPath = String(finalVideoMeta.output_path);
  const filename = outputPath.split(/[/\\]/).pop() ?? 'final_rendered.mp4';
  const versionMatch = filename.match(/_v(\d+)\.mp4$/i);
  const versionNumber = versionMatch?.[1] ?? String(sharedMemoryVersion ?? 1);
  const timestamp = Number(finalVideoMeta.rendered_at ?? Date.now());

  return [{
    id: `${currentJobId}-${filename}`,
    versionLabel: `V${versionNumber}`,
    timestamp,
    snapshotId: String(finalVideoMeta.default_variant_id ?? sharedMemoryVersion ?? versionNumber),
  }];
};

export const EditVersionSection: React.FC<EditVersionSectionProps> = ({
  currentJobId,
  finalVideoMeta,
  sharedMemoryVersion,
  onPreviewResult,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved !== null) setIsExpanded(saved === 'true');
  }, []);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(isExpanded));
  }, [isExpanded]);

  const versions = useMemo(
    () => buildVersions(currentJobId, finalVideoMeta, sharedMemoryVersion),
    [currentJobId, finalVideoMeta, sharedMemoryVersion],
  );

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  };

  if (!isExpanded) {
    return (
      <CollapsibleSectionHeader
        title="剪辑结果"
        count={versions.length}
        isExpanded={false}
        onToggle={() => setIsExpanded(true)}
      />
    );
  }

  return (
    <div style={{ flexShrink: 0 }}>
      <CollapsibleSectionHeader
        title="剪辑结果"
        count={versions.length}
        isExpanded={true}
        onToggle={() => setIsExpanded(false)}
      />
      <div style={{ padding: 12, maxHeight: 300, overflowY: 'auto' }}>
        {versions.length === 0 ? (
          <div style={{ fontSize: 13, color: 'var(--color-neutral-500)', textAlign: 'center', paddingTop: 20, paddingBottom: 20 }}>
            暂无剪辑版本
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {versions.map((version) => (
              <button
                key={version.id}
                onClick={() => onPreviewResult?.(version.snapshotId)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-lg)',
                  backgroundColor: 'white',
                  border: '1px solid var(--color-neutral-200)',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                <div
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: 10,
                    backgroundColor: 'var(--color-primary-500)',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 700,
                    fontSize: 12,
                    flexShrink: 0,
                  }}
                >
                  成片
                </div>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-neutral-800)' }}>
                    {version.versionLabel}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--color-neutral-500)', marginTop: 2 }}>
                    {formatTime(version.timestamp)} · 点击查看结果视频
                  </div>
                </div>
                <span
                  style={{
                    padding: '6px 10px',
                    borderRadius: 999,
                    backgroundColor: finalVideoMeta?.success ? '#ecfdf5' : '#fef2f2',
                    color: finalVideoMeta?.success ? '#166534' : '#991b1b',
                    fontSize: 11,
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                >
                  {finalVideoMeta?.success ? '已渲染' : '未完成'}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
