'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { QnAChat } from '@/components/qna/qna-chat'
import { ConversationHistory } from '@/components/qna/conversation-history'
import { QnASearch } from '@/components/qna/qna-search'
import { VideoTagging } from '@/components/qna/video-tagging'
import { QnAAnalytics } from '@/components/qna/qna-analytics'
import { useWebSocket } from '@/hooks/use-websocket'

interface QnAStats {
  totalQuestions: number
  totalConversations: number
  averageResponseTime: number
  topChannels: Array<{ name: string; count: number }>
}

export default function QnAPage() {
  const [stats, setStats] = useState<QnAStats | null>(null)
  const [activeTab, setActiveTab] = useState('chat')
  const { isConnected, lastMessage } = useWebSocket('/ws/qna')

  useEffect(() => {
    fetchStats()
  }, [])

  useEffect(() => {
    if (lastMessage?.type === 'qna_stats_update') {
      setStats(lastMessage.data)
    }
  }, [lastMessage])

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/qna/stats')
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (error) {
      console.error('Failed to fetch QnA stats:', error)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Q&A System</h1>
          <p className="text-muted-foreground">
            Ask questions about processed videos and explore conversations
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-muted-foreground">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {stats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Questions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.totalQuestions}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Conversations</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.totalConversations}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.averageResponseTime}s</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Channels</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.topChannels.length}</div>
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="chat">Chat Interface</TabsTrigger>
          <TabsTrigger value="history">Conversation History</TabsTrigger>
          <TabsTrigger value="search">Search Q&A</TabsTrigger>
          <TabsTrigger value="tagging">Video Tagging</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="chat" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Ask Questions</CardTitle>
              <CardDescription>
                Ask questions about any processed video content. The system will search through summaries and subtitles to provide relevant answers.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <QnAChat />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Conversation History</CardTitle>
              <CardDescription>
                Browse and manage your Q&A conversation sessions across all channels.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ConversationHistory />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="search" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Search Q&A Exchanges</CardTitle>
              <CardDescription>
                Search through all previous questions and answers using semantic search.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <QnASearch />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tagging" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Video Tagging System</CardTitle>
              <CardDescription>
                Tag specific videos for targeted questioning and better context retrieval.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <VideoTagging />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Q&A Analytics</CardTitle>
              <CardDescription>
                Analyze question patterns, response quality, and system performance.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <QnAAnalytics />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}