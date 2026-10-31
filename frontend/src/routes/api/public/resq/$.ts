import { createFileRoute } from "@tanstack/react-router";

// Forwards browser requests to the RESQ FastAPI backend so the app is not
// blocked by the backend's CORS allow-list. Only the fixed backend host is reachable.
const BASE = "https://tied-politics-supervision-blink.trycloudflare.com";

async function forward(request: Request, splat: string) {
  const url = new URL(request.url);
  const path = splat.replace(/^\/+/, "");
  if (path.includes("..")) return new Response("Bad path", { status: 400 });
  const target = `${BASE}/${path}${url.search}`;
  const headers = new Headers();
  const auth = request.headers.get("authorization");
  if (auth) headers.set("authorization", auth);
  const ct = request.headers.get("content-type");
  if (ct) headers.set("content-type", ct);
  try {
    const init: RequestInit = { method: request.method, headers };
    if (!["GET", "HEAD"].includes(request.method)) init.body = await request.text();
    const res = await fetch(target, init);
    return new Response(await res.text(), {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
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
