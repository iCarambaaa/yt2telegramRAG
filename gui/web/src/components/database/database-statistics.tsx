'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface DatabaseStatistics {
  overview: {
    total_videos: number
    total_channels: number
    processed_today: number
    processing_errors: number
    total_cost: number
    avg_processing_time: number
  }
  by_channel: Array<{
    channel_id: string
    channel_name: string
    video_count: number
    total_cost: number
    avg_cost_per_video: number
    success_rate: number
  }>
  by_model: Array<{
    model: string
    usage_count: number
    total_cost: number
    avg_cost: number
    avg_processing_time: number
  }>
  processing_trends: {
    daily_counts: Array<{
      date: string
      count: number
      cost: number
    }>
    success_rate_trend: Array<{
      date: string
      success_rate: number
    }>
  }
  storage_info: {
    database_size_mb: number
    subtitle_storage_mb: number
    summary_storage_mb: number
    growth_rate_mb_per_day: number
  }
  performance_metrics: {
    avg_query_time_ms: number
    slow_queries_count: number
    connection_pool_usage: number
    cache_hit_rate: number
  }
}

interface DatabaseStatisticsProps {
  refreshTrigger: number
}

export function DatabaseStatistics({ refreshTrigger }: DatabaseStatisticsProps) {
  const [statistics, setStatistics] = useState<DatabaseStatistics | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchStatistics = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/analytics/database/statistics', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch statistics: ${response.statusText}`)
      }

      const data = await response.json()
      setStatistics(data)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch statistics')
      console.error('Error fetching statistics:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatistics()
  }, [fetchStatistics, refreshTrigger])

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

  const formatSize = (mb: number): string => {
    if (mb >= 1024) {
      return `${(mb / 1024).toFixed(1)} GB`
    }
    return `${mb.toFixed(1)} MB`
  }

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
          <Button onClick={fetchStatistics} variant="outline">
            Try Again
          </Button>
        </div>
      </Card>
    )
  }

  if (!statistics) {
    return null
  }

  return (
    <div className="space-y-6">
      {/* Overview Statistics */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Overview</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {formatNumber(statistics.overview.total_videos)}
            </div>
            <div className="text-sm text-muted-foreground">Total Videos</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {statistics.overview.total_channels}
            </div>
            <div className="text-sm text-muted-foreground">Channels</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              {statistics.overview.processed_today}
            </div>
            <div className="text-sm text-muted-foreground">Today</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">
              {statistics.overview.processing_errors}
            </div>
            <div className="text-sm text-muted-foreground">Errors</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">
              {formatCurrency(statistics.overview.total_cost)}
            </div>
            <div className="text-sm text-muted-foreground">Total Cost</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-teal-600">
              {statistics.overview.avg_processing_time.toFixed(1)}s
            </div>
            <div className="text-sm text-muted-foreground">Avg Time</div>
          </div>
        </div>
      </Card>

      {/* Channel Statistics */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">By Channel</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2">Channel</th>
                <th className="text-right py-2">Videos</th>
                <th className="text-right py-2">Total Cost</th>
                <th className="text-right py-2">Avg Cost</th>
                <th className="text-right py-2">Success Rate</th>
              </tr>
            </thead>
            <tbody>
              {statistics.by_channel.map((channel, index) => (
                <tr key={index} className="border-b">
                  <td className="py-2">
                    <div>
                      <div className="font-medium">{channel.channel_name}</div>
                      <div className="text-xs text-muted-foreground">
                        {channel.channel_id.substring(0, 12)}...
                      </div>
                    </div>
                  </td>
                  <td className="text-right py-2">{formatNumber(channel.video_count)}</td>
                  <td className="text-right py-2">{formatCurrency(channel.total_cost)}</td>
                  <td className="text-right py-2">{formatCurrency(channel.avg_cost_per_video)}</td>
                  <td className="text-right py-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      channel.success_rate >= 0.95 ? 'bg-green-100 text-green-800' :
                      channel.success_rate >= 0.90 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {formatPercentage(channel.success_rate)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Model Statistics */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">By Model</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2">Model</th>
                <th className="text-right py-2">Usage</th>
                <th className="text-right py-2">Total Cost</th>
                <th className="text-right py-2">Avg Cost</th>
                <th className="text-right py-2">Avg Time</th>
              </tr>
            </thead>
            <tbody>
              {statistics.by_model.map((model, index) => (
                <tr key={index} className="border-b">
                  <td className="py-2 font-medium">{model.model}</td>
                  <td className="text-right py-2">{formatNumber(model.usage_count)}</td>
                  <td className="text-right py-2">{formatCurrency(model.total_cost)}</td>
                  <td className="text-right py-2">{formatCurrency(model.avg_cost)}</td>
                  <td className="text-right py-2">{model.avg_processing_time.toFixed(1)}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Storage and Performance */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Storage Information</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span>Database Size:</span>
              <span className="font-medium">{formatSize(statistics.storage_info.database_size_mb)}</span>
            </div>
            <div className="flex justify-between">
              <span>Subtitle Storage:</span>
              <span className="font-medium">{formatSize(statistics.storage_info.subtitle_storage_mb)}</span>
            </div>
            <div className="flex justify-between">
              <span>Summary Storage:</span>
              <span className="font-medium">{formatSize(statistics.storage_info.summary_storage_mb)}</span>
            </div>
            <div className="flex justify-between border-t pt-3">
              <span>Growth Rate:</span>
              <span className="font-medium">{formatSize(statistics.storage_info.growth_rate_mb_per_day)}/day</span>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Performance Metrics</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span>Avg Query Time:</span>
              <span className="font-medium">{statistics.performance_metrics.avg_query_time_ms.toFixed(1)}ms</span>
            </div>
            <div className="flex justify-between">
              <span>Slow Queries:</span>
              <span className="font-medium">{statistics.performance_metrics.slow_queries_count}</span>
            </div>
            <div className="flex justify-between">
              <span>Connection Pool:</span>
              <span className="font-medium">{formatPercentage(statistics.performance_metrics.connection_pool_usage)}</span>
            </div>
            <div className="flex justify-between border-t pt-3">
              <span>Cache Hit Rate:</span>
              <span className="font-medium">{formatPercentage(statistics.performance_metrics.cache_hit_rate)}</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Processing Trends */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Recent Processing Trends</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-medium mb-3">Daily Processing</h4>
            <div className="space-y-2">
              {statistics.processing_trends.daily_counts.map((day, index) => (
                <div key={index} className="flex justify-between text-sm">
                  <span>{day.date}</span>
                  <span>{day.count} videos ({formatCurrency(day.cost)})</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h4 className="font-medium mb-3">Success Rate Trend</h4>
            <div className="space-y-2">
              {statistics.processing_trends.success_rate_trend.map((day, index) => (
                <div key={index} className="flex justify-between text-sm">
                  <span>{day.date}</span>
                  <span className={`px-2 py-1 rounded text-xs ${
                    day.success_rate >= 0.95 ? 'bg-green-100 text-green-800' :
                    day.success_rate >= 0.90 ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {formatPercentage(day.success_rate)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}