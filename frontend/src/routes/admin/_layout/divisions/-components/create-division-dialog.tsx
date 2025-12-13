import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { Plus, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
  useAdminCreateDivision,
  createDivisionInputSchema,
  type CreateDivisionInput,
} from "@/lib/api/divisions";
import { useOrganizations } from "@/lib/api/organizations";

interface CreateDivisionDialogProps {
  trigger?: React.ReactNode;
}

export function CreateDivisionDialog({ trigger }: CreateDivisionDialogProps) {
  const [open, setOpen] = useState(false);
  const createDivision = useAdminCreateDivision();
  const { data: orgsData } = useOrganizations();

  const form = useForm<CreateDivisionInput>({
    resolver: zodResolver(createDivisionInputSchema),
    defaultValues: {
      name: "",
      billing_mode: "inherit",
      license_tier: "free",
    },
  });

  const onSubmit = async (data: CreateDivisionInput) => {
    try {
      await createDivision.mutateAsync(data);
      toast.success("Division created successfully");
      setOpen(false);
      form.reset();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to create division";
      toast.error(message);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Add Division
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Create Division</DialogTitle>
            <DialogDescription>
              Add a new division to an organization. Configure billing and license settings.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="org">Organization</Label>
              <Select
                value={form.watch("org")}
                onValueChange={(value) => form.setValue("org", value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select organization" />
                </SelectTrigger>
                <SelectContent>
                  {orgsData?.results?.map((org) => (
                    <SelectItem key={org.id} value={org.id}>
                      {org.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {form.formState.errors.org && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.org.message}
                </p>
              )}
            </div>
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
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createDivision.isPending}>
              {createDivision.isPending && (
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
