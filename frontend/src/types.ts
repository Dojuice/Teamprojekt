export interface FileAttachment {
  name: string;
  type: 'exam' | 'solution';
  file: File;
}

export interface ChatMessageData {
  id: number;
  sender: 'bot' | 'user';
  text: string;
  files: FileAttachment[];
  streaming?: boolean;
}

export interface ChatSummary {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}
