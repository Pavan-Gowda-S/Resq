// Client for the RESQ backend (proxied through /api/public/resq to avoid CORS).
export const API_DISPLAY_BASE = "http://127.0.0.1:8000/api/v1";
const PROXY = "/api/public/resq";

const TOKEN_KEY = "resq.token";
const USER_KEY = "resq.user";

export const DEFAULT_HOSPITAL_ID = "1c11ce50-f018-41ee-8765-49cd8577578e"; // Wayanad District Hospital
export const DEFAULT_RESCUE_ORG_ID = "3d8599f7-10a0-46fa-a061-315b3b7a8a8f"; // NDRF Wayanad
export const DEFAULT_CONTROL_ORG_ID = "4a054031-717c-4523-b776-a50fae58354e"; // DEOC

export type SessionUser = {
  id?: string;
  full_name: string;
  email: string;
  role: string;
  organization_id?: string;
  organization_name?: string;
};

export function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): SessionUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as SessionUser) : null;
}

export function setSession(token: string, user: SessionUser) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function ensureDemoAuth(roleLabel: string = "Admin"): Promise<SessionUser> {
  const currentToken = getToken();
  const currentUser = getUser();
  if (currentToken && currentUser) {
    return currentUser;
  }
  try {
    const res = await login("admin@resq.system", "Admin@123456");
    return res;
  } catch (err) {
    console.warn("Auto-login failed, falling back to local demo profile", err);
    const mockUser: SessionUser = {
      full_name: `Dr. Demo (${roleLabel})`,
      email: "admin@resq.system",
      role: "SUPERADMIN",
      organization_id: DEFAULT_HOSPITAL_ID,
      organization_name: "Wayanad District Hospital",
    };
    return mockUser;
  }
}

export async function api<T>(path: string, init: RequestInit = {}, prefix = "api/v1"): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("content-type")) headers.set("content-type", "application/json");
  const token = getToken();
  if (token) headers.set("authorization", `Bearer ${token}`);
  const res = await fetch(`${PROXY}/${prefix}${path}`, { ...init, headers });
  const text = await res.text();
  let data: any = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  // Auto-heal on 401 Unauthorized (e.g. backend tunnel restarted or expired token)
  if (res.status === 401 && !path.includes("/auth/login")) {
    try {
      const loginRes = await fetch(`${PROXY}/api/v1/auth/login`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email: "admin@resq.system", password: "Admin@123456" }),
      });
      if (loginRes.ok) {
        const loginData = await loginRes.json();
        if (loginData.access_token) {
          setSession(loginData.access_token, loginData.user || {
            full_name: "System Administrator",
            email: "admin@resq.system",
            role: "SUPERADMIN",
            organization_id: DEFAULT_HOSPITAL_ID,
          });
          headers.set("authorization", `Bearer ${loginData.access_token}`);
          const retryRes = await fetch(`${PROXY}/${prefix}${path}`, { ...init, headers });
          const retryText = await retryRes.text();
          try {
            return JSON.parse(retryText) as T;
          } catch {
            return retryText as any;
          }
        }
      }
    } catch {
      // Retry failed, fall through to error handling
    }
  }

  if (!res.ok) {
    const detail = data?.detail;
    throw new Error(typeof detail === "string" ? detail : `Request failed (${res.status})`);
  }
  return data as T;
}

export async function checkHealth(): Promise<{ ok: boolean; ms: number }> {
  const t = performance.now();
  try {
    const res = await fetch(`${PROXY}/health`);
    return { ok: res.ok, ms: Math.round(performance.now() - t) };
  } catch {
    return { ok: false, ms: Math.round(performance.now() - t) };
  }
}

export async function login(email: string, password: string) {
  const r = await api<{ access_token: string; user: SessionUser }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setSession(r.access_token, r.user);
  return r.user;
}

// ----------------- Resources & Hospital Capacity -----------------

export type HospitalCapacity = {
  id: string;
  organization_id: string;
  total_emergency_beds: number;
  occupied_emergency_beds: number;
  reserved_emergency_beds: number;
  out_of_service_emergency_beds: number;
  available_emergency_beds: number;
  total_icu_beds: number;
  occupied_icu_beds: number;
  reserved_icu_beds: number;
  out_of_service_icu_beds: number;
  available_icu_beds: number;
  has_oxygen_facility: boolean;
  has_trauma_center: boolean;
  updated_at: string;
};

export type HospitalCapacityUpdate = {
  total_emergency_beds?: number;
  occupied_emergency_beds?: number;
  reserved_emergency_beds?: number;
  out_of_service_emergency_beds?: number;
  total_icu_beds?: number;
  occupied_icu_beds?: number;
  reserved_icu_beds?: number;
  out_of_service_icu_beds?: number;
  has_oxygen_facility?: boolean;
  has_trauma_center?: boolean;
};

export const getHospitalCapacity = (orgId: string = DEFAULT_HOSPITAL_ID) =>
  api<HospitalCapacity>(`/resources/hospitals/${orgId}/capacity`);

