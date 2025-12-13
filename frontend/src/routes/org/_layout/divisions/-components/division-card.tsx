import { Link } from "@tanstack/react-router";
import { Building, Users, UsersRound, MoreHorizontal, Trash2, Edit } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useDeleteDivision } from "@/lib/api/divisions";
import type { DivisionListItem } from "@/lib/api/divisions";

interface DivisionCardProps {
  division: DivisionListItem;
  orgId: string;
}

export function DivisionCard({ division, orgId }: DivisionCardProps) {
  const deleteMutation = useDeleteDivision(orgId);

  const handleDelete = () => {
    if (confirm(`Are you sure you want to delete "${division.name}"?`)) {
      deleteMutation.mutate(division.id);
    }
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
              <Building className="h-5 w-5 text-white" />
            </div>
            <div>
              <CardTitle className="text-base">{division.name}</CardTitle>
              {division.license_tier && (
                <Badge variant="secondary" className="mt-1 text-xs">
                  {division.license_tier}
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
              <DropdownMenuItem asChild>
                <Link to={`/org/divisions/${division.id}`}>View Details</Link>
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Edit className="mr-2 h-4 w-4" />
                Edit Division
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive"
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                {deleteMutation.isPending ? "Deleting..." : "Delete Division"}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Billing Mode</span>
            <Badge variant="outline">{division.billing_mode}</Badge>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <UsersRound className="h-4 w-4" />
              <span>{division.teams_count || 0} teams</span>
            </div>
            <div className="flex items-center gap-1">
              <Users className="h-4 w-4" />
              <span>{division.members_count || 0} members</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
