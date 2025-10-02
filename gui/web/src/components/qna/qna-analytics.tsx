'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { MessageCircle, Clock, TrendingUp, Users, ThumbsUp, ThumbsDown, Target, Zap } from 'lucide-react'

interface QnAAnalytics {
  overview: {
    totalQuestions: number
    totalConversations: number
    averageResponseTime: number
    averageConfidenceScore: number
    positiveRating: number
    negativeRating: number
    totalRatings: number
  }
  trends: {
    daily: Array<{
      date: string
      questions: number
      conversations: number
      avgResponseTime: number
      avgConfidence: number
    }>
    hourly: Array<{
      hour: number
      questions: number
      avgResponseTime: number
    }>
  }
  channels: Array<{
    name: string
    displayName: string
    questions: number
    conversations: number
    avgConfidence: number
    avgResponseTime: number
    positiveRatings: number
    totalRatings: number
  }>
  topics: Array<{
    topic: string
    count: number
    avgConfidence: number
    category: string
  }>
  performance: {
    confidenceDistribution: Array<{
      range: string
      count: number
      percentage: number
    }>
    responseTimeDistribution: Array<{
      range: string
      count: number
      percentage: number
    }>
  }
  userEngagement: {
    repeatUsers: number
    avgQuestionsPerUser: number
    mostActiveHours: Array<{
      hour: number
      activity: number
    }>
  }
}

