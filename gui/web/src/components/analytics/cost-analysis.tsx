'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface CostData {
  overview: {
    total_cost_period: number
    total_cost_today: number
    avg_cost_per_video: number
    projected_monthly_cost: number
    cost_trend: 'increasing' | 'decreasing' | 'stable'
  }
  by_model: Array<{
    model: string
    cost: number
    usage_count: number
    avg_cost_per_use: number
    percentage_of_total: number
  }>
  by_channel: Array<{
    channel_id: string
    channel_name: string
    cost: number
    video_count: number
    avg_cost_per_video: number
    cost_efficiency: number
  }>
  daily_breakdown: Array<{
    date: string
    total_cost: number
    video_count: number
    avg_cost_per_video: number
    model_breakdown: {
      [model: string]: {
        cost: number
        count: number
      }
    }
  }>
  cost_optimization: {
    potential_savings: number
    recommendations: Array<{
      type: 'model_switch' | 'threshold_adjustment' | 'batch_processing'
      description: string
      estimated_savings: number
      impact: 'low' | 'medium' | 'high'
    }>
  }
}

interface CostAnalysisProps {
  timeRange: string
  refreshTrigger: number
  compact: boolean
}

export function CostAnalysis({ timeRange, refreshTrigger, compact }: CostAnalysisProps) {
  const [data, setData] = useState<CostData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeView, setActiveView] = useState<'overview' | 'models' | 'channels' | 'optimization'>('overview')

  const fetchCostData = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/analytics/costs?timeRange=${timeRange}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch cost data: ${response.statusText}`)
      }

      const costData = await response.json()
      setData(costData)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch cost data')
      console.error('Error fetching cost data:', err)
    } finally {
      setLoading(false)
    }
  }, [timeRange])

  useEffect(() => {
    fetchCostData()
  }, [fetchCostData, refreshTrigger])

  const formatCurrency = (amount: number): string => {
    return `$${amount.toFixed(2)}`
  }

  const formatPercentage = (rate: number): string => {
    return `${(rate * 100).toFixed(1)}%`
  }

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'increasing': return 'text-red-600'
      case 'decreasing': return 'text-green-600'
      case 'stable': return 'text-blue-600'
      default: return 'text-gray-600'
    }
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing': return '↗'
      case 'decreasing': return '↘'
      case 'stable': return '→'
      default: return '–'
    }
  }

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high': return 'bg-green-100 text-green-800'
      case 'medium': return 'bg-yellow-100 text-yellow-800'
      case 'low': return 'bg-blue-100 text-blue-800'
      default: return 'bg-gray-100 text-gray-800'
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
          <Button onClick={fetchCostData} variant="outline">
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
        <h3 className="text-lg font-semibold mb-4">Cost Overview</h3>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">
              {formatCurrency(data.overview.total_cost_period)}
            </div>
            <div className="text-sm text-muted-foreground">Total Cost</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {formatCurrency(data.overview.avg_cost_per_video)}
            </div>
            <div className="text-sm text-muted-foreground">Avg per Video</div>
          </div>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span>Trend:</span>
          <span className={`font-medium ${getTrendColor(data.overview.cost_trend)}`}>
            {getTrendIcon(data.overview.cost_trend)} {data.overview.cost_trend}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm mt-2">
          <span>Projected Monthly:</span>
          <span className="font-medium">{formatCurrency(data.overview.projected_monthly_cost)}</span>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Navigation */}
      <Card className="p-4">
        <div className="flex space-x-1 bg-muted p-1 rounded-lg">
          <Button
            variant={activeView === 'overview' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveView('overview')}
          >
            Overview
          </Button>
          <Button
            variant={activeView === 'models' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveView('models')}
          >
            By Model
          </Button>
          <Button
            variant={activeView === 'channels' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveView('channels')}
          >
            By Channel
          </Button>
          <Button
            variant={activeView === 'optimization' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveView('optimization')}
          >
            Optimization
          </Button>
        </div>
      </Card>

      {/* Content */}
      {activeView === 'overview' && (
        <div className="space-y-6">
          {/* Cost Overview */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Cost Overview</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {formatCurrency(data.overview.total_cost_period)}
                </div>
                <div className="text-sm text-muted-foreground">Total Cost ({timeRange})</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {formatCurrency(data.overview.total_cost_today)}
                </div>
                <div className="text-sm text-muted-foreground">Cost Today</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {formatCurrency(data.overview.avg_cost_per_video)}
                </div>
                <div className="text-sm text-muted-foreground">Avg per Video</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {formatCurrency(data.overview.projected_monthly_cost)}
                </div>
                <div className="text-sm text-muted-foreground">Projected Monthly</div>
              </div>
            </div>
            <div className="mt-4 flex items-center justify-center">
              <div className="flex items-center space-x-2">
                <span className="text-sm">Cost Trend:</span>
                <Badge className={getTrendColor(data.overview.cost_trend)}>
                  {getTrendIcon(data.overview.cost_trend)} {data.overview.cost_trend}
                </Badge>
              </div>
            </div>
          </Card>

          {/* Daily Breakdown */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Daily Cost Breakdown</h3>
            <div className="space-y-3">
              {data.daily_breakdown.map((day, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-muted rounded">
                  <div>
                    <div className="font-medium">{day.date}</div>
                    <div className="text-sm text-muted-foreground">
                      {day.video_count} videos processed
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold">{formatCurrency(day.total_cost)}</div>
                    <div className="text-sm text-muted-foreground">
                      {formatCurrency(day.avg_cost_per_video)} avg
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {activeView === 'models' && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Cost by Model</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2">Model</th>
                  <th className="text-right py-2">Total Cost</th>
                  <th className="text-right py-2">Usage Count</th>
                  <th className="text-right py-2">Avg Cost/Use</th>
                  <th className="text-right py-2">% of Total</th>
                </tr>
              </thead>
              <tbody>
                {data.by_model.map((model, index) => (
                  <tr key={index} className="border-b">
                    <td className="py-3 font-medium">{model.model}</td>
                    <td className="text-right py-3 font-bold">
                      {formatCurrency(model.cost)}
                    </td>
                    <td className="text-right py-3">{model.usage_count}</td>
                    <td className="text-right py-3">
                      {formatCurrency(model.avg_cost_per_use)}
                    </td>
                    <td className="text-right py-3">
                      <Badge variant="outline">
                        {formatPercentage(model.percentage_of_total)}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {activeView === 'channels' && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Cost by Channel</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2">Channel</th>
                  <th className="text-right py-2">Total Cost</th>
                  <th className="text-right py-2">Videos</th>
                  <th className="text-right py-2">Avg Cost/Video</th>
                  <th className="text-right py-2">Efficiency</th>
                </tr>
              </thead>
              <tbody>
                {data.by_channel.map((channel, index) => (
                  <tr key={index} className="border-b">
                    <td className="py-3">
                      <div>
                        <div className="font-medium">{channel.channel_name}</div>
                        <div className="text-xs text-muted-foreground">
                          {channel.channel_id.substring(0, 12)}...
                        </div>
                      </div>
                    </td>
                    <td className="text-right py-3 font-bold">
                      {formatCurrency(channel.cost)}
                    </td>
                    <td className="text-right py-3">{channel.video_count}</td>
                    <td className="text-right py-3">
                      {formatCurrency(channel.avg_cost_per_video)}
                    </td>
                    <td className="text-right py-3">
                      <Badge className={
                        channel.cost_efficiency >= 0.8 ? 'bg-green-100 text-green-800' :
                        channel.cost_efficiency >= 0.6 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }>
                        {formatPercentage(channel.cost_efficiency)}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {activeView === 'optimization' && (
        <div className="space-y-6">
          {/* Potential Savings */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Cost Optimization</h3>
            <div className="text-center mb-6">
              <div className="text-3xl font-bold text-green-600">
                {formatCurrency(data.cost_optimization.potential_savings)}
              </div>
              <div className="text-sm text-muted-foreground">Potential Monthly Savings</div>
            </div>
          </Card>

          {/* Recommendations */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Optimization Recommendations</h3>
            <div className="space-y-4">
              {data.cost_optimization.recommendations.map((rec, index) => (
                <div key={index} className="p-4 border rounded-lg">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="font-medium">{rec.description}</div>
                      <div className="text-sm text-muted-foreground mt-1">
                        Estimated savings: {formatCurrency(rec.estimated_savings)}/month
                      </div>
                    </div>
                    <Badge className={getImpactColor(rec.impact)}>
                      {rec.impact} impact
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}