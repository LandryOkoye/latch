import { useId } from "react";

/** The Latch mark: a ring held shut by the signal-orange latch bar.
 *  Geometry follows the v1.0 lockup; the stroke thickens at small sizes. */
export function LatchMark({ size = 24, className }: { size?: number; className?: string }) {
  const maskId = useId();
  const stroke = size < 32 ? 25 : 21;
  const radius = 69 - stroke / 2;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 138 141"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <mask id={maskId}>
        <rect x="-10" y="-10" width="160" height="160" fill="white" />
        <rect x="31" y="-4" width="76" height="33" rx="6" fill="black" />
      </mask>
      <circle cx="69" cy="72" r={radius} fill="none" stroke="currentColor" strokeWidth={stroke} mask={`url(#${maskId})`} />
      <rect x="35" y="0" width="68" height="25" rx="3.5" fill="var(--signal)" />
    </svg>
  );
}

export function Wordmark({ className = "" }: { className?: string }) {
  return <span className={`font-semibold tracking-[-0.06em] leading-none ${className}`}>latch</span>;
}

/** Compact lockup for nav bars. */
export function Lockup() {
  return (
    <span className="inline-flex items-center gap-2 text-ink" aria-label="Latch">
      <LatchMark size={22} />
      <Wordmark className="text-[1.375rem]" />
    </span>
  );
}
