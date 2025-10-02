'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Video, Tag, Plus, X, Search, Calendar, ExternalLink, MessageCircle, Edit } from 'lucide-react'

interface VideoTag {
  id: string
  videoId: string
  videoTitle: string
  videoUrl: string
  channelName: string
  uploadDate: string
  tags: string[]
  notes: string
  createdAt: string
  questionCount: number
}

interface TaggedVideo {
  id: string
  title: string
  url: string
  channelName: string
  uploadDate: string
  duration: string
  summary: string
  tags: string[]
  notes: string
  questionCount: number
  lastQuestionAt?: string
}

export function VideoTagging() {
  const [taggedVideos, setTaggedVideos] = useState<TaggedVideo[]>([])
  const [availableVideos, setAvailableVideos] = useState<Array<{ id: string; title: string; url: string; channelName: string }>>([])
  const [selectedChannel, setSelectedChannel] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedVideo, setSelectedVideo] = useState<TaggedVideo | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [channels, setChannels] = useState<Array<{ id: string; name: string; displayName: string }>>([])
  const [isTagDialogOpen, setIsTagDialogOpen] = useState(false)
  const [newTags, setNewTags] = useState('')
  const [newNotes, setNewNotes] = useState('')
  const [videoToTag, setVideoToTag] = useState<string>('')

  useEffect(() => {
    fetchChannels()
    fetchTaggedVideos()
    fetchAvailableVideos()
  }, [])

  useEffect(() => {
    if (selectedChannel !== 'all') {
      fetchAvailableVideos()
    }
  }, [selectedChannel])

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

  const fetchTaggedVideos = async () => {
    try {
      setIsLoading(true)
      const params = new URLSearchParams()
      if (selectedChannel !== 'all') {
        params.append('channel', selectedChannel)
      }
      if (searchQuery) {
        params.append('search', searchQuery)
      }

      const response = await fetch(`/api/qna/tagged-videos?${params}`)
      if (response.ok) {
        const data = await response.json()
        setTaggedVideos(data)
      }
    } catch (error) {
      console.error('Failed to fetch tagged videos:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchAvailableVideos = async () => {
    try {
      const params = new URLSearchParams()
      if (selectedChannel !== 'all') {
        params.append('channel', selectedChannel)
      }

      const response = await fetch(`/api/database/videos?${params}&limit=100`)
      if (response.ok) {
        const data = await response.json()
        setAvailableVideos(data.videos || [])
      }
    } catch (error) {
      console.error('Failed to fetch available videos:', error)
    }
  }

  const handleTagVideo = async () => {
    if (!videoToTag || !newTags.trim()) return

    try {
      const tags = newTags.split(',').map(tag => tag.trim()).filter(tag => tag)
      
      const response = await fetch('/api/qna/tag-video', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_id: videoToTag,
          tags,
          notes: newNotes.trim()
        }),
      })

      if (response.ok) {
        setIsTagDialogOpen(false)
        setVideoToTag('')
        setNewTags('')
        setNewNotes('')
        fetchTaggedVideos()
      }
    } catch (error) {
      console.error('Failed to tag video:', error)
    }
  }

  const handleRemoveTag = async (videoId: string, tagToRemove: string) => {
    try {
      const response = await fetch('/api/qna/remove-tag', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_id: videoId,
          tag: tagToRemove
        }),
      })

      if (response.ok) {
        fetchTaggedVideos()
      }
    } catch (error) {
      console.error('Failed to remove tag:', error)
    }
  }

  const handleUpdateNotes = async (videoId: string, notes: string) => {
    try {
      const response = await fetch('/api/qna/update-notes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_id: videoId,
          notes
        }),
      })

      if (response.ok) {
        fetchTaggedVideos()
      }
    } catch (error) {
      console.error('Failed to update notes:', error)
    }
  }

  const openTagDialog = (videoId?: string) => {
    setVideoToTag(videoId || '')
    setNewTags('')
    setNewNotes('')
    setIsTagDialogOpen(true)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  const getChannelDisplayName = (channelName: string) => {
    const channel = channels.find(ch => ch.name === channelName)
    return channel?.displayName || channelName
  }

  const filteredVideos = taggedVideos.filter(video => {
    const matchesChannel = selectedChannel === 'all' || video.channelName === selectedChannel
    const matchesSearch = !searchQuery || 
      video.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      video.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase())) ||
      video.notes.toLowerCase().includes(searchQuery.toLowerCase())
    
    return matchesChannel && matchesSearch
  })

  const allTags = Array.from(new Set(taggedVideos.flatMap(video => video.tags))).sort()

  return (
    <div className="space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search videos, tags, or notes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={selectedChannel} onValueChange={setSelectedChannel}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Filter by channel" />
          </SelectTrigger>
          <SelectContent>
            {channels.map((channel) => (
              <SelectItem key={channel.id} value={channel.id}>
                {channel.displayName}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button onClick={() => openTagDialog()}>
          <Plus className="h-4 w-4 mr-2" />
          Tag Video
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Video className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Tagged Videos</span>
            </div>
            <div className="text-2xl font-bold mt-1">{filteredVideos.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Tag className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Unique Tags</span>
            </div>
            <div className="text-2xl font-bold mt-1">{allTags.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <MessageCircle className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Total Questions</span>
            </div>
            <div className="text-2xl font-bold mt-1">
              {filteredVideos.reduce((sum, video) => sum + video.questionCount, 0)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Popular Tags */}
      {allTags.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Popular Tags</CardTitle>
            <CardDescription>Click a tag to filter videos</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {allTags.slice(0, 20).map((tag) => {
                const count = taggedVideos.filter(video => video.tags.includes(tag)).length
                return (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="cursor-pointer hover:bg-secondary/80"
                    onClick={() => setSearchQuery(tag)}
                  >
                    {tag} ({count})
                  </Badge>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tagged Videos List */}
      <Card>
        <CardHeader>
          <CardTitle>Tagged Videos</CardTitle>
          <CardDescription>
            {filteredVideos.length} video{filteredVideos.length !== 1 ? 's' : ''} tagged for enhanced Q&A
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : filteredVideos.length === 0 ? (
            <div className="text-center py-8">
              <Video className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-muted-foreground">No tagged videos found</p>
              <p className="text-sm text-muted-foreground mt-2">
                Tag videos to enable targeted questioning and better context retrieval
              </p>
              <Button className="mt-4" onClick={() => openTagDialog()}>
                <Plus className="h-4 w-4 mr-2" />
                Tag Your First Video
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredVideos.map((video) => (
                <Card key={video.id} className="border-l-4 border-l-primary/20">
                  <CardContent className="p-4">
                    <div className="space-y-3">
                      {/* Header */}
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="font-medium line-clamp-2">{video.title}</h3>
                          <div className="flex items-center space-x-4 mt-1 text-sm text-muted-foreground">
                            <span>{getChannelDisplayName(video.channelName)}</span>
                            <div className="flex items-center space-x-1">
                              <Calendar className="h-3 w-3" />
                              <span>{formatDate(video.uploadDate)}</span>
                            </div>
                            <span>{video.duration}</span>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2 ml-4">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => window.open(video.url, '_blank')}
                          >
                            <ExternalLink className="h-4 w-4" />
                          </Button>
                          <Dialog>
                            <DialogTrigger asChild>
                              <Button variant="ghost" size="sm">
                                <Edit className="h-4 w-4" />
                              </Button>
                            </DialogTrigger>
                            <DialogContent>
                              <DialogHeader>
                                <DialogTitle>Edit Video Tags</DialogTitle>
                                <DialogDescription>
                                  Update tags and notes for this video
                                </DialogDescription>
                              </DialogHeader>
                              <div className="space-y-4">
                                <div>
                                  <label className="text-sm font-medium">Tags (comma-separated)</label>
                                  <Input
                                    defaultValue={video.tags.join(', ')}
                                    onChange={(e) => setNewTags(e.target.value)}
                                    placeholder="machine learning, AI, research"
                                  />
                                </div>
                                <div>
                                  <label className="text-sm font-medium">Notes</label>
                                  <Textarea
                                    defaultValue={video.notes}
                                    onChange={(e) => setNewNotes(e.target.value)}
                                    placeholder="Add notes about this video..."
                                    rows={3}
                                  />
                                </div>
                                <Button 
                                  onClick={() => {
                                    const tags = newTags.split(',').map(tag => tag.trim()).filter(tag => tag)
                                    // Update logic here
                                  }}
                                >
                                  Update
                                </Button>
                              </div>
                            </DialogContent>
                          </Dialog>
                        </div>
                      </div>

                      {/* Summary */}
                      {video.summary && (
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {video.summary}
                        </p>
                      )}

                      {/* Tags */}
                      <div className="flex flex-wrap gap-1">
                        {video.tags.map((tag) => (
                          <Badge
                            key={tag}
                            variant="secondary"
                            className="text-xs group cursor-pointer"
                            onClick={() => setSearchQuery(tag)}
                          >
                            {tag}
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-3 w-3 p-0 ml-1 opacity-0 group-hover:opacity-100"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleRemoveTag(video.id, tag)
                              }}
                            >
                              <X className="h-2 w-2" />
                            </Button>
                          </Badge>
                        ))}
                      </div>

                      {/* Notes */}
                      {video.notes && (
                        <div className="bg-muted/50 p-3 rounded-lg">
                          <p className="text-sm">{video.notes}</p>
                        </div>
                      )}

                      {/* Stats */}
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <div className="flex items-center space-x-3">
                          <div className="flex items-center space-x-1">
                            <MessageCircle className="h-3 w-3" />
                            <span>{video.questionCount} question{video.questionCount !== 1 ? 's' : ''}</span>
                          </div>
                          {video.lastQuestionAt && (
                            <span>Last question: {formatDate(video.lastQuestionAt)}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tag Video Dialog */}
      <Dialog open={isTagDialogOpen} onOpenChange={setIsTagDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Tag Video for Q&A</DialogTitle>
            <DialogDescription>
              Add tags and notes to improve question answering for specific videos
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Select Video</label>
              <Select value={videoToTag} onValueChange={setVideoToTag}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a video to tag" />
                </SelectTrigger>
                <SelectContent>
                  {availableVideos.map((video) => (
                    <SelectItem key={video.id} value={video.id}>
                      <div className="flex flex-col">
                        <span className="truncate max-w-64">{video.title}</span>
                        <span className="text-xs text-muted-foreground">{video.channelName}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">Tags (comma-separated)</label>
              <Input
                value={newTags}
                onChange={(e) => setNewTags(e.target.value)}
                placeholder="machine learning, AI, research, tutorial"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Add relevant tags to help categorize and find this video
              </p>
            </div>
            <div>
              <label className="text-sm font-medium">Notes (optional)</label>
              <Textarea
                value={newNotes}
                onChange={(e) => setNewNotes(e.target.value)}
                placeholder="Add notes about key topics, timestamps, or context..."
                rows={3}
              />
            </div>
            <div className="flex justify-end space-x-2">
              <Button variant="outline" onClick={() => setIsTagDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleTagVideo} disabled={!videoToTag || !newTags.trim()}>
                Tag Video
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}