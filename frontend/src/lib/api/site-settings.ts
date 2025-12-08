/**
 * Site settings API client.
 */

import { apiGet, apiPut } from "./client";

export interface SiteSettings {
  site_name: string;
  logo_url: string;
  favicon_url: string;
  primary_color: string;
  support_email?: string;
  updated_at?: string;
}

export interface SiteSettingsUpdate {
  site_name?: string;
  logo_url?: string;
  favicon_url?: string;
  primary_color?: string;
  support_email?: string;
}

/**
 * Get public site settings (no auth required).
 */
export async function getPublicSiteSettings(): Promise<SiteSettings> {
  return apiGet<SiteSettings>("settings/site");
}

/**
 * Get admin site settings (requires admin role).
 */
export async function getAdminSiteSettings(): Promise<SiteSettings> {
  return apiGet<SiteSettings>("admin/settings/site");
}

/**
 * Update site settings (requires admin role).
 */
export async function updateSiteSettings(
  data: SiteSettingsUpdate
): Promise<SiteSettings> {
  return apiPut<SiteSettings, SiteSettingsUpdate>("admin/settings/site", data);
}
