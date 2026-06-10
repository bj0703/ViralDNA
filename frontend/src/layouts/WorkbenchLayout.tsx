import React, { useState, useEffect, useCallback, useRef } from 'react';

interface WorkbenchLayoutProps {
  leftContent?: React.ReactNode;
  centerContent?: React.ReactNode;
  rightContent?: React.ReactNode;
  headerControls?: React.ReactNode;
}

const STORAGE_KEYS = {
  leftWidth: 'emo_transfer_left_width',
  rightWidth: 'emo_transfer_right_width',
};

const constrain = (value: number, min: number, max: number): number =>
  Math.max(min, Math.min(max, value));

export const WorkbenchLayout: React.FC<WorkbenchLayoutProps> = ({
  leftContent,
  centerContent,
  rightContent,
  headerControls,
}) => {
  const [leftWidth, setLeftWidth] = useState<number>(240);
  const [rightWidth, setRightWidth] = useState<number>(420);

  const leftBarRef = useRef<HTMLDivElement>(null);
  const rightBarRef = useRef<HTMLDivElement>(null);
  const isDraggingLeftRef = useRef(false);
  const isDraggingRightRef = useRef(false);

  // 从 localStorage 恢复布局
  useEffect(() => {
    const savedLeft = localStorage.getItem(STORAGE_KEYS.leftWidth);
    const savedRight = localStorage.getItem(STORAGE_KEYS.rightWidth);

    if (savedLeft) {
      const num = parseInt(savedLeft, 10);
      if (!isNaN(num)) setLeftWidth(constrain(num, 180, 400));
    }
    if (savedRight) {
      const num = parseInt(savedRight, 10);
      if (!isNaN(num)) setRightWidth(constrain(num, 360, 500));
    }
  }, []);

  // 保存布局
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.leftWidth, String(leftWidth));
  }, [leftWidth]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.rightWidth, String(rightWidth));
  }, [rightWidth]);

  // 左栏拖拽
  const onLeftDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDraggingLeftRef.current = true;
  }, []);

  // 右栏拖拽
  const onRightDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDraggingRightRef.current = true;
  }, []);

  // 全局鼠标移动
  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (isDraggingLeftRef.current) {
        const newWidth = constrain(e.clientX, 180, 400);
        // 保证中栏最小 500px
        const totalWidth = window.innerWidth;
        if (totalWidth - newWidth - rightWidth >= 500) {
          setLeftWidth(newWidth);
        }
      }
      if (isDraggingRightRef.current) {
        const newWidth = constrain(window.innerWidth - e.clientX, 360, 500);
        // 保证中栏最小 500px
        const totalWidth = window.innerWidth;
        if (totalWidth - leftWidth - newWidth >= 500) {
          setRightWidth(newWidth);
        }
      }
    };

    const onMouseUp = () => {
      isDraggingLeftRef.current = false;
      isDraggingRightRef.current = false;
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
  }, [leftWidth, rightWidth]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw' }}>
      {/* 顶部导航栏 */}
      <header
        style={{
          height: 52,
          backgroundColor: 'var(--color-neutral-100)',
          borderBottom: '1px solid var(--color-neutral-200)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingLeft: 20,
          paddingRight: 20,
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--color-primary-500)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontWeight: 'bold',
              fontSize: 16,
            }}
          >
            V
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-neutral-900)', lineHeight: 1.1 }}>
              ViralDNA
            </span>
            <span style={{ fontSize: 12, color: 'var(--color-neutral-500)', lineHeight: 1.1 }}>
              面向短视频爆款结构迁移的智能创作引擎
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {headerControls}
        </div>
      </header>

      {/* 三栏主体区 */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* 左栏 - 资源区 */}
        <div
          ref={leftBarRef}
          style={{
            width: leftWidth,
            backgroundColor: 'var(--color-neutral-100)',
            borderRight: '1px solid var(--color-neutral-200)',
            flexShrink: 0,
            overflow: 'auto',
          }}
        >
          {leftContent}
        </div>

        {/* 左-中分隔条 */}
        <div
          onMouseDown={onLeftDragStart}
          style={{
            width: 4,
            cursor: 'col-resize',
            backgroundColor: 'var(--color-neutral-200)',
            transition: 'width 0.15s ease, background-color 0.15s ease',
            flexShrink: 0,
            position: 'relative',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.width = '8px';
            e.currentTarget.style.backgroundColor = 'var(--color-primary-200)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.width = '4px';
            e.currentTarget.style.backgroundColor = 'var(--color-neutral-200)';
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: 20,
              height: 20,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-primary-500)',
              opacity: 0,
              pointerEvents: 'none',
              transition: 'opacity 0.15s ease',
            }}
            className="drag-indicator"
          >
            ⋮⋮
          </div>
        </div>

        {/* 中栏 - 主工作区 */}
        <div
          style={{
            flex: 1,
            backgroundColor: 'var(--color-neutral-50)',
            overflow: 'auto',
            minWidth: 500,
          }}
        >
          {centerContent}
        </div>

        {/* 中-右分隔条 */}
        <div
          onMouseDown={onRightDragStart}
          style={{
            width: 4,
            cursor: 'col-resize',
            backgroundColor: 'var(--color-neutral-200)',
            transition: 'width 0.15s ease, background-color 0.15s ease',
            flexShrink: 0,
            position: 'relative',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.width = '8px';
            e.currentTarget.style.backgroundColor = 'var(--color-primary-200)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.width = '4px';
            e.currentTarget.style.backgroundColor = 'var(--color-neutral-200)';
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: 20,
              height: 20,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-primary-500)',
              opacity: 0,
              pointerEvents: 'none',
              transition: 'opacity 0.15s ease',
            }}
            className="drag-indicator"
          >
            ⋮⋮
          </div>
        </div>

        {/* 右栏 - 操作区 */}
        <div
          ref={rightBarRef}
          style={{
            width: rightWidth,
            backgroundColor: 'var(--color-neutral-100)',
            borderLeft: '1px solid var(--color-neutral-200)',
            flexShrink: 0,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {rightContent}
        </div>
      </div>

      {/* hover 时拖拽指示器显示 */}
      <style>{`
        div:hover > .drag-indicator {
          opacity: 0.6 !important;
        }
      `}</style>
    </div>
  );
};
