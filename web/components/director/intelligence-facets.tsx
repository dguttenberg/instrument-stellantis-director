import { cn } from "@/lib/utils";

// The three intelligences whose intersection drives the scene. Each is color-keyed
// and labeled so the synopsis reads as their synthesis.
const LENSES = [
  { key: "brand", label: "Brand", dot: "bg-aurora-violet" },
  { key: "location", label: "Location", dot: "bg-sky-deep" },
  { key: "audience", label: "Audience", dot: "bg-aurora-green-deep" },
] as const;

export function IntelligenceFacets({
  intelligence,
  className,
}: {
  intelligence?: { brand?: string; location?: string; audience?: string };
  className?: string;
}) {
  if (!intelligence) return null;
  const rows = LENSES.filter((l) => intelligence[l.key]?.trim());
  if (rows.length === 0) return null;
  return (
    <dl className={cn("flex flex-col gap-1", className)}>
      {rows.map((l) => (
        <div key={l.key} className="flex items-baseline gap-2 text-xs">
          <dt className="text-muted-foreground flex w-[4.75rem] shrink-0 items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide">
            <span className={cn("h-2 w-2 shrink-0 rounded-[2px]", l.dot)} />
            {l.label}
          </dt>
          <dd className="text-foreground">{intelligence[l.key]}</dd>
        </div>
      ))}
    </dl>
  );
}
