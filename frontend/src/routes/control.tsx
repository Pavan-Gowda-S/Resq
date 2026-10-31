import { createFileRoute } from "@tanstack/react-router";
import { Ambulance, Anchor, BedDouble, HeartPulse, Map as MapIcon, Terminal, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { KeralaMap } from "@/components/resq/kerala-map";
import { Panel, TriageBadge } from "@/components/resq/shell";
import { listIncidents } from "@/lib/api";
import { nextFeed, SEED_INCIDENTS, SEED_UNITS, type FeedItem, type MapPoint, type Triage } from "@/lib/resq-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/control")({
  head: () => ({
    meta: [
      { title: "RESQ District Control Room — Command center" },
      { name: "description", content: "Live GIS map, AI agent decisions and crisis analytics for Kerala district coordinators." },
      { property: "og:title", content: "RESQ District Control Room" },
      { property: "og:description", content: "Live command center for Kerala flood & landslide response." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: ControlRoom,
});

const PRIO: Record<string, Triage> = { CRITICAL: "RED", HIGH: "RED", MEDIUM: "YELLOW", LOW: "GREEN" };

function ControlRoom() {
  const [points, setPoints] = useState<MapPoint[]>([...SEED_INCIDENTS, ...SEED_UNITS]);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [stats, setStats] = useState({ casualties: 312, rescued: 1847, boats: 46, ambulances: 72, beds: 87 });
  const [source, setSource] = useState<"live" | "sim">("sim");

  // Try to load real incidents (requires dispatcher sign-in)
  useEffect(() => {
    listIncidents()
      .then((list) => {
        if (!list.length) return;
        setSource("live");
        setPoints((p) => [
          ...list.map((i) => ({ id: i.id, kind: "incident" as const, lat: i.location.coordinates[1], lng: i.location.coordinates[0], severity: PRIO[i.priority] ?? "YELLOW", label: i.incident_number })),
          ...p.filter((x) => x.kind === "unit"),
        ]);
      })
      .catch(() => setSource("sim"));
  }, []);

  useEffect(() => {
    let i = 0;
    setFeed([nextFeed(i++), nextFeed(i++), nextFeed(i++)]);
    const id = setInterval(() => {
      setFeed((f) => [nextFeed(i++), ...f].slice(0, 40));
      setPoints((p) => p.map((x) => (x.kind === "unit" ? { ...x, lat: x.lat + (Math.random() - 0.5) * 0.05, lng: x.lng + (Math.random() - 0.5) * 0.05 } : x)));
      setStats((s) => ({ ...s, rescued: s.rescued + Math.round(Math.random() * 3), casualties: s.casualties + (Math.random() > 0.8 ? 1 : 0), beds: Math.min(99, Math.max(70, s.beds + (Math.random() > 0.5 ? 1 : -1))) }));
    }, 2500);
    return () => clearInterval(id);
  }, []);

  const metrics = [
    { label: "Total Casualties", v: stats.casualties, icon: HeartPulse, tone: "text-primary" },
    { label: "Rescued", v: stats.rescued, icon: Users, tone: "text-success" },
    { label: "Boats Deployed", v: stats.boats, icon: Anchor, tone: "text-info" },
    { label: "Ambulances Active", v: stats.ambulances, icon: Ambulance, tone: "text-info" },
    { label: "Bed Saturation", v: `${stats.beds}%`, icon: BedDouble, tone: stats.beds > 90 ? "text-primary" : "text-warning" },
  ];

  const incidents = points.filter((p) => p.kind === "incident");

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <div className="label-caps">District Emergency Operations Centre · Wayanad</div>
          <h1 className="text-5xl font-bold uppercase">War Room</h1>
        </div>
        <span className={cn("rounded px-2 py-1 font-mono text-xs", source === "live" ? "bg-success text-success-foreground" : "bg-warning text-warning-foreground")}>
          {source === "live" ? "LIVE INCIDENT DATA" : "SIMULATION FEED"}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {metrics.map((m) => (
          <div key={m.label} className="rounded-lg border border-border bg-card p-4">
            <div className="label-caps flex items-center gap-1.5"><m.icon className="size-3.5" />{m.label}</div>
            <div className={cn("mt-1 font-mono text-4xl font-bold", m.tone)}>{m.v}</div>
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[380px_1fr_420px]">
        <Panel title="GIS · Kerala" icon={MapIcon} className="xl:row-span-2">
          <div className="h-[620px]"><KeralaMap points={points} highlight="Wayanad" /></div>
          <div className="mt-2 flex gap-4 font-mono text-[10px] text-muted-foreground">
            <span className="flex items-center gap-1"><span className="size-2 rounded-full bg-primary" />RED</span>
            <span className="flex items-center gap-1"><span className="size-2 rounded-full bg-warning" />YELLOW</span>
            <span className="flex items-center gap-1"><span className="size-2 rounded-full bg-success" />GREEN</span>
            <span className="flex items-center gap-1"><span className="size-2 rotate-45 bg-info" />UNIT</span>
          </div>
        </Panel>

        <Panel title="Active incidents" icon={HeartPulse}>
          <div className="divide-y divide-border">
            {incidents.map((i) => (
              <div key={i.id} className="flex items-center gap-3 py-2.5">
                <TriageBadge level={i.severity ?? "GREEN"} />
                <span className="flex-1 font-medium">{i.label}</span>
                <span className="font-mono text-xs text-muted-foreground">{i.lat.toFixed(2)}, {i.lng.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="AI agent perception" icon={Terminal} className="xl:row-span-2">
          <div className="h-[620px] overflow-y-auto rounded bg-surface p-3 font-mono text-xs leading-relaxed">
            {feed.map((f, idx) => (
              <div key={idx} className={cn("border-l-2 py-1 pl-2", f.level === "crit" ? "border-primary" : f.level === "warn" ? "border-warning" : "border-success")}>
                <span className="text-muted-foreground">{f.t}</span>{" "}
                <span className={cn("font-bold", f.level === "crit" ? "text-primary" : f.level === "warn" ? "text-warning" : "text-success")}>[{f.agent}]</span>{" "}
                <span>{f.msg}</span>
              </div>
            ))}
            <span className="animate-blink">▌</span>
          </div>
        </Panel>

        <Panel title="District load">
          <div className="grid gap-2">
            {[["Wayanad", 92], ["Idukki", 71], ["Alappuzha", 64], ["Pathanamthitta", 48], ["Ernakulam", 33]].map(([d, v]) => (
              <div key={d} className="flex items-center gap-3 text-sm">
                <span className="w-32">{d}</span>
                <div className="h-2 flex-1 rounded bg-muted"><div className={cn("h-2 rounded", Number(v) > 80 ? "bg-primary" : Number(v) > 55 ? "bg-warning" : "bg-success")} style={{ width: `${v}%` }} /></div>
                <span className="w-10 text-right font-mono">{v}%</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
