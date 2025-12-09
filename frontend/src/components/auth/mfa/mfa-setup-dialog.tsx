import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, Shield, Copy, Check, Download } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useMfaSetup, useMfaConfirm } from "@/lib/api/mfa";
import { toast } from "sonner";

const verifyCodeSchema = z.object({
  code: z.string().length(6, "Code must be 6 digits"),
});

type VerifyCodeForm = z.infer<typeof verifyCodeSchema>;

interface MfaSetupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function MfaSetupDialog({
  open,
  onOpenChange,
  onSuccess,
}: MfaSetupDialogProps) {
  const [setupData, setSetupData] = useState<{
    secret: string;
    qr_code: string;
    backup_codes: string[];
  } | null>(null);
  const [showBackupCodes, setShowBackupCodes] = useState(false);
  const [copiedBackupCodes, setCopiedBackupCodes] = useState(false);

  const setupMutation = useMfaSetup();
  const confirmMutation = useMfaConfirm();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<VerifyCodeForm>({
    resolver: zodResolver(verifyCodeSchema),
  });

  const handleSetup = async () => {
    try {
      const data = await setupMutation.mutateAsync();
      setSetupData(data);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to setup MFA"
      );
    }
  };

  const onSubmit = async (data: VerifyCodeForm) => {
    try {
      await confirmMutation.mutateAsync(data.code);
      setShowBackupCodes(true);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Invalid code. Please try again."
      );
    }
  };

  const handleCopyBackupCodes = () => {
    if (setupData?.backup_codes) {
      navigator.clipboard.writeText(setupData.backup_codes.join("\n"));
      setCopiedBackupCodes(true);
      setTimeout(() => setCopiedBackupCodes(false), 2000);
      toast.success("Backup codes copied to clipboard");
    }
  };

  const handleDownloadBackupCodes = () => {
    if (setupData?.backup_codes) {
      const blob = new Blob([setupData.backup_codes.join("\n")], {
        type: "text/plain",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "mfa-backup-codes.txt";
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Backup codes downloaded");
    }
  };

  const handleComplete = () => {
    reset();
    setSetupData(null);
    setShowBackupCodes(false);
    onOpenChange(false);
    onSuccess?.();
    toast.success("MFA has been enabled successfully");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Enable Two-Factor Authentication
          </DialogTitle>
          <DialogDescription>
            {!setupData
              ? "Add an extra layer of security to your account"
              : showBackupCodes
                ? "Save your backup codes"
                : "Scan the QR code with your authenticator app"}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {!setupData && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Two-factor authentication (2FA) adds an extra layer of security
                to your account. You'll need an authenticator app like Google
                Authenticator, Authy, or 1Password.
              </p>
              <Button
                onClick={handleSetup}
                disabled={setupMutation.isPending}
                className="w-full"
              >
                {setupMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Setting up...
                  </>
                ) : (
                  "Begin Setup"
                )}
              </Button>
            </div>
          )}

          {setupData && !showBackupCodes && (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="flex justify-center rounded-lg bg-white p-4">
                <img
                  src={setupData.qr_code}
                  alt="QR Code"
                  className="h-48 w-48"
                />
              </div>

              <div className="space-y-2">
                <Label>Manual Entry Code</Label>
                <div className="flex gap-2">
                  <Input
                    value={setupData.secret}
                    readOnly
                    className="font-mono text-sm"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => {
                      navigator.clipboard.writeText(setupData.secret);
                      toast.success("Secret copied to clipboard");
                    }}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Can't scan the QR code? Enter this code manually in your app.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="code">Verification Code</Label>
                <Input
                  id="code"
                  placeholder="Enter 6-digit code"
                  maxLength={6}
                  {...register("code")}
                />
                {errors.code && (
                  <p className="text-sm text-red-500">{errors.code.message}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Enter the 6-digit code from your authenticator app to confirm
                  setup.
                </p>
              </div>

              <Button
                type="submit"
                disabled={confirmMutation.isPending}
                className="w-full"
              >
                {confirmMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  "Verify and Enable"
                )}
              </Button>
            </form>
          )}

          {setupData && showBackupCodes && (
            <div className="space-y-4">
              <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-4">
                <p className="text-sm font-medium text-amber-600 dark:text-amber-400">
                  Important: Save these backup codes
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Store these codes in a safe place. You can use them to access
                  your account if you lose your authenticator device.
                </p>
              </div>

              <div className="space-y-1 rounded-lg bg-muted p-4 font-mono text-sm">
                {setupData.backup_codes.map((code, index) => (
                  <div key={index}>{code}</div>
                ))}
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={handleCopyBackupCodes}
                  className="flex-1"
                >
                  {copiedBackupCodes ? (
                    <>
                      <Check className="mr-2 h-4 w-4" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="mr-2 h-4 w-4" />
                      Copy Codes
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={handleDownloadBackupCodes}
                  className="flex-1"
                >
                  <Download className="mr-2 h-4 w-4" />
                  Download
                </Button>
              </div>

              <Button onClick={handleComplete} className="w-full">
                I've Saved My Backup Codes
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
