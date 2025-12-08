import { createFileRoute } from "@tanstack/react-router";
import { UsersRound, Plus, MoreHorizontal, Users, Shield } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export const Route = createFileRoute("/org/_layout/teams/")({
  component: TeamsPage,
});

// Mock data - replace with API calls
const teams = [
  {
    id: "1",
    name: "Engineering",
    description: "Core product development team",
    memberCount: 12,
    role: "team_admin",
  },
  {
    id: "2",
    name: "Marketing",
    description: "Brand and growth initiatives",
    memberCount: 6,
    role: "team_member",
  },
  {
    id: "3",
    name: "Sales",
    description: "Revenue and customer acquisition",
    memberCount: 8,
    role: "team_member",
  },
  {
    id: "4",
    name: "Support",
    description: "Customer success and support",
    memberCount: 5,
    role: "team_admin",
  },
  {
    id: "5",
    name: "Design",
    description: "Product design and UX",
    memberCount: 4,
    role: "team_member",
  },
  {
    id: "6",
    name: "Finance",
    description: "Financial operations and planning",
    memberCount: 3,
    role: "team_member",
  },
];

function TeamsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Teams"
        description="Manage your organization's teams and their members"
        actions={
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Create Team
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {teams.map((team) => (
          <TeamCard key={team.id} team={team} />
        ))}
      </div>
    </div>
  );
}

interface TeamCardProps {
  team: {
    id: string;
    name: string;
    description: string;
    memberCount: number;
    role: string;
  };
}

function TeamCard({ team }: TeamCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600">
              <UsersRound className="h-5 w-5 text-white" />
            </div>
            <div>
              <CardTitle className="text-base">{team.name}</CardTitle>
              {team.role === "team_admin" && (
                <Badge variant="secondary" className="mt-1 text-xs">
                  <Shield className="mr-1 h-3 w-3" />
                  Admin
                </Badge>
              )}
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>View Details</DropdownMenuItem>
              <DropdownMenuItem>Manage Members</DropdownMenuItem>
              <DropdownMenuItem>Edit Team</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-destructive">
                Delete Team
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4">{team.description}</p>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Users className="h-4 w-4" />
          <span>{team.memberCount} members</span>
        </div>
      </CardContent>
    </Card>
  );
}
