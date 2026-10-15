import { cn } from '@/lib/utils'
import { Layout } from '@/components/layout/Layout'
import { Shield, Brain, Heart, Mic, Search, FileCode, BookOpen, Terminal } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Tabs, TabPanel } from '@/components/ui/Tabs'
import { Link } from 'react-router-dom'
import { useState } from 'react'

const apiEndpoints = [
  {
    method: 'POST',
    path: '/api/v1/analyze/image',
    description: 'Analyze an image for deepfake/manipulation indicators',
    params: ['file (image)', 'return_heatmap (boolean)', 'sensitivity (0-1)'],
  },
  {
    method: 'POST',
    path: '/api/v1/analyze/video',
    description: 'Analyze a video with PPG liveness and phoneme-viseme synchronization',
    params: ['file (video)', 'enable_ppg (boolean)', 'enable_phoneme_viseme (boolean)', 'sample_rate (1-30)'],
  },
  {
    method: 'POST',
    path: '/api/v1/analyze/text',
    description: 'Analyze text for financial scam indicators and social engineering tactics',
    params: ['text (string)', 'language (optional)', 'extract_entities (boolean)', 'check_threat_intel (boolean)'],
  },
  {
    method: 'POST',
    path: '/api/v1/analyze/multimodal',
    description: 'Combined multimodal analysis of image, video, audio, and text',
    params: ['image (optional)', 'video (optional)', 'audio (optional)', 'text_content (optional)'],
  },
]

