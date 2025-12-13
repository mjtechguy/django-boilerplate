import { createFileRoute } from "@tanstack/react-router";
import { Shield, CheckCircle, Clock, FileCode } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const Route = createFileRoute("/admin/_layout/policies/")({
  component: PoliciesPage,
});

function PoliciesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Policies"
        description="Cerbos authorization policy information"
      />

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
                <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Policy Status</p>
                <p className="text-xl font-bold">Active</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                <FileCode className="h-6 w-6 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Policies</p>
                <p className="text-xl font-bold">12</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-yellow-100 dark:bg-yellow-900/30">
                <Clock className="h-6 w-6 text-yellow-600 dark:text-yellow-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Last Updated</p>
                <p className="text-xl font-bold">2 hours ago</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Resource Policies
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[
              { name: "organization", version: "v1", actions: ["read", "create", "update", "delete"] },
              { name: "team", version: "v1", actions: ["read", "create", "update", "delete", "manage_members"] },
              { name: "user", version: "v1", actions: ["read", "invite", "deactivate", "impersonate"] },
              { name: "audit_log", version: "v1", actions: ["read", "export", "verify"] },
              { name: "webhook", version: "v1", actions: ["read", "create", "update", "delete", "test"] },
              { name: "settings", version: "v1", actions: ["read", "update"] },
            ].map((policy) => (
              <div
                key={policy.name}
                className="flex items-center justify-between rounded-lg border p-4"
              >
                <div>
                  <h4 className="font-medium">{policy.name}</h4>
                  <p className="text-sm text-muted-foreground">
                    Version: {policy.version}
                  </p>
                </div>
                <div className="flex flex-wrap gap-1">
                  {policy.actions.map((action) => (
                    <Badge key={action} variant="secondary" className="text-xs">
                      {action}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
