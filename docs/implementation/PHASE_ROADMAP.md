# 🚀 RESQ — Industry-Standard Implementation Roadmap

> **Mission-Critical Emergency Coordination Platform**  
> Production-grade, real-time, multi-tenant system with AI orchestration

---

## 📊 EXECUTIVE SUMMARY

Transform RESQ from a working backend into a **world-class emergency response platform** that rivals industry leaders like PulsePoint, RapidSOS, and Everbridge. This roadmap delivers a complete, polished, production-ready system across **8 phases over 24 weeks**.

### Success Metrics
- **Response Time:** < 90 seconds from SOS to first responder dispatch
- **System Uptime:** 99.95% availability
- **Concurrent Users:** Support 10,000+ simultaneous connections
- **Mobile Performance:** < 2s initial page load on 3G
- **Accessibility:** WCAG 2.1 AA compliance
- **User Satisfaction:** > 4.5/5.0 post-incident rating

---

## 🎯 PHASE 1: FOUNDATION & SECURITY HARDENING (Weeks 1-3)

### Objective
Bulletproof the existing backend with enterprise security, monitoring, and the foundation for a scalable frontend monorepo.

### Backend Enhancements

#### 1.1 Data Encryption at Rest
**Why:** PHI/PII compliance (HIPAA-ready architecture)

```python
# New: backend/app/services/encryption_service.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64
import os

class FieldEncryption:
    """Encrypt sensitive database fields before write, decrypt after read"""
    
    def __init__(self):
        # Derive key from SECRET_KEY + ENCRYPTION_SALT
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=os.getenv("ENCRYPTION_SALT").encode(),
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(os.getenv("SECRET_KEY").encode())
        )
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode()).decode()

# Encrypt these fields:
# - users.phone
# - users.email (searchable via hash index)
# - incidents.description
# - incident_reports.raw_text
# - audit_logs.metadata
```

**Migration Strategy:**
```bash
# Create migration to add encrypted columns
alembic revision -m "add_encrypted_fields"

# Columns: phone_encrypted, email_hash, description_encrypted
# Backfill in batches of 1000 rows
# Drop old columns after verification
```

#### 1.2 API Key Rotation System
```python
# New: backend/app/models/api_key.py
class APIKey(BaseModel):
    __tablename__ = "api_keys"
    
    key_prefix: Mapped[str] = mapped_column(String(16))  # e.g., "resq_live_"
    key_hash: Mapped[str] = mapped_column(String(255))   # bcrypt hash
    name: Mapped[str] = mapped_column(String(100))       # "Production Agent"
    scopes: Mapped[list] = mapped_column(JSON)           # ["incidents:write", "tasks:read"]
    
    expires_at: Mapped[datetime]
    last_used_at: Mapped[Optional[datetime]]
    last_used_ip: Mapped[Optional[str]]
    
    is_active: Mapped[bool] = mapped_column(default=True)
    rotation_policy_days: Mapped[int] = mapped_column(default=90)

# Auto-rotation: Cron job alerts 7 days before expiry
```

#### 1.3 Advanced Rate Limiting
```python
# Enhanced: backend/app/middleware/rate_limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address

# Role-based limits
RATE_LIMITS = {
    "anonymous": "10/minute",           # Citizen SOS
    "FIELD_RESPONDER": "100/minute",    # Active responders
    "TRIAGE_DOCTOR": "200/minute",      # Hospital dashboards
    "CONTROL_ROOM_DISPATCHER": "500/minute",
    "SUPERADMIN": "1000/minute",
    "AGENT_SYSTEM": "200/minute",       # AI agents
}

def get_rate_limit_key(request: Request):
    if token := request.headers.get("Authorization"):
        user = decode_token(token)
        return f"user:{user.id}:{user.role}"
    return f"ip:{get_remote_address(request)}"

@limiter.limit(lambda: RATE_LIMITS.get(get_user_role(), "10/minute"))
async def protected_endpoint():
    ...
```

#### 1.4 Comprehensive Logging & Monitoring
```python
# New: backend/app/observability/
# - structured_logging.py (JSON logs with trace IDs)
# - metrics.py (Prometheus metrics export)
# - distributed_tracing.py (OpenTelemetry integration)

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Track:
# - Request duration by endpoint + role
# - Database query performance
# - WebSocket connection count
# - Agent response times
# - Cache hit/miss rates
# - Error rates by type

# Export to: Grafana Cloud, Datadog, or New Relic
```

#### 1.5 Database Connection Pooling & Query Optimization
```python
# Enhanced: backend/app/database/config.py
DATABASE_CONFIG = {
    "pool_size": 20,                    # Concurrent connections
    "max_overflow": 10,                 # Burst capacity
    "pool_timeout": 30,                 # Wait before timeout
    "pool_recycle": 3600,               # Recycle connections hourly
    "pool_pre_ping": True,              # Health check before use
    "echo_pool": True,                  # Log pool events (dev only)
}

# Add read replicas for reporting queries
READ_REPLICA_URL = os.getenv("DATABASE_READ_REPLICA_URL")
```

**Query Optimizations:**
- Add composite indexes: `(status, priority, created_at)` on incidents
- Materialized views for dashboard aggregations
- Partial indexes for common filters (e.g., `WHERE status = 'ACTIVE_RESPONSE'`)

#### 1.6 HTTPS Enforcement & Security Headers
```python
# Enhanced: backend/app/middleware/security_headers.py
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(HTTPSRedirectMiddleware)  # Force HTTPS in production
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["resq.org", "*.resq.org", "localhost"]
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' wss://*.resq.org https://*.resq.org;"
    )
    return response
```

### Frontend Foundation

#### 1.7 Monorepo Setup with Turborepo
```bash
# Structure
frontend/
├── apps/
│   ├── citizen/              # Public SOS portal
│   ├── responder/            # Field responder app
│   ├── hospital/             # Healthcare portal
│   ├── control-room/         # Dispatch center
│   └── admin/                # Superadmin panel
├── packages/
│   ├── ui/                   # Shared component library
│   ├── api/                  # Generated TypeScript client
│   ├── auth/                 # Auth context & hooks
│   ├── realtime/             # WebSocket management
│   ├── maps/                 # Map components
│   ├── utils/                # Shared utilities
│   └── config/               # Shared configs (ESLint, TypeScript, Tailwind)
├── turbo.json
└── package.json

# Key dependencies:
# - Next.js 15 (App Router)
# - React 19
# - TypeScript 5.4
# - TailwindCSS 4.0 Beta
# - Turborepo 2.x
```

**turbo.json:**
```json
{
  "$schema": "https://turbo.build/schema.json",
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "!.next/cache/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "lint": {
      "dependsOn": ["^lint"]
    },
    "test": {
      "dependsOn": ["^build"]
    }
  }
}
```

#### 1.8 Design System Foundation
```typescript
// packages/ui/src/tokens/colors.ts
export const colors = {
  // Brand palette
  brand: {
    primary: {
      50: '#FFF5F5',
      500: '#E53E3E',    // Emergency red
      900: '#7A1A1A',
    },
    secondary: {
      50: '#E6FFFA',
      500: '#38B2AC',    // Medical teal
      900: '#234E52',
    },
  },
  
  // Semantic colors
  semantic: {
    success: '#48BB78',
    warning: '#F6AD55',
    error: '#FC8181',
    info: '#4299E1',
  },
  
  // Role-based accents
  role: {
    citizen: '#4299E1',      // Blue
    responder: '#F6AD55',    // Orange
    hospital: '#48BB78',     // Green
    controlRoom: '#9F7AEA',  // Purple
  },
  
  // Neutrals with slight warmth
  neutral: {
    0: '#FFFFFF',
    50: '#FAFAF9',
    100: '#F5F5F4',
    200: '#E7E5E4',
    500: '#78716C',
    900: '#1C1917',
    1000: '#000000',
  },
};

// packages/ui/src/tokens/typography.ts
export const typography = {
  fonts: {
    display: 'var(--font-display)',    // Inter Variable
    body: 'var(--font-body)',          // Inter Variable
    mono: 'var(--font-mono)',          // JetBrains Mono
  },
  
  sizes: {
    xs: '0.75rem',      // 12px
    sm: '0.875rem',     // 14px
    base: '1rem',       // 16px
    lg: '1.125rem',     // 18px
    xl: '1.25rem',      // 20px
    '2xl': '1.5rem',    // 24px
    '3xl': '1.875rem',  // 30px
    '4xl': '2.25rem',   // 36px
    '5xl': '3rem',      // 48px
  },
};
```

