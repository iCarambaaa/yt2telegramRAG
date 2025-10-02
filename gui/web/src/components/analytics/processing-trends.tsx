'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface TrendsData {
  processing_volume: {
    timestamps: string[]
    values: number[]
    trend: 'increasing' | 'decreasing' | 'stable'
    growth_rate: number
  }
  success_rates: {
    timestamps: string[]
    values: number[]
    avg_success_rate: number
    trend: 'improving' | 'declining' | 'stable'
  }
  model_adoption: {
    timestamps: string[]
    single_model: number[]
    multi_model: number[]
    multi_model_adoption_rate: number
  }
  processing_times: {
    timestamps: string[]
    avg_times: number[]
    p95_times: number[]
    trend: 'improving' | 'declining' | 'stable'
  }
  cost_trends: {
    timestamps: string[]
    daily_costs: number[]
    cost_per_video: number[]
    efficiency_trend: 'improving' | 'declining' | 'stable'
  }
  predictions: {
    next_week_volume: number
    next_week_cost: number
    capacity_utilization: number
    bottlenecks: Array<{
      component: string
      severity: 'low' | 'medium' | 'high'
      description: string
    }>
  }
}

interface ProcessingTrendsProps {
  timeRange: string
  refreshTrigger: number
}

export function ProcessingTrends({ timeRange, refreshTrigger }: ProcessingTrendsProps) {
  const [data, setData] = useState<TrendsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeView, setActiveView] = useState<'volume' | 'quality' | 'performance' | 'predictions'>('volume')

  const fetchTrendsData = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/analytics/trends?timeRange=${timeRange}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch trends data: ${response.statusText}`)
      }

      const trendsData = await response.json()
      setData(trendsData)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch trends data')
      console.error('Error fetching trends data:', err)
    } finally {
      setLoading(false)
    }
  }, [timeRange])

  useEffect(() => {
    fetchTrendsData()
  }, [fetchTrendsData, refreshTrigger])

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

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'increasing':
      case 'improving': return 'text-green-600'
      case 'decreasing':
      case 'declining': return 'text-red-600'
      case 'stable': return 'text-blue-600'
      default: return 'text-gray-600'
    }
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing':
      case 'improving': return '↗'
      case 'decreasing':
      case 'declining': return '↘'
      case 'stable': return '→'
      default: return '–'
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'bg-red-100 text-red-800'
      case 'medium': return 'bg-yellow-100 text-yellow-800'
      case 'low': return 'bg-blue-100 text-blue-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  // Simple trend chart component
  const TrendChart = ({ 
    data, 
    label, 
    color = 'blue',
    height = 80 
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
          <span>Range: {min.toFixed(1)} - {max.toFixed(1)}</span>
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
          <Button onClick={fetchTrendsData} variant="outline">
            Try Again
          </Button>
        </div>
      </Card>
    )
  }

  if (!data) {
    return null
  }

  return (
    <div className="space-y-6">
      {/* Navigation */}
      <Card className="p-4">
        <div className="flex space-x-1 bg-muted p-1 rounded-lg">
          <Button
            variant={activeView === 'volume' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveView('volume')}
          >
            Volume Trends
          </Button>
          <Button
            variant={activeView === 'quality' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveView('quality')}
          >
            Quality Trends
          </Button>
          <Button
            variant={activeView === 'performance' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveView('performance')}
          >
            Performance
          </Button>
          <Button
            variant={activeView === 'predictions' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveView('predictions')}
          >
            Predictions
          </Button>
        </div>
      </Card>

      {/* Content */}
      {activeView === 'volume' && (
        <div className="space-y-6">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Processing Volume Trends</h3>
            <TrendChart 
              data={data.processing_volume.values} 
              label="Videos Processed" 
              color="blue"
              height={120}
            />
            <div className="mt-4 grid grid-cols-2 gap-4 text-center">
              <div>
                <div className={`text-2xl font-bold ${getTrendColor(data.processing_volume.trend)}`}>
                  {getTrendIcon(data.processing_volume.trend)} {data.processing_volume.trend}
                </div>
                <div className="text-sm text-muted-foreground">Volume Trend</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-purple-600">
                  {formatPercentage(data.processing_volume.growth_rate)}
                </div>
                <div className="text-sm text-muted-foreground">Growth Rate</div>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Model Adoption Trends</h3>
            <div className="space-y-4">
              <TrendChart 
                data={data.model_adoption.single_model} 
                label="Single Model Usage" 
                color="blue"
                height={80}
              />
              <TrendChart 
                data={data.model_adoption.multi_model} 
                label="Multi-Model Usage" 
                color="purple"
                height={80}
              />
            </div>
            <div className="mt-4 text-center">
              <div className="text-2xl font-bold text-purple-600">
                {formatPercentage(data.model_adoption.multi_model_adoption_rate)}
              </div>
              <div className="text-sm text-muted-foreground">Multi-Model Adoption Rate</div>
            </div>
          </Card>
        </div>
      )}

      {activeView === 'quality' && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Quality Trends</h3>
          <TrendChart 
            data={data.success_rates.values} 
            label="Success Rate (%)" 
            color="green"
            height={120}
          />
          <div className="mt-4 grid grid-cols-2 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-green-600">
                {formatPercentage(data.success_rates.avg_success_rate)}
              </div>
              <div className="text-sm text-muted-foreground">Average Success Rate</div>
            </div>
            <div>
              <div className={`text-2xl font-bold ${getTrendColor(data.success_rates.trend)}`}>
                {getTrendIcon(data.success_rates.trend)} {data.success_rates.trend}
              </div>
              <div className="text-sm text-muted-foreground">Quality Trend</div>
            </div>
          </div>
        </Card>
      )}

      {activeView === 'performance' && (
        <div className="space-y-6">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Processing Time Trends</h3>
            <div className="space-y-4">
              <TrendChart 
                data={data.processing_times.avg_times} 
                label="Average Processing Time (s)" 
                color="blue"
                height={80}
              />
              <TrendChart 
                data={data.processing_times.p95_times} 
                label="95th Percentile Time (s)" 
                color="red"
                height={80}
              />
            </div>
            <div className="mt-4 text-center">
              <div className={`text-2xl font-bold ${getTrendColor(data.processing_times.trend)}`}>
                {getTrendIcon(data.processing_times.trend)} {data.processing_times.trend}
              </div>
              <div className="text-sm text-muted-foreground">Performance Trend</div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Cost Efficiency Trends</h3>
            <div className="space-y-4">
              <TrendChart 
                data={data.cost_trends.daily_costs} 
                label="Daily Costs ($)" 
                color="orange"
                height={80}
              />
              <TrendChart 
                data={data.cost_trends.cost_per_video} 
                label="Cost per Video ($)" 
                color="purple"
                height={80}
              />
            </div>
            <div className="mt-4 text-center">
              <div className={`text-2xl font-bold ${getTrendColor(data.cost_trends.efficiency_trend)}`}>
                {getTrendIcon(data.cost_trends.efficiency_trend)} {data.cost_trends.efficiency_trend}
              </div>
              <div className="text-sm text-muted-foreground">Efficiency Trend</div>
            </div>
          </Card>
        </div>
      )}

      {activeView === 'predictions' && (
        <div className="space-y-6">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Next Week Predictions</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {formatNumber(data.predictions.next_week_volume)}
                </div>
                <div className="text-sm text-muted-foreground">Predicted Volume</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {formatCurrency(data.predictions.next_week_cost)}
                </div>
                <div className="text-sm text-muted-foreground">Predicted Cost</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {formatPercentage(data.predictions.capacity_utilization)}
                </div>
                <div className="text-sm text-muted-foreground">Capacity Utilization</div>
              </div>
            </div>
          </Card>

          {data.predictions.bottlenecks.length > 0 && (
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Potential Bottlenecks</h3>
              <div className="space-y-3">
                {data.predictions.bottlenecks.map((bottleneck, index) => (
                  <div key={index} className="flex items-start space-x-3 p-3 rounded-md bg-muted">
                    <Badge className={getSeverityColor(bottleneck.severity)}>
                      {bottleneck.severity}
                    </Badge>
                    <div className="flex-1">
                      <div className="font-medium">{bottleneck.component}</div>
                      <div className="text-sm text-muted-foreground mt-1">
                        {bottleneck.description}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}