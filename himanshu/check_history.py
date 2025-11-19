#!/usr/bin/env python3
"""
Quick script to check conversation history in the database
"""

from conversation_db import get_conversation_db
import json

# Initialize database
db = get_conversation_db()

print("\n" + "="*60)
print("📊 CONVERSATION HISTORY DATABASE CHECK")
print("="*60 + "\n")

# Get all clients
clients = db.get_all_clients()
print(f"Total clients with history: {len(clients)}\n")

if not clients:
    print("⚠️  No conversation history found yet.")
    print("   Start the server and have a conversation with the agent.\n")
else:
    for client_id in clients:
        print(f"\n{'='*60}")
        print(f"Client: {client_id}")
        print("="*60)
        
        # Get stats
        stats = db.get_client_stats(client_id)
        print(f"\n📈 Statistics:")
        print(f"   Total messages: {stats.get('total_messages', 0)}")
        print(f"   By role: {stats.get('by_role', {})}")
        print(f"   First message: {stats.get('first_message', 'N/A')}")
        print(f"   Last message: {stats.get('last_message', 'N/A')}")
        
        # Get recent history
        history = db.get_history(client_id, limit=10)
        print(f"\n💬 Last {len(history)} messages:")
        
        for i, msg in enumerate(history, 1):
            role = msg['role']
            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            timestamp = msg.get('timestamp', 'N/A')
            
            emoji = "👤" if role == "user" else "🤖"
            print(f"\n   {i}. {emoji} {role.upper()} [{timestamp}]")
            print(f"      {content}")

print("\n" + "="*60)
print("✅ Database check complete!")
print("="*60 + "\n")
