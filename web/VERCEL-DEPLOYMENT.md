# Vercel Deployment Guide

## Quick Deploy

```bash
cd web
vercel
```

Follow the prompts:
- **Set up and deploy?** Yes
- **Which scope?** Choose your account
- **Link to existing project?** No
- **Project name?** jarvis-frontend (or your choice)
- **Directory?** ./ (current directory)
- **Override settings?** No

## Environment Variables

After the initial deployment, you need to set environment variables in the Vercel dashboard.

### Required Environment Variables

Go to your Vercel project dashboard → Settings → Environment Variables and add:

#### NextAuth Configuration
```bash
NEXTAUTH_URL=https://your-project.vercel.app
NEXTAUTH_SECRET=<generate-with-openssl-rand-base64-32>
```

#### Database (AWS RDS)
```bash
DATABASE_URL=postgresql://jarvisadmin:JarvisDB2024Secure@jarvis-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com:5432/jarvis
```

#### Backend API (AWS ECS)
```bash
NEXT_PUBLIC_API_URL=http://your-backend-alb-url:8000
NEXT_PUBLIC_WS_URL=ws://your-backend-alb-url:8000
```

**Note:** You'll need to get the actual ALB (Application Load Balancer) URL for your backend from AWS, or use the direct ECS task IP once it's running.

#### Optional: Azure AD (for Microsoft SSO)
```bash
NEXT_PUBLIC_AZURE_AD_ENABLED=true
AZURE_AD_CLIENT_ID=your-azure-client-id
AZURE_AD_CLIENT_SECRET=your-azure-client-secret
AZURE_AD_TENANT_ID=your-azure-tenant-id
```

### Setting Environment Variables via CLI

Alternatively, you can set them via CLI:

```bash
# NextAuth
vercel env add NEXTAUTH_SECRET
# Paste the value when prompted

vercel env add NEXTAUTH_URL
# Enter: https://your-project.vercel.app

# Database
vercel env add DATABASE_URL
# Paste your PostgreSQL connection string

# Backend API
vercel env add NEXT_PUBLIC_API_URL
vercel env add NEXT_PUBLIC_WS_URL
```

## Database Access from Vercel

Vercel needs to connect to your AWS RDS database. You have two options:

### Option 1: Make RDS Publicly Accessible (Quick but less secure)
1. Go to AWS RDS Console
2. Select your `jarvis-db` instance
3. Click "Modify"
4. Under "Connectivity", set "Public access" to "Yes"
5. Update security group to allow connections from anywhere (0.0.0.0/0) on port 5432
6. Apply changes

### Option 2: Use Vercel's Static IPs with AWS Security Group (More secure)
1. Get Vercel's static IP ranges from their docs
2. Update RDS security group to allow only those IPs
3. This requires a Vercel Pro plan

## Deployment Workflow

### First Deployment
```bash
cd web
vercel
```

This creates a preview deployment. To deploy to production:

```bash
vercel --prod
```

### Subsequent Deployments
```bash
# Preview deployment (for testing)
vercel

# Production deployment
vercel --prod
```

### Auto-Deploy from Git
Link your GitHub repo to Vercel for automatic deployments:

1. Go to Vercel dashboard
2. Import your GitHub repository
3. Every push to `main` branch will auto-deploy to production
4. Every PR will get a preview deployment

## After Deployment

### 1. Update NEXTAUTH_URL
Once you have your production URL (e.g., `jarvis-frontend.vercel.app`):
```bash
vercel env add NEXTAUTH_URL production
# Enter: https://jarvis-frontend.vercel.app
```

Then redeploy:
```bash
vercel --prod
```

### 2. Update Backend CORS
Your backend needs to allow requests from your Vercel domain. Update `backend/app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://jarvis-frontend.vercel.app",  # Add your Vercel URL
        "https://*.vercel.app"  # Allow preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Test the Deployment
1. Visit your Vercel URL
2. Try signing up for an account
3. Test sign in
4. Check if backend API calls work (may need ALB setup)

## Troubleshooting

### Database Connection Fails
- Check RDS is publicly accessible or Vercel IPs are whitelisted
- Verify DATABASE_URL is correct
- Check RDS security group allows port 5432

### NextAuth Errors
- Ensure NEXTAUTH_SECRET is set
- Verify NEXTAUTH_URL matches your actual domain
- Check browser cookies are enabled

### Backend API Not Working
- You need to set up an Application Load Balancer (ALB) in AWS for your ECS service
- Or use the direct ECS task public IP (changes on restart)
- Update NEXT_PUBLIC_API_URL with the correct endpoint

### Build Fails
```bash
# Check build locally first
npm run build

# View build logs in Vercel dashboard
# Settings → Deployments → Click on failed deployment
```

## Custom Domain

To use `jarvis.frontier.audio`:

1. Go to Vercel dashboard → Settings → Domains
2. Add domain: `jarvis.frontier.audio`
3. Update DNS records in your domain registrar:
   - Add CNAME record pointing to `cname.vercel-dns.com`
4. Wait for DNS propagation (~5-10 minutes)

## Cost

- **Free Tier**: Includes:
  - Unlimited preview deployments
  - 100 GB bandwidth/month
  - Serverless function executions
  - Enough for development and low-traffic production

- **Pro Plan ($20/month)**: If you need:
  - More bandwidth
  - Team collaboration
  - Static IP addresses
  - Priority support

## Next Steps

1. **Deploy**: Run `vercel --prod`
2. **Set environment variables** in Vercel dashboard
3. **Update backend CORS** to allow your Vercel domain
4. **Set up ALB** for backend (or use ECS task IP temporarily)
5. **Test** the full application end-to-end
6. **Add custom domain** (optional)

## Rollback

If something goes wrong:
```bash
# List deployments
vercel ls

# Promote a previous deployment to production
vercel promote <deployment-url>
```

Or use the Vercel dashboard to promote a previous deployment.
