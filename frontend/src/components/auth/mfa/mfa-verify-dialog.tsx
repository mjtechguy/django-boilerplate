import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, Shield } from "lucide-react";
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

const verifyCodeSchema = z.object({
  code: z.string().min(6, "Code must be at least 6 digits"),
});

type VerifyCodeForm = z.infer<typeof verifyCodeSchema>;

interface MfaVerifyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mfaToken: string;
  onVerify: (code: string) => Promise<void>;
  isLoading?: boolean;
}

export function MfaVerifyDialog({
  open,
  onOpenChange,
  onVerify,
  isLoading,
}: MfaVerifyDialogProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<VerifyCodeForm>({
    resolver: zodResolver(verifyCodeSchema),
  });

  const onSubmit = async (data: VerifyCodeForm) => {
    await onVerify(data.code);
    reset();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Two-Factor Authentication
          </DialogTitle>
          <DialogDescription>
            Enter the code from your authenticator app or use a backup code.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="code">Verification Code</Label>
            <Input
              id="code"
              placeholder="Enter 6-digit code"
              autoFocus
              {...register("code")}
            />
            {errors.code && (
              <p className="text-sm text-red-500">{errors.code.message}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Open your authenticator app and enter the 6-digit code.
            </p>
          </div>

          <Button type="submit" disabled={isLoading} className="w-full">
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Verifying...
              </>
            ) : (
              "Verify"
            )}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
