'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface ChannelMetrics {
  channel_id: string
  channel_name: string
  videos_processed: number
  total_cost: number
  avg_cost_per_video: number
  avg_processing_time: number
  success_rate: number
  last_processed: string
  processing_trend: Array<{
    date: string
    count: number
    cost: number
  }>
  model_usage: {
    [model: string]: {
      count: number
      cost: number
      avg_time: number
    }
  }
  error_rate: number
  queue_size: number
}

interface ChannelAnalyticsProps {
  timeRange: string
  refreshTrigger: number
}

export function ChannelAnalytics({ timeRange, refreshTrigger }: ChannelAnalyticsProps) {
  const [channels, setChannels] = useState<ChannelMetrics[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<'videos' | 'cost' | 'success_rate' | 'processing_time'>('videos')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const fetchChannelAnalytics = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/analytics/channels?timeRange=${timeRange}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch channel analytics: ${response.statusText}`)
      }

      const data = await response.json()
      setChannels(data.channels || [])

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch channel analytics')
      console.error('Error fetching channel analytics:', err)
    } finally {
      setLoading(false)
    }
  }, [timeRange])

  useEffect(() => {
    fetchChannelAnalytics()
  }, [fetchChannelAnalytics, refreshTrigger])

  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`
    }
    return num.toString()
  }

  const formatCurrency = (amount: number): string => {
    return `$${amount.toFixed(2)}`
  }

  const formatPercentage = (rate: number): string => {
    return `${(rate * 100).toFixed(1)}%`
  }

  const sortedChannels = [...channels].sort((a, b) => {
    let aValue: number, bValue: number
    
    switch (sortBy) {
      case 'videos':
        aValue = a.videos_processed
        bValue = b.videos_processed
        break
      case 'cost':
        aValue = a.total_cost
        bValue = b.total_cost
        break
      case 'success_rate':
        aValue = a.success_rate
        bValue = b.success_rate
        break
      case 'processing_time':
        aValue = a.avg_processing_time
        bValue = b.avg_processing_time
        break
      default:
        aValue = a.videos_processed
        bValue = b.videos_processed
    }

    return sortOrder === 'asc' ? aValue - bValue : bValue - aValue
  })

  const selectedChannelData = selectedChannel ? channels.find(c => c.channel_id === selectedChannel) : null

  if (loading) {
    return (
      <Card className="p-6">
        <div className="flex justify-center">
          <LoadingSpinner size="lg" />
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="text-center">
          <p className="text-red-600 mb-4">Error: {error}</p>
          <Button onClick={fetchChannelAnalytics} variant="outline">
            Try Again
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Channel List */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Channel Performance</h3>
          <div className="flex items-center space-x-2">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="px-3 py-1 border border-input bg-background rounded-md text-sm"
            >
              <option value="videos">Sort by Videos</option>
              <option value="cost">Sort by Cost</option>
              <option value="success_rate">Sort by Success Rate</option>
              <option value="processing_time">Sort by Processing Time</option>
            </select>
            <Button
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              variant="outline"
              size="sm"
            >
              {sortOrder === 'asc' ? '↑' : '↓'}
            </Button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2">Channel</th>
                <th className="text-right py-2">Videos</th>
                <th className="text-right py-2">Total Cost</th>
                <th className="text-right py-2">Avg Cost</th>
                <th className="text-right py-2">Avg Time</th>
                <th className="text-right py-2">Success Rate</th>
                <th className="text-right py-2">Queue</th>
                <th className="text-center py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedChannels.map((channel) => (
                <tr key={channel.channel_id} className="border-b hover:bg-muted/50">
                  <td className="py-3">
                    <div>
                      <div className="font-medium">{channel.channel_name}</div>
                      <div className="text-xs text-muted-foreground">
                        {channel.channel_id.substring(0, 12)}...
                      </div>
                    </div>
                  </td>
                  <td className="text-right py-3 font-medium">
                    {formatNumber(channel.videos_processed)}
                  </td>
                  <td className="text-right py-3 font-medium">
                    {formatCurrency(channel.total_cost)}
                  </td>
                  <td className="text-right py-3">
                    {formatCurrency(channel.avg_cost_per_video)}
                  </td>
                  <td className="text-right py-3">
                    {channel.avg_processing_time.toFixed(1)}s
                  </td>
                  <td className="text-right py-3">
                    <Badge className={
                      channel.success_rate >= 0.95 ? 'bg-green-100 text-green-800' :
                      channel.success_rate >= 0.90 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }>
                      {formatPercentage(channel.success_rate)}
                    </Badge>
                  </td>
                  <td className="text-right py-3">
                    <Badge variant={channel.queue_size > 0 ? 'default' : 'outline'}>
                      {channel.queue_size}
                    </Badge>
                  </td>
                  <td className="text-center py-3">
                    <Button
                      onClick={() => setSelectedChannel(
                        selectedChannel === channel.channel_id ? null : channel.channel_id
                      )}
                      variant="outline"
                      size="sm"
                    >
                      {selectedChannel === channel.channel_id ? 'Hide' : 'Details'}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {channels.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            No channel data available for the selected time range.
          </div>
        )}
      </Card>

      {/* Channel Details */}
      {selectedChannelData && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Processing Trend */}
          <Card className="p-6">
            <h4 className="font-medium mb-4">Processing Trend - {selectedChannelData.channel_name}</h4>
            <div className="space-y-3">
              {selectedChannelData.processing_trend.map((day, index) => (
                <div key={index} className="flex justify-between items-center">
                  <span className="text-sm">{day.date}</span>
                  <div className="flex items-center space-x-4">
                    <span className="text-sm font-medium">{day.count} videos</span>
                    <span className="text-sm text-muted-foreground">
                      {formatCurrency(day.cost)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Model Usage */}
          <Card className="p-6">
            <h4 className="font-medium mb-4">Model Usage - {selectedChannelData.channel_name}</h4>
            <div className="space-y-3">
              {Object.entries(selectedChannelData.model_usage).map(([model, usage]) => (
                <div key={model} className="border-b pb-2 last:border-b-0">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm font-medium">{model}</span>
                    <span className="text-sm">{usage.count} uses</span>
                  </div>
                  <div className="flex justify-between items-center text-xs text-muted-foreground">
                    <span>Cost: {formatCurrency(usage.cost)}</span>
                    <span>Avg Time: {usage.avg_time.toFixed(1)}s</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* Summary Stats */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Channel Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-blue-600">
              {channels.length}
            </div>
            <div className="text-sm text-muted-foreground">Total Channels</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-green-600">
              {formatNumber(channels.reduce((sum, c) => sum + c.videos_processed, 0))}
            </div>
            <div className="text-sm text-muted-foreground">Total Videos</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-orange-600">
              {formatCurrency(channels.reduce((sum, c) => sum + c.total_cost, 0))}
            </div>
            <div className="text-sm text-muted-foreground">Total Cost</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-purple-600">
              {channels.reduce((sum, c) => sum + c.queue_size, 0)}
            </div>
            <div className="text-sm text-muted-foreground">Total Queue</div>
          </div>
        </div>
      </Card>
    </div>
  )
}