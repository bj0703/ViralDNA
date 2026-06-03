import { useEffect, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import { detectIntent, fetchWorkbenchData, getApiBaseUrl, uploadAnalysisJob } from './lib/api';
import { clampPercent, formatSeconds } from './lib/time';
import type { IntentResponse, TimelineSegment, VideoViewModel, WorkbenchData } from './types';

const QUICK_ACTIONS = [
  '请帮我做全维度分析',
  '只看这个视频的节奏结构',
  '总结脚本结构并指出风险',
];

type PanelTab = 'overview' | 'script' | 'pace' | 'risks' | 'raw';
type TimelineFilter = 'all' | 'script' | 'pace';

const INITIAL_LEFT_WIDTH = 22;
const INITIAL_RIGHT_WIDTH = 26;
const MIN_LEFT_WIDTH = 18;
const MAX_LEFT_WIDTH = 30;
const MIN_RIGHT_WIDTH = 22;
const MAX_RIGHT_WIDTH = 34;

export default function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState(getApiBaseUrl());
  const [jobIdInput, setJobIdInput] = useState('');
  const [sessionName, setSessionName] = useState('workbench-demo');
  const [notesJson, setNotesJson] = useState(
    '{\n  "抖音2026522-387724.mp4": "请分析这个真实样例视频的脚本结构、节奏结构、包装与声音，并输出迁移建议。"\n}',
  );
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [workbenchData, setWorkbenchData] = useState<WorkbenchData | null>(null);
  const [selectedVideoId, setSelectedVideoId] = useState('');
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [prompt, setPrompt] = useState('请帮我分析这个视频的节奏结构');
  const [intentResult, setIntentResult] = useState<IntentResponse | null>(null);
  const [activeTab, setActiveTab] = useState<PanelTab>('overview');
  const [timelineFilter, setTimelineFilter] = useState<TimelineFilter>('all');
  const [leftWidth, setLeftWidth] = useState(INITIAL_LEFT_WIDTH);
  const [rightWidth, setRightWidth] = useState(INITIAL_RIGHT_WIDTH);
  const [isBusy, setIsBusy] = useState(false);
  const [message, setMessage] = useState('上传样例视频或输入已有 job id，即可在独立前端工作台中查看分析结果。');
  const [error, setError] = useState('');
  const playerRef = useRef<HTMLVideoElement | null>(null);

  const selectedVideo = workbenchData?.viewModel.videos.find((video) => video.sample_id === selectedVideoId) ?? null;
  const visibleTimeline = selectedVideo?.timeline.filter((segment) => {
    if (timelineFilter === 'all') {
      return true;
    }
    return segment.segment_type === timelineFilter;
  }) ?? [];

  useEffect(() => {
    if (!selectedVideo) {
      return;
    }

    const activeSegment = findCurrentSegment(selectedVideo.timeline, currentTime);
    if (activeSegment && activeSegment.segment_id !== selectedSegmentId) {
      setSelectedSegmentId(activeSegment.segment_id);
    }
  }, [currentTime, selectedSegmentId, selectedVideo]);

  useEffect(() => {
    if (!workbenchData?.viewModel.videos.length) {
      return;
    }
    if (!selectedVideoId) {
      setSelectedVideoId(workbenchData.viewModel.videos[0].sample_id);
      setSelectedSegmentId(workbenchData.viewModel.videos[0].timeline[0]?.segment_id ?? null);
      setCurrentTime(0);
    }
  }, [selectedVideoId, workbenchData]);

  async function handleLoadJob() {
    if (!jobIdInput.trim()) {
      setError('请输入 job id。');
      return;
    }

    setIsBusy(true);
    setError('');
    setMessage('正在从后端拉取工作台视图模型...');

    try {
      const data = await fetchWorkbenchData(jobIdInput.trim(), apiBaseUrl);
      applyWorkbenchData(data);
      setMessage(`已加载任务 ${data.viewModel.job_id}，共 ${data.viewModel.video_count} 个视频。`);
    } catch (loadError) {
      setError(normalizeError(loadError));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleUpload() {
    if (!selectedFiles.length) {
      setError('请先选择至少一个视频文件。');
      return;
    }

    setIsBusy(true);
    setError('');
    setMessage('正在上传并触发分析任务...');

    try {
      const job = await uploadAnalysisJob(selectedFiles, sessionName, notesJson, apiBaseUrl);
      setJobIdInput(job.job_id);
      const data = await fetchWorkbenchData(job.job_id, apiBaseUrl);
      applyWorkbenchData(data);
      setMessage(`分析任务已完成，当前 job id: ${job.job_id}`);
    } catch (uploadError) {
      setError(normalizeError(uploadError));
    } finally {
      setIsBusy(false);
    }
  }

  async function handlePromptSubmit(customPrompt?: string) {
    if (!selectedVideo) {
      setError('请先加载一个分析任务并选中视频。');
      return;
    }

    const text = (customPrompt ?? prompt).trim();
    if (!text) {
      setError('请输入分析指令。');
      return;
    }

    setIsBusy(true);
    setError('');
    setMessage('正在调用意图路由接口...');

    try {
      const result = await detectIntent(text, selectedVideo.sample_id, apiBaseUrl);
      setIntentResult(result);
      setPrompt(text);
      setMessage(`已解析意图：${result.intent}（${Math.round(result.confidence * 100)}%）`);
    } catch (intentError) {
      setError(normalizeError(intentError));
    } finally {
      setIsBusy(false);
    }
  }

  function applyWorkbenchData(data: WorkbenchData) {
    setWorkbenchData(data);
    const firstVideo = data.viewModel.videos[0] ?? null;
    setSelectedVideoId(firstVideo?.sample_id ?? '');
    setSelectedSegmentId(firstVideo?.timeline[0]?.segment_id ?? null);
    setIntentResult(null);
    setActiveTab('overview');
    setTimelineFilter('all');
    setCurrentTime(0);
  }

  function handleSelectVideo(videoId: string) {
    setSelectedVideoId(videoId);
    const video = workbenchData?.viewModel.videos.find((item) => item.sample_id === videoId) ?? null;
    setSelectedSegmentId(video?.timeline[0]?.segment_id ?? null);
    setCurrentTime(0);
    setIntentResult(null);
    setMessage(`已切换到 ${video?.video.filename ?? '新视频'}，分析上下文已刷新。`);
    if (playerRef.current) {
      playerRef.current.currentTime = 0;
    }
  }

  function handleSegmentFocus(segment: TimelineSegment) {
    setSelectedSegmentId(segment.segment_id);
    setCurrentTime(segment.start_seconds);
    if (playerRef.current) {
      playerRef.current.currentTime = segment.start_seconds;
      void playerRef.current.play().catch(() => {
        // Ignore autoplay rejections; seeking is the primary interaction.
      });
    }
  }

  function startResize(side: 'left' | 'right', event: ReactPointerEvent<HTMLDivElement>) {
    const startX = event.clientX;
    const startLeft = leftWidth;
    const startRight = rightWidth;

    const handleMove = (moveEvent: PointerEvent) => {
      const deltaPercent = (moveEvent.clientX - startX) / window.innerWidth * 100;

      if (side === 'left') {
        setLeftWidth(clamp(startLeft + deltaPercent, MIN_LEFT_WIDTH, MAX_LEFT_WIDTH));
        return;
      }

      setRightWidth(clamp(startRight - deltaPercent, MIN_RIGHT_WIDTH, MAX_RIGHT_WIDTH));
    };

    const handleUp = () => {
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
    };

    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup', handleUp);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Analysis Workbench</p>
          <h1>独立前端分析工作台</h1>
        </div>
        <div className="status-bar">
          <span>{isBusy ? '处理中' : '就绪'}</span>
          <span>API: {apiBaseUrl || 'Vite proxy -> 127.0.0.1:8000'}</span>
        </div>
      </header>

      <main
        className="workbench-grid"
        style={{
          gridTemplateColumns: `${leftWidth}fr 12px minmax(520px, ${100 - leftWidth - rightWidth}fr) 12px ${rightWidth}fr`,
        }}
      >
        <aside className="pane sidebar">
          <section className="card">
            <h2>连接后端</h2>
            <label>
              API Base URL
              <input value={apiBaseUrl} onChange={(event) => setApiBaseUrl(event.target.value)} />
            </label>
            <label>
              已有 Job ID
              <div className="inline-group">
                <input
                  value={jobIdInput}
                  onChange={(event) => setJobIdInput(event.target.value)}
                  placeholder="输入现有分析任务 ID"
                />
                <button onClick={handleLoadJob} disabled={isBusy}>
                  加载
                </button>
              </div>
            </label>
          </section>

          <section className="card">
            <h2>新建分析任务</h2>
            <label>
              Session Name
              <input value={sessionName} onChange={(event) => setSessionName(event.target.value)} />
            </label>
            <label>
              选择视频
              <input
                type="file"
                accept="video/*"
                multiple
                onChange={(event) => setSelectedFiles(Array.from(event.target.files ?? []))}
              />
            </label>
            <label>
              Notes JSON
              <textarea value={notesJson} onChange={(event) => setNotesJson(event.target.value)} rows={5} />
            </label>
            <button className="primary" onClick={handleUpload} disabled={isBusy}>
              上传并分析
            </button>
          </section>

          <section className="card">
            <div className="section-title">
              <h2>资源区</h2>
              <span>{workbenchData?.viewModel.video_count ?? 0} videos</span>
            </div>
            <div className="video-list">
              {workbenchData?.viewModel.videos.map((video) => (
                <button
                  key={video.sample_id}
                  className={`video-item ${video.sample_id === selectedVideoId ? 'active' : ''}`}
                  onClick={() => handleSelectVideo(video.sample_id)}
                >
                  <strong>{video.video.filename}</strong>
                  <span>{formatSeconds(video.video.duration_seconds)}</span>
                </button>
              ))}
              {!workbenchData?.viewModel.videos.length && (
                <p className="empty-state">加载任务后，这里会显示当前 session 的视频列表。</p>
              )}
            </div>
          </section>
        </aside>

        <div className="divider" onPointerDown={(event) => startResize('left', event)} />

        <section className="pane main-pane">
          <div className="hero-card">
            <div>
              <p className="eyebrow">Main Workspace</p>
              <h2>{selectedVideo?.video.filename ?? '等待载入视频'}</h2>
            </div>
            <p className="muted">桌面优先的 React + TypeScript 工作台，播放器、时间轴与右栏结果实时联动。</p>
          </div>

          <div className="player-card">
            {selectedVideo?.video.preview_url ? (
              <video
                key={selectedVideo.sample_id}
                ref={playerRef}
                controls
                className="player"
                src={selectedVideo.video.preview_url}
                onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
              />
            ) : (
              <div className="player-placeholder">当前视频没有可用的预览地址。</div>
            )}
            <div className="player-meta">
              <span>当前时间 {formatSeconds(currentTime)}</span>
              <span>总时长 {formatSeconds(selectedVideo?.video.duration_seconds ?? 0)}</span>
            </div>
          </div>

          <div className="card timeline-card">
            <div className="section-title">
              <h2>时间轴</h2>
              <div className="pill-group">
                {(['all', 'script', 'pace'] as TimelineFilter[]).map((filterKey) => (
                  <button
                    key={filterKey}
                    className={timelineFilter === filterKey ? 'pill active' : 'pill'}
                    onClick={() => setTimelineFilter(filterKey)}
                  >
                    {filterKey === 'all' ? '全部' : filterKey === 'script' ? '脚本结构' : '节奏结构'}
                  </button>
                ))}
              </div>
            </div>

            <div className="timeline-track">
              {visibleTimeline.map((segment) => {
                const duration = selectedVideo?.video.duration_seconds || 1;
                const left = clampPercent(segment.start_seconds / duration * 100);
                const width = clampPercent((segment.end_seconds - segment.start_seconds) / duration * 100);
                const isActive = segment.segment_id === selectedSegmentId;
                return (
                  <button
                    key={segment.segment_id}
                    className={`segment-chip ${segment.segment_type} ${isActive ? 'active' : ''}`}
                    style={{ left: `${left}%`, width: `${Math.max(width, 6)}%` }}
                    onClick={() => handleSegmentFocus(segment)}
                    title={`${segment.title}\n${segment.summary}\n${formatSeconds(segment.start_seconds)} - ${formatSeconds(segment.end_seconds)}`}
                  >
                    <span>{segment.title}</span>
                  </button>
                );
              })}
              {!visibleTimeline.length && <div className="empty-state">当前视频还没有时间轴片段。</div>}
            </div>

            <div className="timeline-list">
              {visibleTimeline.map((segment) => (
                <button
                  key={segment.segment_id}
                  className={`timeline-row ${segment.segment_id === selectedSegmentId ? 'active' : ''}`}
                  onClick={() => handleSegmentFocus(segment)}
                >
                  <span>{segment.title}</span>
                  <span>{formatSeconds(segment.start_seconds)} - {formatSeconds(segment.end_seconds)}</span>
                  <small>{segment.summary}</small>
                </button>
              ))}
            </div>
          </div>
        </section>

        <div className="divider" onPointerDown={(event) => startResize('right', event)} />

        <aside className="pane inspector">
          <section className="card">
            <div className="section-title">
              <h2>分析区</h2>
              <span>{selectedVideo ? '已绑定当前视频' : '未选择视频'}</span>
            </div>
            <label>
              自然语言输入
              <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} rows={4} />
            </label>
            <div className="quick-actions">
              {QUICK_ACTIONS.map((action) => (
                <button key={action} className="secondary" onClick={() => void handlePromptSubmit(action)} disabled={isBusy}>
                  {action}
                </button>
              ))}
            </div>
            <button className="primary" onClick={() => void handlePromptSubmit()} disabled={isBusy}>
              发送分析指令
            </button>
            {intentResult && (
              <div className="intent-box">
                <strong>{intentResult.intent}</strong>
                <span>scope: {intentResult.analysis_scope}</span>
                <span>source: {intentResult.source}</span>
                <span>confidence: {Math.round(intentResult.confidence * 100)}%</span>
              </div>
            )}
          </section>

          <section className="card result-card">
            <div className="pill-group">
              {([
                ['overview', '概览'],
                ['script', '脚本结构'],
                ['pace', '节奏结构'],
                ['risks', '风险提示'],
                ['raw', '原始结果'],
              ] as Array<[PanelTab, string]>).map(([tabKey, label]) => (
                <button
                  key={tabKey}
                  className={activeTab === tabKey ? 'pill active' : 'pill'}
                  onClick={() => setActiveTab(tabKey)}
                >
                  {label}
                </button>
              ))}
            </div>
            {selectedVideo ? <ResultPanel video={selectedVideo} rawResult={workbenchData?.rawResult ?? null} activeTab={activeTab} onFocusSegment={handleSegmentFocus} /> : <p className="empty-state">请选择左侧视频查看结果。</p>}
          </section>

          <section className="card info-card">
            <h2>状态</h2>
            <p>{message}</p>
            {error && <p className="error-text">{error}</p>}
          </section>
        </aside>
      </main>
    </div>
  );
}

function ResultPanel({
  video,
  rawResult,
  activeTab,
  onFocusSegment,
}: {
  video: VideoViewModel;
  rawResult: WorkbenchData['rawResult'] | null;
  activeTab: PanelTab;
  onFocusSegment: (segment: TimelineSegment) => void;
}) {
  if (activeTab === 'overview') {
    return (
      <div className="panel-stack">
        <div className="overview-box">
          <strong>转写概览</strong>
          <p>{video.panels.overview.transcript_overview || '暂无转写概览'}</p>
        </div>
        <div className="overview-box">
          <strong>可用性</strong>
          <pre>{JSON.stringify(video.panels.overview.availability ?? {}, null, 2)}</pre>
        </div>
      </div>
    );
  }

  if (activeTab === 'script') {
    const scriptSegments = video.timeline.filter((segment) => segment.segment_type === 'script');
    return (
      <div className="panel-stack">
        {scriptSegments.map((segment) => (
          <button key={segment.segment_id} className="result-item" onClick={() => onFocusSegment(segment)}>
            <strong>{segment.title}</strong>
            <span>{formatSeconds(segment.start_seconds)} - {formatSeconds(segment.end_seconds)}</span>
            <p>{segment.summary}</p>
          </button>
        ))}
      </div>
    );
  }

  if (activeTab === 'pace') {
    const paceSegments = video.timeline.filter((segment) => segment.segment_type === 'pace');
    return (
      <div className="panel-stack">
        <div className="overview-box">
          <strong>整体节奏</strong>
          <p>{video.panels.pace.overall_pace || '暂无'}</p>
        </div>
        {paceSegments.map((segment) => (
          <button key={segment.segment_id} className="result-item pace" onClick={() => onFocusSegment(segment)}>
            <strong>{segment.title}</strong>
            <span>{formatSeconds(segment.start_seconds)} - {formatSeconds(segment.end_seconds)}</span>
            <p>{segment.summary}</p>
          </button>
        ))}
      </div>
    );
  }

  if (activeTab === 'risks') {
    const risks = video.panels.risks ?? [];
    return (
      <div className="panel-stack">
        {risks.length ? risks.map((risk) => <div key={risk} className="risk-box">{risk}</div>) : <p className="empty-state">暂无风险提示。</p>}
      </div>
    );
  }

  return <pre className="raw-json">{JSON.stringify(rawResult, null, 2)}</pre>;
}

function findCurrentSegment(segments: TimelineSegment[], currentTime: number) {
  return segments.find((segment) => currentTime >= segment.start_seconds && currentTime <= segment.end_seconds) ?? null;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function normalizeError(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }
  return '发生了未知错误。';
}
