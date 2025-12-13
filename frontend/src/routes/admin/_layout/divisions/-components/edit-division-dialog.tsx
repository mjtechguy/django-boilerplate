import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useAdminUpdateDivision,
  updateDivisionInputSchema,
  type UpdateDivisionInput,
  type DivisionListItem,
} from "@/lib/api/divisions";

interface EditDivisionDialogProps {
  division: DivisionListItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EditDivisionDialog({ division, open, onOpenChange }: EditDivisionDialogProps) {
  const updateDivision = useAdminUpdateDivision(division?.id ?? "");

  const form = useForm<UpdateDivisionInput>({
    resolver: zodResolver(updateDivisionInputSchema),
    defaultValues: {
      name: "",
      billing_mode: "inherit",
      license_tier: "free",
    },
  });

  // Reset form when division changes
  useEffect(() => {
    if (division) {
      form.reset({
        name: division.name,
        billing_mode: division.billing_mode,
        license_tier: division.license_tier || "free",
      });
    }
  }, [division, form]);

  const onSubmit = async (data: UpdateDivisionInput) => {
    if (!division) return;
    try {
      await updateDivision.mutateAsync(data);
      toast.success("Division updated successfully");
      onOpenChange(false);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to update division";
      toast.error(message);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Edit Division</DialogTitle>
            <DialogDescription>
              Update the division details and settings.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Division Name</Label>
              <Input
                id="name"
                placeholder="Enter division name"
                {...form.register("name")}
              />
              {form.formState.errors.name && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.name.message}
                </p>
              )}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="billing_mode">Billing Mode</Label>
              <Select
                value={form.watch("billing_mode")}
                onValueChange={(value: "inherit" | "independent") =>
                  form.setValue("billing_mode", value)
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select billing mode" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="inherit">Inherit (Org Pays)</SelectItem>
                  <SelectItem value="independent">Independent (Self Pay)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="license_tier">License Tier</Label>
              <Select
                value={form.watch("license_tier")}
                onValueChange={(value) => form.setValue("license_tier", value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select license tier" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="free">Free</SelectItem>
                  <SelectItem value="professional">Professional</SelectItem>
                  <SelectItem value="enterprise">Enterprise</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={updateDivision.isPending}>
              {updateDivision.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Save Changes
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
