import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'
import { App } from './App'

const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  )
}

describe('App', () => {
  it('renders without crashing', () => {
    renderWithRouter(<App />)
    // App should render routes, but we're testing the component mounts
    expect(screen.getAllByText(/TruthLens AI/i)[0]).toBeInTheDocument()
  })
})