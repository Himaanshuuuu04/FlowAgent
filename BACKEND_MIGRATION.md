# Backend Migration Guide

## Overview
The backend services have been **unified into a single server** located at `himanshu/server.py`. This eliminates the need to run multiple backend services.

## What Changed?

### Before (Multiple Backends)
- **Extension/backend_service.py** (Port 5000) - OAuth & Chat
- **himanshu/server.py** (Port 8080) - Agent & WebSocket

### After (Single Backend)
- **himanshu/server.py** (Port 8080) - Everything unified! 🎉

## Features Now Available on Port 8080

### 1. **OAuth Authentication**
- Google OAuth: `/exchange-code`, `/refresh-token`
- GitHub OAuth: `/github/exchange-code`

### 2. **AI Chat**
- Gemini chat: `/chat`

### 3. **Agent System** 
- Script generation: `/generate-script`
- WebSocket connections: `ws://localhost:8080/socket.io/`

### 4. **Health Check**
- Status endpoint: `/health`

## How to Run

### Single Command (Recommended)
```bash
cd himanshu
python server.py
```

That's it! Everything now runs on **http://localhost:8080**

## Environment Variables

Make sure your `himanshu/.env` file contains:

```env
# Required for agent features
GROQ_API_KEY=your_groq_api_key

# Optional - for Google OAuth
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Optional - for GitHub OAuth  
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# Optional - for Gemini chat
GEMINI_API_KEY=your_gemini_api_key

# Server secret
SECRET_KEY=your_secret_key_here
```

## What to Do with Old Backend?

The **Extension/backend_service.py** file is now **deprecated** and can be safely deleted or kept as a reference. The frontend has been updated to use port 8080 for all requests.

### Optional Cleanup
```bash
# You can remove the old backend service (optional)
rm Extension/backend_service.py
```

## Frontend Changes

The frontend (`Extension/entrypoints/sidepanel/hooks/useAuth.ts`) has been automatically updated:
- Changed `BACKEND_URL` from `http://localhost:5000` → `http://localhost:8080`

## Startup Log

When you run the unified server, you'll see:
```
============================================================
🚀 Starting Unified Backend Server
============================================================
✅ Google OAuth configured
✅ GitHub OAuth configured
✅ Gemini AI configured
✅ Groq AI configured

📡 Server endpoints:
   HTTP/REST: http://0.0.0.0:8080
   WebSocket: ws://0.0.0.0:8080/socket.io/
   OAuth: /exchange-code, /refresh-token, /github/exchange-code
   Chat: /chat
   Agent: /generate-script
============================================================
```

## Benefits

✅ **Single process** - No more managing multiple terminals  
✅ **Single port** - Everything on 8080  
✅ **Easier deployment** - One service to deploy  
✅ **Unified logs** - All activity in one place  
✅ **Better resource usage** - Shared Flask app and SocketIO instance  

## Troubleshooting

### Port Already in Use
If port 8080 is busy:
```bash
# Windows
netstat -ano | findstr :8080
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8080
kill -9 <PID>
```

### Missing Dependencies
```bash
cd himanshu
pip install -r requirements.txt
pip install requests google-generativeai
```

### OAuth Not Working
- Verify environment variables are set in `himanshu/.env`
- Check the startup logs for configuration warnings
- Ensure CLIENT_SECRET values are correct

## Migration Checklist

- [x] Backend services merged into `himanshu/server.py`
- [x] OAuth endpoints integrated (Google + GitHub)
- [x] Gemini chat endpoint added
- [x] Frontend updated to use port 8080
- [x] Startup logs enhanced with feature status
- [ ] Test Google OAuth flow
- [ ] Test GitHub OAuth flow
- [ ] Test agent execution
- [ ] Test WebSocket connection
- [ ] (Optional) Remove old backend_service.py

## Need Help?

If you encounter any issues:
1. Check the server logs for errors
2. Verify all environment variables are set
3. Ensure port 8080 is available
4. Review the startup log for configuration warnings

Happy coding! 🚀
