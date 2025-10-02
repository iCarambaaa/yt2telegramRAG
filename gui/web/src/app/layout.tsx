import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/components/providers/auth-provider'
import { ErrorBoundary } from '@/components/providers/error-boundary'
import { Navigation } from '@/components/layout/navigation'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Unified GUI Platform',
  description: 'YouTube to Telegram management platform with AI assistance',
  manifest: '/manifest.json',
  themeColor: '#000000',
  viewport: 'width=device-width, initial-scale=1, maximum-scale=1',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        <ErrorBoundary>
          <AuthProvider>
            <div className="min-h-screen bg-background">
              <Navigation />
              <main className="container mx-auto px-4 py-6">
                <ErrorBoundary>
                  {children}
                </ErrorBoundary>
              </main>
            </div>
          </AuthProvider>
        </ErrorBoundary>
      </body>
    </html>
  )
}