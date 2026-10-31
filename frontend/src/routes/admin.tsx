import { createFileRoute } from "@tanstack/react-router";
import { BadgeCheck, Database, Fingerprint, LogOut, Plus, Server, Truck } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Panel, useBackendHealth } from "@/components/resq/shell";
import { StaffGate } from "@/components/resq/staff-gate";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { API_DISPLAY_BASE } from "@/lib/api";
import { UNITS } from "@/lib/resq-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/admin")({
  head: () => ({
    meta: [
      { title: "RESQ System Administration" },
      { name: "description", content: "Fleet onboarding, audit ledger verification and system telemetry for RESQ." },
      { property: "og:title", content: "RESQ System Administration" },
      { property: "og:description", content: "Fleet, audit ledger and telemetry for RESQ." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: () => (
    <StaffGate portal="Admin" roles={[{ value: "SUPERADMIN", label: "Superadmin" }]}>
      {(u, out) => <AdminConsole name={u.full_name} onSignOut={out} />}
    </StaffGate>
  ),
});

const AGENCIES = ["NDRF", "SDRF", "Fire Force", "Volunteer"];

const LEDGER = [
  { id: "KL-WYD-0412", claim: "Rescued 4 · 14:02", citizen: "Confirmed 4 · 14:05", hash: "a91f…7c2e", ok: true },
  { id: "KL-ALP-0388", claim: "Rescued 2 · 13:40", citizen: "Confirmed 2 · 13:44", hash: "3be0…d118", ok: true },
  { id: "KL-IDK-0301", claim: "Rescued 6 · 12:15", citizen: "Confirmed 5 · 12:30", hash: "ff42…09ab", ok: false },
  { id: "KL-WYD-0399", claim: "Rescued 3 · 11:52", citizen: "Confirmed 3 · 11:58", hash: "7d1c…e4f0", ok: true },
];

function AdminConsole({ name, onSignOut }: { name: string; onSignOut: () => void }) {
  const health = useBackendHealth(10000);
  const [fleet, setFleet] = useState(UNITS.map((u, i) => ({ ...u, agency: AGENCIES[i % 4], verified: i !== 5 })));
  const [newName, setNewName] = useState("");
  const [agency, setAgency] = useState("SDRF");
  const [sim, setSim] = useState(true);

  const onboard = () => {
    if (!newName.trim()) return;
    setFleet((f) => [...f, { id: `NEW-${f.length + 1}`, name: newName, type: "Rescue", officer: "—", district: "Unassigned", agency, verified: false }]);
    setNewName("");
    toast.success("Unit onboarded — pending verification");
  };

  return (
    <div>
      <div className="mb-6 flex items-end justify-between">
        <div><div className="label-caps">{name}</div><h1 className="text-5xl font-bold uppercase">System Admin</h1></div>
        <Button variant="outline" size="sm" onClick={onSignOut}><LogOut /> Sign out</Button>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <Panel title="Fleet & responders" icon={Truck}>
          <div className="mb-4 flex flex-wrap gap-2">
            <Input placeholder="Unit name, e.g. SDRF Boat Unit 07" value={newName} onChange={(e) => setNewName(e.target.value)} className="min-w-56 flex-1" />
            <select value={agency} onChange={(e) => setAgency(e.target.value)} className="rounded border border-input bg-background px-2 text-sm">
              {AGENCIES.map((a) => <option key={a}>{a}</option>)}
            </select>
            <Button onClick={onboard}><Plus /> Onboard</Button>
          </div>
          <div className="divide-y divide-border">
            {fleet.map((u) => (
              <div key={u.id} className="flex flex-wrap items-center gap-3 py-2.5 text-sm">
                <span className="w-24 font-mono text-xs text-muted-foreground">{u.id}</span>
                <span className="flex-1 font-medium">{u.name}</span>
                <span className="rounded bg-muted px-2 py-0.5 text-xs">{u.agency}</span>
                <span className="w-28 text-muted-foreground">{u.district}</span>
                {u.verified ? (
                  <span className="flex items-center gap-1 text-success"><BadgeCheck className="size-4" />Verified</span>
                ) : (
                  <Button size="sm" variant="secondary" onClick={() => setFleet((f) => f.map((x) => (x.id === u.id ? { ...x, verified: true } : x)))}>Verify</Button>
                )}
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="System telemetry" icon={Server}>
          <div className="grid gap-4 text-sm">
            <div className="flex items-center justify-between rounded bg-surface p-3">
              <div>
                <div className="font-medium">Autonomous agent simulation</div>
                <div className="text-xs text-muted-foreground">{sim ? "Agents propose; dispatch simulated" : "Live dispatch to field units"}</div>
              </div>
              <Switch checked={!sim} onCheckedChange={(v) => { setSim(!v); toast(v ? "Live dispatch enabled" : "Simulation mode"); }} />
            </div>
            <div className="rounded bg-surface p-3">
              <div className="label-caps">Cloudflare tunnel</div>
              <div className="mt-1 break-all font-mono text-xs">{API_DISPLAY_BASE}</div>
              <div className="mt-2 flex items-center gap-2">
                <span className={cn("size-2.5 rounded-full", health.ok ? "bg-success" : health.ok === false ? "bg-primary" : "bg-muted-foreground")} />
                <span className="font-mono">{health.ok === null ? "Checking…" : health.ok ? `Healthy · ${health.ms} ms` : "Unreachable"}</span>
              </div>
            </div>
            <div className="rounded bg-surface p-3">
              <div className="label-caps flex items-center gap-1"><Database className="size-3" />Database sync</div>
              <div className="mt-2 grid grid-cols-3 gap-2 text-center font-mono">
                <div><div className="text-2xl font-bold">0</div><div className="text-[10px] text-muted-foreground">PENDING</div></div>
                <div><div className="text-2xl font-bold text-success">1,284</div><div className="text-[10px] text-muted-foreground">RECONCILED</div></div>
                <div><div className="text-2xl font-bold text-warning">1</div><div className="text-[10px] text-muted-foreground">CONFLICTS</div></div>
              </div>
            </div>
          </div>
        </Panel>
      </div>

      <Panel title="Audit ledger · claim vs citizen confirmation" icon={Fingerprint} className="mt-4">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="label-caps text-left"><th className="py-2">Incident</th><th>Responder claim</th><th>Citizen confirmation</th><th>SHA-256</th><th>Status</th></tr></thead>
            <tbody className="divide-y divide-border">
              {LEDGER.map((l) => (
                <tr key={l.id}>
                  <td className="py-2.5 font-mono">{l.id}</td><td>{l.claim}</td><td>{l.citizen}</td>
                  <td className="font-mono text-xs text-muted-foreground">{l.hash}</td>
                  <td>{l.ok ? <span className="text-success">✓ Match</span> : <span className="font-bold text-primary">⚠ Discrepancy</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
