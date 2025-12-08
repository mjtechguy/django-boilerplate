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
import { useDeactivateUser } from "@/lib/api/users";

interface DeactivateUserDialogProps {
  user: { id: number; email: string; name: string } | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DeactivateUserDialog({
  user,
  open,
  onOpenChange,
}: DeactivateUserDialogProps) {
  const deactivateUser = useDeactivateUser();

  const handleDeactivate = async () => {
    if (!user) return;
    try {
      await deactivateUser.mutateAsync(user.id);
      onOpenChange(false);
    } catch (error) {
      console.error("Failed to deactivate user:", error);
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
              <DialogTitle>Deactivate User</DialogTitle>
              <DialogDescription>
                This will prevent the user from logging in.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>
        <div className="py-4">
          <p className="text-sm text-muted-foreground">
            Are you sure you want to deactivate{" "}
            <span className="font-semibold text-foreground">{user?.name || user?.email}</span>?
            They will no longer be able to access the platform.
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
            disabled={deactivateUser.isPending}
          >
            {deactivateUser.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Deactivate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
