import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface HeaderShellProps {
  leftContent?: ReactNode;
  rightContent?: ReactNode;
  className?: string;
}

export function HeaderShell({
  leftContent,
  rightContent,
  className,
}: HeaderShellProps) {
  return (
    <header
      className={cn(
        "sticky top-0 z-40 flex h-16 items-center justify-between border-b bg-background/95 px-6 backdrop-blur supports-[backdrop-filter]:bg-background/60",
        className
      )}
    >
      {leftContent}
      {rightContent}
    </header>
  );
}
