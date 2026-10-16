import { cn } from '@/lib/utils'
import { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { 
  Shield, Brain, Mic, Search, Menu, Sun, Moon
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useAppStore } from '@/store/appStore'

interface LayoutProps {
  children: ReactNode
}

export const Layout = ({ children }: LayoutProps) => {
  const { theme, setTheme, toggleSidebar } = useAppStore()

  return (
    <div className={cn('min-h-screen bg-gray-50', theme === 'dark' && 'dark')}>
      {/* Header */}
      <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-sm border-b border-gray-200">
        <div className="max-w-full mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            {/* Logo & Title */}
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900">TruthLens AI</h1>
                <p className="text-xs text-gray-500">Deepfake & Scam Detection</p>
              </div>
            </div>

            {/* Feature Badges */}
            <div className="hidden md:flex items-center gap-2">
              <span className="px-2 py-1 bg-primary-100 text-primary-700 rounded-full text-xs font-medium flex items-center gap-1">
                <Brain className="w-3 h-3" /> PPG Liveness
              </span>
              <span className="px-2 py-1 bg-success-100 text-success-700 rounded-full text-xs font-medium flex items-center gap-1">
                <Mic className="w-3 h-3" /> Phoneme-Viseme
              </span>
              <span className="px-2 py-1 bg-warning-100 text-warning-700 rounded-full text-xs font-medium flex items-center gap-1">
                <Search className="w-3 h-3" /> Financial Threats
              </span>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
                {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              </Button>
              <Link to="/about" className="px-3 py-1.5 text-sm text-gray-600 rounded-lg hover:bg-gray-100">About</Link>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile menu button */}
      <button
        className="lg:hidden fixed bottom-4 right-4 z-50 p-3 bg-primary-600 text-white rounded-full shadow-lg"
        onClick={toggleSidebar}
        aria-label="Toggle sidebar"
      >
        <Menu className="w-6 h-6" />
      </button>

      {children}
    </div>
  )
}
