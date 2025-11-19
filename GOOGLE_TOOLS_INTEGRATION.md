# Google Tools Integration Guide

## Overview

The agent system now has access to Google Calendar and Gmail data through 4 new tools. These tools are automatically available when a user authenticates with Google OAuth.

## Google Tools

### 1. `get_user_info`
**Purpose**: Get authenticated user's profile information

**Returns**:
```json
{
  "success": true,
  "data": {
    "name": "John Doe",
    "email": "john@example.com",
    "picture": "https://...",
    "verified_email": true
  }
}
```

**Use Cases**:
- Verify user identity
- Display user profile
- Check email for filtering

---

### 2. `get_calendar_events`
**Purpose**: Fetch upcoming calendar events

**Parameters**:
- `max_results` (int, optional): Maximum number of events (default: 10, max: 50)
- `days_ahead` (int, optional): Filter events within next N days

**Returns**:
```json
{
  "success": true,
  "data": [
    {
      "id": "event_123",
      "summary": "Team Meeting",
      "start": "2024-01-15T10:00:00-08:00",
      "end": "2024-01-15T11:00:00-08:00",
      "location": "Conference Room A",
      "description": "Weekly sync",
      "attendees": ["alice@example.com", "bob@example.com"]
    }
  ]
}
```

**Example Queries**:
- "What's on my calendar today?"
- "Show me my meetings for the next 3 days"
- "Do I have any events this week?"

---

### 3. `get_latest_emails`
**Purpose**: Fetch recent inbox messages

**Parameters**:
- `max_results` (int, optional): Maximum number of emails (default: 5, max: 20)
- `query` (str, optional): Gmail search query (e.g., "from:john@example.com", "subject:invoice")

**Returns**:
```json
{
  "success": true,
  "data": [
    {
      "id": "msg_123",
      "subject": "Project Update",
      "from": "alice@example.com",
      "to": "john@example.com",
      "date": "2024-01-15T09:30:00Z",
      "snippet": "Here's the latest status on the project..."
    }
  ]
}
```

**Example Queries**:
- "Show me my latest emails"
- "Any new messages from my boss?"
- "Check emails about the project"

---

### 4. `search_emails`
**Purpose**: Search for specific emails

**Parameters**:
- `search_query` (str, required): Text to search for in emails
- `max_results` (int, optional): Maximum results (default: 10)

**Returns**: Same format as `get_latest_emails`

**Example Queries**:
- "Find emails about invoices"
- "Search for messages from john@example.com"
- "Look for emails with 'meeting' in subject"

---

## Authentication Flow

### 1. User Login (Frontend)
```typescript
// useAuth.ts - handleLogin()
const token = tokenData.access_token;
// ... store user data ...

// Send token to WebSocket server
if (wsClient.isSocketConnected()) {
  await wsClient.setGoogleToken(token);
}
```

### 2. Token Transmission (WebSocket)
```typescript
// websocket-client.ts
async setGoogleToken(accessToken: string): Promise<any> {
  this.socket.emit("set_google_token", { access_token: accessToken });
}
```

### 3. Token Storage (Backend)
```python
# server.py - handle_set_google_token()
@socketio.on('set_google_token')
def handle_set_google_token(data):
    access_token = data.get('access_token')
    set_google_access_token(access_token)
    # Token stored for agent tools
```

### 4. Tool Execution (Agent)
```python
# agent.py - during execution
# Token automatically used by Google tools
result = agent.invoke({"messages": [{"role": "user", "content": goal}]})
# Tools can now access Calendar and Gmail APIs
```

---

## Implementation Details

### Files Modified

1. **`himanshu/agents/google_tools.py`** (NEW)
   - 4 tool implementations
   - Token management functions
   - API request handling with error logging

2. **`himanshu/agents/agent.py`**
   - Import: `from .google_tools import google_tools, set_google_access_token`
   - Tools list: `*google_tools` added to existing tools
   - System prompt: Added "📧 GOOGLE SERVICES" section

3. **`himanshu/server.py`**
   - Import: `from agents.google_tools import set_google_access_token`
   - WebSocket handler: `@socketio.on('set_google_token')`
   - Token storage in `connected_clients` dict
   - Token setup before agent execution

4. **`Extension/entrypoints/utils/websocket-client.ts`**
   - New method: `setGoogleToken(accessToken: string)`
   - Promise-based with success/error handlers

5. **`Extension/entrypoints/sidepanel/hooks/useAuth.ts`**
   - Import: `import { wsClient } from "../../utils/websocket-client"`
   - Token transmission after successful Google login

---

## Agent System Prompt Update

The agent now knows about Google tools:

