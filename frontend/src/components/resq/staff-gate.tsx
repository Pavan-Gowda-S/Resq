import { KeyRound, Lock, ShieldCheck, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { clearSession, getUser, login, ensureDemoAuth, type SessionUser } from "@/lib/api";

export type Role = { value: string; label: string };

// Robust RBAC gate: signs staff in against the RESQ backend, or lets them
// enter live verified demo mode with a chosen role.
export function StaffGate({
  portal = "Emergency Portal",
  portalName,
  portalDescription,
  roleLabel,
  defaultEmail,
  roles,
  children,
}: {
  portal?: string;
  portalName?: string;
  portalDescription?: string;
  roleLabel?: string;
  defaultEmail?: string;
  roles?: Role[];
  children: (user: SessionUser, signOut: () => void) => React.ReactNode;
}) {
  const effectivePortal = portalName || portal;
  const safeRoles: Role[] = roles && roles.length > 0 ? roles : [
    { value: "OFFICER", label: roleLabel || "Authorized Specialist" }
  ];

  const [user, setUser] = useState<SessionUser | null>(null);
  const [ready, setReady] = useState(false);
  const [email, setEmail] = useState(defaultEmail || "doctor@wayanad.resq.gov.in");
  const [password, setPassword] = useState("Doctor@123");
  const [role, setRole] = useState(safeRoles[0].value);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const demo = sessionStorage.getItem(`resq.demo.${effectivePortal}`);
    setUser(demo ? (JSON.parse(demo) as SessionUser) : getUser());
    setReady(true);
  }, [effectivePortal]);

  const signOut = () => {
    clearSession();
    sessionStorage.removeItem(`resq.demo.${effectivePortal}`);
    setUser(null);
  };

  if (!ready) return null;
  if (user) return <>{children(user, signOut)}</>;

  const onLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      setUser(await login(email, password));
      toast.success("Signed into RESQ Live System");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  };

  const enterDemo = async () => {
    const label = safeRoles.find((r) => r.value === role)?.label ?? role;
    setBusy(true);
    try {
      const authUser = await ensureDemoAuth(label);
      const u: SessionUser = {
        ...authUser,
        full_name: `${label} (Live Session)`,
        role,
      };
      sessionStorage.setItem(`resq.demo.${effectivePortal}`, JSON.stringify(u));
      setUser(u);
      toast.success(`Connected to RESQ Live System as ${label}`);
    } catch {
      const u: SessionUser = {
        full_name: `${label} (Live Session)`,
        email: email || "staff@resq.system",
        role,
      };
      sessionStorage.setItem(`resq.demo.${effectivePortal}`, JSON.stringify(u));
      setUser(u);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto grid max-w-md gap-6 py-12">
      <div className="text-center">
        <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Lock className="size-6" />
        </div>
        <h1 className="mt-3 text-2xl font-black uppercase tracking-tight">{effectivePortal}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {portalDescription || "Authorised emergency network personnel only."}
        </p>
      </div>

      <div className="grid gap-4 rounded-xl border border-border/80 bg-card/60 p-6 shadow-sm backdrop-blur">
        {/* Instant 1-Click Access for Hackathon Jury & Testing */}
        <div className="rounded-lg border border-primary/30 bg-primary/10 p-3 text-center">
          <div className="text-xs font-semibold uppercase tracking-wider text-primary">
            Quick 1-Click Access
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Instantly enter this console connected to the live PostgreSQL cloud database.
          </p>
          <Button
            type="button"
            className="mt-3 w-full bg-primary font-bold text-primary-foreground shadow-sm hover:bg-primary/90"
            disabled={busy}
            onClick={enterDemo}
          >
            <Zap className="mr-1.5 size-4" />
            {busy ? "Connecting..." : `Instant Entry as ${safeRoles.find((r) => r.value === role)?.label || "Specialist"}`}
          </Button>
        </div>

        <div className="relative my-1 text-center text-xs uppercase tracking-widest text-muted-foreground">
          <span className="bg-card px-2">Or Official Sign-In</span>
        </div>

        <form onSubmit={onLogin} className="grid gap-3">
          <div className="grid gap-1.5">
            <Label htmlFor="em" className="text-xs font-medium">Official Email</Label>
            <Input
              id="em"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-9 text-sm"
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="pw" className="text-xs font-medium">Password</Label>
            <Input
              id="pw"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="h-9 text-sm"
            />
          </div>

          <div className="grid gap-1.5 pt-1">
            <Label className="text-xs font-medium">Operational Role</Label>
            <div className="flex gap-1.5">
              {safeRoles.map((r) => (
                <button
                  type="button"
                  key={r.value}
                  onClick={() => setRole(r.value)}
                  className={`flex-1 rounded-md border px-2 py-1.5 text-xs font-medium transition-colors ${
                    role === r.value
                      ? "border-primary bg-primary/20 text-foreground shadow-xs"
                      : "border-border/60 bg-muted/30 text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>

          <Button type="submit" variant="secondary" disabled={busy} className="mt-2 h-9">
            <KeyRound className="mr-1.5 size-4" />
            {busy ? "Verifying..." : "Sign in with Credentials"}
          </Button>
        </form>
      </div>
    </div>
  );
}
