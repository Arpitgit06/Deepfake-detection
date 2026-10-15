import { cn } from '@/lib/utils'
import { Layout } from '@/components/layout/Layout'
import { AnalysisUpload } from '@/components/analysis/AnalysisUpload'
import { AnalysisResultView } from '@/components/analysis/AnalysisResult'
import { JobList } from '@/components/analysis/JobList'
import { useAppStore } from '@/store/appStore'
import { useState } from 'react'
import { 
  Image, Video, FileText, Layers, 
  ChevronLeft, ChevronRight, X
} from 'lucide-react'
import { Tabs, TabPanel } from '@/components/ui/Tabs'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

const modes = [
  { id: 'image', label: 'Image', icon: Image },
  { id: 'video', label: 'Video', icon: Video },
  { id: 'text', label: 'Text', icon: FileText },
  { id: 'multimodal', label: 'Multimodal', icon: Layers },
] as const

type Mode = typeof modes[number]['id']

export const AnalysisPage = () => {
  const [activeMode, setActiveMode] = useState<Mode>('image')
  const { currentJobId, jobs, setCurrentJob } = useAppStore()
  const currentJob = jobs.find(j => j.id === currentJobId)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const handleAnalyzeComplete = (jobId: string) => {
    setCurrentJob(jobId)
  }

  const handleModeChange = (tabId: string) => {
    setActiveMode(tabId as Mode)
  }

  return (
    <Layout>
      <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
        {/* Sidebar */}
        <aside className={cn(
          'flex flex-col transition-all duration-300 bg-white border-r border-gray-200',
          sidebarOpen ? 'w-80' : 'w-20'
        )}>
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className={cn('font-semibold text-gray-900', !sidebarOpen && 'hidden')}>
                Analyses
              </h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSidebarOpen(!sidebarOpen)}
                aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
              >
                {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              </Button>
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto">
            <JobList />
          </div>
          
          <div className="p-4 border-t border-gray-200">
            <div className="text-xs text-gray-500 text-center">
              {jobs.length} analysis{jobs.length !== 1 ? 'es' : ''} total
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Mode Tabs */}
          <div className="border-b border-gray-200 bg-white px-4">
            <Tabs
              tabs={modes.map(m => ({ id: m.id, label: m.label, icon: <m.icon className="w-4 h-4" /> }))}
              activeTab={activeMode}
              onChange={handleModeChange}
            />
          </div>

          {/* Content Area */}
          <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
            <div className="max-w-4xl mx-auto w-full">
              {currentJob && currentJob.status !== 'pending' ? (
                <AnalysisResultView result={currentJob.result!} />
              ) : (
                <AnalysisUpload mode={activeMode} onAnalyze={handleAnalyzeComplete} />
              )}
            </div>
          </div>
        </main>

        {/* Mobile sidebar overlay */}
        {!sidebarOpen && (
          <div 
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            onClick={() => setSidebarOpen(true)}
            aria-hidden="true"
          />
        )}
      </div>
    </Layout>
  )
}