### Phase 1 Deliverables
- ✅ Encrypted PII/PHI fields with migration
- ✅ API key rotation system
- ✅ Role-based rate limiting
- ✅ Structured logging with trace IDs
- ✅ Prometheus metrics endpoints
- ✅ Database connection pooling
- ✅ Security headers middleware
- ✅ Frontend monorepo scaffolded
- ✅ Design system tokens defined
- ✅ CI/CD pipeline (GitHub Actions)

**Success Criteria:**
- Security audit passes (OWASP Top 10)
- < 100ms P95 API response time
- Zero PII/PHI in plaintext logs

---

## 🌐 PHASE 2: CITIZEN PORTAL — ZERO-FRICTION SOS (Weeks 4-6)

### Objective
Build the **most accessible emergency reporting interface** in the industry. No login, no friction, works offline, multi-language support.

### Features

#### 2.1 Emergency SOS Form
**Design Philosophy:** Panic-proof UI — large touch targets, minimal steps, instant feedback.

```typescript
// apps/citizen/app/sos/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useGeolocation } from '@/hooks/useGeolocation';
import { useOfflineQueue } from '@/hooks/useOfflineQueue';
import { Button } from '@resq/ui/button';
import { Textarea } from '@resq/ui/textarea';
import { MapPicker } from '@resq/maps/map-picker';

export default function SOSPage() {
  const { location, accuracy, loading } = useGeolocation({ highAccuracy: true });
  const { addToQueue, isOnline } = useOfflineQueue();
  const [description, setDescription] = useState('');
  const [peopleAffected, setPeopleAffected] = useState(1);
  
  // Voice input for hands-free operation
  const { transcript, startListening } = useVoiceInput();
  
  useEffect(() => {
    if (transcript) setDescription(prev => prev + ' ' + transcript);
  }, [transcript]);
  
  const handleSubmit = async () => {
    const report = {
      description,
      location: location || lastKnownLocation,
      people_affected: peopleAffected,
      reported_at: new Date().toISOString(),
    };
    
    if (isOnline) {
      // Direct submission
      const response = await api.incidents.report(report);
      router.push(`/track/${response.tracking_token}`);
    } else {
      // Queue for later sync
      await addToQueue('incident-report', report);
      showToast('Saved offline. Will send when connected.');
    }
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-b from-red-50 to-white dark:from-red-950 dark:to-neutral-900">
      {/* Offline indicator */}
      {!isOnline && (
        <div className="fixed top-0 inset-x-0 bg-amber-500 text-white py-2 px-4 text-center text-sm font-medium">
          📡 Offline Mode — Your report will be sent when reconnected
        </div>
      )}
      
      {/* Emergency header */}
      <header className="pt-safe bg-red-600 text-white px-4 py-6">
        <h1 className="text-3xl font-bold">Emergency SOS</h1>
        <p className="text-red-100 mt-1">Help is on the way. Stay calm.</p>
      </header>
      
      <main className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        {/* Location picker with map */}
        <section>
          <label className="block text-lg font-semibold mb-2">
            Your Location
          </label>
          {loading ? (
            <div className="animate-pulse bg-neutral-200 dark:bg-neutral-800 h-64 rounded-lg" />
          ) : (
            <MapPicker
              initialLocation={location}
              onLocationChange={setLocation}
              accuracy={accuracy}
            />
          )}
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-2">
            {accuracy < 50 ? '✓ Accurate location' : '⚠️ Low accuracy — adjust pin if needed'}
          </p>
        </section>
        
        {/* Description with voice input */}
        <section>
          <label className="block text-lg font-semibold mb-2">
            What's happening?
          </label>
          <div className="relative">
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the emergency... (e.g., trapped in flood, injured person, building collapse)"
              rows={5}
              className="text-base"
            />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="absolute bottom-2 right-2"
              onClick={startListening}
            >
              🎤 Voice Input
            </Button>
          </div>
        </section>
        
        {/* Quick context buttons */}
        <section>
          <label className="block text-lg font-semibold mb-2">
            Emergency Type
          </label>
          <div className="grid grid-cols-2 gap-3">
            {['Flood', 'Medical', 'Fire', 'Collapse', 'Landslide', 'Other'].map(type => (
              <Button
                key={type}
                variant={selectedType === type ? 'solid' : 'outline'}
                onClick={() => setSelectedType(type)}
              >
                {getEmoji(type)} {type}
              </Button>
            ))}
          </div>
        </section>
        
        {/* People count */}
        <section>
          <label className="block text-lg font-semibold mb-2">
            People Affected
          </label>
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="lg"
              onClick={() => setPeopleAffected(Math.max(1, peopleAffected - 1))}
            >
              −
            </Button>
            <span className="text-3xl font-bold w-16 text-center">
              {peopleAffected}
            </span>
            <Button
              variant="outline"
              size="lg"
              onClick={() => setPeopleAffected(peopleAffected + 1)}
            >
              +
            </Button>
          </div>
        </section>
        
        {/* Submit button — large and prominent */}
        <Button
          size="xl"
          variant="solid"
          className="w-full bg-red-600 hover:bg-red-700 text-white text-xl py-6"
          onClick={handleSubmit}
          disabled={!description.trim()}
        >
          🚨 Send Emergency Report
        </Button>
        
        {/* Privacy notice */}
        <p className="text-xs text-neutral-600 dark:text-neutral-400 text-center">
          Your location and details are shared with emergency responders only.
          <br />
          No account required. <a href="/privacy" className="underline">Privacy Policy</a>
        </p>
      </main>
    </div>
  );
}
```

#### 2.2 Live Tracking Interface
**Real-time status updates via WebSocket**

```typescript
// apps/citizen/app/track/[token]/page.tsx
'use client';

import { useIncidentTracking } from '@/hooks/useIncidentTracking';
import { Timeline } from '@resq/ui/timeline';
import { LiveMap } from '@resq/maps/live-map';
import { Badge } from '@resq/ui/badge';

export default function TrackingPage({ params }: { params: { token: string } }) {
  const { incident, tasks, loading } = useIncidentTracking(params.token);
  
  if (loading) return <TrackingSkeleton />;
  if (!incident) return <NotFound />;
  
  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
      <header className="bg-white dark:bg-neutral-900 border-b px-4 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">
                Tracking {incident.incident_number}
              </h1>
              <p className="text-sm text-neutral-600 dark:text-neutral-400">
                Reported {formatDistanceToNow(incident.created_at)} ago
              </p>
            </div>
            <StatusBadge status={incident.status} priority={incident.priority} />
          </div>
        </div>
      </header>
      
      <main className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        {/* Current status card */}
        <section className="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold mb-4">Current Status</h2>
          <StatusMessage incident={incident} />
          
          {/* ETA if rescue dispatched */}
          {incident.status === 'ACTIVE_RESPONSE' && (
            <div className="mt-4 p-4 bg-green-50 dark:bg-green-950 rounded-lg">
              <p className="font-semibold text-green-900 dark:text-green-100">
                🚤 Help is on the way!
              </p>
              <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                Estimated arrival: {getETA(tasks)} minutes
              </p>
            </div>
          )}
        </section>
        
        {/* Live map showing responder locations */}
        {incident.status === 'ACTIVE_RESPONSE' && (
          <section className="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold mb-4">Live Tracking</h2>
            <LiveMap
              incident={incident}
              tasks={tasks}
              height={400}
            />
          </section>
        )}
        
        {/* Timeline of all status changes */}
        <section className="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold mb-4">Timeline</h2>
          <Timeline
            events={incident.status_history}
            renderEvent={(event) => (
              <div>
                <p className="font-medium">{event.status}</p>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">
                  {formatDateTime(event.created_at)}
                </p>
                {event.notes && (
                  <p className="text-sm mt-1">{event.notes}</p>
                )}
              </div>
            )}
          />
        </section>
        
        {/* Contact emergency services */}
        <section className="bg-blue-50 dark:bg-blue-950 rounded-xl p-6">
          <h3 className="font-semibold mb-2">Need immediate assistance?</h3>
          <p className="text-sm text-neutral-700 dark:text-neutral-300 mb-4">
            If life-threatening, call emergency services directly.
          </p>
          <a
            href="tel:112"
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700"
          >
            📞 Call 112 (Emergency)
          </a>
        </section>
      </main>
    </div>
  );
}
```

