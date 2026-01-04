import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface HeaderSearchProps {
  placeholder: string;
  className?: string;
}

export function HeaderSearch({ placeholder, className }: HeaderSearchProps) {
  return (
    <div className={cn("relative w-full", className)}>
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        placeholder={placeholder}
        className="pl-9 bg-muted/50 border-0 focus-visible:ring-1"
      />
    </div>
  );
}
