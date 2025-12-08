import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { type ColumnDef } from "@tanstack/react-table";
import { ArrowLeft, User, Settings, Building2, Shield, Send, Mail, Trash2 } from "lucide-react";
import { format } from "date-fns";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, DataTableColumnHeader } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useUser, useResendInvite, type UserMembership } from "@/lib/api/users";
import { EditUserDialog } from "./-components/edit-user-dialog";
import { DeactivateUserDialog } from "./-components/deactivate-user-dialog";
import { AddMembershipDialog } from "./-components/add-membership-dialog";
import { EditMembershipDialog } from "./-components/edit-membership-dialog";
import { RemoveMembershipDialog } from "./-components/remove-membership-dialog";

export const Route = createFileRoute("/admin/_layout/users/$userId")({
  component: UserDetailPage,
});

function UserDetailPage() {
  const { userId } = Route.useParams();
  const { data: user, isLoading } = useUser(userId);
  const [editOpen, setEditOpen] = useState(false);
  const [deactivateOpen, setDeactivateOpen] = useState(false);
  const [removeMembershipOpen, setRemoveMembershipOpen] = useState(false);
  const [selectedMembership, setSelectedMembership] = useState<{
    id: string;
    org_name: string;
    team_name: string | null;
  } | null>(null);
  const resendInvite = useResendInvite();

  const handleRemoveMembership = (membership: UserMembership) => {
    setSelectedMembership({
      id: membership.id,
      org_name: membership.org_name,
      team_name: membership.team_name,
    });
    setRemoveMembershipOpen(true);
  };

  const isPendingOidc = user?.auth_provider === "oidc" && !user?.email_verified;

  const handleResendInvite = async () => {
    if (!user) return;
    try {
      await resendInvite.mutateAsync(user.id);
    } catch (error) {
      console.error("Failed to resend invite:", error);
    }
  };

  const membershipColumns: ColumnDef<UserMembership>[] = [
    {
      accessorKey: "org_name",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Organization" />
      ),
      cell: ({ row }) => (
        <Link
          to="/admin/organizations/$orgId"
          params={{ orgId: row.original.org }}
          className="font-medium hover:underline"
        >
          {row.original.org_name}
        </Link>
      ),
    },
    {
      accessorKey: "team_name",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Team" />
      ),
      cell: ({ row }) =>
        row.original.team_name ? (
          <Link
            to="/admin/teams/$teamId"
            params={{ teamId: row.original.team ?? "" }}
            className="hover:underline"
          >
            {row.original.team_name}
          </Link>
        ) : (
          <span className="text-muted-foreground">-</span>
        ),
    },
    {
      accessorKey: "org_roles",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Org Roles" />
      ),
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.org_roles.map((role) => (
            <Badge key={role} variant="secondary" className="capitalize text-xs">
              {role.replace(/_/g, " ")}
            </Badge>
          ))}
        </div>
      ),
    },
    {
      accessorKey: "team_roles",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Team Roles" />
      ),
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.team_roles.length > 0 ? (
            row.original.team_roles.map((role) => (
              <Badge key={role} variant="outline" className="capitalize text-xs">
                {role.replace(/_/g, " ")}
              </Badge>
            ))
          ) : (
            <span className="text-muted-foreground">-</span>
          )}
        </div>
      ),
    },
    {
      accessorKey: "created_at",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Joined" />
      ),
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {format(new Date(row.original.created_at), "MMM d, yyyy")}
        </span>
      ),
    },
    {
      id: "actions",
      header: () => <span className="sr-only">Actions</span>,
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <EditMembershipDialog membership={row.original} />
          <Button
            variant="ghost"
            size="sm"
            className="text-destructive hover:text-destructive"
            onClick={() => handleRemoveMembership(row.original)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];

  if (isLoading) {
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

  const userName = user?.first_name || user?.last_name
    ? `${user?.first_name} ${user?.last_name}`.trim()
    : user?.email;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/admin/users">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <PageHeader
          title={userName ?? "User"}
          description={user?.email}
          actions={
            <div className="flex gap-2">
              {isPendingOidc && (
                <Button
                  variant="outline"
                  onClick={handleResendInvite}
                  disabled={resendInvite.isPending}
                >
                  <Send className="mr-2 h-4 w-4" />
                  Resend Invite
                </Button>
              )}
              <Button variant="outline" onClick={() => setEditOpen(true)}>
                <Settings className="mr-2 h-4 w-4" />
                Edit
              </Button>
              {user?.is_active && (
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
        {/* User Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <User className="h-5 w-5" />
              User Details
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Status</span>
              <Badge variant={user?.is_active ? "default" : "secondary"}>
                {user?.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
            <Separator />
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Auth Provider</span>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="capitalize">
                  {user?.auth_provider}
                </Badge>
                {isPendingOidc && (
                  <Badge variant="secondary" className="text-xs">
                    Pending
                  </Badge>
                )}
              </div>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground">Joined</span>
              <span>
                {user?.date_joined
                  ? format(new Date(user.date_joined), "MMM d, yyyy")
                  : "-"}
              </span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground">Last Login</span>
              <span>
                {user?.last_login
                  ? format(new Date(user.last_login), "MMM d, yyyy HH:mm")
                  : "Never"}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Roles */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Shield className="h-5 w-5" />
              Platform Roles
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {user?.roles && user.roles.length > 0 ? (
                user.roles.map((role) => (
                  <Badge key={role} variant="default" className="capitalize">
                    {role.replace(/_/g, " ")}
                  </Badge>
                ))
              ) : (
                <span className="text-sm text-muted-foreground">
                  No platform roles assigned
                </span>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Contact */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Mail className="h-5 w-5" />
              Contact
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Email</span>
              <span className="font-mono text-sm">{user?.email}</span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground">Email Verified</span>
              <Badge variant={user?.email_verified ? "default" : "secondary"}>
                {user?.email_verified ? "Yes" : "No"}
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Memberships */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Building2 className="h-5 w-5" />
            Organization Memberships
          </CardTitle>
          {user && <AddMembershipDialog userId={user.id} />}
        </CardHeader>
        <CardContent>
          {user?.memberships && user.memberships.length > 0 ? (
            <DataTable
              columns={membershipColumns}
              data={user.memberships}
              isLoading={false}
            />
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              No organization memberships
            </p>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <EditUserDialog
        user={user ?? null}
        open={editOpen}
        onOpenChange={setEditOpen}
      />

      {/* Deactivate Dialog */}
      <DeactivateUserDialog
        user={user ? { id: user.id, email: user.email, name: userName ?? "" } : null}
        open={deactivateOpen}
        onOpenChange={setDeactivateOpen}
      />

      {/* Remove Membership Dialog */}
      <RemoveMembershipDialog
        membership={selectedMembership}
        open={removeMembershipOpen}
        onOpenChange={setRemoveMembershipOpen}
      />
    </div>
  );
}
