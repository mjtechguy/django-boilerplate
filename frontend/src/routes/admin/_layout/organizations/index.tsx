import { useState, useEffect } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { type ColumnDef } from "@tanstack/react-table";
import { MoreHorizontal, Building2 } from "lucide-react";
import { format } from "date-fns";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, DataTableColumnHeader } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
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
import { useOrganizations, type OrgListItem } from "@/lib/api/organizations";
import { EmptyState } from "@/components/shared/empty-state";
import { CreateOrgDialog } from "./-components/create-org-dialog";
import { DeactivateOrgDialog } from "./-components/deactivate-org-dialog";

export const Route = createFileRoute("/admin/_layout/organizations/")({
  component: OrganizationsPage,
});

function OrganizationsPage() {
  const [searchInput, setSearchInput] = useState<string>("");
  const [debouncedSearch, setDebouncedSearch] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [licenseTierFilter, setLicenseTierFilter] = useState<string>("all");
  const { data, isLoading } = useOrganizations();
  const [deactivateOrg, setDeactivateOrg] = useState<{ id: string; name: string } | null>(null);

  // Debounce search input to avoid excessive API calls
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchInput]);

  const columns: ColumnDef<OrgListItem>[] = [
    {
      accessorKey: "name",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Organization" />
      ),
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <Building2 className="h-4 w-4 text-primary" />
          </div>
          <div>
            <Link
              to="/admin/organizations/$orgId"
              params={{ orgId: row.original.id }}
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
      accessorKey: "status",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Status" />
      ),
      cell: ({ row }) => {
        const status = row.original.status;
        return (
          <Badge variant={status === "active" ? "default" : "secondary"}>
            {status}
          </Badge>
        );
      },
    },
    {
      accessorKey: "license_tier",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="License" />
      ),
      cell: ({ row }) => (
        <span className="capitalize">{row.original.license_tier}</span>
      ),
    },
    {
      accessorKey: "teams_count",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Teams" />
      ),
      cell: ({ row }) => (
        <span className="text-muted-foreground">{row.original.teams_count}</span>
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
                to="/admin/organizations/$orgId"
                params={{ orgId: row.original.id }}
              >
                View details
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link
                to="/admin/organizations/$orgId"
                params={{ orgId: row.original.id }}
                search={{ edit: true }}
              >
                Edit organization
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link
                to="/admin/organizations/$orgId"
                params={{ orgId: row.original.id }}
                search={{ tab: "license" }}
              >
                Manage license
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => setDeactivateOrg({ id: row.original.id, name: row.original.name })}
            >
              Deactivate
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Organizations"
        description="Manage platform organizations and their licenses"
        actions={<CreateOrgDialog />}
      />

      {!isLoading && (!data?.results || data.results.length === 0) ? (
        <EmptyState
          icon={<Building2 className="h-6 w-6 text-muted-foreground" />}
          title="No organizations yet"
          description="Get started by creating your first organization."
          action={<CreateOrgDialog />}
        />
      ) : (
        <DataTable
          columns={columns}
          data={data?.results ?? []}
          isLoading={isLoading}
        />
      )}

      <DeactivateOrgDialog
        org={deactivateOrg}
        open={!!deactivateOrg}
        onOpenChange={(open) => !open && setDeactivateOrg(null)}
      />
    </div>
  );
}
