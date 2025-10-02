'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface VideoDetails {
  id: string
  title: string
  channel_id: string
  published_at: string
  processed_at: string
  raw_subtitles: string
  cleaned_subtitles: string
  summary: string
  summarization_method: string
  primary_summary?: string
  secondary_summary?: string
  synthesis_summary?: string
  primary_model: string
  secondary_model?: string
  synthesis_model?: string
  token_usage_json: string
  processing_time_seconds: number
  cost_estimate: number
  fallback_used: boolean
  metadata: {
    duration: string
    view_count: number
    like_count: number
    comment_count: number
  }
}

interface VideoDetailsModalProps {
  videoId: string
  onClose: () => void
}

export function VideoDetailsModal({ videoId, onClose }: VideoDetailsModalProps) {
  const [video, setVideo] = useState<VideoDetails | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'content' | 'processing'>('overview')

  const fetchVideoDetails = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/analytics/database/videos/${videoId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch video details: ${response.statusText}`)
      }

      const data = await response.json()
      setVideo(data)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch video details')
      console.error('Error fetching video details:', err)
    } finally {
      setLoading(false)
    }
  }, [videoId])

  useEffect(() => {
    fetchVideoDetails()
  }, [fetchVideoDetails])

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`
    }
    return num.toString()
  }

  const parseTokenUsage = (tokenUsageJson: string) => {
    try {
      return JSON.parse(tokenUsageJson)
    } catch {
      return null
    }
  }

  const truncateText = (text: string, maxLength: number = 200) => {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  // Handle backdrop click
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-background rounded-lg shadow-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">Video Details</h2>
          <Button onClick={onClose} variant="ghost" size="sm">
            ✕
          </Button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-120px)]">
          {loading && (
            <div className="flex justify-center py-8">
              <LoadingSpinner size="lg" />
            </div>
          )}

          {error && (
            <div className="p-6">
              <div className="text-center">
                <p className="text-red-600 mb-4">Error: {error}</p>
                <Button onClick={fetchVideoDetails} variant="outline">
                  Try Again
                </Button>
              </div>
            </div>
          )}

          {video && (
            <div className="p-6 space-y-6">
              {/* Video Info */}
              <div>
                <h3 className="text-lg font-medium mb-2">{video.title}</h3>
                <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                  <span>ID: {video.id}</span>
                  <span>Channel: {video.channel_id.substring(0, 12)}...</span>
                  <span>Published: {formatTimestamp(video.published_at)}</span>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex space-x-1 bg-muted p-1 rounded-lg">
                <Button
                  variant={activeTab === 'overview' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setActiveTab('overview')}
                >
                  Overview
                </Button>
                <Button
                  variant={activeTab === 'content' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setActiveTab('content')}
                >
                  Content
                </Button>
                <Button
                  variant={activeTab === 'processing' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setActiveTab('processing')}
                >
                  Processing
                </Button>
              </div>

              {/* Tab Content */}
              {activeTab === 'overview' && (
                <div className="space-y-4">
                  {/* Metadata */}
                  <Card className="p-4">
                    <h4 className="font-medium mb-3">Video Metadata</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <div className="text-sm text-muted-foreground">Duration</div>
                        <div className="font-medium">{video.metadata.duration}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Views</div>
                        <div className="font-medium">{formatNumber(video.metadata.view_count)}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Likes</div>
                        <div className="font-medium">{formatNumber(video.metadata.like_count)}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Comments</div>
                        <div className="font-medium">{formatNumber(video.metadata.comment_count)}</div>
                      </div>
                    </div>
                  </Card>

                  {/* Processing Summary */}
                  <Card className="p-4">
                    <h4 className="font-medium mb-3">Processing Summary</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <div className="text-sm text-muted-foreground">Method</div>
                        <Badge className={video.summarization_method === 'multi' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'}>
                          {video.summarization_method}
                        </Badge>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Processing Time</div>
                        <div className="font-medium">{video.processing_time_seconds.toFixed(1)}s</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Cost</div>
                        <div className="font-medium">${video.cost_estimate.toFixed(3)}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Fallback Used</div>
                        <Badge className={video.fallback_used ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}>
                          {video.fallback_used ? 'Yes' : 'No'}
                        </Badge>
                      </div>
                    </div>
                  </Card>

                  {/* Models Used */}
                  <Card className="p-4">
                    <h4 className="font-medium mb-3">Models Used</h4>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Primary Model:</span>
                        <span className="font-medium">{video.primary_model}</span>
                      </div>
                      {video.secondary_model && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Secondary Model:</span>
                          <span className="font-medium">{video.secondary_model}</span>
                        </div>
                      )}
                      {video.synthesis_model && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Synthesis Model:</span>
                          <span className="font-medium">{video.synthesis_model}</span>
                        </div>
                      )}
                    </div>
                  </Card>
                </div>
              )}

              {activeTab === 'content' && (
                <div className="space-y-4">
                  {/* Summary */}
                  <Card className="p-4">
                    <h4 className="font-medium mb-3">Final Summary</h4>
                    <div className="text-sm leading-relaxed">
                      {video.summary || 'No summary available'}
                    </div>
                  </Card>

                  {/* Multi-model Summaries */}
                  {video.summarization_method === 'multi' && (
                    <>
                      {video.primary_summary && (
                        <Card className="p-4">
                          <h4 className="font-medium mb-3">Primary Summary ({video.primary_model})</h4>
                          <div className="text-sm leading-relaxed">
                            {truncateText(video.primary_summary, 500)}
                          </div>
                        </Card>
                      )}

                      {video.secondary_summary && (
                        <Card className="p-4">
                          <h4 className="font-medium mb-3">Secondary Summary ({video.secondary_model})</h4>
                          <div className="text-sm leading-relaxed">
                            {truncateText(video.secondary_summary, 500)}
                          </div>
                        </Card>
                      )}

                      {video.synthesis_summary && (
                        <Card className="p-4">
                          <h4 className="font-medium mb-3">Synthesis Summary ({video.synthesis_model})</h4>
                          <div className="text-sm leading-relaxed">
                            {truncateText(video.synthesis_summary, 500)}
                          </div>
                        </Card>
                      )}
                    </>
                  )}

                  {/* Subtitles */}
                  <Card className="p-4">
                    <h4 className="font-medium mb-3">Cleaned Subtitles (Preview)</h4>
                    <div className="text-sm leading-relaxed bg-muted p-3 rounded max-h-40 overflow-y-auto">
                      {truncateText(video.cleaned_subtitles, 1000)}
                    </div>
                  </Card>
                </div>
              )}

              {activeTab === 'processing' && (
                <div className="space-y-4">
                  {/* Token Usage */}
                  {parseTokenUsage(video.token_usage_json) && (
                    <Card className="p-4">
                      <h4 className="font-medium mb-3">Token Usage</h4>
                      <div className="space-y-3">
                        {Object.entries(parseTokenUsage(video.token_usage_json)).map(([model, usage]: [string, any]) => (
                          <div key={model} className="border-b pb-2 last:border-b-0">
                            <div className="font-medium text-sm mb-1 capitalize">{model} Model</div>
                            <div className="grid grid-cols-3 gap-4 text-sm">
                              <div>
                                <span className="text-muted-foreground">Input:</span>
                                <span className="ml-1 font-medium">{formatNumber(usage.input)}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Output:</span>
                                <span className="ml-1 font-medium">{formatNumber(usage.output)}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Total:</span>
                                <span className="ml-1 font-medium">{formatNumber(usage.input + usage.output)}</span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </Card>
                  )}

                  {/* Processing Timeline */}
                  <Card className="p-4">
                    <h4 className="font-medium mb-3">Processing Timeline</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span>Published:</span>
                        <span>{formatTimestamp(video.published_at)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Processed:</span>
                        <span>{formatTimestamp(video.processed_at)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Processing Duration:</span>
                        <span>{video.processing_time_seconds.toFixed(1)} seconds</span>
                      </div>
                    </div>
                  </Card>

                  {/* Raw Data */}
                  <Card className="p-4">
                    <h4 className="font-medium mb-3">Raw Subtitles (Preview)</h4>
                    <div className="text-sm leading-relaxed bg-muted p-3 rounded max-h-40 overflow-y-auto font-mono">
                      {truncateText(video.raw_subtitles, 1000)}
                    </div>
                  </Card>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}