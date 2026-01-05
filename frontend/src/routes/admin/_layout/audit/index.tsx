import { createFileRoute } from "@tanstack/react-router";
import { type ColumnDef } from "@tanstack/react-table";
import { Download, FileText, Filter, X } from "lucide-react";
import { format } from "date-fns";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, DataTableColumnHeader } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useAuditLogs, type AuditLog, getAuditExportUrl } from "@/lib/api/audit";
import { EmptyState } from "@/components/shared/empty-state";
import { AuditLogFilters } from "@/components/shared/audit-log-filters";
import { useAuditFilters } from "@/hooks/use-audit-filters";

export const Route = createFileRoute("/admin/_layout/audit/")({
  component: AuditLogsPage,
});

const actionColors: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  CREATE: "default",
  UPDATE: "secondary",
  DELETE: "destructive",
  READ: "outline",
  LOGIN: "default",
  LOGOUT: "secondary",
};

const columns: ColumnDef<AuditLog>[] = [
  {
    accessorKey: "timestamp",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Timestamp" />
    ),
    cell: ({ row }) => (
      <span className="text-sm">
        {format(new Date(row.original.timestamp), "MMM d, yyyy HH:mm:ss")}
      </span>
    ),
  },
  {
    accessorKey: "action",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Action" />
    ),
    cell: ({ row }) => (
      <Badge variant={actionColors[row.original.action] ?? "outline"}>
        {row.original.action}
      </Badge>
    ),
  },
  {
    accessorKey: "actor_email",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Actor" />
    ),
    cell: ({ row }) => (
      <span className="text-sm">
        {row.original.actor_email ?? row.original.actor_id}
      </span>
    ),
  },
  {
    accessorKey: "resource_type",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Resource" />
    ),
    cell: ({ row }) => (
      <div className="text-sm">
        <span className="font-medium">{row.original.resource_type}</span>
        {row.original.resource_id && (
          <span className="text-muted-foreground ml-1">
            ({row.original.resource_id.slice(0, 8)}...)
          </span>
        )}
      </div>
    ),
  },
  {
    accessorKey: "ip_address",
    header: "IP Address",
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {row.original.ip_address ?? "-"}
      </span>
    ),
  },
];

function AuditLogsPage() {
  const {
    draftFilters,
    setDraftFilters,
    appliedFilters,
    applyFilters,
    clearFilters,
    clearFilter,
    activeFilterCount,
    hasActiveFilters,
  } = useAuditFilters();

  const { data, isLoading } = useAuditLogs(appliedFilters);

  const handleExport = () => {
    window.open(getAuditExportUrl(appliedFilters), "_blank");
  };

  // Helper to get human-readable filter labels
  const getFilterLabel = (key: string, value: string): string => {
    switch (key) {
      case "action":
        return `Action: ${value}`;
      case "resource_type":
        return `Resource: ${value}`;
      case "actor_id":
        return `Actor: ${value}`;
      case "start_date":
        return `From: ${format(new Date(value), "MMM d, yyyy")}`;
      case "end_date":
        return `To: ${format(new Date(value), "MMM d, yyyy")}`;
      default:
        return `${key}: ${value}`;
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Logs"
        description="View system-wide audit trail and activity logs"
        actions={
          <div className="flex gap-2">
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" className="relative">
                  <Filter className="mr-2 h-4 w-4" />
                  Filter
                  {hasActiveFilters && (
                    <Badge
                      variant="default"
                      className="ml-2 h-5 min-w-5 rounded-full px-1.5 text-xs"
                    >
                      {activeFilterCount}
                    </Badge>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-80">
                <AuditLogFilters
                  filters={draftFilters}
                  onFiltersChange={setDraftFilters}
                  onApply={applyFilters}
                  onClear={clearFilters}
                />
              </PopoverContent>
            </Popover>
            <Button variant="outline" onClick={handleExport}>
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
          </div>
        }
      />

      {hasActiveFilters && (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-muted/50 p-3">
          <span className="text-sm font-medium text-muted-foreground">
            Active filters:
          </span>
          {Object.entries(appliedFilters).map(([key, value]) => {
            if (!value) return null;
            return (
              <Badge
                key={key}
                variant="secondary"
                className="gap-1 pr-1 cursor-pointer hover:bg-secondary/80"
                onClick={() => clearFilter(key as keyof typeof appliedFilters)}
              >
                {getFilterLabel(key, value)}
                <X className="h-3 w-3" />
              </Badge>
            );
          })}
          <Button
            variant="ghost"
            size="sm"
            onClick={clearFilters}
            className="h-6 px-2 text-xs"
          >
            Clear all
          </Button>
        </div>
      )}

      {!isLoading && (!data?.results || data.results.length === 0) ? (
        <EmptyState
          icon={<FileText className="h-6 w-6 text-muted-foreground" />}
          title="No audit logs yet"
          description="Audit logs will appear here as system activity occurs."
        />
      ) : (
        <DataTable
          columns={columns}
          data={data?.results ?? []}
          isLoading={isLoading}
        />
      )}
    </div>
  );
}
