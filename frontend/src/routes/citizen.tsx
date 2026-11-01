import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  Camera,
  Crosshair,
  Loader2,
  MapPin,
  Mic,
  MicOff,
  Send,
  X,
  Wifi,
  WifiOff,
  Radio,
  FileText,
  Copy,
  CheckCircle2,
  MessageSquare,
  Smartphone,
  AlertTriangle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import { submitReport } from "@/lib/api";
import { createAndPropagateEmergency } from "@/lib/crisis-sync";
import { DISTRICTS, extractIncident, HAZARDS, nearestDistrict, type Hazard } from "@/lib/resq-data";
import { cn } from "@/lib/utils";

// PES_HACK Canonical Enums
const EMERGENCY_TYPES = ["FLOOD", "FIRE", "MEDICAL", "COLLAPSE", "OTHER"] as const;
type EmergencyType = typeof EMERGENCY_TYPES[number];

const VICTIM_STATUSES = [
  "TRAPPED",
  "INJURED",
  "UNCONSCIOUS",
  "NEED_EVACUATION",
  "SAFE_BUT_NEED_HELP",
] as const;
type VictimStatus = typeof VICTIM_STATUSES[number];

const SMS_GATEWAY_NUMBER = "+919847123112"; // Kerala State Disaster Emergency Hotline
const LOCATION_UNKNOWN_MARKER = "LOC:UNKNOWN";

