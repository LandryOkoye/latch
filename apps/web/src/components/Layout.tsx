import { ChartBar, ListChecks, Waveform, type Icon } from "@phosphor-icons/react";
import { NavLink, Outlet } from "react-router-dom";
import { Lockup } from "./Logo";

const NAV: { to: string; label: string; icon: Icon; end?: boolean }[] = [
  { to: "/", label: "Worklist", icon: ListChecks, end: true },
  { to: "/reliability", label: "Reliability", icon: ChartBar },
  { to: "/meetings/new", label: "New meeting", icon: Waveform },
];

function NavItem({ to, label, icon: IconComponent, end }: (typeof NAV)[number]) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `group relative flex h-9 shrink-0 items-center gap-2.5 rounded-lg px-3 text-sm font-medium transition-colors duration-150 ${
          isActive ? "bg-surface text-ink shadow-[0_0_0_1px_var(--line)]" : "text-ink-2 hover:bg-sunken hover:text-ink"
        }`
      }
    >
      {({ isActive }) => (
        <>
          <IconComponent size={18} weight={isActive ? "fill" : "regular"} aria-hidden="true" className={isActive ? "text-signal" : ""} />
          {label}
        </>
      )}
    </NavLink>
  );
}

export function Layout() {
  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[15rem_1fr]">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-ink focus:px-3 focus:py-2 focus:text-paper"
      >
        Skip to content
      </a>

      <aside className="sticky top-0 z-30 border-b border-line bg-paper/95 backdrop-blur-sm lg:h-dvh lg:border-b-0 lg:border-r">
        <div className="flex h-full flex-col gap-4 px-4 py-3 lg:gap-8 lg:px-4 lg:py-6">
          <div className="flex items-center justify-between lg:px-2">
            <NavLink to="/" aria-label="Latch home">
              <Lockup />
            </NavLink>
          </div>
          <nav aria-label="Main" className="-mx-1 flex gap-1 overflow-x-auto px-1 lg:mx-0 lg:flex-col lg:overflow-visible lg:px-0">
            {NAV.map((item) => (
              <NavItem key={item.to} {...item} />
            ))}
          </nav>
          <div className="mt-auto hidden px-2 lg:block">
            <p className="text-sm text-ink-2">Every promise, tracked to close.</p>
            <p className="eyebrow mt-3">Strands Agents · Amazon Bedrock</p>
          </div>
        </div>
      </aside>

      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-6xl px-4 py-8 outline-none sm:px-6 lg:px-10 lg:py-10">
        <Outlet />
      </main>
    </div>
  );
}
