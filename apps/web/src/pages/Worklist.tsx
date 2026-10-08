import { CheckCircle } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { Link, Outlet, useSearchParams } from "react-router-dom";
import { StatusBadge } from "../components/Badges";
import { Card, EmptyState, ErrorState, PageHeader, Skeleton } from "../components/ui";
import { api, type Loop, type LoopStatus, type WorklistItem } from "../lib/api";
import { dueLabel } from "../lib/format";

const REFRESH_MS = 15_000;

const VIEWS = [
  { id: "all", label: "All active", statuses: null },
  { id: "needs-you", label: "Needs you", statuses: ["escalated_to_human", "closed_claimed"] },
  { id: "awaiting", label: "Awaiting reply", statuses: ["awaiting_reply"] },
  { id: "open", label: "Open", statuses: ["open"] },
] as const satisfies readonly { id: string; label: string; statuses: readonly LoopStatus[] | null }[];

type ViewId = (typeof VIEWS)[number]["id"];

function StatTile({ label, value, hint }: { label: string; value: number | undefined; hint: string }) {
  return (
    <Card className="px-4 py-3.5">
      <p className="eyebrow">{label}</p>
      {value === undefined ? (
        <Skeleton className="mt-2 h-8 w-10" />
      ) : (
        <p className="mt-1 text-[1.75rem] font-semibold tracking-[-0.03em] text-ink">{value}</p>
      )}
      <p className="mt-0.5 text-xs text-ink-3">{hint}</p>
    </Card>
  );
}

function Stats({ loops }: { loops: Loop[] | undefined }) {
  const count = (predicate: (loop: Loop) => boolean) => loops?.filter(predicate).length;
  const now = Date.now();
  return (
    <section aria-label="Summary" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <StatTile
        label="Needs you"
        value={count((l) => l.status === "escalated_to_human" || l.status === "closed_claimed")}
        hint="Escalated or unverified closures"
      />
      <StatTile label="Awaiting reply" value={count((l) => l.status === "awaiting_reply")} hint="Chased, waiting on them" />
      <StatTile
        label="Open & overdue"
        value={count((l) => l.status === "open" && new Date(l.due_at).getTime() < now)}
        hint="Next in line for the Pursuer"
      />
      <StatTile label="Closed · verified" value={count((l) => l.status === "closed_verified")} hint="Confirmed in the system of record" />
    </section>
  );
}

function ViewTabs({ active, counts, onChange }: { active: ViewId; counts: Record<ViewId, number>; onChange: (id: ViewId) => void }) {
  return (
    <div role="tablist" aria-label="Filter loops" className="flex gap-1 overflow-x-auto rounded-lg border border-line bg-sunken p-1">
      {VIEWS.map((view) => {
        const selected = view.id === active;
        return (
          <button
            key={view.id}
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(view.id)}
            className={`flex h-8 shrink-0 cursor-pointer items-center gap-2 rounded-md px-3 text-sm font-medium transition-colors duration-150 ${
              selected ? "bg-surface text-ink shadow-[0_0_0_1px_var(--line)]" : "text-ink-2 hover:text-ink"
            }`}
          >
            {view.label}
            <span className="tabular rounded bg-paper px-1.5 text-xs text-ink-3">{counts[view.id]}</span>
          </button>
        );
      })}
    </div>
  );
}

function PriorityCell({ total, max }: { total: number; max: number }) {
  return (
    <div className="flex items-center gap-2.5" title={`Priority score ${total}`}>
      <span className="tabular w-10 text-right text-sm font-semibold text-ink">{Math.round(total)}</span>
      <span className="h-1.5 w-full max-w-16 overflow-hidden rounded-full bg-sunken" aria-hidden="true">
        <span className="block h-full rounded-full bg-series-1" style={{ width: `${Math.max((total / max) * 100, 4)}%` }} />
      </span>
    </div>
  );
}

