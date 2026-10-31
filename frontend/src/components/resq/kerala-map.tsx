import { DISTRICTS, type MapPoint } from "@/lib/resq-data";
import { cn } from "@/lib/utils";

// Stylised GIS view of Kerala: lat 8.2–12.8, lng 74.8–77.4 projected to SVG.
const W = 360;
const H = 640;
const px = (lng: number) => ((lng - 74.8) / 2.6) * W;
const py = (lat: number) => ((12.8 - lat) / 4.6) * H;

// Rough Kerala outline (coast to Western Ghats)
const OUTLINE: [number, number][] = [
  [12.78, 74.86], [12.4, 75.0], [11.9, 75.3], [11.5, 75.6], [11.1, 75.85], [10.6, 75.95],
  [10.1, 76.15], [9.6, 76.3], [9.1, 76.45], [8.7, 76.7], [8.3, 77.05], [8.3, 77.2],
  [8.8, 77.2], [9.3, 77.25], [9.7, 77.2], [10.1, 77.25], [10.4, 76.9], [10.75, 76.85],
  [11.2, 76.75], [11.55, 76.45], [11.95, 76.2], [12.2, 75.8], [12.6, 75.35], [12.78, 74.86],
];

export function KeralaMap({ points, className, highlight }: { points: MapPoint[]; className?: string; highlight?: string }) {
  const path = OUTLINE.map(([la, lo], i) => `${i ? "L" : "M"}${px(lo).toFixed(1)},${py(la).toFixed(1)}`).join(" ") + "Z";
  const color = { RED: "var(--primary)", YELLOW: "var(--warning)", GREEN: "var(--success)" };
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={cn("h-full w-full", className)} role="img" aria-label="Kerala incident map">
      <defs>
        <radialGradient id="heat">
          <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.55" />
          <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
        </radialGradient>
      </defs>
      <path d={path} fill="var(--muted)" stroke="var(--border)" strokeWidth="2" />
      {DISTRICTS.map((d) => (
        <g key={d.name} opacity={highlight && highlight !== d.name ? 0.35 : 0.8}>
          <circle cx={px(d.lng)} cy={py(d.lat)} r="2" fill="var(--muted-foreground)" />
          <text x={px(d.lng) + 5} y={py(d.lat) + 3} fontSize="9" fill="var(--muted-foreground)" fontFamily="var(--font-mono)">
            {d.name.toUpperCase()}
          </text>
        </g>
      ))}
      {points.filter((p) => p.kind === "incident" && p.severity === "RED").map((p) => (
        <circle key={`h-${p.id}`} cx={px(p.lng)} cy={py(p.lat)} r="38" fill="url(#heat)" />
      ))}
      {points.map((p) =>
        p.kind === "incident" ? (
          <g key={p.id}>
            <circle cx={px(p.lng)} cy={py(p.lat)} r="6" fill={color[p.severity ?? "GREEN"]} stroke="var(--background)" strokeWidth="1.5">
              <title>{p.label}</title>
            </circle>
            {p.severity === "RED" && (
              <circle cx={px(p.lng)} cy={py(p.lat)} r="6" fill="none" stroke="var(--primary)">
                <animate attributeName="r" from="6" to="18" dur="1.6s" repeatCount="indefinite" />
                <animate attributeName="opacity" from="1" to="0" dur="1.6s" repeatCount="indefinite" />
              </circle>
            )}
          </g>
        ) : (
          <g key={p.id} style={{ transition: "transform 1.5s linear" }} transform={`translate(${px(p.lng)},${py(p.lat)})`}>
            <rect x="-5" y="-5" width="10" height="10" fill="var(--info)" transform="rotate(45)" />
            <text x="9" y="4" fontSize="9" fill="var(--info)" fontFamily="var(--font-mono)">{p.label}</text>
          </g>
        ),
      )}
    </svg>
  );
}
