"""Application configuration constants"""

# =================================================================
# CONTEXT OPTIMIZATION CONFIGURATION
# =================================================================

# Conversation history limits
MAX_HISTORY_MESSAGES = 10  # Maximum messages to send to API (5 user + 5 assistant)
MEMORY_MESSAGES = 30  # Total messages to keep in memory/database

# Token limits and warnings
MAX_TOKENS_PER_REQUEST = 120000  # Reduced from model limit for safety buffer
WARN_TOKENS_THRESHOLD = 100000  # Warn user when approaching limit

# Enable/disable optimizations
ENABLE_HISTORY_TRIMMING = True
ENABLE_TOKEN_COUNTING = True

# OAuth credentials (loaded from environment)
CLIENT_ID = "95116700360-13ege5jmfrjjt4vmd86oh00eu5jlei5e.apps.googleusercontent.com"
