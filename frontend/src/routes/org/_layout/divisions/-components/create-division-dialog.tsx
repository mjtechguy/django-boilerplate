import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { useCreateDivision, createDivisionInputSchema } from "@/lib/api/divisions";
import type { CreateDivisionInput } from "@/lib/api/divisions";
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
import { Button } from "@/components/ui/button";

interface CreateDivisionDialogProps {
  orgId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateDivisionDialog({
  orgId,
  open,
  onOpenChange,
}: CreateDivisionDialogProps) {
  const createMutation = useCreateDivision(orgId);

  const form = useForm<CreateDivisionInput>({
    resolver: zodResolver(createDivisionInputSchema),
    defaultValues: {
      name: "",
      billing_mode: "inherit",
    },
  });

  const onSubmit = async (data: CreateDivisionInput) => {
    try {
      await createMutation.mutateAsync(data);
      toast.success("Division created successfully");
      form.reset();
      onOpenChange(false);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to create division";
      toast.error(message);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Create Division</DialogTitle>
            <DialogDescription>
              Create a new division within your organization to manage teams and
              billing independently.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Division Name</Label>
              <Input
                id="name"
                placeholder="Engineering, Sales, Marketing..."
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
                  <SelectItem value="inherit">Inherit from Organization</SelectItem>
                  <SelectItem value="independent">Independent Billing</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-sm text-muted-foreground">
                Choose whether this division inherits billing from the
                organization or has independent billing.
              </p>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="billing_email">Billing Email (Optional)</Label>
              <Input
                id="billing_email"
                type="email"
                placeholder="billing@example.com"
                {...form.register("billing_email")}
              />
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
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Create Division
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
