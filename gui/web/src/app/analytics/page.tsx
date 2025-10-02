'use client'

import { useState, useEffect, useCallback } from 'react'
import { SystemMetrics } from '@/components/analytics/system-metrics'
import { ChannelAnalytics } from '@/components/analytics/channel-analytics'
import { PerformanceCharts } from '@/components/analytics/performance-charts'
import { CostAnalysis } from '@/components/analytics/cost-analysis'
import { ProcessingTrends } from '@/components/analytics/processing-trends'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useWebSocket } from '@/hooks/use-websocket'

export default function AnalyticsPage() {
  const [activeView, setActiveView] = useState<'overview' | 'channels' | 'performance' | 'costs' | 'trends'>('overview')
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [timeRange, setTimeRange] = useState<'1h' | '24h' | '7d' | '30d'>('24h')

  // WebSocket connection for real-time updates
  const { isConnected, lastMessage } = useWebSocket('/ws/analytics')

  // Handle real-time analytics updates
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'analytics_update') {
      // Trigger refresh when analytics data changes
      setRefreshTrigger(prev => prev + 1)
    }
  }, [lastMessage])

  const handleRefresh = useCallback(() => {
    setRefreshTrigger(prev => prev + 1)
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics Dashboard</h1>
          <p className="text-muted-foreground">
            System performance metrics, insights, and trends
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-muted-foreground">
            {isConnected ? 'Live Data' : 'Offline'}
          </span>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as any)}
            className="px-3 py-1 border border-input bg-background rounded-md text-sm"
          >
            <option value="1h">Last Hour</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
          <Button onClick={handleRefresh} variant="outline" size="sm">
            Refresh
          </Button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex space-x-1 bg-muted p-1 rounded-lg">
        <Button
          variant={activeView === 'overview' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveView('overview')}
        >
          Overview
        </Button>
        <Button
          variant={activeView === 'channels' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveView('channels')}
        >
          Channels
        </Button>
        <Button
          variant={activeView === 'performance' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveView('performance')}
        >
          Performance
        </Button>
        <Button
          variant={activeView === 'costs' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveView('costs')}
        >
          Costs
        </Button>
        <Button
          variant={activeView === 'trends' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveView('trends')}
        >
          Trends
        </Button>
      </div>

      {/* Content based on active view */}
      <div className="space-y-6">
        {activeView === 'overview' && (
          <>
            <SystemMetrics 
              timeRange={timeRange}
              refreshTrigger={refreshTrigger}
            />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <PerformanceCharts 
                timeRange={timeRange}
                refreshTrigger={refreshTrigger}
                compact={true}
              />
              <CostAnalysis 
                timeRange={timeRange}
                refreshTrigger={refreshTrigger}
                compact={true}
              />
            </div>
          </>
        )}
        
        {activeView === 'channels' && (
          <ChannelAnalytics 
            timeRange={timeRange}
            refreshTrigger={refreshTrigger}
          />
        )}
        
        {activeView === 'performance' && (
          <PerformanceCharts 
            timeRange={timeRange}
            refreshTrigger={refreshTrigger}
            compact={false}
          />
        )}
        
        {activeView === 'costs' && (
          <CostAnalysis 
            timeRange={timeRange}
            refreshTrigger={refreshTrigger}
            compact={false}
          />
        )}
        
        {activeView === 'trends' && (
          <ProcessingTrends 
            timeRange={timeRange}
            refreshTrigger={refreshTrigger}
          />
        )}
      </div>

      {/* Quick Stats Footer */}
      <Card className="p-4">
        <div className="text-center text-sm text-muted-foreground">
          Analytics data updates in real-time • Last refresh: {new Date().toLocaleTimeString()}
        </div>
      </Card>
    </div>
  )
}