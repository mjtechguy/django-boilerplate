import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { Loader2, Pencil } from "lucide-react";
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
import {
  useUpdateMembership,
  updateMembershipInputSchema,
  type UpdateMembershipInput,
} from "@/lib/api/memberships";
import { type UserMembership } from "@/lib/api/users";
import { useTeams } from "@/lib/api/teams";

interface EditMembershipDialogProps {
  membership: UserMembership;
  onSuccess?: () => void;
  trigger?: React.ReactNode;
}

const ORG_ROLES = ["user", "org_admin", "billing_admin"];
const TEAM_ROLES = ["member", "team_admin", "team_lead"];

export function EditMembershipDialog({
  membership,
  onSuccess,
  trigger,
}: EditMembershipDialogProps) {
  const [open, setOpen] = useState(false);
  const updateMembership = useUpdateMembership(membership.id);
  const { data: teamsData } = useTeams({ org_id: membership.org });

  const form = useForm<UpdateMembershipInput>({
    resolver: zodResolver(updateMembershipInputSchema),
    defaultValues: {
      org_roles: membership.org_roles,
      team_roles: membership.team_roles,
      team: membership.team,
    },
  });

  // Reset form when membership changes or dialog opens
  useEffect(() => {
    if (open) {
      form.reset({
        org_roles: membership.org_roles,
        team_roles: membership.team_roles,
        team: membership.team,
      });
    }
  }, [open, membership, form]);

  const onSubmit = async (data: UpdateMembershipInput) => {
    try {
      await updateMembership.mutateAsync(data);
      toast.success("Membership updated successfully");
      setOpen(false);
      onSuccess?.();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to update membership";
      toast.error(message);
    }
  };

  const selectedTeam = form.watch("team");

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="ghost" size="sm">
            <Pencil className="h-4 w-4" />
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Edit Membership</DialogTitle>
            <DialogDescription>
              Update role assignments for this membership in {membership.org_name}.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label>Organization</Label>
              <div className="text-sm text-muted-foreground px-3 py-2 border rounded-md bg-muted/50">
                {membership.org_name}
              </div>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="team">Team (optional)</Label>
              <Select
                value={selectedTeam ?? "none"}
                onValueChange={(value) => {
                  form.setValue("team", value === "none" ? null : value);
                  if (value === "none") {
                    form.setValue("team_roles", []);
                  }
                }}
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

            {selectedTeam && selectedTeam !== "none" && (
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
            <Button type="submit" disabled={updateMembership.isPending}>
              {updateMembership.isPending && (
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