const detectorDocs = [
  {
    id: 'ppg',
    label: 'PPG Liveness',
    icon: Heart,
    color: 'text-red-600 bg-red-100',
    content: (
      <div className="space-y-4">
        <h4 className="font-semibold text-gray-900">Photoplethysmography (PPG) Liveness Detection</h4>
        <p className="text-gray-600">
          Detects human pulse via subtle color changes in facial skin caused by blood volume pulse.
          Uses CHROM (Chrominance) and POS (Plane-Orthogonal-to-Skin) methods.
        </p>
        <div className="bg-gray-50 rounded-lg p-4">
          <h5 className="font-medium mb-2">How it works:</h5>
          <ol className="list-decimal list-inside space-y-1 text-sm text-gray-600">
            <li>Extract frames from video at specified sample rate</li>
            <li>Detect face and extract ROIs (forehead, cheeks) using MediaPipe FaceMesh</li>
            <li>Compute mean RGB values per frame per ROI</li>
            <li>Apply CHROM/POS method to extract pulse signal</li>
            <li>Bandpass filter (0.7-4 Hz) for heart rate range</li>
            <li>Estimate heart rate via FFT peak detection</li>
            <li>Compute signal quality, SNR, and periodicity metrics</li>
          </ol>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <h5 className="font-medium mb-2">Response Fields:</h5>
          <pre className="text-xs overflow-x-auto">{`{
  "detector": "ppg_liveness",
  "has_pulse": true,
  "confidence": 0.92,
  "heart_rate_bpm": 72.5,
  "signal_quality": 0.85,
  "snr_db": 12.3,
  "explanations": [...],
  "raw_signal": [...],
  "timestamps": [...]
}`}</pre>
        </div>
      </div>
    ),
  },
  {
    id: 'phoneme',
    label: 'Phoneme-Viseme',
    icon: Mic,
    color: 'text-blue-600 bg-blue-100',
    content: (
      <div className="space-y-4">
        <h4 className="font-semibold text-gray-900">Cross-Modal Phoneme-Viseme Synchronization</h4>
        <p className="text-gray-600">
          Validates audio-visual consistency by extracting phonemes from audio and visemes (mouth shapes) from video,
          then aligning them using Dynamic Time Warping (DTW).
        </p>
        <div className="bg-gray-50 rounded-lg p-4">
          <h5 className="font-medium mb-2">Process:</h5>
          <ol className="list-decimal list-inside space-y-1 text-sm text-gray-600">
            <li>Extract audio track from video (ffmpeg → 16kHz mono WAV)</li>
            <li>Run ASR (Wav2Vec2) to get phoneme sequence with timestamps</li>
            <li>Extract video frames and detect mouth landmarks (MediaPipe FaceMesh)</li>
            <li>Classify mouth geometry into 16 viseme categories</li>
            <li>Map phonemes to expected visemes using linguistic rules</li>
            <li>Align sequences with DTW and compute sync score</li>
          </ol>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <h5 className="font-medium mb-2">Viseme Categories (16):</h5>
          <div className="grid grid-cols-2 gap-1 text-sm">
            {['silence', 'aa/ao', 'ae/ah', 'ey/ay/oy', 'iy/ih', 'uw/uh', 'ow/aw', 'w/r',
              'l', 'th/dh', 'f/v', 's/z/sh', 'm/n/ng', 'p/b', 't/d/k/g', 'ch/jh'].map((v, i) => (
              <span key={i} className="px-2 py-1 bg-white rounded text-gray-700">{i}: {v}</span>
            ))}
          </div>
        </div>
      </div>
    ),
  },
  {
    id: 'financial',
    label: 'Financial Threat',
    icon: Search,
    color: 'text-amber-600 bg-amber-100',
    content: (
      <div className="space-y-4">
        <h4 className="font-semibold text-gray-900">Financial Threat Graphing</h4>
        <p className="text-gray-600">
          Specialized detection for financial communications. Extracts entities (phones, crypto addresses, URLs, IBANs),
          cross-references against threat intelligence, and classifies psychological manipulation tactics.
        </p>
        <div className="bg-gray-50 rounded-lg p-4">
          <h5 className="font-medium mb-2">Supported Entity Types:</h5>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {['Phone Numbers', 'Email Addresses', 'URLs', 'Bitcoin Addresses', 'Ethereum Addresses', 
              'IBANs', 'SWIFT/BIC', 'Credit Cards', 'Currency Amounts', 'Account Numbers'].map((e, i) => (
              <span key={i} className="px-2 py-1 bg-white rounded text-gray-700">{e}</span>
            ))}
          </div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <h5 className="font-medium mb-2">Psychological Tactics Detected:</h5>
          <ul className="space-y-1 text-sm text-gray-600">
            {['Urgency', 'Authority Impersonation', 'Fear/Intimidation', 'Greed/Reward', 'Scarcity',
              'Social Proof', 'Reciprocity', 'Credential Harvesting', 'Remote Access', 'Payment Demand'].map((t, i) => (
              <li key={i} className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                {t}
              </li>
            ))}
          </ul>
        </div>
      </div>
    ),
  },
  {
    id: 'deepfake',
    label: 'Deepfake Detection',
    icon: Brain,
    color: 'text-purple-600 bg-purple-100',
    content: (
      <div className="space-y-4">
        <h4 className="font-semibold text-gray-900">Deepfake Image & Video Detection</h4>
        <p className="text-gray-600">
          EfficientNet-B0 based classifier with attention heatmap generation. Analyzes single images or 
          video frames for manipulation artifacts, blending boundaries, and frequency domain anomalies.
        </p>
        <div className="bg-gray-50 rounded-lg p-4">
          <h5 className="font-medium mb-2">Detection Pipeline:</h5>
          <ol className="list-decimal list-inside space-y-1 text-sm text-gray-600">
            <li>Detect faces using MediaPipe Face Detection</li>
            <li>Crop and align largest face (with 20% padding)</li>
            <li>Preprocess: resize 224×224, ImageNet normalization</li>
            <li>Inference with EfficientNet-B0 (binary: real vs fake)</li>
            <li>Generate attention heatmap via gradient-weighted class activation</li>
            <li>For video: sample frames, aggregate scores with temporal consistency</li>
          </ol>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <h5 className="font-medium mb-2">Heuristic Fallback (when model unavailable):</h5>
          <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
            <li>FFT frequency analysis for grid artifacts</li>
            <li>Laplacian variance for edge consistency</li>
            <li>Gradient analysis for blending artifacts</li>
            <li>Eye region symmetry analysis</li>
          </ul>
        </div>
      </div>
    ),
  },
]

