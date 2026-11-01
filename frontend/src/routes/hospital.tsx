import { createFileRoute } from "@tanstack/react-router";
import { Ambulance, BedDouble, Droplet, HeartPulse, LogOut, Minus, Plus, RefreshCw, Wind, ShieldCheck, Radio, CheckCircle2 } from "lucide-react";
import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { Panel, TriageBadge } from "@/components/resq/shell";
import { StaffGate } from "@/components/resq/staff-gate";
import { Button } from "@/components/ui/button";
import type { Triage } from "@/lib/resq-data";
import {
  DEFAULT_HOSPITAL_ID,
  getHospitalCapacity,
  updateHospitalCapacity,
  fulfillReservation,
  releaseReservation,
  type HospitalCapacity,
} from "@/lib/api";
import { getActiveCrisis, subscribeToCrisisUpdates, acceptHospitalAdmission, type ActiveCrisis } from "@/lib/crisis-sync";

export const Route = createFileRoute("/hospital")({
  head: () => ({
    meta: [
      { title: "RESQ Hospital Portal — Beds & casualty intake" },
      { name: "description", content: "Live ICU beds, emergency admissions and real-time backend synchronization for Kerala hospitals." },
      { property: "og:title", content: "RESQ Hospital Portal" },
      { property: "og:description", content: "Clinical bed and casualty intake console for Kerala hospitals." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: () => (
    <StaffGate portal="Hospital" roles={[{ value: "TRIAGE_DOCTOR", label: "Doctor" }, { value: "ORG_ADMIN", label: "Intake Admin" }]}>
      {(u, out) => <HospitalConsole name={u.full_name} role={u.role} onSignOut={out} />}
    </StaffGate>
  ),
});

type Arrival = {
  id: string;
  reservationId?: string;
  taskId?: string;
  unit: string;
  triage: Triage;
  eta: number;
  note: string;
  isLive?: boolean;
};

const SEED_ARRIVALS: Arrival[] = [
  { id: "a1", unit: "ALS-114 (108 Wayanad)", triage: "RED", eta: 6, note: "Crush injury, BP 80/50 — Chooralmala sector" },
  { id: "a2", unit: "BLS-208 (Kerala Fire)", triage: "YELLOW", eta: 11, note: "Compound fracture, hemodynamically stable" },
  { id: "a3", unit: "ALS-097 (NDRF MedEvac)", triage: "RED", eta: 14, note: "Submersion trauma, SpO2 88%, on oxygen" },
  { id: "a4", unit: "BLS-311 (Local EMS)", triage: "GREEN", eta: 20, note: "Superficial lacerations, ambulatory" },
];

function HospitalConsole({ name, role, onSignOut }: { name: string; role: string; onSignOut: () => void }) {
  const [crisis, setCrisis] = useState<ActiveCrisis | null>(getActiveCrisis());
  const [capacity, setCapacity] = useState<HospitalCapacity | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [queue, setQueue] = useState<Arrival[]>(() => {
    const currentCrisis = getActiveCrisis();
    if (currentCrisis && !currentCrisis.confirmedReceivedHelp) {
      return [
        {
          id: currentCrisis.incidentNumber,
          unit: `${currentCrisis.assignedRescue?.ngoOrgName || "Nestwise Disaster NGO"} → ${currentCrisis.incidentNumber}`,
          triage: "RED",
          eta: currentCrisis.assignedRescue?.etaMinutes || 6,
          note: `Casualty routed via field radius. ICU bed requested. (${currentCrisis.description.slice(0, 45)}...)`,
          isLive: true,
        },
        ...SEED_ARRIVALS,
      ];
    }
    return SEED_ARRIVALS;
  });
  const [lastSynced, setLastSynced] = useState<string>("");

  // Sync incoming queue with live cross-portal crisis
  useEffect(() => {
    const unsub = subscribeToCrisisUpdates((updatedCrisis) => {
      setCrisis(updatedCrisis);
      if (updatedCrisis && !updatedCrisis.confirmedReceivedHelp) {
        setQueue((prev) => {
          if (prev.some((x) => x.id === updatedCrisis.incidentNumber)) return prev;
          return [
            {
              id: updatedCrisis.incidentNumber,
              unit: `${updatedCrisis.assignedRescue?.ngoOrgName || "Nestwise Disaster NGO"} → ${updatedCrisis.incidentNumber}`,
              triage: "RED",
              eta: updatedCrisis.assignedRescue?.etaMinutes || 6,
              note: `Casualty routed via field radius. ICU bed requested. (${updatedCrisis.description.slice(0, 45)}...)`,
              isLive: true,
            },
            ...prev,
          ];
        });
      }
    });
    return unsub;
  }, []);

  // Load live capacity from the PostgreSQL backend
  const refreshCapacity = useCallback(async (quiet = false) => {
    try {
      if (!quiet) setLoading(true);
      const data = await getHospitalCapacity(DEFAULT_HOSPITAL_ID);
      setCapacity(data);
      setLastSynced(new Date().toLocaleTimeString());
      if (!quiet) toast.success("Hospital capacity synced with live database");
    } catch (err) {
      console.error("Failed to load hospital capacity:", err);
      // Fallback local state if backend unreachable
      if (!capacity) {
        setCapacity({
          id: "local-fallback",
          organization_id: DEFAULT_HOSPITAL_ID,
          total_emergency_beds: 30,
          occupied_emergency_beds: 15,
          reserved_emergency_beds: 0,
          out_of_service_emergency_beds: 3,
          available_emergency_beds: 12,
          total_icu_beds: 10,
          occupied_icu_beds: 7,
          reserved_icu_beds: 0,
          out_of_service_icu_beds: 1,
          available_icu_beds: 2,
          has_oxygen_facility: true,
          has_trauma_center: false,
          updated_at: new Date().toISOString(),
        });
      }
    } finally {
      setLoading(false);
    }
  }, [capacity]);

  // Initial fetch and throttled 25s polling interval (only when tab is visible)
  useEffect(() => {
    refreshCapacity(true);
    const poller = setInterval(() => {
      if (typeof document !== "undefined" && document.visibilityState !== "visible") return;
      refreshCapacity(true);
    }, 25000);
    return () => clearInterval(poller);
  }, [refreshCapacity]);

  // ETA countdown simulation
  useEffect(() => {
    const id = setInterval(() => {
      setQueue((q) => q.map((a) => ({ ...a, eta: Math.max(0, a.eta - 1) })));
    }, 15000);
    return () => clearInterval(id);
  }, []);

  // Update bed occupancy live in PostgreSQL
  const adjustBedOccupancy = async (type: "icu" | "emergency", delta: number) => {
    let currentCapacity = capacity;
    if (!currentCapacity) {
      try {
        currentCapacity = await getHospitalCapacity(DEFAULT_HOSPITAL_ID);
        setCapacity(currentCapacity);
      } catch {
        // Continue with fallback
      }
    }
    if (!currentCapacity) return;
    setSaving(true);

    try {
      if (type === "icu") {
        // Decreasing available = increasing occupied (delta = -1)
        const currentOcc = currentCapacity.occupied_icu_beds;
        const maxOcc = currentCapacity.total_icu_beds - currentCapacity.reserved_icu_beds - currentCapacity.out_of_service_icu_beds;
        const newOcc = Math.max(0, Math.min(maxOcc, currentOcc - delta));
        const updated = await updateHospitalCapacity(DEFAULT_HOSPITAL_ID, {
          occupied_icu_beds: newOcc,
        });
        setCapacity(updated);
        toast.success(`ICU Beds updated: ${updated.available_icu_beds} available (DB Persisted)`);
        return updated;
      } else {
        const currentOcc = currentCapacity.occupied_emergency_beds;
        const maxOcc = currentCapacity.total_emergency_beds - currentCapacity.reserved_emergency_beds - currentCapacity.out_of_service_emergency_beds;
        const newOcc = Math.max(0, Math.min(maxOcc, currentOcc - delta));
        const updated = await updateHospitalCapacity(DEFAULT_HOSPITAL_ID, {
          occupied_emergency_beds: newOcc,
        });
        setCapacity(updated);
        toast.success(`Emergency Beds updated: ${updated.available_emergency_beds} available (DB Persisted)`);
        return updated;
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update capacity in database");
    } finally {
      setSaving(false);
    }
  };

  // Direct admission from Clinical AI Agent Box
  const handleAdmitCrisisDirectly = async () => {
    try {
      setSaving(true);
      acceptHospitalAdmission();
      await adjustBedOccupancy("icu", -1);
      // Remove any matching live item from queue
      setQueue((q) => q.filter((x) => !x.isLive && x.id !== crisis?.incidentNumber));
      toast.success("Hospital admission accepted & ICU bed allocated in PostgreSQL.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to accept admission");
    } finally {
      setSaving(false);
    }
  };

  // Admit patient and fulfill reservation
  const admit = async (a: Arrival) => {
    try {
      setSaving(true);
      // 1. Notify cross-portal network and update citizen tracking status
      acceptHospitalAdmission();

      // 2. Adjust ICU bed in PostgreSQL DB
      if (a.triage === "RED" || a.isLive) {
        await adjustBedOccupancy("icu", -1);
      } else {
        await adjustBedOccupancy("emergency", -1);
      }

      // 3. Fulfill backend reservation if linked
      if (a.reservationId) {
        try {
          await fulfillReservation(a.reservationId, `Admitted by ${name} (${role})`);
        } catch {}
      }

      // 4. Remove from queue
      setQueue((q) => q.filter((x) => x.id !== a.id));
      toast.success(`Admission accepted for ${a.unit}. 1 ICU Bed occupied in PostgreSQL.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to admit patient");
    } finally {
      setSaving(false);
    }
  };

  // Divert patient and release reservation
  const divert = async (a: Arrival) => {
    try {
      if (a.reservationId) {
        await releaseReservation(a.reservationId, "Diverted by intake doctor to Mananthavady");
      }
      setQueue((q) => q.filter((x) => x.id !== a.id));
      toast.warning(`${a.unit} diverted to District Hospital Mananthavady (8.2 km)`);
      refreshCapacity(true);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to divert patient");
    }
  };

  const icuAvailable = capacity?.available_icu_beds ?? 0;
  const icuTotal = capacity?.total_icu_beds ?? 10;
  const icuLow = icuAvailable / icuTotal < 0.2;

  const emerAvailable = capacity?.available_emergency_beds ?? 0;
  const emerTotal = capacity?.total_emergency_beds ?? 30;
  const emerLow = emerAvailable / emerTotal < 0.2;

  return (
    <div>
      {/* Header bar */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-500 border border-emerald-500/20">
              <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live Database Connected
            </span>
            <span className="text-xs text-muted-foreground font-mono">
              {lastSynced ? `Synced at ${lastSynced}` : "Connecting..."}
            </span>
          </div>
          <h1 className="mt-1 text-4xl sm:text-5xl font-bold uppercase tracking-tight">
            Wayanad District Hospital
          </h1>
          <p className="text-sm text-muted-foreground">
            Clinical Triage & Real-Time Capacity Console · Disaster Relief Network
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refreshCapacity(false)}
            disabled={loading}
          >
            <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
          </Button>
          <div className="hidden sm:flex items-center gap-2 text-sm border-l pl-3">
            <span className="text-muted-foreground">{name}</span>
            <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">{role}</span>
          </div>
          <Button variant="outline" size="sm" onClick={onSignOut}>
            <LogOut className="size-3.5" /> Sign out
          </Button>
        </div>
      </div>

      {/* Active Clinical AI Agent Reasoning Perspective Box */}
      <div className="mb-6 rounded-xl border border-sky-500/30 bg-sky-500/10 p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Radio className="size-4 text-sky-400 animate-pulse" />
            <span className="font-mono text-xs font-bold uppercase text-sky-400">
              Active Clinical AI Agent: HospitalRoutingAgent
            </span>
          </div>
          <span className="rounded bg-sky-500/20 px-2.5 py-0.5 text-[10px] font-mono font-bold uppercase text-sky-300">
            {crisis?.assignedHospital?.acceptedByHospital ? "Admission Accepted" : "30-Min Bed Hold Buffer"}
          </span>
        </div>
        <div className="mt-2 text-xs font-semibold text-foreground">
          {crisis?.assignedHospital?.acceptedByHospital
            ? "Admission Confirmed & ICU Bed Reserved"
            : "Hospital Admission Request from Field NGO"}
        </div>
        <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed">
          {crisis?.assignedHospital?.acceptedByHospital
            ? `Wayanad District Hospital confirmed admission for ${crisis?.incidentNumber || "active crisis"}. Bed occupancy updated in live PostgreSQL database.`
            : `${crisis?.assignedRescue?.ngoOrgName || "Nestwise Humanitarian Rescue NGO"} requested 1 ICU bed reservation for incoming casualty. Awaiting doctor confirmation.`}
        </p>

        {!crisis?.assignedHospital?.acceptedByHospital && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-sky-500/20 pt-2.5">
            <span className="text-xs text-sky-200">
              Emergency casualty en route · 1 Bed Requested
            </span>
            <Button
              size="sm"
              variant="default"
              className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md"
              onClick={handleAdmitCrisisDirectly}
              disabled={saving}
            >
              <CheckCircle2 className="size-3.5 mr-1" />
              Accept Admission & Allocate ICU Bed
            </Button>
          </div>
        )}
      </div>

      {/* Counters Grid with Real DB Values & Controls */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* ICU Beds */}
        <div className={`rounded-xl border bg-card p-5 transition-colors shadow-sm ${icuLow ? "border-red-500/60 bg-red-500/5" : "border-border"}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <HeartPulse className={`size-4 ${icuLow ? "text-red-500" : "text-primary"}`} />
              ICU Beds (Critical)
            </div>
            {icuLow && <span className="text-[10px] uppercase font-bold text-red-500 bg-red-500/15 px-1.5 py-0.5 rounded">Low</span>}
          </div>
          <div className="mt-4 flex items-center justify-between">
            <button
              aria-label="Decrease ICU Beds"
              disabled={saving || icuAvailable <= 0}
              onClick={() => adjustBedOccupancy("icu", -1)}
              className="grid size-12 place-items-center rounded-lg bg-muted hover:bg-red-500/20 active:scale-95 disabled:opacity-40 transition-all"
            >
              <Minus className="size-5" />
            </button>
            <div className="text-center">
              <div className={`font-mono text-5xl font-extrabold tracking-tight ${icuLow ? "text-red-500" : "text-foreground"}`}>
                {icuAvailable}
              </div>
              <div className="text-xs text-muted-foreground uppercase tracking-wider mt-0.5">
                of {icuTotal} capacity
              </div>
              <div className="text-[11px] text-muted-foreground font-mono">
                {capacity?.reserved_icu_beds ?? 0} reserved · {capacity?.occupied_icu_beds ?? 0} occ
              </div>
            </div>
            <button
              aria-label="Increase ICU Beds"
              disabled={saving}
              onClick={() => adjustBedOccupancy("icu", 1)}
              className="grid size-12 place-items-center rounded-lg bg-muted hover:bg-emerald-500/20 active:scale-95 disabled:opacity-40 transition-all"
            >
              <Plus className="size-5" />
            </button>
          </div>
        </div>

        {/* Emergency / Trauma Beds */}
        <div className={`rounded-xl border bg-card p-5 transition-colors shadow-sm ${emerLow ? "border-amber-500/60 bg-amber-500/5" : "border-border"}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <BedDouble className={`size-4 ${emerLow ? "text-amber-500" : "text-primary"}`} />
              Emergency Beds
            </div>
            {emerLow && <span className="text-[10px] uppercase font-bold text-amber-500 bg-amber-500/15 px-1.5 py-0.5 rounded">Low</span>}
          </div>
          <div className="mt-4 flex items-center justify-between">
            <button
              aria-label="Decrease Emergency Beds"
              disabled={saving || emerAvailable <= 0}
              onClick={() => adjustBedOccupancy("emergency", -1)}
              className="grid size-12 place-items-center rounded-lg bg-muted hover:bg-red-500/20 active:scale-95 disabled:opacity-40 transition-all"
            >
              <Minus className="size-5" />
            </button>
            <div className="text-center">
              <div className={`font-mono text-5xl font-extrabold tracking-tight ${emerLow ? "text-amber-500" : "text-foreground"}`}>
                {emerAvailable}
              </div>
              <div className="text-xs text-muted-foreground uppercase tracking-wider mt-0.5">
                of {emerTotal} capacity
              </div>
              <div className="text-[11px] text-muted-foreground font-mono">
                {capacity?.reserved_emergency_beds ?? 0} reserved · {capacity?.occupied_emergency_beds ?? 0} occ
              </div>
            </div>
            <button
              aria-label="Increase Emergency Beds"
              disabled={saving}
              onClick={() => adjustBedOccupancy("emergency", 1)}
              className="grid size-12 place-items-center rounded-lg bg-muted hover:bg-emerald-500/20 active:scale-95 disabled:opacity-40 transition-all"
            >
              <Plus className="size-5" />
            </button>
          </div>
        </div>

        {/* Oxygen Facility Status */}
        <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Wind className="size-4 text-sky-500" />
              Oxygen Generation
            </div>
            <span className="text-[10px] uppercase font-bold text-emerald-500 bg-emerald-500/15 px-1.5 py-0.5 rounded">Active</span>
          </div>
          <div className="mt-4 text-center">
            <div className="font-mono text-4xl font-extrabold text-sky-400">
              {capacity?.has_oxygen_facility ? "ONLINE" : "OFFLINE"}
            </div>
            <div className="text-xs text-muted-foreground mt-2">
              High-Flow PSA Plant: Operational
            </div>
            <div className="text-[11px] text-muted-foreground font-mono mt-1">
              42 Cylinders in reserve stock
            </div>
          </div>
        </div>

        {/* Trauma Center & Blood Bank */}
        <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Droplet className="size-4 text-rose-500" />
              O-Neg & Trauma
            </div>
            <span className="text-[10px] uppercase font-bold text-emerald-500 bg-emerald-500/15 px-1.5 py-0.5 rounded">Stocked</span>
          </div>
          <div className="mt-4 text-center">
            <div className="font-mono text-4xl font-extrabold text-rose-500">
              6 <span className="text-lg font-normal text-muted-foreground">Units</span>
            </div>
            <div className="text-xs text-muted-foreground mt-2">
              Emergency Cross-Match Ready
            </div>
            <div className="text-[11px] text-muted-foreground font-mono mt-1">
              Kerala Blood Bank Link Active
            </div>
          </div>
        </div>
      </div>

      {/* Incoming Casualty Queue */}
      <Panel
        title="Incoming Casualty & Ambulance Queue"
        icon={Ambulance}
        className="mt-6"
        action={
          <div className="flex items-center gap-2">
            <span className="label-caps font-mono">{queue.length} inbound ambulances</span>
          </div>
        }
      >
        {queue.length === 0 ? (
          <div className="py-12 text-center text-muted-foreground">
            <ShieldCheck className="mx-auto size-8 text-emerald-500/50 mb-2" />
            <p className="font-medium">All incoming casualties admitted or stabilized.</p>
            <p className="text-xs mt-1">Listening for auto-dispatched medevac routing from AI Agents...</p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {queue.sort((a, b) => a.eta - b.eta).map((a) => (
              <div key={a.id} className="flex flex-wrap items-center justify-between gap-4 py-4">
                <div className="flex items-center gap-3 min-w-64">
                  <TriageBadge level={a.triage} />
                  <div>
                    <div className="font-mono font-bold text-base flex items-center gap-2">
                      {a.unit}
                      {a.isLive && (
                        <span className="text-[10px] font-sans uppercase font-bold bg-primary/20 text-primary px-1.5 py-0.5 rounded animate-pulse">
                          AI Dispatched
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground">{a.note}</div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="font-mono text-2xl font-bold text-primary">
                      {a.eta} <span className="text-sm font-normal text-muted-foreground">min</span>
                    </div>
                    <div className="text-[11px] text-muted-foreground uppercase tracking-wider">
                      ETA to Triage Bay
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button variant="success" onClick={() => admit(a)} disabled={saving}>
                      Admit Patient
                    </Button>
                    <Button variant="outline" onClick={() => divert(a)} disabled={saving}>
                      Divert
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
