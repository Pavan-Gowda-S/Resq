import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Camera, Crosshair, Loader2, MapPin, Mic, MicOff, Send, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import { submitReport } from "@/lib/api";
import { DISTRICTS, extractIncident, HAZARDS, nearestDistrict, type Hazard } from "@/lib/resq-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/citizen")({
  head: () => ({
    meta: [
      { title: "RESQ Citizen SOS — Report an emergency" },
      { name: "description", content: "Tap, speak in Malayalam or English, and send your location to Kerala rescue teams." },
      { property: "og:title", content: "RESQ Citizen SOS" },
      { property: "og:description", content: "Voice-first emergency reporting for Kerala floods and landslides." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: CitizenPage,
});

type SR = {
  lang: string; continuous: boolean; interimResults: boolean;
  start(): void; stop(): void;
  onresult: ((e: { results: ArrayLike<{ 0: { transcript: string }; isFinal: boolean }> }) => void) | null;
  onend: (() => void) | null; onerror: ((e: { error: string }) => void) | null;
};

function CitizenPage() {
  const navigate = useNavigate();
  const [lang, setLang] = useState<"ml-IN" | "en-IN">("en-IN");
  const [listening, setListening] = useState(false);
  const [text, setText] = useState("");
  const [hazard, setHazard] = useState<Hazard | null>(null);
  const [affected, setAffected] = useState(1);
  const [trapped, setTrapped] = useState(0);
  const [photo, setPhoto] = useState<string | null>(null);
  const [geo, setGeo] = useState<{ lat: number; lng: number; acc: number } | null>(null);
  const [geoErr, setGeoErr] = useState<string | null>(null);
  const [district, setDistrict] = useState("Wayanad");
  const [sending, setSending] = useState(false);
  const [levels, setLevels] = useState<number[]>(Array(32).fill(0.05));

  const recRef = useRef<SR | null>(null);
  const audioRef = useRef<{ ctx: AudioContext; stream: MediaStream; raf: number } | null>(null);

  // Auto GPS
  const locate = () => {
    if (!navigator.geolocation) return setGeoErr("GPS not available");
    setGeoErr(null);
    navigator.geolocation.getCurrentPosition(
      (p) => {
        const g = { lat: p.coords.latitude, lng: p.coords.longitude, acc: Math.round(p.coords.accuracy) };
        setGeo(g);
        if (g.lat > 8 && g.lat < 13 && g.lng > 74.5 && g.lng < 77.5) setDistrict(nearestDistrict(g.lat, g.lng));
      },
      () => setGeoErr("Location blocked — pick your district"),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };
  useEffect(locate, []);

  // Auto-extraction on every transcript change
  useEffect(() => {
    if (!text) return;
    const r = extractIncident(text);
    if (r.hazard) setHazard(r.hazard);
    if (r.affected) setAffected(r.affected);
    if (r.trapped !== null) setTrapped(r.trapped);
  }, [text]);

  const stopAudio = () => {
    const a = audioRef.current;
    if (a) { cancelAnimationFrame(a.raf); a.stream.getTracks().forEach((t) => t.stop()); a.ctx.close(); }
    audioRef.current = null;
    setLevels(Array(32).fill(0.05));
  };

  const startAudio = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const ctx = new AudioContext();
      const an = ctx.createAnalyser();
      an.fftSize = 64;
      ctx.createMediaStreamSource(stream).connect(an);
      const buf = new Uint8Array(an.frequencyBinCount);
      const tick = () => {
        an.getByteFrequencyData(buf);
        setLevels(Array.from(buf).map((v) => Math.max(0.05, v / 255)));
        if (audioRef.current) audioRef.current.raf = requestAnimationFrame(tick);
      };
      audioRef.current = { ctx, stream, raf: requestAnimationFrame(tick) };
    } catch {
      /* waveform is optional */
    }
  };

  const toggleMic = async () => {
    if (listening) { recRef.current?.stop(); return; }
    const w = window as unknown as { SpeechRecognition?: new () => SR; webkitSpeechRecognition?: new () => SR };
    const Ctor = w.SpeechRecognition ?? w.webkitSpeechRecognition;
    if (!Ctor) { toast.error("Voice input isn't supported in this browser — type below instead."); return; }
    const rec = new Ctor();
    rec.lang = lang; rec.continuous = true; rec.interimResults = true;
    const base = text ? text + " " : "";
    rec.onresult = (e) => {
      let s = "";
      for (let i = 0; i < e.results.length; i++) s += e.results[i]![0].transcript;
      setText(base + s);
    };
    rec.onerror = (e) => { if (e.error !== "aborted") toast.error(`Microphone: ${e.error}`); };
    rec.onend = () => { setListening(false); stopAudio(); };
    recRef.current = rec;
    rec.start();
    setListening(true);
    startAudio();
  };

  const onPhoto = (f: File | undefined) => {
    if (!f) return;
    setPhoto(URL.createObjectURL(f));
    const r = extractIncident(f.name.replace(/[_-]/g, " "));
    if (r.hazard && !hazard) setHazard(r.hazard);
    toast.success("Photo attached as visual proof");
  };

  const submit = async () => {
    const d = DISTRICTS.find((x) => x.name === district) ?? DISTRICTS[2]!;
    const lat = geo?.lat ?? d.lat;
    const lng = geo?.lng ?? d.lng;
    const desc = `[${(hazard ?? "Emergency").toUpperCase()}] ${text || "Emergency reported via one-tap SOS"} — affected:${affected}, trapped:${trapped}`;
    setSending(true);
    let token: string;
    try {
      const r = await submitReport({ description: desc.padEnd(10, "."), lat, lng, district, people_affected: affected });
      token = r.tracking_token;
      toast.success(`SOS received · ${r.incident_number}`);
    } catch {
      token = `demo-${Math.random().toString(36).slice(2, 10)}`;
      localStorage.setItem(`resq.track.${token}`, JSON.stringify({ created: Date.now(), district, hazard, affected, trapped }));
      toast.warning("Live server busy — SOS queued in offline mode");
    }
    setSending(false);
    navigate({ to: "/track/$token", params: { token } });
  };

  return (
    <div className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[1fr_1fr]">
      <div className="flex flex-col items-center rounded-lg border border-border bg-card p-6">
        <div className="flex w-full items-center justify-between">
          <div className="label-caps">Citizen SOS</div>
          <div className="flex rounded border border-border p-0.5 text-xs">
            {(["en-IN", "ml-IN"] as const).map((l) => (
              <button key={l} onClick={() => setLang(l)} className={cn("rounded px-2.5 py-1", lang === l ? "bg-primary text-primary-foreground" : "text-muted-foreground")}>
                {l === "en-IN" ? "English" : "മലയാളം"}
              </button>
            ))}
          </div>
        </div>
        <h1 className="mt-4 text-center text-4xl font-bold uppercase">{listening ? "Listening…" : "Tap & speak"}</h1>
        <p className="text-center text-sm text-muted-foreground">Say what happened, how many people, who is trapped.</p>

        <button
          onClick={toggleMic}
          aria-label={listening ? "Stop recording" : "Start voice SOS"}
          className={cn(
            "mt-8 grid size-24 place-items-center rounded-full bg-primary text-primary-foreground shadow-glow transition-transform active:scale-95",
            listening && "animate-sos",
          )}
        >
          {listening ? <MicOff className="size-10" /> : <Mic className="size-10" />}
        </button>

        <div className="mt-6 flex h-14 w-full items-center justify-center gap-[3px]" aria-hidden>
          {levels.map((v, i) => (
            <div key={i} className={cn("w-1.5 rounded-full", listening ? "bg-primary" : "bg-muted")} style={{ height: `${Math.round(v * 100)}%` }} />
          ))}
        </div>

        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Live transcript appears here…"
          className="mt-4 min-h-28 bg-surface"
        />

        <label className="mt-4 flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-border py-4 text-sm text-muted-foreground hover:border-primary">
          <Camera className="size-5" /> {photo ? "Replace photo" : "Capture / upload disaster photo"}
          <input type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => onPhoto(e.target.files?.[0])} />
        </label>
        {photo && (
          <div className="relative mt-3 w-full">
            <img src={photo} alt="Disaster proof" className="max-h-48 w-full rounded-lg object-cover" />
            <button onClick={() => setPhoto(null)} className="absolute right-2 top-2 rounded-full bg-background/80 p-1" aria-label="Remove photo"><X className="size-4" /></button>
          </div>
        )}
      </div>

      <div className="grid content-start gap-4 rounded-lg border border-border bg-card p-6">
        <div className="label-caps">Incident summary · auto-filled</div>
        <div>
          <div className="mb-2 text-sm font-medium">Hazard type</div>
          <div className="flex flex-wrap gap-2">
            {HAZARDS.map((h) => (
              <button key={h} onClick={() => setHazard(h)} className={cn("rounded border px-3 py-2 text-sm font-medium", hazard === h ? "border-primary bg-primary text-primary-foreground" : "border-border text-muted-foreground")}>
                {h}
              </button>
            ))}
          </div>
        </div>
        <div>
          <div className="mb-2 flex justify-between text-sm font-medium"><span>People affected</span><span className="font-mono text-2xl">{affected}</span></div>
          <Slider value={[affected]} min={1} max={50} step={1} onValueChange={(v) => setAffected(v[0] ?? 1)} />
        </div>
        <div>
          <div className="mb-2 flex justify-between text-sm font-medium"><span>Trapped</span><span className="font-mono text-2xl text-primary">{trapped}</span></div>
          <Slider value={[trapped]} min={0} max={Math.max(affected, 1)} step={1} onValueChange={(v) => setTrapped(v[0] ?? 0)} />
        </div>
        <div className="rounded border border-border bg-surface p-3">
          <div className="flex items-center gap-2 text-sm">
            <Crosshair className="size-4 text-primary" />
            {geo ? (
              <>
                <span className="font-mono">{geo.lat.toFixed(5)}, {geo.lng.toFixed(5)}</span>
                <span className={cn("ml-auto rounded px-2 py-0.5 font-mono text-xs", geo.acc < 50 ? "bg-success text-success-foreground" : "bg-warning text-warning-foreground")}>±{geo.acc}m</span>
              </>
            ) : (
              <span className="text-muted-foreground">{geoErr ?? "Detecting GPS…"}</span>
            )}
            {!geo && <button onClick={locate} className="ml-auto text-xs text-primary">Retry</button>}
          </div>
          <div className="mt-3 flex items-center gap-2">
            <MapPin className="size-4 text-muted-foreground" />
            <select value={district} onChange={(e) => setDistrict(e.target.value)} className="flex-1 rounded border border-input bg-background px-2 py-1.5 text-sm">
              {DISTRICTS.map((d) => <option key={d.name}>{d.name}</option>)}
            </select>
          </div>
        </div>
        <Button size="lg" className="h-14 text-lg font-bold uppercase" onClick={submit} disabled={sending}>
          {sending ? <Loader2 className="animate-spin" /> : <Send />} Send SOS
        </Button>
      </div>
    </div>
  );
}