#### 2.3 Multi-Language Support
```typescript
// packages/i18n/locales/
// - en.json (English)
// - hi.json (Hindi - हिन्दी)
// - ml.json (Malayalam - മലയാളം)
// - ta.json (Tamil - தமிழ்)
// - te.json (Telugu - తెలుగు)
// - kn.json (Kannada - ಕನ್ನಡ)

// Auto-detect from browser, persist choice
import { useTranslation } from 'next-i18next';

const { t, i18n } = useTranslation('common');

// SOS form in local language
<Button>{t('sos.submit')}</Button>  // "Send Emergency Report" / "आपातकालीन रिपोर्ट भेजें"
```

#### 2.4 Progressive Web App (PWA)
```typescript
// apps/citizen/public/manifest.json
{
  "name": "RESQ Emergency SOS",
  "short_name": "RESQ SOS",
  "description": "Emergency coordination platform for citizens",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#FFFFFF",
  "theme_color": "#E53E3E",
  "orientation": "portrait",
  "icons": [
    {
      "src": "/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "shortcuts": [
    {
      "name": "Emergency SOS",
      "short_name": "SOS",
      "url": "/sos",
      "icons": [{ "src": "/icons/sos-96.png", "sizes": "96x96" }]
    }
  ]
}

// Service worker for offline support
// apps/citizen/sw.ts
import { precacheAndRoute } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { NetworkFirst, CacheFirst } from 'workbox-strategies';

// Cache static assets
registerRoute(
  ({ request }) => request.destination === 'image',
  new CacheFirst({ cacheName: 'images' })
);

// Network-first for API calls, fallback to queue
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/'),
  new NetworkFirst({
    cacheName: 'api',
    networkTimeoutSeconds: 10,
  })
);
```

### Phase 2 Deliverables
- ✅ Citizen SOS form (web + mobile responsive)
- ✅ Real-time incident tracking page
- ✅ Voice input for hands-free reporting
- ✅ GPS auto-detection with map picker
- ✅ Offline mode with IndexedDB queue
- ✅ PWA with installable app
- ✅ Multi-language support (6 languages)
- ✅ Push notification registration
- ✅ Accessibility audit passed (WCAG AA)

**Success Criteria:**
- < 3 seconds to submit SOS on 3G
- 100% offline submissions successfully sync
- Lighthouse score > 90 (Performance, Accessibility)

---

## 🚤 PHASE 3: RESPONDER DASHBOARD — FIELD OPERATIONS (Weeks 7-9)

### Objective
Build a **battle-tested field operations interface** for rescue teams and ambulance drivers working in high-stress, low-connectivity environments.

### Features

#### 3.1 Task Queue with Smart Prioritization
```typescript
// apps/responder/app/dashboard/page.tsx
'use client';

import { useTaskQueue } from '@/hooks/useTaskQueue';
import { TaskCard } from '@/components/task-card';
import { FilterBar } from '@/components/filter-bar';

export default function ResponderDashboard() {
  const {
    tasks,
    activeTask,
    acceptTask,
    rejectTask,
    completeTask,
  } = useTaskQueue();
  
  // Smart sorting: Critical → High → closest distance
  const sortedTasks = useMemo(() => {
    return tasks.sort((a, b) => {
      if (a.priority !== b.priority) {
        return PRIORITY_WEIGHT[a.priority] - PRIORITY_WEIGHT[b.priority];
      }
      return a.distance - b.distance;  // Closest first
    });
  }, [tasks]);
  
  return (
    <div className="min-h-screen bg-neutral-100 dark:bg-neutral-950">
      {/* Active task banner */}
      {activeTask && (
        <ActiveTaskBanner
          task={activeTask}
          onNavigate={() => openMaps(activeTask.location)}
          onComplete={() => completeTask(activeTask.id)}
        />
      )}
      
      {/* Task queue */}
      <main className="max-w-7xl mx-auto px-4 py-6 space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Available Tasks</h1>
          <Badge variant={tasks.length > 0 ? 'warning' : 'success'}>
            {tasks.length} Pending
          </Badge>
        </div>
        
        <FilterBar
          filters={['All', 'Critical', 'Nearby', 'Medical', 'Rescue']}
          onFilterChange={setActiveFilter}
        />
        
        <div className="grid gap-4 lg:grid-cols-2">
          {sortedTasks.map(task => (
            <TaskCard
              key={task.id}
              task={task}
              onAccept={() => acceptTask(task.id)}
              onReject={() => rejectTask(task.id)}
            />
          ))}
        </div>
      </main>
    </div>
  );
}

// components/task-card.tsx
export function TaskCard({ task, onAccept, onReject }) {
  return (
    <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-sm p-6 border-l-4"
         style={{ borderLeftColor: PRIORITY_COLORS[task.priority] }}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <Badge variant="solid" className={PRIORITY_BADGE_CLASSES[task.priority]}>
            {task.priority}
          </Badge>
          <h3 className="font-semibold text-lg mt-2">
            {task.task_type.replace('_', ' ')}
          </h3>
        </div>
        <span className="text-sm text-neutral-600 dark:text-neutral-400">
          {task.distance}km away
        </span>
      </div>
      
      {/* Incident details */}
      <div className="space-y-2 text-sm mb-4">
        <div className="flex items-center gap-2">
          <MapPinIcon className="w-4 h-4 text-neutral-500" />
          <span>{task.incident.district} • {task.incident.landmark || 'No landmark'}</span>
        </div>
        <div className="flex items-center gap-2">
          <UsersIcon className="w-4 h-4 text-neutral-500" />
          <span>{task.incident.people_affected} people affected</span>
        </div>
        <div className="flex items-center gap-2">
          <ClockIcon className="w-4 h-4 text-neutral-500" />
          <span>Reported {formatDistanceToNow(task.created_at)} ago</span>
        </div>
      </div>
      
      {/* Description */}
      <p className="text-sm text-neutral-700 dark:text-neutral-300 mb-4 line-clamp-2">
        {task.incident.description}
      </p>
      
      {/* Actions */}
      <div className="flex gap-2">
        <Button
          variant="solid"
          className="flex-1 bg-green-600 hover:bg-green-700"
          onClick={onAccept}
        >
          ✓ Accept
        </Button>
        <Button
          variant="outline"
          onClick={onReject}
        >
          Decline
        </Button>
      </div>
    </div>
  );
}
```

#### 3.2 Live Map with Navigation Integration
```typescript
// apps/responder/components/live-map.tsx
'use client';

import Map, { Marker, NavigationControl, GeolocateControl } from 'react-map-gl';
import { useGeolocation } from '@/hooks/useGeolocation';
import { useResponderLocation } from '@/hooks/useResponderLocation';

export function LiveOperationsMap() {
  const { location: myLocation } = useGeolocation({ watch: true });
  const { tasks, activeTask } = useTaskQueue();
  
  // Broadcast location every 30s when on active task
  useResponderLocation(activeTask?.id, myLocation);
  
  return (
    <div className="relative h-[600px] rounded-lg overflow-hidden">
      <Map
        mapboxAccessToken={process.env.NEXT_PUBLIC_MAPBOX_TOKEN}
        initialViewState={{
          longitude: myLocation?.longitude || 76.2711,
          latitude: myLocation?.latitude || 10.8505,
          zoom: 12,
        }}
        mapStyle="mapbox://styles/mapbox/streets-v12"
      >
        {/* My location */}
        {myLocation && (
          <Marker
            longitude={myLocation.longitude}
            latitude={myLocation.latitude}
          >
            <div className="relative">
              <div className="w-6 h-6 bg-blue-500 border-4 border-white rounded-full shadow-lg" />
              <div className="absolute inset-0 bg-blue-400 rounded-full animate-ping opacity-75" />
            </div>
          </Marker>
        )}
        
        {/* Task locations */}
        {tasks.map(task => (
          <Marker
            key={task.id}
            longitude={task.incident.location.coordinates[0]}
            latitude={task.incident.location.coordinates[1]}
            onClick={() => setSelectedTask(task)}
          >
            <div className={`
              w-10 h-10 rounded-full flex items-center justify-center
              shadow-lg border-2 border-white font-semibold text-white text-sm
              ${PRIORITY_COLORS_BG[task.priority]}
            `}>
              {task.incident.people_affected}
            </div>
          </Marker>
        ))}
        
        <GeolocateControl position="top-right" trackUserLocation />
        <NavigationControl position="top-right" />
      </Map>
      
      {/* Navigate button overlay */}
      {activeTask && (
        <div className="absolute bottom-4 left-4 right-4">
          <Button
            size="lg"
            className="w-full bg-blue-600 hover:bg-blue-700 shadow-xl"
            onClick={() => {
              // Open in native maps app
              const coords = activeTask.incident.location.coordinates;
              window.open(
                `https://www.google.com/maps/dir/?api=1&destination=${coords[1]},${coords[0]}`,
                '_blank'
              );
            }}
          >
            🧭 Navigate to Incident ({activeTask.distance}km)
          </Button>
        </div>
      )}
    </div>
  );
}
```

#### 3.3 Offline Task Management
```typescript
// hooks/useOfflineTaskQueue.ts
import { useEffect } from 'react';
import Dexie from 'dexie';

