import { Link, useRouterState } from "@tanstack/react-router";
import { Activity, Ambulance, Hospital, LifeBuoy, Radar, ShieldCheck, Siren } from "lucide-react";
import { useEffect, useState } from "react";
import { checkHealth } from "@/lib/api";
import { cn } from "@/lib/utils";

const PORTALS = [
  { to: "/citizen", label: "Citizen SOS", icon: Siren },
  { to: "/hospital", label: "Hospital", icon: Hospital },
  { to: "/rescue", label: "Rescue Team", icon: LifeBuoy },
  { to: "/control", label: "Control Room", icon: Radar },
  { to: "/admin", label: "Admin", icon: ShieldCheck },
] as const;

export function useBackendHealth(intervalMs = 20000) {
  const [state, setState] = useState<{ ok: boolean | null; ms: number }>({ ok: null, ms: 0 });
  useEffect(() => {
    let alive = true;
    const run = () => checkHealth().then((r) => alive && setState(r));
    run();
    const id = setInterval(run, intervalMs);
    return () => { alive = false; clearInterval(id); };
  }, [intervalMs]);
  return state;
}

export function AppHeader() {
  const path = useRouterState({ select: (s) => s.location.pathname });
  const health = useBackendHealth();
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-surface/95 backdrop-blur">
      <div className="mx-auto flex max-w-[1600px] items-center gap-4 px-4 py-2">
        <Link to="/" className="flex items-center gap-2">
          <span className="grid size-8 place-items-center rounded bg-primary text-primary-foreground">
            <Activity className="size-5" />
          </span>
          <span className="font-display text-2xl font-bold tracking-wider">RESQ</span>
          <span className="hidden label-caps md:inline">Kerala · KSDMA</span>
        </Link>
        <nav className="ml-auto flex gap-1 overflow-x-auto">
          {PORTALS.map((p) => {
            const active = path.startsWith(p.to);
            return (
              <Link
                key={p.to}
                to={p.to}
                className={cn(
                  "flex shrink-0 items-center gap-1.5 rounded px-3 py-1.5 text-sm font-medium transition-colors",
                  active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <p.icon className="size-4" />
                <span className="hidden sm:inline">{p.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="hidden items-center gap-2 rounded border border-border px-2 py-1 font-mono text-xs lg:flex">
          <span
            className={cn(
              "size-2 rounded-full animate-blink",
              health.ok === null ? "bg-muted-foreground" : health.ok ? "bg-success" : "bg-warning",
            )}
          />
          {health.ok === null ? "CHECKING" : health.ok ? `LIVE ${health.ms}ms` : "SIMULATION"}
        </div>
      </div>
    </header>
  );
}

export { PORTALS };

export function TriageBadge({ level }: { level: "RED" | "YELLOW" | "GREEN" }) {
  const map = {
    RED: "bg-primary text-primary-foreground",
    YELLOW: "bg-warning text-warning-foreground",
    GREEN: "bg-success text-success-foreground",
  };
  const label = { RED: "IMMEDIATE", YELLOW: "DELAYED", GREEN: "MINOR" };
  return (
    <span className={cn("rounded px-2 py-0.5 font-mono text-[10px] font-bold tracking-wider", map[level])}>
      {level} · {label[level]}
    </span>
  );
}

export function PageTitle({ eyebrow, title, children }: { eyebrow: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className="label-caps">{eyebrow}</div>
        <h1 className="text-4xl font-bold uppercase md:text-5xl">{title}</h1>
      </div>
      {children}
    </div>
  );
}

export function Panel({ title, icon: Icon, children, className, action }: {
  title: string;
  icon?: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  className?: string;
  action?: React.ReactNode;
}) {
  return (
    <section className={cn("rounded-lg border border-border bg-card", className)}>
      <div className="flex items-center gap-2 border-b border-border px-4 py-2.5">
        {Icon && <Icon className="size-4 text-primary" />}
        <h2 className="font-display text-lg font-semibold uppercase tracking-wide">{title}</h2>
        <div className="ml-auto">{action}</div>
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

export { Ambulance };
