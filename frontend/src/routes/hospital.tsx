import { createFileRoute } from "@tanstack/react-router";
import { Ambulance, BedDouble, Droplet, HeartPulse, LogOut, Minus, Plus, Wind } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Panel, TriageBadge } from "@/components/resq/shell";
import { StaffGate } from "@/components/resq/staff-gate";
import { Button } from "@/components/ui/button";
import type { Triage } from "@/lib/resq-data";

export const Route = createFileRoute("/hospital")({
  head: () => ({
    meta: [
      { title: "RESQ Hospital Portal — Beds & casualty intake" },
      { name: "description", content: "Update ICU beds, oxygen and blood stock in seconds and admit incoming casualties." },
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

const COUNTERS = [
  { key: "icu", label: "ICU Beds", icon: HeartPulse, total: 24 },
  { key: "gen", label: "General Beds", icon: BedDouble, total: 180 },
  { key: "o2", label: "Oxygen Cylinders", icon: Wind, total: 60 },
  { key: "oneg", label: "O-Neg Blood Units", icon: Droplet, total: 20 },
] as const;

type Arrival = { id: string; unit: string; triage: Triage; eta: number; note: string };

const SEED: Arrival[] = [
  { id: "a1", unit: "ALS-114", triage: "RED", eta: 6, note: "Crush injury, BP 80/50 — Mundakkai" },
  { id: "a2", unit: "BLS-208", triage: "YELLOW", eta: 12, note: "Compound fracture, stable" },
  { id: "a3", unit: "ALS-097", triage: "RED", eta: 15, note: "Near-drowning, intubated" },
  { id: "a4", unit: "BLS-311", triage: "GREEN", eta: 22, note: "Lacerations, ambulatory" },
];

function HospitalConsole({ name, role, onSignOut }: { name: string; role: string; onSignOut: () => void }) {
  const [counts, setCounts] = useState<Record<string, number>>({ icu: 3, gen: 41, o2: 18, oneg: 4 });
  const [queue, setQueue] = useState(SEED);

  useEffect(() => {
    const id = setInterval(() => setQueue((q) => q.map((a) => ({ ...a, eta: Math.max(0, a.eta - 1) }))), 15000);
    return () => clearInterval(id);
  }, []);

  const bump = (k: string, d: number, max: number) => setCounts((c) => ({ ...c, [k]: Math.min(max, Math.max(0, (c[k] ?? 0) + d)) }));

  const admit = (a: Arrival) => {
    setQueue((q) => q.filter((x) => x.id !== a.id));
    if (a.triage === "RED") bump("icu", -1, 24); else bump("gen", -1, 180);
    toast.success(`${a.unit} patient admitted`);
  };
  const divert = (a: Arrival) => {
    setQueue((q) => q.filter((x) => x.id !== a.id));
    toast.warning(`${a.unit} diverted to District Hospital Mananthavady (8.2 km)`);
  };

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="label-caps">Govt Medical College · Kozhikode</div>
          <h1 className="text-5xl font-bold uppercase">Clinical Capacity</h1>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-muted-foreground">{name} · <span className="font-mono">{role}</span></span>
          <Button variant="outline" size="sm" onClick={onSignOut}><LogOut /> Sign out</Button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {COUNTERS.map((c) => {
          const v = counts[c.key] ?? 0;
          const low = v / c.total < 0.15;
          return (
            <div key={c.key} className={`rounded-lg border bg-card p-4 ${low ? "border-primary" : "border-border"}`}>
              <div className="flex items-center gap-2 text-sm font-medium"><c.icon className={`size-4 ${low ? "text-primary" : "text-muted-foreground"}`} />{c.label}</div>
              <div className="mt-3 flex items-center justify-between">
                <button aria-label={`Decrease ${c.label}`} onClick={() => bump(c.key, -1, c.total)} className="grid size-14 place-items-center rounded-lg bg-muted active:bg-primary"><Minus /></button>
                <div className="text-center">
                  <div className={`font-mono text-5xl font-bold ${low ? "text-primary" : ""}`}>{v}</div>
                  <div className="label-caps">of {c.total}</div>
                </div>
                <button aria-label={`Increase ${c.label}`} onClick={() => bump(c.key, 1, c.total)} className="grid size-14 place-items-center rounded-lg bg-muted active:bg-success"><Plus /></button>
              </div>
            </div>
          );
        })}
      </div>

      <Panel title="Incoming casualty queue" icon={Ambulance} className="mt-6" action={<span className="label-caps">{queue.length} inbound</span>}>
        {queue.length === 0 ? (
          <p className="py-6 text-center text-muted-foreground">No inbound ambulances.</p>
        ) : (
          <div className="divide-y divide-border">
            {queue.sort((a, b) => a.eta - b.eta).map((a) => (
              <div key={a.id} className="flex flex-wrap items-center gap-4 py-3">
                <TriageBadge level={a.triage} />
                <div className="min-w-48 flex-1">
                  <div className="font-mono font-semibold">{a.unit}</div>
                  <div className="text-sm text-muted-foreground">{a.note}</div>
                </div>
                <div className="font-mono text-2xl font-bold">{a.eta}<span className="text-sm"> min</span></div>
                <div className="flex gap-2">
                  <Button variant="success" onClick={() => admit(a)}>Admit Patient</Button>
                  <Button variant="outline" onClick={() => divert(a)}>Divert</Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
