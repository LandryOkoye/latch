import * as Dialog from "@radix-ui/react-dialog";
import {
  ArrowBendUpLeft,
  ClockCounterClockwise,
  Plus,
  Prohibit,
  Quotes,
  Robot,
  PaperPlaneTilt,
  SealCheck,
  SealQuestion,
  UserSwitch,
  Warning,
  WarningOctagon,
  X,
  type Icon,
} from "@phosphor-icons/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api, type Loop, type LoopDetail, type LoopEvent, type LoopEventType, type PriorityBreakdown } from "../lib/api";
import { dueLabel, formatDate, formatDateTime } from "../lib/format";
import { StakesLabel, StatusBadge, WindowBadge } from "./Badges";
import { Button, ErrorState, Skeleton } from "./ui";

/* ---------- evidence ---------- */

function EvidenceText({ text, evidence }: { text: string; evidence: string | null }) {
  const start = evidence ? text.indexOf(evidence) : -1;
  if (!evidence || start === -1) return <p className="whitespace-pre-wrap">{text}</p>;
  return (
    <p className="whitespace-pre-wrap">
      {text.slice(0, start)}
      <mark className="rounded-[3px] bg-highlight px-0.5 text-ink">{evidence}</mark>
      {text.slice(start + evidence.length)}
    </p>
  );
}

/* ---------- priority breakdown (stacked bar + legend table) ---------- */

const BREAKDOWN: { key: keyof PriorityBreakdown; label: string; color: string }[] = [
  { key: "days_past_window", label: "Days overdue", color: "var(--series-1)" },
  { key: "stakes", label: "Stakes", color: "var(--series-2)" },
  { key: "deferral_count", label: "Deferrals", color: "var(--series-3)" },
  { key: "touch_count", label: "Times chased", color: "var(--series-4)" },
  { key: "counterparty_unreliability", label: "Their track record", color: "var(--series-5)" },
];

