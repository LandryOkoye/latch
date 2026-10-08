import { ArrowClockwise, CircleNotch, WarningCircle, type Icon } from "@phosphor-icons/react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-ink text-paper hover:bg-ink/85 border-transparent",
  secondary: "bg-surface text-ink border-line-strong hover:bg-sunken",
  ghost: "bg-transparent text-ink-2 border-transparent hover:bg-sunken hover:text-ink",
};

export function Button({
  variant = "secondary",
  icon: IconComponent,
  loading = false,
  children,
  className = "",
  disabled,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; icon?: Icon; loading?: boolean }) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`inline-flex h-9 cursor-pointer items-center justify-center gap-2 rounded-lg border px-3.5 text-sm font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 ${BUTTON_VARIANTS[variant]} ${className}`}
    >
      {loading ? (
        <CircleNotch size={16} weight="bold" className="animate-spin" aria-hidden="true" />
      ) : (
        IconComponent && <IconComponent size={16} weight="bold" aria-hidden="true" />
      )}
      {children}
    </button>
  );
}

export function PageHeader({ eyebrow, title, description, actions }: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl">
        <p className="eyebrow">{eyebrow}</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-ink sm:text-[1.75rem]">{title}</h1>
        <p className="mt-1.5 text-[0.9375rem] leading-relaxed text-ink-2">{description}</p>
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </header>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-xl border border-line bg-surface ${className}`}>{children}</div>;
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-sunken ${className}`} aria-hidden="true" />;
}

export function EmptyState({ icon: IconComponent, title, children }: { icon: Icon; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      <span className="flex size-10 items-center justify-center rounded-full bg-sunken text-ink-2">
        <IconComponent size={20} weight="bold" aria-hidden="true" />
      </span>
      <p className="mt-3 font-medium text-ink">{title}</p>
      {children && <div className="mt-1 max-w-sm text-sm text-ink-2">{children}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: Error; onRetry: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center px-6 py-14 text-center">
      <span className="flex size-10 items-center justify-center rounded-full bg-crit-soft text-crit">
        <WarningCircle size={20} weight="bold" aria-hidden="true" />
      </span>
      <p className="mt-3 font-medium text-ink">Couldn't load this</p>
      <p className="mt-1 max-w-sm text-sm text-ink-2">{error.message}</p>
      <Button className="mt-4" icon={ArrowClockwise} onClick={onRetry}>
        Try again
      </Button>
    </div>
  );
}