// IndexedDB schema
class OfflineDB extends Dexie {
  tasks!: Dexie.Table<Task, string>;
  queuedActions!: Dexie.Table<QueuedAction, string>;
  
  constructor() {
    super('ResponderOfflineDB');
    this.version(1).stores({
      tasks: 'id, status, priority, created_at',
      queuedActions: '++id, action, task_id, created_at, synced',
    });
  }
}

const db = new OfflineDB();

export function useOfflineTaskQueue() {
  const { isOnline } = useNetworkStatus();
  
  // Accept task offline
  const acceptTask = async (taskId: string) => {
    if (isOnline) {
      await api.tasks.accept(taskId);
    } else {
      // Queue for later
      await db.queuedActions.add({
        action: 'accept',
        task_id: taskId,
        created_at: new Date().toISOString(),
        synced: false,
      });
      
      // Update local state
      await db.tasks.update(taskId, { status: 'ACCEPTED_OFFLINE' });
      showToast('Task accepted offline. Will sync when connected.');
    }
  };
  
  // Sync queue when back online
  useEffect(() => {
    if (!isOnline) return;
    
    const syncQueue = async () => {
      const pending = await db.queuedActions
        .where('synced')
        .equals(false)
        .toArray();
      
      for (const action of pending) {
        try {
          if (action.action === 'accept') {
            await api.tasks.accept(action.task_id);
          } else if (action.action === 'complete') {
            await api.tasks.complete(action.task_id, action.metadata);
          }
          
          // Mark as synced
          await db.queuedActions.update(action.id!, { synced: true });
        } catch (error) {
          console.error('Failed to sync action:', action, error);
        }
      }
      
      if (pending.length > 0) {
        showToast(`Synced ${pending.length} offline actions`, 'success');
      }
    };
    
    syncQueue();
  }, [isOnline]);
  
  return { acceptTask, completeTask, queuedActionsCount };
}
```

#### 3.4 Voice Status Updates
```typescript
// components/voice-status-updater.tsx
'use client';

import { useState } from 'react';
import { useVoiceRecognition } from '@/hooks/useVoiceRecognition';

export function VoiceStatusUpdater({ taskId }: { taskId: string }) {
  const [isListening, setIsListening] = useState(false);
  const { transcript, startListening, stopListening } = useVoiceRecognition();
  
  const handleVoiceUpdate = async () => {
    if (isListening) {
      stopListening();
      
      // Parse intent from transcript
      const intent = parseStatusIntent(transcript);
      
      if (intent) {
        await api.tasks.updateStatus(taskId, {
          status: intent.status,
          notes: transcript,
        });
        showToast('Status updated via voice');
      }
    } else {
      startListening();
    }
    
    setIsListening(!isListening);
  };
  
  return (
    <Button
      variant={isListening ? 'solid' : 'outline'}
      onClick={handleVoiceUpdate}
      className={isListening ? 'animate-pulse bg-red-500' : ''}
    >
      {isListening ? '🔴 Listening...' : '🎤 Voice Update'}
    </Button>
  );
}

// Parse common status phrases
function parseStatusIntent(transcript: string): StatusIntent | null {
  const lower = transcript.toLowerCase();
  
  if (lower.includes('arrived') || lower.includes('reached')) {
    return { status: 'ARRIVED_ON_SCENE' };
  }
  if (lower.includes('transport') || lower.includes('moving')) {
    return { status: 'IN_TRANSIT' };
  }
  if (lower.includes('complete') || lower.includes('done')) {
    return { status: 'COMPLETED' };
  }
  
  return null;
}
```

### Phase 3 Deliverables
- ✅ Task queue with smart prioritization
- ✅ Live map with responder tracking
- ✅ One-tap accept/reject/complete actions
- ✅ Offline task queue with auto-sync
- ✅ Native map navigation integration
- ✅ Voice status updates
- ✅ Background geolocation tracking
- ✅ Low battery mode (reduces GPS polling)
- ✅ Dark mode optimized for night operations

**Success Criteria:**
- < 500ms task card render time
- 100% offline actions successfully sync
- Battery usage < 5% per hour with GPS tracking

---

## 🏥 PHASE 4: HOSPITAL PORTAL — CAPACITY MANAGEMENT (Weeks 10-12)

### Objective
Build a **real-time hospital operations dashboard** for capacity management, incoming patient triage, and resource coordination.

### Features

#### 4.1 Capacity Dashboard
```typescript
// apps/hospital/app/dashboard/page.tsx
'use client';

import { useHospitalCapacity } from '@/hooks/useHospitalCapacity';
import { CapacityCard } from '@/components/capacity-card';
import { IncomingPatientQueue } from '@/components/patient-queue';

export default function HospitalDashboard() {
  const { capacity, updateCapacity } = useHospitalCapacity();
  const { incomingPatients, acceptPatient, rejectPatient } = useIncomingPatients();
  
  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
      <header className="bg-white dark:bg-neutral-900 border-b px-6 py-4">
        <h1 className="text-2xl font-bold">Hospital Operations</h1>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          {capacity.organization_name}
        </p>
      </header>
      
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Capacity overview */}
        <section>
          <h2 className="text-xl font-semibold mb-4">Bed Availability</h2>
          <div className="grid gap-4 md:grid-cols-3">
            <CapacityCard
              label="ICU Beds"
              available={capacity.icu_beds_available}
              total={capacity.icu_beds_total}
              occupied={capacity.icu_beds_occupied}
              reserved={capacity.icu_beds_reserved}
              onUpdate={(delta) => updateCapacity('icu_beds', delta)}
            />
            <CapacityCard
              label="General Beds"
              available={capacity.general_beds_available}
              total={capacity.general_beds_total}
              occupied={capacity.general_beds_occupied}
              reserved={capacity.general_beds_reserved}
              onUpdate={(delta) => updateCapacity('general_beds', delta)}
            />
            <CapacityCard
              label="Emergency Beds"
              available={capacity.emergency_beds_available}
              total={capacity.emergency_beds_total}
              occupied={capacity.emergency_beds_occupied}
              reserved={capacity.emergency_beds_reserved}
              onUpdate={(delta) => updateCapacity('emergency_beds', delta)}
            />
          </div>
        </section>
        
        {/* Incoming patient requests */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Incoming Patients</h2>
            <Badge variant="warning">
              {incomingPatients.length} Pending
            </Badge>
          </div>
          <IncomingPatientQueue
            patients={incomingPatients}
            onAccept={acceptPatient}
            onReject={rejectPatient}
          />
        </section>
        
        {/* Ambulance status */}
        <section>
          <h2 className="text-xl font-semibold mb-4">Ambulance Fleet</h2>
          <AmbulanceFleetStatus />
        </section>
      </main>
    </div>
  );
}

