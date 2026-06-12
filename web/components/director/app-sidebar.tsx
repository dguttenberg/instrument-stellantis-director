"use client";

import { useRef, useState } from "react";
import {
  Upload,
  CheckCircle2,
  Circle,
  Play,
  ClipboardCheck,
  Download,
  FileUp,
  ChevronDown,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { exportUrl } from "@/lib/api";
import type { Dials, Lane, Project } from "@/lib/types";

const STEPS = [
  { label: "Upload", icon: Upload },
  { label: "Confirm", icon: CheckCircle2 },
  { label: "Run", icon: Play },
  { label: "Review", icon: ClipboardCheck },
  { label: "Export", icon: Download },
];

const DIAL_DEFS: { key: keyof Dials; name: string; live?: boolean }[] = [
  { key: "regional_specificity", name: "Regional specificity", live: true },
  { key: "styling_carry_over", name: "Styling carry-over" },
  { key: "voice_adherence", name: "Voice adherence" },
  { key: "narrative_continuity", name: "Narrative continuity" },
];

export interface AppSidebarProps {
  project: Project | null;
  lanes: Lane[];
  shownRegions: string[];
  onToggleRegion: (key: string) => void;
  dials: Dials;
  onDialChange: (key: keyof Dials, value: number) => void;
  onLoadSample: () => void;
  onUpload: (file: File) => void;
  ingestStatus: string;
  busy: boolean;
  resultsCount: number;
  currentStep: number;
}

// hidden when the sidebar collapses to its icon rail
const HIDE_ON_ICON = "group-data-[collapsible=icon]:hidden";

export function AppSidebar(props: AppSidebarProps) {
  const {
    project,
    lanes,
    shownRegions,
    onToggleRegion,
    dials,
    onDialChange,
    onLoadSample,
    onUpload,
    ingestStatus,
    busy,
    resultsCount,
    currentStep,
  } = props;

  const fileRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b">
        <div
          className={cn(
            "text-muted-foreground px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.12em]",
            HIDE_ON_ICON,
          )}
        >
          Setup
        </div>
      </SidebarHeader>

      <SidebarContent>
        {/* Step tracker — stays visible in the icon rail */}
        <SidebarGroup>
          <SidebarGroupLabel>Flow</SidebarGroupLabel>
          <SidebarMenu>
            {STEPS.map((step, i) => {
              const done = i < currentStep;
              const active = i === currentStep;
              const Icon = done ? CheckCircle2 : active ? step.icon : Circle;
              return (
                <SidebarMenuItem key={step.label}>
                  <SidebarMenuButton
                    isActive={active}
                    tooltip={step.label}
                    className="pointer-events-none"
                  >
                    <Icon
                      className={cn(
                        done && "text-aurora-green-deep",
                        active && "text-aurora-violet",
                        !done && !active && "text-muted-foreground/50",
                      )}
                    />
                    <span>{step.label}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              );
            })}
          </SidebarMenu>
        </SidebarGroup>

        {/* Deck */}
        <SidebarGroup className={HIDE_ON_ICON}>
          <SidebarGroupLabel>Deck</SidebarGroupLabel>
          <div
            role="button"
            tabIndex={0}
            onClick={() => fileRef.current?.click()}
            onKeyDown={(e) => e.key === "Enter" && fileRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              const f = e.dataTransfer.files?.[0];
              if (f) onUpload(f);
            }}
            className={cn(
              "flex cursor-pointer flex-col items-center gap-1.5 rounded-md border border-dashed p-4 text-center transition-colors",
              drag
                ? "border-aurora-green-deep bg-aurora-green-deep/10"
                : "border-input hover:border-aurora-green-deep/60",
            )}
          >
            <FileUp className="text-muted-foreground h-5 w-5" />
            <span className="text-xs font-medium">Drop a .pdf / .pptx storyboard</span>
            <span className="text-muted-foreground text-[11px]">or click to browse</span>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.pptx,.ppt"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onUpload(f);
            }}
          />
          <Button
            variant="outline"
            size="sm"
            className="mt-2 w-full"
            onClick={onLoadSample}
            disabled={busy}
          >
            Load sample
          </Button>
          {ingestStatus && (
            <p className="text-muted-foreground mt-2 text-[11px] leading-snug">
              {ingestStatus}
            </p>
          )}
        </SidebarGroup>

        {/* Dials */}
        <SidebarGroup className={HIDE_ON_ICON}>
          <SidebarGroupLabel>Dials</SidebarGroupLabel>
          <div className="flex flex-col gap-4 px-2 py-1">
            {DIAL_DEFS.map((d) => (
              <div key={d.key} className="flex flex-col gap-1.5">
                <div className="flex items-baseline justify-between text-xs">
                  <span className="flex items-center gap-1.5">
                    {d.name}
                    {d.live && (
                      <span className="text-aurora-green-deep inline-flex items-center gap-1 text-[10px] uppercase tracking-wide">
                        <span className="leading-none">●</span> live
                      </span>
                    )}
                  </span>
                  <span className="text-aurora-violet font-semibold tabular-nums">
                    {dials[d.key].toFixed(2)}
                  </span>
                </div>
                <Slider
                  value={[dials[d.key]]}
                  min={0}
                  max={1}
                  step={0.05}
                  onValueChange={(v) => onDialChange(d.key, v[0])}
                />
              </div>
            ))}
          </div>
        </SidebarGroup>

        {/* Regions */}
        <SidebarGroup className={HIDE_ON_ICON}>
          <SidebarGroupLabel>Regions</SidebarGroupLabel>
          <div className="flex flex-wrap gap-1.5 px-2 py-1">
            {lanes.map((l) => {
              const on = shownRegions.includes(l.key);
              return (
                <button
                  key={l.key}
                  onClick={() => onToggleRegion(l.key)}
                  title={l.label}
                  className={cn(
                    "rounded-full border px-2.5 py-1 text-[11px] font-semibold transition-colors",
                    on
                      ? "border-aurora-green-deep bg-aurora-green-deep/15 text-aurora-green-deep"
                      : "border-input text-muted-foreground hover:border-aurora-green-deep/60",
                  )}
                >
                  {l.abbrev}
                </button>
              );
            })}
          </div>
        </SidebarGroup>

        {/* Export */}
        <SidebarGroup className={HIDE_ON_ICON}>
          <SidebarGroupLabel>Export</SidebarGroupLabel>
          <div className="px-2 py-1">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full justify-between"
                  disabled={resultsCount === 0}
                >
                  Export{resultsCount ? ` (${resultsCount})` : ""}
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-56">
                <DropdownMenuItem asChild>
                  <a href={exportUrl("cgi.xlsx")} download>
                    CGI workbook (.xlsx)
                  </a>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <a href={exportUrl("twelvelabs.csv")} download>
                    TwelveLabs (.csv)
                  </a>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <a href={exportUrl("twelvelabs.json")} download>
                    TwelveLabs (.json)
                  </a>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            {resultsCount === 0 && (
              <p className="text-muted-foreground mt-1.5 text-[11px]">
                Run a region to enable export.
              </p>
            )}
          </div>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
