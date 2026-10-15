import { Layout } from '@/components/layout/Layout'
import { Shield, Brain, Heart, Mic, Search, FileCode, Github, Twitter, Mail } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Link } from 'react-router-dom'

export const AboutPage = () => {
  const team = [
    { name: 'Arpit', role: 'ML Engineer', github: 'https://github.com' },
    { name: 'Contributors', role: 'Open Source Community', github: 'https://github.com' },
  ]

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-16">
          <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
            <Shield className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">About TruthLens AI</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            A cutting-edge platform for detecting manipulated media and fraudulent communications 
            using advanced AI techniques. Built for hackathon excellence.
          </p>
        </div>

        {/* Mission */}
        <Card className="mb-8">
          <div className="p-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-3">
              <Brain className="w-6 h-6 text-primary-600" />
              Mission
            </h2>
            <p className="text-gray-600 text-lg leading-relaxed">
              In an era where synthetic media is becoming indistinguishable from reality, 
              TruthLens AI empowers individuals and organizations to verify the authenticity 
              of digital content. We go beyond simple classification by providing 
              <strong className="text-gray-900">explainable results</strong> — showing exactly which signals 
              triggered warnings and why.
            </p>
          </div>
        </Card>

        {/* Technical Approach */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">Technical Approach</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { icon: Heart, title: 'Biological Signals', desc: 'PPG-based liveness detection via micro-color variations in skin' },
              { icon: Mic, title: 'Cross-Modal Sync', desc: 'Phoneme-viseme alignment using Dynamic Time Warping' },
              { icon: Search, title: 'Threat Intelligence', desc: 'Entity extraction + psychological tactic classification' },
              { icon: Brain, title: 'Deep Learning', desc: 'EfficientNet-B0 with attention heatmaps for manipulation detection' },
            ].map((item, i) => (
              <Card key={i} className="h-full">
                <div className="p-6">
                  <div className="w-12 h-12 rounded-xl bg-primary-100 text-primary-600 flex items-center justify-center mb-4">
                    <item.icon className="w-6 h-6" />
                  </div>
                  <h3 className="font-semibold text-gray-900 mb-2">{item.title}</h3>
                  <p className="text-gray-600">{item.desc}</p>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Tech Stack */}
        <Card className="mb-8">
          <div className="p-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-3">
              <FileCode className="w-6 h-6 text-primary-600" />
              Tech Stack
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { category: 'Backend', items: ['Python 3.10+', 'FastAPI', 'PyTorch', 'OpenCV', 'MediaPipe', 'Transformers'] },
                { category: 'Frontend', items: ['React 18', 'TypeScript', 'Vite', 'Tailwind CSS', 'Zustand', 'Recharts'] },
                { category: 'ML/AI', items: ['EfficientNet-B0', 'Wav2Vec2', 'MediaPipe FaceMesh', 'SciPy', 'fastDTW'] },
                { category: 'Infrastructure', items: ['Docker', 'Redis', 'ONNX Runtime', 'Prometheus', 'Loguru'] },
              ].map((cat, i) => (
                <div key={i}>
                  <h4 className="font-semibold text-gray-900 mb-2">{cat.category}</h4>
                  <ul className="space-y-1 text-sm text-gray-600">
                    {cat.items.map((item, j) => (
                      <li key={j} className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-primary-500" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* Team */}
        <Card className="mb-8">
          <div className="p-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Team</h2>
            <div className="grid md:grid-cols-2 gap-6">
              {team.map((member, i) => (
                <div key={i} className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
                  <div className="w-12 h-12 rounded-full bg-primary-100 flex items-center justify-center text-primary-600 font-bold text-lg">
                    {member.name.charAt(0)}
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">{member.name}</p>
                    <p className="text-sm text-gray-500">{member.role}</p>
                  </div>
                  <a href={member.github} target="_blank" rel="noopener noreferrer" className="ml-auto text-gray-400 hover:text-primary-600">
                    <Github className="w-5 h-5" />
                  </a>
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* Links */}
        <div className="text-center space-y-4">
          <p className="text-gray-600">Connect with us</p>
          <div className="flex justify-center gap-4">
            <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="p-3 bg-gray-100 rounded-lg text-gray-600 hover:bg-primary-100 hover:text-primary-600 transition-colors">
              <Github className="w-6 h-6" />
            </a>
            <a href="https://twitter.com" target="_blank" rel="noopener noreferrer" className="p-3 bg-gray-100 rounded-lg text-gray-600 hover:bg-primary-100 hover:text-primary-600 transition-colors">
              <Twitter className="w-6 h-6" />
            </a>
            <a href="mailto:team@truthlens.ai" className="p-3 bg-gray-100 rounded-lg text-gray-600 hover:bg-primary-100 hover:text-primary-600 transition-colors">
              <Mail className="w-6 h-6" />
            </a>
          </div>
          <p className="text-sm text-gray-500">MIT License </p>
        </div>
      </div>
    </Layout>
  )
}