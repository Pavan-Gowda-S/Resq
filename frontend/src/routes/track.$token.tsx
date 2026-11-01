import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Check,
  CheckCircle2,
  Navigation,
  Phone,
  ShieldCheck,
  Timer,
  User,
  Ambulance,
  Building2,
  Radio,
  AlertCircle,
  HeartHandshake,
  ArrowLeft,
  Copy,
  RefreshCw,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { confirmArrival, trackIncident, type TrackResult } from "@/lib/api";
import {
  getActiveCrisis,
  subscribeToCrisisUpdates,
  updateCrisisStage,
  type ActiveCrisis,
} from "@/lib/crisis-sync";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/track/$token")({
  head: () => ({
    meta: [
      { title: "RESQ — Live Rescue Tracking & Assistance" },
      { name: "description", content: "Track your rescue team, ETA, assigned ambulance, and confirm help received." },
      { property: "og:title", content: "RESQ — Live Rescue Tracking" },
      { property: "og:description", content: "Real-time rescue tracking for citizens in distress." },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: TrackPage,
});

const PROGRESS_STAGES = [
  { label: "SOS Received", desc: "Logged at Command" },
  { label: "Dispatched", desc: "Team Mobilized" },
  { label: "En Route", desc: "Closing Distance" },
  { label: "On Scene", desc: "At Your Location" },
  { label: "Safe & Rescued", desc: "Casualty Extracted" },
];

export function TrackPage() {
  const { token } = Route.useParams();
  const [crisis, setCrisis] = useState<ActiveCrisis | null>(getActiveCrisis());
  const [apiData, setApiData] = useState<TrackResult | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [dist, setDist] = useState(2.8);
  const [eta, setEta] = useState(7);
  const [copied, setCopied] = useState(false);

  // Sync with cross-portal crisis broadcast
  useEffect(() => {
    const unsubscribe = subscribeToCrisisUpdates((updated) => {
      if (updated) {
        setCrisis(updated);
        if (updated.confirmedReceivedHelp) {
          setConfirmed(true);
        }
      }
    });
    return unsubscribe;
  }, []);

  // Poll backend and local crisis storage for real-time status updates (throttled)
  useEffect(() => {
    let alive = true;
    const pollStatus = async () => {
      // 1. Check local synchronized crisis (instant reflex without hitting backend)
      const current = getActiveCrisis();
      if (alive && current) {
        setCrisis(current);
        if (current.confirmedReceivedHelp) {
          setConfirmed(true);
        }
      }

      // 2. Poll backend for official audit record only if document is visible
      if (typeof document !== "undefined" && document.visibilityState !== "visible") return;

      try {
        const res = await trackIncident(token);
        if (alive) {
          setApiData(res);
        }
      } catch {
        // Fallback to active crisis
      }
    };

    pollStatus();
    // 12s gentle interval prevents tunnel rate limiting; BroadcastChannel handles instant multi-tab sync
    const interval = setInterval(pollStatus, 12000);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, [token]);

  // Simulate closing distance smoothly if en route
  useEffect(() => {
    if (crisis?.stageIndex === 3) {
      setDist(0.1);
      setEta(1);
      return;
    }
    if (crisis?.stageIndex === 4 || confirmed) {
      setDist(0);
      setEta(0);
      return;
    }

    const timer = setInterval(() => {
      setDist((prev) => +(Math.max(0.2, prev - 0.1).toFixed(1)));
      setEta((prev) => Math.max(1, prev - 1));
    }, 4000);
    return () => clearInterval(timer);
  }, [crisis?.stageIndex, confirmed]);

  const incidentNumber =
    crisis?.incidentNumber || apiData?.incident_number || `RESQ-2026-${token.slice(4, 8).toUpperCase()}`;

  const currentStage = confirmed ? 4 : (crisis?.stageIndex ?? 2);

  // One-tap confirm help received
  const handleConfirmHelp = async () => {
    setConfirmed(true);
    updateCrisisStage("RESCUED");
    try {
      await confirmArrival(token, "Citizen tapped one-touch confirmation: Help received safely.");
      toast.success("Help confirmation recorded in the official audit log.");
    } catch {
      toast.success("Help recorded locally. Stay safe with the rescue team.");
    }
  };

  const copyIncidentId = () => {
    navigator.clipboard.writeText(incidentNumber);
    setCopied(true);
    toast.success("Incident ID copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mx-auto max-w-2xl py-6 pb-20">
      {/* Top back & emergency hotlines */}
      <div className="mb-4 flex items-center justify-between">
        <Link
          to="/citizen"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" /> Back to SOS
        </Link>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-muted-foreground">Emergency Hotline:</span>
          <a
            href="tel:112"
            className="inline-flex items-center gap-1 rounded bg-red-500/10 border border-red-500/20 px-2 py-0.5 text-xs font-bold text-red-500 hover:bg-red-500/20"
          >
            <Phone className="size-3" /> Call 112
          </a>
        </div>
      </div>

      {/* Hero Status Card */}
      <section className="rounded-2xl border-2 border-primary/40 bg-card p-6 shadow-xl relative overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "size-3 rounded-full animate-pulse",
                confirmed ? "bg-emerald-500" : "bg-primary"
              )}
            />
            <span className="font-mono text-xs font-bold uppercase tracking-wider text-primary">
              {confirmed ? "Rescue Completed" : "Active Emergency Response"}
            </span>
          </div>

          {/* Copyable Incident Number */}
          <button
            onClick={copyIncidentId}
            className="inline-flex items-center gap-1.5 rounded-lg bg-muted px-2.5 py-1 text-xs font-mono font-bold hover:bg-muted/80 transition-colors"
            title="Click to copy ID"
          >
            ID: <span className="text-primary">{incidentNumber}</span>
            <Copy className="size-3 text-muted-foreground" />
          </button>
        </div>

        <h1 className="mt-3 text-3xl sm:text-4xl font-extrabold uppercase tracking-tight text-foreground">
          {confirmed
            ? "You Are Safe & Help Has Arrived"
            : currentStage >= 3
            ? "Rescuers Are At Your Location"
            : "Help Is On The Way"}
        </h1>

        <p className="mt-1 text-sm text-muted-foreground">
          {confirmed
            ? "Your confirmation has been relayed to the District War Room and medical staff."
            : "Stay in place, conserve your phone battery, and look out for flashlights or boat horns."}
        </p>

        {/* Live Distance and ETA */}
        {!confirmed && (
          <div className="mt-5 grid grid-cols-2 gap-3 border-t border-border/60 pt-4">
            <div className="rounded-xl bg-muted/50 p-3.5">
              <div className="text-xs text-muted-foreground flex items-center gap-1.5 font-medium">
                <Navigation className="size-3.5 text-sky-400" /> Current Distance
              </div>
              <div className="font-mono text-3xl sm:text-4xl font-extrabold text-foreground mt-1">
                {dist} <span className="text-sm font-normal text-muted-foreground">km</span>
              </div>
            </div>

            <div className="rounded-xl bg-muted/50 p-3.5">
              <div className="text-xs text-muted-foreground flex items-center gap-1.5 font-medium">
                <Timer className="size-3.5 text-amber-500" /> Estimated Arrival
              </div>
              <div className="font-mono text-3xl sm:text-4xl font-extrabold text-amber-500 mt-1">
                {eta} <span className="text-sm font-normal text-muted-foreground">min</span>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Progress Stepper */}
      <section className="mt-6 rounded-2xl border border-border bg-card p-5">
        <div className="label-caps mb-3">Rescue Response Timeline</div>
        <div className="grid grid-cols-5 gap-1.5 sm:gap-2">
          {PROGRESS_STAGES.map((s, idx) => {
            const isCompleted = idx < currentStage;
            const isCurrent = idx === currentStage;
            return (
              <div key={s.label} className="flex flex-col items-center text-center">
                <div
                  className={cn(
                    "grid size-9 sm:size-10 place-items-center rounded-full border-2 font-mono text-xs sm:text-sm font-bold transition-all",
                    isCompleted && "border-emerald-500 bg-emerald-500 text-white shadow-sm",
                    isCurrent && "border-primary bg-primary text-primary-foreground animate-pulse shadow-md",
                    !isCompleted && !isCurrent && "border-border text-muted-foreground bg-muted/30"
                  )}
                >
                  {isCompleted ? <Check className="size-4 sm:size-5" /> : idx + 1}
                </div>
                <span
                  className={cn(
                    "text-[10px] sm:text-xs font-bold uppercase mt-1.5 leading-tight",
                    idx <= currentStage ? "text-foreground" : "text-muted-foreground"
                  )}
                >
                  {s.label}
                </span>
                <span className="hidden sm:block text-[9px] text-muted-foreground mt-0.5">
                  {s.desc}
                </span>
              </div>
            );
          })}
        </div>
      </section>

      {/* WHO IS COMING TO HELP YOU (Human & Reassuring) */}
      <section className="mt-6 rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="label-caps flex items-center gap-1 text-primary font-bold mb-3">
          <ShieldCheck className="size-3.5" />
          Who Is Coming To Help You
        </div>

        <div className="space-y-4">
          {/* Primary Rescue Team / NGO */}
          <div className="flex items-start justify-between gap-3 rounded-xl bg-muted/40 p-4 border border-border/50">
            <div>
              <div className="text-xs uppercase tracking-wider text-muted-foreground font-semibold flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
                Assigned Disaster Response NGO
              </div>
              <div className="text-lg font-bold text-foreground mt-0.5">
                {crisis?.assignedRescue?.unitName ?? "Nestwise Disaster NGO — NDRF Wayanad Rapid Wing"}
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">
                NGO Organization: <strong className="text-foreground">{crisis?.assignedRescue?.ngoOrgName ?? "Nestwise Humanitarian Rescue NGO"}</strong>
              </div>
              <div className="text-sm text-muted-foreground mt-1 flex items-center gap-1.5">
                <User className="size-3.5 text-primary" />
                Team Commander: <strong className="text-foreground">{crisis?.assignedRescue?.teamLeader ?? "Insp. Rajesh Nair (Team Bravo)"}</strong>
              </div>
            </div>

            <a
              href="tel:112"
              className="inline-flex items-center gap-1 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 px-3 py-2 text-xs font-bold uppercase transition-all"
            >
              <Phone className="size-3.5" /> Call Rescuer
            </a>
          </div>

          {/* Assigned Ambulance */}
          <div className="flex items-start justify-between gap-3 rounded-xl bg-muted/40 p-4 border border-border/50">
            <div>
              <div className="text-xs uppercase tracking-wider text-muted-foreground font-semibold flex items-center gap-1">
                <Ambulance className="size-3 text-sky-400" /> MedEvac Standby Unit
              </div>
              <div className="text-base font-bold text-foreground mt-0.5">
                {crisis?.assignedAmbulance?.vehicleNumber ?? "KL-11-AV-1080 (108 ALS Ambulance)"}
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">
                3 Certified Trauma Paramedics On Board · Oxygen Equipped
              </div>
            </div>
            <span className="text-[11px] font-mono font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20 px-2 py-0.5 rounded">
              Ready
            </span>
          </div>

          {/* Hospital Bed Reserved & Acceptance */}
          <div className="flex items-start justify-between gap-3 rounded-xl bg-muted/40 p-4 border border-border/50">
            <div>
              <div className="text-xs uppercase tracking-wider text-muted-foreground font-semibold flex items-center gap-1">
                <Building2 className="size-3 text-emerald-500" /> Destination Medical Center
              </div>
              <div className="text-base font-bold text-foreground mt-0.5">
                {crisis?.assignedHospital?.name ?? "Wayanad District Hospital"}
              </div>
              <div className="mt-1 flex items-center gap-1.5 text-xs font-semibold">
                {crisis?.assignedHospital?.acceptedByHospital ? (
                  <span className="inline-flex items-center gap-1 text-emerald-500">
                    <CheckCircle2 className="size-3.5" /> Hospital Admission Confirmed & Bed Allocated
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-amber-500">
                    <RefreshCw className="size-3 animate-spin" /> ICU Hold Requested by NGO · Awaiting Intake Accept
                  </span>
                )}
              </div>
            </div>
            <a
              href="tel:04936202222"
              className="inline-flex items-center gap-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
            >
              <Phone className="size-3" /> Hospital Line
            </a>
          </div>
        </div>
      </section>

      {/* ONE-TAP CONFIRMATION BUTTON: "YES, I HAVE RECEIVED HELP" */}
      <section className="mt-6 rounded-2xl border-2 border-emerald-500/40 bg-card p-6 text-center shadow-lg">
        {confirmed ? (
          <div className="py-4">
            <CheckCircle2 className="mx-auto size-12 text-emerald-500 mb-2" />
            <h2 className="text-2xl font-bold uppercase text-emerald-500">
              Safe Extraction Confirmed
            </h2>
            <p className="text-sm text-muted-foreground max-w-md mx-auto mt-1">
              Your status has been updated across the Kerala Disaster Response Network. Rescuers and
              hospital intake have recorded your safety.
            </p>
            <div className="mt-4 inline-flex items-center gap-2 text-xs font-mono text-muted-foreground bg-muted px-3 py-1.5 rounded-full">
              <ShieldCheck className="size-3.5 text-emerald-500" /> Sealed in immutable audit log
            </div>
          </div>
        ) : (
          <div>
            <HeartHandshake className="mx-auto size-10 text-emerald-500 mb-2" />
            <h2 className="text-2xl font-extrabold uppercase">
              Have The Rescuers Reached You?
            </h2>
            <p className="text-sm text-muted-foreground max-w-md mx-auto mt-1">
              Once rescue personnel are with you and you are in safe hands, press this button.
              It immediately alerts the Command Center that you are safe.
            </p>

            <Button
              size="lg"
              variant="default"
              onClick={handleConfirmHelp}
              className="mt-5 w-full max-w-md py-6 text-base font-bold uppercase bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/30 active:scale-95 transition-all"
            >
              <CheckCircle2 className="size-5 mr-2" />
              Yes, Help Has Arrived! I Am Safe
            </Button>
          </div>
        )}
      </section>
    </div>
  );
}
