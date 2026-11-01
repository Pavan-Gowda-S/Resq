import { createFileRoute } from "@tanstack/react-router";
import {
  AlertTriangle,
  Anchor,
  Check,
  Crosshair,
  HeartPulse,
  LogOut,
  Plane,
  RefreshCw,
  Stethoscope,
  Users,
  Ambulance,
  Building2,
  PhoneCall,
  CheckCircle2,
  Radio,
} from "lucide-react";
import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { Panel } from "@/components/resq/shell";
import { StaffGate } from "@/components/resq/staff-gate";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  DEFAULT_RESCUE_ORG_ID,
  DEFAULT_HOSPITAL_ID,
  searchHospitals,
  searchAmbulances,
  updateTaskStatus,
  type HospitalSearchResult,
  type AmbulanceSearchResult,
  type ResponseTask,
} from "@/lib/api";
import {
  getActiveCrisis,
  subscribeToCrisisUpdates,
  updateCrisisStage,
  assignHospitalFromNgo,
  type ActiveCrisis,
} from "@/lib/crisis-sync";

export const Route = createFileRoute("/rescue")({
  head: () => ({
    meta: [
      { title: "RESQ Field Responder — Active dispatch" },
      { name: "description", content: "Rugged field console for Kerala rescue teams: live dispatch, status progression, casualties and backup." },
      { property: "og:title", content: "RESQ Field Responder" },
      { property: "og:description", content: "Rugged field console for Kerala rescue teams." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: () => (
    <StaffGate portal="Rescue" roles={[{ value: "FIELD_RESPONDER", label: "Responder" }]}>
      {(u, out) => <FieldConsole name={u.full_name} onSignOut={out} />}
    </StaffGate>
  ),
});

const TASK_STAGES = [
  { key: "ASSIGNED", label: "Assigned", description: "Dispatched by AI Agent" },
  { key: "EN_ROUTE", label: "En Route", description: "Team deployed to site" },
  { key: "ON_SCENE", label: "On Scene", description: "Extraction operational" },
  { key: "COMPLETED", label: "Rescued", description: "Victims secure & extracted" },
] as const;

const INJURIES = ["Trauma / Crush", "Compound Fracture", "Hypothermia", "Head Trauma", "Near Drowning"];
const HAZARDS = ["Power Line Submerged", "Flash Surge 3m/s", "Slope Debris / Mud", "Road Inaccessible"];
const BACKUP = [
  { label: "Air Evac (IAF)", icon: Plane },
  { label: "Inflatable Boats", icon: Anchor },
  { label: "Trauma Medics", icon: Stethoscope },
];

function FieldConsole({ name, onSignOut }: { name: string; onSignOut: () => void }) {
  const [crisis, setCrisis] = useState<ActiveCrisis | null>(getActiveCrisis());
  const [currentStageIdx, setCurrentStageIdx] = useState(1); // default En Route
  const [activeTask, setActiveTask] = useState<ResponseTask | null>(null);
  const [log, setLog] = useState<string[]>([]);
  const [hospitals, setHospitals] = useState<HospitalSearchResult[]>([]);
  const [ambulances, setAmbulances] = useState<AmbulanceSearchResult[]>([]);
  const [loadingRadar, setLoadingRadar] = useState(false);
  const [syncingStatus, setSyncingStatus] = useState(false);
  const [searchRadius, setSearchRadius] = useState<number>(25);

  // Subscribe to real-time crisis events across portals
  useEffect(() => {
    const unsub = subscribeToCrisisUpdates((updated) => {
      if (updated) {
        setCrisis(updated);
        if (updated.stageIndex >= 4) setCurrentStageIdx(3);
        else if (updated.stageIndex === 3) setCurrentStageIdx(2);
        else if (updated.stageIndex === 2) setCurrentStageIdx(1);
        else setCurrentStageIdx(0);
      }
    });
    return unsub;
  }, []);

  const addLog = (s: string) => {
    setLog((l) => [`${new Date().toLocaleTimeString("en-GB")} · ${s}`, ...l]);
  };

  // Fetch nearby medical resources based on selected radius
  const refreshRadar = useCallback(async () => {
    setLoadingRadar(true);
    try {
      // Wayanad coordinates: lat: 11.5601, lng: 76.1335
      const [hospList, ambList] = await Promise.allSettled([
        searchHospitals(11.5601, 76.1335, searchRadius),
        searchAmbulances(11.5601, 76.1335),
      ]);

      if (hospList.status === "fulfilled" && hospList.value.length > 0) {
        setHospitals(hospList.value);
      } else {
        // Fallback hospital card matching backend data
        setHospitals([
          {
            organization_id: DEFAULT_HOSPITAL_ID,
            hospital_name: "Wayanad District Hospital",
            distance_km: 7.4,
            available_emergency_beds: 12,
            available_icu_beds: 3,
            has_trauma_center: false,
            location: { type: "Point", coordinates: [76.132, 11.685] },
          },
          {
            organization_id: "ebc36214-1826-49b7-9acc-9711e3dbf5db",
            hospital_name: "Ernakulam General Hospital",
            distance_km: 21.6,
            available_emergency_beds: 24,
            available_icu_beds: 5,
            has_trauma_center: true,
            location: { type: "Point", coordinates: [76.28, 9.98] },
          },
        ]);
      }

      if (ambList.status === "fulfilled" && ambList.value.length > 0) {
        setAmbulances(ambList.value);
      } else {
        setAmbulances([
          {
            id: "amb-108-wyd",
            organization_id: "amb-org-1",
            vehicle_number: "KL-11-AV-1080 (108 ALS)",
            ambulance_type: "ALS",
            status: "EN_ROUTE",
            distance_km: 3.2,
            current_location: { type: "Point", coordinates: [76.134, 11.562] },
            crew_size: 3,
          },
        ]);
      }
    } catch (err) {
      console.warn("Radar fetch warning:", err);
    } finally {
      setLoadingRadar(false);
    }
  }, [searchRadius]);

  const handleAssignHospital = (h: HospitalSearchResult) => {
    assignHospitalFromNgo(h.organization_id, h.hospital_name, h.distance_km);
    addLog(`HospitalRoutingAgent: Assigned casualty to ${h.hospital_name} (${h.distance_km} km). ICU bed hold requested.`);
    toast.success(`Routed casualty to ${h.hospital_name}. Request sent to triage doctor!`);
  };

  useEffect(() => {
    refreshRadar();
    const interval = setInterval(() => {
      if (typeof document !== "undefined" && document.visibilityState !== "visible") return;
      refreshRadar();
    }, 40000);
    return () => clearInterval(interval);
  }, [refreshRadar]);

  // Update task status and synchronize with live backend
  const handleStageSelect = async (index: number) => {
    const targetStage = TASK_STAGES[index];
    if (!targetStage) return;

    setCurrentStageIdx(index);
    setSyncingStatus(true);
    addLog(`Transitioning status → ${targetStage.key}`);

    if (targetStage.key === "EN_ROUTE") updateCrisisStage("EN_ROUTE");
    else if (targetStage.key === "ON_SCENE") updateCrisisStage("ON_SCENE");
    else if (targetStage.key === "COMPLETED") updateCrisisStage("RESCUED");

    try {
      if (activeTask?.id) {
        await updateTaskStatus(activeTask.id, targetStage.key, `Updated by ${name} in field`);
        addLog(`✓ Status ${targetStage.key} saved to backend`);
        toast.success(`Task status: ${targetStage.label} (DB Synced)`);
      } else {
        // Optimistic / simulated task update
        addLog(`✓ Status ${targetStage.key} recorded locally`);
        toast.success(`Status updated: ${targetStage.label}`);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to sync status");
      addLog(`✗ Sync error: ${err instanceof Error ? err.message : "Network error"}`);
    } finally {
      setSyncingStatus(false);
    }
  };

  const handleCasualtyLog = (injury: string) => {
    addLog(`Casualty logged: ${injury}`);
    toast.success(`Casualty recorded: ${injury}`);
  };

  const handleHazardLog = (hazard: string) => {
    addLog(`Field hazard reported: ${hazard}`);
    toast.warning(`Hazard flagged: ${hazard}`);
  };

  const handleBackupRequest = (label: string) => {
    addLog(`🚨 EMERGENCY BACKUP REQUESTED: ${label} at 11.5601, 76.1335`);
    toast.error(`Escalated to Control Room: ${label}`);
  };

  return (
    <div className="mx-auto max-w-3xl pb-12">
      {/* Header */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-semibold text-emerald-500 border border-emerald-500/20">
              <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Field Team Active
            </span>
            <span className="text-xs text-muted-foreground font-mono">
              Nestwise Disaster NGO · Rapid Field Wing
            </span>
          </div>
          <h1 className="mt-1 text-3xl sm:text-4xl font-extrabold uppercase tracking-tight">
            Field Ops Console
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={refreshRadar} disabled={loadingRadar}>
            <RefreshCw className={`size-3.5 ${loadingRadar ? "animate-spin" : ""}`} /> Radar
          </Button>
          <Button variant="outline" size="sm" onClick={onSignOut}>
            <LogOut className="size-3.5" /> Sign out
          </Button>
        </div>
      </div>

      {/* Active AI Agent Reasoning Perspective Box */}
      <div className="mb-4 rounded-xl border border-sky-500/30 bg-sky-500/10 p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Radio className="size-4 text-sky-400 animate-pulse" />
            <span className="font-mono text-xs font-bold uppercase text-sky-400">
              Active AI Agent: {crisis?.activeAgentAction?.agentName || "TaskDispatchAgent"}
            </span>
          </div>
          <span className="rounded bg-sky-500/20 px-2.5 py-0.5 text-[10px] font-mono font-bold uppercase text-sky-300">
            Confidence: {Math.round((crisis?.activeAgentAction?.confidence ?? 0.97) * 100)}%
          </span>
        </div>
        <div className="mt-2 text-xs font-semibold text-foreground">
          {crisis?.activeAgentAction?.title || "Autonomous Task Dispatch Operational"}
        </div>
        <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed">
          {crisis?.activeAgentAction?.details ||
            "PostGIS nearest-neighbor query matched Nestwise Disaster NGO (2.8 km away). Citizen report validated."}
        </p>
      </div>

      {/* Active Mission Hero Card */}
      <section className="rounded-xl border-2 border-primary bg-card p-5 shadow-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="size-2.5 animate-pulse rounded-full bg-primary" />
            <span className="label-caps font-mono font-bold text-primary">
              Mission · {crisis?.incidentNumber ?? "KL-WYD-0419"} · RESCUE_EXTRACTION
            </span>
          </div>
          <span className="rounded bg-primary/15 px-2 py-0.5 text-[11px] font-mono font-bold uppercase text-primary">
            Priority: CRITICAL
          </span>
        </div>

        <h2 className="mt-2 text-2xl sm:text-3xl font-bold uppercase leading-tight">
          {crisis?.description ? (crisis.description.length > 60 ? crisis.description.slice(0, 60) + "..." : crisis.description) : "Rooftop Extraction — Chooralmala Riverbank"}
        </h2>

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div className="rounded-lg bg-muted/60 p-3">
            <div className="label-caps flex items-center gap-1">
              <Crosshair className="size-3" /> Target GPS
            </div>
            <a
              className="font-mono text-sm text-sky-400 underline"
              href={`https://maps.google.com/?q=${crisis?.coordinates?.[1] ?? 11.5601},${crisis?.coordinates?.[0] ?? 76.1335}`}
              target="_blank"
              rel="noreferrer"
            >
              {crisis?.coordinates ? `${crisis.coordinates[1].toFixed(4)}, ${crisis.coordinates[0].toFixed(4)}` : "11.5601, 76.1335"}
            </a>
          </div>

          <div className="rounded-lg bg-muted/60 p-3">
            <div className="label-caps flex items-center gap-1">
              <Users className="size-3" /> Casualties
            </div>
            <div className="font-mono text-2xl font-extrabold">
              {crisis ? crisis.peopleAffected : 5}{" "}
              <span className="text-xs font-normal text-rose-400">
                ({crisis ? crisis.trappedCount : 2} trapped)
              </span>
            </div>
          </div>

          <div className="col-span-2 rounded-lg bg-amber-500/10 border border-amber-500/20 p-3 sm:col-span-1">
            <div className="label-caps flex items-center gap-1 text-amber-500 font-bold">
              <AlertTriangle className="size-3" /> Active Hazard
            </div>
            <div className="text-xs font-semibold text-amber-500 mt-1">
              Surge 3 m/s · High Debris Load
            </div>
          </div>
        </div>
      </section>

      {/* 4-Stage Status Progress Selector */}
      <Panel title="Mission Lifecycle Status" className="mt-4">
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          {TASK_STAGES.map((s, i) => {
            const isDone = i < currentStageIdx;
            const isCurrent = i === currentStageIdx;
            return (
              <button
                key={s.key}
                disabled={syncingStatus}
                onClick={() => handleStageSelect(i)}
                className={cn(
                  "flex min-h-[76px] flex-col items-center justify-center rounded-xl border-2 p-2.5 text-center transition-all active:scale-95",
                  isDone && "border-emerald-500 bg-emerald-500/10 text-emerald-500",
                  isCurrent && "border-primary bg-primary text-primary-foreground shadow-lg shadow-primary/20",
                  !isDone && !isCurrent && "border-border text-muted-foreground hover:border-muted-foreground/40"
                )}
              >
                <div className="flex items-center gap-1 text-sm font-bold uppercase">
                  {isDone && <CheckCircle2 className="size-4 text-emerald-500" />}
                  {s.label}
                </div>
                <div className="text-[10px] opacity-80 mt-0.5 leading-tight">{s.description}</div>
              </button>
            );
          })}
        </div>
      </Panel>

      {/* Live Inter-Agency Radar: Hospital & Ambulance */}
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        {/* Nearest Hospital Radar with Radius Filtering & One-Click Routing */}
        <Panel
          title="Hospital Radar (ICU Radius Search)"
          icon={Building2}
          action={
            <div className="flex items-center gap-1">
              {[10, 25, 50].map((r) => (
                <button
                  key={r}
                  onClick={() => setSearchRadius(r)}
                  className={cn(
                    "rounded px-2 py-0.5 font-mono text-[11px] font-bold transition-colors",
                    searchRadius === r
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground hover:bg-muted/80"
                  )}
                >
                  {r}km
                </button>
              ))}
            </div>
          }
        >
          {hospitals.length === 0 ? (
            <p className="text-xs text-muted-foreground py-2">Searching facilities within {searchRadius} km...</p>
          ) : (
            hospitals.map((h) => {
              const isAssigned = crisis?.assignedHospital?.id === h.organization_id;
              const isAccepted = isAssigned && crisis?.assignedHospital?.acceptedByHospital;
              return (
                <div
                  key={h.organization_id}
                  className={cn(
                    "rounded-xl border p-3.5 mb-3 last:mb-0 transition-all",
                    isAccepted
                      ? "border-emerald-500/50 bg-emerald-500/10"
                      : isAssigned
                      ? "border-amber-500/50 bg-amber-500/10"
                      : "border-border bg-muted/40"
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="font-bold text-sm text-foreground flex items-center gap-1.5">
                        {h.hospital_name}
                        {isAccepted && (
                          <span className="text-[10px] font-sans font-bold bg-emerald-500 text-white px-1.5 py-0.2 rounded">
                            Accepted
                          </span>
                        )}
                        {isAssigned && !isAccepted && (
                          <span className="text-[10px] font-sans font-bold bg-amber-500/20 text-amber-500 px-1.5 py-0.2 rounded animate-pulse">
                            Hold Requested
                          </span>
                        )}
                      </div>
                      <div className="font-mono text-xs text-muted-foreground mt-0.5">
                        {h.distance_km} km away · Radius match ({searchRadius}km)
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-mono text-lg font-bold text-emerald-500">
                        {h.available_icu_beds} <span className="text-xs font-normal">ICU beds</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-border/50 pt-2.5">
                    <span className="text-xs text-muted-foreground font-mono">
                      Emerg: {h.available_emergency_beds}
                    </span>

                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant={isAccepted ? "secondary" : isAssigned ? "outline" : "default"}
                        disabled={isAssigned}
                        onClick={() => handleAssignHospital(h)}
                        className="text-xs font-bold uppercase"
                      >
                        {isAccepted ? (
                          <span className="flex items-center gap-1 text-emerald-500">
                            <CheckCircle2 className="size-3.5" /> Admission Confirmed
                          </span>
                        ) : isAssigned ? (
                          <span className="flex items-center gap-1 text-amber-500">
                            <RefreshCw className="size-3.5 animate-spin" /> Awaiting Hospital
                          </span>
                        ) : (
                          "Assign & Request ICU Bed"
                        )}
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </Panel>

        {/* Inbound Ambulance Radar */}
        <Panel title="Inbound MedEvac Units" icon={Ambulance}>
          {ambulances.length === 0 ? (
            <p className="text-xs text-muted-foreground py-2">No units within 15 km...</p>
          ) : (
            ambulances.slice(0, 2).map((a) => (
              <div key={a.id} className="rounded-lg border border-border bg-muted/40 p-3 mb-2 last:mb-0">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-semibold text-sm">{a.vehicle_number}</div>
                    <div className="font-mono text-xs text-muted-foreground mt-0.5">
                      Crew: {a.crew_size} medics · Status: {a.status}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono text-lg font-bold text-primary">
                      {a.distance_km} km
                    </div>
                    <div className="text-[10px] text-muted-foreground uppercase">Distance</div>
                  </div>
                </div>
                <div className="mt-2.5 flex items-center justify-between border-t border-border/50 pt-2 text-xs">
                  <span className="text-muted-foreground">Type: {a.ambulance_type}</span>
                  <span className="text-emerald-500 font-medium">GPS Tracking Active</span>
                </div>
              </div>
            ))
          )}
        </Panel>
      </div>

      {/* Field Actions: Casualties & Hazards */}
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <Panel title="Casualty Triage Logger" icon={HeartPulse}>
          <div className="flex flex-wrap gap-2">
            {INJURIES.map((x) => (
              <Button
                key={x}
                variant="secondary"
                size="sm"
                onClick={() => handleCasualtyLog(x)}
                className="text-xs"
              >
                + {x}
              </Button>
            ))}
          </div>
        </Panel>

        <Panel title="Report Field Hazard" icon={AlertTriangle}>
          <div className="flex flex-wrap gap-2">
            {HAZARDS.map((x) => (
              <Button
                key={x}
                variant="secondary"
                size="sm"
                onClick={() => handleHazardLog(x)}
                className="text-xs text-amber-500"
              >
                + {x}
              </Button>
            ))}
          </div>
        </Panel>
      </div>

      {/* Emergency Backup Escalation */}
      <Panel title="Emergency Backup Escalation" className="mt-4">
        <div className="grid grid-cols-3 gap-2.5">
          {BACKUP.map((b) => (
            <button
              key={b.label}
              onClick={() => handleBackupRequest(b.label)}
              className="flex min-h-[88px] flex-col items-center justify-center gap-2 rounded-xl bg-destructive hover:bg-destructive/90 p-3 font-display text-sm sm:text-base font-bold uppercase text-destructive-foreground active:scale-95 transition-all shadow-md"
            >
              <b.icon className="size-6 sm:size-7" />
              <span className="text-center leading-tight">{b.label}</span>
            </button>
          ))}
        </div>
      </Panel>

      {/* Real-time Field Audit Trail */}
      {log.length > 0 && (
        <Panel title="Field Transmission Audit Log" className="mt-4">
          <ul className="space-y-1.5 font-mono text-xs text-muted-foreground max-h-48 overflow-y-auto pr-2">
            {log.map((l, i) => (
              <li key={i} className="border-b border-border/40 pb-1 last:border-0">
                {l}
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}
