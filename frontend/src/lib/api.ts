import axios from 'axios'

const API_BASE_URL = '/api'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Health endpoints
export const healthApi = {
  check: () => api.get('/health').then(r => r.data),
  ready: () => api.get('/health/ready').then(r => r.data),
  status: () => api.get('/health/status').then(r => r.data),
}

// Content endpoints
export const contentApi = {
  generate: (topic: string, autoApprove?: boolean, includeTrends?: boolean) =>
    api.post('/content/generate', { topic, auto_approve: autoApprove, include_trends: includeTrends })
      .then(r => r.data),
  
  generateBatch: (topics: string[], maxConcurrent?: number) =>
    api.post('/content/generate/batch', topics, {
      params: { max_concurrent: maxConcurrent },
    }).then(r => r.data),
  
  getQueue: () => api.get('/content/queue').then(r => r.data),
  
  getBriefs: (status?: string, limit?: number, offset?: number) =>
    api.get('/content/briefs', { params: { status, limit, offset } }).then(r => r.data),
  
  getBrief: (id: string) => api.get(`/content/briefs/${id}`).then(r => r.data),
  
  approveBrief: (id: string) => api.post(`/content/briefs/${id}/approve`).then(r => r.data),
  
  rejectBrief: (id: string, reason?: string) =>
    api.post(`/content/briefs/${id}/reject`, null, { params: { reason } }).then(r => r.data),
  
  getTrending: (limit?: number) =>
    api.get('/content/trending', { params: { limit } }).then(r => r.data),
}

// Competitor endpoints
export const competitorsApi = {
  list: (platform?: string, activeOnly?: boolean) =>
    api.get('/competitors/accounts', { params: { platform, active_only: activeOnly } })
      .then(r => r.data),
  
  create: (platform: string, username: string, scraperEnabled?: boolean) =>
    api.post('/competitors/accounts', { platform, username, is_scraper_enabled: scraperEnabled })
      .then(r => r.data),
  
  delete: (id: string) => api.delete(`/competitors/accounts/${id}`).then(r => r.data),
  
  scrape: (id: string, limit?: number, daysBack?: number) =>
    api.post(`/scraping/accounts/${id}/scrape`, { limit, days_back: daysBack })
      .then(r => r.data),
  
  getSummary: () => api.get('/competitors/summary').then(r => r.data),
  
  getContent: (platform?: string, minViralScore?: number, limit?: number, offset?: number) =>
    api.get('/scraping/content', { params: { platform, min_viral_score: minViralScore, limit, offset } })
      .then(r => r.data),
  
  getTrends: (daysBack?: number) =>
    api.get('/scraping/analysis/trends', { params: { days_back: daysBack } })
      .then(r => r.data),
}

// Rendering endpoints
export const renderingApi = {
  render: (briefId: string, voice?: string, includeMusic?: boolean, visualStyle?: object) =>
    api.post('/rendering/render', {
      brief_id: briefId,
      voice,
      include_music: includeMusic,
      visual_style: visualStyle,
    }).then(r => r.data),
  
  getJobStatus: (jobId: string) => api.get(`/rendering/jobs/${jobId}`).then(r => r.data),
  
  getVideos: (briefId?: string, status?: string, limit?: number) =>
    api.get('/rendering/videos', { params: { brief_id: briefId, status, limit } })
      .then(r => r.data),
  
  getVideo: (id: string) => api.get(`/rendering/videos/${id}`).then(r => r.data),
  
  publishVideo: (id: string) => api.post(`/rendering/videos/${id}/publish`).then(r => r.data),
  
  getVoices: () => api.get('/rendering/voices').then(r => r.data),
}

// Analytics endpoints
export const analyticsApi = {
  record: (videoId: string, views: number, likes: number, comments: number, shares: number, saves?: number) =>
    api.post('/analytics/record', { video_id: videoId, views, likes, comments, shares, saves })
      .then(r => r.data),

  getVideoAnalytics: (videoId: string) =>
    api.get(`/analytics/videos/${videoId}`).then(r => r.data),

  getOverview: (days?: number) =>
    api.get('/analytics/overview', { params: { days } }).then(r => r.data),

  getFeedback: (limit?: number) =>
    api.get('/analytics/feedback', { params: { limit } }).then(r => r.data),
}

// Settings endpoints
export const settingsApi = {
  getAll: (category?: string) =>
    api.get('/settings', category ? { params: { category } } : {}).then(r => r.data),

  get: (key: string) =>
    api.get(`/settings/${key}`).then(r => r.data),

  update: (key: string, value: any, valueType: string = 'string') =>
    api.put(`/settings/${key}`, { value, value_type: valueType }).then(r => r.data),

  delete: (key: string) =>
    api.delete(`/settings/${key}`).then(r => r.data),

  getCategories: () =>
    api.get('/settings/categories').then(r => r.data),
}

export default api