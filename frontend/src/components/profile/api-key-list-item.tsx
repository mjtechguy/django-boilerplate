import { Key } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDistanceToNow } from "date-fns";
import type { UserAPIKey } from "@/lib/api/api-keys/types";

interface ApiKeyListItemProps {
  apiKey: UserAPIKey;
  onRevoke: (apiKey: UserAPIKey) => void;
}

export function ApiKeyListItem({ apiKey, onRevoke }: ApiKeyListItemProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <Key className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <p className="font-medium">{apiKey.name}</p>
            {apiKey.revoked ? (
              <Badge variant="destructive" className="text-xs">
                Revoked
              </Badge>
            ) : (
              <Badge variant="secondary" className="text-xs">
                Active
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground">
            {apiKey.prefix}••••••••
            {" · "}
            Created{" "}
            {formatDistanceToNow(new Date(apiKey.created), {
              addSuffix: true,
            })}
          </p>
        </div>
      </div>
      {!apiKey.revoked && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => onRevoke(apiKey)}
        >
          Revoke
        </Button>
      )}
    </div>
  );
}
