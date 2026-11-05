import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { AnalysisResultView } from './AnalysisResult'
import type { AnalysisResult } from '@/store/appStore'

afterEach(cleanup)
const base: AnalysisResult = {
  analysis_id: 'test', status: 'inconclusive', confidence: 0, results: {},
  explanations: [], processing_time_ms: 50, timestamp: '2026-10-16T00:00:00Z',
}

describe('image authenticity verdicts', () => {
  it('labels an enabled experimental verdict without calling the score proof', () => {
    render(<AnalysisResultView result={{ ...base, status: 'suspicious', confidence: .99,
      results: { ai_generated_image: { status: 'suspicious', ai_probability: .99,
        verdict_eligible: true, decision_reason: 'experimental_opt_in' } } }} />)
    expect(screen.getByText('Experimental classification')).toBeInTheDocument()
    expect(screen.getByText(/does not prove that the image or video is fake or real/)).toBeInTheDocument()
  })
  it('does not present an unsupported 83 percent activation as fake confidence', () => {
    render(<AnalysisResultView result={{ ...base, explanation_source: 'measured_findings',
      llm_summary: 'Authenticity is inconclusive; the model is unvalidated for this input.',
      results: { ai_generated_image: { status: 'inconclusive', confidence: 0,
        ai_probability: .8324, raw_model_score: .8324, verdict_eligible: false } } }} />)
    expect(screen.getByRole('heading', { name: 'Inconclusive' })).toBeInTheDocument()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    expect(screen.queryByText('AI-generation model score')).not.toBeInTheDocument()
    expect(screen.queryByText(/Raw classifier activation:/)).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'What this result means' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Experimental model diagnostics — not an authenticity verdict' }))
    expect(screen.getByText('Raw classifier activation: 83.24%.')).toBeInTheDocument()
  })
  it('shows measured findings and uncertainty for a 60 percent score', () => {
    render(<AnalysisResultView result={{ ...base, results: {
      ai_generated_image: { status: 'inconclusive', ai_probability: .6 },
    }, evidence_report: {
      findings: [{ check: 'Whole-image AI patterns', observation: 'AI-pattern score: 60%.',
                   meaning: 'Between 30% and 70%; the system abstains.' }],
      limitations: ['No reliable region localization.'], score_note: 'Scores are not proof.',
    } }} />)
    expect(screen.getByRole('heading', { name: 'Inconclusive' })).toBeInTheDocument()
    expect(screen.getByText('AI-pattern score: 60%.')).toBeInTheDocument()
    expect(screen.getByText('Between 30% and 70%; the system abstains.')).toBeInTheDocument()
    expect(screen.getByText('What remains uncertain')).toBeInTheDocument()
  })
  it('does not render inconclusive as clean or real', () => {
    render(<AnalysisResultView result={{ ...base, results: {
      ai_generated_image: { status: 'unavailable', ai_probability: null, confidence: 0 },
      image_deepfake: { status: 'not_applicable', confidence: 0, is_deepfake: null },
    } }} />)
    expect(screen.getByRole('heading', { name: 'Inconclusive' })).toBeInTheDocument()
    expect(screen.getByText('Not applicable')).toBeInTheDocument()
    expect(screen.queryByText('Raw Analysis Data')).not.toBeInTheDocument()
    expect(screen.queryByText('Clean')).not.toBeInTheDocument()
    expect(screen.queryByText('No Threat Detected')).not.toBeInTheDocument()
  })

  it('shows the whole-image score without requiring a face', () => {
    render(<AnalysisResultView result={{ ...base, status: 'suspicious', confidence: .9907, results: {
      ai_generated_image: { status: 'suspicious', ai_probability: .9907, confidence: .9907 },
      image_deepfake: { status: 'not_applicable', confidence: 0, is_deepfake: null },
    } }} />)
    expect(screen.getByRole('heading', { name: 'AI-generated or edited indicators' })).toBeInTheDocument()
    expect(screen.getAllByText('99.1%').length).toBeGreaterThan(0)
    expect(screen.getByText('Not applicable')).toBeInTheDocument()
  })
})
