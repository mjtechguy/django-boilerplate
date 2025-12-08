/**
 * WebSocket client with automatic reconnection and message handling.
 */

export type WebSocketStatus = "connecting" | "connected" | "disconnected" | "error";

export interface WSMessage {
  type: string;
  [key: string]: unknown;
}

export interface WSClientOptions {
  url: string;
  token: string;
  onMessage?: (message: WSMessage) => void;
  onStatusChange?: (status: WebSocketStatus) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  pingInterval?: number;
}

export class WSClient {
  private ws: WebSocket | null = null;
  private url: string;
  private token: string;
  private onMessage?: (message: WSMessage) => void;
  private onStatusChange?: (status: WebSocketStatus) => void;
  private reconnectInterval: number;
  private maxReconnectAttempts: number;
  private pingInterval: number;
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private status: WebSocketStatus = "disconnected";
  private isIntentionallyClosed = false;

  constructor(options: WSClientOptions) {
    this.url = options.url;
    this.token = options.token;
    this.onMessage = options.onMessage;
    this.onStatusChange = options.onStatusChange;
    this.reconnectInterval = options.reconnectInterval ?? 3000;
    this.maxReconnectAttempts = options.maxReconnectAttempts ?? 10;
    this.pingInterval = options.pingInterval ?? 30000;
  }

  private setStatus(status: WebSocketStatus): void {
    this.status = status;
    this.onStatusChange?.(status);
  }

  private buildUrl(): string {
    // Add token to query string for authentication
    const separator = this.url.includes("?") ? "&" : "?";
    return `${this.url}${separator}token=${encodeURIComponent(this.token)}`;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isIntentionallyClosed = false;
    this.setStatus("connecting");

    try {
      this.ws = new WebSocket(this.buildUrl());

      this.ws.onopen = () => {
        this.setStatus("connected");
        this.reconnectAttempts = 0;
        this.startPing();
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WSMessage;
          this.onMessage?.(message);
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      };

      this.ws.onclose = (event) => {
        this.stopPing();
        this.setStatus("disconnected");

        // Don't reconnect if intentionally closed or unauthorized
        if (this.isIntentionallyClosed || event.code === 4001 || event.code === 4003) {
          return;
        }

        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        this.setStatus("error");
      };
    } catch (error) {
      console.error("WebSocket connection error:", error);
      this.setStatus("error");
      this.scheduleReconnect();
    }
  }

  disconnect(): void {
    this.isIntentionallyClosed = true;
    this.stopPing();
    this.clearReconnectTimer();

    if (this.ws) {
      this.ws.close(1000, "Client disconnect");
      this.ws = null;
    }

    this.setStatus("disconnected");
  }

  send(message: WSMessage): boolean {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      return false;
    }

    try {
      this.ws.send(JSON.stringify(message));
      return true;
    } catch (error) {
      console.error("Failed to send WebSocket message:", error);
      return false;
    }
  }

  private startPing(): void {
    this.stopPing();
    this.pingTimer = setInterval(() => {
      this.send({
        type: "ping",
        timestamp: Date.now(),
      });
    }, this.pingInterval);
  }

  private stopPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error("Max reconnect attempts reached");
      return;
    }

    this.clearReconnectTimer();

    // Exponential backoff with jitter
    const delay = Math.min(
      this.reconnectInterval * Math.pow(2, this.reconnectAttempts) + Math.random() * 1000,
      30000
    );

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      this.connect();
    }, delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  getStatus(): WebSocketStatus {
    return this.status;
  }

  updateToken(token: string): void {
    this.token = token;
    // Reconnect with new token
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.disconnect();
      this.connect();
    }
  }
}
