import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { WSClient, type WebSocketStatus, type WSMessage } from "./ws-client";
import { useAuth } from "@/lib/auth";

interface Notification {
  id: string;
  title: string;
  body: string;
  timestamp: string;
  read?: boolean;
}

interface WebSocketContextType {
  // Connection status
  notificationStatus: WebSocketStatus;
  orgEventsStatus: WebSocketStatus;

  // Notifications
  notifications: Notification[];
  unreadCount: number;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  clearNotifications: () => void;

  // Org events
  orgEvents: WSMessage[];
  clearOrgEvents: () => void;

  // Connection control
  connectToOrg: (orgId: string) => void;
  disconnectFromOrg: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export function useWebSocket(): WebSocketContextType {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error("useWebSocket must be used within WebSocketProvider");
  }
  return context;
}

interface WebSocketProviderProps {
  children: ReactNode;
}

export function WebSocketProvider({ children }: WebSocketProviderProps) {
  const { isAuthenticated, getAccessToken } = useAuth();

  // Connection status
  const [notificationStatus, setNotificationStatus] = useState<WebSocketStatus>("disconnected");
  const [orgEventsStatus, setOrgEventsStatus] = useState<WebSocketStatus>("disconnected");

  // Notifications state
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [orgEvents, setOrgEvents] = useState<WSMessage[]>([]);

  // WebSocket clients
  const notificationClient = useRef<WSClient | null>(null);
  const orgEventsClient = useRef<WSClient | null>(null);
  const currentOrgId = useRef<string | null>(null);

  // Compute unread count
  const unreadCount = notifications.filter((n) => !n.read).length;

  // Handle notification messages
  const handleNotificationMessage = useCallback((message: WSMessage) => {
    if (message.type === "notification") {
      const notification = message.notification as Notification;
      setNotifications((prev) => [
        { ...notification, id: notification.id || crypto.randomUUID(), read: false },
        ...prev,
      ]);
    }
    // Handle connection established
    if (message.type === "connection.established") {
      console.log("Notification WebSocket connected:", message);
    }
  }, []);

  // Handle org event messages
  const handleOrgEventMessage = useCallback((message: WSMessage) => {
    if (message.type === "event") {
      setOrgEvents((prev) => [message, ...prev.slice(0, 99)]); // Keep last 100 events
    }
    if (message.type === "connection.established") {
      console.log("Org events WebSocket connected:", message);
    }
  }, []);

  // Connect to notifications WebSocket when authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      notificationClient.current?.disconnect();
      notificationClient.current = null;
      setNotificationStatus("disconnected");
      return;
    }

    const connectNotifications = async () => {
      const token = await getAccessToken();
      if (!token) return;

      const wsUrl = `${import.meta.env.VITE_WS_URL || "ws://localhost:8000"}/ws/notifications/`;

      notificationClient.current = new WSClient({
        url: wsUrl,
        token,
        onMessage: handleNotificationMessage,
        onStatusChange: setNotificationStatus,
      });

      notificationClient.current.connect();
    };

    connectNotifications();

    return () => {
      notificationClient.current?.disconnect();
      notificationClient.current = null;
    };
  }, [isAuthenticated, getAccessToken, handleNotificationMessage]);

  // Connect to org events
  const connectToOrg = useCallback(async (orgId: string) => {
    // Disconnect from previous org if any
    if (orgEventsClient.current) {
      orgEventsClient.current.disconnect();
      orgEventsClient.current = null;
    }

    if (!isAuthenticated) {
      setOrgEventsStatus("disconnected");
      return;
    }

    const token = await getAccessToken();
    if (!token) return;

    currentOrgId.current = orgId;
    const wsUrl = `${import.meta.env.VITE_WS_URL || "ws://localhost:8000"}/ws/events/${orgId}/`;

    orgEventsClient.current = new WSClient({
      url: wsUrl,
      token,
      onMessage: handleOrgEventMessage,
      onStatusChange: setOrgEventsStatus,
    });

    orgEventsClient.current.connect();
  }, [isAuthenticated, getAccessToken, handleOrgEventMessage]);

  const disconnectFromOrg = useCallback(() => {
    orgEventsClient.current?.disconnect();
    orgEventsClient.current = null;
    currentOrgId.current = null;
    setOrgEventsStatus("disconnected");
    setOrgEvents([]);
  }, []);

  // Notification actions
  const markAsRead = useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  const clearOrgEvents = useCallback(() => {
    setOrgEvents([]);
  }, []);

  const value: WebSocketContextType = {
    notificationStatus,
    orgEventsStatus,
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    clearNotifications,
    orgEvents,
    clearOrgEvents,
    connectToOrg,
    disconnectFromOrg,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}
