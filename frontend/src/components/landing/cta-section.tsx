import { Link } from "@tanstack/react-router";
import { ArrowRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export function CTASection() {

  return (
    <section className="relative py-32 bg-[#0a0a0f] overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-[128px]" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-[128px]" />
      </div>

      <div className="relative max-w-4xl mx-auto px-6 text-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-emerald-500/10 to-teal-500/10 border border-emerald-500/20 mb-8">
          <Sparkles className="w-4 h-4 text-emerald-400" />
          <span className="text-sm text-emerald-300 font-medium">
            Start building today
          </span>
        </div>

        {/* Headline */}
        <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white mb-6">
          Ready to ship your
          <br />
          <span className="bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400 bg-clip-text text-transparent">
            next big idea?
          </span>
        </h2>

        {/* Description */}
        <p className="text-lg text-slate-400 max-w-xl mx-auto mb-10">
          Join thousands of developers building secure, scalable applications
          with our platform.
        </p>

        {/* CTA */}
        <Button
          size="lg"
          asChild
          className="group h-14 px-10 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white font-semibold text-lg rounded-xl shadow-lg shadow-emerald-500/25 transition-all duration-300 hover:shadow-emerald-500/40 hover:scale-[1.02]"
        >
          <Link to="/register">
            <span className="flex items-center gap-2">
              Get Started Free
              <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
            </span>
          </Link>
        </Button>

        {/* Trust indicators */}
        <p className="mt-6 text-sm text-slate-500">
          No credit card required · Free tier available · Cancel anytime
        </p>
      </div>
    </section>
  );
}
