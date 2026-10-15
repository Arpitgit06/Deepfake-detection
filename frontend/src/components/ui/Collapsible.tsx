import { useState } from 'react'
import { cn } from '@/lib/utils'
import { ChevronDown, ChevronUp } from 'lucide-react'

interface CollapsibleProps {
  title: string
  children: React.ReactNode
  defaultOpen?: boolean
  className?: string
  icon?: React.ReactNode
}

export const Collapsible = ({ title, children, defaultOpen = false, className, icon }: CollapsibleProps) => {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className={cn('border border-gray-200 rounded-xl overflow-hidden', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-3">
          {icon}
          <h3 className="font-medium text-gray-900">{title}</h3>
        </div>
        <div className="flex items-center gap-2 text-gray-500">
          {isOpen ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </div>
      </button>
      <div
        className={cn('overflow-hidden transition-all duration-200', isOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0')}
      >
        <div className="p-4 border-t border-gray-200 bg-white animate-fade-in">
          {children}
        </div>
      </div>
    </div>
  )
}