import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from "@tanstack/react-router";
import * as wsContext from "@/lib/websocket/ws-context";

// Import the component under test
import { Route } from "./index";

// Mock the useWebSocket hook
const mockUseWebSocket = vi.fn();
vi.mock("@/lib/websocket/ws-context", async () => {
  const actual = await vi.importActual("@/lib/websocket/ws-context");
  return {
    ...actual,
    useWebSocket: () => mockUseWebSocket(),
  };
});

// Helper to create a router for testing
function createTestRouter() {
  const rootRoute = createRootRoute();
  const notificationsRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/app/notifications",
    component: Route.options.component,
  });

  const routeTree = rootRoute.addChildren([notificationsRoute]);
  const router = createRouter({
    routeTree,
    history: createMemoryHistory({
      initialEntries: ["/app/notifications"],
    }),
  });

  return router;
}

// Helper to render the notifications page with router
function renderNotificationsPage() {
  const router = createTestRouter();
  return {
    ...render(<RouterProvider router={router} />),
    router,
  };
}

describe("Notifications Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering with mock WebSocket context", () => {
    it("should render the page header with title and description", () => {
      mockUseWebSocket.mockReturnValue({
        notifications: [],
        unreadCount: 0,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      expect(screen.getByText("Notifications")).toBeInTheDocument();
      expect(screen.getByText("Stay updated with your latest activity")).toBeInTheDocument();
    });

    it("should render action buttons in header", () => {
      mockUseWebSocket.mockReturnValue({
        notifications: [],
        unreadCount: 0,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      expect(screen.getByRole("button", { name: /mark all read/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /settings/i })).toBeInTheDocument();
    });

    it("should display notification statistics", () => {
      mockUseWebSocket.mockReturnValue({
        notifications: [
          {
            id: "1",
            title: "Test Notification",
            body: "Test body",
            timestamp: new Date().toISOString(),
            read: false,
          },
        ],
        unreadCount: 1,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      expect(screen.getByText("1 total")).toBeInTheDocument();
      expect(screen.getByText("1 unread")).toBeInTheDocument();
    });

    it("should render notifications list when notifications exist", () => {
      mockUseWebSocket.mockReturnValue({
        notifications: [
          {
            id: "1",
            title: "New User Registration",
            body: "A new user has registered",
            timestamp: new Date().toISOString(),
            read: false,
          },
          {
            id: "2",
            title: "System Update",
            body: "System has been updated",
            timestamp: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
            read: true,
          },
        ],
        unreadCount: 1,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      expect(screen.getByText("New User Registration")).toBeInTheDocument();
      expect(screen.getByText("A new user has registered")).toBeInTheDocument();
      expect(screen.getByText("System Update")).toBeInTheDocument();
      expect(screen.getByText("System has been updated")).toBeInTheDocument();
    });

    it("should display connection status badge", () => {
      mockUseWebSocket.mockReturnValue({
        notifications: [],
        unreadCount: 0,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    it("should show different connection statuses correctly", () => {
      const statuses = ["connecting", "disconnected", "error"] as const;

      statuses.forEach((status) => {
        const { unmount } = render(
          <RouterProvider
            router={createRouter({
              routeTree: createRootRoute().addChildren([
                createRoute({
                  getParentRoute: () => createRootRoute(),
                  path: "/app/notifications",
                  component: () => {
                    mockUseWebSocket.mockReturnValue({
                      notifications: [],
                      unreadCount: 0,
                      notificationStatus: status,
                      markAsRead: vi.fn(),
                      markAllAsRead: vi.fn(),
                      removeNotification: vi.fn(),
                    });
                    const Component = Route.options.component as () => JSX.Element;
                    return <Component />;
                  },
                }),
              ]),
              history: createMemoryHistory({
                initialEntries: ["/app/notifications"],
              }),
            })}
          />
        );

        const expectedText =
          status === "connecting"
            ? "Connecting"
            : status === "disconnected"
              ? "Disconnected"
              : "Error";

        expect(screen.getByText(expectedText)).toBeInTheDocument();
        unmount();
      });
    });
  });

  describe("Mark as read functionality", () => {
    it("should call markAsRead when clicking mark as read button", async () => {
      const user = userEvent.setup();
      const markAsRead = vi.fn();

      mockUseWebSocket.mockReturnValue({
        notifications: [
          {
            id: "1",
            title: "Test Notification",
            body: "Test body",
            timestamp: new Date().toISOString(),
            read: false,
          },
        ],
        unreadCount: 1,
        notificationStatus: "connected",
        markAsRead,
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      const markAsReadButton = screen.getByRole("button", { name: /mark as read/i });
      await user.click(markAsReadButton);

      expect(markAsRead).toHaveBeenCalledWith("1");
      expect(markAsRead).toHaveBeenCalledTimes(1);
    });

    it("should not show mark as read button for already read notifications", () => {
      mockUseWebSocket.mockReturnValue({
        notifications: [
          {
            id: "1",
            title: "Read Notification",
            body: "This is read",
            timestamp: new Date().toISOString(),
            read: true,
          },
        ],
        unreadCount: 0,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      expect(screen.queryByRole("button", { name: /mark as read/i })).not.toBeInTheDocument();
    });

    it("should display visual indicator for unread notifications", () => {
      mockUseWebSocket.mockReturnValue({
        notifications: [
          {
            id: "1",
            title: "Unread Notification",
            body: "This is unread",
            timestamp: new Date().toISOString(),
            read: false,
          },
        ],
        unreadCount: 1,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      const { container } = renderNotificationsPage();

      // Check for the unread indicator dot (h-2 w-2 rounded-full bg-primary)
      const unreadDot = container.querySelector(".h-2.w-2.rounded-full.bg-primary");
      expect(unreadDot).toBeInTheDocument();
    });
  });

  describe("Mark all as read functionality", () => {
    it("should call markAllAsRead when clicking mark all read button", async () => {
      const user = userEvent.setup();
      const markAllAsRead = vi.fn();

      mockUseWebSocket.mockReturnValue({
        notifications: [
          {
            id: "1",
            title: "Notification 1",
            body: "Body 1",
            timestamp: new Date().toISOString(),
            read: false,
          },
          {
            id: "2",
            title: "Notification 2",
            body: "Body 2",
            timestamp: new Date().toISOString(),
            read: false,
          },
        ],
        unreadCount: 2,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead,
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      const markAllReadButton = screen.getByRole("button", { name: /mark all read/i });
      await user.click(markAllReadButton);

      expect(markAllAsRead).toHaveBeenCalledTimes(1);
    });
  });

  describe("Delete notification functionality", () => {
    it("should call removeNotification when clicking delete button", async () => {
      const user = userEvent.setup();
      const removeNotification = vi.fn();

      mockUseWebSocket.mockReturnValue({
        notifications: [
          {
            id: "1",
            title: "Test Notification",
            body: "Test body",
            timestamp: new Date().toISOString(),
            read: false,
          },
        ],
        unreadCount: 1,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification,
      });

      renderNotificationsPage();

      // Find the delete button (trash icon button)
      const deleteButtons = screen.getAllByRole("button");
      const deleteButton = deleteButtons.find((btn) => {
        const svg = btn.querySelector("svg");
        return svg?.getAttribute("class")?.includes("lucide-trash-2");
      });

      expect(deleteButton).toBeInTheDocument();

      if (deleteButton) {
        await user.click(deleteButton);
        expect(removeNotification).toHaveBeenCalledWith("1");
        expect(removeNotification).toHaveBeenCalledTimes(1);
      }
    });

    it("should have delete button for each notification", () => {
      mockUseWebSocket.mockReturnValue({
        notifications: [
          {
            id: "1",
            title: "Notification 1",
            body: "Body 1",
            timestamp: new Date().toISOString(),
            read: false,
          },
          {
            id: "2",
            title: "Notification 2",
            body: "Body 2",
            timestamp: new Date().toISOString(),
            read: true,
          },
        ],
        unreadCount: 1,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      const { container } = renderNotificationsPage();

      // Count delete buttons by looking for trash icons
      const trashIcons = container.querySelectorAll(".lucide-trash-2");
      expect(trashIcons).toHaveLength(2);
    });
  });

  describe("Empty state display", () => {
    it("should show empty state when there are no notifications", () => {
      mockUseWebSocket.mockReturnValue({
        notifications: [],
        unreadCount: 0,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      expect(screen.getByText("No notifications yet")).toBeInTheDocument();
      expect(
        screen.getByText("You're all caught up! Notifications will appear here when there's new activity.")
      ).toBeInTheDocument();
    });

    it("should not show Load More button when there are no notifications", () => {
      mockUseWebSocket.mockReturnValue({
        notifications: [],
        unreadCount: 0,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      expect(screen.queryByRole("button", { name: /load more/i })).not.toBeInTheDocument();
    });

    it("should show Load More button when there are notifications", () => {
      mockUseWebSocket.mockReturnValue({
        notifications: [
          {
            id: "1",
            title: "Test Notification",
            body: "Test body",
            timestamp: new Date().toISOString(),
            read: false,
          },
        ],
        unreadCount: 1,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      expect(screen.getByRole("button", { name: /load more/i })).toBeInTheDocument();
    });

    it("should show 0 total in stats when empty", () => {
      mockUseWebSocket.mockReturnValue({
        notifications: [],
        unreadCount: 0,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      expect(screen.getByText("0 total")).toBeInTheDocument();
    });

    it("should not show unread badge when unreadCount is 0", () => {
      mockUseWebSocket.mockReturnValue({
        notifications: [
          {
            id: "1",
            title: "Read Notification",
            body: "This is read",
            timestamp: new Date().toISOString(),
            read: true,
          },
        ],
        unreadCount: 0,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      expect(screen.queryByText(/unread/i)).not.toBeInTheDocument();
    });
  });

  describe("Time formatting", () => {
    it("should format recent timestamps as 'Just now'", () => {
      mockUseWebSocket.mockReturnValue({
        notifications: [
          {
            id: "1",
            title: "Recent Notification",
            body: "Just happened",
            timestamp: new Date().toISOString(),
            read: false,
          },
        ],
        unreadCount: 1,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      expect(screen.getByText("Just now")).toBeInTheDocument();
    });

    it("should format timestamps as minutes ago", () => {
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();

      mockUseWebSocket.mockReturnValue({
        notifications: [
          {
            id: "1",
            title: "Recent Notification",
            body: "A few minutes ago",
            timestamp: fiveMinutesAgo,
            read: false,
          },
        ],
        unreadCount: 1,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      expect(screen.getByText("5 min ago")).toBeInTheDocument();
    });

    it("should format timestamps as hours ago", () => {
      const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();

      mockUseWebSocket.mockReturnValue({
        notifications: [
          {
            id: "1",
            title: "Older Notification",
            body: "Happened a while ago",
            timestamp: twoHoursAgo,
            read: false,
          },
        ],
        unreadCount: 1,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      expect(screen.getByText("2 hours ago")).toBeInTheDocument();
    });

    it("should format timestamps as days ago", () => {
      const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString();

      mockUseWebSocket.mockReturnValue({
        notifications: [
          {
            id: "1",
            title: "Old Notification",
            body: "Happened days ago",
            timestamp: threeDaysAgo,
            read: false,
          },
        ],
        unreadCount: 1,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      expect(screen.getByText("3 days ago")).toBeInTheDocument();
    });
  });

  describe("Notification types and icons", () => {
    it("should display info icon for info type notifications", () => {
      mockUseWebSocket.mockReturnValue({
        notifications: [
          {
            id: "1",
            title: "Info Notification",
            body: "This is an info",
            timestamp: new Date().toISOString(),
            read: false,
          },
        ],
        unreadCount: 1,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      const { container } = renderNotificationsPage();

      // The default type is "info", so it should have the Info icon (lucide-info)
      const infoIcon = container.querySelector(".lucide-info");
      expect(infoIcon).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have proper button labels for screen readers", () => {
      mockUseWebSocket.mockReturnValue({
        notifications: [
          {
            id: "1",
            title: "Test Notification",
            body: "Test body",
            timestamp: new Date().toISOString(),
            read: false,
          },
        ],
        unreadCount: 1,
        notificationStatus: "connected",
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
      });

      renderNotificationsPage();

      // All buttons should be accessible
      expect(screen.getByRole("button", { name: /mark all read/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /settings/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /mark as read/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /load more/i })).toBeInTheDocument();
    });
  });
});
