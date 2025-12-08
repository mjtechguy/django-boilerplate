import { createFileRoute, redirect, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { RegisterForm } from "@/components/auth/register-form";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Shield, CheckCircle, Mail } from "lucide-react";

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
      <div className="min-h-screen flex items-center justify-center bg-[#0a0a0f]">
        <div className="w-full max-w-md p-8">
          <Skeleton className="mx-auto h-12 w-12 rounded-lg mb-6 bg-white/10" />
          <Skeleton className="mx-auto h-8 w-48 mb-2 bg-white/10" />
          <Skeleton className="mx-auto h-4 w-64 mb-8 bg-white/10" />
          <div className="space-y-4">
            <Skeleton className="h-10 w-full bg-white/10" />
            <Skeleton className="h-10 w-full bg-white/10" />
            <Skeleton className="h-10 w-full bg-white/10" />
            <Skeleton className="h-11 w-full bg-white/10" />
          </div>
        </div>
      </div>
    );
  }

  // Registration success state
  if (registrationComplete) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0a0f]">
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 via-transparent to-teal-500/5" />

        <div className="relative w-full max-w-md p-8">
          <Link to="/" className="flex items-center justify-center gap-2 mb-8">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <span className="text-white font-semibold text-xl">Platform</span>
          </Link>

          <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-emerald-500/10 flex items-center justify-center">
              <CheckCircle className="w-8 h-8 text-emerald-400" />
            </div>

            <h1 className="text-2xl font-bold text-white mb-2">Check your email</h1>
            <p className="text-slate-400 mb-6">
              We've sent a verification link to your email address. Please check your inbox.
            </p>

            <div className="p-4 rounded-lg bg-white/5 border border-white/10 mb-6">
              <div className="flex items-center gap-3 text-left">
                <Mail className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                <p className="text-sm text-slate-300">
                  Click the link in the email to verify your account and complete registration.
                </p>
              </div>
            </div>

            <Link to="/login">
              <Button className="w-full h-11 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white font-semibold">
                Go to Login
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0f]">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 via-transparent to-teal-500/5" />

      <div className="relative w-full max-w-md p-8">
        {/* Logo */}
        <Link to="/" className="flex items-center justify-center gap-2 mb-8">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <span className="text-white font-semibold text-xl">Platform</span>
        </Link>

        {/* Card */}
        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-white mb-2">Create an account</h1>
            <p className="text-slate-400">Get started with your free account</p>
          </div>

          {/* Registration Form */}
          <RegisterForm onSuccess={handleRegistrationSuccess} />

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/10" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-[#0a0a0f] text-slate-500">or</span>
            </div>
          </div>

          {/* SSO Registration */}
          <Button
            onClick={login}
            variant="outline"
            className="w-full h-11 bg-white/5 border-white/10 text-white hover:bg-white/10 hover:border-white/20 font-medium transition-all"
          >
            Continue with SSO
          </Button>

          {/* Login link */}
          <p className="mt-6 text-center text-sm text-slate-400">
            Already have an account?{" "}
            <Link
              to="/login"
              className="text-emerald-400 hover:text-emerald-300 font-medium transition-colors"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
