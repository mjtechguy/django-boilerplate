import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { type ColumnDef } from "@tanstack/react-table";
import { MoreHorizontal, Users, User, Send } from "lucide-react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useUsers, useResendInvite, type UserListItem } from "@/lib/api/users";
import { EmptyState } from "@/components/shared/empty-state";
import { CreateUserDialog } from "./-components/create-user-dialog";
import { DeactivateUserDialog } from "./-components/deactivate-user-dialog";

export const Route = createFileRoute("/admin/_layout/users/")({
  component: UsersPage,
});

function UsersPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [providerFilter, setProviderFilter] = useState<string>("all");
  const { data, isLoading } = useUsers({
    is_active: statusFilter === "active" ? true : statusFilter === "inactive" ? false : undefined,
    auth_provider: providerFilter === "all" ? undefined : providerFilter,
  });
  const [deactivateUser, setDeactivateUser] = useState<{ id: number; email: string; name: string } | null>(null);
  const resendInvite = useResendInvite();

  const handleResendInvite = async (userId: number) => {
    try {
      await resendInvite.mutateAsync(userId);
    } catch (error) {
      console.error("Failed to resend invite:", error);
    }
  };

  const columns: ColumnDef<UserListItem>[] = [
    {
      accessorKey: "email",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="User" />
      ),
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10">
            <User className="h-4 w-4 text-primary" />
          </div>
          <div>
            <Link
              to="/admin/users/$userId"
              params={{ userId: String(row.original.id) }}
              className="font-medium hover:underline"
            >
              {row.original.first_name || row.original.last_name
                ? `${row.original.first_name} ${row.original.last_name}`.trim()
                : row.original.email}
            </Link>
            <p className="text-xs text-muted-foreground">
              {row.original.email}
            </p>
          </div>
        </div>
      ),
    },
    {
      accessorKey: "is_active",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Status" />
      ),
      cell: ({ row }) => (
        <Badge variant={row.original.is_active ? "default" : "secondary"}>
          {row.original.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      accessorKey: "auth_provider",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Auth" />
      ),
      cell: ({ row }) => {
        const provider = row.original.auth_provider;
        const verified = row.original.email_verified;
        return (
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="capitalize">
              {provider}
            </Badge>
            {!verified && provider === "oidc" && (
              <Badge variant="secondary" className="text-xs">
                Pending
              </Badge>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: "roles",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Roles" />
      ),
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.roles.length > 0 ? (
            row.original.roles.slice(0, 2).map((role) => (
              <Badge key={role} variant="secondary" className="capitalize text-xs">
                {role.replace(/_/g, " ")}
              </Badge>
            ))
          ) : (
            <span className="text-muted-foreground text-sm">-</span>
          )}
          {row.original.roles.length > 2 && (
            <Badge variant="secondary" className="text-xs">
              +{row.original.roles.length - 2}
            </Badge>
          )}
        </div>
      ),
    },
    {
      accessorKey: "memberships_count",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Orgs" />
      ),
      cell: ({ row }) => (
        <span className="text-muted-foreground">{row.original.memberships_count}</span>
      ),
    },
    {
      accessorKey: "date_joined",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Joined" />
      ),
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {format(new Date(row.original.date_joined), "MMM d, yyyy")}
        </span>
      ),
    },
    {
      id: "actions",
      cell: ({ row }) => {
        const isPendingOidc = row.original.auth_provider === "oidc" && !row.original.email_verified;
        return (
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
                  to="/admin/users/$userId"
                  params={{ userId: String(row.original.id) }}
                >
                  View details
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link
                  to="/admin/users/$userId"
                  params={{ userId: String(row.original.id) }}
                  search={{ edit: true }}
                >
                  Edit user
                </Link>
              </DropdownMenuItem>
              {isPendingOidc && (
                <DropdownMenuItem onClick={() => handleResendInvite(row.original.id)}>
                  <Send className="mr-2 h-4 w-4" />
                  Resend invite
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              {row.original.is_active && (
                <DropdownMenuItem
                  className="text-destructive"
                  onClick={() =>
                    setDeactivateUser({
                      id: row.original.id,
                      email: row.original.email,
                      name: `${row.original.first_name} ${row.original.last_name}`.trim(),
                    })
                  }
                >
                  Deactivate
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Users"
        description="Manage platform users and their access"
        actions={<CreateUserDialog />}
      />

      <div className="flex items-center gap-4">
        <div className="w-[180px]">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger>
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="inactive">Inactive</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="w-[180px]">
          <Select value={providerFilter} onValueChange={setProviderFilter}>
            <SelectTrigger>
              <SelectValue placeholder="All providers" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All providers</SelectItem>
              <SelectItem value="local">Local</SelectItem>
              <SelectItem value="oidc">SSO/OIDC</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {!isLoading && (!data?.results || data.results.length === 0) ? (
        <EmptyState
          icon={<Users className="h-6 w-6 text-muted-foreground" />}
          title="No users yet"
          description="Get started by creating your first user."
          action={<CreateUserDialog />}
        />
      ) : (
        <DataTable
          columns={columns}
          data={data?.results ?? []}
          isLoading={isLoading}
        />
      )}

      <DeactivateUserDialog
        user={deactivateUser}
        open={!!deactivateUser}
        onOpenChange={(open) => !open && setDeactivateUser(null)}
      />
    </div>
  );
}
