import { cn } from '@/lib/utils'
import { Layout } from '@/components/layout/Layout'
import { AnalysisUpload } from '@/components/analysis/AnalysisUpload'
import { AnalysisResultView } from '@/components/analysis/AnalysisResult'
import { JobList } from '@/components/analysis/JobList'
import { useAppStore } from '@/store/appStore'
import { useEffect, useState } from 'react'
import { 
  Image, Video, FileText, Layers, 
  ChevronLeft, ChevronRight, AlertCircle
} from 'lucide-react'
import { Tabs } from '@/components/ui/Tabs'
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
  const { currentJobId, jobs, setCurrentJob, sidebarOpen, toggleSidebar } = useAppStore()
  const currentJob = jobs.find(j => j.id === currentJobId)
  useEffect(() => {
    if (currentJob?.type) setActiveMode(currentJob.type)
  }, [currentJobId, currentJob?.type])

  const handleAnalyzeComplete = (jobId: string) => {
    setCurrentJob(jobId)
  }

  const handleModeChange = (tabId: string) => {
    setActiveMode(tabId as Mode)
    setCurrentJob(null)
  }

  // Only show the result view for a *completed* job of the *same mode* that
  // actually has a result payload. Failed or stale jobs used to crash the
  // whole app here (result was undefined -> Object.entries(undefined)).
  const showResult =
    currentJob !== undefined &&
    currentJob.type === activeMode &&
    currentJob.status === 'completed' &&
    currentJob.result !== undefined

  const showFailed =
    currentJob !== undefined &&
    currentJob.type === activeMode &&
    currentJob.status === 'failed'

  return (
    <Layout>
      <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
        {/* Sidebar */}
        <aside className={cn(
          'fixed inset-y-16 left-0 z-50 lg:static lg:z-auto flex-col shrink-0 transition-all duration-300 bg-white border-r border-gray-200',
          sidebarOpen ? 'flex w-80' : 'hidden lg:flex lg:w-20'
        )}>
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className={cn('font-semibold text-gray-900', !sidebarOpen && 'hidden')}>
                Analyses
              </h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleSidebar}
                aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
              >
                {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              </Button>
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto">
            {sidebarOpen && <JobList />}
          </div>
          
          <div className="p-4 border-t border-gray-200">
            <div className="text-xs text-gray-500 text-center">
              {jobs.length} {jobs.length === 1 ? 'analysis' : 'analyses'} total
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Mode Tabs */}
          <div className="border-b border-gray-200 bg-white px-4">
            <div className="flex items-center justify-between gap-2">
              <Tabs
                className="min-w-0"
                tabs={modes.map(m => ({ id: m.id, label: m.label, icon: <m.icon className="w-4 h-4" /> }))}
                activeTab={activeMode}
                onChange={handleModeChange}
              />
              <Button className="shrink-0" variant="secondary" size="sm" onClick={() => setCurrentJob(null)}>New analysis</Button>
            </div>
          </div>

          {/* Content Area */}
          <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
            <div className="max-w-4xl mx-auto w-full">
              {showResult && currentJob?.result ? (
                <AnalysisResultView key={currentJob.id} result={currentJob.result} />
              ) : showFailed && currentJob ? (
                <Card className="p-6">
                  <div className="flex items-start gap-4">
                    <div className="p-3 rounded-xl bg-danger-100">
                      <AlertCircle className="w-6 h-6 text-danger-600" />
                    </div>
                    <div className="flex-1">
                      <h2 className="text-lg font-bold text-gray-900">Analysis failed</h2>
                      <p className="text-gray-500 mt-1 break-words">
                        {currentJob.error || 'The analysis request failed. Check that the backend server is running, then try again.'}
                      </p>
                      <div className="mt-4 flex gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setCurrentJob(null)}
                        >
                          Try again
                        </Button>
                      </div>
                    </div>
                  </div>
                </Card>
              ) : (
                <AnalysisUpload key={activeMode} mode={activeMode} onAnalyze={handleAnalyzeComplete} />
              )}
            </div>
          </div>
        </main>

        {/* Mobile sidebar overlay */}
        {sidebarOpen && (
          <div 
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            onClick={toggleSidebar}
            aria-hidden="true"
          />
        )}
      </div>
    </Layout>
  )
}
