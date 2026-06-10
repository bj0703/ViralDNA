import './styles/theme.css';
import { useEffect, useMemo, useState } from 'react';
import { WorkbenchLayout } from './layouts/WorkbenchLayout';
import { LeftSidebarContent } from './layouts/LeftSidebarContent';
import { CenterWorkbenchContent } from './layouts/CenterWorkbenchContent';
import { AgentConversationPanel } from './components/AgentConversationPanel';
import type { TabType, UploadedVideo } from './types';

interface DraftWorkspace {
  jobId: string;
  title: string;
  savedAt: number;
  videoCount: number;
  selectedReferenceVideoId: string | null;
}

const STORAGE_KEYS = {
  legacyCurrentJobId: 'emo_transfer_current_job_id',
  legacySelectedReferenceVideoId: 'emo_transfer_selected_reference_video_id',
  legacyActiveTab: 'emo_transfer_active_tab',
  sessionCurrentJobId: 'viral_dna_session_current_job_id',
  sessionSelectedReferenceVideoId: 'viral_dna_session_selected_reference_video_id',
  sessionActiveTab: 'viral_dna_session_active_tab',
  drafts: 'viral_dna_workspace_drafts',
} as const;

const readDrafts = (): DraftWorkspace[] => {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.drafts);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed as DraftWorkspace[] : [];
  } catch {
    return [];
  }
};

const writeDrafts = (drafts: DraftWorkspace[]) => {
  localStorage.setItem(STORAGE_KEYS.drafts, JSON.stringify(drafts));
};

const buildDraftTitle = (videoList: UploadedVideo[], currentJobId: string) => {
  const referenceVideo = videoList.find((video) => video.is_reference);
  const primaryVideo = referenceVideo ?? videoList[0];
  if (primaryVideo?.filename) {
    return primaryVideo.filename;
  }
  return `未命名草稿 ${currentJobId.slice(0, 8)}`;
};

