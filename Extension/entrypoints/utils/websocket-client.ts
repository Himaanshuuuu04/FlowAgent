/**
 * WebSocket Client for AI Extension
 * Manages stable connection to the Python Flask-SocketIO server
 */

import { io, Socket } from "socket.io-client";

const SERVER_URL = "http://localhost:8080";

export class WebSocketClient {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private isConnected = false;
  private eventHandlers: Map<string, Function[]> = new Map();
  private pingInterval: NodeJS.Timeout | null = null;

  constructor() {
    this.connect();
  }

  /**
   * Establish WebSocket connection
   */
  connect(): void {
    if (this.socket?.connected) {
      console.log("WebSocket already connected");
      return;
    }

    console.log("Connecting to WebSocket server...", SERVER_URL);

    this.socket = io(SERVER_URL, {
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionDelay: this.reconnectDelay,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: this.maxReconnectAttempts,
      timeout: 10000,
      autoConnect: true,
    });

    this.setupEventListeners();
  }

  /**
   * Setup core WebSocket event listeners
   */
  private setupEventListeners(): void {
    if (!this.socket) return;

    this.socket.on("connect", () => {
      console.log("✅ WebSocket connected successfully");
      this.isConnected = true;
      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000;
      this.startPingInterval();
      this.emit("connection_status", { connected: true });
    });

    this.socket.on("connection_established", (data) => {
      console.log("🔗 Connection established:", data);
      this.emit("connection_established", data);
    });

    this.socket.on("disconnect", (reason) => {
      console.log("❌ WebSocket disconnected:", reason);
      this.isConnected = false;
      this.stopPingInterval();
      this.emit("connection_status", { connected: false, reason });

      if (reason === "io server disconnect") {
        // Server disconnected, try to reconnect manually
        this.attemptReconnect();
      }
    });

    this.socket.on("connect_error", (error) => {
      console.error("❌ WebSocket connection error:", error.message);
      this.isConnected = false;
      this.emit("connection_error", { error: error.message });
      this.attemptReconnect();
    });

    this.socket.on("pong", (data) => {
      // Keep-alive pong received
      console.log("🏓 Pong received from server");
    });

    // Listen for all custom events
    this.socket.onAny((eventName, ...args) => {
      console.log(`📨 Received event: ${eventName}`, args);
      this.emit(eventName, ...args);
    });
  }

  /**
   * Start sending periodic pings to keep connection alive
   */
  private startPingInterval(): void {
    this.stopPingInterval(); // Clear any existing interval

    this.pingInterval = setInterval(() => {
      if (this.socket?.connected) {
        this.socket.emit("ping", { timestamp: Date.now() });
      }
    }, 20000); // Ping every 20 seconds
  }

  /**
   * Stop ping interval
   */
  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error(
        "❌ Max reconnection attempts reached. Please check server status."
      );
      this.emit("max_reconnect_attempts_reached", {});
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
      10000
    );

    console.log(
      `🔄 Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms...`
    );

    setTimeout(() => {
      if (!this.socket?.connected) {
        this.socket?.connect();
      }
    }, delay);
  }

  /**
   * Send a message through WebSocket
   */
  send(event: string, data: any): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.socket?.connected) {
        reject(new Error("WebSocket not connected"));
        return;
      }

      this.socket.emit(event, data, (response: any) => {
        resolve(response);
      });
    });
  }

  /**
   * Register an event handler
   */
  on(event: string, handler: Function): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event)!.push(handler);
  }

  /**
   * Remove an event handler
   */
  off(event: string, handler: Function): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  /**
   * Emit to registered handlers
   */
  private emit(event: string, ...args: any[]): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(...args);
        } catch (error) {
          console.error(`Error in handler for ${event}:`, error);
        }
      });
    }
  }

  /**
   * Generate script using WebSocket
   */
  async generateScript(
    goal: string,
    targetUrl: string,
    domStructure: any
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.socket?.connected) {
        reject(new Error("WebSocket not connected"));
        return;
      }

      // Listen for progress updates
      const progressHandler = (data: any) => {
        console.log("Progress:", data.message);
        this.emit("generation_progress", data);
      };

      const successHandler = (data: any) => {
        this.socket?.off("script_progress", progressHandler);
        this.socket?.off("script_generated", successHandler);
        this.socket?.off("script_error", errorHandler);
        resolve(data);
      };

      const errorHandler = (data: any) => {
        this.socket?.off("script_progress", progressHandler);
        this.socket?.off("script_generated", successHandler);
        this.socket?.off("script_error", errorHandler);
        reject(new Error(data.error || "Unknown error"));
      };

      this.socket.on("script_progress", progressHandler);
      this.socket.on("script_generated", successHandler);
      this.socket.on("script_error", errorHandler);

      // Send request
      this.socket.emit("generate_script_ws", {
        goal,
        target_url: targetUrl,
        dom_structure: domStructure,
        constraints: {},
      });

      // Timeout after 30 seconds
      setTimeout(() => {
        this.socket?.off("script_progress", progressHandler);
        this.socket?.off("script_generated", successHandler);
        this.socket?.off("script_error", errorHandler);
        reject(new Error("Request timeout"));
      }, 30000);
    });
  }

  /**
   * Update result using WebSocket
   */
  async updateResult(result: any): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.socket?.connected) {
        reject(new Error("WebSocket not connected"));
        return;
      }

      const successHandler = (data: any) => {
        this.socket?.off("result_updated", successHandler);
        this.socket?.off("update_error", errorHandler);
        resolve(data);
      };

      const errorHandler = (data: any) => {
        this.socket?.off("result_updated", successHandler);
        this.socket?.off("update_error", errorHandler);
        reject(new Error(data.error || "Unknown error"));
      };

      this.socket.on("result_updated", successHandler);
      this.socket.on("update_error", errorHandler);

      this.socket.emit("update_result_ws", { result });

      setTimeout(() => {
        this.socket?.off("result_updated", successHandler);
        this.socket?.off("update_error", errorHandler);
        reject(new Error("Request timeout"));
      }, 10000);
    });
  }

  /**
   * Get conversation stats using WebSocket
   */
  async getStats(): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.socket?.connected) {
        reject(new Error("WebSocket not connected"));
        return;
      }

      const successHandler = (data: any) => {
        this.socket?.off("stats_response", successHandler);
        this.socket?.off("stats_error", errorHandler);
        resolve(data);
      };

      const errorHandler = (data: any) => {
        this.socket?.off("stats_response", successHandler);
        this.socket?.off("stats_error", errorHandler);
        reject(new Error(data.error || "Unknown error"));
      };

      this.socket.on("stats_response", successHandler);
      this.socket.on("stats_error", errorHandler);

      this.socket.emit("get_stats_ws");

      setTimeout(() => {
        this.socket?.off("stats_response", successHandler);
        this.socket?.off("stats_error", errorHandler);
        reject(new Error("Request timeout"));
      }, 10000);
    });
  }

  /**
   * Check if WebSocket is connected
   */
  isSocketConnected(): boolean {
    return this.isConnected && this.socket?.connected === true;
  }

  /**
   * Disconnect WebSocket
   */
  disconnect(): void {
    console.log("Disconnecting WebSocket...");
    this.stopPingInterval();
    this.socket?.disconnect();
    this.isConnected = false;
  }

  /**
   * Get connection status
   */
  getStatus(): { connected: boolean; attempts: number } {
    return {
      connected: this.isConnected,
      attempts: this.reconnectAttempts,
    };
  }
}

// Export singleton instance
export const wsClient = new WebSocketClient();
