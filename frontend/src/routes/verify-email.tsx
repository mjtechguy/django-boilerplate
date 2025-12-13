import { createFileRoute, Link, useSearch } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { z } from "zod";
import { Loader2, Shield, CheckCircle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { verifyEmail } from "@/lib/api/auth";
import { ThemeToggle } from "@/components/shared/theme-toggle";

const searchSchema = z.object({
  token: z.string().optional(),
});

export const Route = createFileRoute("/verify-email")({
  validateSearch: searchSchema,
  component: VerifyEmailPage,
});

function VerifyEmailPage() {
  const { token } = useSearch({ from: "/verify-email" });
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setError("No verification token provided");
      return;
    }

    const verify = async () => {
      try {
        await verifyEmail(token);
        setStatus("success");
      } catch (err) {
        setStatus("error");
        setError(
          err instanceof Error
            ? err.message
            : "Verification failed. The link may have expired."
        );
      }
    };

    verify();
  }, [token]);

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
          {status === "loading" && (
            <>
              <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-muted/50 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
              </div>
              <h1 className="text-2xl font-bold text-foreground mb-2">Verifying email...</h1>
              <p className="text-muted-foreground">Please wait while we verify your email address.</p>
            </>
          )}

          {status === "success" && (
            <>
              <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-primary/10 flex items-center justify-center">
                <CheckCircle className="w-8 h-8 text-primary" />
              </div>
              <h1 className="text-2xl font-bold text-foreground mb-2">Email Verified!</h1>
              <p className="text-muted-foreground mb-6">
                Your email has been successfully verified. You can now sign in to your account.
              </p>
              <Link to="/login">
                <Button className="w-full h-11">
                  Sign In
                </Button>
              </Link>
            </>
          )}

          {status === "error" && (
            <>
              <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-destructive/10 flex items-center justify-center">
                <XCircle className="w-8 h-8 text-destructive" />
              </div>
              <h1 className="text-2xl font-bold text-foreground mb-2">Verification Failed</h1>
              <p className="text-muted-foreground mb-6">
                {error || "Unable to verify your email address."}
              </p>
              <div className="space-y-3">
                <Link to="/login">
                  <Button className="w-full h-11">
                    Go to Login
                  </Button>
                </Link>
                <p className="text-sm text-muted-foreground">
                  Need a new verification link? Sign in and request a new one.
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
