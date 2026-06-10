import React, { useState, useEffect, useCallback } from 'react';
import { WorkbenchTabNavigation } from '../components/WorkbenchTabNavigation';
import { SampleVideoTabContent } from '../components/SampleVideoTabContent';
import { MaterialVideoTabContent } from '../components/MaterialVideoTabContent';
import { ResultVideoTabContent } from '../components/ResultVideoTabContent';
import { useSSEEventSource } from '../hooks/useSSEEventSource';
import type { TabType, UploadedVideo, SharedMemorySnapshot, SSEEventPayload } from '../types';

interface CenterWorkbenchContentProps {
  currentJobId: string | null;
  videoList: UploadedVideo[];
  selectedReferenceVideoId: string | null;
  activePreviewVideo: UploadedVideo | null;
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  selectedResultVariantId: string | null;
  setSelectedResultVariantId: React.Dispatch<React.SetStateAction<string | null>>;
}

export const CenterWorkbenchContent: React.FC<CenterWorkbenchContentProps> = ({
  currentJobId,
  videoList,
  selectedReferenceVideoId,
  activePreviewVideo,
  activeTab,
  setActiveTab,
  selectedResultVariantId,
  setSelectedResultVariantId,
}) => {
  const [sharedMemory, setSharedMemory] = useState<SharedMemorySnapshot | null>(null);

  const refreshSharedMemory = useCallback(async () => {
    if (!currentJobId) {
      setSharedMemory(null);
      return;
    }
    try {
      const res = await fetch(`/api/orchestration/jobs/${currentJobId}`);
      const data = await res.json();
      setSharedMemory(data.shared_memory ?? null);
    } catch (error) {
      console.warn('[CenterWorkbench] failed to refresh shared memory', error);
    }
  }, [currentJobId]);

  useEffect(() => {
    refreshSharedMemory();
  }, [refreshSharedMemory]);

  const onSSEEvent = useCallback((evt: SSEEventPayload) => {
    if (
      evt.event_type === 'resource_updated' ||
      evt.event_type === 'step_write' ||
      evt.event_type === 'timeline_updated' ||
      evt.event_type === 'plan_ready'
    ) {
      refreshSharedMemory();
    }
  }, [refreshSharedMemory]);

  useSSEEventSource({
    jobId: currentJobId,
    onEvent: onSSEEvent,
  });

  const entries = sharedMemory?.entries ?? {};
  const referenceAnalysis = (entries.reference_analysis?.data ?? null) as Record<string, any> | null;
  const assetIndex = (entries.asset_index?.data ?? null) as Record<string, any> | null;
  const slotMatches = (entries.slot_matches?.data ?? null) as Record<string, any> | null;
  const resolvedGaps = (entries.resolved_gaps?.data ?? null) as Record<string, any> | null;
  const editTimeline = (entries.edit_timeline?.data ?? null) as Record<string, any> | null;
  const finalVideoMeta = (entries.final_video_meta?.data ?? null) as Record<string, any> | null;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: 'var(--color-neutral-100)',
      overflow: 'hidden',
    }}>
      <WorkbenchTabNavigation activeTab={activeTab} onChange={setActiveTab} />
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {activeTab === 'sample' && (
          <SampleVideoTabContent
            currentJobId={currentJobId}
            activeVideo={activePreviewVideo}
            videoList={videoList}
            selectedReferenceVideoId={selectedReferenceVideoId}
            referenceAnalysis={referenceAnalysis}
          />
        )}
        {activeTab === 'material' && (
          <MaterialVideoTabContent
            activeVideo={activePreviewVideo}
            videoList={videoList}
            assetIndex={assetIndex}
            slotMatches={slotMatches}
            resolvedGaps={resolvedGaps}
            editTimeline={editTimeline}
          />
        )}
        {activeTab === 'result' && (
          <ResultVideoTabContent
            currentJobId={currentJobId}
            editTimeline={editTimeline}
            slotMatches={slotMatches}
            resolvedGaps={resolvedGaps}
            finalVideoMeta={finalVideoMeta}
            initialActiveVariantId={selectedResultVariantId}
            onActiveVariantChange={setSelectedResultVariantId}
          />
        )}
      </div>
    </div>
  );
};
