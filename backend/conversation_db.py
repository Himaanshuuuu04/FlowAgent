"""
Conversation History Database Manager
Handles persistent storage of agent conversations using SQLite
"""

import sqlite3
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class ConversationDB:
    """Manages conversation history in SQLite database"""
    
    def __init__(self, db_path: str = "data/conversations.db"):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._init_db()
        logger.info(f"✅ Conversation database initialized: {db_path}")
    
    def _init_db(self):
        """Create tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    metadata TEXT
                )
            """)
            
            # Create index for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_client_timestamp 
                ON conversations(client_id, timestamp)
            """)
            
            # Sessions table (optional - tracks conversation sessions)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0
                )
            """)
            
            conn.commit()
    
    def add_message(self, client_id: str, role: str, content: str, 
                    session_id: Optional[str] = None, metadata: Optional[Dict] = None):
        """
        Add a message to conversation history
        
        Args:
            client_id: Unique identifier for the client
            role: Message role ('user' or 'assistant')
            content: Message content
            session_id: Optional session identifier
            metadata: Optional metadata dictionary
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                metadata_json = json.dumps(metadata) if metadata else None
                
                cursor.execute("""
                    INSERT INTO conversations (client_id, role, content, session_id, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (client_id, role, content, session_id, metadata_json))
                
                conn.commit()
                logger.debug(f"Added {role} message for client {client_id[:8]}...")
                
        except Exception as e:
            logger.error(f"Error adding message to database: {e}")
    
    def get_history(self, client_id: str, limit: int = 20, 
                   session_id: Optional[str] = None) -> List[Dict]:
        """
        Get conversation history for a client
        
        Args:
            client_id: Unique identifier for the client
            limit: Maximum number of messages to retrieve
            session_id: Optional session filter
            
        Returns:
            List of message dictionaries with role and content
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if session_id:
                    cursor.execute("""
                        SELECT role, content, timestamp, metadata
                        FROM conversations
                        WHERE client_id = ? AND session_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (client_id, session_id, limit))
                else:
                    cursor.execute("""
                        SELECT role, content, timestamp, metadata
                        FROM conversations
                        WHERE client_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (client_id, limit))
                
                rows = cursor.fetchall()
                
                # Reverse to get chronological order (oldest first)
                messages = []
                for row in reversed(rows):
                    message = {
                        "role": row[0],
                        "content": row[1],
                        "timestamp": row[2]
                    }
                    if row[3]:
                        message["metadata"] = json.loads(row[3])
                    messages.append(message)
                
                logger.debug(f"Retrieved {len(messages)} messages for client {client_id[:8]}...")
                return messages
                
        except Exception as e:
            logger.error(f"Error retrieving history from database: {e}")
            return []
    
    def clear_history(self, client_id: str, session_id: Optional[str] = None):
        """
        Clear conversation history for a client
        
        Args:
            client_id: Unique identifier for the client
            session_id: Optional session filter
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if session_id:
                    cursor.execute("""
                        DELETE FROM conversations
                        WHERE client_id = ? AND session_id = ?
                    """, (client_id, session_id))
                else:
                    cursor.execute("""
                        DELETE FROM conversations
                        WHERE client_id = ?
                    """, (client_id,))
                
                deleted = cursor.rowcount
                conn.commit()
                logger.info(f"Cleared {deleted} messages for client {client_id[:8]}...")
                
        except Exception as e:
            logger.error(f"Error clearing history from database: {e}")
    
    def get_client_stats(self, client_id: str) -> Dict:
        """
        Get statistics for a client's conversation history
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            Dictionary with statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total messages
                cursor.execute("""
                    SELECT COUNT(*) FROM conversations WHERE client_id = ?
                """, (client_id,))
                total = cursor.fetchone()[0]
                
                # Messages by role
                cursor.execute("""
                    SELECT role, COUNT(*) FROM conversations 
                    WHERE client_id = ? 
                    GROUP BY role
                """, (client_id,))
                by_role = dict(cursor.fetchall())
                
                # First and last message timestamps
                cursor.execute("""
                    SELECT MIN(timestamp), MAX(timestamp) 
                    FROM conversations 
                    WHERE client_id = ?
                """, (client_id,))
                first, last = cursor.fetchone()
                
                return {
                    "total_messages": total,
                    "by_role": by_role,
                    "first_message": first,
                    "last_message": last
                }
                
        except Exception as e:
            logger.error(f"Error getting client stats: {e}")
            return {}
    
    def cleanup_old_conversations(self, days: int = 30):
        """
        Remove conversations older than specified days
        
        Args:
            days: Number of days to keep
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM conversations
                    WHERE timestamp < datetime('now', '-' || ? || ' days')
                """, (days,))
                
                deleted = cursor.rowcount
                conn.commit()
                
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} old messages (>{days} days)")
                
        except Exception as e:
            logger.error(f"Error cleaning up old conversations: {e}")
    
    def get_all_clients(self) -> List[str]:
        """
        Get list of all client IDs with conversation history
        
        Returns:
            List of client IDs
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT DISTINCT client_id FROM conversations
                """)
                
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting all clients: {e}")
            return []
    
    def export_conversation(self, client_id: str, output_file: str):
        """
        Export conversation history to JSON file
        
        Args:
            client_id: Unique identifier for the client
            output_file: Path to output JSON file
        """
        try:
            history = self.get_history(client_id, limit=1000)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "client_id": client_id,
                    "exported_at": datetime.now().isoformat(),
                    "message_count": len(history),
                    "messages": history
                }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(history)} messages to {output_file}")
            
        except Exception as e:
            logger.error(f"Error exporting conversation: {e}")
    
    def close(self):
        """Close database connection (for cleanup)"""
        # SQLite connections are closed automatically with context manager
        pass


# Global database instance
_db_instance = None


def get_conversation_db(db_path: str = "data/conversations.db") -> ConversationDB:
    """
    Get or create global database instance (singleton pattern)
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        ConversationDB instance
    """
    global _db_instance
    
    if _db_instance is None:
        _db_instance = ConversationDB(db_path)
    
    return _db_instance
