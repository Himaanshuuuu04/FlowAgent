import React from "react";
import {
  formatTokenCount,
  getTokenPercentage,
  TokenEstimate,
} from "../utils/tokenEstimator";

interface TokenUsageIndicatorProps {
  estimate: TokenEstimate;
  compact?: boolean;
}

export const TokenUsageIndicator: React.FC<TokenUsageIndicatorProps> = ({
  estimate,
  compact = false,
}) => {
  const percentage = getTokenPercentage(estimate.total);

  // Color based on usage
  let color = "#4ade80"; // green
  if (estimate.error) {
    color = "#ef4444"; // red
  } else if (estimate.warning) {
    color = "#f59e0b"; // amber
  } else if (percentage > 60) {
    color = "#eab308"; // yellow
  }

  if (compact) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          fontSize: "12px",
          color: "#64748b",
        }}
      >
        <div
          style={{
            width: "80px",
            height: "4px",
            backgroundColor: "#e2e8f0",
            borderRadius: "2px",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${percentage}%`,
              height: "100%",
              backgroundColor: color,
              transition: "width 0.3s ease, background-color 0.3s ease",
            }}
          />
        </div>
        <span style={{ color }}>{formatTokenCount(estimate.total)}</span>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: "12px",
        backgroundColor: "#f8fafc",
        borderRadius: "8px",
        border: `1px solid ${
          estimate.error ? "#fee2e2" : estimate.warning ? "#fef3c7" : "#e2e8f0"
        }`,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "8px",
        }}
      >
        <span style={{ fontSize: "13px", fontWeight: 600, color: "#475569" }}>
          Token Usage
        </span>
        <span style={{ fontSize: "13px", fontWeight: 600, color }}>
          {formatTokenCount(estimate.total)}
        </span>
      </div>

      <div
        style={{
          width: "100%",
          height: "8px",
          backgroundColor: "#e2e8f0",
          borderRadius: "4px",
          overflow: "hidden",
          marginBottom: "8px",
        }}
      >
        <div
          style={{
            width: `${Math.min(100, percentage)}%`,
            height: "100%",
            backgroundColor: color,
            transition: "width 0.3s ease, background-color 0.3s ease",
          }}
        />
      </div>

      <div
        style={{
          display: "flex",
          gap: "16px",
          fontSize: "11px",
          color: "#64748b",
        }}
      >
        <div>
          <span>History: </span>
          <span style={{ fontWeight: 600 }}>
            {formatTokenCount(estimate.history)}
          </span>
        </div>
        <div>
          <span>Prompt: </span>
          <span style={{ fontWeight: 600 }}>
            {formatTokenCount(estimate.currentPrompt)}
          </span>
        </div>
      </div>

      {estimate.message && (
        <div
          style={{
            marginTop: "8px",
            padding: "8px",
            backgroundColor: estimate.error ? "#fef2f2" : "#fffbeb",
            borderRadius: "6px",
            fontSize: "11px",
            color: estimate.error ? "#991b1b" : "#92400e",
            lineHeight: "1.5",
          }}
        >
          {estimate.message}
        </div>
      )}
    </div>
  );
};
