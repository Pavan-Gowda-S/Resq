import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { PORTALS } from "@/components/resq/shell";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "RESQ — Choose your portal" },
      { name: "description", content: "Kerala disaster response: citizen SOS, hospitals, rescue teams, control room and admin portals." },
      { property: "og:title", content: "RESQ — Choose your portal" },
      { property: "og:description", content: "Kerala disaster response: citizen SOS, hospitals, rescue teams, control room and admin portals." },
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

function Index() {
  return (
    <div className="py-8">
      <div className="label-caps">Kerala State Disaster Management · Flood & Landslide Response</div>
      <h1 className="mt-2 max-w-4xl text-6xl font-bold uppercase leading-none md:text-8xl">
        One incident.<br /><span className="text-primary">Every responder.</span>
      </h1>
      <p className="mt-4 max-w-xl text-muted-foreground">
        RESQ coordinates citizens, rescue teams, ambulances, hospitals and blood banks in real time. Select your role.
      </p>
      <div className="mt-10 grid gap-3 md:grid-cols-5">
        {PORTALS.map((p, i) => (
          <Link
            key={p.to}
            to={p.to}
            className={`group flex flex-col justify-between rounded-lg border p-5 transition-colors ${i === 0 ? "border-primary bg-primary/15 md:row-span-1" : "border-border bg-card hover:border-primary"}`}
          >
            <p.icon className={`size-8 ${i === 0 ? "text-primary" : "text-muted-foreground group-hover:text-primary"}`} />
            <div className="mt-8">
              <div className="font-display text-2xl font-bold uppercase">{p.label}</div>
              <p className="mt-1 text-sm text-muted-foreground">{DESC[p.to]}</p>
              <ArrowRight className="mt-3 size-4 text-primary" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
