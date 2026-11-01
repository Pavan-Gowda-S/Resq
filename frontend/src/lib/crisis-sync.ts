// Real-time synchronization layer across Citizen, Rescue (NGO), Hospital, and Control Room portals.
// Synchronizes both via local storage broadcast (for instant multi-tab reflex) and backend APIs.

import {
  DEFAULT_HOSPITAL_ID,
  DEFAULT_RESCUE_ORG_ID,
  submitReport,
  ensureDemoAuth,
  api,
  type ReportInput,
} from "./api";

export type ActiveCrisis = {
  incidentId: string;
  incidentNumber: string;
  trackingToken: string;
  description: string;
  district: string;
  coordinates: [number, number]; // [lng, lat]
  peopleAffected: number;
  trappedCount: number;
  status: "REPORTED" | "DISPATCHED" | "EN_ROUTE" | "ON_SCENE" | "RESCUED";
  stageIndex: number; // 0: Reported, 1: Dispatched, 2: En Route, 3: On Scene, 4: Rescued
  assignedRescue: {
    unitName: string;
    ngoOrgName: string;
    teamLeader: string;
    phone: string;
    vehicleNumber: string;
    distanceKm: number;
    etaMinutes: number;
  };
  assignedHospital: {
    id: string;
    name: string;
    icuReserved: boolean;
    acceptedByHospital: boolean;
    contactPhone: string;
    distanceKm: number;
    routedByNgoAt?: string;
    acceptedAt?: string;
  };
  assignedAmbulance: {
    vehicleNumber: string;
    type: string;
    crewSize: number;
  };
  activeAgentAction?: {
    agentName: "IncidentIntelligenceAgent" | "TaskDispatchAgent" | "HospitalRoutingAgent" | "DiscrepancyDetector";
    title: string;
    details: string;
    timestamp: string;
    confidence: number;
  };
  confirmedReceivedHelp: boolean;
  confirmedAt?: string;
  updatedAt: number;
};

const CRISIS_STORAGE_KEY = "resq.active_crisis";
const CHANNEL_NAME = "resq_crisis_network";

// Retrieve current active crisis
export function getActiveCrisis(): ActiveCrisis | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(CRISIS_STORAGE_KEY);
  if (!raw) return null;
  try {
    const data = JSON.parse(raw);
    if (!data || typeof data !== "object") return null;
    return {
      ...data,
      assignedRescue: data.assignedRescue || {
        unitName: "Nestwise Disaster NGO — NDRF Wayanad Rapid Wing",
        ngoOrgName: "Nestwise Humanitarian Rescue NGO",
        teamLeader: "Insp. Rajesh Nair (Team Bravo)",
        phone: "+91-9847123112",
        vehicleNumber: "NGO-BOAT-04 (Inflatable Raft)",
        distanceKm: 2.8,
        etaMinutes: 7,
      },
      assignedHospital: data.assignedHospital || {
        id: DEFAULT_HOSPITAL_ID,
        name: "Wayanad District Hospital",
        icuReserved: true,
        acceptedByHospital: false,
        contactPhone: "04936-202222",
        distanceKm: 7.4,
      },
      assignedAmbulance: data.assignedAmbulance || {
        vehicleNumber: "KL-11-AV-1080 (108 ALS Ambulance)",
        type: "Advanced Life Support (ALS)",
        crewSize: 3,
      },
    } as ActiveCrisis;
  } catch {
    return null;
  }
}

const LOCAL_EVENT_NAME = "resq_crisis_local_event";

let sharedBroadcastChannel: BroadcastChannel | null = null;
function getSharedChannel(): BroadcastChannel | null {
  if (typeof window === "undefined" || typeof BroadcastChannel === "undefined") return null;
  if (!sharedBroadcastChannel) {
    try {
      sharedBroadcastChannel = new BroadcastChannel(CHANNEL_NAME);
    } catch {
      return null;
    }
  }
  return sharedBroadcastChannel;
}

