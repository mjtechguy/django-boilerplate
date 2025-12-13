import { createFileRoute, redirect, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { RegisterForm } from "@/components/auth/register-form";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Shield, CheckCircle, Mail } from "lucide-react";
import { ThemeToggle } from "@/components/shared/theme-toggle";

export const Route = createFileRoute("/register")({
  beforeLoad: async ({ context }) => {
    const { auth } = context;

    // If already authenticated, redirect to home
    if (auth.isAuthenticated && !auth.isLoading) {
      throw redirect({ to: "/" });
    }
  },
  component: RegisterPage,
});

function RegisterPage() {
  const { login, isLoading } = useAuth();
  const [registrationComplete, setRegistrationComplete] = useState(false);

  const handleRegistrationSuccess = () => {
    setRegistrationComplete(true);
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
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-11 w-full" />
          </div>
        </div>
      </div>
    );
  }

  // Registration success state
  if (registrationComplete) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-primary/5" />

        {/* Theme Toggle */}
        <div className="absolute top-4 right-4 z-10">
          <ThemeToggle />
        </div>

        <div className="relative w-full max-w-md p-8">
          <Link to="/" className="flex items-center justify-center gap-2 mb-8">
            <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center shadow-lg shadow-primary/25">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <span className="text-foreground font-semibold text-xl">Platform</span>
          </Link>

          <div className="bg-card/50 backdrop-blur-xl border border-border rounded-2xl p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-primary/10 flex items-center justify-center">
              <CheckCircle className="w-8 h-8 text-primary" />
            </div>

            <h1 className="text-2xl font-bold text-foreground mb-2">Check your email</h1>
            <p className="text-muted-foreground mb-6">
              We've sent a verification link to your email address. Please check your inbox.
            </p>

            <div className="p-4 rounded-lg bg-muted/50 border border-border mb-6">
              <div className="flex items-center gap-3 text-left">
                <Mail className="w-5 h-5 text-primary flex-shrink-0" />
                <p className="text-sm text-foreground">
                  Click the link in the email to verify your account and complete registration.
                </p>
              </div>
            </div>

            <Link to="/login">
              <Button className="w-full h-11">
                Go to Login
              </Button>
            </Link>
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
          <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center shadow-lg shadow-primary/25">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <span className="text-foreground font-semibold text-xl">Platform</span>
        </Link>

        {/* Card */}
        <div className="bg-card/50 backdrop-blur-xl border border-border rounded-2xl p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-foreground mb-2">Create an account</h1>
            <p className="text-muted-foreground">Get started with your free account</p>
          </div>

          {/* Registration Form */}
          <RegisterForm onSuccess={handleRegistrationSuccess} />

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-background text-muted-foreground">or</span>
            </div>
          </div>

          {/* SSO Registration */}
          <Button
            onClick={login}
            variant="outline"
            className="w-full h-11 font-medium transition-all"
          >
            Continue with SSO
          </Button>

          {/* Login link */}
          <p className="mt-6 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link
              to="/login"
              className="text-primary hover:text-primary/80 font-medium transition-colors"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
