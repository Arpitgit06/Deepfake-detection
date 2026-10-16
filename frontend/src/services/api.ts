import axios from 'axios'

const API_BASE = '/api/v1'

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 300000, // 5 minutes for video analysis
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail
    const message = Array.isArray(detail)
      ? detail.map(item => `${item.loc?.join('.') || 'Input'}: ${item.msg}`).join('; ')
      : typeof detail === 'string' ? detail
      : !error.response || error.response.status === 502
        ? 'Cannot reach the analysis server. Start the backend on port 8000 and try again.'
        : error.message || 'An error occurred'
    return Promise.reject(new Error(message))
  }
)

export interface AnalyzeImageParams {
  file: File
  return_heatmap?: boolean
  sensitivity?: number
}

export interface AnalyzeVideoParams {
  file: File
  enable_ppg?: boolean
  enable_phoneme_viseme?: boolean
  sample_rate?: number
}

export interface AnalyzeTextParams {
  text: string
  language?: string
  extract_entities?: boolean
  check_threat_intel?: boolean
}

export interface AnalyzeMultimodalParams {
  image?: File
  video?: File
  audio?: File
  text_content?: string
}

export const analyzeImage = async (params: AnalyzeImageParams) => {
  const formData = new FormData()
  formData.append('file', params.file)
  if (params.return_heatmap !== undefined) formData.append('return_heatmap', String(params.return_heatmap))
  if (params.sensitivity !== undefined) formData.append('sensitivity', String(params.sensitivity))
  
  const response = await api.post('/analyze/image', formData)
  return response.data
}

export const analyzeVideo = async (params: AnalyzeVideoParams) => {
  const formData = new FormData()
  formData.append('file', params.file)
  if (params.enable_ppg !== undefined) formData.append('enable_ppg', String(params.enable_ppg))
  if (params.enable_phoneme_viseme !== undefined) formData.append('enable_phoneme_viseme', String(params.enable_phoneme_viseme))
  if (params.sample_rate !== undefined) formData.append('sample_rate', String(params.sample_rate))
  
  const response = await api.post('/analyze/video', formData)
  return response.data
}

export const analyzeText = async (params: AnalyzeTextParams) => {
  const response = await api.post('/analyze/text', params)
  return response.data
}

export const analyzeMultimodal = async (params: AnalyzeMultimodalParams) => {
  const formData = new FormData()
  if (params.image) formData.append('image', params.image)
  if (params.video) formData.append('video', params.video)
  if (params.audio) formData.append('audio', params.audio)
  if (params.text_content) formData.append('text_content', params.text_content)
  
  const response = await api.post('/analyze/multimodal', formData)
  return response.data
}

export const getAnalysisStatus = async (analysisId: string) => {
  const response = await api.get(`/analyze/${analysisId}/status`)
  return response.data
}

export const getAnalysisReport = async (analysisId: string) => {
  const response = await api.get(`/analyze/${analysisId}/report`)
  return response.data
}

// ---- LLM (local Qwen3-4B, managed lifecycle) ----

export interface LLMAskResponse {
  answer: string | null
  model_used: string
  vram_freed_mb: number | null
}

export const askLLM = async (analysisId: string, question: string): Promise<LLMAskResponse> => {
  const response = await api.post('/llm/ask', { analysis_id: analysisId, question })
  return response.data
}

export const llmStatus = async () => {
  const response = await api.get('/llm/status')
  return response.data
}

export const llmUnload = async () => {
  const response = await api.post('/llm/unload')
  return response.data
}

export const healthCheck = async () => {
  const response = await api.get('/health')
  return response.data
}

export const detailedHealthCheck = async () => {
  const response = await api.get('/health/detailed')
  return response.data
}