function App() {
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [videoList, setVideoList] = useState<UploadedVideo[]>([]);
  const [selectedReferenceVideoId, setSelectedReferenceVideoId] = useState<string | null>(null);
  const [activePreviewVideo, setActivePreviewVideo] = useState<UploadedVideo | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('sample');
  const [selectedResultVariantId, setSelectedResultVariantId] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<DraftWorkspace[]>([]);
  const [draftBoxOpen, setDraftBoxOpen] = useState(false);

  const clearWorkspace = () => {
    setCurrentJobId(null);
    setVideoList([]);
    setSelectedReferenceVideoId(null);
    setActivePreviewVideo(null);
    setActiveTab('sample');
    setSelectedResultVariantId(null);
  };

  const upsertDraft = (jobId: string, options?: { bumpSavedAt?: boolean }) => {
    const entry: DraftWorkspace = {
      jobId,
      title: buildDraftTitle(videoList, jobId),
      savedAt: options?.bumpSavedAt === false
        ? (drafts.find((item) => item.jobId === jobId)?.savedAt ?? Date.now())
        : Date.now(),
      videoCount: videoList.length,
      selectedReferenceVideoId,
    };

    setDrafts((prev) => {
      const next = [entry, ...prev.filter((item) => item.jobId !== jobId)];
      writeDrafts(next);
      return next;
    });
  };

  const saveCurrentAsDraft = () => {
    if (!currentJobId) return;
    upsertDraft(currentJobId, { bumpSavedAt: true });
  };

  const openDraft = (draft: DraftWorkspace) => {
    setCurrentJobId(draft.jobId);
    setSelectedReferenceVideoId(draft.selectedReferenceVideoId);
    setActivePreviewVideo(null);
    setActiveTab('sample');
    setDraftBoxOpen(false);
  };

  const createNewPage = () => {
    if (currentJobId) {
      upsertDraft(currentJobId, { bumpSavedAt: true });
    }
    clearWorkspace();
    setDraftBoxOpen(false);
  };

  useEffect(() => {
    const savedJobId = sessionStorage.getItem(STORAGE_KEYS.sessionCurrentJobId);
    const savedReferenceId = sessionStorage.getItem(STORAGE_KEYS.sessionSelectedReferenceVideoId);
    const savedTab = sessionStorage.getItem(STORAGE_KEYS.sessionActiveTab) as TabType | null;

    const legacyJobId = localStorage.getItem(STORAGE_KEYS.legacyCurrentJobId);
    const legacyReferenceId = localStorage.getItem(STORAGE_KEYS.legacySelectedReferenceVideoId);
    const legacyTab = localStorage.getItem(STORAGE_KEYS.legacyActiveTab) as TabType | null;

    const existingDrafts = readDrafts();
    setDrafts(existingDrafts);

    if (savedJobId) {
      setCurrentJobId(savedJobId);
    } else if (legacyJobId) {
      const legacyDraft: DraftWorkspace = {
        jobId: legacyJobId,
        title: `历史任务 ${legacyJobId.slice(0, 8)}`,
        savedAt: Date.now(),
        videoCount: 0,
        selectedReferenceVideoId: legacyReferenceId,
      };
      const nextDrafts = [legacyDraft, ...existingDrafts.filter((item) => item.jobId !== legacyJobId)];
      writeDrafts(nextDrafts);
      setDrafts(nextDrafts);
      localStorage.removeItem(STORAGE_KEYS.legacyCurrentJobId);
      localStorage.removeItem(STORAGE_KEYS.legacySelectedReferenceVideoId);
      localStorage.removeItem(STORAGE_KEYS.legacyActiveTab);
    }

    if (savedReferenceId) {
      setSelectedReferenceVideoId(savedReferenceId);
    }

    const effectiveTab = savedTab ?? legacyTab;
    if (effectiveTab === 'sample' || effectiveTab === 'material' || effectiveTab === 'result') {
      setActiveTab(effectiveTab);
    }
  }, []);

  useEffect(() => {
    if (currentJobId) {
      sessionStorage.setItem(STORAGE_KEYS.sessionCurrentJobId, currentJobId);
    } else {
      sessionStorage.removeItem(STORAGE_KEYS.sessionCurrentJobId);
    }
  }, [currentJobId]);

  useEffect(() => {
    if (selectedReferenceVideoId) {
      sessionStorage.setItem(STORAGE_KEYS.sessionSelectedReferenceVideoId, selectedReferenceVideoId);
    } else {
      sessionStorage.removeItem(STORAGE_KEYS.sessionSelectedReferenceVideoId);
    }
  }, [selectedReferenceVideoId]);

  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEYS.sessionActiveTab, activeTab);
  }, [activeTab]);

  useEffect(() => {
    if (!currentJobId) return;
    upsertDraft(currentJobId, { bumpSavedAt: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentJobId, videoList, selectedReferenceVideoId]);

  useEffect(() => {
    const onBeforeUnload = () => {
      if (!currentJobId) return;
      const nextEntry: DraftWorkspace = {
        jobId: currentJobId,
        title: buildDraftTitle(videoList, currentJobId),
        savedAt: Date.now(),
        videoCount: videoList.length,
        selectedReferenceVideoId,
      };
      const nextDrafts = [nextEntry, ...readDrafts().filter((item) => item.jobId !== currentJobId)];
      writeDrafts(nextDrafts);
    };

    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, [currentJobId, selectedReferenceVideoId, videoList]);

  const headerControls = useMemo(() => (
    <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: 10 }}>
      <button
        type="button"
        onClick={saveCurrentAsDraft}
        disabled={!currentJobId}
        style={{
          border: '1px solid var(--color-neutral-300)',
          backgroundColor: 'white',
          color: 'var(--color-neutral-800)',
          borderRadius: 12,
          padding: '8px 12px',
          fontSize: 12,
          fontWeight: 700,
          cursor: currentJobId ? 'pointer' : 'not-allowed',
          opacity: currentJobId ? 1 : 0.5,
        }}
      >
        保存草稿
      </button>
      <button
        type="button"
        onClick={createNewPage}
        style={{
          border: '1px solid var(--color-primary-200)',
          backgroundColor: 'var(--color-primary-50)',
          color: 'var(--color-primary-500)',
          borderRadius: 12,
          padding: '8px 12px',
          fontSize: 12,
          fontWeight: 700,
          cursor: 'pointer',
        }}
      >
        新建页面
      </button>
      <button
        type="button"
        onClick={() => setDraftBoxOpen((prev) => !prev)}
        style={{
          border: '1px solid var(--color-neutral-300)',
          backgroundColor: 'white',
          color: 'var(--color-neutral-800)',
          borderRadius: 12,
          padding: '8px 12px',
          fontSize: 12,
          fontWeight: 700,
          cursor: 'pointer',
        }}
      >
        草稿箱 {drafts.length > 0 ? `(${drafts.length})` : ''}
      </button>
      {draftBoxOpen && (
        <div
          style={{
            position: 'absolute',
            top: 42,
            right: 0,
            width: 320,
            maxHeight: 360,
            overflowY: 'auto',
            backgroundColor: 'white',
            border: '1px solid var(--color-neutral-200)',
            borderRadius: 16,
            boxShadow: '0 16px 40px rgba(15, 23, 42, 0.12)',
            padding: 12,
            zIndex: 20,
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', marginBottom: 10 }}>草稿箱</div>
          {drafts.length > 0 ? (
            <div style={{ display: 'grid', gap: 8 }}>
              {drafts.map((draft) => (
                <button
                  key={draft.jobId}
                  type="button"
                  onClick={() => openDraft(draft)}
                  style={{
                    display: 'grid',
                    gap: 4,
                    textAlign: 'left',
                    padding: 12,
                    borderRadius: 12,
                    border: '1px solid #e2e8f0',
                    backgroundColor: draft.jobId === currentJobId ? '#eef2ff' : '#f8fafc',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', wordBreak: 'break-word' }}>
                    {draft.title}
                  </div>
                  <div style={{ fontSize: 11, color: '#64748b' }}>
                    {new Date(draft.savedAt).toLocaleString()} | {draft.videoCount} 个视频
                  </div>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>
                    job {draft.jobId.slice(0, 8)}
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: 12, color: '#94a3b8' }}>当前还没有保存的草稿。</div>
          )}
        </div>
      )}
    </div>
  ), [currentJobId, draftBoxOpen, drafts]);

  return (
    <WorkbenchLayout
      headerControls={headerControls}
      leftContent={
        <LeftSidebarContent
          currentJobId={currentJobId}
          setCurrentJobId={setCurrentJobId}
          videoList={videoList}
          setVideoList={setVideoList}
          selectedReferenceVideoId={selectedReferenceVideoId}
          setSelectedReferenceVideoId={setSelectedReferenceVideoId}
          setActivePreviewVideo={setActivePreviewVideo}
          setActiveTab={setActiveTab}
          setSelectedResultVariantId={setSelectedResultVariantId}
        />
      }
      centerContent={
        <CenterWorkbenchContent
          currentJobId={currentJobId}
          videoList={videoList}
          selectedReferenceVideoId={selectedReferenceVideoId}
          activePreviewVideo={activePreviewVideo}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          selectedResultVariantId={selectedResultVariantId}
          setSelectedResultVariantId={setSelectedResultVariantId}
        />
      }
      rightContent={
        <AgentConversationPanel
          currentJobId={currentJobId}
          setCurrentJobId={setCurrentJobId}
          videoList={videoList}
          setVideoList={setVideoList}
          selectedReferenceVideoId={selectedReferenceVideoId}
        />
      }
    />
  );
}

export default App;