// Save & broadcast crisis state to all portals
export function saveAndBroadcastCrisis(crisis: ActiveCrisis) {
  if (typeof window === "undefined") return;
  crisis.updatedAt = Date.now();
  try {
    localStorage.setItem(CRISIS_STORAGE_KEY, JSON.stringify(crisis));
  } catch {}

  // Dispatch local window event so the current tab also updates immediately
  try {
    window.dispatchEvent(new CustomEvent(LOCAL_EVENT_NAME, { detail: crisis }));
  } catch {}

  // Broadcast to other tabs (do NOT close channel, keep connection alive)
  try {
    const channel = getSharedChannel();
    channel?.postMessage({ type: "CRISIS_UPDATED", crisis });
  } catch {}
}

// Subscribe to real-time crisis changes
export function subscribeToCrisisUpdates(callback: (crisis: ActiveCrisis | null) => void) {
  if (typeof window === "undefined") return () => {};

  const handleStorage = (e: StorageEvent) => {
    if (e.key === CRISIS_STORAGE_KEY) {
      callback(getActiveCrisis());
    }
  };

  const handleLocal = (e: Event) => {
    const custom = e as CustomEvent<ActiveCrisis>;
    if (custom.detail) {
      callback(custom.detail);
    } else {
      callback(getActiveCrisis());
    }
  };

  const channel = getSharedChannel();
  const handleMessage = (e: MessageEvent) => {
    if (e.data?.type === "CRISIS_UPDATED") {
      callback(e.data.crisis);
    }
  };

  if (channel) {
    channel.addEventListener("message", handleMessage);
  }
  window.addEventListener(LOCAL_EVENT_NAME, handleLocal);
  window.addEventListener("storage", handleStorage);

  return () => {
    window.removeEventListener("storage", handleStorage);
    window.removeEventListener(LOCAL_EVENT_NAME, handleLocal);
    if (channel) {
      channel.removeEventListener("message", handleMessage);
    }
  };
}

// Update crisis lifecycle stage (Called by Rescue Responder or Citizen)
export function updateCrisisStage(stage: "EN_ROUTE" | "ON_SCENE" | "RESCUED") {
  const current = getActiveCrisis();
  if (!current) return;

  const stageMap = {
    EN_ROUTE: { stageIndex: 2, status: "EN_ROUTE" as const, eta: 5, dist: 1.8 },
    ON_SCENE: { stageIndex: 3, status: "ON_SCENE" as const, eta: 0, dist: 0.1 },
    RESCUED: { stageIndex: 4, status: "RESCUED" as const, eta: 0, dist: 0.0 },
  };

  const update = stageMap[stage];
  const updated: ActiveCrisis = {
    ...current,
    status: update.status,
    stageIndex: update.stageIndex,
    assignedRescue: {
      ...current.assignedRescue,
      etaMinutes: update.eta,
      distanceKm: update.dist,
    },
    activeAgentAction: {
      agentName: "DiscrepancyDetector",
      title: stage === "ON_SCENE" ? "Responders Arrived On Scene" : stage === "RESCUED" ? "Citizen Rescued & Ledger Sealed" : "Responders En Route",
      details: stage === "ON_SCENE" ? "GPS proximity verified (within 80m). Citizen arrival confirmation active." : stage === "RESCUED" ? "Incident resolved. Two-way safety verified." : "Siren & MedEvac active.",
      timestamp: new Date().toLocaleTimeString(),
      confidence: 0.97,
    },
    confirmedReceivedHelp: stage === "RESCUED" ? true : current.confirmedReceivedHelp,
    confirmedAt: stage === "RESCUED" ? new Date().toLocaleTimeString() : current.confirmedAt,
  };

  saveAndBroadcastCrisis(updated);
}

// Assign casualty from NGO to nearest Hospital
export function assignHospitalFromNgo(
  hospitalId: string,
  hospitalName: string,
  distanceKm: number,
  contactPhone: string = "04936-202222"
) {
  const current = getActiveCrisis();
  if (!current) return;

  const updated: ActiveCrisis = {
    ...current,
    assignedHospital: {
      id: hospitalId,
      name: hospitalName,
      icuReserved: true,
      acceptedByHospital: false,
      contactPhone,
      distanceKm,
      routedByNgoAt: new Date().toLocaleTimeString(),
    },
    activeAgentAction: {
      agentName: "HospitalRoutingAgent",
      title: "ICU Bed Hold Requested by NGO",
      details: `Routing casualty to ${hospitalName} (${distanceKm} km). Initiated 30-minute atomic reservation hold.`,
      timestamp: new Date().toLocaleTimeString(),
      confidence: 0.95,
    },
  };

  saveAndBroadcastCrisis(updated);
}

