import { Loader2, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useDeleteOrganization } from "@/lib/api/organizations";

interface DeactivateOrgDialogProps {
  org: { id: string; name: string } | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DeactivateOrgDialog({
  org,
  open,
  onOpenChange,
}: DeactivateOrgDialogProps) {
  const deleteOrg = useDeleteOrganization();

  const handleDeactivate = async () => {
    if (!org) return;
    try {
      await deleteOrg.mutateAsync(org.id);
      onOpenChange(false);
    } catch (error) {
      console.error("Failed to deactivate organization:", error);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-destructive/10">
              <AlertTriangle className="h-5 w-5 text-destructive" />
            </div>
            <div>
              <DialogTitle>Deactivate Organization</DialogTitle>
              <DialogDescription>
                This action cannot be easily undone.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>
        <div className="py-4">
          <p className="text-sm text-muted-foreground">
            Are you sure you want to deactivate{" "}
            <span className="font-semibold text-foreground">{org?.name}</span>?
            This will prevent all users in this organization from accessing the platform.
          </p>
        </div>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleDeactivate}
            disabled={deleteOrg.isPending}
          >
            {deleteOrg.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Deactivate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
