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

export interface EvaluationResultItem {
  filename: string;
  student_name: string;
  overall_grade: string;
  overall_score: number;
  total_points: number | string;
  max_points: number | string;
  status: string;
  error?: string;
  downloadUrl: string;
}

export interface EvaluationResults {
  items: EvaluationResultItem[];
  chatId: number;
  totalExams: number;
  successCount: number;
  averageScore: number;
  averageGrade: string;
  downloadAllUrl?: string;
}

export interface EvalProgress {
  step: string;
  label: string;
  current: number;
  total: number;
}

export interface ChatMessageData {
  id: number;
  sender: 'bot' | 'user';
  text: string;
  files: FileAttachment[];
  streaming?: boolean;
  isNew?: boolean;
  isLoading?: boolean;
  isError?: boolean;
  downloadUrl?: string;
  downloadLabel?: string;
  evaluationResults?: EvaluationResults;
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