// components/capacity-card.tsx
export function CapacityCard({ label, available, total, occupied, reserved, onUpdate }) {
  const utilizationPercent = ((occupied + reserved) / total) * 100;
  
  return (
    <div className="bg-white dark:bg-neutral-900 rounded-lg p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">{label}</h3>
        <Badge variant={available > 5 ? 'success' : available > 0 ? 'warning' : 'error'}>
          {available} Available
        </Badge>
      </div>
      
      {/* Visual capacity bar */}
      <div className="relative h-8 bg-neutral-200 dark:bg-neutral-800 rounded-full overflow-hidden mb-4">
        <div
          className="absolute inset-y-0 left-0 bg-red-500 flex items-center justify-center text-white text-xs font-semibold"
          style={{ width: `${(occupied / total) * 100}%` }}
        >
          {occupied > 0 && `${occupied} Occ`}
        </div>
        <div
          className="absolute inset-y-0 bg-amber-400 flex items-center justify-center text-white text-xs font-semibold"
          style={{
            left: `${(occupied / total) * 100}%`,
            width: `${(reserved / total) * 100}%`
          }}
        >
          {reserved > 0 && `${reserved} Res`}
        </div>
      </div>
      
      {/* Quick stats */}
      <div className="grid grid-cols-3 gap-2 text-sm mb-4">
        <div>
          <span className="text-neutral-600 dark:text-neutral-400">Total</span>
          <p className="font-semibold">{total}</p>
        </div>
        <div>
          <span className="text-neutral-600 dark:text-neutral-400">Occupied</span>
          <p className="font-semibold">{occupied}</p>
        </div>
        <div>
          <span className="text-neutral-600 dark:text-neutral-400">Reserved</span>
          <p className="font-semibold">{reserved}</p>
        </div>
      </div>
      
      {/* Quick actions */}
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={() => onUpdate(-1)}
          disabled={available === 0}
        >
          − Release
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => onUpdate(1)}
          disabled={available === total}
        >
          + Admit
        </Button>
      </div>
    </div>
  );
}
```

#### 4.2 Incoming Patient Cards with Reservation Timers
```typescript
// components/patient-queue.tsx
'use client';

import { useState } from 'react';
import { CountdownTimer } from '@/components/countdown-timer';

export function IncomingPatientQueue({ patients, onAccept, onReject }) {
  return (
    <div className="space-y-4">
      {patients.map(request => (
        <PatientRequestCard
          key={request.id}
          request={request}
          onAccept={onAccept}
          onReject={onReject}
        />
      ))}
    </div>
  );
}

