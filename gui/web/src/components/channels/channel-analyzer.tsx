'use client'

import { useState, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { Badge } from '@/components/ui/badge'

interface ChannelAnalysis {
  channel_id: string
  channel_name: string
  title: string
  description: string
  subscriber_count: number
  video_count: number
  recent_videos: Array<{
    title: string
    duration: string
    view_count: number
    published_at: string
  }>
  content_themes: string[]
  language: string
  upload_frequency: string
  recommended_config: {
    model: string
    cost_threshold: number
    multi_model_enabled: boolean
    custom_prompt_suggestions: string[]
  }
}

interface ChannelAnalyzerProps {
  onChannelAnalyzed: () => void
  onCancel: () => void
}

export function ChannelAnalyzer({ onChannelAnalyzed, onCancel }: ChannelAnalyzerProps) {
  const [inputUrl, setInputUrl] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [analysis, setAnalysis] = useState<ChannelAnalysis | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  const extractChannelId = (url: string): string | null => {
    // Handle various YouTube URL formats
    const patterns = [
      /youtube\.com\/channel\/([a-zA-Z0-9_-]+)/,
      /youtube\.com\/c\/([a-zA-Z0-9_-]+)/,
      /youtube\.com\/user\/([a-zA-Z0-9_-]+)/,
      /youtube\.com\/@([a-zA-Z0-9_-]+)/,
      /^UC[a-zA-Z0-9_-]{22}$/ // Direct channel ID
    ]

    for (const pattern of patterns) {
      const match = url.match(pattern)
      if (match) {
        return match[1]
      }
    }

    return null
  }

  const analyzeChannel = useCallback(async () => {
    if (!inputUrl.trim()) {
      setError('Please enter a YouTube channel URL or ID')
      return
    }

    setAnalyzing(true)
    setError(null)
    setAnalysis(null)

    try {
      // Extract channel identifier
      const channelId = extractChannelId(inputUrl.trim())
      if (!channelId) {
        throw new Error('Invalid YouTube channel URL or ID format')
      }

      // TODO: Implement actual YouTube API integration
      // For now, simulate the analysis with mock data
      await new Promise(resolve => setTimeout(resolve, 2000))

      // Mock analysis result
      const mockAnalysis: ChannelAnalysis = {
        channel_id: `UC${Math.random().toString(36).substr(2, 22)}`,
        channel_name: channelId.toLowerCase().replace(/[^a-z0-9]/g, '_'),
        title: `${channelId} Channel`,
        description: 'Analyzed channel description would appear here...',
        subscriber_count: Math.floor(Math.random() * 1000000),
        video_count: Math.floor(Math.random() * 500) + 50,
        recent_videos: [
          {
            title: 'Recent Video 1',
            duration: '10:23',
            view_count: 15000,
            published_at: '2024-01-15'
          },
          {
            title: 'Recent Video 2', 
            duration: '8:45',
            view_count: 22000,
            published_at: '2024-01-12'
          }
        ],
        content_themes: ['Technology', 'Education', 'Tutorial'],
        language: 'English',
        upload_frequency: '2-3 videos per week',
        recommended_config: {
          model: 'gpt-4o-mini',
          cost_threshold: 0.50,
          multi_model_enabled: false,
          custom_prompt_suggestions: [
            'Focus on technical accuracy and clear explanations',
            'Maintain educational tone and highlight key concepts',
            'Include practical applications and examples'
          ]
        }
      }

      setAnalysis(mockAnalysis)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze channel')
      console.error('Channel analysis error:', err)
    } finally {
      setAnalyzing(false)
    }
  }, [inputUrl])

  const createChannelFromAnalysis = async () => {
    if (!analysis) return

    setCreating(true)
    setError(null)

    try {
      const channelConfig = {
        channel_id: analysis.channel_id,
        channel_name: analysis.channel_name,
        model: analysis.recommended_config.model,
        cost_threshold: analysis.recommended_config.cost_threshold,
        multi_model_enabled: analysis.recommended_config.multi_model_enabled,
        telegram_chat_id: '',
        custom_prompt: analysis.recommended_config.custom_prompt_suggestions.join('\n\n')
      }

      const response = await fetch('/api/channels', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(channelConfig)
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to create channel: ${response.statusText}`)
      }

      onChannelAnalyzed()

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create channel')
      console.error('Error creating channel:', err)
    } finally {
      setCreating(false)
    }
  }

  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`
    }
    return num.toString()
  }

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="space-y-4">
          <div>
            <h2 className="text-xl font-semibold">Smart Channel Analyzer</h2>
            <p className="text-sm text-muted-foreground">
              Analyze a YouTube channel and get intelligent configuration recommendations.
            </p>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          <div className="space-y-3">
            <Label htmlFor="channel_url">YouTube Channel URL or ID</Label>
            <div className="flex space-x-2">
              <Input
                id="channel_url"
                placeholder="https://youtube.com/@channelname or UCxxxxxxxxxxxxxxxxxxxxx"
                value={inputUrl}
                onChange={(e) => setInputUrl(e.target.value)}
                disabled={analyzing}
              />
              <Button
                onClick={analyzeChannel}
                disabled={analyzing || !inputUrl.trim()}
                className="flex items-center space-x-2"
              >
                {analyzing && <LoadingSpinner size="sm" />}
                <span>{analyzing ? 'Analyzing...' : 'Analyze'}</span>
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Supports channel URLs, @handles, and direct channel IDs
            </p>
          </div>

          {analyzing && (
            <div className="text-center py-8">
              <LoadingSpinner size="lg" />
              <p className="text-sm text-muted-foreground mt-4">
                Analyzing channel metadata and recent content...
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* Analysis Results */}
      {analysis && (
        <div className="space-y-4">
          {/* Channel Overview */}
          <Card className="p-6">
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold">{analysis.title}</h3>
                  <p className="text-sm text-muted-foreground">
                    Channel ID: {analysis.channel_id}
                  </p>
                </div>
                <div className="flex space-x-2">
                  <Badge>{analysis.language}</Badge>
                  <Badge variant="outline">{analysis.upload_frequency}</Badge>
                </div>
              </div>

              <p className="text-sm">{analysis.description}</p>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {formatNumber(analysis.subscriber_count)}
                  </div>
                  <div className="text-xs text-muted-foreground">Subscribers</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {analysis.video_count}
                  </div>
                  <div className="text-xs text-muted-foreground">Videos</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">
                    {analysis.content_themes.length}
                  </div>
                  <div className="text-xs text-muted-foreground">Themes</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-orange-600">
                    {analysis.recent_videos.length}
                  </div>
                  <div className="text-xs text-muted-foreground">Recent</div>
                </div>
              </div>
            </div>
          </Card>

          {/* Content Analysis */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Content Themes */}
            <Card className="p-4">
              <h4 className="font-medium mb-3">Content Themes</h4>
              <div className="flex flex-wrap gap-2">
                {analysis.content_themes.map((theme, index) => (
                  <Badge key={index} variant="outline">
                    {theme}
                  </Badge>
                ))}
              </div>
            </Card>

            {/* Recent Videos */}
            <Card className="p-4">
              <h4 className="font-medium mb-3">Recent Videos</h4>
              <div className="space-y-2">
                {analysis.recent_videos.map((video, index) => (
                  <div key={index} className="text-sm">
                    <div className="font-medium truncate">{video.title}</div>
                    <div className="text-muted-foreground text-xs">
                      {video.duration} • {formatNumber(video.view_count)} views • {video.published_at}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Recommended Configuration */}
          <Card className="p-6">
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Recommended Configuration</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <Label className="text-sm font-medium">AI Model</Label>
                  <div className="mt-1 p-2 bg-blue-50 rounded text-sm">
                    {analysis.recommended_config.model}
                  </div>
                </div>
                <div>
                  <Label className="text-sm font-medium">Cost Threshold</Label>
                  <div className="mt-1 p-2 bg-green-50 rounded text-sm">
                    ${analysis.recommended_config.cost_threshold.toFixed(2)}
                  </div>
                </div>
                <div>
                  <Label className="text-sm font-medium">Multi-Model</Label>
                  <div className="mt-1 p-2 bg-purple-50 rounded text-sm">
                    {analysis.recommended_config.multi_model_enabled ? 'Enabled' : 'Disabled'}
                  </div>
                </div>
              </div>

              <div>
                <Label className="text-sm font-medium">Custom Prompt Suggestions</Label>
                <div className="mt-2 space-y-2">
                  {analysis.recommended_config.custom_prompt_suggestions.map((suggestion, index) => (
                    <div key={index} className="p-2 bg-gray-50 rounded text-sm">
                      • {suggestion}
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex space-x-2 pt-4 border-t">
                <Button
                  onClick={createChannelFromAnalysis}
                  disabled={creating}
                  className="flex items-center space-x-2"
                >
                  {creating && <LoadingSpinner size="sm" />}
                  <span>{creating ? 'Creating...' : 'Create Channel with These Settings'}</span>
                </Button>
                <Button onClick={onCancel} variant="outline">
                  Cancel
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Help Card */}
      <Card className="p-4">
        <div className="space-y-3">
          <h4 className="font-medium">How Smart Analysis Works</h4>
          <div className="text-sm text-muted-foreground space-y-2">
            <div>
              <strong>1. Channel Detection:</strong> Extracts channel ID from various YouTube URL formats
            </div>
            <div>
              <strong>2. Metadata Analysis:</strong> Retrieves channel info, subscriber count, and recent videos
            </div>
            <div>
              <strong>3. Content Analysis:</strong> Analyzes video titles, descriptions, and themes
            </div>
            <div>
              <strong>4. Smart Recommendations:</strong> Suggests optimal AI model and configuration based on content type
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}