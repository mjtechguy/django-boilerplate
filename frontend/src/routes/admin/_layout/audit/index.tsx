import { createFileRoute } from "@tanstack/react-router";
import { type ColumnDef } from "@tanstack/react-table";
import { Download, FileText, Filter } from "lucide-react";
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
import { AuditLogFilters } from "./-components/audit-log-filters";
import { useAuditFilters } from "./-hooks/use-audit-filters";

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
  } = useAuditFilters();

  const { data, isLoading } = useAuditLogs(appliedFilters);

  const handleExport = () => {
    window.open(getAuditExportUrl(appliedFilters), "_blank");
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
                <Button variant="outline">
                  <Filter className="mr-2 h-4 w-4" />
                  Filter
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
