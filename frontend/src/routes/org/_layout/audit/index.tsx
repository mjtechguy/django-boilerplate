import { createFileRoute } from "@tanstack/react-router";
import { FileText, Download, Filter, X } from "lucide-react";
import { format } from "date-fns";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useAuditLogs, type AuditLog, getAuditExportUrl } from "@/lib/api/audit";
import { EmptyState } from "@/components/shared/empty-state";
import { AuditLogFilters } from "@/components/shared/audit-log-filters";
import { useAuditFilters } from "@/hooks/use-audit-filters";

export const Route = createFileRoute("/org/_layout/audit/")({
  component: OrgAuditPage,
});

const actionColors: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  CREATE: "default",
  UPDATE: "secondary",
  DELETE: "destructive",
  READ: "outline",
  LOGIN: "default",
  LOGOUT: "secondary",
};

function OrgAuditPage() {
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

  const auditLogs = data?.results ?? [];

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
        description="Track all activity within your organization"
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
              Export Logs
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

      {/* Audit Log Table */}
      {!isLoading && auditLogs.length === 0 ? (
        <EmptyState
          icon={<FileText className="h-6 w-6 text-muted-foreground" />}
          title="No audit logs yet"
          description="Audit logs will appear here as organization activity occurs."
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Resource</TableHead>
                  <TableHead>IP Address</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                      Loading audit logs...
                    </TableCell>
                  </TableRow>
                ) : (
                  auditLogs.map((log) => (
                    <AuditLogRow key={log.id} log={log} />
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Pagination */}
      {!isLoading && auditLogs.length > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {auditLogs.length} {data?.count ? `of ${data.count}` : ""} entries
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={!data?.previous}>
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={!data?.next}>
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

interface AuditLogRowProps {
  log: AuditLog;
}

function AuditLogRow({ log }: AuditLogRowProps) {
  return (
    <TableRow>
      <TableCell className="font-mono text-sm">
        {format(new Date(log.timestamp), "MMM d, yyyy HH:mm:ss")}
      </TableCell>
      <TableCell>{log.actor_email ?? log.actor_id}</TableCell>
      <TableCell>
        <Badge variant={actionColors[log.action] ?? "outline"}>
          {log.action}
        </Badge>
      </TableCell>
      <TableCell className="text-sm">
        <span className="font-medium">{log.resource_type}</span>
        {log.resource_id && (
          <span className="text-muted-foreground ml-1">
            ({log.resource_id.slice(0, 8)}...)
          </span>
        )}
      </TableCell>
      <TableCell className="text-sm text-muted-foreground">
        {log.ip_address ?? "-"}
      </TableCell>
    </TableRow>
  );
}
