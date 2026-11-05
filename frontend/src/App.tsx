import { Routes, Route, Navigate } from 'react-router-dom'
import { LandingPage } from '@/pages/LandingPage'
import { AnalysisPage } from '@/pages/AnalysisPage'
import { DocsPage } from '@/pages/DocsPage'
import { AboutPage } from '@/pages/AboutPage'
import { useLayoutEffect } from 'react'
import { useAppStore } from '@/store/appStore'

export const App = () => {
  const theme = useAppStore(state => state.theme)
  useLayoutEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/analyze" element={<AnalysisPage />} />
      <Route path="/docs" element={<DocsPage />} />
      <Route path="/about" element={<AboutPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
