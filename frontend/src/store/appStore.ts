import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * crypto.randomUUID() only exists in secure contexts (https or localhost).
 * The dev server binds to 0.0.0.0, so opening the app via a LAN address over
 * plain HTTP used to crash analysis with a TypeError (white screen). This
 * fallback keeps UUIDs working everywhere.
 */
const generateId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `id-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 11)}`
}

export interface DetectorResult {
  status?: string
  confidence?: number
  ai_probability?: number | null
  raw_model_score?: number | null
  verdict_eligible?: boolean
  score_kind?: string
  decision_reason?: string
  is_deepfake?: boolean | null
  is_threat?: boolean | null
  is_synchronized?: boolean | null
  error?: string
  model_used?: string
  explanations?: Explanation[]
  metadata_evidence?: { description: string; verified: boolean }[]
  heart_rate_bpm?: number | null
  snr_db?: number
  signal_quality?: number
  sync_score?: number
  risk_score?: number
  threat_level?: string
  raw_signal?: number[] | null
  phoneme_viseme_pairs?: {
    phoneme: string; expected_viseme: string | number; observed_viseme: string | number
    match: boolean; time_diff?: number
  }[]
  entities?: { type: string; value: string; confidence: number }[]
  tactics?: { name: string; description: string; confidence: number; evidence?: string[] }[]
  region_analysis?: { preview_base64: string; limitation: string; regions: unknown[] }
}

export interface AnalysisResult {
  analysis_id: string
  status: string
  confidence: number
  results: Record<string, DetectorResult>
  explanations: Explanation[]
  processing_time_ms: number
  timestamp: string
  llm_summary?: string
  explanation_source?: string | null
  llm_review?: { status: string; assessment?: string; reason: string; scope: string }
  evidence_report?: {
    findings: { check: string; observation: string; meaning: string; score?: number }[]
    limitations: string[]
    score_note: string
  }
}

export interface Explanation {
  type: string
  message: string
  severity: 'success' | 'warning' | 'error' | 'info'
  details?: Record<string, unknown>
}

export interface AnalysisJob {
  id: string
  type: 'image' | 'video' | 'text' | 'multimodal'
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  result?: AnalysisResult
  error?: string
  createdAt: string
}

interface AppState {
  // Analysis jobs
  jobs: AnalysisJob[]
  currentJobId: string | null
  
  // UI state
  sidebarOpen: boolean
  theme: 'light' | 'dark'
  
  // Actions
  addJob: (job: Omit<AnalysisJob, 'id' | 'createdAt'>) => string
  updateJob: (id: string, updates: Partial<AnalysisJob>) => void
  removeJob: (id: string) => void
  setCurrentJob: (id: string | null) => void
  toggleSidebar: () => void
  setTheme: (theme: 'light' | 'dark') => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      jobs: [],
      currentJobId: null,
      sidebarOpen: true,
      theme: 'light',
      
      addJob: (job) => {
        const id = generateId()
        const newJob: AnalysisJob = {
          ...job,
          id,
          createdAt: new Date().toISOString(),
        }
        set((state) => ({
          jobs: [newJob, ...state.jobs],
          currentJobId: id,
        }))
        return id
      },
      
      updateJob: (id, updates) =>
        set((state) => ({
          jobs: state.jobs.map((job) =>
            job.id === id ? { ...job, ...updates } : job
          ),
        })),
      
      removeJob: (id) =>
        set((state) => ({
          jobs: state.jobs.filter((job) => job.id !== id),
          currentJobId: state.currentJobId === id ? null : state.currentJobId,
        })),
      
      setCurrentJob: (id) => set({ currentJobId: id }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'truthlens-store',
      partialize: (state) => ({ theme: state.theme, sidebarOpen: state.sidebarOpen }),
    }
  )
)
