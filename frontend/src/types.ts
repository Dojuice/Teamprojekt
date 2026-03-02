export interface FileAttachment {
  name: string;
  type: 'exam' | 'solution';
  file: File;
}

export interface UploadProgress {
  total: number;
  uploaded: number;
  currentFile: string;
  status: 'uploading' | 'done' | 'error';
  errors: string[];
}

export interface ChatMessageData {
  id: number;
  sender: 'bot' | 'user';
  text: string;
  files: FileAttachment[];
  streaming?: boolean;
  isLoading?: boolean;
  isError?: boolean;
  downloadUrl?: string;
  downloadLabel?: string;
}

export interface ChatSummary {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export type AIModel = string;

export interface AIModelOption {
  id: AIModel;
  label: string;
  description: string;
  free: boolean;
}
