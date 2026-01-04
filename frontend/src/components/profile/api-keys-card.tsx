import { useState } from "react";
import { Key, Plus, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useApiKeys } from "@/lib/api/api-keys";
import { CreateApiKeyDialog } from "./create-api-key-dialog";
import { RevokeApiKeyDialog } from "./revoke-api-key-dialog";
import { ApiKeyListItem } from "./api-key-list-item";
import type { UserAPIKey } from "@/lib/api/api-keys/types";

export function ApiKeysCard() {
  const { data, isLoading, error } = useApiKeys();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [keyToRevoke, setKeyToRevoke] = useState<UserAPIKey | null>(null);

  // Loading skeleton
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Key className="h-5 w-5" />
            API Keys
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 flex-1">
              <Skeleton className="h-10 w-10 rounded-lg" />
              <div className="space-y-2 flex-1">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-48" />
              </div>
            </div>
            <Skeleton className="h-9 w-20" />
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 flex-1">
              <Skeleton className="h-10 w-10 rounded-lg" />
              <div className="space-y-2 flex-1">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-48" />
              </div>
            </div>
            <Skeleton className="h-9 w-20" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Key className="h-5 w-5" />
            API Keys
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3 p-4 border border-destructive/50 rounded-lg bg-destructive/10">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <div>
              <p className="text-sm font-medium text-destructive">
                Failed to load API keys
              </p>
              <p className="text-sm text-muted-foreground">
                {error instanceof Error ? error.message : "An error occurred"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const apiKeys = data?.api_keys || [];

  // Empty state
  if (apiKeys.length === 0) {
    return (
      <>
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Key className="h-5 w-5" />
              API Keys
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-4">
                <Key className="h-8 w-8 text-muted-foreground" />
              </div>
              <p className="font-medium mb-1">No API keys yet</p>
              <p className="text-sm text-muted-foreground mb-4">
                Create an API key to access the API programmatically
              </p>
              <Button onClick={() => setIsCreateDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create API Key
              </Button>
            </div>
          </CardContent>
        </Card>

        <CreateApiKeyDialog
          open={isCreateDialogOpen}
          onOpenChange={setIsCreateDialogOpen}
        />
      </>
    );
  }

  // List of API keys
  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Key className="h-5 w-5" />
              API Keys
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsCreateDialogOpen(true)}
            >
              <Plus className="mr-2 h-4 w-4" />
              Create Key
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {apiKeys.map((apiKey, index) => (
            <div key={apiKey.id}>
              {index > 0 && <Separator className="my-4" />}
              <ApiKeyListItem
                apiKey={apiKey}
                onRevoke={setKeyToRevoke}
              />
            </div>
          ))}
        </CardContent>
      </Card>

      <CreateApiKeyDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
      />

      <RevokeApiKeyDialog
        apiKey={keyToRevoke}
        open={!!keyToRevoke}
        onOpenChange={(open) => !open && setKeyToRevoke(null)}
      />
    </>
  );
}
