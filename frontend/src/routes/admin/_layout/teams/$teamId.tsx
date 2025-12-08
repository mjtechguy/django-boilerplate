import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { type ColumnDef } from "@tanstack/react-table";
import { ArrowLeft, Users2, Settings, Building2, User } from "lucide-react";
import { format } from "date-fns";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, DataTableColumnHeader } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useTeam, useTeamMembers, type TeamMember } from "@/lib/api/teams";
import { EditTeamDialog } from "./-components/edit-team-dialog";
import { DeleteTeamDialog } from "./-components/delete-team-dialog";

export const Route = createFileRoute("/admin/_layout/teams/$teamId")({
  component: TeamDetailPage,
});

function TeamDetailPage() {
  const { teamId } = Route.useParams();
  const { data: team, isLoading: teamLoading } = useTeam(teamId);
  const { data: membersData, isLoading: membersLoading } = useTeamMembers(teamId);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const memberColumns: ColumnDef<TeamMember>[] = [
    {
      accessorKey: "email",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Member" />
      ),
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
            <User className="h-4 w-4 text-primary" />
          </div>
          <div>
            <div className="font-medium">
              {row.original.first_name} {row.original.last_name}
            </div>
            <div className="text-xs text-muted-foreground">
              {row.original.email}
            </div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: "team_roles",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Roles" />
      ),
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.team_roles.length > 0 ? (
            row.original.team_roles.map((role) => (
              <Badge key={role} variant="secondary" className="capitalize">
                {role.replace(/_/g, " ")}
              </Badge>
            ))
          ) : (
            <span className="text-muted-foreground text-sm">Member</span>
          )}
        </div>
      ),
    },
    {
      accessorKey: "joined_at",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Joined" />
      ),
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {format(new Date(row.original.joined_at), "MMM d, yyyy")}
        </span>
      ),
    },
  ];

  if (teamLoading) {
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
          <Link to="/admin/teams">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <PageHeader
          title={team?.name ?? "Team"}
          description={`ID: ${teamId}`}
          actions={
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setEditOpen(true)}>
                <Settings className="mr-2 h-4 w-4" />
                Edit
              </Button>
              <Button
                variant="outline"
                className="text-destructive hover:text-destructive"
                onClick={() => setDeleteOpen(true)}
              >
                Delete
              </Button>
            </div>
          }
        />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Team Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Users2 className="h-5 w-5" />
              Team Details
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Name</span>
              <span className="font-medium">{team?.name}</span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground">Created</span>
              <span>
                {team?.created_at
                  ? format(new Date(team.created_at), "MMM d, yyyy")
                  : "-"}
              </span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground">Members</span>
              <span className="font-medium">{team?.members_count ?? 0}</span>
            </div>
          </CardContent>
        </Card>

        {/* Organization Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Building2 className="h-5 w-5" />
              Organization
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Name</span>
              <Link
                to="/admin/organizations/$orgId"
                params={{ orgId: team?.org ?? "" }}
                className="font-medium hover:underline"
              >
                {team?.org_name}
              </Link>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground">Organization ID</span>
              <span className="text-sm text-muted-foreground font-mono">
                {team?.org}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Team Members */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <User className="h-5 w-5" />
            Team Members
          </CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={memberColumns}
            data={membersData?.members ?? []}
            isLoading={membersLoading}
          />
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <EditTeamDialog
        team={team ?? null}
        open={editOpen}
        onOpenChange={setEditOpen}
      />

      {/* Delete Dialog */}
      <DeleteTeamDialog
        team={team ? { id: team.id, name: team.name, org_name: team.org_name } : null}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
      />
    </div>
  );
}
