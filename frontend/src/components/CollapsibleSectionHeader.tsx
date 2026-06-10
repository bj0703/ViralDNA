import React from 'react';

interface CollapsibleSectionHeaderProps {
  title: string;
  count: number;
  isExpanded: boolean;
  onToggle: () => void;
  onUploadClick?: () => void;
}

export const CollapsibleSectionHeader: React.FC<CollapsibleSectionHeaderProps> = ({
  title,
  count,
  isExpanded,
  onToggle,
  onUploadClick,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingTop: 12,
        paddingBottom: 12,
        paddingLeft: 12,
        paddingRight: 12,
        borderBottom: '1px solid var(--color-neutral-200)',
      }}
    >
      <div
        style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}
        onClick={onToggle}
      >
        <span style={{ fontSize: 14 }}>{isExpanded ? '▼' : '▶'}</span>
        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-neutral-700)' }}>
          {title}
        </span>
        {count > 0 && (
          <span
            style={{
              fontSize: 11,
              padding: '2px 8px',
              borderRadius: 999,
              backgroundColor: 'var(--color-primary-50)',
              color: 'var(--color-primary-500)',
            }}
          >
            {count}
          </span>
        )}
      </div>

      {onUploadClick && (
        <button
          onClick={onUploadClick}
          style={{
            fontSize: 13,
            color: 'var(--color-primary-500)',
            backgroundColor: 'var(--color-primary-50)',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            padding: '4px 10px',
            cursor: 'pointer',
          }}
        >
          + 上传
        </button>
      )}
    </div>
  );
};
