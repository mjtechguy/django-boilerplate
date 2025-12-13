import { createFileRoute } from "@tanstack/react-router";
import {
  Webhook,
  Plus,
  MoreHorizontal,
  Check,
  X,
  Clock,
  Send,
  ExternalLink,
} from "lucide-react";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export const Route = createFileRoute("/org/_layout/webhooks/")({
  component: WebhooksPage,
});

// Mock data - replace with API calls to /api/v1/webhooks
const webhooks = [
  {
    id: "1",
    name: "Slack Notifications",
    url: "https://hooks.slack.com/services/xxx",
    events: ["user.created", "team.created"],
    status: "active",
    lastDelivery: {
      status: "success",
      timestamp: "2024-12-07 14:32:15",
    },
  },
  {
    id: "2",
    name: "Analytics Pipeline",
    url: "https://api.analytics.example.com/webhook",
    events: ["user.login", "user.logout"],
    status: "active",
    lastDelivery: {
      status: "success",
      timestamp: "2024-12-07 13:45:02",
    },
  },
  {
    id: "3",
    name: "CRM Integration",
    url: "https://crm.example.com/hooks/inbound",
    events: ["user.created", "user.updated"],
    status: "inactive",
    lastDelivery: {
      status: "failed",
      timestamp: "2024-12-06 10:22:18",
    },
  },
  {
    id: "4",
    name: "Audit Log Backup",
    url: "https://backup.example.com/audit",
    events: ["audit.created"],
    status: "active",
    lastDelivery: {
      status: "success",
      timestamp: "2024-12-07 12:00:00",
    },
  },
];

function WebhooksPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Webhooks"
        description="Configure webhook endpoints to receive real-time notifications"
        actions={
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Add Webhook
          </Button>
        }
      />

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Webhook</TableHead>
                <TableHead>Events</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Delivery</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {webhooks.map((webhook) => (
                <WebhookRow key={webhook.id} webhook={webhook} />
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

interface WebhookRowProps {
  webhook: {
    id: string;
    name: string;
    url: string;
    events: string[];
    status: string;
    lastDelivery: {
      status: string;
      timestamp: string;
    };
  };
}

function WebhookRow({ webhook }: WebhookRowProps) {
  return (
    <TableRow>
      <TableCell>
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
            <Webhook className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="font-medium">{webhook.name}</p>
            <p className="text-sm text-muted-foreground flex items-center gap-1">
              {webhook.url.substring(0, 35)}...
              <ExternalLink className="h-3 w-3" />
            </p>
          </div>
        </div>
      </TableCell>
      <TableCell>
        <div className="flex gap-1 flex-wrap max-w-[200px]">
          {webhook.events.slice(0, 2).map((event) => (
            <Badge key={event} variant="secondary" className="text-xs">
              {event}
            </Badge>
          ))}
          {webhook.events.length > 2 && (
            <Badge variant="secondary" className="text-xs">
              +{webhook.events.length - 2}
            </Badge>
          )}
        </div>
      </TableCell>
      <TableCell>
        <Badge
          variant={webhook.status === "active" ? "default" : "secondary"}
          className={
            webhook.status === "active"
              ? "bg-green-500/10 text-green-600 dark:text-green-500 hover:bg-green-500/20"
              : ""
          }
        >
          {webhook.status === "active" ? (
            <Check className="mr-1 h-3 w-3" />
          ) : (
            <X className="mr-1 h-3 w-3" />
          )}
          {webhook.status}
        </Badge>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className={
              webhook.lastDelivery.status === "success"
                ? "border-green-500 text-green-600 dark:text-green-500"
                : "border-destructive text-destructive"
            }
          >
            {webhook.lastDelivery.status === "success" ? (
              <Check className="mr-1 h-3 w-3" />
            ) : (
              <X className="mr-1 h-3 w-3" />
            )}
            {webhook.lastDelivery.status}
          </Badge>
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {webhook.lastDelivery.timestamp.split(" ")[0]}
          </span>
        </div>
      </TableCell>
      <TableCell>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>
              <Send className="mr-2 h-4 w-4" />
              Send Test
            </DropdownMenuItem>
            <DropdownMenuItem>View Deliveries</DropdownMenuItem>
            <DropdownMenuItem>Edit Webhook</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              {webhook.status === "active" ? "Disable" : "Enable"}
            </DropdownMenuItem>
            <DropdownMenuItem className="text-destructive">
              Delete Webhook
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}
