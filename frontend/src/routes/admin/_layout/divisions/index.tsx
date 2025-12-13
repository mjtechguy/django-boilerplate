import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { type ColumnDef } from "@tanstack/react-table";
import { MoreHorizontal, Network } from "lucide-react";
import { format } from "date-fns";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, DataTableColumnHeader } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useDivisions, type DivisionListItem } from "@/lib/api/divisions";
import { EmptyState } from "@/components/shared/empty-state";
import { CreateDivisionDialog } from "./-components/create-division-dialog";
import { EditDivisionDialog } from "./-components/edit-division-dialog";
import { DeleteDivisionDialog } from "./-components/delete-division-dialog";

export const Route = createFileRoute("/admin/_layout/divisions/")({
  component: DivisionsPage,
});

function DivisionsPage() {
  const { data, isLoading } = useDivisions();
  const [editDivision, setEditDivision] = useState<DivisionListItem | null>(null);
  const [deleteDivision, setDeleteDivision] = useState<{ id: string; name: string } | null>(null);

  const columns: ColumnDef<DivisionListItem>[] = [
    {
      accessorKey: "name",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Division" />
      ),
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <Network className="h-4 w-4 text-primary" />
          </div>
          <div>
            <div className="font-medium">{row.original.name}</div>
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
          className="text-sm hover:underline"
        >
          {row.original.org_name}
        </Link>
      ),
    },
    {
      accessorKey: "billing_mode",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Billing Mode" />
      ),
      cell: ({ row }) => {
        const mode = row.original.billing_mode;
        return (
          <Badge variant={mode === "inherit" ? "secondary" : "default"}>
            {mode === "inherit" ? "Org Pays" : "Self Pay"}
          </Badge>
        );
      },
    },
    {
      accessorKey: "license_tier",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="License Tier" />
      ),
      cell: ({ row }) => (
        <span className="capitalize">{row.original.license_tier || "N/A"}</span>
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
                params={{ orgId: row.original.org }}
                search={{ tab: "divisions" }}
              >
                View in organization
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setEditDivision(row.original)}>
              Edit division
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => setDeleteDivision({ id: row.original.id, name: row.original.name })}
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
        title="Divisions"
        description="Manage divisions across all organizations"
        actions={<CreateDivisionDialog />}
      />

      {!isLoading && (!data?.results || data.results.length === 0) ? (
        <EmptyState
          icon={<Network className="h-6 w-6 text-muted-foreground" />}
          title="No divisions yet"
          description="Get started by creating your first division."
          action={<CreateDivisionDialog />}
        />
      ) : (
        <DataTable
          columns={columns}
          data={data?.results ?? []}
          isLoading={isLoading}
        />
      )}

      <EditDivisionDialog
        division={editDivision}
        open={!!editDivision}
        onOpenChange={(open) => !open && setEditDivision(null)}
      />

      <DeleteDivisionDialog
        division={deleteDivision}
        open={!!deleteDivision}
        onOpenChange={(open) => !open && setDeleteDivision(null)}
      />
    </div>
  );
}
