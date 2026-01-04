# Notifications Page Test Setup

This document describes how to run the tests for the notifications page.

## Prerequisites

The following testing dependencies need to be installed:

```bash
cd frontend
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom @vitest/ui
```

Or with pnpm:

```bash
cd frontend
pnpm add -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom @vitest/ui
```

## Running Tests

### Run tests in watch mode (recommended for development)
```bash
npm run test
```

### Run tests once (CI mode)
```bash
npm run test:run
```

### Run tests with UI (interactive)
```bash
npm run test:ui
```

## Test Coverage

The test suite (`index.test.tsx`) covers the following scenarios:

### 1. Rendering with Mock WebSocket Context
- ✓ Renders page header with title and description
- ✓ Renders action buttons (Mark all read, Settings)
- ✓ Displays notification statistics (total count, unread count)
- ✓ Renders notifications list when notifications exist
- ✓ Displays connection status badge
- ✓ Shows different connection statuses (connected, connecting, disconnected, error)

### 2. Mark as Read Functionality
- ✓ Calls `markAsRead()` when clicking "Mark as read" button
- ✓ Doesn't show "Mark as read" button for already read notifications
- ✓ Displays visual indicator for unread notifications

### 3. Mark All as Read Functionality
- ✓ Calls `markAllAsRead()` when clicking "Mark all read" button

### 4. Delete Notification Functionality
- ✓ Calls `removeNotification()` when clicking delete button
- ✓ Has delete button for each notification

### 5. Empty State Display
- ✓ Shows empty state message when no notifications exist
- ✓ Doesn't show "Load More" button when empty
- ✓ Shows "Load More" button when notifications exist
- ✓ Shows "0 total" in stats when empty
- ✓ Doesn't show unread badge when unreadCount is 0

### 6. Time Formatting
- ✓ Formats recent timestamps as "Just now"
- ✓ Formats timestamps as "X min ago"
- ✓ Formats timestamps as "X hours ago"
- ✓ Formats timestamps as "X days ago"

### 7. Notification Types and Icons
- ✓ Displays correct icon for notification type (info, warning, success, error)

### 8. Accessibility
- ✓ All buttons have proper labels for screen readers

## Test Structure

The tests use:
- **Vitest** - Fast unit test framework
- **React Testing Library** - For rendering React components in tests
- **@testing-library/user-event** - For simulating user interactions
- **@testing-library/jest-dom** - For additional DOM matchers

All tests mock the `useWebSocket` hook to provide controlled test data and verify function calls.

## Configuration

- **vitest.config.ts** - Vitest configuration
- **src/test/setup.ts** - Test setup file that runs before all tests
