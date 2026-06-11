import type { NextConfig } from "next";

// The Director front end calls the existing FastAPI backend through a same-origin
// proxy so the browser never makes a cross-origin request (no CORS, no backend
// change). All API calls go to /api/be/* and are rewritten to the backend.
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Pin the workspace root to this app (a stray ~/package-lock.json otherwise
  // makes Turbopack infer the home dir as root).
  turbopack: { root: __dirname },
  async rewrites() {
    return [
      { source: "/api/be/:path*", destination: `${BACKEND_ORIGIN}/:path*` },
    ];
  },
};

export default nextConfig;
