/**
 * Hook to fetch and cache site settings.
 */

import { useQuery } from "@tanstack/react-query";
import { getPublicSiteSettings, type SiteSettings } from "@/lib/api/site-settings";

export const SITE_SETTINGS_QUERY_KEY = ["site-settings"] as const;

/**
 * Fetch site settings with caching.
 * Settings are fetched once and cached for the session.
 */
export function useSiteSettings() {
  return useQuery<SiteSettings>({
    queryKey: SITE_SETTINGS_QUERY_KEY,
    queryFn: getPublicSiteSettings,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
