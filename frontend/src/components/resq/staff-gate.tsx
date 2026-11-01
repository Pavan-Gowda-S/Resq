import { KeyRound, Lock } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { clearSession, getUser, login, ensureDemoAuth, type SessionUser } from "@/lib/api";

type Role = { value: string; label: string };

// Simple RBAC gate: signs staff in against the RESQ backend, or lets them
// enter demo mode with a chosen role when the backend is unreachable.
export function StaffGate({ portal, roles, children }: {
  portal: string;
  roles: Role[];
  children: (user: SessionUser, signOut: () => void) => React.ReactNode;
}) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [ready, setReady] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState(roles[0]!.value);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const demo = sessionStorage.getItem(`resq.demo.${portal}`);
    setUser(demo ? (JSON.parse(demo) as SessionUser) : getUser());
    setReady(true);
  }, [portal]);

  const signOut = () => {
    clearSession();
    sessionStorage.removeItem(`resq.demo.${portal}`);
    setUser(null);
  };

  if (!ready) return null;
  if (user) return <>{children(user, signOut)}</>;

  const onLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      setUser(await login(email, password));
      toast.success("Signed in");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  };

  const enterDemo = async () => {
    const label = roles.find((r) => r.value === role)?.label ?? role;
    setBusy(true);
    try {
      const authUser = await ensureDemoAuth(label);
      const u = {
        ...authUser,
        full_name: `${label} (Live Session)`,
        role,
      };
      sessionStorage.setItem(`resq.demo.${portal}`, JSON.stringify(u));
      setUser(u);
      toast.success(`Connected to Live Database as ${label}`);
    } catch {
      const u = { full_name: `Demo ${label}`, email: "demo@resq.kerala.gov.in", role };
      sessionStorage.setItem(`resq.demo.${portal}`, JSON.stringify(u));
      setUser(u);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto grid max-w-md gap-6 py-16">
      <div className="text-center">
        <Lock className="mx-auto size-10 text-primary" />
        <h1 className="mt-3 text-4xl font-bold uppercase">{portal} Access</h1>
        <p className="text-sm text-muted-foreground">Authorised personnel only</p>
      </div>
      <form onSubmit={onLogin} className="grid gap-4 rounded-lg border border-border bg-card p-6">
        <div className="grid gap-2">
          <Label htmlFor="em">Official email</Label>
          <Input id="em" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="pw">Password</Label>
          <Input id="pw" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        <Button type="submit" disabled={busy}><KeyRound /> {busy ? "Verifying…" : "Sign in"}</Button>
        <div className="border-t border-border pt-4">
          <div className="label-caps mb-2">Or continue as demo role</div>
          <div className="flex gap-2">
            {roles.map((r) => (
              <button
                type="button"
                key={r.value}
                onClick={() => setRole(r.value)}
                className={`flex-1 rounded border px-2 py-2 text-sm ${role === r.value ? "border-primary bg-primary/15 text-foreground" : "border-border text-muted-foreground"}`}
              >
                {r.label}
              </button>
            ))}
          </div>
          <Button type="button" variant="secondary" className="mt-3 w-full" onClick={enterDemo}>Enter demo mode</Button>
        </div>
      </form>
    </div>
  );
}
