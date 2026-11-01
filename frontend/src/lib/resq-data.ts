// Kerala reference data, extraction heuristics, and the simulated operations feed
// used whenever the live backend is unavailable or requires a sign-in.

export const DISTRICTS: { name: string; lat: number; lng: number }[] = [
  { name: "Kasaragod", lat: 12.5, lng: 75.0 },
  { name: "Kannur", lat: 11.87, lng: 75.37 },
  { name: "Wayanad", lat: 11.68, lng: 76.13 },
  { name: "Kozhikode", lat: 11.25, lng: 75.78 },
  { name: "Malappuram", lat: 11.07, lng: 76.07 },
  { name: "Palakkad", lat: 10.78, lng: 76.65 },
  { name: "Thrissur", lat: 10.52, lng: 76.21 },
  { name: "Ernakulam", lat: 9.98, lng: 76.28 },
  { name: "Idukki", lat: 9.85, lng: 76.97 },
  { name: "Kottayam", lat: 9.59, lng: 76.52 },
  { name: "Alappuzha", lat: 9.5, lng: 76.34 },
  { name: "Pathanamthitta", lat: 9.26, lng: 76.78 },
  { name: "Kollam", lat: 8.89, lng: 76.61 },
  { name: "Thiruvananthapuram", lat: 8.52, lng: 76.94 },
];

export function nearestDistrict(lat: number, lng: number) {
  let best = DISTRICTS[0]!;
  let d = Infinity;
  for (const x of DISTRICTS) {
    const dd = (x.lat - lat) ** 2 + (x.lng - lng) ** 2;
    if (dd < d) { d = dd; best = x; }
  }
  return best.name;
}

export type Hazard = "Flood" | "Landslide" | "Fire" | "Collapse" | "Medical";
export const HAZARDS: Hazard[] = ["Flood", "Landslide", "Fire", "Collapse", "Medical"];

const HAZARD_WORDS: Record<Hazard, string[]> = {
  Flood: ["flood", "water", "river", "submerged", "rain", "വെള്ളം", "പ്രളയം"],
  Landslide: ["landslide", "mud", "slide", "hill", "debris", "ഉരുൾ", "മണ്ണിടിച്ചിൽ"],
  Fire: ["fire", "smoke", "burn", "തീ"],
  Collapse: ["collapse", "building", "roof", "wall", "trapped under", "തകർന്നു"],
  Medical: ["injured", "bleeding", "unconscious", "heart", "pregnant", "ambulance", "പരിക്ക്"],
};

const NUM_WORDS: Record<string, number> = {
  one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  twelve: 12, fifteen: 15, twenty: 20,
};

function findCount(text: string, keys: string[]): number | null {
  const t = text.toLowerCase();
  for (const k of keys) {
    const re = new RegExp(`(\\d+|${Object.keys(NUM_WORDS).join("|")})\\s+(?:\\w+\\s+){0,2}${k}`);
    const m = t.match(re);
    if (m && m[1]) return /\d/.test(m[1]) ? parseInt(m[1]) : (NUM_WORDS[m[1]] ?? null);
  }
  return null;
}

export function extractIncident(text: string, photoTag?: Hazard | null) {
  const t = text.toLowerCase();
  let hazard: Hazard | null = photoTag ?? null;
  let bestScore = 0;
  for (const h of HAZARDS) {
    const s = HAZARD_WORDS[h].filter((w) => t.includes(w)).length;
    if (s > bestScore) { bestScore = s; hazard = h; }
  }
  const affected = findCount(t, ["people", "persons", "family", "members", "children", "of us"]);
  const trapped = findCount(t, ["trapped", "stuck", "stranded"]);
  return { hazard, affected, trapped };
}

export type Triage = "RED" | "YELLOW" | "GREEN";

export const UNITS = [
  { id: "SDRF-WR-02", name: "Kerala SDRF Water Rescue Unit 02", type: "Boat", officer: "Insp. Anil Kumar", district: "Wayanad" },
  { id: "ALS-114", name: "ALS Ambulance KL-12-114", type: "Ambulance", officer: "Dr. Reshma Nair", district: "Wayanad" },
  { id: "NDRF-04", name: "NDRF 4th Battalion Team B", type: "Rescue", officer: "Asst. Cmdt. R. Menon", district: "Idukki" },
  { id: "FRS-KZD", name: "Fire & Rescue Kozhikode", type: "Fire", officer: "Stn. Officer P. Das", district: "Kozhikode" },
  { id: "AIR-17", name: "IAF Mi-17 Air Evac", type: "Air", officer: "Wg Cdr S. Pillai", district: "Ernakulam" },
  { id: "VOL-ALP", name: "Alappuzha Fishermen Volunteers", type: "Boat", officer: "Joseph Varghese", district: "Alappuzha" },
];

