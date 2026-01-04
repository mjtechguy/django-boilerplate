import { ReactElement, ReactNode } from "react";
import { render, RenderOptions } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@/lib/auth/auth-context";
import type { AuthContextType } from "@/types/auth";
import { createMockAuthContext } from "./mocks/auth";

/**
 * Custom render options that extend RTL's RenderOptions
 */
interface CustomRenderOptions extends Omit<RenderOptions, "wrapper"> {
  /**
   * Custom auth context to provide to components
   * If not provided, defaults to unauthenticated state
   */
  authContext?: Partial<AuthContextType>;
  /**
   * Custom QueryClient instance
   * If not provided, creates a new one with test-friendly defaults
   */
  queryClient?: QueryClient;
}

/**
 * Creates a test-friendly QueryClient with disabled retries and cache
 * to make tests more predictable and faster
 */
function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
        refetchOnWindowFocus: false,
        refetchOnReconnect: false,
      },
      mutations: {
        retry: false,
      },
    },
    logger: {
      log: () => {},
      warn: () => {},
      error: () => {},
    },
  });
}

/**
 * Wrapper component that provides all necessary context providers for testing
 */
function AllProviders({
  children,
  authContext,
  queryClient,
}: {
  children: ReactNode;
  authContext: AuthContextType;
  queryClient: QueryClient;
}) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={authContext}>
        {children}
      </AuthContext.Provider>
    </QueryClientProvider>
  );
}

/**
 * Custom render function that wraps components with necessary providers
 *
 * @example
 * ```tsx
 * // Render with authenticated user
 * const { getByText } = renderWithProviders(<MyComponent />, {
 *   authContext: {
 *     user: createMockUser({ email: 'test@example.com' }),
 *     isAuthenticated: true,
 *   }
 * });
 *
 * // Render with unauthenticated state (default)
 * const { getByText } = renderWithProviders(<MyComponent />);
 * ```
 */
export function renderWithProviders(
  ui: ReactElement,
  options: CustomRenderOptions = {}
) {
  const { authContext: customAuthContext, queryClient: customQueryClient, ...renderOptions } = options;

  // Create test QueryClient if not provided
  const queryClient = customQueryClient ?? createTestQueryClient();

  // Create mock auth context with custom overrides
  const authContext = createMockAuthContext(customAuthContext);

  // Render with all providers
  const result = render(ui, {
    wrapper: ({ children }) => (
      <AllProviders authContext={authContext} queryClient={queryClient}>
        {children}
      </AllProviders>
    ),
    ...renderOptions,
  });

  return {
    ...result,
    queryClient,
    authContext,
  };
}

/**
 * Re-export everything from @testing-library/react
 * This allows tests to import from a single location
 */
export * from "@testing-library/react";

/**
 * Override the default render with our custom version
 */
export { renderWithProviders as render };