function LoopRow({ item, rank, max, search }: { item: WorklistItem; rank: number; max: number; search: string }) {
  const { loop } = item;
  const due = dueLabel(loop.due_at);
  return (
    <li>
      <Link
        to={{ pathname: `/loops/${loop.id}`, search }}
        className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-2 px-4 py-3.5 transition-colors duration-150 hover:bg-sunken/60 focus-visible:bg-sunken/60 md:grid-cols-[2rem_minmax(0,1fr)_10rem_8.5rem_9rem_6.5rem] md:px-5"
      >
        <span className="tabular hidden font-mono text-xs text-ink-3 md:block">{String(rank).padStart(2, "0")}</span>
        <span className="min-w-0">
          <span className="line-clamp-2 font-medium text-ink md:line-clamp-none md:block md:truncate">{loop.promise}</span>
          <span className="mt-0.5 block truncate text-sm text-ink-3">“{loop.source_quote}”</span>
        </span>
        <span className="md:hidden">
          <StatusBadge status={loop.status} />
        </span>
        <span className="min-w-0 text-sm">
          <span className="block truncate text-ink">{loop.owner_name}</span>
          <span className="block truncate text-ink-3">{loop.counterparty_org}</span>
        </span>
        <span className={`text-sm ${due.overdue ? "font-medium text-crit" : "text-ink-2"}`}>{due.text}</span>
        <span className="hidden md:block">
          <StatusBadge status={loop.status} />
        </span>
        <span className="col-span-2 md:col-span-1">
          <PriorityCell total={item.priority_total} max={max} />
        </span>
      </Link>
    </li>
  );
}

export function Worklist() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeView = (VIEWS.find((v) => v.id === searchParams.get("view"))?.id ?? "all") as ViewId;

  const worklist = useQuery({ queryKey: ["worklist"], queryFn: api.worklist, refetchInterval: REFRESH_MS });
  const loops = useQuery({ queryKey: ["loops"], queryFn: api.loops, refetchInterval: REFRESH_MS });

  const items = worklist.data ?? [];
  const inView = (id: ViewId) => {
    const statuses = VIEWS.find((v) => v.id === id)!.statuses as readonly LoopStatus[] | null;
    return statuses ? items.filter((i) => statuses.includes(i.loop.status)) : items;
  };
  const counts = Object.fromEntries(VIEWS.map((v) => [v.id, inView(v.id).length])) as Record<ViewId, number>;
  const visible = inView(activeView);
  const max = Math.max(...items.map((i) => i.priority_total), 1);

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow="Worklist"
        title="What needs attention first"
        description="Every commitment from your meetings that hasn't closed, ranked by how late it is, what's at stake, and how reliable the other side has been."
      />

      <Stats loops={loops.data} />

      <section aria-labelledby="loops-heading" className="flex flex-col gap-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 id="loops-heading" className="sr-only">
            Loops
          </h2>
          <ViewTabs
            active={activeView}
            counts={counts}
            onChange={(id) => setSearchParams(id === "all" ? {} : { view: id }, { replace: true })}
          />
          <p className="text-xs text-ink-3" aria-live="polite">
            {worklist.isFetching ? "Refreshing…" : "Updates every 15 seconds"}
          </p>
        </div>

        <Card className="overflow-hidden">
          <div className="hidden grid-cols-[2rem_minmax(0,1fr)_10rem_8.5rem_9rem_6.5rem] gap-x-4 border-b border-line px-5 py-2.5 md:grid">
            {["#", "Commitment", "Owner", "Due", "Status", "Priority"].map((h) => (
              <span key={h} className={`eyebrow ${h === "Priority" ? "pl-12" : ""}`}>
                {h}
              </span>
            ))}
          </div>
          {worklist.isPending ? (
            <ul aria-label="Loading loops" className="divide-y divide-line">
              {Array.from({ length: 5 }, (_, i) => (
                <li key={i} className="flex flex-col gap-2 px-5 py-4">
                  <Skeleton className="h-4 w-2/3" />
                  <Skeleton className="h-3 w-1/2" />
                </li>
              ))}
            </ul>
          ) : worklist.isError ? (
            <ErrorState error={worklist.error} onRetry={() => worklist.refetch()} />
          ) : visible.length === 0 ? (
            <EmptyState icon={CheckCircle} title="Nothing here">
              {activeView === "all" ? "No open commitments. Add a meeting to start tracking." : "No loops in this view right now."}
            </EmptyState>
          ) : (
            <ul className="divide-y divide-line">
              {visible.map((item, index) => (
                <LoopRow key={item.loop.id} item={item} rank={index + 1} max={max} search={searchParams.toString() ? `?${searchParams}` : ""} />
              ))}
            </ul>
          )}
        </Card>
      </section>

      <Outlet />
    </div>
  );
}
