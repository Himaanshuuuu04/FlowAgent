import { useState, useEffect, useRef } from "react";
import {
  Settings,
  Brain,
  Wrench,
  CheckCircle,
  XCircle,
  FileText,
  Clock,
  StopCircle,
  Camera,
  Mic,
  Plus,
  ArrowUp,
  MoreHorizontal,
  MessageSquarePlus as MessageSquare,
} from "lucide-react";
import { wsClient } from "../utils/websocket-client";
import { marked } from "marked";

interface AgentExecutorProps {
  wsConnected: boolean;
}

interface ProgressUpdate {
  status: string;
  message: string;
  timestamp?: string;
  step?: number;
  node?: string;
  tools?: string[];
  content?: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  isExecuting?: boolean;
}

export function AgentExecutor({ wsConnected }: AgentExecutorProps) {
  const [goal, setGoal] = useState("");
  const [isExecuting, setIsExecuting] = useState(false);
  const [progress, setProgress] = useState<ProgressUpdate[]>([]);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [showMentionMenu, setShowMentionMenu] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Configure marked options
  marked.setOptions({
    breaks: true,
    gfm: true,
  });

  // Load chat history from browser storage on mount
  useEffect(() => {
    const loadChatHistory = async () => {
      try {
        const result = await browser.storage.local.get("chatHistory");
        if (result.chatHistory) {
          setChatHistory(result.chatHistory);
          console.log(
            "✅ Loaded chat history from storage:",
            result.chatHistory.length,
            "messages"
          );
        }
      } catch (error) {
        console.error("Failed to load chat history:", error);
      }
    };
    loadChatHistory();
  }, []);

  // Save chat history to browser storage whenever it changes
  useEffect(() => {
    if (chatHistory.length > 0) {
      browser.storage.local
        .set({ chatHistory })
        .then(() => {
          console.log(
            "Saved chat history to storage:",
            chatHistory.length,
            "messages"
          );
        })
        .catch((error) => {
          console.error("Failed to save chat history:", error);
        });
    }
  }, [chatHistory]);

  // Auto-scroll to bottom when chat history updates
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop =
        chatContainerRef.current.scrollHeight;
    }
  }, [chatHistory, isExecuting]);

  // Render markdown to HTML
  const renderMarkdown = (markdown: string) => {
    try {
      return marked.parse(markdown);
    } catch (err) {
      console.error("Markdown parsing error:", err);
      return markdown;
    }
  };

  const formatResponseToText = (data: any): string => {
    if (typeof data === "string") return data;
    if (!data) return "Empty response received.";

    // Check common keys your backend might return
    if (data.result) return data.result;
    if (data.response) return data.response;
    if (data.answer) return data.answer;
    if (data.text) return data.text;
    if (data.output) return data.output;
    if (data.content) return data.content;

    // Fallback: Pretty print the JSON object
    return "```json\n" + JSON.stringify(data, null, 2) + "\n```";
  };

  const handleExecute = async () => {
    if (!goal.trim()) {
      setError("Please enter a goal for the agent");
      return;
    }

    if (!wsConnected) {
      setError("WebSocket not connected. Please connect first.");
      return;
    }

    // Add user message to chat history
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: goal.trim(),
      timestamp: new Date().toISOString(),
    };
    setChatHistory((prev) => [...prev, userMessage]);

    const currentGoal = goal.trim();
    setGoal(""); // Clear input immediately
    setIsExecuting(true);
    setProgress([]);
    setResult(null);
    setError(null);

    try {
      const response = await wsClient.executeAgent(
        currentGoal,
        (progressData) => {
          setProgress((prev) => [
            ...prev,
            {
              status: progressData.status,
              message: progressData.message,
              timestamp: new Date().toISOString(),
              step: progressData.step,
              node: progressData.node,
              tools: progressData.tools,
              content: progressData.content,
            },
          ]);
        }
      );

      setResult(response);

      // Add assistant response to chat history
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: formatResponseToText(response),
        timestamp: new Date().toISOString(),
      };
      setChatHistory((prev) => [...prev, assistantMessage]);

      setProgress((prev) => [
        ...prev,
        {
          status: "completed",
          message: "Agent execution completed successfully!",
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      let errorMessage = (err as Error).message;

      // Parse HTML error responses for better display
      if (
        errorMessage.includes("<!DOCTYPE html>") ||
        errorMessage.includes("<html")
      ) {
        if (errorMessage.includes("groq.com") && errorMessage.includes("500")) {
          errorMessage =
            "Groq API is currently unavailable (500 Internal Server Error). Please try again in a few minutes.";
        } else if (
          errorMessage.includes("502") ||
          errorMessage.includes("503")
        ) {
          errorMessage =
            "Service temporarily unavailable. Please try again later.";
        } else if (errorMessage.includes("429")) {
          errorMessage =
            "Rate limit exceeded. Please wait before trying again.";
        } else {
          errorMessage = "Server error occurred. Please try again later.";
        }
      }

      setError(errorMessage);

      // Add error to chat history
      setChatHistory((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: `❌ **Error:** ${errorMessage}`,
          timestamp: new Date().toISOString(),
        },
      ]);

      setProgress((prev) => [
        ...prev,
        {
          status: "error",
          message: `Error: ${errorMessage}`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleStop = async () => {
    try {
      await wsClient.stopAgent();
      setIsExecuting(false);
      setError("Agent execution stopped by user");
    } catch (err: any) {
      console.error("Failed to stop agent:", err);
      setError(err.message || "Failed to stop agent");
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setGoal(value);
    if (value.endsWith("@")) setShowMentionMenu(true);
    else setShowMentionMenu(false);
  };

  const handleMentionSelect = (action: string) => {
    // Remove the @ and add the selected action
    const newGoal = goal.slice(0, -1) + action;
    setGoal(newGoal);
    setShowMentionMenu(false);
  };

  const handleNewChat = async () => {
    try {
      // Clear chat history from state
      setChatHistory([]);
      // Clear from browser storage
      await browser.storage.local.remove("chatHistory");
      // Reset other state
      setProgress([]);
      setResult(null);
      setError(null);
      console.log("Chat history cleared - starting new conversation");
    } catch (error) {
      console.error("Failed to clear chat history:", error);
    }
  };

  const getStatusIcon = (status: string) => {
    const iconProps = { size: 14, strokeWidth: 2.5 };
    switch (status) {
      case "initializing":
        return <Settings {...iconProps} />;
      case "planning":
        return <Brain {...iconProps} />;
      case "executing":
      case "tool_calling":
        return <Wrench {...iconProps} />;
      case "responding":
        return <FileText {...iconProps} />;
      case "completed":
        return <CheckCircle {...iconProps} />;
      case "error":
        return <XCircle {...iconProps} />;
      default:
        return <FileText {...iconProps} />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "initializing":
        return "#60a5fa";
      case "planning":
        return "#a78bfa";
      case "executing":
        return "#fbbf24";
      case "tool_calling":
        return "#f97316";
      case "responding":
        return "#22d3ee";
      case "completed":
        return "#34d399";
      case "error":
        return "#f87171";
      default:
        return "#9ca3af";
    }
  };

  const exampleGoals = [
    "Open a new tab and search for 'AI news'",
    "Fill out the login form with test@example.com",
    "Take a screenshot of the current page",
    "Click all buttons with class 'submit'",
    "Extract all links from the current page",
  ];

  return (
    <div className="agent-executor-fixed">
      {/* WebSocket Connection Warning */}
      {!wsConnected && (
        <div
          style={{
            padding: "8px 12px",
            fontSize: "11px",
            color: "#f87171",
            backgroundColor: "#2a1414",
            borderBottom: "1px solid #3f1f1f",
            textAlign: "center",
            fontWeight: 500,
          }}
        >
          ⚠️ WebSocket not connected - Please connect in settings
        </div>
      )}

      {/* Chat Messages Area */}
      <div
        ref={chatContainerRef}
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px",
          backgroundColor: "#0a0a0a",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        {chatHistory.length === 0 ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "#666",
              fontSize: "13px",
              textAlign: "center",
              padding: "60px 20px 40px 20px",
              flexDirection: "column",
              gap: "48px",
            }}
          >
            {/* Mention Tabs Card */}
            <div
              style={{
                position: "relative",
                transform: "rotate(-5deg)",
              }}
            >
              <div
                style={{
                  padding: "16px 20px",
                  background:
                    "linear-gradient(145deg, rgba(35, 35, 40, 0.95), rgba(25, 25, 30, 0.95))",
                  border: "1px solid rgba(70, 70, 80, 0.5)",
                  borderRadius: "14px",
                  backdropFilter: "blur(12px)",
                  boxShadow: "0 10px 40px rgba(0, 0, 0, 0.5)",
                  minWidth: "280px",
                  maxWidth: "280px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    marginBottom: "10px",
                  }}
                >
                  <div
                    style={{
                      width: "28px",
                      height: "28px",
                      borderRadius: "50%",
                      background: "linear-gradient(135deg, #4f46e5, #7c3aed)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    <MessageSquare size={16} strokeWidth={2.5} color="#fff" />
                  </div>
                  <span
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: "#f5f5f5",
                    }}
                  >
                    Mention Tabs
                  </span>
                </div>
                <p
                  style={{
                    margin: 0,
                    fontSize: "11.5px",
                    color: "#a0a0a0",
                    lineHeight: "1.5",
                  }}
                >
                  Should I buy{" "}
                  <span style={{ color: "#6b7cff" }}>Multicolor Titanium</span>{" "}
                  or{" "}
                  <span
                    style={{ color: "#6b7cff", textDecoration: "underline" }}
                  >
                    ACTIVE TU...
                  </span>
                </p>
              </div>
            </div>

            {/* Main Text */}
            <div style={{ maxWidth: "320px" }}>
              <h3
                style={{
                  margin: "0 0 10px 0",
                  color: "#f5f5f5",
                  fontSize: "19px",
                  fontWeight: 600,
                  letterSpacing: "-0.3px",
                }}
              >
                Mention tabs to add context
              </h3>
              <p
                style={{
                  margin: "0",
                  fontSize: "13px",
                  color: "#777",
                  lineHeight: "1.5",
                }}
              >
                Type @ to mention a tab
              </p>
            </div>
          </div>
        ) : (
          <>
            {chatHistory.map((message, index) => (
              <div
                key={message.id}
                style={{
                  display: "flex",
                  gap: "12px",
                  alignItems: "flex-start",
                  flexDirection: "row",
                  justifyContent:
                    message.role === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    maxWidth: "75%",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      gap: "8px",
                      alignItems: "center",
                      marginBottom: "6px",
                      justifyContent:
                        message.role === "user" ? "flex-end" : "flex-start",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 600,
                        color: "#888",
                        textTransform: "uppercase",
                        letterSpacing: "0.5px",
                      }}
                    >
                      {message.role === "user" ? "YOU" : "ASSISTANT"}
                    </span>
                    <span
                      style={{
                        fontSize: "10px",
                        color: "#666",
                      }}
                    >
                      {new Date(message.timestamp).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </span>
                  </div>

                  <div
                    style={{
                      padding: "14px 18px",
                      borderRadius: "16px",
                      background:
                        message.role === "user"
                          ? "linear-gradient(135deg, rgba(30, 35, 60, 0.9), rgba(25, 30, 50, 0.95))"
                          : "linear-gradient(135deg, rgba(35, 35, 40, 0.8), rgba(30, 30, 35, 0.85))",
                      border:
                        message.role === "user"
                          ? "1px solid rgba(50, 60, 90, 0.6)"
                          : "1px solid rgba(55, 55, 60, 0.5)",
                      fontSize: "13.5px",
                      lineHeight: "1.6",
                      color: "#e8e8e8",
                      wordBreak: "break-word",
                    }}
                  >
                    <div
                      className="markdown-content"
                      dangerouslySetInnerHTML={{
                        __html: renderMarkdown(message.content),
                      }}
                    />
                  </div>

                  {/* Show progress for the latest assistant message if executing */}
                  {message.role === "assistant" &&
                    index === chatHistory.length - 1 &&
                    isExecuting &&
                    progress.length > 0 && (
                      <div
                        style={{
                          marginTop: "8px",
                          padding: "8px 12px",
                          background: "rgba(20, 20, 20, 0.5)",
                          border: "1px solid rgba(55, 55, 55, 0.3)",
                          borderRadius: "8px",
                          fontSize: "11px",
                        }}
                      >
                        {progress.slice(-3).map((update, i) => (
                          <div
                            key={i}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "8px",
                              marginBottom: i < 2 ? "4px" : "0",
                              opacity: i === 2 ? 1 : 0.5,
                            }}
                          >
                            <span
                              style={{ color: getStatusColor(update.status) }}
                            >
                              {getStatusIcon(update.status)}
                            </span>
                            <span style={{ color: "#aaa", flex: 1 }}>
                              {update.message}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                </div>
              </div>
            ))}

            {/* Typing Indicator */}
            {isExecuting && (
              <div
                style={{
                  display: "flex",
                  gap: "12px",
                  alignItems: "flex-start",
                  justifyContent: "flex-start",
                }}
              >
                <div
                  style={{
                    padding: "12px 18px",
                    borderRadius: "16px",
                    background:
                      "linear-gradient(135deg, rgba(35, 35, 40, 0.8), rgba(30, 30, 35, 0.85))",
                    border: "1px solid rgba(55, 55, 60, 0.5)",
                    display: "flex",
                    gap: "5px",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      width: "7px",
                      height: "7px",
                      borderRadius: "50%",
                      backgroundColor: "#888",
                      animation: "bounce 1.4s infinite ease-in-out",
                      animationDelay: "0s",
                    }}
                  />
                  <span
                    style={{
                      width: "7px",
                      height: "7px",
                      borderRadius: "50%",
                      backgroundColor: "#888",
                      animation: "bounce 1.4s infinite ease-in-out",
                      animationDelay: "0.2s",
                    }}
                  />
                  <span
                    style={{
                      width: "7px",
                      height: "7px",
                      borderRadius: "50%",
                      backgroundColor: "#888",
                      animation: "bounce 1.4s infinite ease-in-out",
                      animationDelay: "0.4s",
                    }}
                  />
                </div>
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div
                style={{
                  padding: "12px 16px",
                  background: "rgba(127, 29, 29, 0.2)",
                  border: "1px solid rgba(248, 113, 113, 0.3)",
                  borderRadius: "8px",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "8px",
                }}
              >
                <XCircle
                  size={16}
                  strokeWidth={2}
                  style={{ color: "#f87171", flexShrink: 0, marginTop: "2px" }}
                />
                <span
                  style={{
                    fontSize: "12px",
                    color: "#f87171",
                    lineHeight: "1.5",
                  }}
                >
                  {error}
                </span>
              </div>
            )}
          </>
        )}
      </div>

      {/* Quick Actions Pills - Moved to bottom before composer */}
      <div
        style={{
          padding: "10px 12px",
          backgroundColor: "#0a0a0a",
          display: "flex",
          gap: "6px",
          overflowX: "auto",
          borderBottom: "1px solid #151515",
        }}
      >
        <button
          onClick={handleNewChat}
          disabled={isExecuting}
          style={{
            padding: "7px 13px",
            fontSize: "11.5px",
            fontWeight: 500,
            color: "#d5d5d5",
            background: "rgba(40, 40, 45, 0.7)",
            border: "1px solid rgba(65, 65, 70, 0.5)",
            borderRadius: "18px",
            cursor: isExecuting ? "not-allowed" : "pointer",
            whiteSpace: "nowrap",
            opacity: isExecuting ? 0.5 : 1,
            transition: "all 0.15s",
            display: "flex",
            alignItems: "center",
            gap: "5px",
          }}
        >
          <Plus size={13} strokeWidth={2.5} />
          New Chat
        </button>
        <button
          onClick={() => setGoal("Summarize this page")}
          disabled={isExecuting}
          style={{
            padding: "7px 13px",
            fontSize: "11.5px",
            fontWeight: 500,
            color: "#a0a0a0",
            background: "rgba(30, 30, 35, 0.5)",
            border: "1px solid rgba(55, 55, 60, 0.4)",
            borderRadius: "18px",
            cursor: isExecuting ? "not-allowed" : "pointer",
            whiteSpace: "nowrap",
            opacity: isExecuting ? 0.5 : 1,
            transition: "all 0.15s",
          }}
        >
          Summarize
        </button>
        <button
          onClick={() => setGoal("Explain this page in simple terms")}
          disabled={isExecuting}
          style={{
            padding: "7px 13px",
            fontSize: "11.5px",
            fontWeight: 500,
            color: "#a0a0a0",
            background: "rgba(30, 30, 35, 0.5)",
            border: "1px solid rgba(55, 55, 60, 0.4)",
            borderRadius: "18px",
            cursor: isExecuting ? "not-allowed" : "pointer",
            whiteSpace: "nowrap",
            opacity: isExecuting ? 0.5 : 1,
            transition: "all 0.15s",
          }}
        >
          Explain
        </button>
        <button
          onClick={() => setGoal("Analyze the structure of this page")}
          disabled={isExecuting}
          style={{
            padding: "7px 13px",
            fontSize: "11.5px",
            fontWeight: 500,
            color: "#a0a0a0",
            background: "rgba(30, 30, 35, 0.5)",
            border: "1px solid rgba(55, 55, 60, 0.4)",
            borderRadius: "18px",
            cursor: isExecuting ? "not-allowed" : "pointer",
            whiteSpace: "nowrap",
            opacity: isExecuting ? 0.5 : 1,
            transition: "all 0.15s",
          }}
        >
          Analyze
        </button>
      </div>

      {/* Composer */}
      <div
        style={{
          padding: "12px 12px 14px 12px",
          backgroundColor: "#0a0a0a",
          position: "relative",
        }}
      >
        {/* Mention Menu */}
        {showMentionMenu && (
          <div
            style={{
              position: "absolute",
              bottom: "100%",
              left: "16px",
              marginBottom: "8px",
              background:
                "linear-gradient(135deg, rgba(25, 25, 30, 0.98), rgba(30, 30, 35, 0.98))",
              border: "1px solid rgba(60, 60, 65, 0.6)",
              borderRadius: "12px",
              padding: "8px",
              boxShadow: "0 8px 24px rgba(0, 0, 0, 0.6)",
              backdropFilter: "blur(20px)",
              zIndex: 100,
              minWidth: "200px",
            }}
          >
            <div
              style={{
                fontSize: "10px",
                color: "#666",
                marginBottom: "8px",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.5px",
              }}
            >
              Quick Actions
            </div>
            {["Summarize", "Explain", "Analyze", "Extract data"].map(
              (action) => (
                <button
                  key={action}
                  onClick={() => handleMentionSelect(action)}
                  style={{
                    display: "block",
                    width: "100%",
                    padding: "8px 12px",
                    fontSize: "12px",
                    color: "#e5e5e5",
                    background: "transparent",
                    border: "none",
                    borderRadius: "6px",
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "background 0.2s",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background =
                      "rgba(59, 130, 246, 0.15)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "transparent";
                  }}
                >
                  {action}
                </button>
              )
            )}
          </div>
        )}

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "9px 12px",
            background: "rgba(23, 23, 28, 0.95)",
            border: "1px solid rgba(50, 50, 55, 0.5)",
            borderRadius: "22px",
          }}
        >
          <button
            disabled={isExecuting}
            style={{
              padding: "5px",
              background: "transparent",
              border: "none",
              color: "#808080",
              cursor: isExecuting ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              opacity: isExecuting ? 0.3 : 1,
            }}
          >
            <Plus size={19} strokeWidth={2} />
          </button>

          <button
            disabled={isExecuting}
            style={{
              padding: "5px",
              background: "transparent",
              border: "none",
              color: "#808080",
              cursor: isExecuting ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              opacity: isExecuting ? 0.3 : 1,
            }}
          >
            <MoreHorizontal size={19} strokeWidth={2} />
          </button>

          <input
            type="text"
            value={goal}
            onChange={handleInputChange}
            onKeyDown={(e) => {
              if (
                e.key === "Enter" &&
                !e.shiftKey &&
                !isExecuting &&
                wsConnected
              ) {
                e.preventDefault();
                handleExecute();
              }
            }}
            placeholder="Ask a question about this page..."
            disabled={isExecuting}
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              color: "#e5e5e5",
              fontSize: "12.5px",
              padding: "5px 4px",
            }}
          />

          <button
            disabled={isExecuting}
            style={{
              padding: "5px",
              background: "transparent",
              border: "none",
              color: "#808080",
              cursor: isExecuting ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              opacity: isExecuting ? 0.3 : 1,
            }}
          >
            <Camera size={19} strokeWidth={2} />
          </button>

          <button
            disabled={isExecuting}
            style={{
              padding: "5px",
              background: "transparent",
              border: "none",
              color: "#808080",
              cursor: isExecuting ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              opacity: isExecuting ? 0.3 : 1,
            }}
          >
            <Mic size={19} strokeWidth={2} />
          </button>

          {isExecuting ? (
            <button
              onClick={handleStop}
              style={{
                padding: "9px",
                background: "linear-gradient(135deg, #991b1b, #b91c1c)",
                border: "none",
                borderRadius: "50%",
                color: "#fff",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "all 0.2s",
                width: "34px",
                height: "34px",
              }}
            >
              <StopCircle size={17} strokeWidth={2.5} />
            </button>
          ) : (
            <button
              onClick={handleExecute}
              disabled={!wsConnected || !goal.trim()}
              style={{
                padding: "9px",
                background:
                  wsConnected && goal.trim()
                    ? "linear-gradient(135deg, #4f46e5, #7c3aed)"
                    : "rgba(60, 60, 65, 0.5)",
                border: "none",
                borderRadius: "50%",
                color: "#fff",
                cursor: wsConnected && goal.trim() ? "pointer" : "not-allowed",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "all 0.2s",
                opacity: wsConnected && goal.trim() ? 1 : 0.5,
                width: "34px",
                height: "34px",
              }}
            >
              <ArrowUp size={17} strokeWidth={2.5} />
            </button>
          )}
        </div>
      </div>

      <style>{`
        .agent-executor-fixed {
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          padding: 0;
          background-color: #0a0a0a;
          box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.5);
          z-index: 1000;
          border-top: 1px solid #1f1f1f;
          height: calc(100vh - 52px);
          max-height: calc(100vh - 52px);
          display: flex;
          flex-direction: column;
        }

        .agent-executor-fixed > div:nth-child(2)::-webkit-scrollbar {
          width: 6px;
        }

        .agent-executor-fixed > div:nth-child(2)::-webkit-scrollbar-track {
          background: transparent;
        }

        .agent-executor-fixed > div:nth-child(2)::-webkit-scrollbar-thumb {
          background: #2a2a2a;
          border-radius: 3px;
        }

        .agent-executor-fixed > div:nth-child(2)::-webkit-scrollbar-thumb:hover {
          background: #3a3a3a;
        }

        @keyframes bounce {
          0%, 80%, 100% {
            transform: translateY(0);
            opacity: 0.5;
          }
          40% {
            transform: translateY(-8px);
            opacity: 1;
          }
        }

        .markdown-content {
          font-size: 13px;
          line-height: 1.6;
        }

        .markdown-content p {
          margin: 0 0 8px 0;
        }

        .markdown-content p:last-child {
          margin-bottom: 0;
        }

        .markdown-content code {
          background: rgba(0, 0, 0, 0.3);
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 12px;
          font-family: 'Courier New', monospace;
        }

        .markdown-content pre {
          background: rgba(0, 0, 0, 0.4);
          padding: 12px;
          border-radius: 6px;
          overflow-x: auto;
          margin: 8px 0;
        }

        .markdown-content pre code {
          background: none;
          padding: 0;
        }

        .markdown-content ul,
        .markdown-content ol {
          margin: 8px 0;
          padding-left: 24px;
        }

        .markdown-content li {
          margin: 4px 0;
        }

        .markdown-content h1,
        .markdown-content h2,
        .markdown-content h3,
        .markdown-content h4 {
          margin: 12px 0 8px 0;
          font-weight: 600;
        }

        .markdown-content a {
          color: #3b82f6;
          text-decoration: none;
        }

        .markdown-content a:hover {
          text-decoration: underline;
        }
      `}</style>
    </div>
  );
}
