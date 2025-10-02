'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface SystemMetrics {
  overview: {
    total_videos_processed: number
    active_channels: number
    processing_queue_size: number
    total_cost_today: number
    avg_processing_time: number
    success_rate: number
  }
  real_time: {
    videos_processed_last_hour: number
    current_processing_rate: number
    active_connections: number
    system_load: number
    memory_usage: number
    disk_usage: number
  }
  alerts: Array<{
    type: 'info' | 'warning' | 'error'
    message: string
    timestamp: string
  }>
}

interface SystemMetricsProps {
  timeRange: string
  refreshTrigger: number
}

export function SystemMetrics({ timeRange, refreshTrigger }: SystemMetricsProps) {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchMetrics = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/analytics/metrics?timeRange=${timeRange}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch metrics: ${response.statusText}`)
      }

      const data = await response.json()
      setMetrics(data)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics')
      console.error('Error fetching metrics:', err)
    } finally {
      setLoading(false)
    }
  }, [timeRange])

  useEffect(() => {
    fetchMetrics()
  }, [fetchMetrics, refreshTrigger])

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

  const getStatusColor = (type: string) => {
    switch (type) {
      case 'error': return 'text-red-600'
      case 'warning': return 'text-yellow-600'
      case 'info': return 'text-blue-600'
      default: return 'text-gray-600'
    }
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
          <Button onClick={fetchMetrics} variant="outline">
            Try Again
          </Button>
        </div>
      </Card>
    )
  }

  if (!metrics) {
    return null
  }

  return (
    <div className="space-y-6">
      {/* Overview Metrics */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">System Overview</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {formatNumber(metrics.overview.total_videos_processed)}
            </div>
            <div className="text-sm text-muted-foreground">Videos Processed</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {metrics.overview.active_channels}
            </div>
            <div className="text-sm text-muted-foreground">Active Channels</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              {metrics.overview.processing_queue_size}
            </div>
            <div className="text-sm text-muted-foreground">Queue Size</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">
              {formatCurrency(metrics.overview.total_cost_today)}
            </div>
            <div className="text-sm text-muted-foreground">Cost Today</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-teal-600">
              {metrics.overview.avg_processing_time.toFixed(1)}s
            </div>
            <div className="text-sm text-muted-foreground">Avg Time</div>
          </div>
          <div className="text-center">
            <div className={`text-2xl font-bold ${
              metrics.overview.success_rate >= 0.95 ? 'text-green-600' :
              metrics.overview.success_rate >= 0.90 ? 'text-yellow-600' :
              'text-red-600'
            }`}>
              {formatPercentage(metrics.overview.success_rate)}
            </div>
            <div className="text-sm text-muted-foreground">Success Rate</div>
          </div>
        </div>
      </Card>

      {/* Real-time Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Real-time Activity</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm">Videos/Hour:</span>
              <span className="font-bold text-lg">{metrics.real_time.videos_processed_last_hour}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm">Processing Rate:</span>
              <span className="font-bold text-lg">{metrics.real_time.current_processing_rate.toFixed(1)}/min</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm">Active Connections:</span>
              <span className="font-bold text-lg">{metrics.real_time.active_connections}</span>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">System Resources</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm">System Load:</span>
              <div className="flex items-center space-x-2">
                <div className="w-24 bg-gray-200 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full ${
                      metrics.real_time.system_load > 0.8 ? 'bg-red-500' :
                      metrics.real_time.system_load > 0.6 ? 'bg-yellow-500' :
                      'bg-green-500'
                    }`}
                    style={{ width: `${metrics.real_time.system_load * 100}%` }}
                  />
                </div>
                <span className="font-bold text-sm">{formatPercentage(metrics.real_time.system_load)}</span>
              </div>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm">Memory Usage:</span>
              <div className="flex items-center space-x-2">
                <div className="w-24 bg-gray-200 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full ${
                      metrics.real_time.memory_usage > 0.8 ? 'bg-red-500' :
                      metrics.real_time.memory_usage > 0.6 ? 'bg-yellow-500' :
                      'bg-green-500'
                    }`}
                    style={{ width: `${metrics.real_time.memory_usage * 100}%` }}
                  />
                </div>
                <span className="font-bold text-sm">{formatPercentage(metrics.real_time.memory_usage)}</span>
              </div>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm">Disk Usage:</span>
              <div className="flex items-center space-x-2">
                <div className="w-24 bg-gray-200 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full ${
                      metrics.real_time.disk_usage > 0.8 ? 'bg-red-500' :
                      metrics.real_time.disk_usage > 0.6 ? 'bg-yellow-500' :
                      'bg-green-500'
                    }`}
                    style={{ width: `${metrics.real_time.disk_usage * 100}%` }}
                  />
                </div>
                <span className="font-bold text-sm">{formatPercentage(metrics.real_time.disk_usage)}</span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Alerts */}
      {metrics.alerts.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">System Alerts</h3>
          <div className="space-y-3">
            {metrics.alerts.map((alert, index) => (
              <div key={index} className="flex items-start space-x-3 p-3 rounded-md bg-muted">
                <div className={`w-2 h-2 rounded-full mt-2 ${
                  alert.type === 'error' ? 'bg-red-500' :
                  alert.type === 'warning' ? 'bg-yellow-500' :
                  'bg-blue-500'
                }`} />
                <div className="flex-1">
                  <p className={`text-sm font-medium ${getStatusColor(alert.type)}`}>
                    {alert.message}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {new Date(alert.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}