function PriorityBreakdownChart({ total, breakdown }: { total: number; breakdown: PriorityBreakdown }) {
  const parts = BREAKDOWN.map((b) => ({ ...b, value: breakdown[b.key] }));
  const sum = parts.reduce((acc, p) => acc + p.value, 0) || 1;
  return (
    <section aria-labelledby="priority-heading">
      <div className="flex items-baseline justify-between">
        <h3 id="priority-heading" className="eyebrow">
          Why it ranks here
        </h3>
        <p className="tabular text-sm text-ink-2">
          Score <span className="font-semibold text-ink">{Math.round(total)}</span>
        </p>
      </div>
      <div className="mt-3 flex h-2.5 gap-[2px] overflow-hidden rounded-[4px]" role="img" aria-label={`Priority score ${total}, breakdown listed below`}>
        {parts
          .filter((p) => p.value > 0)
          .map((p) => (
            <span
              key={p.key}
              title={`${p.label}: ${p.value}`}
              className="h-full first:rounded-l-[4px] last:rounded-r-[4px]"
              style={{ width: `${(p.value / sum) * 100}%`, background: p.color }}
            />
          ))}
      </div>
      <table className="mt-3 w-full text-sm">
        <caption className="sr-only">Priority score components</caption>
        <tbody>
          {parts.map((p) => (
            <tr key={p.key} className="text-ink-2">
              <th scope="row" className="py-1 text-left font-normal">
                <span className="inline-flex items-center gap-2">
                  <span className="size-2.5 rounded-[3px]" style={{ background: p.color }} aria-hidden="true" />
                  {p.label}
                </span>
              </th>
              <td className="tabular py-1 text-right text-ink">{p.value.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

/* ---------- deferral chain ---------- */

function DeferralChain({ detail }: { detail: LoopDetail }) {
  const { search } = useLocation();
  const chain: { loop: Loop; current: boolean }[] = [
    ...detail.ancestors.map((loop) => ({ loop, current: false })),
    { loop: detail.loop, current: true },
    ...detail.children.map((loop) => ({ loop, current: false })),
  ];
  if (chain.length === 1) return null;
  return (
    <section aria-labelledby="chain-heading">
      <h3 id="chain-heading" className="eyebrow">
        Deferral chain
      </h3>
      <p className="mt-1 text-sm text-ink-3">Each re-promise becomes a child loop, so the original history is never overwritten.</p>
      <ol className="relative mt-3 flex flex-col gap-2 before:absolute before:bottom-4 before:left-[7px] before:top-4 before:w-px before:bg-line-strong">
        {chain.map(({ loop, current }) => (
          <li key={loop.id} className="relative flex items-start gap-3">
            <span
              className={`relative z-10 mt-3.5 size-[15px] shrink-0 rounded-full border-2 ${current ? "border-signal bg-signal" : "border-line-strong bg-surface"}`}
              aria-hidden="true"
            />
            <Link
              to={{ pathname: `/loops/${loop.id}`, search }}
              aria-current={current ? "true" : undefined}
              className={`flex min-w-0 flex-1 items-center justify-between gap-3 rounded-lg border px-3 py-2.5 transition-colors duration-150 ${
                current ? "border-line-strong bg-sunken" : "border-line hover:bg-sunken"
              }`}
            >
              <span className="min-w-0">
                <span className="block truncate text-sm font-medium text-ink">{loop.promise}</span>
                <span className="text-xs text-ink-3">
                  Due {formatDate(loop.due_at)}
                  {current && " · this loop"}
                </span>
              </span>
              <StatusBadge status={loop.status} />
            </Link>
          </li>
        ))}
      </ol>
    </section>
  );
}

/* ---------- timeline ---------- */

const EVENT: Record<LoopEventType, { label: string; icon: Icon; tone: string }> = {
  created: { label: "Loop created", icon: Plus, tone: "bg-sunken text-ink-2" },
  touched: { label: "Chased", icon: PaperPlaneTilt, tone: "bg-info-soft text-info" },
  reply_received: { label: "Reply received", icon: ArrowBendUpLeft, tone: "bg-info-soft text-info" },
  deferred: { label: "Judged: deferred", icon: ClockCounterClockwise, tone: "bg-warn-soft text-warn" },
  transferred: { label: "Judged: transferred", icon: UserSwitch, tone: "bg-info-soft text-info" },
  disputed: { label: "Judged: disputed", icon: Warning, tone: "bg-crit-soft text-crit" },
  escalated: { label: "Escalated to you", icon: WarningOctagon, tone: "bg-crit-soft text-crit" },
  closed_verified: { label: "Closed · verified", icon: SealCheck, tone: "bg-good-soft text-good" },
  closed_claimed: { label: "Closed · claimed", icon: SealQuestion, tone: "bg-warn-soft text-warn" },
  abandoned: { label: "Abandoned", icon: Prohibit, tone: "bg-sunken text-ink-2" },
};

function EventDetail({ text }: { text: string }) {
  if (text.length <= 180) return <p className="mt-0.5 whitespace-pre-wrap text-sm text-ink-2">{text}</p>;
  return (
    <details className="group mt-0.5 text-sm text-ink-2">
      <summary className="cursor-pointer list-none">
        {text.slice(0, 140)}… <span className="font-medium text-ink underline underline-offset-2 group-open:hidden">Show all</span>
      </summary>
      <p className="mt-1 whitespace-pre-wrap">{text}</p>
    </details>
  );
}

function Timeline({ events }: { events: LoopEvent[] }) {
  const judgedReplies = new Set(events.filter((e) => e.evidence_span && e.reply_text).map((e) => e.reply_text));
  return (
    <section aria-labelledby="timeline-heading">
      <h3 id="timeline-heading" className="eyebrow">
        Timeline
      </h3>
      <ol className="mt-3 flex flex-col">
        {events.map((event, index) => {
          const config = EVENT[event.event_type];
          const showReply = event.reply_text && (event.evidence_span || !judgedReplies.has(event.reply_text));
          return (
            <li key={event.id} className="relative flex gap-3 pb-5 last:pb-0">
              {index < events.length - 1 && <span className="absolute bottom-0 left-[13px] top-7 w-px bg-line" aria-hidden="true" />}
              <span className={`relative flex size-7 shrink-0 items-center justify-center rounded-full ${config.tone}`}>
                <config.icon size={14} weight="bold" aria-hidden="true" />
              </span>
              <div className="min-w-0 flex-1 pt-0.5">
                <p className="text-sm">
                  <span className="font-medium text-ink">{config.label}</span>
                  <span className="text-ink-3">
                    {" "}
                    · <time dateTime={event.occurred_at}>{formatDateTime(event.occurred_at)}</time>
                    {event.channel && ` · ${event.channel}`}
                  </span>
                </p>
                {event.detail && <EventDetail text={event.detail} />}
                {showReply && (
                  <figure className="mt-2 rounded-lg border border-line bg-sunken px-3 py-2.5 text-sm text-ink">
                    <EvidenceText text={event.reply_text!} evidence={event.evidence_span} />
                    {event.evidence_span && (
                      <figcaption className="mt-2 flex items-center gap-1.5 text-xs text-ink-3">
                        <span className="size-2.5 rounded-[2px] bg-highlight" aria-hidden="true" />
                        Highlighted: the exact words the verdict rests on
                      </figcaption>
                    )}
                  </figure>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

/* ---------- next action ---------- */

function NextAction({ detail }: { detail: LoopDetail }) {
  const queryClient = useQueryClient();
  const { loop } = detail;
  const pursue = useMutation({
    mutationFn: () => api.pursue(loop.id),
    onSuccess: () => queryClient.invalidateQueries(),
  });

  if (detail.children.length > 0) {
    return (
      <Callout title="Superseded by a re-promise">
        The newest loop in the deferral chain carries the live commitment, so this one isn't chased on its own.
      </Callout>
    );
  }
  if (loop.status === "escalated_to_human") {
    const reason = [...loop.events].reverse().find((e) => ["escalated", "disputed", "transferred"].includes(e.event_type));
    return (
      <Callout title="Handed to you" tone="crit">
        Latch stopped chasing this one{reason ? `: ${reason.detail}` : "."}
      </Callout>
    );
  }
  if (loop.status === "closed_claimed") {
    return (
      <Callout title="Claimed, not verified" tone="warn">
        They say it's done, but it isn't in the system of record. Latch doesn't take their word for it; confirm it yourself.
      </Callout>
    );
  }
  if (loop.status !== "open" && loop.status !== "awaiting_reply") return null;

  return (
    <section aria-labelledby="action-heading" className="rounded-xl border border-line bg-surface">
      <div className="border-b border-line px-4 py-3">
        <h3 id="action-heading" className="eyebrow">
          Next action
        </h3>
        <p className="mt-1 text-sm text-ink-2">
          The Pursuer checks the system of record and the inbox first, then decides for itself whether to email, switch channel, or
          escalate to you. It can send a real email.
        </p>
      </div>
      <div className="px-4 py-3">
        <p className="text-xs font-medium text-ink-3">Drafted follow-up</p>
        <pre className="mt-1.5 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg bg-sunken px-3 py-2.5 font-sans text-sm text-ink-2">{detail.draft}</pre>
      </div>
      <div className="flex flex-col gap-3 border-t border-line px-4 py-3">
        <Button variant="primary" icon={Robot} loading={pursue.isPending} onClick={() => pursue.mutate()} className="self-start">
          {pursue.isPending ? "Pursuer is working…" : "Run Pursuer"}
        </Button>
        <div aria-live="polite">
          {pursue.isPending && <p className="text-sm text-ink-3">Checking the record and the inbox. This can take up to a minute.</p>}
          {pursue.isError && (
            <p role="alert" className="text-sm text-crit">
              {pursue.error.message}
            </p>
          )}
          {pursue.data && (
            <div className="rounded-lg border border-line bg-sunken px-3 py-2.5">
              <p className="text-xs font-medium text-ink-3">The Pursuer's decision</p>
              <p className="mt-1 whitespace-pre-wrap text-sm text-ink">{pursue.data.result}</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function Callout({ title, tone = "neutral", children }: { title: string; tone?: "neutral" | "crit" | "warn"; children: React.ReactNode }) {
  const tones = { neutral: "border-line bg-sunken", crit: "border-crit-line bg-crit-soft", warn: "border-warn-line bg-warn-soft" };
  const titleTones = { neutral: "text-ink", crit: "text-crit", warn: "text-warn" };
  return (
    <section className={`rounded-xl border px-4 py-3 ${tones[tone]}`}>
      <p className={`text-sm font-semibold ${titleTones[tone]}`}>{title}</p>
      <p className="mt-1 text-sm text-ink-2">{children}</p>
    </section>
  );
}

/* ---------- drawer ---------- */

function Fact({ label, children, wide = false }: { label: string; children: React.ReactNode; wide?: boolean }) {
  return (
    <div className={wide ? "col-span-2" : ""}>
      <dt className="text-xs text-ink-3">{label}</dt>
      <dd className="mt-0.5 text-sm text-ink">{children}</dd>
    </div>
  );
}

function DrawerBody({ detail }: { detail: LoopDetail }) {
  const { loop } = detail;
  const due = dueLabel(loop.due_at);
  const quoteSource = loop.source_meeting_id ? `Said in ${loop.source_meeting_id}` : loop.parent_id ? "From their reply" : "Source";
  return (
    <div className="flex flex-col gap-7">
      <figure className="border-l-2 border-signal pl-4">
        <Quotes size={18} weight="fill" className="text-ink-3" aria-hidden="true" />
        <blockquote className="mt-1 text-[1.0625rem] leading-relaxed text-ink">{loop.source_quote}</blockquote>
        <figcaption className="eyebrow mt-2">{quoteSource}</figcaption>
      </figure>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-4">
        <Fact label="Due">
          {formatDate(loop.due_at)} · <span className={due.overdue ? "font-medium text-crit" : ""}>{due.text}</span>
        </Fact>
        <Fact label="Window">
          <WindowBadge source={loop.window_source} />
        </Fact>
        <Fact label="Owner">
          {loop.owner_name}
          <span className="block truncate text-ink-3">{loop.owner_email}</span>
        </Fact>
        <Fact label="Stakes">
          <StakesLabel stakes={loop.stakes} />
        </Fact>
        <Fact label="Closes when" wide>
          {loop.closure_criterion}
        </Fact>
        <Fact label="Chased">
          <span className="tabular">{loop.touch_count}</span> time{loop.touch_count === 1 ? "" : "s"}
          {loop.channels_tried.length > 0 && <span className="text-ink-3"> · {loop.channels_tried.join(", ")}</span>}
        </Fact>
        <Fact label="Deferred">
          <span className="tabular">{loop.deferral_count}</span> time{loop.deferral_count === 1 ? "" : "s"}
        </Fact>
      </dl>

      <NextAction detail={detail} />
      <PriorityBreakdownChart total={detail.priority_total} breakdown={detail.priority_breakdown} />
      <DeferralChain detail={detail} />
      <Timeline events={loop.events} />
    </div>
  );
}

export function LoopDrawer() {
  const { loopId = "" } = useParams();
  const navigate = useNavigate();
  const { search } = useLocation();
  const query = useQuery({ queryKey: ["loop", loopId], queryFn: () => api.loop(loopId), refetchInterval: 15_000 });
  const loop = query.data?.loop;

  return (
    <Dialog.Root open onOpenChange={(open) => !open && navigate({ pathname: "/", search })}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-ink/40 data-[state=open]:animate-[fade-in_180ms_ease-out]" />
        <Dialog.Content
          aria-describedby={undefined}
          className="fixed inset-y-0 right-0 z-50 flex w-full max-w-[40rem] flex-col border-l border-line bg-paper shadow-[0_0_0_1px_var(--line)] outline-none data-[state=open]:animate-[drawer-in_240ms_cubic-bezier(0.2,0.8,0.2,1)]"
        >
          <header className="flex items-start justify-between gap-4 border-b border-line bg-surface px-5 py-4 sm:px-6">
            <div className="min-w-0">
              {loop ? (
                <>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={loop.status} />
                    <span className="eyebrow">{loop.counterparty_org}</span>
                  </div>
                  <Dialog.Title className="mt-2 text-lg font-semibold tracking-[-0.02em] text-ink">{loop.promise}</Dialog.Title>
                </>
              ) : (
                <>
                  <Dialog.Title className="sr-only">Loop details</Dialog.Title>
                  <Skeleton className="h-5 w-24" />
                  <Skeleton className="mt-3 h-6 w-72" />
                </>
              )}
            </div>
            <Dialog.Close asChild>
              <button
                aria-label="Close"
                className="flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-lg text-ink-2 transition-colors duration-150 hover:bg-sunken hover:text-ink"
              >
                <X size={18} weight="bold" aria-hidden="true" />
              </button>
            </Dialog.Close>
          </header>
          <div className="flex-1 overflow-y-auto px-5 py-6 sm:px-6">
            {query.isPending ? (
              <div className="flex flex-col gap-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-48 w-full" />
              </div>
            ) : query.isError ? (
              <ErrorState error={query.error} onRetry={() => query.refetch()} />
            ) : (
              <DrawerBody detail={query.data} />
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
