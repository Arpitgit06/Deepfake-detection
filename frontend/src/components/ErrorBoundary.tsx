import { Component, ErrorInfo, ReactNode } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

/**
 * Catches render errors anywhere in the tree and shows a readable error
 * card instead of an unrecoverable white screen.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error('TruthLens UI crashed:', error, info.componentStack)
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 p-6">
          <div className="max-w-lg w-full bg-white rounded-xl shadow-lg border border-gray-200 p-8 text-center">
            <div className="w-14 h-14 mx-auto mb-4 bg-danger-100 rounded-full flex items-center justify-center">
              <AlertCircle className="w-7 h-7 text-danger-600" />
            </div>
            <h1 className="text-xl font-bold text-gray-900">Something went wrong</h1>
            <p className="text-sm text-gray-500 mt-2">
              The TruthLens interface hit an unexpected error. Your analyses are safe -
              reloading the page usually fixes it.
            </p>
            <pre className="mt-4 text-left text-xs bg-gray-50 border border-gray-200 rounded-lg p-3 overflow-auto max-h-40 text-gray-600">
              {this.state.error?.message || 'Unknown error'}
            </pre>
            <button
              onClick={this.handleReload}
              className="mt-5 inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Reload page
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
