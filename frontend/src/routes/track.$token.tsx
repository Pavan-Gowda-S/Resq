import { createFileRoute } from "@tanstack/react-router";
import { Check, Handshake, Navigation, Phone, ShieldCheck, Timer, User } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { confirmArrival, trackIncident, type TrackResult } from "@/lib/api";
import { stageFromStatus, TRACK_STAGES, UNITS } from "@/lib/resq-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/track/$token")({
  head: () => ({
    meta: [
      { title: "RESQ — Live rescue tracking" },
      { name: "description", content: "Follow your SOS from received to rescued, with live unit distance and ETA." },
      { property: "og:title", content: "RESQ — Live rescue tracking" },
      { property: "og:description", content: "Follow your SOS from received to rescued." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: TrackPage,
});

const CHECKS = ["Safe Extraction", "First Aid", "Food / Water"];

function TrackPage() {
  const { token } = Route.useParams();
  const demo = token.startsWith("demo-");
  const [data, setData] = useState<TrackResult | null>(null);
  const [stage, setStage] = useState(0);
  const [dist, setDist] = useState(4.2);
  const [checks, setChecks] = useState<string[]>([]);
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      if (demo) {
        const raw = localStorage.getItem(`resq.track.${token}`);
        const created = raw ? (JSON.parse(raw).created as number) : Date.now();
        const s = Math.min(3, Math.floor((Date.now() - created) / 8000));
        if (alive) {
          setStage((cur) => (cur === 4 ? 4 : s));
          setData({ incident_number: `KL-${token.slice(5, 9).toUpperCase()}`, status: "SIM", reported_at: new Date(created).toISOString(), tasks: [] });
        }
        return;
      }
      try {
        const r = await trackIncident(token);
        if (alive) { setData(r); setStage(stageFromStatus(r.status)); setError(null); }
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : "Could not load");
      }
    };
    poll();
    const id = setInterval(poll, 4000);
    return () => { alive = false; clearInterval(id); };
  }, [token, demo]);

  // Unit closing distance once dispatched
  useEffect(() => {
    if (stage < 2 || stage === 4) return;
    const id = setInterval(() => setDist((d) => Math.max(0.2, +(d - 0.1).toFixed(1))), 2000);
    return () => clearInterval(id);
  }, [stage]);

  const task = data?.tasks[0];
  const unit = UNITS[0]!;
  const eta = task?.eta_minutes ?? Math.max(1, Math.round(dist * 3));

  const confirm = async () => {
    try {
      if (!demo) await confirmArrival(token, `Checklist: ${checks.join(", ")}`);
      setConfirmed(true);
      setStage(4);
      toast.success("Rescue confirmed — thank you. Stay safe.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Confirmation failed");
    }
  };

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <div>
        <div className="label-caps">Tracking · {token.slice(0, 14)}</div>
        <h1 className="text-5xl font-bold uppercase">{data?.incident_number ?? "Loading…"}</h1>
        {error && <p className="mt-1 text-sm text-warning">{error}</p>}
      </div>

      <ol className="grid grid-cols-5 gap-2">
        {TRACK_STAGES.map((s, i) => (
          <li key={s} className="flex flex-col items-center gap-2 text-center">
            <div className={cn(
              "grid size-10 place-items-center rounded-full border-2 font-mono text-sm font-bold",
              i < stage ? "border-success bg-success text-success-foreground"
                : i === stage ? "border-primary bg-primary text-primary-foreground animate-sos" : "border-border text-muted-foreground",
            )}>
              {i < stage || (i === 4 && stage === 4) ? <Check className="size-5" /> : i + 1}
            </div>
            <span className={cn("text-xs font-medium uppercase", i <= stage ? "text-foreground" : "text-muted-foreground")}>{s}</span>
            <div className={cn("h-1 w-full rounded", i <= stage ? "bg-success" : "bg-muted")} />
          </li>
        ))}
      </ol>

      {stage >= 2 && (
        <section className="grid gap-4 rounded-lg border border-border bg-card p-5 md:grid-cols-[1fr_auto]">
          <div>
            <div className="label-caps">Deployed unit</div>
            <div className="font-display text-2xl font-bold uppercase">{task?.responder_type ?? unit.name}</div>
            <div className="mt-1 text-sm text-muted-foreground">+ ALS Ambulance KL-12-114 on standby</div>
            <div className="mt-3 flex flex-wrap gap-4 text-sm">
              <span className="flex items-center gap-1.5"><User className="size-4 text-primary" /> {unit.officer}</span>
              <span className="flex items-center gap-1.5"><Phone className="size-4 text-primary" /> 112</span>
            </div>
          </div>
          <div className="flex gap-6">
            <div><div className="label-caps flex items-center gap-1"><Navigation className="size-3" />Distance</div><div className="font-mono text-4xl font-bold">{dist} <span className="text-base">km</span></div></div>
            <div><div className="label-caps flex items-center gap-1"><Timer className="size-3" />ETA</div><div className="font-mono text-4xl font-bold text-warning">{eta} <span className="text-base">min</span></div></div>
          </div>
        </section>
      )}

      <section className="rounded-lg border border-border bg-card p-5">
        <div className="flex items-center gap-2"><Handshake className="size-5 text-success" /><h2 className="font-display text-xl font-bold uppercase">Two-way handshake</h2></div>
        {confirmed ? (
          <p className="mt-3 flex items-center gap-2 text-success"><ShieldCheck className="size-5" /> Help received and recorded in the audit ledger.</p>
        ) : (
          <>
            <p className="mt-1 text-sm text-muted-foreground">Once rescuers reach you, confirm what you received.</p>
            <div className="mt-4 grid gap-3">
              {CHECKS.map((c) => (
                <label key={c} className="flex items-center gap-3 text-sm">
                  <Checkbox checked={checks.includes(c)} onCheckedChange={(v) => setChecks((cur) => (v ? [...cur, c] : cur.filter((x) => x !== c)))} />
                  {c}
                </label>
              ))}
            </div>
            <Button variant="success" className="mt-4 w-full" size="lg" disabled={!checks.length} onClick={confirm}>
              🤝 Confirm Help Received
            </Button>
          </>
        )}
      </section>
    </div>
  );
}
