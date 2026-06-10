import React from 'react';
import type { AgentNode, AgentStatus } from '../types';

interface AgentNodeProgressProps {
  nodes: AgentNode[];
}

const statusCircleStyle: Record<AgentStatus, React.CSSProperties> = {
  pending: {
    width: 24,
    height: 24,
    borderRadius: '50%',
    border: '2px solid var(--color-neutral-300)',
    backgroundColor: 'transparent',
  },
  running: {
    width: 24,
    height: 24,
    borderRadius: '50%',
    backgroundColor: 'var(--color-primary-500)',
    animation: 'breathing 1.5s ease-in-out infinite',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
  },
  done: {
    width: 24,
    height: 24,
    borderRadius: '50%',
    backgroundColor: 'var(--color-neutral-900)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontSize: 13,
  },
  skipped: {
    width: 24,
    height: 24,
    borderRadius: '50%',
    backgroundColor: 'var(--color-neutral-300)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--color-neutral-500)',
    fontSize: 13,
  },
  error: {
    width: 24,
    height: 24,
    borderRadius: '50%',
    backgroundColor: 'var(--color-error)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontSize: 13,
  },
};

export const AgentNodeProgress: React.FC<AgentNodeProgressProps> = ({ nodes }) => {
  return (
    <div style={{
      height: 56,
      display: 'flex',
      alignItems: 'center',
      paddingTop: 8,
      paddingBottom: 8,
      paddingLeft: 16,
      paddingRight: 16,
      borderBottom: '1px solid var(--color-neutral-200)',
      overflowX: 'auto',
      overflowY: 'hidden', // 或者 'auto' / 'scroll'
      gap: 6,
    }}>
      {nodes.map((node, index) => (
        <React.Fragment key={node.id}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, flexShrink: 0 }}>
            <div style={statusCircleStyle[node.status]}>
              {node.status === 'done' && '✓'}
              {node.status === 'skipped' && '→'}
              {node.status === 'error' && '✕'}
              {node.status === 'running' && '⚡'}
            </div>
            <span style={{ fontSize: 10, color: 'var(--color-neutral-500)', whiteSpace: 'nowrap' }}>
              {node.name}
            </span>
          </div>
          {index < nodes.length - 1 && (
            <div style={{
              flex: 1,
              height: 2,
              minWidth: 16,
              backgroundColor: node.status === 'done' ? 'var(--color-primary-500)' : 'var(--color-neutral-200)',
            }} />
          )}
        </React.Fragment>
      ))}
      <style>{`
        @keyframes breathing {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.15); opacity: 0.85; }
        }
      `}</style>
    </div>
  );
};
