const ITEMS = [
  { kind: "stock", symbol: "✓", label: "In stock" },
  { kind: "out", symbol: "✕", label: "Out of stock" },
  { kind: "unknown", symbol: "?", label: "No information" },
] as const;

export function MapLegend({ counts }: { counts: Record<"stock" | "out" | "unknown", number> }) {
  return (
    <ul aria-label="Map legend" className="flex flex-wrap gap-x-5 gap-y-2">
      {ITEMS.map((item) => (
        <li key={item.kind} className="flex items-center gap-2">
          <span className={`marker-pin marker-pin--${item.kind}`} style={{ width: 24, height: 24, fontSize: 13 }} aria-hidden>
            {item.symbol}
          </span>
          <span>
            {item.label} <span className="text-muted">({counts[item.kind]})</span>
          </span>
        </li>
      ))}
      <li className="flex items-center gap-2">
        <span className="marker-pin marker-pin--you" style={{ width: 16, height: 16, outlineWidth: 4 }} aria-hidden />
        Your position
      </li>
    </ul>
  );
}
