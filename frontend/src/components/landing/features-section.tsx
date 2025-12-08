import {
  Shield,
  Users,
  Building2,
  Webhook,
  FileText,
  CreditCard,
  Lock,
  Zap,
  Globe,
} from "lucide-react";

const features = [
  {
    icon: Shield,
    title: "Enterprise SSO",
    description:
      "Seamless integration with Keycloak, Okta, Auth0, and any OIDC provider. SAML support included.",
    gradient: "from-emerald-500 to-teal-500",
  },
  {
    icon: Lock,
    title: "Fine-grained RBAC",
    description:
      "Policy-based access control with Cerbos. Define complex permissions without code changes.",
    gradient: "from-blue-500 to-cyan-500",
  },
  {
    icon: Building2,
    title: "Multi-tenancy",
    description:
      "Built-in organization and team management. Isolate data and permissions per tenant.",
    gradient: "from-violet-500 to-purple-500",
  },
  {
    icon: Users,
    title: "Team Management",
    description:
      "Create teams, assign roles, and manage members with an intuitive interface.",
    gradient: "from-pink-500 to-rose-500",
  },
  {
    icon: Webhook,
    title: "Webhooks",
    description:
      "Real-time event notifications to any endpoint. Retry logic and delivery tracking included.",
    gradient: "from-orange-500 to-amber-500",
  },
  {
    icon: FileText,
    title: "Audit Logging",
    description:
      "Comprehensive audit trail with integrity verification. Export and compliance-ready.",
    gradient: "from-teal-500 to-green-500",
  },
  {
    icon: CreditCard,
    title: "Billing Ready",
    description:
      "License management and usage tracking built-in. Stripe integration ready.",
    gradient: "from-indigo-500 to-blue-500",
  },
  {
    icon: Zap,
    title: "Real-time Updates",
    description:
      "WebSocket-powered live notifications. Keep your users informed instantly.",
    gradient: "from-yellow-500 to-orange-500",
  },
  {
    icon: Globe,
    title: "API-first",
    description:
      "RESTful API with OpenAPI documentation. Build integrations with confidence.",
    gradient: "from-cyan-500 to-blue-500",
  },
];

export function FeaturesSection() {
  return (
    <section className="relative py-32 bg-[#0a0a0f]">
      {/* Section header */}
      <div className="max-w-6xl mx-auto px-6 mb-20 text-center">
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6">
          Everything you need to{" "}
          <span className="bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
            ship faster
          </span>
        </h2>
        <p className="text-lg text-slate-400 max-w-2xl mx-auto">
          Stop rebuilding auth, permissions, and team management from scratch.
          Focus on what makes your product unique.
        </p>
      </div>

      {/* Features grid */}
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <FeatureCard key={feature.title} feature={feature} index={index} />
          ))}
        </div>
      </div>

      {/* Background decoration */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-radial from-emerald-500/5 via-transparent to-transparent rounded-full blur-3xl pointer-events-none" />
    </section>
  );
}

interface FeatureCardProps {
  feature: {
    icon: React.ElementType;
    title: string;
    description: string;
    gradient: string;
  };
  index: number;
}

function FeatureCard({ feature, index }: FeatureCardProps) {
  const Icon = feature.icon;

  return (
    <div
      className="group relative p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05] backdrop-blur-sm hover:bg-white/[0.04] hover:border-white/[0.1] transition-all duration-500"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* Icon */}
      <div
        className={`inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br ${feature.gradient} mb-4 shadow-lg group-hover:scale-110 transition-transform duration-300`}
      >
        <Icon className="w-6 h-6 text-white" />
      </div>

      {/* Content */}
      <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
      <p className="text-slate-400 text-sm leading-relaxed">
        {feature.description}
      </p>

      {/* Hover glow effect */}
      <div
        className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-[0.03] transition-opacity duration-500 pointer-events-none`}
      />
    </div>
  );
}
