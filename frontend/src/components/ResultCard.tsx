import React from 'react';
import type { ResultCard as ResultCardType } from '../types';

interface ResultCardProps {
  card: ResultCardType;
  onClick: () => void;
}

export const ResultCard: React.FC<ResultCardProps> = ({ card, onClick }) => {
  return (
    <div
      onClick={onClick}
      style={{
        flexShrink: 0,
        width: 100,
        height: 110,
        background: 'linear-gradient(135deg, var(--color-primary-50), var(--color-primary-100))',
        borderRadius: 'var(--radius-xl)',
        border: '1px solid var(--color-primary-100)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
        transition: 'transform 0.15s ease, box-shadow 0.15s ease',
      } as React.CSSProperties}
    >
      <div style={{ fontSize: 32, marginBottom: 6 }}>{card.emoji}</div>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-primary-600)' }}>
        {card.title}
      </div>
      <div style={{ fontSize: 10, color: 'var(--color-primary-400)', marginTop: 2 }}>
        {card.agentName}
      </div>
    </div>
  );
};
