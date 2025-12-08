import { createFileRoute } from "@tanstack/react-router";
import { Plus, MoreHorizontal, Mail, Shield, Clock } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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
import { Card, CardContent } from "@/components/ui/card";

export const Route = createFileRoute("/org/_layout/users/")({
  component: OrgUsersPage,
});

// Mock data - replace with API calls
const users = [
  {
    id: "1",
    name: "Alice Johnson",
    email: "alice@example.com",
    role: "org_admin",
    teams: ["Engineering", "Design"],
    lastActive: "Just now",
    status: "active",
  },
  {
    id: "2",
    name: "Bob Smith",
    email: "bob@example.com",
    role: "team_admin",
    teams: ["Marketing"],
    lastActive: "5 min ago",
    status: "active",
  },
  {
    id: "3",
    name: "Carol Williams",
    email: "carol@example.com",
    role: "org_member",
    teams: ["Sales", "Support"],
    lastActive: "2 hours ago",
    status: "active",
  },
  {
    id: "4",
    name: "David Brown",
    email: "david@example.com",
    role: "org_member",
    teams: ["Engineering"],
    lastActive: "1 day ago",
    status: "inactive",
  },
  {
    id: "5",
    name: "Eva Martinez",
    email: "eva@example.com",
    role: "billing_admin",
    teams: ["Finance"],
    lastActive: "3 hours ago",
    status: "active",
  },
];

const roleLabels: Record<string, string> = {
  org_admin: "Org Admin",
  team_admin: "Team Admin",
  org_member: "Member",
  billing_admin: "Billing Admin",
};

function OrgUsersPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Users"
        description="Manage organization members and their roles"
        actions={
          <div className="flex gap-2">
            <Button variant="outline">
              <Mail className="mr-2 h-4 w-4" />
              Invite User
            </Button>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Add User
            </Button>
          </div>
        }
      />

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Teams</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Active</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user) => (
                <UserRow key={user.id} user={user} />
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

interface UserRowProps {
  user: {
    id: string;
    name: string;
    email: string;
    role: string;
    teams: string[];
    lastActive: string;
    status: string;
  };
}

function UserRow({ user }: UserRowProps) {
  const initials = user.name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <TableRow>
      <TableCell>
        <div className="flex items-center gap-3">
          <Avatar className="h-9 w-9">
            <AvatarFallback className="bg-gradient-to-br from-emerald-500 to-teal-600 text-white text-xs">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div>
            <p className="font-medium">{user.name}</p>
            <p className="text-sm text-muted-foreground">{user.email}</p>
          </div>
        </div>
      </TableCell>
      <TableCell>
        <Badge variant="outline" className="font-normal">
          {user.role === "org_admin" && <Shield className="mr-1 h-3 w-3" />}
          {roleLabels[user.role] || user.role}
        </Badge>
      </TableCell>
      <TableCell>
        <div className="flex gap-1 flex-wrap">
          {user.teams.slice(0, 2).map((team) => (
            <Badge key={team} variant="secondary" className="text-xs">
              {team}
            </Badge>
          ))}
          {user.teams.length > 2 && (
            <Badge variant="secondary" className="text-xs">
              +{user.teams.length - 2}
            </Badge>
          )}
        </div>
      </TableCell>
      <TableCell>
        <Badge
          variant={user.status === "active" ? "default" : "secondary"}
          className={
            user.status === "active"
              ? "bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20"
              : ""
          }
        >
          {user.status}
        </Badge>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-1 text-sm text-muted-foreground">
          <Clock className="h-3 w-3" />
          {user.lastActive}
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
            <DropdownMenuItem>View Profile</DropdownMenuItem>
            <DropdownMenuItem>Edit Roles</DropdownMenuItem>
            <DropdownMenuItem>Manage Teams</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive">
              Remove User
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}
