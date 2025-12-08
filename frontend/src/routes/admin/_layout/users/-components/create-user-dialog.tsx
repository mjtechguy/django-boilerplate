import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Plus } from "lucide-react";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useCreateUser,
  useInviteUser,
  createUserInputSchema,
  inviteUserInputSchema,
  type CreateUserInput,
  type InviteUserInput,
} from "@/lib/api/users";
import { useOrganizations } from "@/lib/api/organizations";

export function CreateUserDialog() {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<"local" | "oidc">("local");
  const createUser = useCreateUser();
  const inviteUser = useInviteUser();
  const { data: orgsData } = useOrganizations({ status: "active" });

  const localForm = useForm<CreateUserInput>({
    resolver: zodResolver(createUserInputSchema),
    defaultValues: {
      email: "",
      password: "",
      first_name: "",
      last_name: "",
      roles: [],
    },
  });

  const oidcForm = useForm<InviteUserInput>({
    resolver: zodResolver(inviteUserInputSchema),
    defaultValues: {
      email: "",
      first_name: "",
      last_name: "",
      roles: [],
      org_id: null,
      org_roles: [],
    },
  });

  const onLocalSubmit = async (data: CreateUserInput) => {
    try {
      await createUser.mutateAsync(data);
      setOpen(false);
      localForm.reset();
    } catch (error) {
      console.error("Failed to create user:", error);
    }
  };

  const onOidcSubmit = async (data: InviteUserInput) => {
    try {
      await inviteUser.mutateAsync(data);
      setOpen(false);
      oidcForm.reset();
    } catch (error) {
      console.error("Failed to invite user:", error);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Add User
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Add User</DialogTitle>
          <DialogDescription>
            Create a local user or invite an SSO user.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={tab} onValueChange={(v) => setTab(v as "local" | "oidc")}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="local">Local User</TabsTrigger>
            <TabsTrigger value="oidc">SSO Invite</TabsTrigger>
          </TabsList>

          <TabsContent value="local" className="mt-4">
            <form onSubmit={localForm.handleSubmit(onLocalSubmit)}>
              <div className="grid gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="local-email">Email</Label>
                  <Input
                    id="local-email"
                    type="email"
                    placeholder="user@example.com"
                    {...localForm.register("email")}
                  />
                  {localForm.formState.errors.email && (
                    <p className="text-sm text-destructive">
                      {localForm.formState.errors.email.message}
                    </p>
                  )}
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="local-password">Password</Label>
                  <Input
                    id="local-password"
                    type="password"
                    placeholder="Min 8 chars, 1 upper, 1 lower, 1 digit"
                    {...localForm.register("password")}
                  />
                  {localForm.formState.errors.password && (
                    <p className="text-sm text-destructive">
                      {localForm.formState.errors.password.message}
                    </p>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label htmlFor="local-first-name">First Name</Label>
                    <Input
                      id="local-first-name"
                      {...localForm.register("first_name")}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="local-last-name">Last Name</Label>
                    <Input
                      id="local-last-name"
                      {...localForm.register("last_name")}
                    />
                  </div>
                </div>
              </div>
              <DialogFooter className="mt-6">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={createUser.isPending}>
                  {createUser.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Create User
                </Button>
              </DialogFooter>
            </form>
          </TabsContent>

          <TabsContent value="oidc" className="mt-4">
            <form onSubmit={oidcForm.handleSubmit(onOidcSubmit)}>
              <div className="grid gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="oidc-email">Email</Label>
                  <Input
                    id="oidc-email"
                    type="email"
                    placeholder="user@example.com"
                    {...oidcForm.register("email")}
                  />
                  {oidcForm.formState.errors.email && (
                    <p className="text-sm text-destructive">
                      {oidcForm.formState.errors.email.message}
                    </p>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label htmlFor="oidc-first-name">First Name</Label>
                    <Input
                      id="oidc-first-name"
                      {...oidcForm.register("first_name")}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="oidc-last-name">Last Name</Label>
                    <Input
                      id="oidc-last-name"
                      {...oidcForm.register("last_name")}
                    />
                  </div>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="oidc-org">Organization (optional)</Label>
                  <Select
                    value={oidcForm.watch("org_id") ?? "none"}
                    onValueChange={(value) =>
                      oidcForm.setValue("org_id", value === "none" ? null : value)
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select an organization" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No organization</SelectItem>
                      {orgsData?.results.map((org) => (
                        <SelectItem key={org.id} value={org.id}>
                          {org.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter className="mt-6">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={inviteUser.isPending}>
                  {inviteUser.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Send Invite
                </Button>
              </DialogFooter>
            </form>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
