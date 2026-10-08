import {
  CalendarCheck,
  CalendarBlank,
  CellSignalHigh,
  CellSignalLow,
  CellSignalMedium,
  Circle,
  Hourglass,
  Prohibit,
  SealCheck,
  SealQuestion,
  WarningOctagon,
  type Icon,
} from "@phosphor-icons/react";
import type { ReactNode } from "react";
import type { LoopStatus, Stakes } from "../lib/api";

type Tone = "neutral" | "info" | "good" | "warn" | "crit";

const TONE_CLASSES: Record<Tone, string> = {
  neutral: "bg-sunken text-ink-2 border-line",
  info: "bg-info-soft text-info border-info-line",
  good: "bg-good-soft text-good border-good-line",
  warn: "bg-warn-soft text-warn border-warn-line",
  crit: "bg-crit-soft text-crit border-crit-line",
};

export function Badge({ tone, icon: IconComponent, children }: { tone: Tone; icon: Icon; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-md border px-1.5 py-0.5 text-xs font-medium ${TONE_CLASSES[tone]}`}
    >
      <IconComponent size={13} weight="bold" aria-hidden="true" />
      {children}
    </span>
  );
}

export const STATUS: Record<LoopStatus, { label: string; tone: Tone; icon: Icon }> = {
  open: { label: "Open", tone: "neutral", icon: Circle },
  awaiting_reply: { label: "Awaiting reply", tone: "info", icon: Hourglass },
  closed_verified: { label: "Closed · verified", tone: "good", icon: SealCheck },
  closed_claimed: { label: "Closed · claimed", tone: "warn", icon: SealQuestion },
  escalated_to_human: { label: "Needs you", tone: "crit", icon: WarningOctagon },
  abandoned: { label: "Abandoned", tone: "neutral", icon: Prohibit },
};

export function StatusBadge({ status }: { status: LoopStatus }) {
  const { label, tone, icon } = STATUS[status];
  return (
    <Badge tone={tone} icon={icon}>
      {label}
    </Badge>
  );
}

export function WindowBadge({ source }: { source: "stated" | "inferred" }) {
  return source === "stated" ? (
    <Badge tone="neutral" icon={CalendarCheck}>
      Stated date
    </Badge>
  ) : (
    <Badge tone="neutral" icon={CalendarBlank}>
      Inferred window
    </Badge>
  );
}

const STAKES_ICON: Record<Stakes, Icon> = { high: CellSignalHigh, medium: CellSignalMedium, low: CellSignalLow };

export function StakesLabel({ stakes }: { stakes: Stakes }) {
  const IconComponent = STAKES_ICON[stakes];
  return (
    <span className="inline-flex items-center gap-1 text-sm text-ink-2">
      <IconComponent size={16} weight="bold" aria-hidden="true" />
      <span className="capitalize">{stakes}</span>
    </span>
  );
}
