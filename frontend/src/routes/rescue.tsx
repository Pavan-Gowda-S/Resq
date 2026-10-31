import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle, Anchor, Check, Crosshair, HeartPulse, LogOut, Plane, Stethoscope, Users } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Panel } from "@/components/resq/shell";
import { StaffGate } from "@/components/resq/staff-gate";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/rescue")({
  head: () => ({
    meta: [
      { title: "RESQ Field Responder — Active dispatch" },
      { name: "description", content: "Rugged field console for Kerala rescue teams: dispatch, status, casualties and backup." },
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

const STATUSES = ["En Route", "On Scene", "Extraction in Progress", "Target Rescued"];
const INJURIES = ["Cardiac", "Compound Fracture", "Hypothermia", "Head Trauma", "Drowning"];
const HAZARDS = ["Power Line Down", "Flash Flood Surge", "Unstable Slope", "Road Washed Out"];
const BACKUP = [
  { label: "Air Evacuation", icon: Plane },
  { label: "Boats", icon: Anchor },
  { label: "Trauma Medics", icon: Stethoscope },
];

function FieldConsole({ name, onSignOut }: { name: string; onSignOut: () => void }) {
  const [status, setStatus] = useState(0);
  const [log, setLog] = useState<string[]>([]);
  const add = (s: string) => {
    setLog((l) => [`${new Date().toLocaleTimeString("en-GB")} · ${s}`, ...l]);
    toast.success(s);
  };

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-4 flex items-center justify-between">
        <div><div className="label-caps">SDRF-WR-02 · {name}</div><h1 className="text-4xl font-bold uppercase">Field Ops</h1></div>
        <Button variant="outline" size="sm" onClick={onSignOut}><LogOut /> Sign out</Button>
      </div>

      <section className="rounded-lg border-2 border-primary bg-card p-5">
        <div className="flex items-center gap-2"><span className="size-2 animate-blink rounded-full bg-primary" /><span className="label-caps">Active task · KL-WYD-0419</span></div>
        <h2 className="mt-2 text-3xl font-bold uppercase">Rooftop extraction — Chooralmala</h2>
        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3">
          <div className="rounded bg-surface p-3"><div className="label-caps flex items-center gap-1"><Crosshair className="size-3" />GPS</div><a className="font-mono text-sm text-info underline" href="https://maps.google.com/?q=11.5601,76.1335" target="_blank" rel="noreferrer">11.5601, 76.1335</a></div>
          <div className="rounded bg-surface p-3"><div className="label-caps flex items-center gap-1"><Users className="size-3" />Victims</div><div className="font-mono text-2xl font-bold">5 <span className="text-sm text-primary">(2 trapped)</span></div></div>
          <div className="col-span-2 rounded bg-warning/15 p-3 md:col-span-1"><div className="label-caps flex items-center gap-1"><AlertTriangle className="size-3" />Hazard</div><div className="text-sm font-medium text-warning">Fast current 3 m/s · debris</div></div>
        </div>
      </section>

      <Panel title="Status" className="mt-4">
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          {STATUSES.map((s, i) => (
            <button
              key={s}
              onClick={() => { setStatus(i); add(`Status → ${s}`); }}
              className={cn("flex min-h-20 flex-col items-center justify-center gap-1 rounded-lg border-2 px-2 text-center font-display text-lg font-bold uppercase leading-tight",
                i < status ? "border-success bg-success/15 text-success" : i === status ? "border-primary bg-primary text-primary-foreground" : "border-border text-muted-foreground")}
            >
              {i < status && <Check className="size-5" />}{s}
            </button>
          ))}
        </div>
      </Panel>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Panel title="Casualty logger" icon={HeartPulse}>
          <div className="flex flex-wrap gap-2">{INJURIES.map((x) => <Button key={x} variant="secondary" onClick={() => add(`Casualty: ${x}`)}>{x}</Button>)}</div>
        </Panel>
        <Panel title="New hazard" icon={AlertTriangle}>
          <div className="flex flex-wrap gap-2">{HAZARDS.map((x) => <Button key={x} variant="secondary" onClick={() => add(`Hazard: ${x}`)}>{x}</Button>)}</div>
        </Panel>
      </div>

      <Panel title="Request backup" className="mt-4">
        <div className="grid grid-cols-3 gap-2">
          {BACKUP.map((b) => (
            <button key={b.label} onClick={() => add(`BACKUP REQUESTED: ${b.label}`)} className="flex min-h-24 flex-col items-center justify-center gap-2 rounded-lg bg-primary font-display text-lg font-bold uppercase text-primary-foreground active:scale-95">
              <b.icon className="size-7" />{b.label}
            </button>
          ))}
        </div>
      </Panel>

      {log.length > 0 && (
        <Panel title="Sync log" className="mt-4">
          <ul className="space-y-1 font-mono text-xs text-muted-foreground">{log.map((l, i) => <li key={i}>{l}</li>)}</ul>
        </Panel>
      )}
    </div>
  );
}