function PatientRequestCard({ request, onAccept, onReject }) {
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectForm, setShowRejectForm] = useState(false);
  
  return (
    <div className="bg-white dark:bg-neutral-900 rounded-lg p-6 shadow-sm border-l-4"
         style={{ borderLeftColor: SEVERITY_COLORS[request.severity] }}>
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Badge variant="solid" className={SEVERITY_BADGE_CLASSES[request.severity]}>
              {request.severity}
            </Badge>
            <span className="text-sm text-neutral-600 dark:text-neutral-400">
              {request.distance}km away • ETA {request.eta} min
            </span>
          </div>
          <h3 className="font-semibold text-lg">
            Patient Transfer Request
          </h3>
        </div>
        
        {/* Reservation expiry countdown */}
        {request.reservation && (
          <CountdownTimer
            expiresAt={request.reservation.expires_at}
            onExpire={() => showToast('Reservation expired', 'warning')}
          />
        )}
      </div>
      
      {/* Patient details */}
      <div className="space-y-2 text-sm mb-4">
        <div className="flex items-center gap-2">
          <span className="font-medium">Condition:</span>
          <span>{request.medical_condition}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-medium">Required Bed:</span>
          <span>{request.bed_type}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-medium">Ambulance:</span>
          <span>{request.ambulance_type} • {request.ambulance_id}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-medium">From:</span>
          <span>{request.origin_location}</span>
        </div>
      </div>
      
      {/* Medical history notes */}
      {request.medical_notes && (
        <div className="bg-neutral-50 dark:bg-neutral-800 rounded p-3 mb-4">
          <p className="text-sm text-neutral-700 dark:text-neutral-300">
            {request.medical_notes}
          </p>
        </div>
      )}
      
      {/* Actions */}
      {!showRejectForm ? (
        <div className="flex gap-2">
          <Button
            variant="solid"
            className="flex-1 bg-green-600 hover:bg-green-700"
            onClick={() => onAccept(request.id)}
          >
            ✓ Accept & Reserve Bed
          </Button>
          <Button
            variant="outline"
            className="text-red-600 border-red-600 hover:bg-red-50 dark:hover:bg-red-950"
            onClick={() => setShowRejectForm(true)}
          >
            Decline
          </Button>
        </div>
      ) : (
        <div className="space-y-2">
          <Select
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Select reason..."
          >
            <option value="NO_CAPACITY">No capacity available</option>
            <option value="WRONG_SPECIALTY">Wrong specialty</option>
            <option value="EQUIPMENT_UNAVAILABLE">Equipment unavailable</option>
            <option value="OTHER">Other reason</option>
          </Select>
          <div className="flex gap-2">
            <Button
              variant="solid"
              className="flex-1 bg-red-600 hover:bg-red-700"
              onClick={() => {
                onReject(request.id, rejectReason);
                setShowRejectForm(false);
              }}
              disabled={!rejectReason}
            >
              Confirm Decline
            </Button>
            <Button
              variant="outline"
              onClick={() => setShowRejectForm(false)}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
```

#### 4.3 Real-Time Ambulance Tracking
```typescript
// components/ambulance-fleet-status.tsx
'use client';

import { useAmbulanceFleet } from '@/hooks/useAmbulanceFleet';
import { LiveMap } from '@resq/maps/live-map';

export function AmbulanceFleetStatus() {
  const { ambulances } = useAmbulanceFleet();
  
  const byStatus = {
    available: ambulances.filter(a => a.status === 'AVAILABLE'),
    enRoute: ambulances.filter(a => a.status === 'EN_ROUTE_TO_SCENE'),
    transporting: ambulances.filter(a => a.status === 'TRANSPORTING_PATIENT'),
    outOfService: ambulances.filter(a => a.status === 'OUT_OF_SERVICE'),
  };
  
  return (
    <div className="space-y-4">
      {/* Status summary */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Available" value={byStatus.available.length} variant="success" />
        <StatCard label="En Route" value={byStatus.enRoute.length} variant="warning" />
        <StatCard label="Transporting" value={byStatus.transporting.length} variant="info" />
        <StatCard label="Out of Service" value={byStatus.outOfService.length} variant="error" />
      </div>
      
      {/* Live ambulance locations */}
      <div className="bg-white dark:bg-neutral-900 rounded-lg p-4 shadow-sm">
        <h3 className="font-semibold mb-4">Live Locations</h3>
        <LiveMap
          ambulances={ambulances}
          centerOnHospital
          height={400}
        />
      </div>
      
      {/* Ambulance list */}
      <div className="space-y-2">
        {ambulances.map(ambulance => (
          <AmbulanceCard key={ambulance.id} ambulance={ambulance} />
        ))}
      </div>
    </div>
  );
}
```

### Phase 4 Deliverables
- ✅ Real-time capacity dashboard
- ✅ Incoming patient request cards
- ✅ Bed reservation system with 30-min timers
- ✅ Accept/reject patient flow
- ✅ Ambulance fleet tracking
- ✅ Blood bank inventory integration
- ✅ Staff shift management
- ✅ Patient admission workflow

**Success Criteria:**
- < 10 seconds bed availability updates
- Zero double-booking incidents
- 100% reservation expiry handled correctly

---

## 🖥️ PHASE 5: CONTROL ROOM — SYSTEM OVERSIGHT (Weeks 13-15)

### Objective
Build the **command center dashboard** with system-wide visibility, manual overrides, analytics, and audit trails.

### Features

#### 5.1 Real-Time Incident Feed
```typescript
// apps/control-room/app/dashboard/page.tsx
'use client';

import { useIncidentFeed } from '@/hooks/useIncidentFeed';
import { IncidentCard } from '@/components/incident-card';
import { SystemMetrics } from '@/components/system-metrics';

export default function ControlRoomDashboard() {
  const {
    incidents,
    filter,
    setFilter,
    overrideStatus,
    reassignTask,
  } = useIncidentFeed();
  
  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      {/* Top metrics bar */}
      <header className="border-b border-neutral-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Emergency Control Room</h1>
          <SystemMetrics />
        </div>
      </header>
      
      <div className="flex h-[calc(100vh-73px)]">
        {/* Left sidebar: Filters */}
        <aside className="w-64 border-r border-neutral-800 p-4">
          <FilterPanel
            activeFilter={filter}
            onFilterChange={setFilter}
          />
        </aside>
        
        {/* Center: Incident feed */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl space-y-4">
            {incidents.map(incident => (
              <IncidentCard
                key={incident.id}
                incident={incident}
                onOverride={overrideStatus}
                onReassign={reassignTask}
              />
            ))}
          </div>
        </main>
        
        {/* Right sidebar: Live map */}
        <aside className="w-96 border-l border-neutral-800">
          <LiveSystemMap />
        </aside>
      </div>
    </div>
  );
}
```

#### 5.2 Analytics Dashboard
```typescript
// apps/control-room/app/analytics/page.tsx
'use client';

import { useSystemAnalytics } from '@/hooks/useSystemAnalytics';
import { LineChart, BarChart, PieChart } from '@resq/charts';

export default function AnalyticsDashboard() {
  const {
    responseTimeMetrics,
    incidentsByType,
    resourceUtilization,
    successRates,
  } = useSystemAnalytics();
  
  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950 p-8">
      <h1 className="text-3xl font-bold mb-8">System Analytics</h1>
      
      <div className="grid gap-6 mb-8 md:grid-cols-4">
        <MetricCard
          label="Avg Response Time"
          value={`${responseTimeMetrics.average}s`}
          change={responseTimeMetrics.change}
          trend={responseTimeMetrics.trend}
        />
        <MetricCard
          label="Active Incidents"
          value={responseTimeMetrics.activeCount}
          change={'+12'}
          trend="up"
        />
        <MetricCard
          label="Success Rate"
          value={`${successRates.overall}%`}
          change={successRates.change}
          trend="up"
        />
        <MetricCard
          label="Resource Utilization"
          value={`${resourceUtilization.average}%`}
          change={resourceUtilization.change}
          trend="stable"
        />
      </div>
      
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Response times over time */}
        <ChartCard title="Response Time Trend">
          <LineChart
            data={responseTimeMetrics.history}
            xKey="timestamp"
            yKey="responseTime"
            height={300}
          />
        </ChartCard>
        
        {/* Incidents by type */}
        <ChartCard title="Incidents by Type">
          <BarChart
            data={incidentsByType}
            xKey="type"
            yKey="count"
            height={300}
          />
        </ChartCard>
        
        {/* Resource utilization */}
        <ChartCard title="Resource Utilization">
          <PieChart
            data={resourceUtilization.byType}
            height={300}
          />
        </ChartCard>
        
        {/* Geographic heatmap */}
        <ChartCard title="Incident Heatmap">
          <IncidentHeatmap
            incidents={incidents}
            height={300}
          />
        </ChartCard>
      </div>
    </div>
  );
}
```

#### 5.3 Audit Log Viewer
```typescript
// apps/control-room/app/audit/page.tsx
'use client';

import { useAuditLogs } from '@/hooks/useAuditLogs';
import { AuditLogTable } from '@/components/audit-log-table';

export default function AuditPage() {
  const {
    logs,
    filters,
    setFilters,
    exportLogs,
  } = useAuditLogs();
  
  return (
    <div className="min-h-screen bg-white dark:bg-neutral-900 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">Audit Trail</h1>
          <Button onClick={exportLogs}>
            Export CSV
          </Button>
        </div>
        
        {/* Filter bar */}
        <div className="grid gap-4 mb-6 md:grid-cols-5">
          <Select
            value={filters.actor}
            onChange={(e) => setFilters({ ...filters, actor: e.target.value })}
            placeholder="Filter by actor..."
          >
            <option value="">All Actors</option>
            <option value="AGENT_SYSTEM">AI Agent</option>
            <option value="CONTROL_ROOM">Control Room</option>
            <option value="FIELD_RESPONDER">Responder</option>
          </Select>
          
          <Select
            value={filters.action}
            onChange={(e) => setFilters({ ...filters, action: e.target.value })}
            placeholder="Filter by action..."
          >
            <option value="">All Actions</option>
            <option value="incident_created">Incident Created</option>
            <option value="task_assigned">Task Assigned</option>
            <option value="capacity_updated">Capacity Updated</option>
          </Select>
          
          <Input
            type="date"
            value={filters.startDate}
            onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
          />
          
          <Input
            type="date"
            value={filters.endDate}
            onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
          />
          
          <Input
            type="search"
            placeholder="Search..."
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          />
        </div>
        
        {/* Audit table */}
        <AuditLogTable
          logs={logs}
          onRowClick={(log) => setSelectedLog(log)}
        />
      </div>
    </div>
  );
}
```

### Phase 5 Deliverables
- ✅ Real-time incident feed with filters
- ✅ System-wide analytics dashboard
- ✅ Manual override controls
- ✅ Task reassignment interface
- ✅ Audit log viewer with search
- ✅ Export functionality (CSV, PDF)
- ✅ System health monitoring
- ✅ Alert configuration

**Success Criteria:**
- < 1 second incident feed updates
- Analytics queries < 2 seconds
- Audit logs searchable back 90 days

---

## 🎨 PHASE 6: POLISH & ADVANCED FEATURES (Weeks 16-18)

### Objective
Add **industry-differentiating features** that elevate RESQ from functional to exceptional.

### Advanced Features

#### 6.1 Smart Notifications System
```typescript
// packages/notifications/src/NotificationEngine.ts
import { OneSignal } from 'onesignal-node';

export class NotificationEngine {
  async send(userId: string, notification: Notification) {
    // Route by urgency
    if (notification.priority === 'CRITICAL') {
      await this.sendPushWithVibration(userId, notification);
      await this.sendSMS(userId, notification);
      await this.triggerPhoneCall(userId, notification);
    } else if (notification.priority === 'HIGH') {
      await this.sendPushWithSound(userId, notification);
    } else {
      await this.sendSilentPush(userId, notification);
    }
  }
  
  async sendPushWithVibration(userId: string, notification: Notification) {
    return OneSignal.createNotification({
      include_external_user_ids: [userId],
      contents: { en: notification.message },
      headings: { en: notification.title },
      priority: 10,
      ttl: 0,  // Immediate delivery
      android_channel_id: 'emergency_critical',
      ios_sound: 'emergency_alert.wav',
      android_sound: 'emergency_alert',
      android_led_color: 'FFFF0000',
      android_accent_color: 'FFFF0000',
      vibrate: [0, 200, 100, 200, 100, 200],
    });
  }
}
```

#### 6.2 Predictive Resource Allocation
```typescript
// AI-powered resource prediction
// apps/control-room/lib/predictions.ts

export async function predictResourceNeeds(incident: Incident) {
  // Historical pattern analysis
  const similar = await getSimilarIncidents(incident);
  
  const prediction = {
    likelyNeeds: {
      rescueTeams: calculateMedian(similar.map(i => i.rescue_teams_used)),
      ambulances: calculateMedian(similar.map(i => i.ambulances_used)),
      hospitalBeds: calculateMedian(similar.map(i => i.hospital_beds_used)),
      estimatedDuration: calculateMedian(similar.map(i => i.duration_minutes)),
    },
    confidence: calculateConfidence(similar.length),
    recommendations: generateRecommendations(prediction),
  };
  
  return prediction;
}

// Display in Control Room
<PredictionPanel incident={incident}>
  <h3>Predicted Resource Needs</h3>
  <ul>
    <li>Rescue Teams: {prediction.rescueTeams} (85% confidence)</li>
    <li>Ambulances: {prediction.ambulances} (78% confidence)</li>
    <li>Duration: ~{prediction.estimatedDuration} minutes</li>
  </ul>
</PredictionPanel>
```

#### 6.3 Collaborative Task Notes
```typescript
// Real-time collaborative editing with conflict resolution
import { useYDoc } from '@/hooks/useYDoc';
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';

export function CollaborativeTaskNotes({ taskId }: { taskId: string }) {
  const { doc, text, users } = useYDoc(`task-${taskId}`);
  
  return (
    <div>
      {/* Show who's typing */}
      {users.length > 1 && (
        <div className="text-sm text-neutral-600 mb-2">
          {users.filter(u => u.id !== currentUser.id).map(u => u.name).join(', ')} {users.length > 2 ? 'are' : 'is'} typing...
        </div>
      )}
      
      <RichTextEditor
        content={text}
        onChange={(newText) => {
          // Yjs handles conflict resolution automatically
          text.delete(0, text.length);
          text.insert(0, newText);
        }}
        placeholder="Add notes about this task..."
      />
    </div>
  );
}
```

#### 6.4 Advanced Search
```typescript
// apps/control-room/components/GlobalSearch.tsx
'use client';

import { useSearch } from '@/hooks/useSearch';
import { Command } from 'cmdk';

export function GlobalSearch() {
  const { results, search, loading } = useSearch();
  const [open, setOpen] = useState(false);
  
  // Keyboard shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen(true);
      }
    };
    
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);
  
  return (
    <Command.Dialog open={open} onOpenChange={setOpen}>
      <Command.Input
        placeholder="Search incidents, tasks, users..."
        onValueChange={search}
      />
      
      <Command.List>
        {loading && <Command.Loading>Searching...</Command.Loading>}
        
        <Command.Group heading="Incidents">
          {results.incidents?.map(incident => (
            <Command.Item
              key={incident.id}
              onSelect={() => router.push(`/incidents/${incident.id}`)}
            >
              <SearchIcon className="mr-2" />
              <span>{incident.incident_number}</span>
              <span className="ml-auto text-sm text-neutral-500">
                {incident.status}
              </span>
            </Command.Item>
          ))}
        </Command.Group>
        
        <Command.Group heading="Tasks">
          {results.tasks?.map(task => (
            <Command.Item
              key={task.id}
              onSelect={() => router.push(`/tasks/${task.id}`)}
            >
              <TaskIcon className="mr-2" />
              <span>{task.task_type}</span>
              <span className="ml-auto text-sm text-neutral-500">
                {task.priority}
              </span>
            </Command.Item>
          ))}
        </Command.Group>
      </Command.List>
    </Command.Dialog>
  );
}
```

#### 6.5 Data Export & Reporting
```typescript
// Generate comprehensive incident reports
export async function generateIncidentReport(incidentId: string) {
  const incident = await api.incidents.get(incidentId);
  const tasks = await api.incidents.getTasks(incidentId);
  const auditLogs = await api.auditLogs.getByIncident(incidentId);
  
  // Generate PDF report
  const pdf = await generatePDF({
    template: 'incident-report',
    data: {
      incident,
      tasks,
      auditLogs,
      timeline: buildTimeline(incident, tasks, auditLogs),
      resourcesUsed: calculateResourcesUsed(tasks),
      totalCost: calculateCost(tasks),
      responseMetrics: {
        timeToFirstResponse: calculateTimeToFirstResponse(incident, tasks),
        timeToResolution: calculateTimeToResolution(incident),
        successRate: calculateSuccessRate(incident),
      },
    },
  });
  
  return pdf;
}
```

### Phase 6 Deliverables
- ✅ Smart notification system (push, SMS, call)
- ✅ Predictive resource allocation
- ✅ Collaborative task notes
- ✅ Global search (Cmd+K)
- ✅ Data export (PDF, CSV, JSON)
- ✅ Incident report generator
- ✅ Performance optimizations
- ✅ Lighthouse score > 95

---

## 🔒 PHASE 7: COMPLIANCE & PRODUCTION READINESS (Weeks 19-21)

### Objective
Ensure **regulatory compliance, security hardening, and production deployment readiness**.

### Compliance

#### 7.1 HIPAA Compliance Checklist
- ✅ PHI encrypted at rest (Phase 1)
- ✅ PHI encrypted in transit (TLS 1.3)
- ✅ Access control with RBAC
- ✅ Audit logging (all PHI access logged)
- ✅ Business Associate Agreements (BAA) templates
- ✅ Breach notification procedures
- ✅ Data retention policies (7 years)
- ✅ Automatic PHI purging after retention period

#### 7.2 GDPR Compliance
```typescript
// Data export for subject access requests
export async function exportUserData(userId: string) {
  const userData = {
    profile: await db.users.findOne({ id: userId }),
    incidents: await db.incidentReports.find({ reporter_id: userId }),
    tasks: await db.responseTasks.find({ assigned_user_id: userId }),
    auditLogs: await db.auditLogs.find({ actor_id: userId }),
  };
  
  // Anonymize referenced data
  return anonymizeExport(userData);
}

