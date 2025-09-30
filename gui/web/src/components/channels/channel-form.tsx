'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface ChannelConfig {
  channel_id: string
  channel_name: string
  model: string
  cost_threshold: number
  multi_model_enabled: boolean
  telegram_chat_id?: string
  custom_prompt?: string
}

interface ChannelFormProps {
  mode: 'create' | 'edit'
  channelName?: string | null
  onSaved: () => void
  onCancel: () => void
}

const DEFAULT_CONFIG: ChannelConfig = {
  channel_id: '',
  channel_name: '',
  model: 'gpt-4o-mini',
  cost_threshold: 0.50,
  multi_model_enabled: false,
  telegram_chat_id: '',
  custom_prompt: ''
}

const AVAILABLE_MODELS = [
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini (Recommended)' },
  { value: 'gpt-4o', label: 'GPT-4o (Premium)' },
  { value: 'claude-3-haiku', label: 'Claude 3 Haiku' },
  { value: 'claude-3-sonnet', label: 'Claude 3 Sonnet' },
  { value: 'x-ai/grok-4-fast:free', label: 'Grok 4 Fast (Free)' },
  { value: 'deepseek/deepseek-chat-v3.1:free', label: 'DeepSeek Chat (Free)' }
]

export function ChannelForm({ mode, channelName, onSaved, onCancel }: ChannelFormProps) {
  const [config, setConfig] = useState<ChannelConfig>(DEFAULT_CONFIG)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})
  const [showPreview, setShowPreview] = useState(false)

  // Load existing configuration for edit mode
  useEffect(() => {
    if (mode === 'edit' && channelName) {
      loadChannelConfig(channelName)
    }
  }, [mode, channelName])

  const loadChannelConfig = async (name: string) => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/channels/${name}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to load channel: ${response.statusText}`)
      }

      const data = await response.json()
      setConfig(data)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load channel configuration')
      console.error('Error loading channel:', err)
    } finally {
      setLoading(false)
    }
  }

  const validateForm = useCallback(() => {
    const errors: Record<string, string> = {}

    if (!config.channel_id.trim()) {
      errors.channel_id = 'Channel ID is required'
    } else if (!config.channel_id.match(/^UC[a-zA-Z0-9_-]{22}$/)) {
      errors.channel_id = 'Invalid YouTube Channel ID format (should start with UC and be 24 characters)'
    }

    if (!config.channel_name.trim()) {
      errors.channel_name = 'Channel name is required'
    } else if (config.channel_name.length < 2) {
      errors.channel_name = 'Channel name must be at least 2 characters'
    }

    if (!config.model.trim()) {
      errors.model = 'Model selection is required'
    }

    if (config.cost_threshold <= 0) {
      errors.cost_threshold = 'Cost threshold must be greater than 0'
    } else if (config.cost_threshold > 10) {
      errors.cost_threshold = 'Cost threshold seems too high (max recommended: $10)'
    }

    if (config.telegram_chat_id && !config.telegram_chat_id.match(/^(@\w+|[-]?\d+)$/)) {
      errors.telegram_chat_id = 'Invalid Telegram chat ID format (@username or numeric ID)'
    }

    setValidationErrors(errors)
    return Object.keys(errors).length === 0
  }, [config])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    setSaving(true)
    setError(null)

    try {
      const url = mode === 'create' ? '/api/channels' : `/api/channels/${channelName}`
      const method = mode === 'create' ? 'POST' : 'PUT'

      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to ${mode} channel: ${response.statusText}`)
      }

      onSaved()

    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${mode} channel`)
      console.error(`Error ${mode}ing channel:`, err)
    } finally {
      setSaving(false)
    }
  }

  const handleInputChange = (field: keyof ChannelConfig, value: any) => {
    setConfig(prev => ({ ...prev, [field]: value }))
    
    // Clear validation error for this field
    if (validationErrors[field]) {
      setValidationErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors[field]
        return newErrors
      })
    }
  }

  const generateChannelName = () => {
    if (config.channel_id) {
      // Extract potential name from channel ID or use a default
      const name = `channel_${config.channel_id.slice(-8).toLowerCase()}`
      handleInputChange('channel_name', name)
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

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold">
              {mode === 'create' ? 'Add New Channel' : `Edit Channel: ${channelName}`}
            </h2>
            <p className="text-sm text-muted-foreground">
              Configure YouTube channel for automated processing and Telegram notifications.
            </p>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Basic Configuration */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="channel_id">YouTube Channel ID *</Label>
                <div className="flex space-x-2">
                  <Input
                    id="channel_id"
                    placeholder="UCbfYPyITQ-7l4upoX8nvctg"
                    value={config.channel_id}
                    onChange={(e) => handleInputChange('channel_id', e.target.value)}
                    className={validationErrors.channel_id ? 'border-red-500' : ''}
                  />
                  <Button
                    type="button"
                    onClick={generateChannelName}
                    variant="outline"
                    size="sm"
                    disabled={!config.channel_id}
                  >
                    Auto Name
                  </Button>
                </div>
                {validationErrors.channel_id && (
                  <p className="text-xs text-red-600">{validationErrors.channel_id}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Find this in the YouTube channel URL or page source
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="channel_name">Channel Name *</Label>
                <Input
                  id="channel_name"
                  placeholder="my_awesome_channel"
                  value={config.channel_name}
                  onChange={(e) => handleInputChange('channel_name', e.target.value)}
                  className={validationErrors.channel_name ? 'border-red-500' : ''}
                />
                {validationErrors.channel_name && (
                  <p className="text-xs text-red-600">{validationErrors.channel_name}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Used for file names and identification
                </p>
              </div>
            </div>

            {/* AI Configuration */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="model">AI Model *</Label>
                <select
                  id="model"
                  value={config.model}
                  onChange={(e) => handleInputChange('model', e.target.value)}
                  className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm"
                >
                  {AVAILABLE_MODELS.map((model) => (
                    <option key={model.value} value={model.value}>
                      {model.label}
                    </option>
                  ))}
                </select>
                {validationErrors.model && (
                  <p className="text-xs text-red-600">{validationErrors.model}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="cost_threshold">Cost Threshold (USD) *</Label>
                <Input
                  id="cost_threshold"
                  type="number"
                  step="0.01"
                  min="0.01"
                  max="10.00"
                  placeholder="0.50"
                  value={config.cost_threshold}
                  onChange={(e) => handleInputChange('cost_threshold', parseFloat(e.target.value) || 0)}
                  className={validationErrors.cost_threshold ? 'border-red-500' : ''}
                />
                {validationErrors.cost_threshold && (
                  <p className="text-xs text-red-600">{validationErrors.cost_threshold}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Maximum cost per video processing
                </p>
              </div>
            </div>

            {/* Multi-Model Configuration */}
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="multi_model_enabled"
                  checked={config.multi_model_enabled}
                  onChange={(e) => handleInputChange('multi_model_enabled', e.target.checked)}
                />
                <Label htmlFor="multi_model_enabled">Enable Multi-Model Processing</Label>
              </div>
              <p className="text-xs text-muted-foreground">
                Uses multiple AI models for enhanced summary quality (increases cost ~2.5x)
              </p>
            </div>

            {/* Telegram Configuration */}
            <div className="space-y-2">
              <Label htmlFor="telegram_chat_id">Telegram Chat ID (Optional)</Label>
              <Input
                id="telegram_chat_id"
                placeholder="@channel_name or -1234567890"
                value={config.telegram_chat_id || ''}
                onChange={(e) => handleInputChange('telegram_chat_id', e.target.value)}
                className={validationErrors.telegram_chat_id ? 'border-red-500' : ''}
              />
              {validationErrors.telegram_chat_id && (
                <p className="text-xs text-red-600">{validationErrors.telegram_chat_id}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Where to send notifications (leave empty to use default)
              </p>
            </div>

            {/* Custom Prompt */}
            <div className="space-y-2">
              <Label htmlFor="custom_prompt">Custom Prompt (Optional)</Label>
              <textarea
                id="custom_prompt"
                rows={4}
                placeholder="Custom instructions for AI summarization..."
                value={config.custom_prompt || ''}
                onChange={(e) => handleInputChange('custom_prompt', e.target.value)}
                className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm resize-vertical"
              />
              <p className="text-xs text-muted-foreground">
                Override default prompt template with custom instructions
              </p>
            </div>

            {/* Preview Toggle */}
            <div className="flex items-center space-x-2">
              <Button
                type="button"
                onClick={() => setShowPreview(!showPreview)}
                variant="outline"
                size="sm"
              >
                {showPreview ? 'Hide' : 'Show'} Configuration Preview
              </Button>
            </div>

            {/* Configuration Preview */}
            {showPreview && (
              <Card className="p-4 bg-muted">
                <div className="text-sm">
                  <h4 className="font-medium mb-2">Configuration Preview:</h4>
                  <pre className="text-xs overflow-x-auto">
                    {JSON.stringify(config, null, 2)}
                  </pre>
                </div>
              </Card>
            )}

            {/* Form Actions */}
            <div className="flex space-x-2 pt-4 border-t">
              <Button
                type="submit"
                disabled={saving}
                className="flex items-center space-x-2"
              >
                {saving && <LoadingSpinner size="sm" />}
                <span>{saving ? 'Saving...' : (mode === 'create' ? 'Create Channel' : 'Update Channel')}</span>
              </Button>
              <Button
                type="button"
                onClick={onCancel}
                variant="outline"
                disabled={saving}
              >
                Cancel
              </Button>
            </div>
          </form>
        </div>
      </Card>

      {/* Help Card */}
      <Card className="p-4">
        <div className="space-y-3">
          <h4 className="font-medium">Configuration Tips</h4>
          <div className="text-sm text-muted-foreground space-y-2">
            <div>
              <strong>Channel ID:</strong> Found in YouTube channel URL or page source. Always starts with "UC".
            </div>
            <div>
              <strong>Model Selection:</strong> GPT-4o Mini offers the best balance of quality and cost for most channels.
            </div>
            <div>
              <strong>Cost Threshold:</strong> Prevents expensive processing. Typical video costs $0.10-$0.30.
            </div>
            <div>
              <strong>Multi-Model:</strong> Significantly improves summary quality but increases costs. Best for important channels.
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}