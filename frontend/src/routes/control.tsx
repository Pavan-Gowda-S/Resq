import { createFileRoute } from "@tanstack/react-router";
import { Ambulance, Anchor, BedDouble, HeartPulse, Map as MapIcon, Terminal, Users, RefreshCw, Radio } from "lucide-react";
import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { KeralaMap } from "@/components/resq/kerala-map";
import { Panel, TriageBadge } from "@/components/resq/shell";
import { Button } from "@/components/ui/button";
import { listIncidents, ensureDemoAuth, type Incident } from "@/lib/api";
import { getActiveCrisis, subscribeToCrisisUpdates } from "@/lib/crisis-sync";
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
  const [liveIncidents, setLiveIncidents] = useState<Incident[]>([]);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [stats, setStats] = useState({ casualties: 18, rescued: 42, boats: 14, ambulances: 26, beds: 88 });
  const [source, setSource] = useState<"live" | "sim">("sim");
  const [loading, setLoading] = useState(false);

  // Authenticate and load live incidents from the database
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      await ensureDemoAuth("Dispatcher");
      const list = await listIncidents();
      if (list && list.length > 0) {
        setSource("live");
        setLiveIncidents(list);
        setPoints((prev) => [
          ...list.map((i) => ({
            id: i.id,
            kind: "incident" as const,
            lat: i.location?.coordinates ? i.location.coordinates[1] : 11.56,
            lng: i.location?.coordinates ? i.location.coordinates[0] : 76.13,
            severity: PRIO[i.priority] ?? "YELLOW",
            label: i.incident_number,
          })),
          ...prev.filter((x) => x.kind === "unit"),
        ]);
        toast.success(`Loaded ${list.length} live incidents from database`);
      } else {
        setSource("live");
      }
    } catch (err) {
      console.warn("Could not fetch live incidents:", err);
      setSource("sim");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Synchronize with active crisis reported by citizen or simulator
  useEffect(() => {
    const unsub = subscribeToCrisisUpdates((crisis) => {
      if (crisis) {
        setLiveIncidents((prev) => {
          if (prev.some((x) => x.incident_number === crisis.incidentNumber)) {
            return prev.map((x) => (x.incident_number === crisis.incidentNumber ? { ...x, status: crisis.status } : x));
          }
          const newInc: Incident = {
            id: crisis.incidentId,
            incident_number: crisis.incidentNumber,
            status: crisis.status,
            priority: "CRITICAL",
            hazard_type: "FLOOD",
            description: crisis.description,
            location: { coordinates: crisis.coordinates },
            district: crisis.district,
            people_affected: crisis.peopleAffected,
            trapped_count: crisis.trappedCount,
            injured_count: 1,
            created_at: new Date(crisis.updatedAt).toISOString(),
          };
          return [newInc, ...prev];
        });

        setFeed((prev) => {
          const dispatchKey = `${crisis.incidentNumber}-dispatch`;
          if (prev.some((x) => x.id === dispatchKey)) return prev;
          return [
            {
              id: dispatchKey,
              agent: "TaskDispatchAgent",
              text: `Assigned ${crisis.incidentNumber} to ${crisis.assignedRescue.unitName} (PostGIS nearest-neighbor: ${crisis.assignedRescue.distanceKm} km)`,
              time: new Date().toLocaleTimeString(),
              confidence: 96,
              latency: 184,
            },
            {
              id: `${crisis.incidentNumber}-hospital`,
              agent: "HospitalRoutingAgent",
              text: `Atomic ICU Bed reserved at ${crisis.assignedHospital.name} for ${crisis.incidentNumber}`,
              time: new Date().toLocaleTimeString(),
              confidence: 95,
              latency: 142,
            },
            ...prev,
          ];
        });

        setPoints((prev) => {
          if (prev.some((p) => p.label === crisis.incidentNumber)) return prev;
          return [
            {
              id: crisis.incidentId,
              kind: "incident",
              lat: crisis.coordinates[1],
              lng: crisis.coordinates[0],
              severity: "RED",
              label: crisis.incidentNumber,
            },
            ...prev,
          ];
        });
      }
    });
    return unsub;
  }, []);

  // Terminal telemetry feed simulation
  useEffect(() => {
    let i = 0;
    setFeed([nextFeed(i++), nextFeed(i++), nextFeed(i++)]);
    const id = setInterval(() => {
      setFeed((f) => [nextFeed(i++), ...f].slice(0, 40));
      setPoints((p) =>
        p.map((x) =>
          x.kind === "unit"
            ? {
                ...x,
                lat: x.lat + (Math.random() - 0.5) * 0.005,
                lng: x.lng + (Math.random() - 0.5) * 0.005,
              }
            : x
        )
      );
    }, 3000);
    return () => clearInterval(id);
  }, []);

  const metrics = [
    { label: "Casualties Tracked", v: stats.casualties, icon: HeartPulse, tone: "text-primary" },
    { label: "Rescued to Safety", v: stats.rescued, icon: Users, tone: "text-emerald-500" },
    { label: "Boats Deployed", v: stats.boats, icon: Anchor, tone: "text-sky-400" },
    { label: "Ambulances Active", v: stats.ambulances, icon: Ambulance, tone: "text-sky-400" },
    { label: "ICU Bed Saturation", v: `${stats.beds}%`, icon: BedDouble, tone: stats.beds > 90 ? "text-primary" : "text-amber-500" },
  ];

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-500 border border-emerald-500/20">
              <Radio className="size-3 text-emerald-500 animate-pulse" />
              DEOC Wayanad Command
            </span>
          </div>
          <h1 className="mt-1 text-4xl sm:text-5xl font-extrabold uppercase tracking-tight">
            War Room Operations
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
            <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh Feed
          </Button>
          <span
            className={cn(
              "rounded-full px-3 py-1 font-mono text-xs font-bold uppercase",
              source === "live"
                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
            )}
          >
            {source === "live" ? "● Live Database Connected" : "○ Simulation Mode"}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {metrics.map((m) => (
          <div key={m.label} className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <div className="label-caps flex items-center gap-1.5 font-semibold">
              <m.icon className="size-3.5" />
              {m.label}
            </div>
            <div className={cn("mt-1.5 font-mono text-3xl sm:text-4xl font-extrabold", m.tone)}>{m.v}</div>
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[380px_1fr_420px]">
        {/* GIS Map */}
        <Panel title="GIS Tactical Map · Kerala" icon={MapIcon} className="xl:row-span-2">
          <div className="h-[620px]">
            <KeralaMap points={points} highlight="Wayanad" />
          </div>
          <div className="mt-3 flex gap-4 font-mono text-[10px] text-muted-foreground border-t border-border/50 pt-2">
            <span className="flex items-center gap-1">
              <span className="size-2 rounded-full bg-red-500" /> Critical / Red
            </span>
            <span className="flex items-center gap-1">
              <span className="size-2 rounded-full bg-amber-500" /> Yellow
            </span>
            <span className="flex items-center gap-1">
              <span className="size-2 rounded-full bg-emerald-500" /> Green
            </span>
            <span className="flex items-center gap-1">
              <span className="size-2 rotate-45 bg-sky-400" /> Unit
            </span>
          </div>
        </Panel>

        {/* Live Active Incidents */}
        <Panel
          title="Active Incident Stream"
          icon={HeartPulse}
          action={
            <span className="label-caps font-mono">
              {liveIncidents.length > 0 ? `${liveIncidents.length} active` : "Monitored"}
            </span>
          }
        >
          <div className="divide-y divide-border max-h-[620px] overflow-y-auto pr-1">
            {liveIncidents.length > 0 ? (
              liveIncidents.map((inc) => (
                <div key={inc.id} className="py-3">
                  <div className="flex items-center justify-between">
                    <div className="font-mono font-bold text-sm text-foreground flex items-center gap-2">
                      {inc.incident_number}
                      <TriageBadge level={PRIO[inc.priority] ?? "YELLOW"} />
                    </div>
                    <span className="text-[11px] font-mono text-muted-foreground">
                      {new Date(inc.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1 line-clamp-2">
                    {inc.description}
                  </div>
                  <div className="flex items-center gap-3 mt-2 font-mono text-[11px] text-muted-foreground">
                    <span>District: <strong className="text-foreground">{inc.district}</strong></span>
                    <span>Trapped: <strong className="text-red-400">{inc.trapped_count}</strong></span>
                    <span>Affected: <strong className="text-amber-400">{inc.people_affected}</strong></span>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-muted-foreground">
                <p className="text-sm font-medium">No active incidents in queue.</p>
                <p className="text-xs mt-1">Submit an SOS from the Citizen Portal to trigger live routing.</p>
              </div>
            )}
          </div>
        </Panel>

        {/* AI Agent Telemetry & Reasoning Log */}
        <Panel title="AI Agent Decision Stream" icon={Terminal} action={<span className="label-caps text-emerald-400">4 Agents Online</span>}>
          <div className="h-[620px] overflow-y-auto font-mono text-xs divide-y divide-border/40">
            {feed.map((f) => (
              <div key={f.id} className="py-2.5">
                <div className="flex items-center justify-between text-muted-foreground text-[11px]">
                  <span className="text-sky-400 font-bold">{f.agent}</span>
                  <span>{f.time}</span>
                </div>
                <div className="mt-1 text-foreground leading-relaxed">{f.text}</div>
                <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
                  <span className="rounded bg-muted px-1.5 py-0.5">Confidence: {f.confidence}%</span>
                  <span className="rounded bg-muted px-1.5 py-0.5">Latency: {f.latency}ms</span>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