// Right to be forgotten
export async function deleteUserData(userId: string) {
  await db.transaction(async (tx) => {
    // Anonymize instead of delete (preserve audit trail)
    await tx.users.update(userId, {
      email: `deleted_${userId}@anonymized.local`,
      phone: 'REDACTED',
      full_name: 'DELETED USER',
      is_active: false,
      deleted_at: new Date(),
    });
    
    // Redact personal data from incident reports
    await tx.incidentReports.updateMany(
      { reporter_id: userId },
      {
        reporter_name: 'REDACTED',
        reporter_phone: 'REDACTED',
      }
    );
  });
}
```

#### 7.3 SOC 2 Type II Preparation
- ✅ Incident response plan documented
- ✅ Disaster recovery procedures
- ✅ Penetration testing (annual)
- ✅ Vulnerability scanning (weekly)
- ✅ Employee security training
- ✅ Third-party vendor assessments

### Production Infrastructure

#### 7.4 High Availability Setup
```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: resq-backend
spec:
  replicas: 3  # Multi-instance for HA
  strategy:
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
      - name: fastapi
        image: resq/backend:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
      
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - resq-backend
              topologyKey: kubernetes.io/hostname

---
# PostgreSQL with read replicas
apiVersion: v1
kind: Service
metadata:
  name: postgres-primary
spec:
  selector:
    app: postgres
    role: primary
  ports:
  - port: 5432

---
apiVersion: v1
kind: Service
metadata:
  name: postgres-replica
spec:
  selector:
    app: postgres
    role: replica
  ports:
  - port: 5432
```

#### 7.5 Monitoring & Alerting
```python
# backend/app/observability/alerts.py
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration_seconds = Histogram(
    'request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

active_incidents = Gauge(
    'active_incidents_total',
    'Number of active incidents',
    ['status', 'priority']
)

# Alert rules (Prometheus)
groups:
  - name: resq_alerts
    rules:
    - alert: HighErrorRate
      expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
      for: 5m
      annotations:
        summary: "High error rate detected"
    
    - alert: SlowResponseTime
      expr: histogram_quantile(0.95, request_duration_seconds) > 1
      for: 10m
      annotations:
        summary: "95th percentile response time > 1s"
    
    - alert: DatabaseConnectionPoolExhausted
      expr: db_connection_pool_available < 5
      for: 2m
      annotations:
        summary: "Database connection pool nearly exhausted"
```

### Phase 7 Deliverables
- ✅ HIPAA compliance documentation
- ✅ GDPR compliance (data export, deletion)
- ✅ SOC 2 preparation
- ✅ Kubernetes deployment configs
- ✅ Multi-region setup (primary + DR)
- ✅ Monitoring & alerting configured
- ✅ Load testing (10k concurrent users)
- ✅ Security audit completed

---

## 🧪 PHASE 8: TESTING & LAUNCH (Weeks 22-24)

### Objective
Comprehensive testing, beta launch, and go-to-market preparation.

### Testing Strategy

#### 8.1 E2E Testing Suite
```typescript
// tests/e2e/citizen-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Citizen SOS Flow', () => {
  test('should submit SOS and track incident', async ({ page }) => {
    // Navigate to SOS page
    await page.goto('/sos');
    
    // Fill form
    await page.fill('[name="description"]', 'Trapped in flood water');
    await page.selectOption('[name="emergency_type"]', 'FLOOD');
    await page.fill('[name="people_affected"]', '3');
    
    // Submit
    await page.click('button:has-text("Send Emergency Report")');
    
    // Wait for redirect to tracking page
    await page.waitForURL(/\/track\/trk_.+/);
    
    // Verify tracking page loads
    await expect(page.locator('h1')).toContainText('Tracking');
    await expect(page.locator('[data-testid="status-badge"]')).toContainText('REPORTED');
    
    // Verify timeline exists
    await expect(page.locator('[data-testid="timeline"]')).toBeVisible();
  });
  
  test('should work offline', async ({ page, context }) => {
    // Go offline
    await context.setOffline(true);
    
    await page.goto('/sos');
    
    // Submit form
    await page.fill('[name="description"]', 'Offline test');
    await page.click('button:has-text("Send Emergency Report")');
    
    // Verify offline indicator
    await expect(page.locator('[data-testid="offline-indicator"]')).toContainText('Offline Mode');
    
    // Go back online
    await context.setOffline(false);
    
    // Wait for sync
    await page.waitForSelector('[data-testid="sync-success"]', { timeout: 10000 });
  });
});

