export interface Speaker {
  label: string;
  name: string | null;
}

export interface Decision {
  decision: string;
  rationale: string;
}

export interface ActionItem {
  task: string;
  assignee: string;
  deadline: string;
}

export interface Discussion {
  topic: string;
  context: string;
  key_arguments: string[];
  conclusion: string;
}

export interface Summary {
  executive_summary: string | null;
  topics: string[];
  decisions: Decision[];
  action_items: ActionItem[];
  discussions: Discussion[];
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
  transcripts?: Transcript[];
  summaries?: Summary[];
  speakers?: Speaker[];
}

export interface MeetingDetail extends Meeting {}
