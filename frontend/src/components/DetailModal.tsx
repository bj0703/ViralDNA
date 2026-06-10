import React from 'react';
import type { ResultCard as ResultCardType } from '../types';

interface DetailModalProps {
  card: ResultCardType | null;
  onClose: () => void;
}

export const DetailModal: React.FC<DetailModalProps> = ({ card, onClose }) => {
  if (!card) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      backgroundColor: 'rgba(0, 0, 0, 0.55)',
      zIndex: 9999,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 24,
    }} onClick={onClose}>
      <div
        style={{
          width: '100%',
          maxWidth: 720,
          maxHeight: '85vh',
          backgroundColor: 'var(--color-neutral-100)',
          borderRadius: 'var(--radius-xl)',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: 20,
          borderBottom: '1px solid var(--color-neutral-200)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 28 }}>{card.emoji}</span>
            <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-neutral-900)' }}>
              {card.title}
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              border: 'none',
              backgroundColor: 'var(--color-neutral-100)',
              color: 'var(--color-neutral-500)',
              fontSize: 20,
              cursor: 'pointer',
            }}
          >
            ×
          </button>
        </div>
        <div style={{ padding: 24, maxHeight: '65vh', overflowY: 'auto' }}>
          <pre style={{
            fontSize: 13,
            color: 'var(--color-neutral-700)',
            whiteSpace: 'pre-wrap',
            lineHeight: 1.7,
            fontFamily: 'monospace',
          }}>
            {JSON.stringify(card.content, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
};
