import React from 'react';
import type { UserMessage } from '../types';

interface UserMessageBubbleProps {
  message: UserMessage;
}

export const UserMessageBubble: React.FC<UserMessageBubbleProps> = ({ message }) => {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: 12, paddingBottom: 12 }}>
      <div style={{
        maxWidth: '80%',
        backgroundColor: 'var(--color-primary-500)',
        color: 'white',
        borderRadius: 'var(--radius-xl)',
        padding: '10px 16px',
        fontSize: 14,
        lineHeight: 1.5,
      }}>
        {message.content}
      </div>
    </div>
  );
};
