import { useEffect, useRef } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowRight, Shield, Zap, Users, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";

export function HeroSection() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Animated mesh gradient background
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let time = 0;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    const draw = () => {
      time += 0.002;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Create flowing gradient orbs
      const orbs = [
        { x: 0.2, y: 0.3, r: 400, color: "rgba(16, 185, 129, 0.15)" },
        { x: 0.8, y: 0.2, r: 350, color: "rgba(59, 130, 246, 0.12)" },
        { x: 0.5, y: 0.7, r: 450, color: "rgba(168, 85, 247, 0.1)" },
        { x: 0.9, y: 0.8, r: 300, color: "rgba(20, 184, 166, 0.12)" },
      ];

      orbs.forEach((orb, i) => {
        const offsetX = Math.sin(time + i * 1.5) * 50;
        const offsetY = Math.cos(time + i * 1.2) * 40;
        const x = orb.x * canvas.width + offsetX;
        const y = orb.y * canvas.height + offsetY;

        const gradient = ctx.createRadialGradient(x, y, 0, x, y, orb.r);
        gradient.addColorStop(0, orb.color);
        gradient.addColorStop(1, "transparent");

        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      });

      animationId = requestAnimationFrame(draw);
    };

    resize();
    draw();
    window.addEventListener("resize", resize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Animated background */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 z-0"
        style={{ background: "linear-gradient(to bottom, #0a0a0f, #0d1117)" }}
      />

      {/* Grain overlay */}
      <div
        className="absolute inset-0 z-[1] opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
        }}
      />

      {/* Grid pattern */}
      <div
        className="absolute inset-0 z-[1] opacity-[0.02]"
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                           linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
          backgroundSize: "64px 64px",
        }}
      />

      {/* Content */}
      <div className="relative z-10 max-w-6xl mx-auto px-6 py-24 text-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 backdrop-blur-sm mb-8 animate-fade-in">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-sm text-slate-300 font-medium tracking-wide">
            Enterprise-ready platform
          </span>
        </div>

        {/* Headline */}
        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight mb-6 animate-fade-in-up">
          <span className="text-white">Build secure apps</span>
          <br />
          <span className="bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400 bg-clip-text text-transparent">
            at lightning speed
          </span>
        </h1>

        {/* Subheadline */}
        <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed animate-fade-in-up animation-delay-100">
          The complete platform for authentication, authorization, and team management.
          Ship faster with enterprise-grade security built in.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16 animate-fade-in-up animation-delay-200">
          <Button
            size="lg"
            asChild
            className="group relative h-14 px-8 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white font-semibold text-lg rounded-xl shadow-lg shadow-emerald-500/25 transition-all duration-300 hover:shadow-emerald-500/40 hover:scale-[1.02]"
          >
            <Link to="/register">
              <span className="flex items-center gap-2">
                Get Started
                <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
              </span>
            </Link>
          </Button>
          <Button
            size="lg"
            variant="outline"
            className="h-14 px-8 bg-white/5 border-white/10 text-white hover:bg-white/10 hover:border-white/20 font-semibold text-lg rounded-xl backdrop-blur-sm transition-all duration-300"
          >
            View Documentation
          </Button>
        </div>

        {/* Feature pills */}
        <div className="flex flex-wrap items-center justify-center gap-3 animate-fade-in-up animation-delay-300">
          <FeaturePill icon={Shield} label="SSO & SAML" />
          <FeaturePill icon={Users} label="Team Management" />
          <FeaturePill icon={Lock} label="RBAC Policies" />
          <FeaturePill icon={Zap} label="Real-time Events" />
        </div>
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#0a0a0f] to-transparent z-[2]" />
    </section>
  );
}

function FeaturePill({ icon: Icon, label }: { icon: React.ElementType; label: string }) {
  return (
    <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 backdrop-blur-sm">
      <Icon className="w-4 h-4 text-emerald-400" />
      <span className="text-sm text-slate-300">{label}</span>
    </div>
  );
}
