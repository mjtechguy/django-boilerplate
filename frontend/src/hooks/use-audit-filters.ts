import { useNavigate } from "@tanstack/react-router";
import { useCallback, useState, useEffect } from "react";
import { type AuditAction } from "@/lib/api/audit/types";

export interface AuditFilterValues {
  action?: AuditAction;
  resource_type?: string;
  actor_id?: string;
  start_date?: string;
  end_date?: string;
}

/**
 * Custom hook to manage audit log filters with URL synchronization
 *
 * This hook maintains two states:
 * 1. Local filter state (draftFilters) - Updated as user interacts with filter form
 * 2. Applied filter state (appliedFilters) - Synced to URL when user clicks Apply
 *
 * This allows users to experiment with filters before applying them, and
 * ensures the URL represents the currently applied filters for shareability.
 */
export function useAuditFilters() {
  const navigate = useNavigate();

  // Read filters from URL on mount
  const getFiltersFromUrl = useCallback((): AuditFilterValues => {
    if (typeof window === "undefined") {
      return {};
    }

    const params = new URLSearchParams(window.location.search);
    const filters: AuditFilterValues = {};

    const action = params.get("action");
    if (action) {
      filters.action = action as AuditAction;
    }

    const resourceType = params.get("resource_type");
    if (resourceType) {
      filters.resource_type = resourceType;
    }

    const actorId = params.get("actor_id");
    if (actorId) {
      filters.actor_id = actorId;
    }

    const startDate = params.get("start_date");
    if (startDate) {
      filters.start_date = startDate;
    }

    const endDate = params.get("end_date");
    if (endDate) {
      filters.end_date = endDate;
    }

    return filters;
  }, []);

  // Draft filters - what's being edited in the form
  const [draftFilters, setDraftFilters] = useState<AuditFilterValues>(getFiltersFromUrl);

  // Applied filters - what's actually synced to URL and used for API queries
  const [appliedFilters, setAppliedFilters] = useState<AuditFilterValues>(getFiltersFromUrl);

  // Initialize from URL on mount
  useEffect(() => {
    const urlFilters = getFiltersFromUrl();
    setDraftFilters(urlFilters);
    setAppliedFilters(urlFilters);
  }, [getFiltersFromUrl]);

  // Apply filters - sync draft to URL
  const applyFilters = useCallback(() => {
    const search: Record<string, string> = {};

    if (draftFilters.action) {
      search.action = draftFilters.action;
    }
    if (draftFilters.resource_type) {
      search.resource_type = draftFilters.resource_type;
    }
    if (draftFilters.actor_id) {
      search.actor_id = draftFilters.actor_id;
    }
    if (draftFilters.start_date) {
      search.start_date = draftFilters.start_date;
    }
    if (draftFilters.end_date) {
      search.end_date = draftFilters.end_date;
    }

    setAppliedFilters(draftFilters);
    navigate({
      search,
      replace: true,
    });
  }, [draftFilters, navigate]);

  // Clear all filters
  const clearFilters = useCallback(() => {
    setDraftFilters({});
    setAppliedFilters({});
    navigate({
      search: {},
      replace: true,
    });
  }, [navigate]);

  // Clear individual filter
  const clearFilter = useCallback(
    (key: keyof AuditFilterValues) => {
      const newFilters = { ...appliedFilters };
      delete newFilters[key];

      setDraftFilters(newFilters);
      setAppliedFilters(newFilters);

      const search: Record<string, string> = {};
      Object.entries(newFilters).forEach(([k, v]) => {
        if (v) {
          search[k] = v;
        }
      });

      navigate({
        search,
        replace: true,
      });
    },
    [appliedFilters, navigate]
  );

  // Count active filters (based on applied filters)
  const activeFilterCount = Object.values(appliedFilters).filter(
    (value) => value !== undefined && value !== ""
  ).length;

  // Check if any filters are active
  const hasActiveFilters = activeFilterCount > 0;

  return {
    // Draft filters for the form
    draftFilters,
    setDraftFilters,

    // Applied filters for API queries
    appliedFilters,

    // Actions
    applyFilters,
    clearFilters,
    clearFilter,

    // Status
    activeFilterCount,
    hasActiveFilters,
  };
}
