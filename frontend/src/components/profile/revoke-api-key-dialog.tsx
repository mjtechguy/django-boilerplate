import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { UserAPIKey } from "@/lib/api/api-keys/types";

interface RevokeApiKeyDialogProps {
  apiKey: UserAPIKey | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RevokeApiKeyDialog({
  apiKey,
  open,
  onOpenChange,
}: RevokeApiKeyDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Revoke API Key</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          This dialog will be implemented in subtask 2.3
        </p>
        {apiKey && (
          <p className="text-sm">
            Key to revoke: <strong>{apiKey.name}</strong>
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}
