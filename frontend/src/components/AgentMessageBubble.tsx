import React, { useState } from 'react';
import type { AgentMessage } from '../types';

interface AgentMessageBubbleProps {
  message: AgentMessage;
}

export const AgentMessageBubble: React.FC<AgentMessageBubbleProps> = ({ message }) => {
  const [isExpanded, setIsExpanded] = useState(message.thinking.isExpanded);

  return (
    <div style={{ paddingTop: 12, paddingBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <div style={{
          width: 32,
          height: 32,
          borderRadius: 'var(--radius-md)',
          backgroundColor: 'var(--color-primary-50)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--color-primary-500)',
          fontWeight: 600,
          fontSize: 14,
        }}>
          A
        </div>
        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-neutral-800)' }}>
          {message.agentName}
        </span>
      </div>

      <button
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          fontSize: 13,
          color: 'var(--color-neutral-500)',
          backgroundColor: 'var(--color-neutral-50)',
          border: '1px solid var(--color-neutral-200)',
          borderRadius: 'var(--radius-md)',
          padding: '6px 12px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}
      >
        {isExpanded ? '▼' : '▶'} 思考过程
      </button>

      {isExpanded && (
        <div style={{
          marginTop: 8,
          padding: 12,
          backgroundColor: 'var(--color-neutral-50)',
          borderRadius: 'var(--radius-lg)',
          fontSize: 13,
          color: 'var(--color-neutral-600)',
          lineHeight: 1.6,
          whiteSpace: 'pre-wrap',
        }}>
          {message.thinking.content}
        </div>
      )}
    </div>
  );
};