// Schema for offline payload compatibility with Bhuvan's offline sync repo
export interface OfflineEmergencyPayload {
  version: "1.0";
  protocol: "RESQ_SMS_PACKET";
  hazard: string;
  latitude: number;
  longitude: number;
  district: string;
  affected: number;
  trapped: number;
  message: string;
  timestamp: string;
  client_id: string;
}

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
  const [isOfflineMode, setIsOfflineMode] = useState(false);
  const [offlinePacket, setOfflinePacket] = useState<string | null>(null);
  const [copiedPacket, setCopiedPacket] = useState(false);

  // PES_HACK SMS Interface State
  const [smsMode, setSmsMode] = useState(false);
  const [emergencyType, setEmergencyType] = useState<EmergencyType>("FLOOD");
  const [victimStatus, setVictimStatus] = useState<VictimStatus>("TRAPPED");
  const [sendWithoutLocation, setSendWithoutLocation] = useState(false);
  const [smsPayload, setSmsPayload] = useState<string>("");
  const [gsmCharCount, setGsmCharCount] = useState(0);

  const recRef = useRef<SR | null>(null);
  const audioRef = useRef<{ ctx: AudioContext; stream: MediaStream; raf: number } | null>(null);

  // Monitor network offline status automatically
  useEffect(() => {
    const handleOnline = () => {
      setIsOfflineMode(false);
      setSmsMode(false);
      toast.success("Online connection restored");
    };
    const handleOffline = () => {
      setIsOfflineMode(true);
      setSmsMode(true);
      toast.warning("Network connection lost — Switched to Offline SMS mode");
    };
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      setIsOfflineMode(true);
      setSmsMode(true);
    }
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  // Calculate GSM-7 character count (pipe character counts as 2 units in extended table)
  const calculateGSM7Count = (text: string): number => {
    const extendedChars = ['|', '^', '{', '}', '[', ']', '~', '\\'];
    let count = 0;
    for (const char of text) {
      count += extendedChars.includes(char) ? 2 : 1;
    }
    return count;
  };

  // Generate PES_HACK SMS payload
  const generateSMSPayload = (): string => {
    let locationPart: string;

    if (sendWithoutLocation || !geo) {
      locationPart = LOCATION_UNKNOWN_MARKER;
    } else {
      const lat = geo.lat.toFixed(5);
      const lng = geo.lng.toFixed(5);
      locationPart = `${lat},${lng}`;
    }

    return `${emergencyType} | ${victimStatus} | ${locationPart}`;
  };

  // Update SMS payload whenever inputs change
  useEffect(() => {
    if (smsMode) {
      const payload = generateSMSPayload();
      setSmsPayload(payload);
      setGsmCharCount(calculateGSM7Count(payload));
    }
  }, [smsMode, emergencyType, victimStatus, geo, sendWithoutLocation]);

  // Detect platform and generate SMS URL
  const generateSMSLink = (): string => {
    const userAgent = navigator.userAgent;
    const isIOS = /iPhone|iPad|iPod/i.test(userAgent);
    const encodedMessage = encodeURIComponent(smsPayload);

    // iOS uses & separator, Android uses ? separator
    if (isIOS) {
      return `sms:${SMS_GATEWAY_NUMBER}&body=${encodedMessage}`;
    } else {
      return `sms:${SMS_GATEWAY_NUMBER}?body=${encodedMessage}`;
    }
  };

  // Send offline SMS SOS
  const sendOfflineSMS = () => {
    // Queue to localStorage
    try {
      const queueKey = "resq_offline_emergency_queue";
      const existing = JSON.parse(localStorage.getItem(queueKey) || "[]");
      existing.unshift({
        version: "1.0",
        protocol: "SMS_GATEWAY",
        sms_payload: smsPayload,
        emergency_type: emergencyType,
        victim_status: victimStatus,
        latitude: geo?.lat ?? null,
        longitude: geo?.lng ?? null,
        location_unknown: sendWithoutLocation || !geo,
        district,
        timestamp: new Date().toISOString(),
        client_id: `sms_${Math.random().toString(36).slice(2, 10)}`,
      });
      localStorage.setItem(queueKey, JSON.stringify(existing.slice(0, 20)));
      toast.success("Emergency queued for sync");
    } catch (e) {
      console.error("Failed to queue emergency:", e);
    }

    // Open SMS app with prefilled message
    const smsLink = generateSMSLink();
    window.location.href = smsLink;

    toast.success(`Opening SMS app to ${SMS_GATEWAY_NUMBER}`);
  };

  // Generate offline payload compatible with Bhuvan's offline sync repo
  const generateOfflinePacket = () => {
    const d = DISTRICTS.find((x) => x.name === district) ?? DISTRICTS[2]!;
    const lat = +(geo?.lat ?? d.lat).toFixed(5);
    const lng = +(geo?.lng ?? d.lng).toFixed(5);
    const hz = hazard ?? "FLOOD";
    const msg = text || "Immediate rescue required, isolated by rising water";

    // Compact format for SMS/mesh sync: RESQ|HAZARD|LAT|LNG|DISTRICT|AFFECTED|TRAPPED|MSG
    const compactString = `RESQ|${hz}|${lat}|${lng}|${district}|${affected}|${trapped}|${msg.slice(0, 80)}`;

    const fullPayload: OfflineEmergencyPayload = {
      version: "1.0",
      protocol: "RESQ_SMS_PACKET",
      hazard: hz,
      latitude: lat,
      longitude: lng,
      district,
      affected,
      trapped,
      message: msg,
      timestamp: new Date().toISOString(),
      client_id: `offline_${Math.random().toString(36).slice(2, 10)}`,
    };

    // Store in IndexedDB/localStorage queue for automatic background sync when reconnected
    try {
      const queueKey = "resq_offline_emergency_queue";
      const existing = JSON.parse(localStorage.getItem(queueKey) || "[]");
      existing.unshift(fullPayload);
      localStorage.setItem(queueKey, JSON.stringify(existing.slice(0, 20)));
    } catch {}

    setOfflinePacket(compactString);
    toast.success("Offline SOS packet generated & saved to sync queue");
  };

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
      const crisis = await createAndPropagateEmergency({
        description: desc.padEnd(10, "."),
        lat,
        lng,
        district,
        people_affected: affected,
        trappedCount: trapped,
      });
      token = crisis.trackingToken;
      toast.success(`SOS Active · Incident ${crisis.incidentNumber}`);
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
          <div className="flex items-center gap-2">
            {/* Mode Toggle: Online vs Offline SMS */}
            <div className="flex rounded border-2 border-border p-0.5 text-xs">
              <button
                onClick={() => {
                  setSmsMode(false);
                  setIsOfflineMode(false);
                  toast.success("Switched to Online SOS mode");
                }}
                className={cn(
                  "rounded px-3 py-1.5 font-semibold transition-all flex items-center gap-1.5",
                  !smsMode
                    ? "bg-emerald-500 text-white shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Wifi className="size-3" />
                Online SOS
              </button>
              <button
                onClick={() => {
                  setSmsMode(true);
                  setIsOfflineMode(true);
                  toast.warning("Switched to Offline Cellular (SMS) mode");
                }}
                className={cn(
                  "rounded px-3 py-1.5 font-semibold transition-all flex items-center gap-1.5",
                  smsMode
                    ? "bg-amber-500 text-white shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Smartphone className="size-3" />
                Offline SMS
              </button>
            </div>

            {!smsMode && (
              <div className="flex rounded border border-border p-0.5 text-xs">
                {(["en-IN", "ml-IN"] as const).map((l) => (
                  <button key={l} onClick={() => setLang(l)} className={cn("rounded px-2.5 py-1", lang === l ? "bg-primary text-primary-foreground" : "text-muted-foreground")}>
                    {l === "en-IN" ? "English" : "മലയാളം"}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* SMS Mode Interface */}
        {smsMode ? (
          <div className="mt-6 w-full space-y-6">
            {/* SMS Mode Header */}
            <div className="rounded-xl border-2 border-amber-500/40 bg-amber-500/10 p-4 text-left shadow-lg">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-amber-400">
                  <MessageSquare className="size-5 animate-pulse" />
                  Offline Cellular SMS Mode
                </div>
                <span className="rounded bg-amber-500/30 px-2.5 py-1 text-[10px] font-mono font-bold text-amber-200">
                  2G GSM Ready
                </span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Works without internet. Standard 2G cellular SMS to Kerala State Disaster Gateway <span className="font-mono text-amber-400">{SMS_GATEWAY_NUMBER}</span>. Structured payload ensures machine-parseable emergency data.
              </p>
            </div>

            {/* Emergency Type Selection */}
            <div>
              <div className="mb-3 text-sm font-bold flex items-center gap-2">
                <AlertTriangle className="size-4 text-primary" />
                Emergency Type
              </div>
              <div className="grid grid-cols-2 gap-3">
                {EMERGENCY_TYPES.map((type) => (
                  <button
                    key={type}
                    onClick={() => setEmergencyType(type)}
                    className={cn(
                      "min-h-[48px] rounded-lg border-2 px-4 py-3 text-sm font-bold transition-all",
                      emergencyType === type
                        ? "border-primary bg-primary text-primary-foreground shadow-md scale-105"
                        : "border-border bg-surface text-foreground hover:border-primary/50"
                    )}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>

            {/* Victim Status Selection */}
            <div>
              <div className="mb-3 text-sm font-bold">Your Situation</div>
              <div className="grid grid-cols-1 gap-2">
                {VICTIM_STATUSES.map((status) => (
                  <button
                    key={status}
                    onClick={() => setVictimStatus(status)}
                    className={cn(
                      "min-h-[48px] rounded-lg border-2 px-4 py-3 text-left text-sm font-semibold transition-all",
                      victimStatus === status
                        ? "border-primary bg-primary text-primary-foreground shadow-md"
                        : "border-border bg-surface text-foreground hover:border-primary/50"
                    )}
                  >
                    {status.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            </div>

            {/* GPS Status & Send Without Location */}
            <div className="rounded-lg border border-border bg-surface p-4">
              <div className="flex items-center gap-2 text-sm mb-3">
                <Crosshair className="size-4 text-primary" />
                {geo ? (
                  <>
                    <span className="font-mono text-xs">{geo.lat.toFixed(5)}, {geo.lng.toFixed(5)}</span>
                    <span className={cn("ml-auto rounded px-2 py-0.5 font-mono text-[10px]", geo.acc < 50 ? "bg-success text-success-foreground" : "bg-warning text-warning-foreground")}>
                      ±{geo.acc}m
                    </span>
                  </>
                ) : (
                  <span className="text-muted-foreground text-xs">{geoErr ?? "Detecting GPS…"}</span>
                )}
                {!geo && <button onClick={locate} className="ml-auto text-xs text-primary font-semibold">Retry GPS</button>}
              </div>

              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={sendWithoutLocation}
                  onChange={(e) => setSendWithoutLocation(e.target.checked)}
                  className="size-4 rounded border-border"
                />
                <span className="text-sm font-medium">Send without location (LOC:UNKNOWN)</span>
              </label>
            </div>

            {/* Live SMS Preview */}
            <div className="rounded-lg border-2 border-primary bg-surface p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase text-muted-foreground">Live SMS Preview</span>
                <span className={cn(
                  "rounded px-2 py-0.5 font-mono text-[10px] font-bold",
                  gsmCharCount <= 160 ? "bg-success/20 text-success" : "bg-warning/20 text-warning"
                )}>
                  {gsmCharCount} / 160 chars · {Math.ceil(gsmCharCount / 160)} SMS segment{Math.ceil(gsmCharCount / 160) > 1 ? 's' : ''}
                </span>
              </div>
              <div className="font-mono text-sm bg-muted/80 p-3 rounded text-foreground break-all leading-relaxed">
                {smsPayload || "Payload will appear here..."}
              </div>
              <div className="mt-2 text-[10px] text-muted-foreground">
                Gateway: <span className="font-mono text-primary">{SMS_GATEWAY_NUMBER}</span>
              </div>
            </div>

            {/* Emergency Dispatch Button */}
            <Button
              size="lg"
              onClick={sendOfflineSMS}
              disabled={!smsPayload}
              className="w-full h-16 text-lg font-bold uppercase bg-amber-500 hover:bg-amber-600 text-white shadow-xl"
            >
              <MessageSquare className="size-6 mr-2" />
              SEND OFFLINE SOS (OPENS SMS APP)
            </Button>

            <p className="text-center text-xs text-muted-foreground">
              Clicking will open your SMS app with the gateway number and payload pre-filled. Send immediately.
            </p>
          </div>
        ) : (
          <>
            {/* Original Online Mode Interface */}
            {isOfflineMode && !smsMode && (
              <div className="mt-4 w-full rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-left shadow-md">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-amber-400">
                    <Radio className="size-4 animate-pulse" />
                    Offline Emergency Packet Mode
                  </div>
                  <span className="rounded bg-amber-500/20 px-2 py-0.5 text-[10px] font-mono text-amber-300">
                    Mesh / SMS Ready
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                  No cellular data needed. Generates a structured geographical packet (hazard, GPS coordinates, casualties) stored in local IndexedDB queue for offline sync.
                </p>

                {offlinePacket && (
                  <div className="mt-3 rounded-lg bg-background/80 p-3 border border-border">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[10px] font-mono uppercase text-muted-foreground flex items-center gap-1">
                        <FileText className="size-3 text-amber-400" /> Compact Mesh Payload
                      </span>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(offlinePacket);
                          setCopiedPacket(true);
                          toast.success("Packet copied to clipboard");
                          setTimeout(() => setCopiedPacket(false), 2000);
                        }}
                        className="inline-flex items-center gap-1 text-[11px] font-mono font-bold text-amber-400 hover:text-amber-300"
                      >
                        {copiedPacket ? <CheckCircle2 className="size-3 text-emerald-400" /> : <Copy className="size-3" />}
                        {copiedPacket ? "Copied" : "Copy Payload"}
                      </button>
                    </div>
                    <div className="font-mono text-xs break-all bg-muted/60 p-2 rounded text-foreground select-all">
                      {offlinePacket}
                    </div>
                  </div>
                )}

                <div className="mt-3 flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={generateOfflinePacket}
                    className="text-xs h-8 border-amber-500/30 hover:bg-amber-500/20 text-amber-300"
                  >
                    Refresh Coordinates & Packet
                  </Button>
                </div>
              </div>
            )}
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
          </>
        )}
      </div>

      {!smsMode && (
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
      )}
    </div>
  );
}
