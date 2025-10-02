/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8001/api/:path*', // Proxy to FastAPI backend
      },
      {
        source: '/ws/:path*',
        destination: 'http://localhost:8001/ws/:path*', // Proxy WebSocket connections
      },
    ]
  },
}

module.exports = nextConfig