```
📧 GOOGLE SERVICES:
- Get user profile info (get_user_info) - Returns name, email, picture, verified status
- Check calendar events (get_calendar_events) - Fetch upcoming events with optional date range
- Read latest emails (get_latest_emails) - Get inbox messages with optional Gmail query
- Search emails (search_emails) - Find specific emails by subject, sender, or content
```

---

## Example Agent Queries

### Calendar Queries
```
User: "What meetings do I have today?"
Agent: Uses get_calendar_events(days_ahead=1) to check today's schedule

User: "Show my calendar for the next week"
Agent: Uses get_calendar_events(days_ahead=7, max_results=50)

User: "Am I free at 2pm tomorrow?"
Agent: Gets calendar events and checks for conflicts at that time
```

### Email Queries
```
User: "Any new emails from my manager?"
Agent: Uses get_latest_emails(query="from:manager@company.com")

User: "Find emails about the project launch"
Agent: Uses search_emails(search_query="project launch")

User: "Show me unread messages"
Agent: Uses get_latest_emails(query="is:unread")
```

### Combined Queries
```
User: "Check if I got an email about today's meeting"
Agent: 
1. Uses get_calendar_events(days_ahead=1) to find meeting details
2. Uses search_emails() with meeting subject to find related emails
3. Correlates and reports findings
```

---

## OAuth Scopes Required

The following scopes are requested during Google login:

```typescript
const scopes = 
  "openid email profile " +
  "https://www.googleapis.com/auth/calendar.events.readonly " +
  "https://www.googleapis.com/auth/gmail.readonly";
```

- `openid email profile`: User profile (get_user_info)
- `calendar.events.readonly`: Read calendar events (get_calendar_events)
- `gmail.readonly`: Read email messages (get_latest_emails, search_emails)

---

## Error Handling

All tools return structured error responses:

```json
{
  "success": false,
  "error": "Error description",
  "details": "Detailed error message"
}
```

Common errors:
- **No access token**: User not authenticated with Google
- **Token expired**: Access token needs refresh
- **API error**: Google API returned error (quota, permissions, etc.)
- **Invalid parameters**: Tool called with bad parameters

The agent will automatically handle these errors and may:
- Request user to re-authenticate
- Inform user about permission issues
- Suggest alternative approaches

---

## Testing

### Manual Testing

1. **Start backend**: `cd himanshu && python server.py`
2. **Load extension**: Open extension in browser
3. **Sign in with Google**: Use Google OAuth (grants Calendar and Gmail access)
4. **Connect WebSocket**: Should auto-connect and send token
5. **Test agent queries**:
   - "What's on my calendar today?"
   - "Show me my latest emails"
   - "Find emails about meetings"

### Verification

Check backend logs for:
```
✅ Google access token set for client <client_id>
✅ Google access token configured for agent tools
🔧 TOOL CALLBACK TRIGGERED
Action Type: get_calendar_events
```

---

## Future Enhancements

Potential improvements:

1. **Email Composition**: Add `send_email` tool
2. **Calendar Management**: Add `create_event`, `update_event` tools
3. **Advanced Search**: More Gmail query parameters
4. **Attachments**: Download/analyze email attachments
5. **Contacts**: Access Google Contacts API
6. **Drive Integration**: Search and access Google Drive files
7. **Token Refresh**: Automatic token refresh on expiry

---

## Troubleshooting

### Token Not Set
**Symptom**: Tools return "No Google access token available"

**Solutions**:
- Ensure user logged in with Google (not GitHub)
- Check WebSocket connection established before login
- Verify `wsClient.setGoogleToken()` called after login
- Check backend logs for token reception

### API Quota Exceeded
**Symptom**: Tools return quota errors

**Solutions**:
- Use smaller `max_results` values
- Reduce agent query frequency
- Check Google Cloud Console quota limits
- Consider caching results

### Permission Denied
**Symptom**: Tools return 403 or permission errors

**Solutions**:
- Verify OAuth scopes include required permissions
- Re-authenticate with `prompt=consent` to refresh scopes
- Check Google account settings for app permissions

---

## Security Considerations

1. **Token Storage**: Access tokens stored in memory only, not persisted
2. **Token Scope**: Minimal scopes (read-only access)
3. **Token Lifetime**: Tokens expire, requiring refresh or re-auth
4. **Client-Side**: Tokens sent over WebSocket (ensure HTTPS in production)
5. **Backend**: Consider token encryption for production deployment

---

## Conclusion

The Google tools integration enables the agent to:
- ✅ Access user's Google Calendar events
- ✅ Read Gmail inbox and search messages  
- ✅ Provide intelligent scheduling assistance
- ✅ Help with email management and triage
- ✅ Correlate calendar and email data

This creates a more powerful AI assistant that can help with daily productivity tasks beyond just browser automation.
