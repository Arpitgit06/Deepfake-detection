import { Routes, Route, Navigate } from 'react-router-dom'
import { LandingPage } from '@/pages/LandingPage'
import { AnalysisPage } from '@/pages/AnalysisPage'
import { DocsPage } from '@/pages/DocsPage'
import { AboutPage } from '@/pages/AboutPage'

export const App = () => {
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