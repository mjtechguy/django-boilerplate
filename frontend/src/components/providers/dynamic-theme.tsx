/**
 * Dynamic theme component that applies the primary color from site settings.
 * Must be used within QueryClientProvider.
 */

import { useEffect } from "react";
import { useSiteSettings } from "@/hooks/use-site-settings";
import { hexToOklch, getPrimaryForeground, adjustLightness } from "@/lib/color-utils";

/**
 * Apply dynamic primary color from site settings.
 * Updates CSS custom properties on the document root.
 */
function applyDynamicPrimaryColor(primaryColor: string) {
  const root = document.documentElement;

  // Generate OKLCh values for primary color variants
  const primary = hexToOklch(primaryColor);
  const primaryForeground = getPrimaryForeground(primaryColor);

  // Light mode primary (slightly darker for better contrast on white)
  const primaryLight = primary;
  // Dark mode primary (slightly lighter for better visibility)
  const primaryDark = adjustLightness(primaryColor, -0.05);

  // Sidebar primary variants
  const sidebarPrimary = adjustLightness(primaryColor, 0.05);
  const sidebarPrimaryDark = adjustLightness(primaryColor, 0.1);

  // Apply to :root (light mode)
  root.style.setProperty("--primary", primaryLight);
  root.style.setProperty("--primary-foreground", primaryForeground);
  root.style.setProperty("--sidebar-primary", sidebarPrimary);
  root.style.setProperty("--sidebar-primary-foreground", primaryForeground);

  // Chart colors based on primary
  root.style.setProperty("--chart-1", adjustLightness(primaryColor, 0.3));
  root.style.setProperty("--chart-2", adjustLightness(primaryColor, 0.15));
  root.style.setProperty("--chart-3", adjustLightness(primaryColor, 0.05));
  root.style.setProperty("--chart-4", primary);
  root.style.setProperty("--chart-5", adjustLightness(primaryColor, -0.05));

  // Create a style element for dark mode overrides
  let darkStyle = document.getElementById("dynamic-theme-dark");
  if (!darkStyle) {
    darkStyle = document.createElement("style");
    darkStyle.id = "dynamic-theme-dark";
    document.head.appendChild(darkStyle);
  }

  darkStyle.textContent = `
    .dark {
      --primary: ${primaryDark};
      --primary-foreground: ${primaryForeground};
      --sidebar-primary: ${sidebarPrimaryDark};
      --sidebar-primary-foreground: ${primaryForeground};
      --chart-1: ${adjustLightness(primaryColor, 0.3)};
      --chart-2: ${adjustLightness(primaryColor, 0.15)};
      --chart-3: ${adjustLightness(primaryColor, 0.05)};
      --chart-4: ${primary};
      --chart-5: ${adjustLightness(primaryColor, -0.05)};
    }
  `;
}

/**
 * Component that fetches site settings and applies dynamic primary color.
 * Should be placed inside QueryClientProvider but can be outside ThemeProvider.
 */
export function DynamicTheme({ children }: { children: React.ReactNode }) {
  const { data: settings } = useSiteSettings();

  useEffect(() => {
    if (settings?.primary_color) {
      applyDynamicPrimaryColor(settings.primary_color);
    }
  }, [settings?.primary_color]);

  return <>{children}</>;
}
