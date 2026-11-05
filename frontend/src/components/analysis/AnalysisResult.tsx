import { cn, getSeverityColor, formatConfidence, formatDuration, truncate, verdictLabel } from '@/lib/utils'
import { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { Collapsible } from '@/components/ui/Collapsible'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { askLLM } from '@/services/api'
import { 
  AlertCircle, CheckCircle, AlertTriangle, Info, 
  Heart, Mic, Brain, Shield, Search, Eye, 
  Loader2
} from 'lucide-react'
import { Explanation, AnalysisResult, DetectorResult } from '@/store/appStore'

const severityIcons = {
  error: AlertCircle,
  warning: AlertTriangle,
  success: CheckCircle,
  info: Info,
} as const

const getSeverityIconComponent = (severity: Explanation['severity']) => {
  // Unknown severities fall back to the info icon instead of crashing
  return (severityIcons[severity] ?? Info) as React.ComponentType<React.SVGProps<SVGSVGElement>>
}

export const ExplanationList = ({ explanations }: { explanations: Explanation[] }) => {
  if (!explanations || explanations.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Info className="w-8 h-8 mx-auto mb-2 text-gray-300" />
        <p>No explanations available</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {explanations.map((exp, index) => {
        const IconComponent = getSeverityIconComponent(exp.severity)
        return (
        <div
          key={index}
          className={cn(
            'flex gap-3 p-4 rounded-lg border',
            getSeverityColor(exp.severity)
          )}
        >
          <div className="flex-shrink-0 mt-0.5">
            <IconComponent className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium">{exp.message}</p>
            {exp.details && (
              <Collapsible title="Details" defaultOpen={false} className="mt-2">
                <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto max-h-48">
                  {JSON.stringify(exp.details, null, 2)}
                </pre>
              </Collapsible>
            )}
          </div>
        </div>
        )
      })}
    </div>
  )
}
export const ConfidenceIndicator = ({ 
  confidence, 
  label = 'Confidence', 
  showProgress = true,
  size = 'md',
  risk = false,
}: { 
  confidence: number 
  label?: string 
  showProgress?: boolean
  size?: 'sm' | 'md' | 'lg'
  risk?: boolean
}) => {
  const color = !risk ? 'primary' : confidence >= 0.7 ? 'danger' : confidence > 0.3 ? 'warning' : 'success'
  
  return (
    <div className="flex items-center gap-4">
      <div className={cn('flex-1', size === 'sm' && 'max-w-xs')}>
        <div className="flex items-center justify-between gap-3 text-sm mb-1">
          <span className="font-medium text-gray-700">{label}</span>
          <span className="font-semibold text-gray-700">
            {formatConfidence(confidence)}
          </span>
        </div>
        {showProgress && <Progress value={confidence * 100} color={color} size={size === 'sm' ? 'sm' : 'md'} />}
      </div>
    </div>
  )
}

export const DetectorResultCard = ({ 
  detectorName, 
  result, 
  explanations 
}: { 
  detectorName: string
  result: DetectorResult
  explanations: Explanation[]
}) => {
  const detectorIcons: Record<string, React.ReactNode> = {
    ppg_liveness: <Heart className="w-5 h-5" />,
    phoneme_viseme: <Mic className="w-5 h-5" />,
    deepfake_image: <Brain className="w-5 h-5" />,
    frame_deepfake: <Brain className="w-5 h-5" />,
    video_deepfake: <Brain className="w-5 h-5" />,
    video_ppg: <Heart className="w-5 h-5" />,
    video_phoneme_viseme: <Mic className="w-5 h-5" />,
    financial_threat: <Shield className="w-5 h-5" />,
    image_deepfake: <Brain className="w-5 h-5" />,
  }

  const detectorTitles: Record<string, string> = {
    ai_generated_image: 'AI Image Detection — Whole Image',
    ai_generated_video: 'AI Video Detection — Sampled Frames',
    llm_text_review: 'Qwen Contextual Text Review',
    phoneme_viseme_sync: 'Speech and Mouth Timing',
    ppg_liveness: 'PPG Liveness Detection',
    phoneme_viseme: 'Phoneme-Viseme Sync',
    deepfake_image: 'Deepfake Detection',
    frame_deepfake: 'Frame Deepfake Detection',
    video_deepfake: 'Video Deepfake Detection',
    video_ppg: 'PPG Liveness Detection',
    video_phoneme_viseme: 'Phoneme-Viseme Sync',
    financial_threat: 'Financial Threat Analysis',
    image_deepfake: 'Face Manipulation Check',
  }

  const confidence = result.confidence ?? 0
  const isThreat = result.is_deepfake ?? result.is_threat ?? (result.is_synchronized === false)
  const detectorStatus = result.status || (isThreat ? 'suspicious' : 'clean')
  const aiScore = result.verdict_eligible !== false && typeof result.ai_probability === 'number' ? result.ai_probability : null
  const noScore = ['not_applicable', 'inconclusive', 'unavailable', 'error'].includes(detectorStatus)
  
  return (
    <Card className="overflow-hidden">
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-100 rounded-lg text-primary-600">
              {detectorIcons[detectorName] || <Search className="w-5 h-5" />}
            </div>
            <div>
              <h4 className="font-semibold text-gray-900">{detectorTitles[detectorName] || detectorName}</h4>
              <p className="text-xs text-gray-500">
                {verdictLabel(detectorStatus)}
              </p>
            </div>
          </div>
          {detectorName === 'ai_generated_image' || detectorName === 'ai_generated_video' ? (
            aiScore !== null && <ConfidenceIndicator confidence={aiScore} label="AI-generation model score" size="sm" risk />
          ) : !noScore && confidence > 0 && <ConfidenceIndicator confidence={confidence} label="Confidence" size="sm" />}
        </div>
      </div>
      
      <div className="p-4">
        {result.decision_reason === 'experimental_opt_in' &&
          <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
            <p className="font-semibold">Experimental classification</p>
            <p>This result uses an uncalibrated model score. It can flag AI-generation indicators, but it does not prove that the image or video is fake or real.</p>
          </div>}
        {result.verdict_eligible === false && typeof result.raw_model_score === 'number' &&
          <Collapsible title="Experimental model diagnostics — not an authenticity verdict" defaultOpen={false}>
            <p className="text-sm text-gray-700">Raw classifier activation: {(result.raw_model_score * 100).toFixed(2)}%.</p>
            <p className="text-sm text-gray-600 mt-2">This is an uncalibrated model output, not the probability that the input is fake. It was excluded from the verdict. A high or low activation can be wrong.</p>
          </Collapsible>}
        {result.region_analysis?.preview_base64 && <div className="mb-4">
          <h4 className="font-medium text-gray-900 mb-2">Areas that influenced the model</h4>
          <img src={`data:image/jpeg;base64,${result.region_analysis.preview_base64}`} alt="Numbered regions tested for model sensitivity" className="max-h-96 max-w-full rounded-lg" />
          {!result.region_analysis.regions?.length && <p className="text-sm text-gray-600 mt-2">No tested area reduced support for the predicted class by at least one score point. This test did not identify a dominant area.</p>}
          <p className="text-sm text-gray-600 mt-2">{result.region_analysis.limitation}</p>
        </div>}
        {/* Key metrics based on detector type */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          {detectorName.includes('ppg') && result.heart_rate_bpm && (
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">Heart Rate</p>
              <p className="font-bold text-lg text-gray-900">{result.heart_rate_bpm} BPM</p>
            </div>
          )}
          {detectorName.includes('ppg') && result.snr_db !== undefined && (
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">Signal-to-Noise</p>
              <p className="font-bold text-lg text-gray-900">{result.snr_db.toFixed(1)} dB</p>
            </div>
          )}
          {detectorName.includes('ppg') && result.signal_quality !== undefined && (
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">Signal Quality</p>
              <p className="font-bold text-lg text-gray-900">{(result.signal_quality * 100).toFixed(0)}%</p>
            </div>
          )}
          {detectorName.includes('phoneme') && !noScore && result.sync_score !== undefined && (
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">Sync Score</p>
              <p className="font-bold text-lg text-gray-900">{(result.sync_score * 100).toFixed(0)}%</p>
            </div>
          )}
          {detectorName.includes('phoneme') && result.phoneme_viseme_pairs && result.phoneme_viseme_pairs.length > 0 && (
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">Pairs Analyzed</p>
              <p className="font-bold text-lg text-gray-900">{result.phoneme_viseme_pairs.length}</p>
            </div>
          )}
          {detectorName === 'financial_threat' && result.risk_score !== undefined && (
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">Risk Score</p>
              <p className="font-bold text-lg text-gray-900">{(result.risk_score * 100).toFixed(0)}%</p>
            </div>
          )}
          {detectorName === 'financial_threat' && result.threat_level && (
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">Threat Level</p>
              <Badge variant={result.threat_level === 'critical' || result.threat_level === 'high' ? 'danger' : result.threat_level === 'medium' ? 'warning' : 'success'}>
                {result.threat_level.toUpperCase()}
              </Badge>
            </div>
          )}
          {detectorName === 'financial_threat' && result.entities?.length && (
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">Entities Found</p>
              <p className="font-bold text-lg text-gray-900">{result.entities.length}</p>
            </div>
          )}
        </div>

        {/* Explanations */}
        {explanations && explanations.length > 0 && (
          <Collapsible title={`${explanations.length} Explanation(s)`} defaultOpen={true} icon={<Info className="w-4 h-4" />}>
            <ExplanationList explanations={explanations} />
          </Collapsible>
        )}

        {/* Detector-specific details */}
        {detectorName.includes('phoneme') && result.phoneme_viseme_pairs && (
          <Collapsible title="Phoneme-Viseme Pairs" defaultOpen={false} icon={<Eye className="w-4 h-4" />}>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b border-gray-200">
                    <th className="pb-2 pr-4">Phoneme</th>
                    <th className="pb-2 pr-4">Expected</th>
                    <th className="pb-2 pr-4">Observed</th>
                    <th className="pb-2 pr-4">Match</th>
                    <th className="pb-2 pr-4">Time Diff</th>
                  </tr>
                </thead>
                <tbody>
                  {result.phoneme_viseme_pairs.slice(0, 20).map((pair, i) => (
                    <tr key={i} className="border-b border-gray-100">
                      <td className="py-2 pr-4 font-mono">{pair.phoneme}</td>
                      <td className="py-2 pr-4">{pair.expected_viseme}</td>
                      <td className="py-2 pr-4">{pair.observed_viseme}</td>
                      <td className="py-2 pr-4">
                        {pair.match ? (
                          <CheckCircle className="w-4 h-4 text-success-600 mx-auto" />
                        ) : (
                          <AlertCircle className="w-4 h-4 text-danger-600 mx-auto" />
                        )}
                      </td>
                      <td className="py-2 pr-4 font-mono text-gray-500">{pair.time_diff?.toFixed(3)}s</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Collapsible>
        )}

        {detectorName === 'financial_threat' && result.entities && (
          <Collapsible title="Extracted Entities" defaultOpen={false} icon={<Search className="w-4 h-4" />}>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {result.entities.slice(0, 20).map((entity, i) => (
                <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <Badge variant="info" size="sm">{entity.type}</Badge>
                    <code className="text-sm font-mono truncate max-w-xs">{truncate(entity.value, 50)}</code>
                  </div>
                  <ConfidenceIndicator confidence={entity.confidence} label="" showProgress={false} size="sm" />
                </div>
              ))}
            </div>
          </Collapsible>
        )}

        {detectorName === 'financial_threat' && result.tactics && (
          <Collapsible title="Psychological Tactics" defaultOpen={false} icon={<Brain className="w-4 h-4" />}>
            <div className="space-y-2">
              {result.tactics.map((tactic, i) => (
                <div key={i} className="p-3 bg-gray-50 rounded-lg border-l-4 border-warning-500">
                  <div className="flex items-center justify-between">
                    <span className="font-medium capitalize">{tactic.name.replace(/_/g, ' ')}</span>
                    <Badge variant="warning" size="sm">{(tactic.confidence * 100).toFixed(0)}%</Badge>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">{tactic.description}</p>
                  {tactic.evidence?.length && (
                    <p className="text-xs text-gray-500 mt-1">
                      Evidence: {tactic.evidence.slice(0, 3).join(', ')}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </Collapsible>
        )}

        {result.raw_signal && (
          <Collapsible title="Raw PPG Signal" defaultOpen={false} icon={<Heart className="w-4 h-4" />}>
            <div className="h-48 bg-gray-50 rounded-lg p-2 relative overflow-hidden">
              <canvas 
                ref={(el) => {
                  if (el && result.raw_signal) drawSignal(el, result.raw_signal)
                }} 
                className="w-full h-full"
              />
            </div>
          </Collapsible>
        )}
      </div>
    </Card>
  )
}

// Simple signal visualization
function drawSignal(canvas: HTMLCanvasElement, signal: number[]) {
  const ctx = canvas.getContext('2d')
  if (!ctx || signal.length === 0) return
  
  const dpr = window.devicePixelRatio || 1
  const rect = canvas.getBoundingClientRect()
  canvas.width = rect.width * dpr
  canvas.height = rect.height * dpr
  ctx.scale(dpr, dpr)
  
  const width = rect.width
  const height = rect.height
  const padding = 20
  const plotWidth = width - padding * 2
  const plotHeight = height - padding * 2
  
  // Normalize signal
  const min = Math.min(...signal)
  const max = Math.max(...signal)
  const range = max - min || 1
  
  ctx.strokeStyle = '#0ea5e9'
  ctx.lineWidth = 1.5
  ctx.beginPath()
  
  signal.forEach((value, i) => {
    const x = padding + (i / (signal.length - 1)) * plotWidth
    const y = padding + plotHeight - ((value - min) / range) * plotHeight
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  })
  
  ctx.stroke()
  
  // Draw center line
  ctx.strokeStyle = '#e2e8f0'
  ctx.lineWidth = 1
  ctx.setLineDash([4, 4])
  ctx.beginPath()
  ctx.moveTo(padding, padding + plotHeight / 2)
  ctx.lineTo(width - padding, padding + plotHeight / 2)
  ctx.stroke()
  ctx.setLineDash([])
}

export const AnalysisResultView = ({ result }: { result: AnalysisResult }) => {
  // Defensive: the payload shape is not guaranteed for every job
  const resultEntries = Object.entries(result?.results ?? {})
  const detectorResults = resultEntries.filter(([_, v]) => v && typeof v === 'object' && !v.error)
  const hasErrors = resultEntries.some(([, value]) => value?.error)
  const confidence = result?.confidence ?? 0
  const unknown = !['suspicious', 'clean'].includes(result.status)
  const imageResult = result.results?.ai_generated_image ?? result.results?.ai_generated_video
  const imageScore = imageResult?.verdict_eligible !== false && typeof imageResult?.ai_probability === 'number' ? imageResult.ai_probability : null

  return (
    <div className="space-y-6">
      {/* Overall Status */}
      <Card className={cn('border-l-4', unknown ? 'border-warning-500' : result.status === 'suspicious' ? 'border-danger-500' : 'border-success-500')}>
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={cn('p-3 rounded-xl', unknown ? 'bg-warning-100' : result.status === 'suspicious' ? 'bg-danger-100' : 'bg-success-100')}>
                {unknown ? <AlertTriangle className="w-6 h-6 text-warning-600" /> : result.status === 'suspicious' ? (
                  <AlertCircle className="w-6 h-6 text-danger-600" />
                ) : (
                  <CheckCircle className="w-6 h-6 text-success-600" />
                )}
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  {result.status === 'suspicious' && imageResult ? 'AI-generated or edited indicators' : verdictLabel(result.status)}
                </h2>
                <p className="text-gray-500">Analysis ID: {truncate(result.analysis_id ?? '', 12)}</p>
              </div>
            </div>
            <div className="text-right">
              {imageScore !== null ? <ConfidenceIndicator confidence={imageScore} label="AI-generation model score" size="lg" risk />
                : !unknown && confidence > 0 ? <ConfidenceIndicator confidence={confidence} label="Verdict confidence" size="lg" />
                : <p className="text-sm text-gray-500">{imageResult?.metadata_evidence?.length ? 'Metadata evidence' : unknown ? 'Insufficient evidence for a verdict' : 'Contextual assessment; no calibrated score'}</p>}
              <p className="text-xs text-gray-500 mt-1">Processed in {formatDuration(result.processing_time_ms ?? 0)}</p>
            </div>
          </div>
        </div>
      </Card>

      {unknown && <Alert variant="warning">The available evidence is insufficient or conflicting. Review the findings below; this result does not establish that the input is real or fake.</Alert>}

      {result.llm_review && <Alert variant={result.llm_review.assessment === 'needs_review' ? 'warning' : 'info'}>
        <strong>Qwen evidence review: </strong>{result.llm_review.reason}
        <p className="text-xs mt-1">Reviews algorithm findings only; the installed Qwen model cannot view images or video. It does not change classifier scores.</p>
      </Alert>}

      {result.evidence_report && <Card>
        <div className="p-4 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900">What the checks found</h3>
          <p className="text-sm text-gray-600 mt-2">{result.evidence_report.score_note}</p>
        </div>
        <div className="p-4 space-y-4">
          {result.evidence_report.findings.filter(finding => !finding.check.startsWith('Frame at ')).map((finding, index) => <div key={index} className="rounded-lg bg-gray-50 p-3">
            <h4 className="font-medium text-gray-900">{finding.check}</h4>
            <p className="text-sm text-gray-800 mt-1">{finding.observation}</p>
            <p className="text-sm text-gray-600 mt-1">{finding.meaning}</p>
          </div>)}
          {result.evidence_report.findings.some(finding => finding.check.startsWith('Frame at ')) &&
            <Collapsible title="Frame-by-frame findings" defaultOpen={false}>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
                {result.evidence_report.findings.filter(finding => finding.check.startsWith('Frame at ')).map((finding, index) =>
                  <div key={index} className="p-3 bg-gray-50 rounded-lg text-sm">
                    <h4 className="font-medium">{finding.check}</h4><p>{finding.observation}</p>
                    <p className="text-gray-600">{finding.meaning}</p>
                  </div>)}
              </div>
            </Collapsible>}
          {result.evidence_report.limitations.length > 0 && <div>
            <h4 className="font-medium text-gray-900">What remains uncertain</h4>
            <ul className="list-disc pl-5 text-sm text-gray-600 space-y-1 mt-2">
              {result.evidence_report.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}
            </ul>
          </div>}
        </div>
      </Card>}

      {/* AI Explanation (local Qwen LLM) */}
      {result.llm_summary && (
        <Card>
          <div className="p-4 border-b border-gray-200 flex items-center gap-3">
            <div className="p-2 bg-primary-100 rounded-lg text-primary-600">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">{result.explanation_source === 'measured_findings' ? 'What this result means' : 'AI Explanation'}</h3>
              <p className="text-xs text-gray-500">{result.explanation_source === 'measured_findings' ? 'Based on measured input properties and the limits of the installed detector.' : 'Qwen reviews the measured findings and explains them in plain language.'}</p>
            </div>
          </div>
          <div className="p-4">
            <p className="text-sm text-gray-700 whitespace-pre-line">{result.llm_summary}</p>
          </div>
        </Card>
      )}

      {hasErrors && (
        <Alert variant="warning">
          Some detectors encountered errors. Results may be incomplete.
        </Alert>
      )}

      {/* Detector Results */}
      {detectorResults.some(([, detector]) => detector.model_used === 'heuristic_ensemble' && detector.status !== 'not_applicable') && (
        <Alert variant="warning">
          Trained face-manipulation weights are not installed. Facial heuristic checks are inconclusive; whole-image AI classification is reported separately.
        </Alert>
      )}
      <div className="space-y-4">
        {detectorResults.map(([detectorName, detectorResult]) => (
          <DetectorResultCard
            key={detectorName}
            detectorName={detectorName}
            result={detectorResult}
            explanations={detectorResult.explanations || []}
          />
        ))}
      </div>

      {/* All Explanations Combined */}
      {result.explanations && result.explanations.length > 0 && (
        <Card>
          <div className="p-4 border-b border-gray-200">
            <h3 className="font-semibold text-gray-900">All Explanations</h3>
          </div>
          <div className="p-4">
            <ExplanationList explanations={result.explanations} />
          </div>
        </Card>
      )}

      {/* Ask the local AI about this result */}
      <AskAIPanel analysisId={result.analysis_id} />
    </div>
  )
}

const AskAIPanel = ({ analysisId }: { analysisId: string }) => {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async () => {
    if (!question.trim()) return
    setLoading(true)
    setError(null)
    setAnswer(null)
    try {
      const response = await askLLM(analysisId, question.trim())
      setAnswer(response.answer)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The AI assistant is unavailable')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <div className="p-4 border-b border-gray-200 flex items-center gap-3">
        <div className="p-2 bg-primary-100 rounded-lg text-primary-600">
          <Brain className="w-5 h-5" />
        </div>
        <div>
          <h3 className="font-semibold text-gray-900">Ask AI about this result</h3>
          <p className="text-xs text-gray-500">Local Qwen3-4B loads into VRAM to answer, then frees it</p>
        </div>
      </div>
      <div className="p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') submit() }}
            placeholder="e.g. Why was this flagged as suspicious?"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            disabled={loading}
          />
          <Button onClick={submit} disabled={loading || !question.trim()} loading={loading}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Ask
          </Button>
        </div>

        {loading && (
          <p className="text-xs text-gray-500 mt-3">
            Loading the AI model into GPU memory... this can take a few seconds.
          </p>
        )}
        {error && <Alert variant="danger" className="mt-3">{error}</Alert>}
        {answer && (
          <div className="mt-3 p-4 bg-primary-50 border border-primary-200 rounded-lg">
            <p className="text-sm text-gray-700 whitespace-pre-line">{answer}</p>
          </div>
        )}
      </div>
    </Card>
  )
}
