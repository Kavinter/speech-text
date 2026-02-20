export interface Speaker {
  label: string;
  name: string | null;
}

export interface Summary {
  executive_summary: string | null;
  topics: string[];
  decisions: string[];
  action_items: string[];
  discussions: string[];
}

export interface Transcript {
  raw_text?: string;
  reconstructed_text?: string;
}

export interface Meeting {
  id: number;
  title: string;
  date: string;
  status: "pending" | "processing" | "completed" | "failed";
  audio_file_path?: string;
  duration?: number;
  transcript?: Transcript;
  summaries?: Summary[];
  speakers?: Speaker[];
}

export interface MeetingDetail extends Meeting {}
