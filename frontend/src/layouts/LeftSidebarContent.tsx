import React, { useCallback, useEffect } from 'react';
import { SampleVideoSection } from '../components/SampleVideoSection';
import { MaterialVideoSection } from '../components/MaterialVideoSection';
import { EditVersionSection } from '../components/EditVersionSection';
import { useSSEEventSource } from '../hooks/useSSEEventSource';
import type { UploadedVideo, SSEEventPayload, TabType } from '../types';

interface LeftSidebarContentProps {
  currentJobId: string | null;
  setCurrentJobId: (jobId: string | null) => void;
  videoList: UploadedVideo[];
  setVideoList: React.Dispatch<React.SetStateAction<UploadedVideo[]>>;
  selectedReferenceVideoId: string | null;
  setSelectedReferenceVideoId: React.Dispatch<React.SetStateAction<string | null>>;
  setActivePreviewVideo: React.Dispatch<React.SetStateAction<UploadedVideo | null>>;
  setActiveTab: (tab: TabType) => void;
  setSelectedResultVariantId: React.Dispatch<React.SetStateAction<string | null>>;
}

const toFrontendVideo = (video: Record<string, any>): UploadedVideo => ({
  id: video.saved_filename || video.id,
  filename: video.original_filename || video.filename,
  url: `/api/orchestration/uploads/${video.saved_filename || video.id}`,
  duration: 0,
  is_reference: Boolean(video.is_reference),
  createdAt: Date.now(),
  savedFilename: video.saved_filename,
  originalFilename: video.original_filename,
  storagePath: video.storage_path,
});

