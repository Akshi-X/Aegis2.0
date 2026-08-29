/**
 * AEGIS-X brand mark: a geometric shield (security / governance) with a check
 * (an approved, guarded action). Renders standalone — the shield takes
 * `currentColor` (set it to the brand blue) and the check is white, so it reads
 * cleanly on a light background without needing a filled tile behind it.
 */
export function AegisMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" className={className} aria-hidden="true">
      <path
        d="M16 6.5 L25 9.7 L25 16.5 C25 22.3 21.3 26.4 16 28.8 C10.7 26.4 7 22.3 7 16.5 L7 9.7 Z"
        fill="currentColor"
      />
      <path
        d="M11.6 16.3 L14.8 19.5 L20.9 12.7"
        fill="none"
        stroke="#ffffff"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
