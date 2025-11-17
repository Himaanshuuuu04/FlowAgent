import { useState } from "react";
import { wsClient } from "../utils/websocket-client";

interface AgentExecutorProps {
  wsConnected: boolean;
}

interface ProgressUpdate {
  status: string;
  message: string;
  timestamp?: string;
}

export function AgentExecutor({ wsConnected }: AgentExecutorProps) {
  const [goal, setGoal] = useState("");
  const [isExecuting, setIsExecuting] = useState(false);
  const [progress, setProgress] = useState<ProgressUpdate[]>([]);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleExecute = async () => {
    if (!goal.trim()) {
      setError("Please enter a goal for the agent");
      return;
    }

    if (!wsConnected) {
      setError("WebSocket not connected. Please connect first.");
      return;
    }

    setIsExecuting(true);
    setProgress([]);
    setResult(null);
    setError(null);

    try {
      const response = await wsClient.executeAgent(goal, (progressData) => {
        setProgress((prev) => [
          ...prev,
          {
            status: progressData.status,
            message: progressData.message,
            timestamp: new Date().toISOString(),
          },
        ]);
      });

      setResult(response);
      setProgress((prev) => [
        ...prev,
        {
          status: "completed",
          message: "✅ Agent execution completed successfully!",
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      const errorMessage = (err as Error).message;
      setError(errorMessage);
      setProgress((prev) => [
        ...prev,
        {
          status: "error",
          message: `❌ Error: ${errorMessage}`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsExecuting(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "initializing":
        return "⚙️";
      case "planning":
        return "🧠";
      case "executing":
        return "🔧";
      case "completed":
        return "✅";
      case "error":
        return "❌";
      default:
        return "📝";
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
    <div className="agent-executor">
      <div className="section-header">
        <h3>🤖 AI Agent Executor</h3>
        <p className="section-description">
          Natural language browser automation with sophisticated tools
        </p>
      </div>

      <div className="agent-input-section">
        <label htmlFor="agent-goal">What should the agent do?</label>
        <textarea
          id="agent-goal"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="Example: Open Gmail, find the first unread email, and reply with 'Thanks!'"
          rows={4}
          disabled={isExecuting}
          style={{
            width: "100%",
            padding: "12px",
            borderRadius: "8px",
            border: "1px solid #374151",
            backgroundColor: "#1f2937",
            color: "#f3f4f6",
            fontSize: "14px",
            resize: "vertical",
            fontFamily: "inherit",
          }}
        />

        <div className="example-goals">
          <p
            style={{ fontSize: "12px", color: "#9ca3af", marginBottom: "8px" }}
          >
            Try these examples:
          </p>
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "8px",
            }}
          >
            {exampleGoals.map((example, index) => (
              <button
                key={index}
                onClick={() => setGoal(example)}
                disabled={isExecuting}
                style={{
                  padding: "6px 12px",
                  fontSize: "12px",
                  backgroundColor: "#374151",
                  border: "1px solid #4b5563",
                  borderRadius: "6px",
                  color: "#d1d5db",
                  cursor: isExecuting ? "not-allowed" : "pointer",
                  transition: "all 0.2s",
                }}
                onMouseEnter={(e) => {
                  if (!isExecuting) {
                    e.currentTarget.style.backgroundColor = "#4b5563";
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = "#374151";
                }}
              >
                {example}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleExecute}
          disabled={isExecuting || !wsConnected}
          style={{
            width: "100%",
            padding: "12px",
            marginTop: "12px",
            backgroundColor: isExecuting
              ? "#4b5563"
              : wsConnected
              ? "#3b82f6"
              : "#6b7280",
            color: "white",
            border: "none",
            borderRadius: "8px",
            fontSize: "14px",
            fontWeight: "600",
            cursor: isExecuting || !wsConnected ? "not-allowed" : "pointer",
            transition: "all 0.2s",
          }}
        >
          {isExecuting ? "🔄 Agent is working..." : "🚀 Execute Agent"}
        </button>

        {!wsConnected && (
          <p
            style={{
              marginTop: "8px",
              fontSize: "12px",
              color: "#f87171",
              textAlign: "center",
            }}
          >
            ⚠️ WebSocket not connected. Please ensure the server is running.
          </p>
        )}
      </div>

      {progress.length > 0 && (
        <div className="agent-progress">
          <h4
            style={{
              marginBottom: "12px",
              fontSize: "14px",
              fontWeight: "600",
            }}
          >
            📊 Execution Progress
          </h4>
          <div
            style={{
              maxHeight: "300px",
              overflowY: "auto",
              backgroundColor: "#111827",
              borderRadius: "8px",
              padding: "12px",
            }}
          >
            {progress.map((update, index) => (
              <div
                key={index}
                style={{
                  marginBottom: "8px",
                  padding: "8px",
                  backgroundColor: "#1f2937",
                  borderRadius: "6px",
                  borderLeft: `3px solid ${getStatusColor(update.status)}`,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}
                >
                  <span style={{ fontSize: "16px" }}>
                    {getStatusIcon(update.status)}
                  </span>
                  <span
                    style={{
                      fontSize: "12px",
                      color: getStatusColor(update.status),
                      fontWeight: "600",
                      textTransform: "uppercase",
                    }}
                  >
                    {update.status}
                  </span>
                </div>
                <p
                  style={{
                    marginTop: "4px",
                    fontSize: "13px",
                    color: "#d1d5db",
                    marginLeft: "24px",
                  }}
                >
                  {update.message}
                </p>
                {update.timestamp && (
                  <p
                    style={{
                      marginTop: "4px",
                      fontSize: "11px",
                      color: "#6b7280",
                      marginLeft: "24px",
                    }}
                  >
                    {new Date(update.timestamp).toLocaleTimeString()}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {result && (
        <div className="agent-result">
          <h4
            style={{
              marginBottom: "12px",
              fontSize: "14px",
              fontWeight: "600",
            }}
          >
            ✨ Result
          </h4>
          <div
            style={{
              backgroundColor: "#065f46",
              borderRadius: "8px",
              padding: "12px",
              border: "1px solid #10b981",
            }}
          >
            <pre
              style={{
                margin: 0,
                fontSize: "12px",
                color: "#d1fae5",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {error && (
        <div
          style={{
            marginTop: "12px",
            padding: "12px",
            backgroundColor: "#7f1d1d",
            borderRadius: "8px",
            border: "1px solid #dc2626",
          }}
        >
          <p style={{ margin: 0, fontSize: "13px", color: "#fecaca" }}>
            ❌ {error}
          </p>
        </div>
      )}

      <style>{`
        .agent-executor {
          padding: 16px;
          background-color: #111827;
          border-radius: 12px;
          margin-bottom: 20px;
        }

        .section-header {
          margin-bottom: 16px;
        }

        .section-header h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 700;
          color: #f3f4f6;
        }

        .section-description {
          margin: 4px 0 0 0;
          font-size: 13px;
          color: #9ca3af;
        }

        .agent-input-section {
          margin-bottom: 20px;
        }

        .agent-input-section label {
          display: block;
          margin-bottom: 8px;
          font-size: 14px;
          font-weight: 600;
          color: #d1d5db;
        }

        .example-goals {
          margin-top: 12px;
        }

        .agent-progress,
        .agent-result {
          margin-top: 20px;
        }

        .agent-progress h4,
        .agent-result h4 {
          color: #f3f4f6;
        }
      `}</style>
    </div>
  );
}
