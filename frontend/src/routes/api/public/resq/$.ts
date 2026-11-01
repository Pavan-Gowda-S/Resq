import { createFileRoute } from "@tanstack/react-router";

// Forwards browser requests to the RESQ FastAPI backend so the app is not
// blocked by the backend's CORS allow-list. Only the fixed backend host is reachable.
const BASE = process.env.VITE_BACKEND_URL || "https://competitors-fees-robertson-whom.trycloudflare.com";

// Lightweight proxy-level cache to protect the Cloudflare tunnel from rate limiting / resource exhaustion
const proxyGetCache = new Map<string, { time: number; status: number; text: string; contentType: string }>();
const CACHE_TTL_MS = 3500; // 3.5s cache for read queries across open tabs

async function forward(request: Request, splat: string) {
  const url = new URL(request.url);
  const rawPath = splat || url.pathname.replace(/^\/api\/public\/resq\/?/, "");
  const path = rawPath.replace(/^\/+/, "");
  if (path.includes("..")) return new Response("Bad path", { status: 400 });
  const target = `${BASE}/${path}${url.search}`;
  console.log(`[PROXY] Forwarding ${request.method} ${url.pathname} to ${target}`);

  // Serve from cache for repeated GETs to prevent Cloudflare tunnel rate limiting
  if (request.method === "GET") {
    const cached = proxyGetCache.get(target);
    if (cached && Date.now() - cached.time < CACHE_TTL_MS) {
      return new Response(cached.text, {
        status: cached.status,
        headers: {
          "content-type": cached.contentType,
          "x-resq-cache": "HIT",
        },
      });
    }
  }

  const headers = new Headers();
  const auth = request.headers.get("authorization");
  if (auth) headers.set("authorization", auth);
  const ct = request.headers.get("content-type");
  if (ct) headers.set("content-type", ct);
  try {
    const init: RequestInit = { method: request.method, headers };
    if (!["GET", "HEAD"].includes(request.method)) init.body = await request.text();
    const res = await fetch(target, init);
    const text = await res.text();
    const contentType = res.headers.get("content-type") ?? "application/json";

    if (request.method === "GET" && res.status === 200) {
      proxyGetCache.set(target, { time: Date.now(), status: res.status, text, contentType });
    } else if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method)) {
      // Invalidate read cache immediately on state changes
      proxyGetCache.clear();
    }

    return new Response(text, {
      status: res.status,
      headers: { "content-type": contentType },
    });
  } catch {
    return Response.json({ detail: "Backend unreachable" }, { status: 502 });
  }
}

export const Route = createFileRoute("/api/public/resq/$")({
  server: {
    handlers: {
      GET: ({ request, params }) => forward(request, params._splat ?? ""),
      POST: ({ request, params }) => forward(request, params._splat ?? ""),
      PUT: ({ request, params }) => forward(request, params._splat ?? ""),
      PATCH: ({ request, params }) => forward(request, params._splat ?? ""),
    },
  },
});
