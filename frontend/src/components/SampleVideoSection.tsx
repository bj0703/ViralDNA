import React, { useEffect, useRef, useState } from 'react';
import type { UploadedVideo } from '../types';
import { CollapsibleSectionHeader } from './CollapsibleSectionHeader';

const STORAGE_KEY = 'emo_transfer_sample_video_expanded';

interface SampleVideoSectionProps {
  jobId: string | null;
  ensureDraftJob: () => Promise<string>;
  videoList: UploadedVideo[];
  onVideoListChange: (list: UploadedVideo[]) => void;
  onDeleteVideo?: (videoId: string) => Promise<void> | void;
  onVideoSelect?: (video: UploadedVideo) => void;
  selectedReferenceVideoId: string | null;
  onSelectedReferenceVideoIdChange: (videoId: string | null) => void;
}

export const SampleVideoSection: React.FC<SampleVideoSectionProps> = ({
  jobId,
  ensureDraftJob,
  videoList,
  onVideoListChange,
  onDeleteVideo,
  onVideoSelect,
  selectedReferenceVideoId,
  onSelectedReferenceVideoIdChange,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isSavingToKB, setIsSavingToKB] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const sampleVideos = videoList.filter((v) => v.is_reference === true);

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved !== null) {
      setIsExpanded(saved === 'true');
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(isExpanded));
  }, [isExpanded]);

  const onFileSelect = () => {
    fileInputRef.current?.click();
  };

  const onFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) {
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('is_reference', 'true');

    try {
      const effectiveJobId = jobId ?? await ensureDraftJob();
      const res = await fetch(`/api/orchestration/jobs/${effectiveJobId}/upload-video`, {
        method: 'POST',
        body: formData,
      });
      const newVideo = await res.json();
      const normalized: UploadedVideo = {
        ...newVideo,
        savedFilename: newVideo.id,
        originalFilename: newVideo.filename,
      };
      onVideoListChange([...videoList, normalized]);
      onSelectedReferenceVideoIdChange(normalized.id);
      onVideoSelect?.(normalized);
    } catch (err) {
      console.error('[SampleVideo] upload failed:', err);
    } finally {
      e.target.value = '';
    }
  };

  const onDelete = (id: string) => {
    if (onDeleteVideo) {
      void onDeleteVideo(id);
      return;
    }
    const nextList = videoList.filter((v) => v.id !== id);
    onVideoListChange(nextList);
    if (selectedReferenceVideoId === id) {
      const fallback = nextList.find((video) => video.is_reference) ?? null;
      onSelectedReferenceVideoIdChange(fallback?.id ?? null);
    }
  };

  const onSaveToKnowledgeBase = async () => {
    if (!jobId) {
      alert("请先创建任务");
      return;
    }
    setIsSavingToKB(true);
    try {
      const res = await fetch(`/api/orchestration/jobs/${jobId}/save-to-knowledge-base`, {
        method: "POST",
      });
      const data = await res.json();
      if (data.success) {
        alert(`✅ 已成功沉淀到知识库！\nstyle_id: ${data.style_id}\n模板文件: ${data.target_file}`);
      } else {
        alert(`❌ 沉淀失败: ${data.detail || JSON.stringify(data)}`);
      }
    } catch (err) {
      console.error("[SampleVideo] save to kb failed:", err);
      alert(`❌ 沉淀失败: ${err}`);
    } finally {
      setIsSavingToKB(false);
    }
  };

  if (!isExpanded) {
    return (
      <CollapsibleSectionHeader
        title="样例视频"
        count={sampleVideos.length}
        isExpanded={false}
        onToggle={() => setIsExpanded(true)}
      />
    );
  }

  return (
    <div style={{ borderBottom: '1px solid var(--color-neutral-200)' }}>
      <CollapsibleSectionHeader
        title="样例视频"
        count={sampleVideos.length}
        isExpanded
        onToggle={() => setIsExpanded(false)}
        onUploadClick={onFileSelect}
      />
      <div style={{ padding: 12 }}>
        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          style={{ display: 'none' }}
          onChange={onFileChange}
        />

        {sampleVideos.length === 0 ? (
          <div
            onClick={onFileSelect}
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
            <span>点击上传参考样例视频</span>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: 10 }}>
            {sampleVideos.map((video) => {
              const isSelected = video.id === selectedReferenceVideoId;
              return (
                <div
                  key={video.id}
                  onClick={() => {
                    onSelectedReferenceVideoIdChange(video.id);
                    onVideoSelect?.(video);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-lg)',
                    border: isSelected ? '1px solid var(--color-primary-500)' : '1px solid var(--color-neutral-200)',
                    backgroundColor: isSelected ? 'var(--color-primary-50)' : 'white',
                    cursor: 'pointer',
                  }}
                >
                  <div
                    style={{
                      width: 34,
                      height: 34,
                      borderRadius: 10,
                      backgroundColor: isSelected ? 'var(--color-primary-500)' : 'var(--color-neutral-200)',
                      color: isSelected ? 'white' : 'var(--color-neutral-700)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 11,
                      fontWeight: 700,
                      flexShrink: 0,
                    }}
                  >
                    样例
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
                      {isSelected ? '当前解析目标' : '点击切换为解析目标'}
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
              );
            })}
          </div>
        )}
        {sampleVideos.length > 0 ? (
          <div style={{ marginTop: 12 }}>
            <button
              onClick={onSaveToKnowledgeBase}
              disabled={isSavingToKB || !jobId}
              style={{
                width: '100%',
                padding: '10px 16px',
                borderRadius: 'var(--radius-lg)',
                border: 'none',
                backgroundColor: isSavingToKB ? 'var(--color-primary-200)' : 'var(--color-primary-500)',
                color: 'white',
                fontSize: 13,
                fontWeight: 600,
                cursor: isSavingToKB ? 'not-allowed' : 'pointer',
              }}
            >
              {isSavingToKB ? '⏳ 正在沉淀到知识库...' : '💾 沉淀该样例结构到知识库'}
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
};
