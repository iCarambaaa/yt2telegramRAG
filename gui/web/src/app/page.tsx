'use client'

import { useState } from 'react'
import { InterfaceModeToggle } from '@/components/interface/interface-mode-toggle'
import { DashboardOverview } from '@/components/dashboard/dashboard-overview'
import { AIChat } from '@/components/ai/ai-chat'
import { ClientOnly } from '@/components/providers/client-only'

export default function HomePage() {
  const [interfaceMode, setInterfaceMode] = useState<'gui' | 'ai'>('gui')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Unified GUI Platform
          </h1>
          <p className="text-muted-foreground">
            Manage your YouTube to Telegram system with traditional GUI or AI assistance
          </p>
        </div>
        <ClientOnly
          fallback={
            <div className="h-10 w-48 bg-gray-200 animate-pulse rounded"></div>
          }
        >
          <InterfaceModeToggle 
            mode={interfaceMode} 
            onModeChange={setInterfaceMode} 
          />
        </ClientOnly>
      </div>

      <ClientOnly
        fallback={
          <div className="space-y-4">
            <div className="h-32 bg-gray-200 animate-pulse rounded"></div>
            <div className="h-64 bg-gray-200 animate-pulse rounded"></div>
          </div>
        }
      >
        {interfaceMode === 'gui' ? (
          <DashboardOverview />
        ) : (
          <AIChat />
        )}
      </ClientOnly>
    </div>
  )
}