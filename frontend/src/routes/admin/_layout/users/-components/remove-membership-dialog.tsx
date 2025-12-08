import { Loader2, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useDeleteMembership } from "@/lib/api/memberships";

interface RemoveMembershipDialogProps {
  membership: {
    id: string;
    org_name: string;
    team_name: string | null;
  } | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function RemoveMembershipDialog({
  membership,
  open,
  onOpenChange,
  onSuccess,
}: RemoveMembershipDialogProps) {
  const deleteMembership = useDeleteMembership();

  const handleRemove = async () => {
    if (!membership) return;
    try {
      await deleteMembership.mutateAsync(membership.id);
      toast.success("Membership removed successfully");
      onOpenChange(false);
      onSuccess?.();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to remove membership";
      toast.error(message);
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
              <DialogTitle>Remove Membership</DialogTitle>
              <DialogDescription>
                This will remove the user from the organization.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>
        <div className="py-4">
          <p className="text-sm text-muted-foreground">
            Are you sure you want to remove the membership from{" "}
            <span className="font-semibold text-foreground">{membership?.org_name}</span>
            {membership?.team_name && (
              <>
                {" "}(Team: <span className="font-semibold text-foreground">{membership.team_name}</span>)
              </>
            )}
            ? The user will lose access to this organization.
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
            onClick={handleRemove}
            disabled={deleteMembership.isPending}
          >
            {deleteMembership.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Remove
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
