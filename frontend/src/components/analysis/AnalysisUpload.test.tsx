import { fireEvent, render, screen, waitFor, cleanup } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { AnalysisUpload } from './AnalysisUpload'
import { AnalysisPage } from '@/pages/AnalysisPage'
import { api } from '@/services/api'
import { useAppStore } from '@/store/appStore'

beforeEach(() => {
  useAppStore.setState({ jobs: [], currentJobId: null, sidebarOpen: false, theme: 'light' })
  URL.createObjectURL = vi.fn(() => 'blob:test')
  URL.revokeObjectURL = vi.fn()
})
afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('analysis interaction regressions', () => {
  it('opens the native picker when the upload area is clicked', () => {
    render(<AnalysisUpload mode="image" onAnalyze={vi.fn()} />)
    const input = screen.getByLabelText('Choose files') as HTMLInputElement
    const click = vi.spyOn(input, 'click')
    fireEvent.click(screen.getByText('Image Analysis'))
    expect(click).toHaveBeenCalledOnce()
  })

  it('submits actual File bytes in FormData and permits another analysis', async () => {
    const post = vi.spyOn(api, 'post').mockResolvedValue({ data: {
      analysis_id: 'sample', status: 'clean', confidence: 0.1, results: {},
      explanations: [], processing_time_ms: 20, timestamp: new Date().toISOString(),
    } })
    render(<MemoryRouter><AnalysisPage /></MemoryRouter>)
    const file = new File(['image-content'], 'photo.png', { type: 'image/png' })
    fireEvent.change(screen.getByLabelText('Choose files'), { target: { files: [file] } })
    await screen.findByText('photo.png')
    fireEvent.click(screen.getByRole('button', { name: 'Analyze Image' }))
    await waitFor(() => expect(post).toHaveBeenCalledOnce())
    const body = post.mock.calls[0][1] as FormData
    const sent = body.get('file') as File
    expect(sent).toBeInstanceOf(File)
    expect(sent.name).toBe('photo.png')
    expect(sent.size).toBe(file.size)
    expect(sent.type).toBe('image/png')
    await screen.findByText('Ask AI about this result')
    fireEvent.click(screen.getByRole('button', { name: 'New analysis' }))
    expect(screen.getByLabelText('Choose files')).toBeInTheDocument()
  })

  it('shows rejected files instead of silently ignoring them', async () => {
    render(<AnalysisUpload mode="image" onAnalyze={vi.fn()} />)
    fireEvent.change(screen.getByLabelText('Choose files'), {
      target: { files: [new File(['bad'], 'document.txt', { type: 'text/plain' })] },
    })
    await screen.findByText(/document.txt:/)
    expect(screen.getByRole('button', { name: 'Analyze Image' })).toBeDisabled()
  })

  it('replaces single uploads and clears selections when changing modes', async () => {
    render(<MemoryRouter><AnalysisPage /></MemoryRouter>)
    const select = (name: string) => fireEvent.change(screen.getByLabelText('Choose files'), {
      target: { files: [new File(['img'], name, { type: 'image/png' })] },
    })
    select('first.png')
    await screen.findByText('first.png')
    select('second.png')
    await screen.findByText('second.png')
    expect(screen.queryByText('first.png')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'Video' }))
    expect(screen.queryByText('second.png')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Analyze Video' })).toBeDisabled()
  })

  it('updates the theme and uses the same sidebar state for both controls', () => {
    render(<MemoryRouter><AnalysisPage /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: 'Switch to dark theme' }))
    expect(useAppStore.getState().theme).toBe('dark')
    fireEvent.click(screen.getByRole('button', { name: 'Toggle sidebar' }))
    expect(screen.getByRole('button', { name: 'Collapse sidebar' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Collapse sidebar' }))
    expect(useAppStore.getState().sidebarOpen).toBe(false)
  })
})
