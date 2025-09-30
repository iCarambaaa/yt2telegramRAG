# Unified GUI Platform - Web Interface

This is the Next.js web interface for the Unified GUI Platform, providing both traditional GUI and AI-powered conversational management for the YouTube to Telegram system.

## Features

- **Hybrid Interface**: Switch between traditional GUI and AI chat modes
- **Authentication**: Secure login with NextAuth.js
- **Responsive Design**: Mobile-first design with Tailwind CSS
- **Real-time Updates**: WebSocket integration for live data
- **Progressive Web App**: PWA capabilities for mobile installation

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Running FastAPI backend on port 8000

### Installation

1. Install dependencies:
```bash
npm install
```

2. Copy environment variables:
```bash
cp .env.local.example .env.local
```

3. Update environment variables in `.env.local` as needed

### Development

Run the development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Building for Production

```bash
npm run build
npm start
```

## Project Structure

```
src/
├── app/                 # Next.js App Router pages
│   ├── api/            # API routes
│   ├── auth/           # Authentication pages
│   └── */              # Feature pages
├── components/         # React components
│   ├── ui/            # Base UI components
│   ├── layout/        # Layout components
│   ├── interface/     # Interface switching
│   ├── dashboard/     # Dashboard components
│   └── ai/            # AI chat components
└── lib/               # Utilities and configurations
```

## Authentication

Default demo credentials:
- Username: `admin`
- Password: `admin`

## Interface Modes

### GUI Mode
Traditional web interface with:
- Dashboard overview
- Navigation menu
- Form-based interactions
- Data tables and charts

### AI Chat Mode
Conversational interface with:
- Natural language processing
- Context-aware responses
- Quick action buttons
- Streaming responses

## Integration with Backend

The web interface communicates with the FastAPI backend through:
- REST API calls for data operations
- WebSocket connections for real-time updates
- Proxy configuration in `next.config.js`

## Mobile Support

- Responsive design for all screen sizes
- Touch-optimized interactions
- PWA manifest for app installation
- Offline capabilities (future enhancement)

## Development Notes

- Uses TypeScript for type safety
- Tailwind CSS for styling
- Lucide React for icons
- NextAuth.js for authentication
- Class Variance Authority for component variants