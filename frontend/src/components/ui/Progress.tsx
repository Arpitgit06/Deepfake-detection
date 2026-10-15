import { cn } from '@/lib/utils'

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number
  max?: number
  showLabel?: boolean
  size?: 'sm' | 'md' | 'lg'
  color?: 'primary' | 'success' | 'warning' | 'danger'
}

export const Progress = ({
  className,
  value,
  max = 100,
  showLabel = false,
  size = 'md',
  color = 'primary',
  ...props
}: ProgressProps) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)

  const colors = {
    primary: 'bg-primary-600',
    success: 'bg-success-600',
    warning: 'bg-warning-600',
    danger: 'bg-danger-600',
  }

  const sizes = {
    sm: 'h-1.5',
    md: 'h-2.5',
    lg: 'h-4',
  }

  return (
    <div className={cn('w-full', className)} {...props}>
      <div className={cn('relative overflow-hidden rounded-full bg-gray-200', sizes[size])}>
        <div
          className={cn(
            'h-full rounded-full transition-all duration-300 ease-out',
            colors[color]
          )}
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
        />
      </div>
      {showLabel && (
        <div className="mt-1 flex justify-between text-xs text-gray-500">
          <span>{value}</span>
          <span>{max}</span>
        </div>
      )}
    </div>
  )
}