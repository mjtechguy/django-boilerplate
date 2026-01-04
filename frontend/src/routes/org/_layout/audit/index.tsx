import { createFileRoute } from "@tanstack/react-router";
import { FileText, Download, Filter, Search, Clock } from "lucide-react";
import { format } from "date-fns";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuditLogs, type AuditLog, getAuditExportUrl } from "@/lib/api/audit";
import { EmptyState } from "@/components/shared/empty-state";

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
  const { data, isLoading } = useAuditLogs();

  const handleExport = () => {
    window.open(getAuditExportUrl(), "_blank");
  };

  const auditLogs = data?.results ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Logs"
        description="Track all activity within your organization"
        actions={
          <Button variant="outline" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export Logs
          </Button>
        }
      />

      {/* Filters - will be wired up in subtask 4.2 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder="Search by actor or resource..." className="pl-9" disabled />
            </div>
            <Select defaultValue="all" disabled>
              <SelectTrigger className="w-[160px]">
                <Filter className="mr-2 h-4 w-4" />
                <SelectValue placeholder="Action type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Actions</SelectItem>
                <SelectItem value="user">User Actions</SelectItem>
                <SelectItem value="team">Team Actions</SelectItem>
                <SelectItem value="webhook">Webhook Actions</SelectItem>
                <SelectItem value="settings">Settings</SelectItem>
                <SelectItem value="auth">Authentication</SelectItem>
              </SelectContent>
            </Select>
            <Select defaultValue="7d" disabled>
              <SelectTrigger className="w-[140px]">
                <Clock className="mr-2 h-4 w-4" />
                <SelectValue placeholder="Time range" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="24h">Last 24 hours</SelectItem>
                <SelectItem value="7d">Last 7 days</SelectItem>
                <SelectItem value="30d">Last 30 days</SelectItem>
                <SelectItem value="90d">Last 90 days</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

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