export type FeedItem = { t: string; agent: string; msg: string; level: "info" | "warn" | "crit" };

const AGENT_LINES: Omit<FeedItem, "t">[] = [
  { agent: "INTEL", msg: "Parsed SOS #KL-WYD-0419 → hazard=FLOOD, trapped=4, conf=0.91", level: "info" },
  { agent: "TRIAGE", msg: "SALT score: 2 victims RED (immediate), 3 YELLOW", level: "crit" },
  { agent: "MATCH", msg: "Allocated SDRF-WR-02 (boat, 1.4 km) to Meppadi cluster", level: "info" },
  { agent: "ROUTE", msg: "NH-766 Thamarassery ghat blocked — rerouting via Kuttiady", level: "warn" },
  { agent: "HOSP", msg: "Reserved ICU bed @ Govt Medical College Kozhikode (30-min hold)", level: "info" },
  { agent: "MARKET", msg: "O-neg deficit 6 units → requested from KSBTC Ernakulam", level: "warn" },
  { agent: "DEDUP", msg: "Merged 3 duplicate reports near Chooralmala bridge", level: "info" },
  { agent: "AUDIT", msg: "Citizen confirmed rescue for #KL-ALP-0388 — ledger sealed", level: "info" },
  { agent: "TRIAGE", msg: "Landslide risk ↑ Mundakkai: rainfall 214mm/24h", level: "crit" },
  { agent: "CONT", msg: "Offline sync: 12 field events reconciled from SDRF-WR-02", level: "info" },
  { agent: "MATCH", msg: "Diverted ALS-114 → District Hospital Mananthavady (ICU saturated)", level: "warn" },
];

export function nextFeed(i: number): FeedItem {
  const base = AGENT_LINES[i % AGENT_LINES.length]!;
  return { ...base, t: new Date().toLocaleTimeString("en-GB") };
}

export type MapPoint = { id: string; lat: number; lng: number; kind: "incident" | "unit"; severity?: Triage; label: string };

export const SEED_INCIDENTS: MapPoint[] = [
  { id: "i1", lat: 11.53, lng: 76.15, kind: "incident", severity: "RED", label: "Mundakkai landslide" },
  { id: "i2", lat: 11.56, lng: 76.13, kind: "incident", severity: "RED", label: "Chooralmala flood" },
  { id: "i3", lat: 11.79, lng: 76.0, kind: "incident", severity: "YELLOW", label: "Mananthavady" },
  { id: "i4", lat: 9.48, lng: 76.38, kind: "incident", severity: "YELLOW", label: "Kuttanad flooding" },
  { id: "i5", lat: 9.86, lng: 76.97, kind: "incident", severity: "RED", label: "Idukki slide" },
  { id: "i6", lat: 10.15, lng: 76.4, kind: "incident", severity: "GREEN", label: "Aluva riverbank" },
  { id: "i7", lat: 11.3, lng: 75.85, kind: "incident", severity: "GREEN", label: "Kozhikode urban" },
  { id: "i8", lat: 9.3, lng: 76.65, kind: "incident", severity: "YELLOW", label: "Pathanamthitta" },
];

export const SEED_UNITS: MapPoint[] = [
  { id: "u1", lat: 11.6, lng: 76.2, kind: "unit", label: "SDRF-WR-02" },
  { id: "u2", lat: 11.4, lng: 76.0, kind: "unit", label: "ALS-114" },
  { id: "u3", lat: 9.95, lng: 76.85, kind: "unit", label: "NDRF-04" },
  { id: "u4", lat: 9.55, lng: 76.32, kind: "unit", label: "VOL-ALP" },
  { id: "u5", lat: 10.1, lng: 76.3, kind: "unit", label: "AIR-17" },
];

export const TRACK_STAGES = ["Received", "Triaged", "Dispatched", "En Route", "Rescued"] as const;

export function stageFromStatus(status: string): number {
  const s = status.toUpperCase();
  if (["RESOLVED", "CLOSED", "COMPLETED"].includes(s)) return 4;
  if (["ACTIVE_RESPONSE", "EN_ROUTE", "ON_SCENE"].includes(s)) return 3;
  if (["DISPATCHING", "ASSIGNED", "ACCEPTED"].includes(s)) return 2;
  if (["TRIAGED", "ANALYZING"].includes(s)) return 1;
  return 0;
}
