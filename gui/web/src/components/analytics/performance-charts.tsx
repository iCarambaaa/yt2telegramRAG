'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface PerformanceData {
  response_times: {
    timestamps: string[]
    values: number[]
    avg: number
    p95: number
    p99: number
  }
  throughput: {
    timestamps: string[]
    values: number[]
    peak: number
    avg: number
  }
  error_rates: {
    timestamps: string[]
    values: number[]
    total_errors: number
    error_rate: number
  }
  resource_usage: {
    cpu: {
      timestamps: string[]
      values: number[]
      avg: number
      peak: number
    }
    memory: {
      timestamps: string[]
      values: number[]
      avg: number
      peak: number
    }
    disk_io: {
      timestamps: string[]
      read_values: number[]
      write_values: number[]
    }
  }
}

interface PerformanceChartsProps {
  timeRange: string
  refreshTrigger: number
  compact: boolean
}

export function PerformanceCharts({ timeRange, refreshTrigger, compact }: PerformanceChartsProps) {
  const [data, setData] = useState<PerformanceData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeChart, setActiveChart] = useState<'response' | 'throughput' | 'errors' | 'resources'>('response')

  const fetchPerformanceData = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/analytics/performance?timeRange=${timeRange}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch performance data: ${response.statusText}`)
      }

      const performanceData = await response.json()
      setData(performanceData)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch performance data')
      console.error('Error fetching performance data:', err)
    } finally {
      setLoading(false)
    }
  }, [timeRange])

  useEffect(() => {
    fetchPerformanceData()
  }, [fetchPerformanceData, refreshTrigger])

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  const formatBytes = (bytes: number) => {
    if (bytes >= 1024 * 1024 * 1024) {
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
    } else if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    } else if (bytes >= 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`
    }
    return `${bytes} B`
  }

  // Simple ASCII chart component
  const SimpleChart = ({ 
    data, 
    label, 
    color = 'blue',
    height = 60 
  }: { 
    data: number[]
    label: string
    color?: string
    height?: number 
  }) => {
    if (!data || data.length === 0) return null

    const max = Math.max(...data)
    const min = Math.min(...data)
    const range = max - min || 1

    return (
      <div className="space-y-2">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>{label}</span>
          <span>Max: {max.toFixed(1)}</span>
        </div>
        <div className="relative bg-muted rounded" style={{ height: `${height}px` }}>
          <svg width="100%" height={height} className="absolute inset-0">
            <polyline
              fill="none"
              stroke={color === 'blue' ? '#3b82f6' : color === 'green' ? '#10b981' : color === 'red' ? '#ef4444' : '#8b5cf6'}
              strokeWidth="2"
              points={data.map((value, index) => {
                const x = (index / (data.length - 1)) * 100
                const y = height - ((value - min) / range) * (height - 10) - 5
                return `${x}%,${y}`
              }).join(' ')}
            />
          </svg>
        </div>
      </div>
    )
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
          <Button onClick={fetchPerformanceData} variant="outline">
            Try Again
          </Button>
        </div>
      </Card>
    )
  }

  if (!data) {
    return null
  }

  if (compact) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Performance Overview</h3>
        <div className="space-y-4">
          <SimpleChart 
            data={data.response_times.values} 
            label="Response Time (ms)" 
            color="blue"
          />
          <SimpleChart 
            data={data.throughput.values} 
            label="Throughput (req/min)" 
            color="green"
          />
          <SimpleChart 
            data={data.error_rates.values} 
            label="Error Rate (%)" 
            color="red"
          />
        </div>
        <div className="mt-4 grid grid-cols-3 gap-4 text-center text-sm">
          <div>
            <div className="font-medium">{data.response_times.avg.toFixed(1)}ms</div>
            <div className="text-muted-foreground">Avg Response</div>
          </div>
          <div>
            <div className="font-medium">{data.throughput.avg.toFixed(1)}</div>
            <div className="text-muted-foreground">Avg Throughput</div>
          </div>
          <div>
            <div className="font-medium">{(data.error_rates.error_rate * 100).toFixed(2)}%</div>
            <div className="text-muted-foreground">Error Rate</div>
          </div>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Chart Navigation */}
      <Card className="p-4">
        <div className="flex space-x-1 bg-muted p-1 rounded-lg">
          <Button
            variant={activeChart === 'response' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveChart('response')}
          >
            Response Times
          </Button>
          <Button
            variant={activeChart === 'throughput' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveChart('throughput')}
          >
            Throughput
          </Button>
          <Button
            variant={activeChart === 'errors' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveChart('errors')}
          >
            Error Rates
          </Button>
          <Button
            variant={activeChart === 'resources' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveChart('resources')}
          >
            Resources
          </Button>
        </div>
      </Card>

      {/* Chart Content */}
      {activeChart === 'response' && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Response Times</h3>
          <SimpleChart 
            data={data.response_times.values} 
            label="Response Time (ms)" 
            color="blue"
            height={120}
          />
          <div className="mt-4 grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-blue-600">{data.response_times.avg.toFixed(1)}ms</div>
              <div className="text-sm text-muted-foreground">Average</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-purple-600">{data.response_times.p95.toFixed(1)}ms</div>
              <div className="text-sm text-muted-foreground">95th Percentile</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-red-600">{data.response_times.p99.toFixed(1)}ms</div>
              <div className="text-sm text-muted-foreground">99th Percentile</div>
            </div>
          </div>
        </Card>
      )}

      {activeChart === 'throughput' && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">System Throughput</h3>
          <SimpleChart 
            data={data.throughput.values} 
            label="Requests per Minute" 
            color="green"
            height={120}
          />
          <div className="mt-4 grid grid-cols-2 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-green-600">{data.throughput.avg.toFixed(1)}</div>
              <div className="text-sm text-muted-foreground">Average req/min</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-blue-600">{data.throughput.peak.toFixed(1)}</div>
              <div className="text-sm text-muted-foreground">Peak req/min</div>
            </div>
          </div>
        </Card>
      )}

      {activeChart === 'errors' && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Error Rates</h3>
          <SimpleChart 
            data={data.error_rates.values} 
            label="Error Rate (%)" 
            color="red"
            height={120}
          />
          <div className="mt-4 grid grid-cols-2 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-red-600">{data.error_rates.total_errors}</div>
              <div className="text-sm text-muted-foreground">Total Errors</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-orange-600">{(data.error_rates.error_rate * 100).toFixed(2)}%</div>
              <div className="text-sm text-muted-foreground">Error Rate</div>
            </div>
          </div>
        </Card>
      )}

      {activeChart === 'resources' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">CPU Usage</h3>
            <SimpleChart 
              data={data.resource_usage.cpu.values} 
              label="CPU Usage (%)" 
              color="purple"
              height={100}
            />
            <div className="mt-4 grid grid-cols-2 gap-4 text-center">
              <div>
                <div className="text-xl font-bold text-purple-600">{(data.resource_usage.cpu.avg * 100).toFixed(1)}%</div>
                <div className="text-sm text-muted-foreground">Average</div>
              </div>
              <div>
                <div className="text-xl font-bold text-red-600">{(data.resource_usage.cpu.peak * 100).toFixed(1)}%</div>
                <div className="text-sm text-muted-foreground">Peak</div>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Memory Usage</h3>
            <SimpleChart 
              data={data.resource_usage.memory.values} 
              label="Memory Usage (%)" 
              color="blue"
              height={100}
            />
            <div className="mt-4 grid grid-cols-2 gap-4 text-center">
              <div>
                <div className="text-xl font-bold text-blue-600">{(data.resource_usage.memory.avg * 100).toFixed(1)}%</div>
                <div className="text-sm text-muted-foreground">Average</div>
              </div>
              <div>
                <div className="text-xl font-bold text-red-600">{(data.resource_usage.memory.peak * 100).toFixed(1)}%</div>
                <div className="text-sm text-muted-foreground">Peak</div>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}