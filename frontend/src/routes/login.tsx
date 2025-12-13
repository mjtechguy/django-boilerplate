import { createFileRoute, redirect, useNavigate, Link, useSearch } from "@tanstack/react-router";
import { useEffect } from "react";
import { z } from "zod";
import { useAuth } from "@/lib/auth";
import { LoginForm } from "@/components/auth/login-form";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Shield } from "lucide-react";
import { ThemeToggle } from "@/components/shared/theme-toggle";

// Define search params schema for redirect
const loginSearchSchema = z.object({
  redirect: z.string().optional(),
});

export const Route = createFileRoute("/login")({
  validateSearch: loginSearchSchema,
  beforeLoad: async ({ context, search }) => {
    const { auth } = context;

    // If already authenticated, redirect to intended destination or home
    if (auth.isAuthenticated && !auth.isLoading) {
      throw redirect({ to: search.redirect || "/" });
    }
  },
  component: LoginPage,
});

function LoginPage() {
  const { login, isLoading, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const { redirect: redirectTo } = useSearch({ from: "/login" });

  useEffect(() => {
    // Auto-redirect if already authenticated
    if (isAuthenticated && !isLoading) {
      navigate({ to: redirectTo || "/" });
    }
  }, [isAuthenticated, isLoading, navigate, redirectTo]);

  const handleLoginSuccess = () => {
    navigate({ to: redirectTo || "/" });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="w-full max-w-md p-8">
          <Skeleton className="mx-auto h-12 w-12 rounded-lg mb-6" />
          <Skeleton className="mx-auto h-8 w-48 mb-2" />
          <Skeleton className="mx-auto h-4 w-64 mb-8" />
          <div className="space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-11 w-full" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-primary/5" />

      {/* Theme Toggle */}
      <div className="absolute top-4 right-4 z-10">
        <ThemeToggle />
      </div>

      <div className="relative w-full max-w-md p-8">
        {/* Logo */}
        <Link to="/" className="flex items-center justify-center gap-2 mb-8">
          <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center shadow-lg shadow-primary/20">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <span className="text-foreground font-semibold text-xl">Platform</span>
        </Link>

        {/* Card */}
        <div className="bg-card/50 backdrop-blur-xl border border-border rounded-2xl p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-foreground mb-2">Welcome back</h1>
            <p className="text-muted-foreground">Sign in to your account</p>
          </div>

          {/* Local Login Form */}
          <LoginForm onSuccess={handleLoginSuccess} />

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-background text-muted-foreground">or</span>
            </div>
          </div>

          {/* SSO Login */}
          <Button
            onClick={login}
            variant="outline"
            className="w-full h-11 font-medium transition-all"
          >
            Sign in with SSO
          </Button>

          {/* Register link */}
          <p className="mt-6 text-center text-sm text-muted-foreground">
            Don't have an account?{" "}
            <Link
              to="/register"
              className="text-primary hover:text-primary/80 font-medium transition-colors"
            >
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
