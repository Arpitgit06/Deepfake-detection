import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-react'

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'circular' | 'rectangular'
  width?: string | number
  height?: string | number
}

export const Skeleton = ({
  className,
  variant = 'text',
  width,
  height,
  ...props
}: SkeletonProps) => {
  const variants = {
    text: 'h-4 rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-lg',
  }

  return (
    <div
      className={cn(
        'animate-pulse bg-gray-200',
        variants[variant],
        className
      )}
      style={{ width, height }}
      {...props}
    />
  )
}

export const SkeletonText = ({ lines = 3, className }: { lines?: number; className?: string }) => (
  <div className={cn('space-y-3', className)}>
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton key={i} variant="text" width={i === lines - 1 ? '60%' : '100%'}/>
    ))}
  </div>
)

export const SkeletonCard = ({ className }: { className?: string }) => (
  <div className={cn('p-6 space-y-4 border border-gray-200 rounded-xl bg-white', className)}>
    <div className="flex items-center gap-4">
      <Skeleton variant="circular" width={48} height={48} />
      <div className="flex-1 space-y-2">
        <Skeleton variant="text" width="40%" />
        <Skeleton variant="text" width="60%" />
      </div>
    </div>
    <Skeleton variant="rectangular" height={120} />
    <div className="flex gap-2">
      <Skeleton variant="text" width="80px" />
      <Skeleton variant="text" width="80px" />
    </div>
  </div>
)

export const LoadingSpinner = ({ size = 'md', className }: { size?: 'sm' | 'md' | 'lg'; className?: string }) => {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  }

  return (
    <div className={cn('flex items-center justify-center', className)}>
      <Loader2 className={cn(sizes[size], 'text-primary-600 animate-spin')} />
    </div>
  )
}

export const LoadingOverlay = ({ message = 'Processing...' }: { message?: string }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/80 backdrop-blur-sm">
    <div className="text-center space-y-4">
      <LoadingSpinner size="lg" />
      <p className="text-gray-600">{message}</p>
    </div>
  </div>
)