export function QnAAnalytics() {
  const [analytics, setAnalytics] = useState<QnAAnalytics | null>(null)
  const [timeRange, setTimeRange] = useState('7d')
  const [selectedChannel, setSelectedChannel] = useState('all')
  const [isLoading, setIsLoading] = useState(true)
  const [channels, setChannels] = useState<Array<{ id: string; name: string; displayName: string }>>([])

  useEffect(() => {
    fetchChannels()
    fetchAnalytics()
  }, [])

  useEffect(() => {
    fetchAnalytics()
  }, [timeRange, selectedChannel])

  const fetchChannels = async () => {
    try {
      const response = await fetch('/api/channels')
      if (response.ok) {
        const data = await response.json()
        setChannels([
          { id: 'all', name: 'all', displayName: 'All Channels' },
          ...data.map((ch: any) => ({
            id: ch.channel_id,
            name: ch.channel_name,
            displayName: ch.display_name || ch.channel_name
          }))
        ])
      }
    } catch (error) {
      console.error('Failed to fetch channels:', error)
    }
  }

  const fetchAnalytics = async () => {
    try {
      setIsLoading(true)
      const params = new URLSearchParams({
        time_range: timeRange,
        ...(selectedChannel !== 'all' && { channel: selectedChannel })
      })

      const response = await fetch(`/api/qna/analytics?${params}`)
      if (response.ok) {
        const data = await response.json()
        setAnalytics(data)
      }
    } catch (error) {
      console.error('Failed to fetch analytics:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const formatNumber = (num: number) => {
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'k'
    }
    return num.toString()
  }

  const formatDuration = (seconds: number) => {
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`
    }
    return `${(seconds / 60).toFixed(1)}m`
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600'
    if (confidence >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D']

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!analytics) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground">Failed to load analytics data</p>
      </div>
    )
  }

  const satisfactionRate = analytics.overview.totalRatings > 0 
    ? (analytics.overview.positiveRating / analytics.overview.totalRatings) * 100 
    : 0

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex items-center space-x-4">
        <Select value={timeRange} onValueChange={setTimeRange}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1d">Last Day</SelectItem>
            <SelectItem value="7d">Last Week</SelectItem>
            <SelectItem value="30d">Last Month</SelectItem>
            <SelectItem value="90d">Last 3 Months</SelectItem>
          </SelectContent>
        </Select>
        <Select value={selectedChannel} onValueChange={setSelectedChannel}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {channels.map((channel) => (
              <SelectItem key={channel.id} value={channel.id}>
                {channel.displayName}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Overview Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <MessageCircle className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-medium">Total Questions</span>
            </div>
            <div className="text-2xl font-bold mt-1">{formatNumber(analytics.overview.totalQuestions)}</div>
            <div className="text-xs text-muted-foreground mt-1">
              {analytics.overview.totalConversations} conversations
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Clock className="h-4 w-4 text-green-600" />
              <span className="text-sm font-medium">Avg Response Time</span>
            </div>
            <div className="text-2xl font-bold mt-1">
              {formatDuration(analytics.overview.averageResponseTime)}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              System performance
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Target className="h-4 w-4 text-purple-600" />
              <span className="text-sm font-medium">Avg Confidence</span>
            </div>
            <div className={`text-2xl font-bold mt-1 ${getConfidenceColor(analytics.overview.averageConfidenceScore)}`}>
              {Math.round(analytics.overview.averageConfidenceScore * 100)}%
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Answer quality
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <ThumbsUp className="h-4 w-4 text-orange-600" />
              <span className="text-sm font-medium">Satisfaction</span>
            </div>
            <div className="text-2xl font-bold mt-1">{Math.round(satisfactionRate)}%</div>
            <div className="text-xs text-muted-foreground mt-1">
              {analytics.overview.totalRatings} ratings
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Trends Charts */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Question Volume Trends</CardTitle>
            <CardDescription>Daily questions and conversations over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={analytics.trends.daily}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="questions" stackId="1" stroke="#8884d8" fill="#8884d8" />
                <Area type="monotone" dataKey="conversations" stackId="1" stroke="#82ca9d" fill="#82ca9d" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Response Time Trends</CardTitle>
            <CardDescription>Average response time and confidence over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={analytics.trends.daily}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Legend />
                <Line yAxisId="left" type="monotone" dataKey="avgResponseTime" stroke="#8884d8" name="Response Time (s)" />
                <Line yAxisId="right" type="monotone" dataKey="avgConfidence" stroke="#82ca9d" name="Confidence" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Channel Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Channel Performance</CardTitle>
          <CardDescription>Q&A metrics by channel</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {analytics.channels.map((channel) => (
              <div key={channel.name} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span className="font-medium">{channel.displayName}</span>
                    <Badge variant="secondary">{channel.questions} questions</Badge>
                    <Badge variant="outline">{channel.conversations} conversations</Badge>
                  </div>
                  <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                    <span className={getConfidenceColor(channel.avgConfidence)}>
                      {Math.round(channel.avgConfidence * 100)}% confidence
                    </span>
                    <span>{formatDuration(channel.avgResponseTime)}</span>
                    <span>
                      {channel.totalRatings > 0 
                        ? Math.round((channel.positiveRatings / channel.totalRatings) * 100)
                        : 0}% satisfaction
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Questions</div>
                    <Progress value={(channel.questions / Math.max(...analytics.channels.map(c => c.questions))) * 100} className="h-2" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Confidence</div>
                    <Progress value={channel.avgConfidence * 100} className="h-2" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Satisfaction</div>
                    <Progress 
                      value={channel.totalRatings > 0 ? (channel.positiveRatings / channel.totalRatings) * 100 : 0} 
                      className="h-2" 
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Topic Analysis and Performance Distribution */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Popular Topics</CardTitle>
            <CardDescription>Most frequently asked about topics</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={analytics.topics.slice(0, 10)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="topic" angle={-45} textAnchor="end" height={80} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Confidence Distribution</CardTitle>
            <CardDescription>Distribution of answer confidence scores</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={analytics.performance.confidenceDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ range, percentage }) => `${range}: ${percentage}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="count"
                >
                  {analytics.performance.confidenceDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* User Engagement */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>User Engagement</CardTitle>
            <CardDescription>User activity patterns</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{analytics.userEngagement.repeatUsers}</div>
                <div className="text-sm text-muted-foreground">Repeat Users</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {analytics.userEngagement.avgQuestionsPerUser.toFixed(1)}
                </div>
                <div className="text-sm text-muted-foreground">Avg Questions/User</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Activity by Hour</CardTitle>
            <CardDescription>Most active hours for Q&A</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={analytics.userEngagement.mostActiveHours}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="activity" fill="#82ca9d" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Response Time Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Response Time Analysis</CardTitle>
          <CardDescription>Distribution of system response times</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={analytics.performance.responseTimeDistribution}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="range" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" fill="#FFBB28" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-3">
              <h4 className="font-medium">Performance Insights</h4>
              {analytics.performance.responseTimeDistribution.map((item, index) => (
                <div key={index} className="flex items-center justify-between">
                  <span className="text-sm">{item.range}</span>
                  <div className="flex items-center space-x-2">
                    <Progress value={item.percentage} className="w-20 h-2" />
                    <span className="text-sm text-muted-foreground">{item.percentage}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}