export interface SampleVideo {
  id: string;
  name: string;
  thumbnailUrl: string;
  file?: File;
  timestamp: number;
}

export interface MaterialVideo {
  id: string;
  name: string;
  thumbnailUrl: string;
  file?: File;
  timestamp: number;
}

export interface EditVersion {
  id: string;
  versionLabel: string;
  timestamp: number;
  thumbnailUrl: string;
}
