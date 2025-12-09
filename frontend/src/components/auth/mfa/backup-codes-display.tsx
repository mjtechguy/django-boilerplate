import { useState } from "react";
import { Copy, Check, Download, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

interface BackupCodesDisplayProps {
  codes: string[];
  onRegenerate?: () => void;
  isRegenerating?: boolean;
}

export function BackupCodesDisplay({
  codes,
  onRegenerate,
  isRegenerating,
}: BackupCodesDisplayProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(codes.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success("Backup codes copied to clipboard");
  };

  const handleDownload = () => {
    const blob = new Blob([codes.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "mfa-backup-codes.txt";
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Backup codes downloaded");
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Backup Codes</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-4">
          <p className="text-sm text-amber-600 dark:text-amber-400">
            Keep these codes in a safe place. Each code can only be used once.
          </p>
        </div>

        <div className="space-y-1 rounded-lg bg-muted p-4 font-mono text-sm">
          {codes.map((code, index) => (
            <div key={index}>{code}</div>
          ))}
        </div>

        <div className="flex gap-2">
          <Button variant="outline" onClick={handleCopy} className="flex-1">
            {copied ? (
              <>
                <Check className="mr-2 h-4 w-4" />
                Copied
              </>
            ) : (
              <>
                <Copy className="mr-2 h-4 w-4" />
                Copy
              </>
            )}
          </Button>
          <Button variant="outline" onClick={handleDownload} className="flex-1">
            <Download className="mr-2 h-4 w-4" />
            Download
          </Button>
        </div>

        {onRegenerate && (
          <Button
            variant="destructive"
            onClick={onRegenerate}
            disabled={isRegenerating}
            className="w-full"
          >
            {isRegenerating ? (
              <>
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                Regenerating...
              </>
            ) : (
              <>
                <RefreshCw className="mr-2 h-4 w-4" />
                Regenerate Codes
              </>
            )}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
