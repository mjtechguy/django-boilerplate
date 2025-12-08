import { useState } from "react";
import { useForm } from "react-hook-form";
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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCreateMembership, type CreateMembershipInput } from "@/lib/api/memberships";
import { useOrganizations } from "@/lib/api/organizations";
import { useTeams } from "@/lib/api/teams";

interface AddMembershipDialogProps {
  userId: number;
  onSuccess?: () => void;
}

interface FormData {
  org: string;
  team: string | null;
  org_roles: string[];
  team_roles: string[];
}

const ORG_ROLES = ["user", "org_admin", "billing_admin"];
const TEAM_ROLES = ["member", "team_admin", "team_lead"];

export function AddMembershipDialog({ userId, onSuccess }: AddMembershipDialogProps) {
  const [open, setOpen] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState<string>("");
  const createMembership = useCreateMembership();
  const { data: orgsData, isLoading: orgsLoading } = useOrganizations({ status: "active" });
  const { data: teamsData } = useTeams({ org_id: selectedOrg || undefined });

  const form = useForm<FormData>({
    defaultValues: {
      org: "",
      team: null,
      org_roles: ["user"],
      team_roles: [],
    },
  });

  const onSubmit = async (data: FormData) => {
    try {
      const payload: CreateMembershipInput = {
        user: userId,
        org: data.org,
        team: data.team,
        org_roles: data.org_roles,
        team_roles: data.team_roles,
      };
      await createMembership.mutateAsync(payload);
      setOpen(false);
      form.reset({ org: "", team: null, org_roles: ["user"], team_roles: [] });
      setSelectedOrg("");
      onSuccess?.();
    } catch (error) {
      console.error("Failed to create membership:", error);
    }
  };

  const handleOrgChange = (value: string) => {
    setSelectedOrg(value);
    form.setValue("org", value);
    form.setValue("team", null);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Plus className="mr-2 h-4 w-4" />
          Add Membership
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Add Organization Membership</DialogTitle>
            <DialogDescription>
              Assign this user to an organization and optionally a team.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="org">Organization</Label>
              <Select
                value={form.watch("org")}
                onValueChange={handleOrgChange}
                disabled={orgsLoading}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select an organization" />
                </SelectTrigger>
                <SelectContent>
                  {orgsData?.results.map((org) => (
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
              <Label htmlFor="team">Team (optional)</Label>
              <Select
                value={form.watch("team") ?? "none"}
                onValueChange={(value) => form.setValue("team", value === "none" ? null : value)}
                disabled={!selectedOrg}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a team" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No team</SelectItem>
                  {teamsData?.results.map((team) => (
                    <SelectItem key={team.id} value={team.id}>
                      {team.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="org_roles">Organization Role</Label>
              <Select
                value={form.watch("org_roles")?.[0] ?? "user"}
                onValueChange={(value) => form.setValue("org_roles", [value])}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {ORG_ROLES.map((role) => (
                    <SelectItem key={role} value={role}>
                      {role.replace(/_/g, " ")}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {form.watch("team") && (
              <div className="grid gap-2">
                <Label htmlFor="team_roles">Team Role</Label>
                <Select
                  value={form.watch("team_roles")?.[0] ?? "member"}
                  onValueChange={(value) => form.setValue("team_roles", [value])}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a role" />
                  </SelectTrigger>
                  <SelectContent>
                    {TEAM_ROLES.map((role) => (
                      <SelectItem key={role} value={role}>
                        {role.replace(/_/g, " ")}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createMembership.isPending}>
              {createMembership.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Add Membership
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
