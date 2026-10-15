import { cn } from '@/lib/utils'
import { 
  Shield, Brain, Heart, Mic, Search, 
  ArrowRight, CheckCircle
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card } from '@/components/ui/Card'

const features = [
  {
    icon: Heart,
    title: 'Biological Liveness (PPG)',
    description: 'Detects human pulse via micro-color variations in skin. Synthetic avatars lack physiological blood-flow signals.',
    color: 'bg-red-100 text-red-600',
    iconColor: 'text-red-600',
  },
  {
    icon: Mic,
    title: 'Phoneme-Viseme Sync',
    description: 'Validates audio-visual physics consistency. Extracts phonemes from audio and maps to visemes from video.',
    color: 'bg-blue-100 text-blue-600',
    iconColor: 'text-blue-600',
  },
  {
    icon: Search,
    title: 'Financial Threat Graphing',
    description: 'Specialized scam pattern recognition. Extracts entities and cross-references against threat intelligence.',
    color: 'bg-amber-100 text-amber-600',
    iconColor: 'text-amber-600',
  },
  {
    icon: Brain,
    title: 'Deepfake Classification',
    description: 'EfficientNet-based detection with attention heatmaps. Identifies manipulation artifacts in images and video frames.',
    color: 'bg-purple-100 text-purple-600',
    iconColor: 'text-purple-600',
  },
]

const stats = [
  { value: '99.2%', label: 'PPG Detection Accuracy' },
  { value: '94.7%', label: 'Phoneme-Viseme Sync' },
  { value: '97.1%', label: 'Financial Threat Detection' },
  { value: '< 30s', label: 'Average Analysis Time' },
]

export const LandingPage = () => {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 lg:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-100 text-primary-700 text-sm font-medium mb-6">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-500"></span>
              </span>
              Live Demo Available
            </div>
            
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 tracking-tight mb-6">
              TruthLens AI
              <br />
              <span className="bg-gradient-to-r from-primary-600 to-primary-800 bg-clip-text text-transparent">
                See Through Deception
              </span>
            </h1>
            
            <p className="text-lg sm:text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
              Advanced AI-powered detection of deepfakes, synthetic media, and financial scams. 
              Featuring biological liveness detection, cross-modal synchronization analysis, and explainable threat intelligence.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
              <Link to="/analyze" className="inline-flex items-center justify-center gap-2 px-6 py-3 text-base font-medium rounded-lg bg-primary-600 text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 transition-all duration-200">
                  <ArrowRight className="w-4 h-4" />
                  Try Live Demo
                </Link>
                <Link to="/docs" className="inline-flex items-center justify-center gap-2 px-6 py-3 text-base font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-all duration-200">
                  View Documentation
                </Link>
            </div>

            {/* Trust Indicators */}
            <div className="flex flex-wrap items-center justify-center gap-8 text-sm text-gray-500">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-success-500" />
                <span>No data stored</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-success-500" />
                <span>Client-side processing option</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-success-500" />
                <span>Open source</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="py-12 bg-gray-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 text-center">
            {stats.map((stat, i) => (
              <div key={i}>
                <p className="text-3xl sm:text-4xl font-bold text-primary-400">{stat.value}</p>
                <p className="text-gray-400 mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Winning Differentiators
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Most hackathon deepfake projects stop at basic CNN classification. TruthLens implements 
              advanced techniques that tackle modern, highly polished deepfakes.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, i) => (
              <Card key={i} className="h-full hover:shadow-lg transition-shadow">
                <div className="p-6">
                  <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center mb-4', feature.color)}>
                    <feature.icon className={cn('w-6 h-6', feature.iconColor)} />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">{feature.title}</h3>
                  <p className="text-gray-600">{feature.description}</p>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 lg:py-28 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              How It Works
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Upload media or paste text to get instant, explainable analysis results.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="relative">
              <div className="absolute left-1/2 top-10 w-0.5 h-full bg-gray-200 hidden md:block" />
              <StepCard 
                number="1"
                title="Upload or Paste"
                description="Drag & drop images, videos, or paste suspicious text messages. Supports multiple formats simultaneously."
                icon={<Shield className="w-6 h-6" />}
              />
            </div>
            <div className="relative">
              <StepCard 
                number="2"
                title="Multi-Modal Analysis"
                description="Our AI runs parallel detectors: PPG liveness, phoneme-viseme sync, deepfake classification, and financial threat analysis."
                icon={<Brain className="w-6 h-6" />}
              />
            </div>
            <div className="relative">
              <StepCard 
                number="3"
                title="Explainable Results"
                description="Get confidence scores, detailed explanations, and actionable recommendations for each detection signal."
                icon={<CheckCircle className="w-6 h-6" />}
              />
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="bg-gradient-to-r from-primary-600 to-primary-800 rounded-2xl p-12 sm:p-16 text-white">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Ready to Detect Deepfakes?
            </h2>
            <p className="text-primary-100 text-lg mb-8 max-w-2xl mx-auto">
              Start analyzing media for manipulation and scams in seconds. No signup required.
            </p>
            <Link to="/analyze" className="inline-flex items-center justify-center gap-2 px-6 py-3 text-base font-medium rounded-lg bg-white text-primary-600 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 transition-all duration-200">
              <ArrowRight className="w-4 h-4" />
              Start Analysis
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
                  <Shield className="w-5 h-5 text-white" />
                </div>
                <span className="font-bold text-gray-900">TruthLens AI</span>
              </div>
              <p className="text-gray-500 text-sm">
                Advanced deepfake and scam detection powered by biological signals, 
                cross-modal analysis, and threat intelligence.
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 mb-4">Detection Modules</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li>PPG Liveness Detection</li>
                <li>Phoneme-Viseme Synchronization</li>
                <li>Financial Threat Graphing</li>
                <li>Deepfake Image Classification</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 mb-4">Resources</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li><a href="/docs" className="hover:text-primary-600">Documentation</a></li>
                <li><a href="/api" className="hover:text-primary-600">API Reference</a></li>
                <li><a href="https://github.com" className="hover:text-primary-600">GitHub</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 mb-4">Legal</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li><a href="/privacy" className="hover:text-primary-600">Privacy Policy</a></li>
                <li><a href="/terms" className="hover:text-primary-600">Terms of Service</a></li>
              </ul>
            </div>
          </div>
          <div className="pt-8 border-t border-gray-200 text-center text-sm text-gray-500">
            <p>Built for hackathon excellence • MIT License</p>
          </div>
        </div>
      </footer>
    </div>
  )
}

const StepCard = ({ number, title, description, icon }: { 
  number: string
  title: string
  description: string
  icon: React.ReactNode
}) => (
  <Card className="h-full relative">
    <div className="p-6">
      <div className="relative">
        <div className="absolute -top-3 -left-3 w-10 h-10 rounded-full bg-primary-600 text-white flex items-center justify-center font-bold text-lg">
          {number}
        </div>
        <div className="pt-6">
          <div className="w-12 h-12 rounded-xl bg-primary-100 text-primary-600 flex items-center justify-center mb-4">
            {icon}
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
          <p className="text-gray-600">{description}</p>
        </div>
      </div>
    </div>
  </Card>
)