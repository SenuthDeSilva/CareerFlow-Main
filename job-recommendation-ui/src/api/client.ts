import axios from 'axios';

const BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error?.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ── Interfaces ────────────────────────────────────────────────

export interface Stats {
  total_jobs:      number;
  rooster_jobs:    number;
  topjobs_jobs:    number;
  total_resumes:   number;
  resumes_matched: number;
  last_updated:    string;
}

export interface Resume {
  id:               number;
  candidate_name:   string;
  email:            string;
  phone:            string;
  years_experience: number;
  skills_count:     number;
  hard_skills:      string[];
  soft_skills:      string[];
  all_skills:       string[];
  file_name:        string;
  uploaded_at:      string;
  predicted_role?:  string;
  role_confidence?: number;
}

export interface Recommendation {
  job_id:           number;
  rank:             number;
  title:            string;
  company:          string;
  location:         string;
  salary:           string;
  source:           string;
  job_url:          string;
  hybrid_score:     number;
  hybrid_score_pct: number;
  tfidf_score_pct:  number;
  skill_score_pct:  number;
  word2vec_score:   number;
  ml_score:         number;
  matched_skills:   string[];
  missing_skills:   string[];
  role_match?:      boolean;
}

export interface Job {
  id:          number;
  title:       string;
  company:     string;
  location:    string;
  salary:      string;
  source:      string;
  job_url:     string;
  description: string;
  job_type:    string;
  scraped_at:  string;
}

export interface Explanation {
  job_id:           number;
  title:            string;
  company:          string;
  hybrid_score:     number;
  hybrid_score_pct: number;
  summary:          string;
  shap_explanation: {
    feature_contributions: Record<string, number>;
    why_recommended:       string[];
  };
  lime_explanation: {
    top_keywords:   string[];
    keyword_scores: Record<string, number>;
  };
}

// ── API Functions ─────────────────────────────────────────────

export const getStats = () =>
  api.get('/api/stats');

export const getResumes = () =>
  api.get('/api/resumes');

export const getResume = (id: number) =>
  api.get(`/api/resume/${id}`);

export const deleteResume = (id: number) =>
  api.delete(`/api/resume/${id}`);

export const uploadResume = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return api.post('/api/resume/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const getRecommendations = (id: number, refresh = false) =>
  api.get(`/api/recommendations/${id}?refresh=${refresh}`);

export const getExplanations = (id: number) =>
  api.get(`/api/explain/${id}?top=20`);

export const getJobs = (params: {
  source?: string;
  search?: string;
  limit?:  number;
  offset?: number;
}) => api.get('/api/jobs', { params });

export const getJob = (id: number) =>
  api.get(`/api/jobs/${id}`);

export const getModelReport = () =>
  api.get('/api/model-report');

export default api;