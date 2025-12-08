import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Save, Loader2, Image, Palette } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  getAdminSiteSettings,
  updateSiteSettings,
} from "@/lib/api/site-settings";

export const Route = createFileRoute("/admin/_layout/settings/")({
  component: SettingsPage,
});

const siteSettingsSchema = z.object({
  site_name: z.string().min(1, "Site name is required").max(255),
  logo_url: z.string().url("Must be a valid URL").or(z.literal("")),
  favicon_url: z.string().url("Must be a valid URL").or(z.literal("")),
  primary_color: z.string().regex(/^#[0-9A-Fa-f]{6}$/, "Must be a valid hex color"),
  support_email: z.string().email("Must be a valid email").or(z.literal("")),
});

type SiteSettingsFormData = z.infer<typeof siteSettingsSchema>;

function SettingsPage() {
  const queryClient = useQueryClient();
  const [saveSuccess, setSaveSuccess] = useState(false);

  const { data: settings, isLoading } = useQuery({
    queryKey: ["admin", "site-settings"],
    queryFn: getAdminSiteSettings,
  });

  const mutation = useMutation({
    mutationFn: updateSiteSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "site-settings"] });
      queryClient.invalidateQueries({ queryKey: ["site-settings"] });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    },
  });

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
  } = useForm<SiteSettingsFormData>({
    resolver: zodResolver(siteSettingsSchema),
    values: settings ? {
      site_name: settings.site_name,
      logo_url: settings.logo_url || "",
      favicon_url: settings.favicon_url || "",
      primary_color: settings.primary_color,
      support_email: settings.support_email || "",
    } : undefined,
  });

  const onSubmit = (data: SiteSettingsFormData) => {
    mutation.mutate(data);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Configure global platform settings"
        actions={
          <Button
            onClick={handleSubmit(onSubmit)}
            disabled={mutation.isPending || !isDirty}
          >
            {mutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            {saveSuccess ? "Saved!" : "Save Changes"}
          </Button>
        }
      />

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
      <div className="grid gap-6">
        {/* Site Branding */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Palette className="h-5 w-5" />
              Site Branding
            </CardTitle>
            <CardDescription>
              Configure the site name, logo, and favicon displayed to users
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="site_name">Site Name</Label>
              <Input
                id="site_name"
                placeholder="Platform"
                {...register("site_name")}
              />
              {errors.site_name && (
                <p className="text-xs text-destructive">{errors.site_name.message}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Displayed in the browser tab and header
              </p>
            </div>
            <Separator />
            <div className="grid gap-2">
              <Label htmlFor="logo_url" className="flex items-center gap-2">
                <Image className="h-4 w-4" />
                Logo URL
              </Label>
              <Input
                id="logo_url"
                type="url"
                placeholder="https://example.com/logo.png"
                {...register("logo_url")}
              />
              {errors.logo_url && (
                <p className="text-xs text-destructive">{errors.logo_url.message}</p>
              )}
              <p className="text-xs text-muted-foreground">
                URL to the logo image (recommended: 200x50px PNG or SVG)
              </p>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="favicon_url">Favicon URL</Label>
              <Input
                id="favicon_url"
                type="url"
                placeholder="https://example.com/favicon.ico"
                {...register("favicon_url")}
              />
              {errors.favicon_url && (
                <p className="text-xs text-destructive">{errors.favicon_url.message}</p>
              )}
              <p className="text-xs text-muted-foreground">
                URL to the favicon (recommended: 32x32px ICO or PNG)
              </p>
            </div>
            <Separator />
            <div className="grid gap-2">
              <Label htmlFor="primary_color">Primary Color</Label>
              <div className="flex gap-2">
                <Input
                  id="primary_color"
                  placeholder="#10b981"
                  {...register("primary_color")}
                  className="flex-1"
                />
                <div
                  className="h-10 w-10 rounded-md border"
                  style={{ backgroundColor: settings?.primary_color || "#10b981" }}
                />
              </div>
              {errors.primary_color && (
                <p className="text-xs text-destructive">{errors.primary_color.message}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Primary brand color in hex format (e.g., #10b981)
              </p>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="support_email">Support Email</Label>
              <Input
                id="support_email"
                type="email"
                placeholder="support@example.com"
                {...register("support_email")}
              />
              {errors.support_email && (
                <p className="text-xs text-destructive">{errors.support_email.message}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Displayed in help sections and error pages
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Authorization */}
        <Card>
          <CardHeader>
            <CardTitle>Authorization</CardTitle>
            <CardDescription>
              Configure Cerbos policy engine settings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="cerbos-url">Cerbos URL</Label>
              <Input
                id="cerbos-url"
                placeholder="http://cerbos:3592"
                defaultValue="http://cerbos:3592"
                disabled
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="fail-mode">Authorization Fail Mode</Label>
              <Input
                id="fail-mode"
                placeholder="deny"
                defaultValue="deny"
                disabled
              />
              <p className="text-xs text-muted-foreground">
                How to handle authorization failures (allow/deny)
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Audit Logging</CardTitle>
            <CardDescription>
              Configure audit log retention and integrity checks
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="retention">Retention Period (days)</Label>
              <Input
                id="retention"
                type="number"
                placeholder="365"
                defaultValue="365"
                disabled
              />
            </div>
            <Separator />
            <div className="grid gap-2">
              <Label htmlFor="signing-key">Audit Signing Key</Label>
              <Input
                id="signing-key"
                type="password"
                placeholder="••••••••"
                disabled
              />
              <p className="text-xs text-muted-foreground">
                Key used for tamper-proof audit chain signatures
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Default License Settings</CardTitle>
            <CardDescription>
              Default settings for new organizations
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="default-tier">Default License Tier</Label>
              <Input
                id="default-tier"
                placeholder="free"
                defaultValue="free"
                disabled
              />
            </div>
          </CardContent>
        </Card>
      </div>
      )}
    </div>
  );
}
