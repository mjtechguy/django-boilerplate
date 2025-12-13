import { useDivisionTeams } from "@/lib/api/divisions";
import { Badge } from "@/components/ui/badge";
import { Users } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

interface DivisionTeamsListProps {
  divisionId: string;
}

export function DivisionTeamsList({ divisionId }: DivisionTeamsListProps) {
  const { data, isLoading, error } = useDivisionTeams(divisionId);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <TeamRowSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-muted-foreground">Failed to load teams</p>
      </div>
    );
  }

  if (!data || data.results.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-muted-foreground">
          No teams in this division yet
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {data.results.map((team: any) => (
        <TeamRow key={team.id} team={team} />
      ))}
    </div>
  );
}

function TeamRow({ team }: { team: any }) {
  return (
    <div className="flex items-center justify-between rounded-lg border p-4 hover:bg-accent/50 transition-colors">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
          <Users className="h-5 w-5 text-white" />
        </div>
        <div>
          <p className="font-medium">{team.name}</p>
          <p className="text-sm text-muted-foreground">
            {team.members_count || 0} members
          </p>
        </div>
      </div>
      {team.role && (
        <Badge variant="secondary">{team.role}</Badge>
      )}
    </div>
  );
}

function TeamRowSkeleton() {
  return (
    <div className="flex items-center justify-between rounded-lg border p-4">
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-lg" />
        <div className="space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-20" />
        </div>
      </div>
      <Skeleton className="h-6 w-16" />
    </div>
  );
}
