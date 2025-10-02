'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Search, Filter, Calendar, MessageCircle, Video, ExternalLink, Copy, ThumbsUp, ThumbsDown } from 'lucide-react'

interface SearchResult {
  id: string
  question: string
  answer: string
  timestamp: string
  channelContext?: string
  confidenceScore: number
  contextVideos: Array<{
    id: string
    title: string
    url: string
    relevanceScore: number
  }>
  conversationId: string
  relevanceScore: number
  matchType: 'question' | 'answer' | 'context'
}

interface SearchFilters {
  channel: string
  dateRange: string
  minConfidence: number
  matchType: string
}

export function QnASearch() {
  const [searchQuery, setSearchQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [filters, setFilters] = useState<SearchFilters>({
    channel: 'all',
    dateRange: 'all',
    minConfidence: 0,
    matchType: 'all'
  })
  const [channels, setChannels] = useState<Array<{ id: string; name: string; displayName: string }>>([])
  const [totalResults, setTotalResults] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [resultsPerPage] = useState(10)

  useEffect(() => {
    fetchChannels()
  }, [])

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

  const handleSearch = async (page: number = 1) => {
    if (!searchQuery.trim()) return

    setIsLoading(true)
    setCurrentPage(page)

    try {
      const params = new URLSearchParams({
        query: searchQuery,
        page: page.toString(),
        limit: resultsPerPage.toString(),
        ...(filters.channel !== 'all' && { channel_context: filters.channel }),
        ...(filters.dateRange !== 'all' && { date_range: filters.dateRange }),
        ...(filters.minConfidence > 0 && { min_confidence: filters.minConfidence.toString() }),
        ...(filters.matchType !== 'all' && { match_type: filters.matchType })
      })

      const response = await fetch(`/api/qna/search?${params}`)
      if (response.ok) {
        const data = await response.json()
        setResults(data.results || [])
        setTotalResults(data.total || 0)
      }
    } catch (error) {
      console.error('Failed to search QnA:', error)
      setResults([])
      setTotalResults(0)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    handleSearch(1)
  }

  const handleFilterChange = (key: keyof SearchFilters, value: string | number) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const handleFeedback = async (resultId: string, isPositive: boolean) => {
    try {
      await fetch(`/api/qna/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          exchange_id: resultId,
          is_positive: isPositive
        }),
      })
    } catch (error) {
      console.error('Failed to submit feedback:', error)
    }
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getChannelDisplayName = (channelId?: string) => {
    if (!channelId) return 'All Channels'
    const channel = channels.find(ch => ch.id === channelId)
    return channel?.displayName || channelId
  }

  const getMatchTypeColor = (matchType: string) => {
    switch (matchType) {
      case 'question': return 'bg-blue-100 text-blue-800'
      case 'answer': return 'bg-green-100 text-green-800'
      case 'context': return 'bg-purple-100 text-purple-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const totalPages = Math.ceil(totalResults / resultsPerPage)

  return (
    <div className="space-y-6">
      {/* Search Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Search className="h-5 w-5" />
            <span>Semantic Search</span>
          </CardTitle>
          <CardDescription>
            Search through all Q&A exchanges using natural language queries
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={handleSubmit} className="flex space-x-2">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search questions, answers, or video content..."
              className="flex-1"
            />
            <Button type="submit" disabled={isLoading || !searchQuery.trim()}>
              {isLoading ? 'Searching...' : 'Search'}
            </Button>
          </form>

          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Select value={filters.channel} onValueChange={(value) => handleFilterChange('channel', value)}>
              <SelectTrigger>
                <SelectValue placeholder="Channel" />
              </SelectTrigger>
              <SelectContent>
                {channels.map((channel) => (
                  <SelectItem key={channel.id} value={channel.id}>
                    {channel.displayName}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={filters.dateRange} onValueChange={(value) => handleFilterChange('dateRange', value)}>
              <SelectTrigger>
                <SelectValue placeholder="Date Range" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Time</SelectItem>
                <SelectItem value="today">Today</SelectItem>
                <SelectItem value="week">This Week</SelectItem>
                <SelectItem value="month">This Month</SelectItem>
                <SelectItem value="year">This Year</SelectItem>
              </SelectContent>
            </Select>

            <Select value={filters.matchType} onValueChange={(value) => handleFilterChange('matchType', value)}>
              <SelectTrigger>
                <SelectValue placeholder="Match Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Matches</SelectItem>
                <SelectItem value="question">Questions</SelectItem>
                <SelectItem value="answer">Answers</SelectItem>
                <SelectItem value="context">Video Context</SelectItem>
              </SelectContent>
            </Select>

            <Select 
              value={filters.minConfidence.toString()} 
              onValueChange={(value) => handleFilterChange('minConfidence', parseFloat(value))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Min Confidence" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="0">Any Confidence</SelectItem>
                <SelectItem value="0.5">50%+</SelectItem>
                <SelectItem value="0.7">70%+</SelectItem>
                <SelectItem value="0.8">80%+</SelectItem>
                <SelectItem value="0.9">90%+</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {searchQuery && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Search Results</CardTitle>
                <CardDescription>
                  {totalResults} result{totalResults !== 1 ? 's' : ''} for "{searchQuery}"
                </CardDescription>
              </div>
              {totalResults > 0 && (
                <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                  <span>Page {currentPage} of {totalPages}</span>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : results.length === 0 ? (
              <div className="text-center py-8">
                <MessageCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p className="text-muted-foreground">No results found</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Try different keywords or adjust your filters
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {results.map((result) => (
                  <Card key={result.id} className="border-l-4 border-l-primary/20">
                    <CardContent className="p-4">
                      <div className="space-y-3">
                        {/* Header */}
                        <div className="flex items-start justify-between">
                          <div className="flex items-center space-x-2">
                            <Badge className={getMatchTypeColor(result.matchType)}>
                              {result.matchType}
                            </Badge>
                            <Badge variant="outline">
                              {Math.round(result.relevanceScore * 100)}% match
                            </Badge>
                            {result.channelContext && (
                              <Badge variant="secondary">
                                {getChannelDisplayName(result.channelContext)}
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center space-x-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0"
                              onClick={() => copyToClipboard(`Q: ${result.question}\nA: ${result.answer}`)}
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0"
                              onClick={() => handleFeedback(result.id, true)}
                            >
                              <ThumbsUp className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0"
                              onClick={() => handleFeedback(result.id, false)}
                            >
                              <ThumbsDown className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>

                        {/* Question */}
                        <div className="bg-muted/50 p-3 rounded-lg">
                          <p className="font-medium text-sm">Q: {result.question}</p>
                        </div>

                        {/* Answer */}
                        <div className="bg-background border p-3 rounded-lg">
                          <p className="text-sm whitespace-pre-wrap">{result.answer}</p>
                        </div>

                        {/* Context Videos */}
                        {result.contextVideos.length > 0 && (
                          <div className="space-y-2">
                            <p className="text-xs font-medium text-muted-foreground">Related Videos:</p>
                            <div className="grid gap-2">
                              {result.contextVideos.map((video) => (
                                <div key={video.id} className="flex items-center justify-between p-2 bg-muted/30 rounded text-xs">
                                  <div className="flex items-center space-x-2">
                                    <Video className="h-3 w-3" />
                                    <span className="truncate max-w-64">{video.title}</span>
                                    <Badge variant="outline" className="text-xs">
                                      {Math.round(video.relevanceScore * 100)}%
                                    </Badge>
                                  </div>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-6 w-6 p-0"
                                    onClick={() => window.open(video.url, '_blank')}
                                  >
                                    <ExternalLink className="h-3 w-3" />
                                  </Button>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Metadata */}
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <div className="flex items-center space-x-3">
                            <div className="flex items-center space-x-1">
                              <Calendar className="h-3 w-3" />
                              <span>{formatTimestamp(result.timestamp)}</span>
                            </div>
                            <Badge variant={result.confidenceScore > 0.8 ? "default" : "secondary"} className="text-xs">
                              {Math.round(result.confidenceScore * 100)}% confidence
                            </Badge>
                          </div>
                          <div className="flex items-center space-x-1">
                            <MessageCircle className="h-3 w-3" />
                            <span>Conversation: {result.conversationId.split('_')[1]}</span>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center space-x-2 pt-4">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={currentPage === 1}
                      onClick={() => handleSearch(currentPage - 1)}
                    >
                      Previous
                    </Button>
                    <div className="flex items-center space-x-1">
                      {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                        const page = i + Math.max(1, currentPage - 2)
                        if (page > totalPages) return null
                        return (
                          <Button
                            key={page}
                            variant={page === currentPage ? "default" : "outline"}
                            size="sm"
                            onClick={() => handleSearch(page)}
                          >
                            {page}
                          </Button>
                        )
                      })}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={currentPage === totalPages}
                      onClick={() => handleSearch(currentPage + 1)}
                    >
                      Next
                    </Button>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}