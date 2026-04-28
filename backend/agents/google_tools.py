"""
Google API Tools for Agent
Provides access to Gmail and Google Calendar
"""

from langchain_core.tools import tool
import requests
import datetime
import json
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Store the access token globally (will be set by the agent when user authenticates)
_google_access_token = None

def set_google_access_token(token: str):
    """Set the Google access token for API calls"""
    global _google_access_token
    _google_access_token = token
    logger.info("✅ Google access token set successfully")

def get_access_token() -> Optional[str]:
    """Get the current Google access token"""
    return _google_access_token


@tool
def get_user_info() -> str:
    """
    Get the authenticated user's Google profile information.
    
    Returns:
        JSON string with user's name, email, and profile picture
        
    Use this to verify who is authenticated or get user details.
    """
    if not _google_access_token:
        return json.dumps({
            "success": False, 
            "error": "Not authenticated. User needs to sign in with Google first."
        })
    
    try:
        url = "https://openidconnect.googleapis.com/v1/userinfo"
        headers = {"Authorization": f"Bearer {_google_access_token}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return json.dumps({
                "success": False,
                "error": f"Failed to get user info: {response.status_code}"
            })
        
        user_info = response.json()
        return json.dumps({
            "success": True,
            "name": user_info.get("name"),
            "email": user_info.get("email"),
            "picture": user_info.get("picture"),
            "verified_email": user_info.get("verified_email")
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        return json.dumps({"success": False, "error": str(e)})


@tool
def get_calendar_events(max_results: int = 10, days_ahead: Optional[int] = None) -> str:
    """
    Fetch upcoming Google Calendar events.
    
    Args:
        max_results: Maximum number of events to return (default: 10, max: 50)
        days_ahead: Only get events within this many days (optional)
        
    Returns:
        JSON string with list of upcoming events including title, time, location, description
        
    Use this to check user's schedule, upcoming meetings, or availability.
    """
    if not _google_access_token:
        return json.dumps({
            "success": False,
            "error": "Not authenticated. User needs to sign in with Google first."
        })
    
    try:
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        headers = {"Authorization": f"Bearer {_google_access_token}"}
        
        # Limit max_results to reasonable bounds
        max_results = min(max(1, max_results), 50)
        
        time_min = datetime.datetime.utcnow()
        params = {
            "maxResults": max_results,
            "orderBy": "startTime",
            "singleEvents": True,
            "timeMin": time_min.isoformat() + "Z"
        }
        
        # Add time_max if days_ahead is specified
        if days_ahead:
            time_max = time_min + datetime.timedelta(days=days_ahead)
            params["timeMax"] = time_max.isoformat() + "Z"
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code != 200:
            return json.dumps({
                "success": False,
                "error": f"Failed to get calendar events: {response.status_code}"
            })
        
        events = response.json().get("items", [])
        
        formatted_events = []
        for event in events:
            start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
            end = event.get("end", {}).get("dateTime") or event.get("end", {}).get("date")
            
            formatted_events.append({
                "id": event.get("id"),
                "summary": event.get("summary", "No title"),
                "start": start,
                "end": end,
                "location": event.get("location"),
                "description": event.get("description"),
                "attendees": [a.get("email") for a in event.get("attendees", [])],
                "status": event.get("status")
            })
        
        return json.dumps({
            "success": True,
            "count": len(formatted_events),
            "events": formatted_events
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting calendar events: {e}")
        return json.dumps({"success": False, "error": str(e)})


def _fetch_emails_impl(max_results: int = 5, query: Optional[str] = None) -> str:
    """Internal implementation for fetching emails"""
    if not _google_access_token:
        return json.dumps({
            "success": False,
            "error": "Not authenticated. User needs to sign in with Google first."
        })
    
    try:
        base_url = "https://gmail.googleapis.com/gmail/v1/users/me"
        headers = {"Authorization": f"Bearer {_google_access_token}"}
        
        # Limit max_results to reasonable bounds
        max_results = min(max(1, max_results), 20)
        
        # Build query - default to inbox if no query provided
        search_query = query if query else "is:inbox"
        
        # Step 1: Get message IDs
        params = {
            "maxResults": max_results,
            "labelIds": ["INBOX"],
            "q": search_query
        }
        response = requests.get(f"{base_url}/messages", headers=headers, params=params, timeout=10)
        
        if response.status_code != 200:
            return json.dumps({
                "success": False,
                "error": f"Failed to list messages: {response.status_code}"
            })
        
        messages = response.json().get("messages", [])
        if not messages:
            return json.dumps({
                "success": True,
                "count": 0,
                "emails": [],
                "message": "No emails found matching the criteria"
            })
        
        emails = []
        # Step 2: Fetch each message's details
        for msg in messages:
            msg_id = msg["id"]
            msg_response = requests.get(f"{base_url}/messages/{msg_id}", headers=headers, timeout=10)
            
            if msg_response.status_code != 200:
                continue
            
            msg_data = msg_response.json()
            headers_list = msg_data.get("payload", {}).get("headers", [])
            
            email_info = {
                "id": msg_id,
                "threadId": msg_data.get("threadId")
            }
            
            # Extract important headers
            for h in headers_list:
                name = h["name"].lower()
                if name == "subject":
                    email_info["subject"] = h["value"]
                elif name == "from":
                    email_info["from"] = h["value"]
                elif name == "date":
                    email_info["date"] = h["value"]
                elif name == "to":
                    email_info["to"] = h["value"]
            
            email_info["snippet"] = msg_data.get("snippet", "")
            email_info["labels"] = msg_data.get("labelIds", [])
            
            emails.append(email_info)
        
        return json.dumps({
            "success": True,
            "count": len(emails),
            "query": search_query,
            "emails": emails
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting emails: {e}")
        return json.dumps({"success": False, "error": str(e)})


@tool
def get_latest_emails(max_results: int = 5, query: Optional[str] = None) -> str:
    """
    Fetch latest emails from Gmail inbox.
    
    Args:
        max_results: Maximum number of emails to return (default: 5, max: 20)
        query: Optional Gmail search query (e.g., "from:someone@example.com", "subject:urgent")
        
    Returns:
        JSON string with list of emails including subject, from, date, and snippet
        
    Use this to check recent emails, search for specific messages, or get inbox overview.
    """
    return _fetch_emails_impl(max_results=max_results, query=query)


@tool
def search_emails(search_query: str, max_results: int = 10) -> str:
    """
    Search Gmail with a specific query.
    
    Args:
        search_query: Gmail search query (e.g., "from:boss@company.com", "subject:meeting", "is:unread")
        max_results: Maximum number of results (default: 10, max: 20)
        
    Returns:
        JSON string with matching emails
        
    Common query examples:
    - "is:unread" - Unread emails
    - "from:email@example.com" - Emails from specific sender
    - "subject:urgent" - Emails with "urgent" in subject
    - "has:attachment" - Emails with attachments
    - "after:2024/01/01" - Emails after specific date
    """
    return _fetch_emails_impl(max_results=max_results, query=search_query)


# Export all tools
google_tools = [
    get_user_info,
    get_calendar_events,
    get_latest_emails,
    search_emails
]
