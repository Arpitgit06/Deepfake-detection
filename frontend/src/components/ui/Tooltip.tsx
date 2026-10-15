import React, { useState, useRef } from 'react'
import { cn } from '@/lib/utils'

interface TooltipProps {
  content: React.ReactNode
  children: React.ReactElement
  position?: 'top' | 'bottom' | 'left' | 'right'
  delay?: number
}

export const Tooltip = ({ content, children, position = 'top', delay = 200 }: TooltipProps) => {
  const [isVisible, setIsVisible] = useState(false)
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>()

  const show = () => {
    timeoutRef.current = setTimeout(() => setIsVisible(true), delay)
  }

  const hide = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    setIsVisible(false)
  }

  const positions = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  }

  const arrows = {
    top: 'border-t-gray-900',
    bottom: 'border-b-gray-900',
    left: 'border-l-gray-900',
    right: 'border-r-gray-900',
  }

  return (
    <div className="relative inline-block" onMouseEnter={show} onMouseLeave={hide} onFocus={show} onBlur={hide}>
      {React.cloneElement(children, {
        'aria-describedby': isVisible ? 'tooltip' : undefined,
      })}
      {isVisible && (
        <div
          id="tooltip"
          role="tooltip"
          className={cn(
            'absolute z-50 px-3 py-2 text-xs font-medium text-white bg-gray-900 rounded-lg shadow-lg whitespace-nowrap animate-fade-in',
            positions[position]
          )}
        >
          {content}
          <div className={cn('absolute w-0 h-0 border-4 border-transparent', arrows[position])} />
        </div>
      )}
    </div>
  )
}