import React, { useEffect, useRef, useState } from 'react';
import type { UploadedVideo } from '../types';
import { CollapsibleSectionHeader } from './CollapsibleSectionHeader';

const STORAGE_KEY = 'emo_transfer_material_video_expanded';

interface MaterialVideoSectionProps {
  jobId: string | null;
  ensureDraftJob: () => Promise<string>;
  videoList: UploadedVideo[];
  onVideoListChange: (list: UploadedVideo[]) => void;
  onDeleteVideo?: (videoId: string) => Promise<void> | void;
  onVideoSelect?: (video: UploadedVideo) => void;
}

export const MaterialVideoSection: React.FC<MaterialVideoSectionProps> = ({
  jobId,
  ensureDraftJob,
  videoList,
  onVideoListChange,
  onDeleteVideo,
  onVideoSelect,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const materialVideos = videoList.filter((v) => v.is_reference === false);

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved !== null) setIsExpanded(saved === 'true');
  }, []);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(isExpanded));
  }, [isExpanded]);

  const onBatchUpload = () => {
    fileInputRef.current?.click();
  };

  const onFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) {
      return;
    }

    const results: UploadedVideo[] = [];
    const effectiveJobId = jobId ?? await ensureDraftJob();
    for (let i = 0; i < files.length; i += 1) {
      const formData = new FormData();
      formData.append('file', files[i]);
      formData.append('is_reference', 'false');

      try {
        const res = await fetch(`/api/orchestration/jobs/${effectiveJobId}/upload-video`, {
          method: 'POST',
          body: formData,
        });
        const newVideo = await res.json();
        results.push({
          ...newVideo,
          savedFilename: newVideo.id,
          originalFilename: newVideo.filename,
        });
      } catch (err) {
        console.error('[MaterialVideo] upload failed:', err);
      }
    }
    onVideoListChange([...videoList, ...results]);
    if (results[0]) {
      onVideoSelect?.(results[0]);
    }
    e.target.value = '';
  };

  const onDelete = (id: string) => {
    if (onDeleteVideo) {
      void onDeleteVideo(id);
      return;
    }
    onVideoListChange(videoList.filter((v) => v.id !== id));
  };

  if (!isExpanded) {
    return (
      <CollapsibleSectionHeader
        title="素材视频"
        count={materialVideos.length}
        isExpanded={false}
        onToggle={() => setIsExpanded(true)}
      />
    );
  }

  return (
    <div style={{ borderBottom: '1px solid var(--color-neutral-200)' }}>
      <CollapsibleSectionHeader
        title="素材视频"
        count={materialVideos.length}
        isExpanded
        onToggle={() => setIsExpanded(false)}
        onUploadClick={onBatchUpload}
      />
      <div style={{ padding: 12 }}>
        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          multiple
          style={{ display: 'none' }}
          onChange={onFileChange}
        />

        {materialVideos.length === 0 ? (
          <div
            onClick={onBatchUpload}
            style={{
              border: '2px dashed var(--color-neutral-300)',
              borderRadius: 'var(--radius-xl)',
              height: 140,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexDirection: 'column',
              cursor: 'pointer',
              color: 'var(--color-neutral-500)',
              fontSize: 13,
            }}
          >
            <span style={{ fontSize: 28, marginBottom: 6 }}>+</span>
            <span>点击批量上传素材视频</span>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: 10 }}>
            {materialVideos.map((video, index) => (
              <div
                key={video.id}
                onClick={() => onVideoSelect?.(video)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-lg)',
                  border: '1px solid var(--color-neutral-200)',
                  backgroundColor: 'white',
                  cursor: 'pointer',
                }}
              >
                <div
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: 10,
                    backgroundColor: 'var(--color-neutral-200)',
                    color: 'var(--color-neutral-700)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 11,
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                >
                  {String(index + 1).padStart(2, '0')}
                </div>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: 600,
                      color: 'var(--color-neutral-800)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {video.filename}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--color-neutral-500)', marginTop: 2 }}>
                    点击预览素材
                    {video.isPending ? ' · 待创建任务' : ''}
                  </div>
                </div>
                <button
                  onClick={(event) => {
                    event.stopPropagation();
                    onDelete(video.id);
                  }}
                  style={{
                    border: 'none',
                    backgroundColor: 'transparent',
                    color: 'var(--color-neutral-500)',
                    fontSize: 16,
                    cursor: 'pointer',
                    padding: '4px 6px',
                    flexShrink: 0,
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