export const updateHospitalCapacity = (
  orgId: string = DEFAULT_HOSPITAL_ID,
  body: HospitalCapacityUpdate
) =>
  api<HospitalCapacity>(`/resources/hospitals/${orgId}/capacity`, {
    method: "PUT",
    body: JSON.stringify(body),
  });

export type HospitalSearchResult = {
  organization_id: string;
  hospital_name: string;
  distance_km: number;
  available_emergency_beds: number;
  available_icu_beds: number;
  has_trauma_center: boolean;
  location: { type: "Point"; coordinates: [number, number] };
};

export const searchHospitals = (lat: number, lng: number, radiusKm: number = 100) =>
  api<HospitalSearchResult[]>(
    `/resources/hospitals/search?lat=${lat}&lng=${lng}&radius_km=${radiusKm}`
  );

export type AmbulanceSearchResult = {
  id: string;
  organization_id: string;
  vehicle_number: string;
  ambulance_type: string;
  status: string;
  distance_km: number;
  current_location: { type: "Point"; coordinates: [number, number] };
  crew_size: number;
};

export const searchAmbulances = (lat: number, lng: number) =>
  api<AmbulanceSearchResult[]>(`/resources/ambulances/search?lat=${lat}&lng=${lng}`);

export type ReservationResponse = {
  id: string;
  task_id?: string;
  organization_id: string;
  resource_type: string;
  quantity: number;
  status: string;
  expires_at: string;
  created_at: string;
  updated_at: string;
};

export const fulfillReservation = (reservationId: string, notes?: string) =>
  api<ReservationResponse>(`/resources/reservations/${reservationId}/fulfill`, {
    method: "POST",
    body: JSON.stringify({ notes: notes || "Patient admitted" }),
  });

export const releaseReservation = (reservationId: string, reason?: string) =>
  api<ReservationResponse>(`/resources/reservations/${reservationId}/release`, {
    method: "POST",
    body: JSON.stringify({ reason: reason || "Diverted or cancelled" }),
  });

// ----------------- Response Tasks -----------------

export type ResponseTask = {
  id: string;
  incident_id: string;
  parent_task_id?: string;
  task_type: string;
  status: string;
  priority: string;
  assigned_organization_id?: string;
  assigned_user_id?: string;
  target_location?: { type: "Point"; coordinates: [number, number] };
  instructions?: string;
  assigned_at?: string;
  accepted_at?: string;
  arrived_at?: string;
  completed_at?: string;
  citizen_confirmed_arrival?: boolean;
  created_at: string;
  updated_at: string;
};

export const getTask = (taskId: string) => api<ResponseTask>(`/tasks/${taskId}`);

export const updateTaskStatus = (taskId: string, status: string, notes?: string) =>
  api<ResponseTask>(`/tasks/${taskId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status, notes }),
  });

export const acceptTask = (taskId: string) =>
  api<{ task_id: string; status: string }>(`/tasks/${taskId}/accept`, {
    method: "PATCH",
  });

export const listIncidentTasks = (incidentId: string) =>
  api<ResponseTask[]>(`/incidents/${incidentId}/tasks`);

// ----------------- Citizen SOS & Incident Reports -----------------

export type ReportInput = {
  description: string;
  lat: number;
  lng: number;
  district: string;
  landmark?: string;
  people_affected: number;
  reporter_name?: string;
  reporter_phone?: string;
};

export type ReportResult = { incident_number: string; tracking_token: string; status: string; id?: string };

export function submitReport(r: ReportInput) {
  return api<ReportResult>("/incidents/report", {
    method: "POST",
    body: JSON.stringify({
      description: r.description,
      location: { type: "Point", coordinates: [r.lng, r.lat] },
      district: r.district,
      landmark: r.landmark || null,
      people_affected: r.people_affected,
      reporter_name: r.reporter_name || null,
      reporter_phone: r.reporter_phone || null,
      source: "WEB_ANONYMOUS",
    }),
  });
}

export type TrackResult = {
  incident_number: string;
  status: string;
  reported_at: string;
  tasks: { task_id: string; task_type: string; status: string; responder_type?: string; eta_minutes?: number }[];
};

export const trackIncident = (token: string) => api<TrackResult>(`/incidents/track/${token}`);

export const confirmArrival = (token: string, notes: string) =>
  api(`/incidents/track/${token}/confirm-arrival`, {
    method: "POST",
    body: JSON.stringify({ confirmed: true, notes }),
  });

export type Incident = {
  id: string;
  incident_number: string;
  status: string;
  priority: string;
  hazard_type: string;
  description: string;
  location: { coordinates: [number, number] };
  district: string;
  people_affected: number;
  trapped_count: number;
  injured_count: number;
  created_at: string;
  tasks?: ResponseTask[];
};

export const listIncidents = (status?: string) =>
  api<Incident[]>(status ? `/incidents?status=${status}` : "/incidents");

export const getIncident = (id: string) => api<Incident>(`/incidents/${id}`);
