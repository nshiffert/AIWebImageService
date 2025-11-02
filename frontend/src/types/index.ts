// API Types
export interface Image {
  id: string;
  prompt: string;
  style: string;
  status: 'pending' | 'processing' | 'tagging' | 'ready' | 'approved' | 'rejected';
  description: string | null;
  tags: Tag[];
  created_at: string;
  approved_at: string | null;
  tagging_confidence: number | null;
}

export interface Tag {
  tag: string;
  confidence: number;
  source: 'auto' | 'manual' | 'template';
}

export interface SearchResult {
  id: string;
  storage_path: string;
  score: number;
  tags: string[];
  description: string | null;
  dominant_color: string | null;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query_time_ms: number;
}

export interface GenerateRequest {
  prompt: string;
  style?: string;
}

export interface GenerateBatchRequest {
  prompts: string[];
  style?: string;
  count_per_prompt?: number;
}

export interface HealthResponse {
  status: string;
  database: string;
  openai: string;
  timestamp: string;
}

export interface StatsResponse {
  total_images: number;
  approved_images: number;
  pending_review: number;
  total_tags: number;
  storage_used_mb: number;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: string | null;
}

// Job Tracking Types
export interface GenerationTask {
  id: string;
  job_id: string;
  prompt: string;
  style: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  image_id: string | null;
  error_message: string | null;
  retry_count: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface GenerationJob {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  created_at: string;
  completed_at: string | null;
  updated_at: string;
  tasks: GenerationTask[];
}

export interface JobStatusResponse {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  progress_percentage: number;
  created_at: string;
  completed_at: string | null;
}
