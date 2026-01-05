import { AlertCircle, Loader2, AlertTriangle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useRevokeApiKey } from "@/lib/api/api-keys";
import type { UserAPIKey } from "@/lib/api/api-keys/types";
import { toast } from "sonner";

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
  const revokeMutation = useRevokeApiKey();

  const handleRevoke = async () => {
    if (!apiKey) return;

    try {
      await revokeMutation.mutateAsync(apiKey.id);
      toast.success("API key revoked successfully");
      onOpenChange(false);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to revoke API key"
      );
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
            Revoke API Key
          </DialogTitle>
          <DialogDescription>
            This action cannot be undone. The API key will be permanently
            disabled.
          </DialogDescription>
        </DialogHeader>

        {apiKey && (
          <div className="space-y-4">
            <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-destructive">
                    Warning: This is irreversible
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Once revoked, this API key will immediately stop working. Any
                    applications using this key will lose access.
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-lg border bg-muted/50 p-4">
              <p className="text-sm text-muted-foreground mb-1">
                API Key to revoke:
              </p>
              <p className="font-medium">{apiKey.name}</p>
              <p className="text-sm text-muted-foreground mt-1">
                {apiKey.prefix}••••••••
              </p>
            </div>
          </div>
        )}

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={revokeMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleRevoke}
            disabled={revokeMutation.isPending || !apiKey}
          >
            {revokeMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Revoking...
              </>
            ) : (
              "Revoke API Key"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
