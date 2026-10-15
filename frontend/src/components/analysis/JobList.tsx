import { cn } from '@/lib/utils'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { 
  Clock, CheckCircle, AlertCircle, Loader2, X, 
  Image, Video, FileText, Layers
} from 'lucide-react'
import { AnalysisJob } from '@/store/appStore'
import { useAppStore } from '@/store/appStore'

const typeIcons = {
  image: Image,
  video: Video,
  text: FileText,
  multimodal: Layers,
} as const

const getTypeIconComponent = (type: AnalysisJob['type']) => {
  return typeIcons[type] as React.ComponentType<React.SVGProps<SVGSVGElement>>
}

const typeLabels = {
  image: 'Image',
  video: 'Video',
  text: 'Text',
  multimodal: 'Multimodal',
}

const statusConfig = {
  pending: { icon: Clock, color: 'text-gray-500', bg: 'bg-gray-100', label: 'Pending' },
  processing: { icon: Loader2, color: 'text-primary-600', bg: 'bg-primary-100', label: 'Processing' },
  completed: { icon: CheckCircle, color: 'text-success-600', bg: 'bg-success-100', label: 'Completed' },
  failed: { icon: AlertCircle, color: 'text-danger-600', bg: 'bg-danger-100', label: 'Failed' },
}

export const JobList = () => {
  const { jobs, currentJobId, removeJob, setCurrentJob } = useAppStore()

  if (jobs.length === 0) {
    return (
      <Card className="py-12 text-center">
        <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
          <Clock className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900">No analyses yet</h3>
        <p className="text-sm text-gray-500 mt-1">Upload a file or paste text to start analyzing</p>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      {jobs.map((job) => (
        <JobItem key={job.id} job={job} isActive={currentJobId === job.id} />
      ))}
    </div>
  )
}

interface JobItemProps {
  job: AnalysisJob
  isActive: boolean
}

const JobItem = ({ job, isActive }: JobItemProps) => {
  const { removeJob, setCurrentJob } = useAppStore()
  const { icon: StatusIcon, color, bg, label: statusLabel } = statusConfig[job.status]
  const TypeIcon = getTypeIconComponent(job.type)

  const handleClick = () => setCurrentJob(job.id)
  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation()
    removeJob(job.id)
  }

  return (
    <Card
      className={cn(
        'cursor-pointer transition-all',
        isActive ? 'border-primary-500 bg-primary-50' : 'hover:border-primary-300'
      )}
      onClick={handleClick}
    >
      <div className="flex items-center gap-4 p-4">
        <div className={cn('p-2 rounded-lg', job.status === 'processing' ? 'bg-primary-100' : 'bg-gray-100')}>
          <TypeIcon className="w-5 h-5 text-gray-600" />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="font-medium text-gray-900 truncate">{typeLabels[job.type]}</h4>
            <Badge variant={job.status === 'failed' ? 'danger' : job.status === 'completed' ? 'success' : job.status === 'processing' ? 'info' : 'default'} size="sm">
              {statusLabel}
            </Badge>
          </div>
          
          {job.status === 'processing' && (
            <div className="mt-2 flex items-center gap-2">
              <Progress value={job.progress} size="sm" color="primary" className="flex-1" />
              <span className="text-xs text-gray-500">{job.progress}%</span>
            </div>
          )}
          
          {job.status === 'completed' && job.result && (
            <div className="mt-2 flex items-center gap-4 text-sm text-gray-500">
              <span className="flex items-center gap-1">
                <span className={cn('font-semibold', job.result.status === 'suspicious' ? 'text-danger-600' : 'text-success-600')}>
                  {job.result.status.toUpperCase()}
                </span>
              </span>
              <span>Confidence: {(job.result.confidence * 100).toFixed(1)}%</span>
              <span>{new Date(job.createdAt).toLocaleTimeString()}</span>
            </div>
          )}
          
          {job.status === 'failed' && job.error && (
            <p className="mt-1 text-sm text-danger-600 truncate">{job.error}</p>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          {job.status === 'processing' && (
            <StatusIcon className={cn('w-5 h-5 animate-spin', color)} />
          )}
          {job.status !== 'processing' && (
            <StatusIcon className={cn('w-5 h-5', color)} />
          )}
          <button
            onClick={handleRemove}
            className="p-1 text-gray-400 hover:text-danger-600 hover:bg-danger-50 rounded transition-colors"
            aria-label="Remove analysis"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </Card>
  )
}

export const JobHistory = () => {
  const { jobs, removeJob } = useAppStore()
  const completedJobs = jobs.filter(j => j.status === 'completed' || j.status === 'failed')

  if (completedJobs.length === 0) {
    return (
      <Card className="py-8 text-center">
        <p className="text-gray-500">No completed analyses</p>
      </Card>
    )
  }

  return (
    <Card>
      <div className="p-4 border-b border-gray-200">
        <h3 className="font-semibold text-gray-900">Recent Analyses</h3>
      </div>
      <div className="divide-y divide-gray-200">
        {completedJobs.slice(0, 10).map((job) => {
          const TypeIcon = getTypeIconComponent(job.type)
          return (
            <div key={job.id} className="p-4 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <TypeIcon className="w-5 h-5 text-gray-400" />
                  <div>
                    <p className="font-medium text-gray-900">{typeLabels[job.type]}</p>
                    <p className="text-xs text-gray-500">{new Date(job.createdAt).toLocaleString()}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {job.result && (
                    <Badge variant={job.result.status === 'suspicious' ? 'danger' : 'success'} size="sm">
                      {job.result.status}
                    </Badge>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      removeJob(job.id)
                    }}
                    className="text-gray-400 hover:text-danger-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}