export const LeftSidebarContent: React.FC<LeftSidebarContentProps> = ({
  currentJobId,
  setCurrentJobId,
  videoList,
  setVideoList,
  selectedReferenceVideoId,
  setSelectedReferenceVideoId,
  setActivePreviewVideo,
  setActiveTab,
  setSelectedResultVariantId,
}) => {
  const [finalVideoMeta, setFinalVideoMeta] = React.useState<Record<string, any> | null>(null);
  const [sharedMemoryVersion, setSharedMemoryVersion] = React.useState<number>(1);

  const ensureDraftJob = useCallback(async (): Promise<string> => {
    if (currentJobId) {
      return currentJobId;
    }

    const res = await fetch('/api/orchestration/jobs/draft', {
      method: 'POST',
    });
    if (!res.ok) {
      throw new Error(`create draft job failed: ${res.status}`);
    }
    const data = await res.json();
    const draftJobId = String(data.job_id);
    setCurrentJobId(draftJobId);
    return draftJobId;
  }, [currentJobId, setCurrentJobId]);

  const loadInitialUploadedVideos = useCallback(async (jobId: string) => {
    try {
      const res = await fetch(`/api/orchestration/jobs/${jobId}`);
      const data = await res.json();
      const inputs = data.shared_memory?.inputs;
      const entries = data.shared_memory?.entries ?? {};
      setFinalVideoMeta((entries.final_video_meta?.data ?? null) as Record<string, any> | null);
      setSharedMemoryVersion(Number(data.shared_memory?.version ?? 1));
      if (inputs?.uploaded_videos) {
        const mapped: UploadedVideo[] = (inputs.uploaded_videos as Record<string, any>[]).map(toFrontendVideo);
        setVideoList(mapped);
        setSelectedReferenceVideoId(inputs.selected_reference_video_id ?? null);
        setActivePreviewVideo((prev) => {
          if (prev) {
            const matched = mapped.find((video) => video.id === prev.id);
            if (matched) {
              return matched;
            }
          }
          return mapped[0] ?? null;
        });
      }
    } catch (e) {
      console.warn('[LeftSidebar] failed to load uploaded_videos', e);
    }
  }, [setActivePreviewVideo, setSelectedReferenceVideoId, setVideoList]);

  const deleteUploadedVideo = useCallback(async (videoId: string) => {
    const fallbackLocalDelete = () => {
      const nextList = videoList.filter((video) => video.id !== videoId);
      setVideoList(nextList);
      setSelectedReferenceVideoId((prev) => {
        if (prev !== videoId) {
          return prev;
        }
        const fallback = nextList.find((video) => video.is_reference) ?? null;
        return fallback?.id ?? null;
      });
      setActivePreviewVideo((prev) => {
        if (!prev || prev.id !== videoId) {
          return prev;
        }
        return nextList[0] ?? null;
      });
    };

    if (!currentJobId) {
      fallbackLocalDelete();
      return;
    }

    try {
      const res = await fetch(`/api/orchestration/jobs/${currentJobId}/videos/${videoId}`, {
        method: 'DELETE',
      });
      if (!res.ok) {
        throw new Error(`delete video failed: ${res.status}`);
      }
      const data = await res.json();
      const deletedVideoId = String(data.deleted_video_id ?? videoId);
      const updatedSelectedReferenceId = (data.selected_reference_video_id as string | null) ?? null;
      const nextList = videoList.filter((video) => video.id !== deletedVideoId);
      setVideoList(nextList);
      setSelectedReferenceVideoId(updatedSelectedReferenceId);
      setActivePreviewVideo((prev) => {
        if (!prev || prev.id !== deletedVideoId) {
          return prev;
        }
        const selectedReference = nextList.find((video) => video.id === updatedSelectedReferenceId);
        return selectedReference ?? nextList[0] ?? null;
      });
    } catch (error) {
      console.error('[LeftSidebar] delete uploaded video failed', error);
    }
  }, [
    currentJobId,
    setActivePreviewVideo,
    setSelectedReferenceVideoId,
    setVideoList,
    videoList,
  ]);

  useEffect(() => {
    if (currentJobId) {
      loadInitialUploadedVideos(currentJobId);
    }
  }, [currentJobId, loadInitialUploadedVideos]);

  useEffect(() => {
    if (selectedReferenceVideoId) {
      const exists = videoList.some((video) => video.id === selectedReferenceVideoId && video.is_reference);
      if (!exists) {
        const fallback = videoList.find((video) => video.is_reference) ?? null;
        setSelectedReferenceVideoId(fallback?.id ?? null);
      }
    } else {
      const fallback = videoList.find((video) => video.is_reference) ?? null;
      if (fallback) {
        setSelectedReferenceVideoId(fallback.id);
      }
    }
  }, [selectedReferenceVideoId, setSelectedReferenceVideoId, videoList]);

  const onSSEEvent = useCallback((evt: SSEEventPayload) => {
    if (
      evt.event_type === 'resource_updated' ||
      (evt.event_type === 'step_write' && evt.agent_name === 'FinalVideoRendererAgent')
    ) {
      if (currentJobId) {
        void loadInitialUploadedVideos(currentJobId);
      }
    }
    if (evt.event_type === 'resource_updated') {
      const newList = (evt.payload?.uploaded_videos as Record<string, any>[]) ?? [];
      const normalized = newList.map(toFrontendVideo);
      setVideoList(normalized);
      setSelectedReferenceVideoId((evt.payload?.selected_reference_video_id as string | null) ?? null);
      setActivePreviewVideo((prev) => {
        if (prev) {
          const matched = normalized.find((video) => video.id === prev.id);
          if (matched) {
            return matched;
          }
        }
        return normalized[0] ?? null;
      });
    }
  }, [currentJobId, loadInitialUploadedVideos, setActivePreviewVideo, setSelectedReferenceVideoId, setVideoList]);

  useSSEEventSource({
    jobId: currentJobId,
    onEvent: onSSEEvent,
  });

  if (typeof window !== 'undefined') {
    (window as any).__debugSetJobId = setCurrentJobId;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <SampleVideoSection
        jobId={currentJobId}
        ensureDraftJob={ensureDraftJob}
        videoList={videoList}
        onVideoListChange={setVideoList}
        onDeleteVideo={deleteUploadedVideo}
        onVideoSelect={(video) => {
          setActivePreviewVideo(video);
          setActiveTab('sample');
        }}
        selectedReferenceVideoId={selectedReferenceVideoId}
        onSelectedReferenceVideoIdChange={setSelectedReferenceVideoId}
      />
      <MaterialVideoSection
        jobId={currentJobId}
        ensureDraftJob={ensureDraftJob}
        videoList={videoList}
        onVideoListChange={setVideoList}
        onDeleteVideo={deleteUploadedVideo}
        onVideoSelect={(video) => {
          setActivePreviewVideo(video);
          setActiveTab('material');
        }}
      />
      <EditVersionSection
        currentJobId={currentJobId}
        finalVideoMeta={finalVideoMeta}
        sharedMemoryVersion={sharedMemoryVersion}
        onPreviewResult={(variantId) => {
          setSelectedResultVariantId(variantId ?? null);
          setActiveTab('result');
        }}
      />
    </div>
  );
};