// tests/e2e/responder-flow.spec.ts
test.describe('Responder Task Flow', () => {
  test('should accept and complete task', async ({ page }) => {
    // Login as responder
    await page.goto('/login');
    await page.fill('[name="email"]', 'responder@rescue-team-a.org');
    await page.fill('[name="password"]', 'password123');
    await page.click('button:has-text("Login")');
    
    // Navigate to dashboard
    await page.waitForURL('/responder/dashboard');
    
    // Accept first task
    await page.click('[data-testid="task-card"]:first-child button:has-text("Accept")');
    
    // Verify active task banner appears
    await expect(page.locator('[data-testid="active-task-banner"]')).toBeVisible();
    
    // Update status to arrived
    await page.click('button:has-text("Mark Arrived")');
    
    // Complete task
    await page.click('button:has-text("Complete Task")');
    await page.fill('[name="completion_notes"]', 'Rescue successful');
    await page.click('button:has-text("Confirm Complete")');
    
    // Verify task removed from queue
    await expect(page.locator('[data-testid="active-task-banner"]')).not.toBeVisible();
  });
});
```

#### 8.2 Load Testing
```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class CitizenUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def submit_sos(self):
        self.client.post('/api/v1/incidents/report', json={
            'description': 'Load test SOS',
            'location': {'type': 'Point', 'coordinates': [76.2711, 10.8505]},
            'district': 'Ernakulam',
            'people_affected': 1,
        })
    
    @task(1)
    def track_incident(self):
        self.client.get(f'/api/v1/incidents/track/{self.tracking_token}')

class ResponderUser(HttpUser):
    wait_time = between(5, 10)
    
    def on_start(self):
        # Login
        response = self.client.post('/api/v1/auth/login', json={
            'email': 'responder@test.org',
            'password': 'password',
        })
        self.token = response.json()['access_token']
    
    @task
    def get_tasks(self):
        self.client.get('/api/v1/tasks', headers={
            'Authorization': f'Bearer {self.token}'
        })

# Run: locust -f tests/load/locustfile.py --headless -u 10000 -r 100 --run-time 10m
```

#### 8.3 Beta Launch Checklist
- ✅ Feature flags configured (gradual rollout)
- ✅ Beta user group identified (100 hospitals, 500 responders)
- ✅ Feedback mechanism (in-app + email)
- ✅ Rollback plan documented
- ✅ On-call rotation scheduled
- ✅ Status page configured (status.resq.org)
- ✅ Documentation site live (docs.resq.org)
- ✅ Training materials (videos, guides)

### Phase 8 Deliverables
- ✅ E2E test suite (100+ scenarios)
- ✅ Load test results (10k users, < 200ms P95)
- ✅ Security penetration test passed
- ✅ Beta launch successful (99.9% uptime)
- ✅ User feedback incorporated
- ✅ Production launch approved

---

## 🎉 SUCCESS METRICS & KPIs

### Technical Metrics
- **Uptime:** 99.95% (< 4.5 hours downtime/year)
- **Response Time:** < 100ms P50, < 200ms P95
- **Concurrent Users:** 10,000+ supported
- **Database Query Time:** < 50ms P95
- **WebSocket Latency:** < 100ms
- **Lighthouse Score:** > 95 (all categories)
- **Bundle Size:** < 200KB initial load
- **Time to Interactive:** < 2s on 3G

### Business Metrics
- **Response Time:** < 90 seconds SOS → dispatch
- **Success Rate:** > 95% incidents resolved
- **User Satisfaction:** > 4.5/5.0
- **Adoption Rate:** 80% of emergency services in target region
- **Cost Per Incident:** < $50 infrastructure cost
- **Data Accuracy:** 99%+ location accuracy

### Compliance Metrics
- **Security Incidents:** 0 PHI breaches
- **Audit Compliance:** 100% audit logs captured
- **Uptime SLA:** 99.9% met
- **Data Retention:** 100% compliance with policy
- **Vulnerability Patching:** < 24 hours for critical

---

## 🚀 DEPLOYMENT ARCHITECTURE

### Production Infrastructure
```
┌─────────────────────────────────────────────────────────────┐
│                     Cloudflare CDN + DDoS                    │
└───────────────────────┬──────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────┐
│                  Load Balancer (ALB)                          │
│              SSL Termination + WAF                            │
└───────┬──────────────────────────────────────┬───────────────┘
        │                                      │
┌───────▼─────────┐                  ┌────────▼────────────────┐
│   Frontend      │                  │   Backend API           │
│   (Vercel)      │                  │   (Kubernetes)          │
│                 │                  │   - 3 replicas          │
│ - Next.js Apps  │                  │   - Auto-scaling        │
│ - Edge Cache    │                  │   - Rolling updates     │
│ - Global CDN    │                  │                         │
└─────────────────┘                  └────────┬────────────────┘
                                              │
                        ┌─────────────────────┼─────────────────┐
                        │                     │                 │
              ┌─────────▼────────┐  ┌────────▼────────┐  ┌────▼────┐
              │   PostgreSQL      │  │    Redis        │  │  S3     │
              │   (Primary +      │  │  (Cache +       │  │ (Files) │
              │   2 Replicas)     │  │   PubSub)       │  │         │
              │                   │  │                 │  │         │
              │ - Auto-backup     │  │ - Cluster mode  │  │         │
              │ - Point-in-time   │  │ - Sentinel HA   │  │         │
              │   recovery        │  │                 │  │         │
              └───────────────────┘  └─────────────────┘  └─────────┘
```

---

## 💰 ESTIMATED TIMELINE & COST

### Timeline: 24 Weeks (6 Months)
- **Phase 1:** 3 weeks
- **Phase 2:** 3 weeks
- **Phase 3:** 3 weeks
- **Phase 4:** 3 weeks
- **Phase 5:** 3 weeks
- **Phase 6:** 3 weeks
- **Phase 7:** 3 weeks
- **Phase 8:** 3 weeks

### Team Composition
- **1x Full-Stack Lead** (React + FastAPI + DevOps)
- **1x Frontend Engineer** (React specialist)
- **1x Backend Engineer** (Python + PostgreSQL)
- **1x DevOps Engineer** (Kubernetes + Monitoring)
- **0.5x UI/UX Designer** (Design system + user testing)
- **0.5x QA Engineer** (Test automation)

### Infrastructure Cost (Monthly)
- **Hosting (Kubernetes):** $500
- **Database (PostgreSQL + Replicas):** $300
- **Redis (Managed):** $100
- **CDN (Cloudflare):** $200
- **Monitoring (Datadog/New Relic):** $150
- **S3 Storage:** $50
- **SMS/Push Notifications:** $200
- **Mapbox API:** $150
- **SSL Certificates:** $0 (Let's Encrypt)
- **Backup Storage:** $100

**Total: ~$1,750/month**

---

## 🎯 NEXT STEPS

### Week 1 Action Items
1. Set up monorepo with Turborepo
2. Implement field encryption (backend)
3. Generate TypeScript API client
4. Create design system tokens
5. Set up CI/CD pipeline

### Quick Wins (First 2 Weeks)
- Citizen SOS form (minimal, functional)
- Live tracking page (basic)
- Responder task queue (read-only)
- Deploy to staging environment

---

**This roadmap transforms RESQ into a world-class emergency coordination platform that rivals industry leaders while remaining accessible, reliable, and human-centered. Every feature serves the mission: saving lives through technology.** 🚀🚨
