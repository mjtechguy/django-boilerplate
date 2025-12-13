import { createFileRoute } from "@tanstack/react-router";
import { ArrowLeft, Users, UsersRound, Settings, CreditCard } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useDivision, useDivisionTeams } from "@/lib/api/divisions";
import { DivisionTeamsList } from "./-components/division-teams-list";

export const Route = createFileRoute("/org/_layout/divisions/$divisionId/")({
  component: DivisionDetailPage,
});

function DivisionDetailPage() {
  const { divisionId } = Route.useParams();
  const { data: division, isLoading: divisionLoading } = useDivision(divisionId);

  if (divisionLoading) {
    return <DivisionDetailSkeleton />;
  }

  if (!division) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Division not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/org/divisions">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <PageHeader
          title={division.name}
          description={`Division in ${division.org_name}`}
          actions={
            <Button variant="outline">
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </Button>
          }
        />
      </div>

      {/* Division Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Teams"
          value={division.teams_count || 0}
          icon={UsersRound}
        />
        <StatCard
          title="Members"
          value={division.members_count || 0}
          icon={Users}
        />
        <StatCard
          title="Billing Mode"
          value={division.billing_mode}
          icon={CreditCard}
          variant="text"
        />
        {division.license_tier && (
          <StatCard
            title="License Tier"
            value={division.license_tier}
            icon={Settings}
            variant="text"
          />
        )}
      </div>

      {/* Division Information */}
      <Card>
        <CardHeader>
          <CardTitle>Division Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <InfoRow label="Division ID" value={division.id} />
          <InfoRow label="Organization" value={division.org_name} />
          <InfoRow label="Billing Mode" value={division.billing_mode} />
          {division.billing_email && (
            <InfoRow label="Billing Email" value={division.billing_email} />
          )}
          {division.license_tier && (
            <InfoRow label="License Tier" value={division.license_tier} />
          )}
          <InfoRow
            label="Created"
            value={new Date(division.created_at).toLocaleDateString()}
          />
        </CardContent>
      </Card>

      {/* Teams in Division */}
      <Card>
        <CardHeader>
          <CardTitle>Teams</CardTitle>
        </CardHeader>
        <CardContent>
          <DivisionTeamsList divisionId={divisionId} />
        </CardContent>
      </Card>
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ElementType;
  variant?: "number" | "text";
}

function StatCard({ title, value, icon: Icon, variant = "number" }: StatCardProps) {
  const displayValue =
    variant === "number" && typeof value === "number"
      ? value.toLocaleString()
      : String(value);

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">{displayValue}</p>
          </div>
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Icon className="h-6 w-6 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface InfoRowProps {
  label: string;
  value: string | number;
}

function InfoRow({ label, value }: InfoRowProps) {
  return (
    <div className="flex items-center justify-between border-b pb-2 last:border-0">
      <span className="text-sm font-medium text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}

function DivisionDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Skeleton className="h-10 w-10" />
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-32" />
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
    </div>
  );
}
