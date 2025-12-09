import { Shield, ShieldOff } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface MfaStatusBadgeProps {
  enabled: boolean;
  variant?: "default" | "outline";
}

export function MfaStatusBadge({
  enabled,
  variant = "default",
}: MfaStatusBadgeProps) {
  if (enabled) {
    return (
      <Badge variant={variant} className="border-emerald-500 text-emerald-600">
        <Shield className="mr-1 h-3 w-3" />
        MFA Enabled
      </Badge>
    );
  }

  return (
    <Badge variant="outline" className="border-slate-500 text-slate-600">
      <ShieldOff className="mr-1 h-3 w-3" />
      MFA Disabled
    </Badge>
  );
}
