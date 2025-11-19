// Token estimation utility for client-side monitoring
// Provides rough token estimates to warn users before hitting limits

export interface TokenEstimate {
  total: number;
  history: number;
  currentPrompt: number;
  warning: boolean;
  error: boolean;
  message?: string;
}

// Constants matching server configuration
const MAX_TOKENS = 120000;
const WARN_THRESHOLD = 100000;
const AVG_CHARS_PER_TOKEN = 4;

/**
 * Estimate tokens in a text string
 * Uses rough approximation: ~4 characters = 1 token
 */
export function estimateTokens(text: string): number {
  if (!text) return 0;
  return Math.ceil(text.length / AVG_CHARS_PER_TOKEN);
}

/**
 * Estimate tokens in conversation history
 */
export function estimateHistoryTokens(
  messages: Array<{ role: string; content: string }>
): number {
  return messages.reduce((total, msg) => {
    return total + estimateTokens(msg.content);
  }, 0);
}

/**
 * Get comprehensive token estimate for a request
 */
export function getTokenEstimate(
  currentPrompt: string,
  conversationHistory: Array<{ role: string; content: string }>
): TokenEstimate {
  const promptTokens = estimateTokens(currentPrompt);
  const historyTokens = estimateHistoryTokens(conversationHistory);

  // Add overhead for system prompts and formatting (~1000 tokens)
  const systemOverhead = 1000;

  const total = promptTokens + historyTokens + systemOverhead;

  const warning = total >= WARN_THRESHOLD;
  const error = total >= MAX_TOKENS;

  let message: string | undefined;

  if (error) {
    message = `Request would exceed token limit (${total.toLocaleString()} tokens). Try clearing conversation history or using a shorter prompt.`;
  } else if (warning) {
    message = `Approaching token limit (${total.toLocaleString()} / ${MAX_TOKENS.toLocaleString()} tokens). Consider clearing history soon.`;
  }

  return {
    total,
    history: historyTokens,
    currentPrompt: promptTokens,
    warning,
    error,
    message,
  };
}

/**
 * Format token count for display
 */
export function formatTokenCount(tokens: number): string {
  if (tokens < 1000) {
    return `${tokens} tokens`;
  }
  return `${(tokens / 1000).toFixed(1)}K tokens`;
}

/**
 * Get token usage percentage
 */
export function getTokenPercentage(tokens: number): number {
  return Math.min(100, (tokens / MAX_TOKENS) * 100);
}

/**
 * Suggest actions based on token usage
 */
export function getTokenSuggestions(estimate: TokenEstimate): string[] {
  const suggestions: string[] = [];

  if (estimate.error) {
    suggestions.push("❌ Clear conversation history immediately");
    suggestions.push("✂️ Use shorter, more specific prompts");
    suggestions.push(
      "🎯 Ask about specific page sections instead of entire pages"
    );
  } else if (estimate.warning) {
    suggestions.push("⚠️ Consider clearing history soon");
    suggestions.push("📝 Keep prompts concise");
  } else if (estimate.total > MAX_TOKENS * 0.5) {
    suggestions.push("💡 You're using over 50% of token budget");
  }

  if (estimate.history > estimate.total * 0.7) {
    suggestions.push(
      "🧹 History is using most tokens - clear to free up space"
    );
  }

  return suggestions;
}
