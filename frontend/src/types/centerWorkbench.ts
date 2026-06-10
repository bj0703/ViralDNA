export type TabType = 'sample' | 'material' | 'result';

export interface TimelineNode {
  id: string;
  timeLabel: string;
  x: number;
  detailTitle: string;
  detailContent: string;
}

export interface MaterialItem {
  id: string;
  fileName: string;
  type: 'video' | 'audio';
  slotStatus: 'matched' | 'matching';
}

export interface ClipSegment {
  id: string;
  name: string;
  width: number;
}
