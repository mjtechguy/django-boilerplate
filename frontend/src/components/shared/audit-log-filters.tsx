import * as React from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { type AuditAction } from "@/lib/api/audit/types";

export interface AuditFilterValues {
  action?: AuditAction;
  resource_type?: string;
  actor_id?: string;
  start_date?: string;
  end_date?: string;
}

interface AuditLogFiltersProps {
  filters: AuditFilterValues;
  onFiltersChange: (filters: AuditFilterValues) => void;
  onApply: () => void;
  onClear: () => void;
}

const ACTION_OPTIONS: { value: AuditAction; label: string }[] = [
  { value: "CREATE", label: "Create" },
  { value: "UPDATE", label: "Update" },
  { value: "DELETE", label: "Delete" },
  { value: "READ", label: "Read" },
  { value: "LOGIN", label: "Login" },
  { value: "LOGOUT", label: "Logout" },
];

const RESOURCE_TYPE_OPTIONS = [
  { value: "Org", label: "Organization" },
  { value: "User", label: "User" },
  { value: "Team", label: "Team" },
  { value: "Division", label: "Division" },
  { value: "Membership", label: "Membership" },
  { value: "Invitation", label: "Invitation" },
  { value: "Role", label: "Role" },
  { value: "Permission", label: "Permission" },
];

export function AuditLogFilters({
  filters,
  onFiltersChange,
  onApply,
  onClear,
}: AuditLogFiltersProps) {
  const handleActionChange = (value: string) => {
    onFiltersChange({
      ...filters,
      action: value as AuditAction,
    });
  };

  const handleResourceTypeChange = (value: string) => {
    onFiltersChange({
      ...filters,
      resource_type: value,
    });
  };

  const handleActorChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFiltersChange({
      ...filters,
      actor_id: e.target.value,
    });
  };

  const handleStartDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFiltersChange({
      ...filters,
      start_date: e.target.value,
    });
  };

  const handleEndDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFiltersChange({
      ...filters,
      end_date: e.target.value,
    });
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="action">Action Type</Label>
        <Select
          value={filters.action ?? ""}
          onValueChange={handleActionChange}
        >
          <SelectTrigger id="action">
            <SelectValue placeholder="All actions" />
          </SelectTrigger>
          <SelectContent>
            {ACTION_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="resource-type">Resource Type</Label>
        <Select
          value={filters.resource_type ?? ""}
          onValueChange={handleResourceTypeChange}
        >
          <SelectTrigger id="resource-type">
            <SelectValue placeholder="All resources" />
          </SelectTrigger>
          <SelectContent>
            {RESOURCE_TYPE_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="actor">Actor</Label>
        <Input
          id="actor"
          type="text"
          placeholder="Email or ID"
          value={filters.actor_id ?? ""}
          onChange={handleActorChange}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="start-date">Start Date</Label>
        <Input
          id="start-date"
          type="date"
          value={filters.start_date ?? ""}
          onChange={handleStartDateChange}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="end-date">End Date</Label>
        <Input
          id="end-date"
          type="date"
          value={filters.end_date ?? ""}
          onChange={handleEndDateChange}
        />
      </div>

      <div className="flex gap-2 pt-2">
        <Button onClick={onApply} className="flex-1">
          Apply
        </Button>
        <Button onClick={onClear} variant="outline" className="flex-1">
          Clear
        </Button>
      </div>
    </div>
  );
}
