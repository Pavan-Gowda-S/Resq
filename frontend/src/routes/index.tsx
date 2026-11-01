import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  Flame,
  Play,
  CheckCircle2,
  RefreshCw,
  ExternalLink,
  ShieldAlert,
  Building2,
  Ambulance,
  MapPin,
  Radio,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { PORTALS } from "@/components/resq/shell";
import { Button } from "@/components/ui/button";
import {
  submitReport,
  ensureDemoAuth,
  api,
  DEFAULT_HOSPITAL_ID,
  DEFAULT_RESCUE_ORG_ID,
} from "@/lib/api";
import { createAndPropagateEmergency } from "@/lib/crisis-sync";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "RESQ — Unified Disaster Response Network" },
      { name: "description", content: "Kerala disaster response: live citizen SOS, hospital capacity, rescue teams, control room and crisis simulator." },
      { property: "og:title", content: "RESQ — Unified Disaster Response Network" },
      { property: "og:description", content: "Kerala disaster response: coordinated real-time crisis operations." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

const DESC: Record<string, string> = {
  "/citizen": "Voice-first SOS. Speak, snap a photo, help is dispatched.",
  "/hospital": "Bed & blood counters, incoming casualty queue.",
  "/rescue": "Active dispatch, field updates, backup requests.",
  "/control": "District war room: GIS map, AI agent feed, analytics.",
  "/admin": "Fleet onboarding, audit ledger, system telemetry.",
};

type ScenarioResult = {
  incidentId: string;
  incidentNumber: string;
  trackingToken: string;
  tasksCreated: number;
  assignedHospital: string;
  assignedRescue: string;
};

function Index() {
  const navigate = useNavigate();
  const [running, setRunning] = useState(false);
  const [step, setStep] = useState<number>(0);
  const [scenarioData, setScenarioData] = useState<ScenarioResult | null>(null);

  const runFullCrisisScenario = async () => {
    setRunning(true);
    setStep(1);
    toast.info("Step 1: Submitting Citizen SOS into live system...");

    try {
      // 1. Citizen SOS & Real-Time Multi-Portal Propagation
      const crisis = await createAndPropagateEmergency({
        description: "CRITICAL FLOOD: Flash flood and mudslide at Mundakkai Chooralmala. 4 civilians stranded on rooftop, 1 hypothermic child.",
        lat: 11.5601,
        lng: 76.1335,
        district: "Wayanad",
        landmark: "Chooralmala River Bridge",
        people_affected: 4,
        trappedCount: 2,
        reporter_name: "Praveen Kumar",
        reporter_phone: "+919847123456",
      });

      setStep(2);
      toast.info(`Incident created: ${crisis.incidentNumber}. Running AI Triage...`);
      await new Promise((r) => setTimeout(r, 800));

      setStep(3);
      toast.info("Step 3: AI Agents auto-assigned NDRF Wayanad & reserved ICU Bed...");
      await new Promise((r) => setTimeout(r, 800));

      setStep(4);
      setScenarioData({
        incidentId: crisis.incidentId,
        incidentNumber: crisis.incidentNumber,
        trackingToken: crisis.trackingToken,
        tasksCreated: 2,
        assignedHospital: "Wayanad District Hospital (ICU Bed Reserved)",
        assignedRescue: "NDRF 4th Battalion - Wayanad Unit",
      });

      toast.success(`Crisis ${crisis.incidentNumber} active! Synchronized across all portals.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Scenario execution failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="py-8 pb-16">
      <div className="label-caps flex items-center gap-2">
        <Radio className="size-3.5 text-emerald-500 animate-pulse" />
        Kerala State Disaster Management Authority · Disaster Operations Center
      </div>

      <h1 className="mt-2 max-w-4xl text-5xl sm:text-6xl md:text-8xl font-black uppercase leading-none tracking-tight">
        One incident.<br />
        <span className="text-primary">Every responder.</span>
      </h1>

      <p className="mt-4 max-w-2xl text-base sm:text-lg text-muted-foreground leading-relaxed">
        Autonomous disaster coordination across Kerala. Integrates Citizens, Field Rescue Teams,
        Ambulances, Triage Hospitals, and the War Room in a unified live data mesh.
      </p>

      {/* Live Scenario Simulator Control Panel */}
      <div className="mt-8 rounded-2xl border-2 border-primary/50 bg-card p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 p-6 opacity-10 pointer-events-none">
          <Flame className="size-36 text-primary" />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-bold text-primary mb-2">
              <ShieldAlert className="size-3.5" />
              Live Scenario Simulator
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold uppercase">
              Wayanad Landslide Crisis Simulation
            </h2>
            <p className="text-sm text-muted-foreground max-w-xl mt-1">
              Test the end-to-end autonomous flow: triggers a live Citizen SOS report, runs the
              AI dispatch & ICU routing agents, and synchronizes the entire network in real-time.
            </p>
          </div>

          <Button
            size="lg"
            variant="default"
            disabled={running}
            onClick={runFullCrisisScenario}
            className="font-bold text-base px-6 py-6 shadow-lg shadow-primary/25"
          >
            {running ? (
              <>
                <RefreshCw className="size-5 animate-spin mr-2" />
                Simulating Crisis Flow...
              </>
            ) : (
              <>
                <Play className="size-5 mr-2 fill-current" />
                Run Crisis Simulation
              </>
            )}
          </Button>
        </div>

        {/* Stepper Progress Bar */}
        {step > 0 && (
          <div className="mt-6 border-t border-border pt-5">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className={`rounded-xl p-3 border ${step >= 1 ? "bg-primary/10 border-primary/40 text-primary" : "bg-muted/30 border-border text-muted-foreground"}`}>
                <div className="text-xs font-mono font-bold">01 / CITIZEN SOS</div>
                <div className="text-sm font-semibold mt-0.5">Report Submitted</div>
                <div className="text-[11px] opacity-75 mt-1">POST /incidents/report</div>
              </div>

              <div className={`rounded-xl p-3 border ${step >= 2 ? "bg-primary/10 border-primary/40 text-primary" : "bg-muted/30 border-border text-muted-foreground"}`}>
                <div className="text-xs font-mono font-bold">02 / AI INTELLIGENCE</div>
                <div className="text-sm font-semibold mt-0.5">Triage & Tasks Created</div>
                <div className="text-[11px] opacity-75 mt-1">Task Proposals Built</div>
              </div>

              <div className={`rounded-xl p-3 border ${step >= 3 ? "bg-primary/10 border-primary/40 text-primary" : "bg-muted/30 border-border text-muted-foreground"}`}>
                <div className="text-xs font-mono font-bold">03 / AI AUTO-DISPATCH</div>
                <div className="text-sm font-semibold mt-0.5">PostGIS NDRF + ICU Bed</div>
                <div className="text-[11px] opacity-75 mt-1">Atomic Bed Reservation</div>
              </div>

              <div className={`rounded-xl p-3 border ${step >= 4 ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-500" : "bg-muted/30 border-border text-muted-foreground"}`}>
                <div className="text-xs font-mono font-bold">04 / NETWORK SYNC</div>
                <div className="text-sm font-semibold mt-0.5">All 4 Portals Live</div>
                <div className="text-[11px] opacity-75 mt-1">Multi-Tenant Broadcast</div>
              </div>
            </div>

            {/* Results & Quick Portal Launchers */}
            {scenarioData && (
              <div className="mt-5 rounded-xl bg-muted/40 border border-border p-4">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/50 pb-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="size-5 text-emerald-500" />
                    <span className="font-bold text-sm">
                      Crisis Incident Active:{" "}
                      <span className="font-mono text-primary font-extrabold">
                        {scenarioData.incidentNumber}
                      </span>
                    </span>
                  </div>
                  <span className="text-xs font-mono text-muted-foreground">
                    Token: {scenarioData.trackingToken.slice(0, 18)}...
                  </span>
                </div>

                <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2 text-muted-foreground font-mono">
                  <div>
                    🚒 Assigned Team: <strong className="text-foreground">{scenarioData.assignedRescue}</strong>
                  </div>
                  <div>
                    🏥 Hospital Bed: <strong className="text-emerald-500">{scenarioData.assignedHospital}</strong>
                  </div>
                </div>

                {/* Direct Action Links into each portal for this scenario */}
                <div className="mt-4 flex flex-wrap gap-2.5 pt-2">
                  <Link
                    to="/rescue"
                    className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-bold uppercase text-primary-foreground hover:opacity-90"
                  >
                    <Ambulance className="size-3.5" /> Open Rescue Portal
                  </Link>

                  <Link
                    to="/hospital"
                    className="inline-flex items-center gap-1.5 rounded-lg bg-card border border-border px-3 py-2 text-xs font-bold uppercase hover:border-primary text-foreground"
                  >
                    <Building2 className="size-3.5 text-emerald-500" /> Open Hospital Portal
                  </Link>

                  <Link
                    to="/control"
                    className="inline-flex items-center gap-1.5 rounded-lg bg-card border border-border px-3 py-2 text-xs font-bold uppercase hover:border-primary text-foreground"
                  >
                    <Radio className="size-3.5 text-sky-400" /> Open Control Room
                  </Link>

                  <Link
                    to="/track/$token"
                    params={{ token: scenarioData.trackingToken }}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-muted px-3 py-2 text-xs font-bold uppercase text-muted-foreground hover:text-foreground"
                  >
                    <MapPin className="size-3.5 text-amber-500" /> Citizen Live Tracker
                  </Link>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Portal Selection Grid */}
      <div className="mt-10">
        <div className="label-caps mb-3">Operational Role Consoles</div>
        <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
          {PORTALS.map((p, i) => (
            <Link
              key={p.to}
              to={p.to}
              className={`group flex flex-col justify-between rounded-xl border p-5 transition-all shadow-sm ${
                i === 0
                  ? "border-primary bg-primary/10 hover:bg-primary/15"
                  : "border-border bg-card hover:border-primary/80 hover:shadow-md"
              }`}
            >
              <p.icon
                className={`size-8 transition-transform group-hover:scale-110 ${
                  i === 0 ? "text-primary" : "text-muted-foreground group-hover:text-primary"
                }`}
              />
              <div className="mt-8">
                <div className="font-display text-xl font-bold uppercase tracking-tight">
                  {p.label}
                </div>
                <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{DESC[p.to]}</p>
                <div className="mt-3 flex items-center gap-1 text-xs font-semibold text-primary">
                  Launch Console <ArrowRight className="size-3 transition-transform group-hover:translate-x-1" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
