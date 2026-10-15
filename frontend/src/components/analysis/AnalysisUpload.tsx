import { useCallback, useRef, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileImage, FileVideo, FileText, X, Loader2, CheckCircle, AlertCircle } from 'lucide-react'
import { cn, formatFileSize, validateFile } from '@/lib/utils'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { Alert } from '@/components/ui/Alert'
import { Textarea } from '@/components/ui/Textarea'
import { analyzeImage, analyzeVideo, analyzeText, analyzeMultimodal, AnalyzeImageParams, AnalyzeVideoParams, AnalyzeTextParams, AnalyzeMultimodalParams } from '@/services/api'
import { useAppStore } from '@/store/appStore'

type AnalysisMode = 'image' | 'video' | 'text' | 'multimodal'

interface FileWithPreview extends File {
  preview?: string
}

const ALLOWED_TYPES = {
  image: ['image/jpeg', 'image/png', 'image/webp'],
  video: ['video/mp4', 'video/webm', 'video/quicktime'],
  audio: ['audio/wav', 'audio/mp3', 'audio/m4a'],
}

const MAX_FILE_SIZE = 100 * 1024 * 1024 // 100MB

export const AnalysisUpload = ({ mode, onAnalyze }: { mode: AnalysisMode; onAnalyze: (jobId: string) => void }) => {
  const [files, setFiles] = useState<FileWithPreview[]>([])
  const [textContent, setTextContent] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { addJob, updateJob } = useAppStore()

  const getAllowedTypes = () => {
    switch (mode) {
      case 'image': return ALLOWED_TYPES.image
      case 'video': return ALLOWED_TYPES.video
      case 'multimodal': return [...ALLOWED_TYPES.image, ...ALLOWED_TYPES.video, ...ALLOWED_TYPES.audio]
      default: return []
    }
  }

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map((file) => {
      const validationError = validateFile(file, getAllowedTypes(), MAX_FILE_SIZE)
      if (validationError) {
        setError(validationError)
        return null
      }
      
      let preview: string | undefined
      if (mode !== 'text' && (file.type.startsWith('image/') || file.type.startsWith('video/'))) {
        preview = URL.createObjectURL(file)
      }
      
      return { ...file, preview } as FileWithPreview
    }).filter(Boolean) as FileWithPreview[]
    
    setFiles((prev) => [...prev, ...newFiles])
    setError(null)
  }, [mode])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: getAllowedTypes().reduce((acc, type) => ({ ...acc, [type]: [] }), {}),
    maxSize: MAX_FILE_SIZE,
    multiple: mode === 'multimodal',
  })

  const removeFile = (index: number) => {
    setFiles((prev) => {
      const file = prev[index]
      if (file.preview) URL.revokeObjectURL(file.preview)
      return prev.filter((_, i) => i !== index)
    })
  }

  const handleAnalyze = async () => {
    if ((mode !== 'text' && files.length === 0) || (mode === 'text' && !textContent.trim())) {
      setError('Please provide input to analyze')
      return
    }

    setIsAnalyzing(true)
    setProgress(0)
    setError(null)

    const jobId = addJob({
      type: mode,
      status: 'pending',
      progress: 0,
    })

    let progressInterval: ReturnType<typeof setInterval> | null = null

    try {
      let result
      progressInterval = setInterval(() => {
        setProgress((p) => Math.min(p + 10, 90))
      }, 500)

      switch (mode) {
        case 'image':
          result = await analyzeImage({
            file: files[0],
            return_heatmap: true,
            sensitivity: 0.5,
          } as AnalyzeImageParams)
          break
        case 'video':
          result = await analyzeVideo({
            file: files[0],
            enable_ppg: true,
            enable_phoneme_viseme: true,
            sample_rate: 5,
          } as AnalyzeVideoParams)
          break
        case 'text':
          result = await analyzeText({
            text: textContent,
            language: undefined,
            extract_entities: true,
            check_threat_intel: true,
          } as AnalyzeTextParams)
          break
        case 'multimodal':
          const imageFile = files.find(f => f.type.startsWith('image/'))
          const videoFile = files.find(f => f.type.startsWith('video/'))
          const audioFile = files.find(f => f.type.startsWith('audio/'))
          
          result = await analyzeMultimodal({
            image: imageFile,
            video: videoFile,
            audio: audioFile,
            text_content: textContent || undefined,
          } as AnalyzeMultimodalParams)
          break
      }

      if (progressInterval) clearInterval(progressInterval)
      setProgress(100)
      
      updateJob(jobId, {
        status: 'completed',
        progress: 100,
        result,
      })
      
      onAnalyze(jobId)
    } catch (err) {
      if (progressInterval) clearInterval(progressInterval)
      const message = err instanceof Error ? err.message : 'Analysis failed'
      setError(message)
      updateJob(jobId, { status: 'failed', error: message })
    } finally {
      setIsAnalyzing(false)
    }
  }

  if (mode === 'text') {
    return (
      <Card className={cn('p-6', isDragActive && 'border-primary-500 bg-primary-50')}>
        <div className="text-center mb-6">
          <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-gray-900">Text Analysis</h3>
          <p className="text-sm text-gray-500 mt-1">Paste suspicious messages, emails, or financial communications</p>
        </div>
        
        <Textarea
          value={textContent}
          onChange={(e) => setTextContent(e.target.value)}
          placeholder="Paste text here... (e.g., suspicious email, WhatsApp message, SMS)"
          rows={6}
          label="Text Content"
        />
        
        {error && <Alert variant="danger" className="mt-4">{error}</Alert>}
        
        <div className="mt-6 flex justify-end">
          <Button
            onClick={handleAnalyze}
            disabled={isAnalyzing || !textContent.trim()}
            loading={isAnalyzing}
            size="lg"
          >
            <Loader2 className="w-4 h-4" />
            Analyze Text
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card className={cn('p-6', isDragActive && 'border-primary-500 bg-primary-50')}>
      <div {...getRootProps()} className={cn('relative', isDragActive && 'border-primary-500 bg-primary-50')}>
        <input {...getInputProps()} ref={fileInputRef} />
        
        <div className="text-center py-8">
          {mode === 'image' && <FileImage className="w-12 h-12 text-gray-300 mx-auto mb-3" />}
          {mode === 'video' && <FileVideo className="w-12 h-12 text-gray-300 mx-auto mb-3" />}
          {mode === 'multimodal' && <Upload className="w-12 h-12 text-gray-300 mx-auto mb-3" />}
          
          <h3 className="text-lg font-semibold text-gray-900">
            {mode === 'image' ? 'Image Analysis' : mode === 'video' ? 'Video Analysis' : 'Multimodal Analysis'}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {isDragActive ? 'Drop files here...' : `Drag & drop or click to upload ${mode === 'multimodal' ? 'images, videos, or audio' : mode === 'image' ? 'an image' : 'a video'}`}
          </p>
          <p className="text-xs text-gray-400 mt-2">
            Max size: {formatFileSize(MAX_FILE_SIZE)} • Allowed: {getAllowedTypes().map(t => t.split('/')[1]).join(', ')}
          </p>
        </div>
      </div>

      {files.length > 0 && (
        <div className="mt-6 space-y-3">
          <h4 className="text-sm font-medium text-gray-700">Selected Files</h4>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {files.map((file, index) => (
              <div key={index} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                {file.preview && file.type.startsWith('image/') && (
                  <img src={file.preview} alt="" className="w-12 h-12 rounded object-cover" />
                )}
                {file.preview && file.type.startsWith('video/') && (
                  <div className="w-12 h-12 rounded bg-gray-200 flex items-center justify-center">
                    <FileVideo className="w-6 h-6 text-gray-400" />
                  </div>
                )}
                {!file.preview && (
                  <div className="w-12 h-12 rounded bg-gray-200 flex items-center justify-center">
                    <FileText className="w-6 h-6 text-gray-400" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
                  <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeFile(index)}
                  aria-label="Remove file"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && <Alert variant="danger" className="mt-4">{error}</Alert>}

      {isAnalyzing && (
        <div className="mt-4">
          <Progress value={progress} showLabel color="primary" />
          <p className="text-sm text-gray-500 mt-1 text-center">Analyzing... {progress}%</p>
        </div>
      )}

      <div className="mt-6 flex justify-end">
        <Button
          onClick={handleAnalyze}
          disabled={isAnalyzing || files.length === 0}
          loading={isAnalyzing}
          size="lg"
        >
          <Loader2 className="w-4 h-4" />
          {mode === 'image' ? 'Analyze Image' : mode === 'video' ? 'Analyze Video' : 'Analyze Files'}
        </Button>
      </div>
    </Card>
  )
}