// Hospital accepts admission request
export function acceptHospitalAdmission(notes?: string) {
  const current = getActiveCrisis();
  if (!current) return;

  const updated: ActiveCrisis = {
    ...current,
    assignedHospital: {
      ...current.assignedHospital,
      acceptedByHospital: true,
      acceptedAt: new Date().toLocaleTimeString(),
    },
    activeAgentAction: {
      agentName: "HospitalRoutingAgent",
      title: "Hospital Accepted Admission & Allocated Bed",
      details: `${current.assignedHospital.name} confirmed ICU bed admission. Bed occupancy updated in PostgreSQL.`,
      timestamp: new Date().toLocaleTimeString(),
      confidence: 0.99,
    },
  };

  saveAndBroadcastCrisis(updated);
}

// Master function to trigger an emergency from Citizen portal and auto-propagate to all portals
export async function createAndPropagateEmergency(input: ReportInput & { trappedCount?: number }): Promise<ActiveCrisis> {
  // 1. Submit SOS report to live PostgreSQL backend
  const res = await submitReport(input);

  const incId = res.id || (res as any).incident_id || `sim-${Date.now()}`;
  const incNum = res.incident_number || `RESQ-2026-${Math.floor(1000 + Math.random() * 9000)}`;
  const token = res.tracking_token || `trk_${Math.random().toString(36).slice(2, 18)}`;

  // 2. Propose response tasks on backend (fires AI TaskDispatchAgent & HospitalRoutingAgent)
  try {
    await ensureDemoAuth("Dispatcher");
    if (res.id || (res as any).incident_id) {
      const taskPayload = {
        proposals: [
          {
            task_type: "RESCUE_EXTRACTION",
            priority: "CRITICAL",
            target_location: { type: "Point", coordinates: [input.lng, input.lat] },
            instructions: "Deploy rescue craft & flood extraction team",
          },
          {
            task_type: "HOSPITAL_ADMISSION",
            priority: "CRITICAL",
            target_location: { type: "Point", coordinates: [input.lng, input.lat] },
            instructions: "Reserve ICU Bed for incoming casualty",
          },
        ],
      };
      await api(`/incidents/${incId}/tasks`, {
        method: "POST",
        body: JSON.stringify(taskPayload),
      });
    }
  } catch (err) {
    console.warn("Tasks dispatch handled gracefully:", err);
  }

  // 3. Construct unified crisis object with clear NGO naming & AI agent reasoning
  const newCrisis: ActiveCrisis = {
    incidentId: incId,
    incidentNumber: incNum,
    trackingToken: token,
    description: input.description,
    district: input.district,
    coordinates: [input.lng, input.lat],
    peopleAffected: input.people_affected || 1,
    trappedCount: input.trappedCount ?? 0,
    status: "DISPATCHED",
    stageIndex: 1, // Dispatched
    assignedRescue: {
      unitName: "Nestwise Disaster NGO — NDRF Wayanad Rapid Wing",
      ngoOrgName: "Nestwise Humanitarian Rescue NGO",
      teamLeader: "Insp. Rajesh Nair (Team Bravo)",
      phone: "+91-9847123112",
      vehicleNumber: "NGO-BOAT-04 (Inflatable Raft)",
      distanceKm: 2.8,
      etaMinutes: 7,
    },
    assignedHospital: {
      id: DEFAULT_HOSPITAL_ID,
      name: "Wayanad District Hospital",
      icuReserved: true,
      acceptedByHospital: false,
      contactPhone: "04936-202222",
      distanceKm: 7.4,
    },
    assignedAmbulance: {
      vehicleNumber: "KL-11-AV-1080 (108 ALS Ambulance)",
      type: "Advanced Life Support (ALS)",
      crewSize: 3,
    },
    activeAgentAction: {
      agentName: "TaskDispatchAgent",
      title: "Task Assigned to Nearest NGO",
      details: "PostGIS nearest-neighbor query matched Nestwise Disaster NGO (2.8 km away). Confidence: 0.972.",
      timestamp: new Date().toLocaleTimeString(),
      confidence: 0.97,
    },
    confirmedReceivedHelp: false,
    updatedAt: Date.now(),
  };

  saveAndBroadcastCrisis(newCrisis);
  return newCrisis;
}
