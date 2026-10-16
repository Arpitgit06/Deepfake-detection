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

export interface AnalysisResult {
  analysis_id: string
  status: string
  confidence: number
  results: Record<string, any>
  explanations: Explanation[]
  processing_time_ms: number
  timestamp: string
  llm_summary?: string
}

export interface Explanation {
  type: string
  message: string
  severity: 'success' | 'warning' | 'error' | 'info'
  details?: Record<string, any>
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