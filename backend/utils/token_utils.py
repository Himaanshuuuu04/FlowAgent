"""Token counting and estimation utilities"""
import tiktoken
import json
from typing import Union, List, Dict, Any

# Initialize tokenizer
try:
    tokenizer = tiktoken.encoding_for_model("gpt-4")
except:
    tokenizer = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken"""
    try:
        return len(tokenizer.encode(str(text)))
    except:
        # Fallback: rough estimate (4 chars ≈ 1 token)
        return len(str(text)) // 4


def estimate_messages_tokens(messages: List[Union[Dict, Any]]) -> int:
    """Estimate total tokens in message list"""
    total = 0
    for msg in messages:
        if isinstance(msg, dict):
            total += count_tokens(msg.get('content', ''))
        elif hasattr(msg, 'content'):
            total += count_tokens(msg.content)
        else:
            total += count_tokens(str(msg))
    return total


def estimate_json_tokens(data: Any) -> int:
    """Estimate tokens in JSON-serializable data"""
    try:
        return count_tokens(json.dumps(data))
    except:
        return count_tokens(str(data))
