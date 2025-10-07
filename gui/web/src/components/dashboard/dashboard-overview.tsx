'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { 
  MessageSquare, 
  Settings, 
  Database, 
  BarChart3, 
  HelpCircle,
  Activity,
  Users,
  Video,
  DollarSign
} from 'lucide-react'
import Link from 'next/link'

const quickActions = [
  {
    title: 'View Messages',
    description: 'Browse Telegram message history',
    icon: MessageSquare,
    href: '/messages',
    color: 'text-blue-600'
  },
  {
    title: 'Manage Channels',
    description: 'Configure YouTube channels',
    icon: Settings,
    href: '/channels',
    color: 'text-green-600'
  },
  {
    title: 'Browse Database',
    description: 'Explore video records',
    icon: Database,
    href: '/database',
    color: 'text-purple-600'
  },
  {
    title: 'View Analytics',
    description: 'System performance metrics',
    icon: BarChart3,
    href: '/analytics',
    color: 'text-orange-600'
  },
  {
    title: 'Q&A System',
    description: 'Ask questions about videos',
    icon: HelpCircle,
    href: '/qna',
    color: 'text-indigo-600'
  }
]

interface DashboardStats {
  total_channels: number
  total_videos: number
  total_cost: number
  processed_today: number
}

export function DashboardOverview() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('/api/analytics/database/statistics', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
            'Content-Type': 'application/json'
          }
        })

        if (response.ok) {
          const data = await response.json()
          setStats(data.overview)
        }
      } catch (error) {
        console.error('Failed to fetch dashboard stats:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])

  const displayStats = [
    {
      title: 'Active Channels',
      value: loading ? '...' : (stats?.total_channels || 0).toString(),
      icon: Users,
      description: 'YouTube channels monitored'
    },
    {
      title: 'Videos Processed',
      value: loading ? '...' : (stats?.total_videos || 0).toString(),
      icon: Video,
      description: 'Total videos summarized'
    },
    {
      title: 'Processed Today',
      value: loading ? '...' : (stats?.processed_today || 0).toString(),
      icon: Activity,
      description: 'Videos processed today'
    },
    {
      title: 'Total Cost',
      value: loading ? '...' : `$${(stats?.total_cost || 0).toFixed(2)}`,
      icon: DollarSign,
      description: 'Total processing cost'
    }
  ]

  return (
    <div className="space-y-6">
      {/* Stats Overview */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {displayStats.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {stat.title}
                </CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <p className="text-xs text-muted-foreground">
                  {stat.description}
                </p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight mb-4">Quick Actions</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {quickActions.map((action) => {
            const Icon = action.icon
            return (
              <Card key={action.title} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-center space-x-2">
                    <Icon className={`h-5 w-5 ${action.color}`} />
                    <CardTitle className="text-lg">{action.title}</CardTitle>
                  </div>
                  <CardDescription>{action.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <Link href={action.href}>
                    <Button className="w-full">
                      Open {action.title}
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>
            Latest system events and updates
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center space-x-4">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <div className="flex-1">
                <p className="text-sm font-medium">New video processed</p>
                <p className="text-xs text-muted-foreground">Two Minute Papers - 2 minutes ago</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <div className="flex-1">
                <p className="text-sm font-medium">Message sent to Telegram</p>
                <p className="text-xs text-muted-foreground">Channel: AI Research - 5 minutes ago</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
              <div className="flex-1">
                <p className="text-sm font-medium">Q&A session started</p>
                <p className="text-xs text-muted-foreground">User asked about neural networks - 10 minutes ago</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}