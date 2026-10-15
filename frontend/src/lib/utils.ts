export const cn = (...classes: (string | undefined | null | false)[]): string => {
  return classes.filter(Boolean).join(' ')
}

export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms.toFixed(0)}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}

export const formatConfidence = (confidence: number): string => {
  return `${(confidence * 100).toFixed(1)}%`
}

export const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 0.8) return 'text-danger-600'
  if (confidence >= 0.6) return 'text-warning-600'
  if (confidence >= 0.4) return 'text-primary-600'
  return 'text-success-600'
}

export const getConfidenceBg = (confidence: number): string => {
  if (confidence >= 0.8) return 'bg-danger-100'
  if (confidence >= 0.6) return 'bg-warning-100'
  if (confidence >= 0.4) return 'bg-primary-100'
  return 'bg-success-100'
}

export const getSeverityColor = (severity: string): string => {
  switch (severity) {
    case 'error': return 'text-danger-600 bg-danger-50 border-danger-200'
    case 'warning': return 'text-warning-600 bg-warning-50 border-warning-200'
    case 'success': return 'text-success-600 bg-success-50 border-success-200'
    default: return 'text-primary-600 bg-primary-50 border-primary-200'
  }
}

export const getSeverityIcon = (severity: string) => {
  switch (severity) {
    case 'error': return 'AlertCircle'
    case 'warning': return 'AlertTriangle'
    case 'success': return 'CheckCircle'
    default: return 'Info'
  }
}

export const truncate = (str: string, length: number): string => {
  if (str.length <= length) return str
  return str.slice(0, length) + '...'
}

export const debounce = <T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): ((...args: Parameters<T>) => void) => {
  let timeoutId: ReturnType<typeof setTimeout>
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}

export const readFileAsBase64 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export const readFileAsText = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsText(file)
  })
}

export const validateFile = (file: File, allowedTypes: string[], maxSize: number): string | null => {
  if (!allowedTypes.includes(file.type)) {
    return `File type ${file.type} is not allowed. Allowed types: ${allowedTypes.join(', ')}`
  }
  if (file.size > maxSize) {
    return `File size ${formatFileSize(file.size)} exceeds maximum allowed size of ${formatFileSize(maxSize)}`
  }
  return null
}