export const DocsPage = () => {
  const [activeTab, setActiveTab] = useState('overview')

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Documentation</h1>
          <p className="text-gray-600 text-lg">API reference and detector documentation</p>
        </div>

        <Tabs
          tabs={[
            { id: 'overview', label: 'Overview', icon: <BookOpen className="w-4 h-4" /> },
            { id: 'api', label: 'API Reference', icon: <Terminal className="w-4 h-4" /> },
            ...detectorDocs.map(d => ({ id: d.id, label: d.label, icon: <d.icon className="w-4 h-4" /> })),
          ]}
          activeTab={activeTab}
          onChange={setActiveTab}
        />

        <TabPanel id="overview" activeTab={activeTab}>
          <div className="space-y-8 mt-8">
            <Card>
              <div className="p-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-4">TruthLens AI API</h2>
                <p className="text-gray-600 mb-6">
                  RESTful API for deepfake and scam detection. All endpoints accept multipart/form-data 
                  for file uploads and return JSON responses with analysis results, confidence scores, 
                  and human-readable explanations.
                </p>
                
                <div className="grid md:grid-cols-3 gap-4">
                  <Card className="p-4 bg-primary-50 border-primary-200">
                    <div className="flex items-center gap-3 mb-2">
                      <Shield className="w-6 h-6 text-primary-600" />
                      <h3 className="font-semibold">Base URL</h3>
                    </div>
                    <code className="text-sm bg-white px-3 py-1 rounded">http://localhost:8000/api/v1</code>
                  </Card>
                  <Card className="p-4 bg-success-50 border-success-200">
                    <div className="flex items-center gap-3 mb-2">
                      <Heart className="w-6 h-6 text-success-600" />
                      <h3 className="font-semibold">Health Check</h3>
                    </div>
                    <code className="text-sm bg-white px-3 py-1 rounded">GET /api/v1/health</code>
                  </Card>
                  <Card className="p-4 bg-warning-50 border-warning-200">
                    <div className="flex items-center gap-3 mb-2">
                      <Brain className="w-6 h-6 text-warning-600" />
                      <h3 className="font-semibold">Interactive Docs</h3>
                    </div>
                    <code className="text-sm bg-white px-3 py-1 rounded">GET /docs (Swagger UI)</code>
                  </Card>
                </div>
              </div>
            </Card>

            <Card>
              <div className="p-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-4">Quick Start</h2>
                
                <div className="space-y-6">
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-2">Analyze an Image</h3>
                    <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm"><code>{`curl -X POST http://localhost:8000/api/v1/analyze/image \\
  -F "file=@suspicious_image.jpg" \\
  -F "return_heatmap=true" \\
  -F "sensitivity=0.7"`}</code></pre>
                  </div>
                  
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-2">Analyze a Video</h3>
                    <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm"><code>{`curl -X POST http://localhost:8000/api/v1/analyze/video \\
  -F "file=@suspicious_video.mp4" \\
  -F "enable_ppg=true" \\
  -F "enable_phoneme_viseme=true" \\
  -F "sample_rate=5"`}</code></pre>
                  </div>
                  
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-2">Analyze Text for Scams</h3>
                    <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm"><code>{`curl -X POST http://localhost:8000/api/v1/analyze/text \\
  -H "Content-Type: application/json" \\
  -d '{
    "text": "Urgent: Your bank account is compromised. Click here to verify.",
    "extract_entities": true,
    "check_threat_intel": true
  }'`}</code></pre>
                  </div>
                </div>
              </div>
            </Card>

            <Card>
              <div className="p-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-4">Response Format</h2>
                <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm"><code>{`{
  "analysis_id": "uuid",
  "status": "suspicious" | "clean",
  "confidence": 0.87,
  "results": {
    "ppg_liveness": { ... },
    "phoneme_viseme": { ... },
    "deepfake_image": { ... },
    "financial_threat": { ... }
  },
  "explanations": [
    {
      "type": "pulse_detected",
      "message": "Physiological pulse detected at 72.5 BPM",
      "severity": "success",
      "details": { ... }
    }
  ],
  "processing_time_ms": 2341.5,
  "timestamp": "2024-01-15T10:30:00Z"
}`}</code></pre>
              </div>
            </Card>
          </div>
        </TabPanel>

        <TabPanel id="api" activeTab={activeTab}>
          <div className="mt-8 space-y-6">
            {apiEndpoints.map((endpoint, i) => (
              <Card key={i} className="overflow-hidden">
                <div className="p-4 bg-gray-50 border-b border-gray-200 flex items-center gap-4 flex-wrap">
                  <span className={cn(
                    'px-3 py-1 rounded-full text-xs font-mono font-bold',
                    endpoint.method === 'POST' && 'bg-blue-100 text-blue-700',
                    endpoint.method === 'GET' && 'bg-green-100 text-green-700'
                  )}>
                    {endpoint.method}
                  </span>
                  <code className="text-base font-mono text-gray-900 flex-1 min-w-[200px]">{endpoint.path}</code>
                </div>
                <div className="p-6">
                  <p className="text-gray-600 mb-4">{endpoint.description}</p>
                  <h4 className="font-medium text-gray-900 mb-2">Parameters:</h4>
                  <ul className="space-y-1">
                    {endpoint.params.map((param, j) => (
                      <li key={j} className="flex items-center gap-2 text-sm">
                        <code className="bg-gray-100 px-2 py-0.5 rounded text-gray-700">{param}</code>
                      </li>
                    ))}
                  </ul>
                </div>
              </Card>
            ))}
          </div>
        </TabPanel>

        {detectorDocs.map((detector) => (
          <TabPanel key={detector.id} id={detector.id} activeTab={activeTab}>
            <div className="mt-8">
              <Card>
                <div className="p-6">
                  {detector.content}
                </div>
              </Card>
            </div>
          </TabPanel>
        ))}
      </div>
    </Layout>
  )
}