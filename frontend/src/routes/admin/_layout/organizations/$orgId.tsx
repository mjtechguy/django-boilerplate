import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, Building2, Settings, Shield, Users, Layers } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useOrganization, useOrgLicense } from "@/lib/api/organizations";
import { EditOrgDialog } from "./-components/edit-org-dialog";
import { DeactivateOrgDialog } from "./-components/deactivate-org-dialog";

export const Route = createFileRoute("/admin/_layout/organizations/$orgId")({
  component: OrganizationDetailPage,
});

function OrganizationDetailPage() {
  const { orgId } = Route.useParams();
  const { data: org, isLoading: orgLoading } = useOrganization(orgId);
  const { data: license, isLoading: licenseLoading } = useOrgLicense(orgId);
  const [editOpen, setEditOpen] = useState(false);
  const [deactivateOpen, setDeactivateOpen] = useState(false);

  if (orgLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/admin/organizations">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <PageHeader
          title={org?.name ?? "Organization"}
          description={`ID: ${orgId}`}
          actions={
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setEditOpen(true)}>
                <Settings className="mr-2 h-4 w-4" />
                Edit
              </Button>
              {org?.status === "active" && (
                <Button
                  variant="outline"
                  className="text-destructive hover:text-destructive"
                  onClick={() => setDeactivateOpen(true)}
                >
                  Deactivate
                </Button>
              )}
            </div>
          }
        />
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Organization Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Building2 className="h-5 w-5" />
              Organization Details
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Status</span>
              <Badge variant={org?.status === "active" ? "default" : "secondary"}>
                {org?.status}
              </Badge>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground">Created</span>
              <span>
                {org?.created_at
                  ? new Date(org.created_at).toLocaleDateString()
                  : "-"}
              </span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground">Last Updated</span>
              <span>
                {org?.updated_at
                  ? new Date(org.updated_at).toLocaleDateString()
                  : "-"}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* License Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Shield className="h-5 w-5" />
              License & Features
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {licenseLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            ) : (
              <>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">License Tier</span>
                  <Badge variant="outline" className="capitalize">
                    {license?.tier ?? org?.license_tier}
                  </Badge>
                </div>
                <Separator />
                <div>
                  <span className="text-muted-foreground block mb-2">
                    Feature Flags
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {license?.feature_flags &&
                      Object.entries(license.feature_flags).map(
                        ([key, enabled]) => (
                          <Badge
                            key={key}
                            variant={enabled ? "default" : "secondary"}
                          >
                            {key.replace(/_/g, " ")}
                          </Badge>
                        )
                      )}
                    {!license?.feature_flags && (
                      <span className="text-sm text-muted-foreground">
                        No feature flags configured
                      </span>
                    )}
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Statistics */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Layers className="h-5 w-5" />
              Statistics
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span className="text-muted-foreground flex items-center gap-2">
                <Users className="h-4 w-4" />
                Teams
              </span>
              <span className="font-medium">{org?.teams_count ?? 0}</span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground flex items-center gap-2">
                <Users className="h-4 w-4" />
                Members
              </span>
              <span className="font-medium">{org?.members_count ?? 0}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Edit Dialog */}
      <EditOrgDialog
        org={org ?? null}
        open={editOpen}
        onOpenChange={setEditOpen}
      />

      {/* Deactivate Dialog */}
      <DeactivateOrgDialog
        org={org ? { id: org.id, name: org.name } : null}
        open={deactivateOpen}
        onOpenChange={setDeactivateOpen}
      />
    </div>
  );
}
