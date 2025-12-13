import { createFileRoute } from "@tanstack/react-router";
import { Building, Plus } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { DivisionsList } from "./-components/divisions-list";
import { CreateDivisionDialog } from "./-components/create-division-dialog";
import { useState } from "react";

export const Route = createFileRoute("/org/_layout/divisions/")({
  component: DivisionsPage,
});

function DivisionsPage() {
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  // TODO: Get orgId from route params or org context
  // For now using placeholder - will be connected when org routing is implemented
  const orgId = "placeholder-org-id";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Divisions"
        description="Manage divisions within your organization"
        actions={
          <Button onClick={() => setCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Division
          </Button>
        }
      />

      <DivisionsList orgId={orgId} />

      <CreateDivisionDialog
        orgId={orgId}
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
      />
    </div>
  );
}
