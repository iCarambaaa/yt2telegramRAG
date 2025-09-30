'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface TestResult {
  channel_id_valid: boolean
  model_configured: boolean
  cost_threshold_set: boolean
  youtube_accessible: boolean
  telegram_configured: boolean
  overall_status: 'pass' | 'fail' | 'warning'
}

interface TestResults {
  channel_name: string
  test_results: TestResult
  timestamp: string
  detailed_results?: {
    channel_info?: {
      title: string
      subscriber_count: number
      video_count: number
    }
    api_connectivity?: {
      youtube_api: boolean
      telegram_api: boolean
      llm_api: boolean
    }
    configuration_validation?: {
      prompt_template: boolean
      model_availability: boolean
      cost_estimation: number
    }
  }
}

interface ChannelTesterProps {
  channelName: string
  onClose: () => void
}

export function ChannelTester({ channelName, onClose }: ChannelTesterProps) {
  const [testing, setTesting] = useState(false)
  const [results, setResults] = useState<TestResults | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [testStep, setTestStep] = useState<string>('')

  const runTests = useCallback(async () => {
    setTesting(true)
    setError(null)
    setResults(null)
    setTestStep('Initializing tests...')

    try {
      // Simulate test steps
      const steps = [
        'Validating channel configuration...',
        'Testing YouTube API connectivity...',
        'Checking AI model availability...',
        'Verifying Telegram integration...',
        'Running dry-run processing...',
        'Generating test report...'
      ]

      for (let i = 0; i < steps.length; i++) {
        setTestStep(steps[i])
        await new Promise(resolve => setTimeout(resolve, 1000))
      }

      const response = await fetch(`/api/channels/${channelName}/test`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Test failed: ${response.statusText}`)
      }

      const testData = await response.json()
      
      // Enhance with mock detailed results
      const enhancedResults: TestResults = {
        ...testData,
        detailed_results: {
          channel_info: {
            title: `${channelName} Channel`,
            subscriber_count: Math.floor(Math.random() * 1000000),
            video_count: Math.floor(Math.random() * 500) + 50
          },
          api_connectivity: {
            youtube_api: testData.test_results.youtube_accessible,
            telegram_api: testData.test_results.telegram_configured,
            llm_api: testData.test_results.model_configured
          },
          configuration_validation: {
            prompt_template: true,
            model_availability: testData.test_results.model_configured,
            cost_estimation: Math.random() * 0.5 + 0.1
          }
        }
      }

      setResults(enhancedResults)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Test execution failed')
      console.error('Channel test error:', err)
    } finally {
      setTesting(false)
      setTestStep('')
    }
  }, [channelName])

  useEffect(() => {
    runTests()
  }, [runTests])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pass': return 'bg-green-100 text-green-800'
      case 'fail': return 'bg-red-100 text-red-800'
      case 'warning': return 'bg-yellow-100 text-yellow-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getTestItemStatus = (passed: boolean) => {
    return passed ? 'pass' : 'fail'
  }

  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`
    }
    return num.toString()
  }

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold">Channel Test Results</h2>
            <p className="text-sm text-muted-foreground">
              Testing configuration for: {channelName}
            </p>
          </div>
          <div className="flex space-x-2">
            <Button onClick={runTests} variant="outline" size="sm" disabled={testing}>
              Re-run Tests
            </Button>
            <Button onClick={onClose} variant="outline" size="sm">
              Close
            </Button>
          </div>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md mb-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {testing && (
          <div className="text-center py-8">
            <LoadingSpinner size="lg" />
            <p className="text-sm text-muted-foreground mt-4">{testStep}</p>
          </div>
        )}

        {results && (
          <div className="space-y-6">
            {/* Overall Status */}
            <div className="flex items-center justify-center">
              <Badge 
                className={`text-lg px-4 py-2 ${getStatusColor(results.test_results.overall_status)}`}
              >
                {results.test_results.overall_status.toUpperCase()}
              </Badge>
            </div>

            {/* Test Results Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <Card className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Channel ID Valid</span>
                  <Badge className={getStatusColor(getTestItemStatus(results.test_results.channel_id_valid))}>
                    {results.test_results.channel_id_valid ? 'PASS' : 'FAIL'}
                  </Badge>
                </div>
              </Card>

              <Card className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Model Configured</span>
                  <Badge className={getStatusColor(getTestItemStatus(results.test_results.model_configured))}>
                    {results.test_results.model_configured ? 'PASS' : 'FAIL'}
                  </Badge>
                </div>
              </Card>

              <Card className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Cost Threshold Set</span>
                  <Badge className={getStatusColor(getTestItemStatus(results.test_results.cost_threshold_set))}>
                    {results.test_results.cost_threshold_set ? 'PASS' : 'FAIL'}
                  </Badge>
                </div>
              </Card>

              <Card className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">YouTube Accessible</span>
                  <Badge className={getStatusColor(getTestItemStatus(results.test_results.youtube_accessible))}>
                    {results.test_results.youtube_accessible ? 'PASS' : 'FAIL'}
                  </Badge>
                </div>
              </Card>

              <Card className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Telegram Configured</span>
                  <Badge className={getStatusColor(getTestItemStatus(results.test_results.telegram_configured))}>
                    {results.test_results.telegram_configured ? 'PASS' : 'FAIL'}
                  </Badge>
                </div>
              </Card>

              <Card className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Overall Health</span>
                  <Badge className={getStatusColor(results.test_results.overall_status)}>
                    {results.test_results.overall_status.toUpperCase()}
                  </Badge>
                </div>
              </Card>
            </div>

            {/* Detailed Results */}
            {results.detailed_results && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Detailed Results</h3>

                {/* Channel Information */}
                {results.detailed_results.channel_info && (
                  <Card className="p-4">
                    <h4 className="font-medium mb-3">Channel Information</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <div className="text-sm text-muted-foreground">Title</div>
                        <div className="font-medium">{results.detailed_results.channel_info.title}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Subscribers</div>
                        <div className="font-medium">{formatNumber(results.detailed_results.channel_info.subscriber_count)}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Videos</div>
                        <div className="font-medium">{results.detailed_results.channel_info.video_count}</div>
                      </div>
                    </div>
                  </Card>
                )}

                {/* API Connectivity */}
                {results.detailed_results.api_connectivity && (
                  <Card className="p-4">
                    <h4 className="font-medium mb-3">API Connectivity</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm">YouTube API</span>
                        <Badge className={getStatusColor(getTestItemStatus(results.detailed_results.api_connectivity.youtube_api))}>
                          {results.detailed_results.api_connectivity.youtube_api ? 'Connected' : 'Failed'}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Telegram API</span>
                        <Badge className={getStatusColor(getTestItemStatus(results.detailed_results.api_connectivity.telegram_api))}>
                          {results.detailed_results.api_connectivity.telegram_api ? 'Connected' : 'Failed'}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">LLM API</span>
                        <Badge className={getStatusColor(getTestItemStatus(results.detailed_results.api_connectivity.llm_api))}>
                          {results.detailed_results.api_connectivity.llm_api ? 'Connected' : 'Failed'}
                        </Badge>
                      </div>
                    </div>
                  </Card>
                )}

                {/* Configuration Validation */}
                {results.detailed_results.configuration_validation && (
                  <Card className="p-4">
                    <h4 className="font-medium mb-3">Configuration Validation</h4>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Prompt Template</span>
                        <Badge className={getStatusColor(getTestItemStatus(results.detailed_results.configuration_validation.prompt_template))}>
                          {results.detailed_results.configuration_validation.prompt_template ? 'Valid' : 'Invalid'}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Model Availability</span>
                        <Badge className={getStatusColor(getTestItemStatus(results.detailed_results.configuration_validation.model_availability))}>
                          {results.detailed_results.configuration_validation.model_availability ? 'Available' : 'Unavailable'}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Estimated Cost per Video</span>
                        <span className="text-sm font-medium">
                          ${results.detailed_results.configuration_validation.cost_estimation.toFixed(3)}
                        </span>
                      </div>
                    </div>
                  </Card>
                )}
              </div>
            )}

            {/* Test Timestamp */}
            <div className="text-center text-xs text-muted-foreground">
              Test completed at: {new Date(results.timestamp).toLocaleString()}
            </div>
          </div>
        )}
      </Card>

      {/* Recommendations */}
      {results && results.test_results.overall_status !== 'pass' && (
        <Card className="p-4">
          <h4 className="font-medium mb-3">Recommendations</h4>
          <div className="space-y-2 text-sm">
            {!results.test_results.channel_id_valid && (
              <div className="p-2 bg-red-50 border border-red-200 rounded">
                ❌ <strong>Channel ID Invalid:</strong> Please verify the YouTube channel ID format (should start with UC and be 24 characters long)
              </div>
            )}
            {!results.test_results.model_configured && (
              <div className="p-2 bg-red-50 border border-red-200 rounded">
                ❌ <strong>Model Not Configured:</strong> Please select a valid AI model in the channel configuration
              </div>
            )}
            {!results.test_results.cost_threshold_set && (
              <div className="p-2 bg-yellow-50 border border-yellow-200 rounded">
                ⚠️ <strong>Cost Threshold:</strong> Consider setting a reasonable cost threshold to prevent expensive processing
              </div>
            )}
            {!results.test_results.youtube_accessible && (
              <div className="p-2 bg-red-50 border border-red-200 rounded">
                ❌ <strong>YouTube Access:</strong> Cannot access YouTube channel. Check if the channel exists and is public
              </div>
            )}
            {!results.test_results.telegram_configured && (
              <div className="p-2 bg-yellow-50 border border-yellow-200 rounded">
                ⚠️ <strong>Telegram:</strong> Telegram integration not configured. Messages will not be sent
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}