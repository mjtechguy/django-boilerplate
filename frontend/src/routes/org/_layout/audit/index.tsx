import { createFileRoute } from "@tanstack/react-router";
import { FileText, Download, Filter, Search, Clock } from "lucide-react";
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

export const Route = createFileRoute("/org/_layout/audit/")({
  component: OrgAuditPage,
});

// Mock data - replace with API calls
const auditLogs = [
  {
    id: "1",
    timestamp: "2024-12-07 14:32:15",
    actor: "alice@example.com",
    action: "user.invite",
    resource: "john.doe@example.com",
    result: "success",
  },
  {
    id: "2",
    timestamp: "2024-12-07 13:45:02",
    actor: "bob@example.com",
    action: "team.create",
    resource: "Marketing",
    result: "success",
  },
  {
    id: "3",
    timestamp: "2024-12-07 12:18:44",
    actor: "alice@example.com",
    action: "webhook.create",
    resource: "Slack Integration",
    result: "success",
  },
  {
    id: "4",
    timestamp: "2024-12-07 11:05:31",
    actor: "carol@example.com",
    action: "user.update",
    resource: "david@example.com",
    result: "success",
  },
  {
    id: "5",
    timestamp: "2024-12-07 10:22:18",
    actor: "alice@example.com",
    action: "settings.update",
    resource: "organization_name",
    result: "success",
  },
  {
    id: "6",
    timestamp: "2024-12-06 16:45:00",
    actor: "bob@example.com",
    action: "user.remove",
    resource: "inactive@example.com",
    result: "success",
  },
  {
    id: "7",
    timestamp: "2024-12-06 15:12:33",
    actor: "unknown",
    action: "auth.login_failed",
    resource: "alice@example.com",
    result: "failure",
  },
];

const actionLabels: Record<string, string> = {
  "user.invite": "User Invited",
  "user.update": "User Updated",
  "user.remove": "User Removed",
  "team.create": "Team Created",
  "team.update": "Team Updated",
  "team.delete": "Team Deleted",
  "webhook.create": "Webhook Created",
  "webhook.update": "Webhook Updated",
  "settings.update": "Settings Updated",
  "auth.login_failed": "Login Failed",
};

function OrgAuditPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Logs"
        description="Track all activity within your organization"
        actions={
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export Logs
          </Button>
        }
      />

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder="Search by actor or resource..." className="pl-9" />
            </div>
            <Select defaultValue="all">
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
            <Select defaultValue="7d">
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
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Actor</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead>Result</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {auditLogs.map((log) => (
                <AuditLogRow key={log.id} log={log} />
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Pagination would go here */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Showing 7 of 1,234 entries
        </p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled>
            Previous
          </Button>
          <Button variant="outline" size="sm">
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}

interface AuditLogRowProps {
  log: {
    id: string;
    timestamp: string;
    actor: string;
    action: string;
    resource: string;
    result: string;
  };
}

function AuditLogRow({ log }: AuditLogRowProps) {
  return (
    <TableRow>
      <TableCell className="font-mono text-sm">{log.timestamp}</TableCell>
      <TableCell>{log.actor}</TableCell>
      <TableCell>
        <Badge variant="outline" className="font-normal">
          <FileText className="mr-1 h-3 w-3" />
          {actionLabels[log.action] || log.action}
        </Badge>
      </TableCell>
      <TableCell className="text-muted-foreground">{log.resource}</TableCell>
      <TableCell>
        <Badge
          variant={log.result === "success" ? "default" : "destructive"}
          className={
            log.result === "success"
              ? "bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20"
              : ""
          }
        >
          {log.result}
        </Badge>
      </TableCell>
    </TableRow>
  );
}
