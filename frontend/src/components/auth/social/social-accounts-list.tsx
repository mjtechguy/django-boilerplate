import { Github, Trash2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useSocialAccounts, useDisconnectSocialAccount } from "@/lib/api/social";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";

export function SocialAccountsList() {
  const { data, isLoading } = useSocialAccounts();
  const disconnectMutation = useDisconnectSocialAccount();

  const handleDisconnect = async (accountId: number, provider: string) => {
    if (
      !confirm(`Are you sure you want to disconnect your ${provider} account?`)
    ) {
      return;
    }

    try {
      await disconnectMutation.mutateAsync(accountId);
      toast.success(`${provider} account disconnected`);
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to disconnect account"
      );
    }
  };

  const getProviderIcon = (provider: string) => {
    switch (provider) {
      case "google":
        return (
          <svg className="h-5 w-5" viewBox="0 0 24 24">
            <path
              fill="currentColor"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="currentColor"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="currentColor"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="currentColor"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
        );
      case "github":
        return <Github className="h-5 w-5" />;
      default:
        return null;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!data?.accounts.length) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-center text-sm text-muted-foreground">
            No connected social accounts
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          {data.accounts.map((account, index) => (
            <div key={account.id}>
              {index > 0 && <Separator className="my-4" />}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                    {getProviderIcon(account.provider)}
                  </div>
                  <div>
                    <p className="font-medium capitalize">{account.provider}</p>
                    <p className="text-sm text-muted-foreground">
                      Connected{" "}
                      {formatDistanceToNow(new Date(account.created_at), {
                        addSuffix: true,
                      })}
                    </p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    handleDisconnect(account.id, account.provider)
                  }
                  disabled={disconnectMutation.isPending}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
