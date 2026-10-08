import { CaretDown, CaretUp, CaretUpDown, ChartBar, Eye, Hourglass, SealCheck, WarningOctagon } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "../components/Badges";
import { Card, EmptyState, ErrorState, PageHeader, Skeleton } from "../components/ui";
import { api, type ReliabilityRow } from "../lib/api";
import { percent } from "../lib/format";

type SortKey = "counterparty_org" | "loops_opened" | "closed_on_time" | "median_touches_to_closure" | "deferral_rate" | "escalation_rate" | "unreliability_score";

const COLUMNS: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: "counterparty_org", label: "Counterparty", numeric: false },
  { key: "loops_opened", label: "Loops", numeric: true },
  { key: "closed_on_time", label: "Closed · verified", numeric: true },
  { key: "median_touches_to_closure", label: "Median chases", numeric: true },
  { key: "deferral_rate", label: "Deferral rate", numeric: true },
  { key: "escalation_rate", label: "Escalation rate", numeric: true },
  { key: "unreliability_score", label: "Standing", numeric: true },
];

function Standing({ score, closed }: { score: number; closed: number }) {
  if (score === 0 && closed === 0)
    return (
      <Badge tone="neutral" icon={Hourglass}>
        Too early
      </Badge>
    );
  if (score === 0)
    return (
      <Badge tone="good" icon={SealCheck}>
        Reliable
      </Badge>
    );
  if (score < 0.4)
    return (
      <Badge tone="warn" icon={Eye}>
        Watch
      </Badge>
    );
  return (
    <Badge tone="crit" icon={WarningOctagon}>
      Unreliable
    </Badge>
  );
}

function RateCell({ rate }: { rate: number }) {
  return (
    <div className="flex items-center justify-end gap-2.5">
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-sunken" aria-hidden="true">
        <span className="block h-full rounded-full bg-series-1" style={{ width: `${rate * 100}%` }} />
      </span>
      <span className="tabular w-9 text-right text-ink">{percent(rate)}</span>
    </div>
  );
}

function SortHeader({ column, sort, onSort }: { column: (typeof COLUMNS)[number]; sort: { key: SortKey; desc: boolean }; onSort: (key: SortKey) => void }) {
  const active = sort.key === column.key;
  const SortIcon = active ? (sort.desc ? CaretDown : CaretUp) : CaretUpDown;
  return (
    <th scope="col" aria-sort={active ? (sort.desc ? "descending" : "ascending") : "none"} className={`px-4 py-2.5 ${column.numeric ? "text-right" : "text-left"}`}>
      <button
        onClick={() => onSort(column.key)}
        className={`eyebrow inline-flex cursor-pointer items-center gap-1 hover:text-ink ${active ? "text-ink" : ""}`}
      >
        {column.label}
        <SortIcon size={12} weight="bold" aria-hidden="true" />
      </button>
    </th>
  );
}

export function Reliability() {
  const query = useQuery({ queryKey: ["reliability"], queryFn: api.reliability, refetchInterval: 15_000 });
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: "unreliability_score", desc: true });

  const rows = [...(query.data ?? [])].sort((a: ReliabilityRow, b: ReliabilityRow) => {
    const x = a[sort.key];
    const y = b[sort.key];
    const order = typeof x === "string" ? x.localeCompare(y as string) : (x as number) - (y as number);
    return sort.desc ? -order : order;
  });
  const totalLoops = rows.reduce((acc, r) => acc + r.loops_opened, 0);
  const onSort = (key: SortKey) => setSort((s) => ({ key, desc: s.key === key ? !s.desc : key !== "counterparty_org" }));

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow="Reliability"
        title="Who actually holds their dates"
        description="Built automatically from every loop Latch has tracked: how often each counterparty closed on time, deferred, or had to be escalated."
      />

      <Card className="overflow-hidden">
        {query.isPending ? (
          <div className="flex flex-col gap-3 p-5">
            {Array.from({ length: 5 }, (_, i) => (
              <Skeleton key={i} className="h-6 w-full" />
            ))}
          </div>
        ) : query.isError ? (
          <ErrorState error={query.error} onRetry={() => query.refetch()} />
        ) : rows.length === 0 ? (
          <EmptyState icon={ChartBar} title="No track record yet">
            Reliability builds up as loops are tracked and closed.
          </EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[52rem] text-sm">
              <caption className="border-b border-line px-4 py-3 text-left text-sm text-ink-2">
                <span className="tabular font-medium text-ink">{rows.length}</span> counterparties across{" "}
                <span className="tabular font-medium text-ink">{totalLoops}</span> loops
              </caption>
              <thead className="border-b border-line">
                <tr>
                  {COLUMNS.map((column) => (
                    <SortHeader key={column.key} column={column} sort={sort} onSort={onSort} />
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {rows.map((row) => (
                  <tr key={row.counterparty_org} className="transition-colors duration-150 hover:bg-sunken/60">
                    <th scope="row" className="px-4 py-3 text-left font-medium text-ink">
                      {row.counterparty_org}
                    </th>
                    <td className="tabular px-4 py-3 text-right text-ink">{row.loops_opened}</td>
                    <td className="tabular px-4 py-3 text-right text-ink">{row.closed_on_time}</td>
                    <td className="tabular px-4 py-3 text-right text-ink">
                      {row.closed_on_time ? row.median_touches_to_closure : <span className="text-ink-3">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      <RateCell rate={row.deferral_rate} />
                    </td>
                    <td className="px-4 py-3">
                      <RateCell rate={row.escalation_rate} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Standing score={row.unreliability_score} closed={row.closed_on_time} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <p className="max-w-2xl text-sm text-ink-3">
        Standing combines deferral and escalation rates equally. A closure only counts once it's verified against the system of
        record, never on the counterparty's word alone. Unreliable counterparties also push their loops up the worklist.
      </p>
    </div>
  );
}
