# Jarvis Web Application - Setup Guide

## Prerequisites

1. **Node.js 18+** installed
2. **PostgreSQL** database running

## Database Setup

### Option 1: Local PostgreSQL

1. Install PostgreSQL:
   ```bash
   # macOS
   brew install postgresql@15
   brew services start postgresql@15
   ```

2. Create database:
   ```bash
   createdb jarvis
   ```

3. Update `.env` file with your connection string:
   ```
   DATABASE_URL="postgresql://YOUR_USERNAME@localhost:5432/jarvis?schema=public"
   ```

### Option 2: Cloud PostgreSQL (Recommended for Development)

Use a cloud provider like:
- **Neon** (https://neon.tech) - Free tier with PostgreSQL
- **Supabase** (https://supabase.com) - Free tier with built-in features
- **Railway** (https://railway.app) - Easy PostgreSQL deployment

Example Neon connection string:
```
DATABASE_URL="postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/jarvis?sslmode=require"
```

## Installation Steps

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Generate Prisma client:**
   ```bash
   npx prisma generate
   ```

3. **Run database migrations:**
   ```bash
   npx prisma migrate dev --name init
   ```

4. **Start development server:**
   ```bash
   npm run dev
   ```

5. **Open browser:**
   Navigate to http://localhost:3000

## Environment Variables

Copy `.env.local` and update with your values:

```bash
# Required
DATABASE_URL="postgresql://..."
NEXTAUTH_SECRET="your-secret-here"

# Optional - Azure AD SSO
AZURE_AD_CLIENT_ID=""
AZURE_AD_CLIENT_SECRET=""
AZURE_AD_TENANT_ID=""

# Optional - Enable Azure AD in UI
NEXT_PUBLIC_AZURE_AD_ENABLED="false"

# Backend WebSocket URL
NEXT_PUBLIC_WEBSOCKET_URL="http://localhost:8000"
```

## First Time Setup

1. Sign up at http://localhost:3000/auth/signup
2. Create account with email/password
3. Sign in at http://localhost:3000/auth/signin
4. Start a voice session from the dashboard

## Troubleshooting

### Prisma Client Not Generated
```bash
npx prisma generate
```

### Database Connection Error
- Verify PostgreSQL is running
- Check DATABASE_URL in `.env`
- Ensure database exists

### Migration Errors
```bash
npx prisma migrate reset  # WARNING: Deletes all data
npx prisma migrate dev
```

### Port Already in Use
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

## Project Structure

```
web/
├── app/
│   ├── api/auth/          # Authentication API routes
│   ├── auth/              # Sign in/up pages
│   ├── session/           # Voice session pages
│   ├── components/        # React components
│   ├── hooks/             # Custom React hooks
│   └── lib/               # Utilities and clients
├── prisma/
│   └── schema.prisma      # Database schema
├── public/
│   └── audio-worklet-processor.js  # Audio processing
└── auth.ts                # NextAuth configuration
```

## Next Steps

Once the web app is running:
1. Set up the FastAPI backend (port 8000)
2. Implement Socket.IO handlers for audio streaming
3. Integrate VAD, transcription, and LLM services
4. Connect to knowledge retrieval system
