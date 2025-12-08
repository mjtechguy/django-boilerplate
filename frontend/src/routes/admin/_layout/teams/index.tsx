import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { type ColumnDef } from "@tanstack/react-table";
import { MoreHorizontal, Users2 } from "lucide-react";
import { format } from "date-fns";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, DataTableColumnHeader } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useTeams, type TeamListItem } from "@/lib/api/teams";
import { useOrganizations } from "@/lib/api/organizations";
import { EmptyState } from "@/components/shared/empty-state";
import { CreateTeamDialog } from "./-components/create-team-dialog";
import { DeleteTeamDialog } from "./-components/delete-team-dialog";

export const Route = createFileRoute("/admin/_layout/teams/")({
  component: TeamsPage,
});

function TeamsPage() {
  const [orgFilter, setOrgFilter] = useState<string>("all");
  const { data, isLoading } = useTeams({ org_id: orgFilter === "all" ? undefined : orgFilter });
  const { data: orgsData } = useOrganizations({ status: "active" });
  const [deleteTeam, setDeleteTeam] = useState<{ id: string; name: string; org_name: string } | null>(null);

  const columns: ColumnDef<TeamListItem>[] = [
    {
      accessorKey: "name",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Team" />
      ),
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <Users2 className="h-4 w-4 text-primary" />
          </div>
          <div>
            <Link
              to="/admin/teams/$teamId"
              params={{ teamId: row.original.id }}
              className="font-medium hover:underline"
            >
              {row.original.name}
            </Link>
            <p className="text-xs text-muted-foreground truncate max-w-[200px]">
              {row.original.id}
            </p>
          </div>
        </div>
      ),
    },
    {
      accessorKey: "org_name",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Organization" />
      ),
      cell: ({ row }) => (
        <Link
          to="/admin/organizations/$orgId"
          params={{ orgId: row.original.org }}
          className="text-muted-foreground hover:underline"
        >
          {row.original.org_name}
        </Link>
      ),
    },
    {
      accessorKey: "members_count",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Members" />
      ),
      cell: ({ row }) => (
        <span className="text-muted-foreground">{row.original.members_count}</span>
      ),
    },
    {
      accessorKey: "created_at",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Created" />
      ),
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {format(new Date(row.original.created_at), "MMM d, yyyy")}
        </span>
      ),
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Actions</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link
                to="/admin/teams/$teamId"
                params={{ teamId: row.original.id }}
              >
                View details
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link
                to="/admin/teams/$teamId"
                params={{ teamId: row.original.id }}
                search={{ edit: true }}
              >
                Edit team
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => setDeleteTeam({
                id: row.original.id,
                name: row.original.name,
                org_name: row.original.org_name
              })}
            >
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Teams"
        description="Manage teams across all organizations"
        actions={<CreateTeamDialog />}
      />

      <div className="flex items-center gap-4">
        <div className="w-[250px]">
          <Select value={orgFilter} onValueChange={setOrgFilter}>
            <SelectTrigger>
              <SelectValue placeholder="Filter by organization" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All organizations</SelectItem>
              {orgsData?.results.map((org) => (
                <SelectItem key={org.id} value={org.id}>
                  {org.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {!isLoading && (!data?.results || data.results.length === 0) ? (
        <EmptyState
          icon={<Users2 className="h-6 w-6 text-muted-foreground" />}
          title="No teams yet"
          description={orgFilter !== "all" ? "No teams in this organization." : "Get started by creating your first team."}
          action={<CreateTeamDialog />}
        />
      ) : (
        <DataTable
          columns={columns}
          data={data?.results ?? []}
          isLoading={isLoading}
        />
      )}

      <DeleteTeamDialog
        team={deleteTeam}
        open={!!deleteTeam}
        onOpenChange={(open) => !open && setDeleteTeam(null)}
      />
    </div>
  );
}
