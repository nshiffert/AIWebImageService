import axios from 'axios';
import type {
  SearchRequest,
  SearchResponse,
  Image,
  GenerateRequest,
  GenerateBatchRequest,
  HealthResponse,
  StatsResponse,
  GenerationJob,
  JobStatusResponse,
} from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || 'test-key-local-dev-only';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Public API (requires API key)
export const searchImages = async (request: SearchRequest): Promise<SearchResponse> => {
  const { data } = await api.post<SearchResponse>('/api/v1/search', request, {
    headers: {
      'X-API-Key': API_KEY,
    },
  });
  return data;
};

// Health check
export const healthCheck = async (): Promise<HealthResponse> => {
  const { data } = await api.get<HealthResponse>('/health');
  return data;
};

// Admin API (simplified auth for local dev)
let authToken: string | null = null;

export const setAuthToken = (token: string | null) => {
  authToken = token;
};

const getAuthHeaders = () => ({
  ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
});

export const generateImage = async (request: GenerateRequest) => {
  const { data } = await api.post('/api/admin/generate', request, {
    headers: getAuthHeaders(),
  });
  return data;
};

export const generateBatch = async (request: GenerateBatchRequest): Promise<GenerationJob> => {
  const { data } = await api.post<GenerationJob>('/api/admin/generate/batch', request, {
    headers: getAuthHeaders(),
  });
  return data;
};

export const getJobStatus = async (jobId: string): Promise<JobStatusResponse> => {
  const { data } = await api.get<JobStatusResponse>(`/api/admin/jobs/${jobId}/status`, {
    headers: getAuthHeaders(),
  });
  return data;
};

export const getJobDetails = async (jobId: string): Promise<GenerationJob> => {
  const { data } = await api.get<GenerationJob>(`/api/admin/jobs/${jobId}`, {
    headers: getAuthHeaders(),
  });
  return data;
};

export const getReviewQueue = async (limit = 20): Promise<{ images: Image[]; total: number }> => {
  const { data } = await api.get('/api/admin/images/review', {
    params: { limit },
    headers: getAuthHeaders(),
  });
  return data;
};

export const approveImage = async (imageId: string, overrideTags?: string[]) => {
  const { data } = await api.post(
    `/api/admin/images/${imageId}/approve`,
    { override_tags: overrideTags },
    { headers: getAuthHeaders() }
  );
  return data;
};

export const deleteImage = async (imageId: string) => {
  const { data } = await api.delete(`/api/admin/images/${imageId}`, {
    headers: getAuthHeaders(),
  });
  return data;
};

export const getStats = async (): Promise<StatsResponse> => {
  const { data } = await api.get<StatsResponse>('/api/admin/stats', {
    headers: getAuthHeaders(),
  });
  return data;
};

// Meta prompt configuration (stored in localStorage for now)
export const getMetaPrompt = (): string => {
  return localStorage.getItem('metaPrompt') ||
    'Professional product photography, hyper-realistic, taken with natural lighting, clean background, high quality';
};

export const setMetaPrompt = (prompt: string): void => {
  localStorage.setItem('metaPrompt', prompt);
};

// Image URL helper
export const getImageUrl = (storagePath: string): string => {
  return `${API_URL}/storage/${storagePath}`;
};
