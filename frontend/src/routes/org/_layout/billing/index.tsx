import { createFileRoute } from "@tanstack/react-router";
import {
  CreditCard,
  Check,
  AlertCircle,
  Calendar,
  Users,
  Zap,
  Download,
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

export const Route = createFileRoute("/org/_layout/billing/")({
  component: BillingPage,
});

function BillingPage() {
  // Mock data - replace with API calls to /api/v1/orgs/{id}/license
  const license = {
    plan: "Business",
    status: "active",
    seats: {
      used: 47,
      total: 100,
    },
    apiCalls: {
      used: 12450,
      total: 50000,
    },
    renewalDate: "December 31, 2025",
    features: [
      "Unlimited teams",
      "Advanced audit logging",
      "Custom webhooks",
      "Priority support",
      "SSO/SAML integration",
    ],
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Billing & License"
        description="Manage your subscription and view usage"
        actions={
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Download Invoice
          </Button>
        }
      />

      {/* Current Plan */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Current Plan
            </CardTitle>
            <Badge
              className={
                license.status === "active"
                  ? "bg-green-500/10 text-green-600 dark:text-green-500"
                  : "bg-yellow-500/10 text-yellow-600 dark:text-yellow-500"
              }
            >
              {license.status === "active" ? (
                <Check className="mr-1 h-3 w-3" />
              ) : (
                <AlertCircle className="mr-1 h-3 w-3" />
              )}
              {license.status}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-baseline gap-2 mb-4">
            <span className="text-3xl font-bold">{license.plan}</span>
            <span className="text-muted-foreground">Plan</span>
          </div>

          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
            <Calendar className="h-4 w-4" />
            <span>Renews on {license.renewalDate}</span>
          </div>

          <Button>Upgrade Plan</Button>
        </CardContent>
      </Card>

      {/* Usage Stats */}
      <div className="grid gap-4 md:grid-cols-2">
        <UsageCard
          title="Seats"
          icon={Users}
          used={license.seats.used}
          total={license.seats.total}
          unit="users"
        />
        <UsageCard
          title="API Calls (Monthly)"
          icon={Zap}
          used={license.apiCalls.used}
          total={license.apiCalls.total}
          unit="calls"
        />
      </div>

      {/* Features */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Included Features</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2">
            {license.features.map((feature) => (
              <div key={feature} className="flex items-center gap-2">
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-green-500/10">
                  <Check className="h-3 w-3 text-green-600 dark:text-green-500" />
                </div>
                <span className="text-sm">{feature}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Billing History */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Billing History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <BillingHistoryItem
              date="Nov 1, 2024"
              description="Business Plan - Monthly"
              amount="$299.00"
              status="paid"
            />
            <Separator />
            <BillingHistoryItem
              date="Oct 1, 2024"
              description="Business Plan - Monthly"
              amount="$299.00"
              status="paid"
            />
            <Separator />
            <BillingHistoryItem
              date="Sep 1, 2024"
              description="Business Plan - Monthly"
              amount="$299.00"
              status="paid"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

interface UsageCardProps {
  title: string;
  icon: React.ElementType;
  used: number;
  total: number;
  unit: string;
}

function UsageCard({ title, icon: Icon, used, total, unit }: UsageCardProps) {
  const percentage = Math.round((used / total) * 100);
  const isWarning = percentage >= 80;

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Icon className="h-5 w-5 text-muted-foreground" />
            <span className="font-medium">{title}</span>
          </div>
          <Badge variant={isWarning ? "destructive" : "secondary"}>
            {percentage}%
          </Badge>
        </div>
        <div className="space-y-2">
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                isWarning ? "bg-yellow-500" : "bg-green-500"
              }`}
              style={{ width: `${percentage}%` }}
            />
          </div>
          <p className="text-sm text-muted-foreground">
            {used.toLocaleString()} of {total.toLocaleString()} {unit} used
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

interface BillingHistoryItemProps {
  date: string;
  description: string;
  amount: string;
  status: "paid" | "pending" | "failed";
}

function BillingHistoryItem({
  date,
  description,
  amount,
  status,
}: BillingHistoryItemProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="font-medium">{description}</p>
        <p className="text-sm text-muted-foreground">{date}</p>
      </div>
      <div className="flex items-center gap-3">
        <span className="font-medium">{amount}</span>
        <Badge
          variant="outline"
          className={
            status === "paid"
              ? "border-green-500 text-green-600 dark:text-green-500"
              : status === "failed"
                ? "border-destructive text-destructive"
                : ""
          }
        >
          {status}
        </Badge>
      </div>
    </div>
  );
}
