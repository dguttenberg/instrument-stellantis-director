import { Film, Library, Blend, Sparkles, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { CellType } from "@/lib/types";
import { techniqueMode, type TechniqueKind } from "./helpers";

// Icon + AA-safe color per technique, following the script's color coding:
// hybrid=cyan, stock=green, existing=magenta, AI=amber.
const STYLE: Record<TechniqueKind, { icon: LucideIcon; cls: string }> = {
  hybrid: { icon: Blend, cls: "bg-sky-blue/15 text-sky-deep" },
  stock: { icon: Library, cls: "bg-aurora-green-deep/15 text-aurora-green-deep" },
  existing: { icon: Film, cls: "bg-aurora-violet/12 text-aurora-violet" },
  ai: { icon: Sparkles, cls: "bg-sunset-ember/15 text-ember-deep" },
};

export function TechniqueBadge({
  cellType,
  iconOnly = false,
  className,
}: {
  cellType: CellType;
  iconOnly?: boolean;
  className?: string;
}) {
  const mode = techniqueMode(cellType);
  const { icon: Icon, cls } = STYLE[mode.kind];
  return (
    <span
      title={mode.hint}
      aria-label={mode.label}
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium leading-tight",
        cls,
        className,
      )}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" />
      {!iconOnly && mode.label}
    </span>
  );
}
