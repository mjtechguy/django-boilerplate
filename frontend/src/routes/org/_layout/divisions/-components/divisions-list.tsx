import { useOrgDivisions } from "@/lib/api/divisions";
import { DivisionCard } from "./division-card";
import { Skeleton } from "@/components/ui/skeleton";

interface DivisionsListProps {
  orgId: string;
}

export function DivisionsList({ orgId }: DivisionsListProps) {
  const { data, isLoading, error } = useOrgDivisions(orgId);

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <DivisionCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Failed to load divisions</p>
      </div>
    );
  }

  if (!data || data.results.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">
          No divisions found. Create your first division to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {data.results.map((division) => (
        <DivisionCard key={division.id} division={division} orgId={orgId} />
      ))}
    </div>
  );
}

function DivisionCardSkeleton() {
  return (
    <div className="rounded-lg border p-6 space-y-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-3 w-16" />
          </div>
        </div>
        <Skeleton className="h-8 w-8 rounded-md" />
      </div>
      <Skeleton className="h-4 w-full" />
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-20" />
      </div>
    </div>
  );
}
