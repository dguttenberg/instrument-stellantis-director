import type { NextConfig } from "next";

// Dev: Next dev server proxies API calls to the FastAPI backend (no CORS).
// Prod: STATIC_EXPORT=1 builds a static SPA (web/out) that FastAPI serves directly,
// so there is no Next server to do rewrites — calls go same-origin instead.
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://localhost:8000";
const STATIC_EXPORT = process.env.STATIC_EXPORT === "1";

const nextConfig: NextConfig = {
  // Pin the workspace root to this app (a stray ~/package-lock.json otherwise
  // makes Turbopack infer the home dir as root).
  turbopack: { root: __dirname },
  ...(STATIC_EXPORT
    ? { output: "export", images: { unoptimized: true } }
    : {
        async rewrites() {
          return [
            { source: "/api/be/:path*", destination: `${BACKEND_ORIGIN}/:path*` },
          ];
        },
      }),
};

export default nextConfig;
